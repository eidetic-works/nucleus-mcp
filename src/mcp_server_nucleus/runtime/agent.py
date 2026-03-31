from typing import Dict, Any, List
from .. import commitment_ledger
from pathlib import Path
import os
import json
import hashlib
import uuid
from datetime import datetime, timezone

# v0.6.0 DSoR: Import context manager and IPC auth
from .context_manager import get_context_manager
from .auth import get_ipc_auth_manager, IPCToken
# v0.6.1: Agent Runtime V2 integration
from .agent_runtime_v2 import get_execution_manager, check_cancellation
from .budget_alerts import get_budget_monitor
# Phase 71: Tool Calling Enforcement
from .llm_tool_enforcer import get_tool_enforcer
from .llm_pattern_learner import get_pattern_learner
# Phase 72: Autonomous Tool Discovery
from .tool_recommender import get_tool_recommender

# Gemini types imported dynamically or duck-typed via DualEngineLLM

def get_brain_path_internal() -> Path:
    """Helper to get brain path inside runtime"""
    return Path(os.getenv("NUCLEAR_BRAIN_PATH", "./.brain"))

class DecisionMade:
    """
    NOP v3.0: The "Why" Link.
    Represents a sovereign decision with cryptographic anchoring.
    v0.6.0 DSoR: Now emitted before every tool execution for full provenance.
    """
    def __init__(self, decision_id: str, reasoning: str, context_hash: str, confidence: float = 1.0):
        self.decision_id = decision_id
        self.reasoning = reasoning
        self.context_hash = context_hash
        self.confidence = confidence
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for ledger storage"""
        return {
            "decision_id": self.decision_id,
            "reasoning": self.reasoning,
            "context_hash": self.context_hash,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }

class ActionRequested:
    """
    NOP v3.0: The "What" Linked to "Why".
    """
    def __init__(self, action_id: str, decision_id: str, tool_name: str, args: Dict):
        self.action_id = action_id
        self.decision_id = decision_id
        self.tool_name = tool_name
        self.args = args

class EphemeralAgent:
    """
    The Runtime.
    A disposable agent that runs until completion.
    MDR_005: Supports both LLM-driven (Smart) and Heuristic (Fast) modes.
    MDR_002: Implements Active Correction (Critic) in LLM mode.
    v0.6.0 DSoR: Emits DecisionMade events before every tool execution.
    """
    def __init__(self, context: Dict[str, Any], model: Any = None, timeout_seconds: int = 300):
        self.context = context
        self.model = model
        self.history: List[str] = []
        self.active = True
        self._decision_ledger: List[DecisionMade] = []  # v0.6.0: Track all decisions
        self._current_ipc_token: IPCToken = None  # v0.6.0: Current IPC token for tool calls
        self._context_manager = get_context_manager()  # v0.6.0: For state verification
        
        # v0.6.1: Agent Runtime V2 integration
        self._execution_manager = get_execution_manager()
        self._agent_id: str = None
        self._timeout_seconds = timeout_seconds
        
        # Phase 71: Tool Calling Enforcement
        self._tool_enforcer = get_tool_enforcer()
        self._pattern_learner = get_pattern_learner()
        self._tools_called: List[str] = []  # Track tools called in this execution
        
        # Phase 72: Autonomous Tool Discovery
        self._tool_recommender = get_tool_recommender()
    
    def _compute_context_hash(self, current_history: List[str]) -> str:
        """
        v0.6.0 DSoR: Compute SHA-256 hash of current world-state.
        Includes: persona, intent, and recent execution history.
        """
        state_blob = json.dumps({
            "persona": self.context.get('persona', 'unknown'),
            "intent": self.context.get('intent', ''),
            "history_tail": current_history[-5:] if current_history else [],
            "tools_available": [t['name'] for t in self.context.get('tools', [])]
        }, sort_keys=True)
        return hashlib.sha256(state_blob.encode()).hexdigest()[:16]
    
    def _emit_decision(self, tool_name: str, args: Dict, reasoning: str, 
                       current_history: List[str], confidence: float = 0.9) -> DecisionMade:
        """
        v0.6.0 DSoR: Emit and persist a DecisionMade event before tool execution.
        This creates the cryptographic provenance trail required by the DSoR spec.
        Also issues an IPC token linked to this decision for security.
        """
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        context_hash = self._compute_context_hash(current_history)
        
        decision = DecisionMade(
            decision_id=decision_id,
            reasoning=f"Tool: {tool_name} | {reasoning}",
            context_hash=context_hash,
            confidence=confidence
        )
        
        self._decision_ledger.append(decision)
        
        # v0.6.0 DSoR: Issue IPC token linked to this decision
        try:
            ipc_manager = get_ipc_auth_manager()
            token = ipc_manager.issue_token(
                scope="tool_call",
                decision_id=decision_id
            )
            # Store token for later use in _execute_tool
            self._current_ipc_token = token
        except Exception:
            self._current_ipc_token = None
        
        # Persist to decision log
        try:
            brain_path = get_brain_path_internal()
            decisions_dir = brain_path / "ledger" / "decisions"
            decisions_dir.mkdir(parents=True, exist_ok=True)
            
            # Append to decisions.jsonl (append-only ledger)
            decisions_file = decisions_dir / "decisions.jsonl"
            with open(decisions_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # Non-blocking persistence
        
        return decision

    async def run(self) -> str:
        """
        Execute the agent loop.
        Returns execution log.
        v0.6.0 DSoR: Takes before/after snapshots for state verification.
        v0.6.1: Integrated with Agent Runtime V2 for rate limiting, cost tracking, cancellation.
        """
        # v0.6.1: Spawn with rate limiting
        persona = self.context.get('persona', 'unknown')
        intent = self.context.get('intent', '')
        execution_status = "completed"
        
        try:
            execution = self._execution_manager.spawn_agent(
                persona=persona,
                intent=intent,
                timeout_seconds=self._timeout_seconds
            )
            self._agent_id = execution.agent_id
            self._execution_manager.start_execution(self._agent_id)
        except Exception as e:
            # Rate limited or other spawn error
            return f"Agent spawn failed: {e}"
        
        # MDR_010: Auto-record telemetry
        try:
             brain_path = get_brain_path_internal()
             commitment_ledger.record_interaction(brain_path)
        except Exception:
             pass 

        log = []
        log.append(f"--- Spawning Ephemeral Agent ({persona}) [ID: {self._agent_id}] ---")
        log.append(f"Intent: {intent}")
        
        # v0.6.0 DSoR: Take "before" snapshot for state verification
        before_snapshot = None
        try:
            before_snapshot = self._context_manager.take_snapshot(
                metadata={
                    "agent_persona": self.context.get('persona'),
                    "agent_intent": self.context.get('intent'),
                    "snapshot_type": "before_run"
                }
            )
            log.append(f"📸 State snapshot: {before_snapshot.snapshot_id} (pre-run)")
        except Exception:
            pass
        
        # Execute the agent
        if self.model:
            result = await self._run_llm(log)
        else:
            result = self._run_heuristic(log)
        
        # v0.6.0 DSoR: Take "after" snapshot and verify integrity
        try:
            after_snapshot = self._context_manager.take_snapshot(
                metadata={
                    "agent_persona": self.context.get('persona'),
                    "decisions_made": len(self._decision_ledger),
                    "snapshot_type": "after_run"
                }
            )
            
            if before_snapshot:
                # Verify state integrity (allow ledger mutations from decisions)
                verification = self._context_manager.verify_state_integrity(
                    before_snapshot, 
                    after_snapshot,
                    allowed_mutations=["ledger", "recent_events"]
                )
                
                if not verification.is_valid:
                    # Log unexpected mutations (potential security issue)
                    log.append(f"⚠️ Unexpected state mutations: {verification.mutations_detected}")
                else:
                    log.append(f"✅ State integrity verified (hash: {after_snapshot.state_hash})")
                
                # Persist snapshots for audit
                self._context_manager.persist_snapshot(before_snapshot)
                self._context_manager.persist_snapshot(after_snapshot)
        except Exception:
            pass
        
        # v0.6.1: Complete execution tracking and budget monitoring
        if self._agent_id:
            cost_record = self._execution_manager.complete_execution(self._agent_id, execution_status)
            
            # Check budget thresholds
            if cost_record:
                budget_monitor = get_budget_monitor()
                budget_monitor.check_agent_cost(
                    self._agent_id, 
                    persona, 
                    cost_record.estimated_cost_usd
                )
                budget_monitor.record_spend(cost_record.estimated_cost_usd)
        
        return result

    async def _run_llm(self, log: List[str]) -> str:
        """
        MDR_005 / MDR_002: Real LLM Execution Loop with Critic & Multi-Turn Support
        """
        log.append(">> Mode: LLM (Smart)")
        
        # Phase 71: Pre-flight intent analysis
        intent_result = None
        enforcement_prompt = ""
        user_intent = self.context.get('intent', '')
        try:
            intent_result = self._tool_enforcer.pre_flight(
                user_intent,
                self.context.get('tools', [])
            )
            enforcement_prompt = self._tool_enforcer.generate_enforcement_prompt(intent_result)
            
            # Phase D: Context Retrieval Gate (Phase 71 enhancement)
            # If LLM detected an intent that requires context (like configure or advise)
            if hasattr(intent_result, 'needs_context') and intent_result.needs_context:
                try:
                    # Dynamically inject relevant engrams as context
                    log.append(f"🔍 Intent requires context! Auto-querying Brain Engrams...")
                    from .memory_pipeline import MemoryPipeline
                    pipeline = MemoryPipeline(get_brain_path_internal())
                    # Use the raw string querying logic from memory_pipeline for best match
                    # (This is a simplified read; ideally we call pipeline.query if available)
                    active_engrams = pipeline._load_active_engrams()
                    
                    found_context = []
                    # Simple heuristic match since pipeline doesn't have a public query yet
                    req_lower = user_intent.lower()
                    for e in active_engrams:
                        key_words = e.get("key", "").lower().replace("_", " ")
                        val_words = e.get("value", "").lower()
                        
                        # Find overlapping words between intent and engram
                        intent_words = set(req_lower.split()) - {"the", "a", "an", "is", "are", "how", "what", "why"}
                        if any(w in val_words or w in key_words for w in intent_words if len(w) > 4):
                            found_context.append(f"- {e.get('key', 'unknown')}: {e.get('value', '')}")
                    
                    if found_context:
                        # Take top 5 to avoid blowing up context window
                        top_context = "\n".join(found_context[:5])
                        context_prompt = f"\n\n[SYSTEM ACQUIRED CONTEXT FROM BRAIN ENGRAMS]:\n{top_context}\nUse this context to inform your answer or configuration."
                        enforcement_prompt += context_prompt
                        log.append(f"🧠 Context Gate: Injected {len(found_context[:5])} relevant historical engrams.")
                    else:
                        log.append("🧠 Context Gate: No hyper-relevant engrams found for this intent.")
                        
                except Exception as ctx_e:
                    log.append(f"⚠️ Context injection failed: {ctx_e}")

            # Also inject learned patterns from past failures
            learned_prompt = self._pattern_learner.get_system_prompt_enhancement()
            enforcement_prompt += learned_prompt
            
            if intent_result.has_requirements():
                log.append(f"🎯 Intent: required_tools={intent_result.required_tools}")
        except Exception as e:
            log.append(f"⚠️ Intent analysis skipped: {e}")
        
        # Reset tools called tracker
        self._tools_called = []
        
        # 1. Build Base Prompt
        system_prompt = self.context.get('system_prompt', "You are an agent.")
        
        # Phase 72: Filter tools to only relevant ones (reduces cognitive load)
        all_tools = self.context.get('tools', [])
        if len(all_tools) > 25:
            filtered_tools = self._tool_recommender.filter_tools(user_intent, all_tools)
            log.append(f"🔍 Tool Discovery: {len(filtered_tools)}/{len(all_tools)} tools selected")
        else:
            filtered_tools = all_tools
        
        tools_desc = []
        for t in filtered_tools:
             tools_desc.append(f"### {t['name']}")
             tools_desc.append(f"Description: {t['description']}")
             tools_desc.append(f"Parameters: {json.dumps(t.get('parameters', {}), indent=2)}")
             tools_desc.append("")
        
        tools_block = "\n".join(tools_desc)
        
        base_prompt = f"""{system_prompt}
{enforcement_prompt}
        
