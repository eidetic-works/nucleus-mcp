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
from .ipc_auth import get_ipc_auth_manager, IPCToken

# Gemini types imported dynamically or duck-typed via DualEngineLLM

def get_brain_path_internal() -> Path:
    """Helper to get brain path inside runtime"""
    return Path(os.getenv("NUCLEAR_BRAIN_PATH", "/Users/lokeshgarg/ai-mvp-backend/.brain"))

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
    def __init__(self, context: Dict[str, Any], model: Any = None):
        self.context = context
        self.model = model
        self.history: List[str] = []
        self.active = True
        self._decision_ledger: List[DecisionMade] = []  # v0.6.0: Track all decisions
        self._current_ipc_token: IPCToken = None  # v0.6.0: Current IPC token for tool calls
        self._context_manager = get_context_manager()  # v0.6.0: For state verification
    
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
            with open(decisions_file, "a") as f:
                f.write(json.dumps(decision.to_dict()) + "\n")
        except Exception:
            pass  # Non-blocking persistence
        
        return decision

    async def run(self) -> str:
        """
        Execute the agent loop.
        Returns execution log.
        v0.6.0 DSoR: Takes before/after snapshots for state verification.
        """
        # MDR_010: Auto-record telemetry
        try:
             brain_path = get_brain_path_internal()
             commitment_ledger.record_interaction(brain_path)
        except Exception:
             pass 

        log = []
        log.append(f"--- Spawning Ephemeral Agent ({self.context['persona']}) ---")
        log.append(f"Intent: {self.context['intent']}")
        
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
        
        return result

    async def _run_llm(self, log: List[str]) -> str:
        """
        MDR_005 / MDR_002: Real LLM Execution Loop with Critic & Multi-Turn Support
        """
        log.append(">> Mode: LLM (Smart)")
        
        # 1. Build Base Prompt
        system_prompt = self.context.get('system_prompt', "You are an agent.")
        
        tools_desc = []
        for t in self.context['tools']:
             tools_desc.append(f"### {t['name']}")
             tools_desc.append(f"Description: {t['description']}")
             tools_desc.append(f"Parameters: {json.dumps(t.get('parameters', {}), indent=2)}")
             tools_desc.append("")
        
        tools_block = "\n".join(tools_desc)
        
        base_prompt = f"""{system_prompt}
        
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
                    
                    # v0.6.0 DSoR: Emit DecisionMade BEFORE tool execution
                    decision = self._emit_decision(
                        tool_name=tool_name,
                        args=args,
                        reasoning=f"LLM requested tool call from turn {turn}",
                        current_history=current_history,
                        confidence=0.9
                    )
                    log.append(f"📋 Decision recorded: {decision.decision_id} (ctx:{decision.context_hash})")
                    
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
                             log_path.write_text(json.dumps(mission_data, indent=2))
                             
                             log.append(f"💾 Mission persisted to {mission_dir}")
                         except Exception as persist_error:
                             log.append(f"⚠️ Persistence warning: {persist_error}")
                         
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