AVAILABLE TOOLS:
{tools_block}

CRITICAL RULES (MDR_002):
1. You MUST call a tool to perform actions.
2. Do not just say you did it.
3. Output a JSON block with "tool" and "args" to call a tool.
   Format: 
   ```json
   {{
     "tool": "tool_name",
     "args": {{ ... }}
   }}
   ```
"""
        # 2. Multi-Turn Loop
        max_turns = 5
        turn = 0
        current_history = []
        
        while turn < max_turns:
            turn += 1
            log.append(f"\n--- Turn {turn}/{max_turns} ---")
            
            # Construct full prompt with history
            history_str = "\n\n".join(current_history)
            if history_str:
                turn_prompt = f"{base_prompt}\n\n# EXECUTION HISTORY\n{history_str}\n\nNEXT STEP:"
            else:
                turn_prompt = base_prompt

            try:
                response = self.model.generate_content(turn_prompt)
                
                # v0.6.1: Record token usage for cost tracking
                if self._agent_id:
                    # Estimate tokens (rough: 4 chars = 1 token)
                    input_tokens = len(turn_prompt) // 4
                    output_tokens = len(getattr(response, 'text', '') or '') // 4
                    self._execution_manager.record_tokens(self._agent_id, input_tokens, output_tokens)
                
                # Defensive: Handle None or malformed response
                if response is None:
                    log.append("[LLM Error]: Response is None (quota/network issue)")
                    current_history.append("SYSTEM: LLM returned no response. Retrying...")
                    continue
                
                text = getattr(response, 'text', None)
                if text is None:
                    # Try to extract from candidates
                    if hasattr(response, 'candidates') and response.candidates:
                        text = response.candidates[0].content.parts[0].text if response.candidates[0].content.parts else ""
                    else:
                        log.append("[LLM Error]: Response has no text content")
                        current_history.append("SYSTEM: LLM response malformed. Retrying...")
                        continue
                
                log.append(f"[LLM Output]: {text[:500]}...")
                current_history.append(f"AI: {text}")

                
                # 3. Parse and Execute
                import re
                match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                
                if match:
                    tool_call = json.loads(match.group(1))
                    tool_name = tool_call.get("tool")
                    args = tool_call.get("args", {})
                    
                    log.append(f">> Tool detected: {tool_name}")
                    self._tools_called.append(tool_name)
                    
                    # v0.6.0 DSoR: Emit DecisionMade BEFORE tool execution
                    decision = self._emit_decision(
                        tool_name=tool_name,
                        args=args,
                        reasoning=f"LLM requested tool call from turn {turn}",
                        current_history=current_history,
                        confidence=0.9
                    )
                    log.append(f"📋 Decision recorded: {decision.decision_id} (ctx:{decision.context_hash})")
                    
                    # v0.6.1: Record tool call for cost tracking
                    if self._agent_id:
                        self._execution_manager.record_tool_call(self._agent_id)
                    
                    result = self._execute_tool(tool_name, args)
                    log.append(f"[Tool Result]: {str(result)[:1000]}...")
                    current_history.append(f"TOOL_RESULT ({tool_name}): {result}")
                else:
                    # No tool call - check if it's the final answer
                    if self.context['persona'] == 'Synthesizer' or "MISSION_COMPLETE" in text or "FINAL_ANSWER" in text:
                         log.append("✅ Mission complete signal detected.")
                         
                         # GHOST COMPLETION FIX: Persist mission summary BEFORE returning
                         try:
                             brain_path = get_brain_path_internal()
                             import time as _time
                             timestamp = int(_time.time())
                             session_id = self.context.get('session_id', f'unknown_{timestamp}')
                             
                             mission_dir = brain_path / "swarms" / session_id
                             mission_dir.mkdir(parents=True, exist_ok=True)
                             
                             # Write summary.md
                             summary_path = mission_dir / "summary.md"
                             summary_content = f"""# Mission Summary

**Persona:** {self.context['persona']}
**Intent:** {self.context['intent']}
**Completed At:** {_time.strftime('%Y-%m-%dT%H:%M:%S')}
**Turns Used:** {turn}/{max_turns}

## Final Output

{text}

## Execution Log

```
{chr(10).join(log[-10:])}
```
"""
                             summary_path.write_text(summary_content)
                             
                             # Write mission_log.json
                             log_path = mission_dir / "mission_log.json"
                             mission_data = {
                                 "session_id": session_id,
                                 "persona": self.context['persona'],
                                 "intent": self.context['intent'],
                                 "completed_at": _time.strftime('%Y-%m-%dT%H:%M:%S'),
                                 "turns_used": turn,
                                 "max_turns": max_turns,
                                 "history": current_history[-10:],
                                 "status": "COMPLETE"
                             }
                             log_path.write_text(json.dumps(mission_data, indent=2, ensure_ascii=False))

                             log.append(f"💾 Mission persisted to {mission_dir}")
                         except Exception as persist_error:
                             log.append(f"⚠️ Persistence warning: {persist_error}")

                         # Archive pipeline: record this as a loop turn for third brother training data
                         try:
                             from .archive_pipeline import ArchivePipeline
                             archive = ArchivePipeline()
                             decisions_text = [d.reasoning for d in self._decision_ledger[-5:]]
                             archive.record_turn(
                                 brother="code",
                                 intent=self.context.get('intent', ''),
                                 actions=log[-10:],
                                 tools_used=self._tools_called,
                                 decisions=decisions_text,
                                 outcome=text[:500] if text else "Mission complete",
                                 signal_absorbed=[],
                                 signal_produced=[f"mission/{session_id}"],
                                 confidence=sum(d.confidence for d in self._decision_ledger) / max(len(self._decision_ledger), 1),
                                 context=f"Agent {self.context.get('persona', 'unknown')} turn {turn}/{max_turns}",
                             )
                             log.append("📊 Loop turn archived for training")
                         except Exception:
                             pass  # Non-blocking archive
                         
                         break
                         
                    # MDR_002: THE ACTIVE CRITIC Intervention
                    log.append("⚠️ [CRITIC INTERVENTION] No tool call detected.")
                    
                    critique_prompt = f"{turn_prompt}\n\nSYSTEM CRITIC: You did not call a tool! You MUST output a JSON tool call block or mark MISSION_COMPLETE if finished."
                    response_retry = self.model.generate_content(critique_prompt)
                    text_retry = response_retry.text
                    log.append(f"[LLM Retry Output]: {text_retry[:500]}...")
                    current_history.append(f"AI (Retry): {text_retry}")
                    
                    match_retry = re.search(r'```json\s*(\{.*?\})\s*```', text_retry, re.DOTALL)
                    if match_retry:
                        tool_call = json.loads(match_retry.group(1))
                        tool_name = tool_call.get("tool")
                        args = tool_call.get("args", {})
                        
                        log.append(f">> Tool detected (after critique): {tool_name}")
                        self._tools_called.append(tool_name)
                        
                        # v0.6.0 DSoR: Emit DecisionMade BEFORE tool execution (post-critique)
                        decision = self._emit_decision(
                            tool_name=tool_name,
                            args=args,
                            reasoning=f"LLM tool call after critic intervention, turn {turn}",
                            current_history=current_history,
                            confidence=0.75  # Lower confidence after needing correction
                        )
                        log.append(f"📋 Decision recorded: {decision.decision_id} (ctx:{decision.context_hash})")
                        
                        result = self._execute_tool(tool_name, args)
                        log.append(f"[Tool Result]: {str(result)[:1000]}...")
                        current_history.append(f"TOOL_RESULT ({tool_name}): {result}")
                    else:
                         # Bug 5 Fix: Persist findings even on tool-call failure
                         log.append("❌ Agent failed to call tool after critique.")
                         
                         # Save orphan output before terminating
                         try:
                             brain_path = get_brain_path_internal()
                             orphan_dir = brain_path / "swarms" / "orphan_outputs"
                             orphan_dir.mkdir(parents=True, exist_ok=True)
                             
                             import time as _time
                             timestamp = int(_time.time())
                             output_file = orphan_dir / f"critic_failure_{self.context['persona']}_{timestamp}.md"
                             
                             findings = f"""# Orphan Agent Output

**Persona:** {self.context['persona']}
**Intent:** {self.context['intent']}
**Timestamp:** {timestamp}

## Agent Analysis (Not Persisted via Tool)

{text_retry}

## Execution History

```
{chr(10).join(current_history[-5:])}
```
"""
                             output_file.write_text(findings)
                             log.append(f"💾 Orphan output saved to {output_file}")
                         except Exception as persist_error:
                             log.append(f"⚠️ Failed to save orphan output: {persist_error}")
                         
                         break

            except Exception as e:
                log.append(f"LLM Error: {e}")
                break
                
        return "\n".join(log)

    def _run_heuristic(self, log: List[str]) -> str:
        """Legacy Heuristic Mode - v0.6.0 DSoR: Also emits DecisionMade events"""
        log.append(">> Mode: Heuristic (Fast)")
        
        full_intent = self.context['intent'].lower()
        executed = False
        heuristic_history = [f"Intent: {self.context['intent']}"]
        
        # 1. BRAIN OPS
        if "brain" in full_intent or "task" in full_intent or "scan" in full_intent:
             # Heuristic mapping for heuristic mode
             pass 

        # 2. RENDER OPS
        if "deploy" in full_intent or "check" in full_intent or "list" in full_intent:
             if "render_list_services" in [t['name'] for t in self.context['tools']] and ("list" in full_intent or "check" in full_intent):
                 # v0.6.0 DSoR: Emit DecisionMade before heuristic tool call
                 decision = self._emit_decision(
                     tool_name="render_list_services",
                     args={},
                     reasoning="Heuristic mode: intent matched 'list' or 'check'",
                     current_history=heuristic_history,
                     confidence=0.7  # Heuristic = lower confidence
                 )
                 log.append(f"📋 Decision recorded: {decision.decision_id}")
                 
                 result = self._execute_tool("render_list_services", {})
                 log.append(">> [Heuristic] Calling render_list_services...")
                 log.append(result)
                 executed = True
             elif "render_deploy_service" in [t['name'] for t in self.context['tools']] and "deploy" in full_intent:
                 # v0.6.0 DSoR: Emit DecisionMade before heuristic tool call
                 decision = self._emit_decision(
                     tool_name="render_list_services",
                     args={},
                     reasoning="Heuristic mode: deploy intent, listing first for safety",
                     current_history=heuristic_history,
                     confidence=0.6  # Even lower - we're being cautious
                 )
                 log.append(f"📋 Decision recorded: {decision.decision_id}")
                 
                 result = self._execute_tool("render_list_services", {}) 
                 log.append(">> [Heuristic] Intent detected deploy, listing services first...")
                 log.append(result)
                 executed = True

        if not executed:
             log.append("No heuristic action map found.")
             
        log.append("--- Agent Terminated ---")
        return "\n".join(log)

    def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """
        Execute a tool with v0.6.0 DSoR security.
        Validates and consumes IPC token before execution.
        """
        # v0.6.0 DSoR: Validate and consume IPC token if present
        if self._current_ipc_token:
            try:
                ipc_manager = get_ipc_auth_manager()
                is_valid, error = ipc_manager.validate_token(
                    self._current_ipc_token.token_id,
                    scope="tool_call"
                )
                
                if is_valid:
                    # Compute request hash for audit trail
                    request_hash = hashlib.sha256(
                        json.dumps({"tool": tool_name, "args": args}, sort_keys=True).encode()
                    ).hexdigest()[:16]
                    
                    # Consume token and record metering
                    ipc_manager.consume_token(
                        self._current_ipc_token.token_id,
                        request_hash=request_hash,
                        resource_type="tool_call",
                        units=1.0,
                        metadata={"tool": tool_name}
                    )
                # Clear token after use (single-use)
                self._current_ipc_token = None
            except Exception:
                pass  # Non-blocking security layer
        
        # Find the capability that owns this tool
        caps = self.context.get('capability_instances', [])
        for cap in caps:
            tools = [t['name'] for t in cap.get_tools()]
            if tool_name in tools:
                return cap.execute_tool(tool_name, args)
        
        return f"Error: Tool {tool_name} implementation not found."
