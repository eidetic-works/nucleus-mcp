"""
LLM-Based Intent Analyzer
==========================
Phase 71: Tool Calling Enforcement Layer

Uses LLM to detect which MCP tools are required for a given user request.
No vector DB, no graph DB, no regex - just LLM understanding intent.

This is the "pre-flight check" before agent execution.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("nucleus.intent_analyzer")

# Default model for intent analysis (fast + cheap)
DEFAULT_ANALYSIS_MODEL = "gemini-2.0-flash-exp"

# Phase 73: Resilience imports (lazy to avoid circular)
def _get_resilient_client():
    from .llm_resilience import get_resilient_llm_client
    return get_resilient_llm_client()

def _get_telemetry():
    from .error_telemetry import get_error_telemetry
    return get_error_telemetry()

INTENT_ANALYSIS_PROMPT = """You are an intent analyzer for the Nucleus AI Agent OS.

Given a user request and a list of available MCP tools, determine which tools MUST be called to fulfill the request.

RULES:
1. Only include tools that are REQUIRED (not optional nice-to-haves)
2. If the request is purely conversational (e.g. "hello", "thanks"), return empty required_tools
3. If the request involves creating/adding something, the corresponding create/add tool is REQUIRED
4. If the request involves reading/listing something, the corresponding list/get tool is REQUIRED
5. If the request involves handoff, giving control to another agent, or handing over to Opus, `brain_generate_handoff_summary` and `brain_checkpoint_task` are REQUIRED.
6. Be conservative - only mark as required if the request CANNOT be fulfilled without calling the tool

USER REQUEST:
"{user_request}"

AVAILABLE TOOLS:
{tool_descriptions}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"required_tools": ["tool_name1"], "optional_tools": ["tool_name2"], "reasoning": "brief explanation", "needs_context": true}}
"""


class IntentAnalysisResult:
    """Result of LLM-based intent analysis."""
    
    def __init__(self, required_tools: List[str], optional_tools: List[str], 
                 reasoning: str, needs_context: bool = False, raw_response: str = ""):
        self.required_tools = required_tools
        self.optional_tools = optional_tools
        self.reasoning = reasoning
        self.needs_context = needs_context
        self.raw_response = raw_response
    
    def has_requirements(self) -> bool:
        """Whether any tools are required."""
        return len(self.required_tools) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_tools": self.required_tools,
            "optional_tools": self.optional_tools,
            "reasoning": self.reasoning,
            "needs_context": self.needs_context
        }


class LLMIntentAnalyzer:
    """
    Uses LLM to detect which tools are required for a user request.
    
    This replaces traditional intent detection (regex, vector DB, graph DB)
    with a simple LLM call using a fast/cheap model.
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv(
            "NUCLEUS_INTENT_MODEL", DEFAULT_ANALYSIS_MODEL
        )
        self._client = None
        self._engine = None
        self._use_resilient = True  # Phase 73: Use resilient client by default
    
    def _get_client(self):
        """Lazy-init LLM client."""
        if self._client is not None:
            return self._client, self._engine
        
        # Try google-genai first
        try:
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self._client = genai.Client(api_key=api_key)
                self._engine = "api_key"
            else:
                # Try Vertex AI
                project_id = os.environ.get(
                    "GCP_PROJECT_ID", 
                    os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0894185576")
                )
                self._client = genai.Client(vertexai=True, project=project_id, location="us-central1")
                self._engine = "vertex"
            return self._client, self._engine
        except Exception as e:
            logger.warning(f"Failed to init genai client: {e}")
            return None, None
    
    def _build_tool_descriptions(self, tools: List[Dict[str, Any]], max_tools: int = 50) -> str:
        """Build concise tool descriptions for the prompt."""
        descriptions = []
        for t in tools[:max_tools]:
            name = t.get("name", "unknown")
            desc = t.get("description", "No description")
            # Truncate long descriptions
            if len(desc) > 120:
                desc = desc[:117] + "..."
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)
    
    def analyze(self, user_request: str, available_tools: List[Dict[str, Any]]) -> IntentAnalysisResult:
        """
        Analyze user request to determine required tools.
        
        Args:
            user_request: The user's request text
            available_tools: List of available MCP tool definitions
            
        Returns:
            IntentAnalysisResult with required and optional tools
        """
        # Short-circuit for empty requests
        if not user_request or not user_request.strip():
            return IntentAnalysisResult([], [], "Empty request")
        
        # Short-circuit if no tools available
        if not available_tools:
            return IntentAnalysisResult([], [], "No tools available")
        
        tool_descriptions = self._build_tool_descriptions(available_tools)
        valid_names = {t["name"] for t in available_tools}
        
        prompt = INTENT_ANALYSIS_PROMPT.format(
            user_request=user_request,
            tool_descriptions=tool_descriptions
        )
        
        # Phase 73: Use resilient client with fallback chain
        def _fallback_fn(p):
            """Deterministic fallback when LLM unavailable."""
            fb = self.analyze_without_llm(user_request, available_tools)
            return json.dumps(fb.to_dict())
        
        try:
            if self._use_resilient:
                resilient = _get_resilient_client()
                result_dict = resilient.generate_json(
                    prompt,
                    model_override=self.model_name,
                    fallback_fn=lambda p: self.analyze_without_llm(user_request, available_tools).to_dict()
                )
                if result_dict is None:
                    # Full fallback
                    return self.analyze_without_llm(user_request, available_tools)
            else:
                # Legacy path
                client, engine = self._get_client()
                if client is None:
                    return self.analyze_without_llm(user_request, available_tools)
                response = client.models.generate_content(
                    model=self.model_name, contents=prompt
                )
                text = getattr(response, 'text', '') or ''
                json_text = text.strip()
                if json_text.startswith("```"):
                    lines = json_text.split("\n")
                    json_lines = [l for l in lines if not l.strip().startswith("```")]
                    json_text = "\n".join(json_lines).strip()
                result_dict = json.loads(json_text)
            
            required = result_dict.get("required_tools", [])
            optional = result_dict.get("optional_tools", [])
            reasoning = result_dict.get("reasoning", "")
            needs_context = result_dict.get("needs_context", False)
            
            # Validate tool names exist in available tools
            required = [t for t in required if t in valid_names]
            optional = [t for t in optional if t in valid_names]
            
            # Heuristic for needs_context if LLM missed it or request sounds like it
            req_lower = user_request.lower()
            if not needs_context and any(w in req_lower for w in ["advise", "configure", "how did we", "context", "history", "previous", "earlier", "why did we"]):
                needs_context = True
                logger.info(f"Intent analysis: Auto-enabled needs_context based on heuristic for '{user_request[:50]}'")
            
            logger.info(f"Intent analysis: required={required}, optional={optional}, needs_context={needs_context}")
            
            return IntentAnalysisResult(
                required_tools=required,
                optional_tools=optional,
                reasoning=reasoning,
                needs_context=needs_context,
                raw_response=str(result_dict)
            )
            
        except json.JSONDecodeError as e:
            _get_telemetry().record_error("E105", f"Intent JSON parse: {e}", "llm_intent_analyzer")
            return self.analyze_without_llm(user_request, available_tools)
        except Exception as e:
            _get_telemetry().record_error("E600", f"Intent analysis: {e}", "llm_intent_analyzer", exception=e)
            return self.analyze_without_llm(user_request, available_tools)
    
    def analyze_without_llm(self, user_request: str, available_tools: List[Dict[str, Any]]) -> IntentAnalysisResult:
        """
        Fallback: Simple keyword-based intent analysis when LLM is unavailable.
        Uses basic heuristics - not as good as LLM but better than nothing.
        """
        request_lower = user_request.lower()
        required = []
        optional = []
        
        tool_names = {t["name"]: t for t in available_tools}
        
        # Simple keyword matching (facade-aware)
        # Multi-word keywords are checked first via iteration order;
        # longer phrases should appear before shorter substrings.
        keyword_map = {
            # ── Tasks (16 actions) ──
            "add task": ["nucleus_tasks"],
            "list task": ["nucleus_tasks"],
            "import jsonl": ["nucleus_tasks"],
            "import task": ["nucleus_tasks"],
            "context switch": ["nucleus_tasks"],
            "depth push": ["nucleus_tasks"],
            "depth pop": ["nucleus_tasks"],
            "depth map": ["nucleus_tasks"],
            "next task": ["nucleus_tasks"],
            "claim task": ["nucleus_tasks"],
            "escalate": ["nucleus_tasks"],
            "task": ["nucleus_tasks"],
            "depth": ["nucleus_tasks"],
            "backlog": ["nucleus_tasks"],
            # ── Engrams / Memory (25 actions) ──
            "write engram": ["nucleus_engrams"],
            "query engram": ["nucleus_engrams"],
            "search engram": ["nucleus_engrams"],
            "morning brief": ["nucleus_engrams"],
            "end of day": ["nucleus_engrams"],
            "weekly consolidat": ["nucleus_engrams"],
            "compounding status": ["nucleus_engrams"],
            "hook metric": ["nucleus_engrams"],
            "session inject": ["nucleus_engrams"],
            "export schema": ["nucleus_engrams"],
            "performance metric": ["nucleus_engrams"],
            "prometheus metric": ["nucleus_engrams"],
            "metering summary": ["nucleus_engrams"],
            "ipc token": ["nucleus_engrams"],
            "dsor status": ["nucleus_engrams"],
            "federation dsor": ["nucleus_engrams"],
            "routing decision": ["nucleus_engrams"],
            "list decision": ["nucleus_engrams"],
            "list snapshot": ["nucleus_engrams"],
            "list tool": ["nucleus_engrams"],
            "tier status": ["nucleus_engrams"],
            "engram": ["nucleus_engrams"],
            "health": ["nucleus_engrams"],
            "brain": ["nucleus_engrams"],
            "memory": ["nucleus_engrams"],
            "version": ["nucleus_engrams"],
            # ── Sessions (16 actions) ──
            "resume checkpoint": ["nucleus_sessions"],
            "handoff summary": ["nucleus_sessions"],
            "archive resolved": ["nucleus_sessions"],
            "propose merge": ["nucleus_sessions"],
            "garbage collect": ["nucleus_sessions"],
            "emit event": ["nucleus_sessions"],
            "read event": ["nucleus_sessions"],
            "get state": ["nucleus_sessions"],
            "update state": ["nucleus_sessions"],
            "save session": ["nucleus_sessions"],
            "end session": ["nucleus_sessions"],
            "start session": ["nucleus_sessions"],
            "check recent": ["nucleus_sessions"],
            "checkpoint": ["nucleus_sessions"],
            "hand over": ["nucleus_sessions"],
            "handoff": ["nucleus_sessions"],
            "pass this": ["nucleus_sessions"],
            "give to": ["nucleus_sessions"],
            "session": ["nucleus_sessions"],
            "event": ["nucleus_sessions"],
            # ── Infra (10 actions) ──
            "smoke test": ["nucleus_infra"],
            "file change": ["nucleus_infra"],
            "gcloud status": ["nucleus_infra"],
            "gcloud service": ["nucleus_infra"],
            "list service": ["nucleus_infra"],
            "scan marketing": ["nucleus_infra"],
            "synthesize strategy": ["nucleus_infra"],
            "status report": ["nucleus_infra"],
            "optimize workflow": ["nucleus_infra"],
            "manage strategy": ["nucleus_infra"],
            "update roadmap": ["nucleus_infra"],
            "deploy": ["nucleus_infra"],
            "ship": ["nucleus_infra"],
            "infrastructure": ["nucleus_infra"],
            "gcloud": ["nucleus_infra"],
            "roadmap": ["nucleus_infra"],
            "marketing": ["nucleus_infra"],
            "strategy": ["nucleus_infra"],
            "workflow": ["nucleus_infra"],
            # ── Telemetry (14 actions) ──
            "value ratio": ["nucleus_telemetry"],
            "kill switch": ["nucleus_telemetry"],
            "llm tier": ["nucleus_telemetry"],
            "llm status": ["nucleus_telemetry"],
            "record interaction": ["nucleus_telemetry"],
            "pause notification": ["nucleus_telemetry"],
            "resume notification": ["nucleus_telemetry"],
            "record feedback": ["nucleus_telemetry"],
            "high impact": ["nucleus_telemetry"],
            "check protocol": ["nucleus_telemetry"],
            "request handoff": ["nucleus_telemetry"],
            "get handoff": ["nucleus_telemetry"],
            "cost dashboard": ["nucleus_telemetry"],
            "dispatch metric": ["nucleus_telemetry"],
            "budget": ["nucleus_telemetry"],
            "telemetry": ["nucleus_telemetry"],
            "cost": ["nucleus_telemetry"],
            "notification": ["nucleus_telemetry"],
            # ── Agents (20 actions) ──
            "spawn agent": ["nucleus_agents"],
            "apply critique": ["nucleus_agents"],
            "orchestrate swarm": ["nucleus_agents"],
            "search memory": ["nucleus_agents"],
            "read memory": ["nucleus_agents"],
            "respond to consent": ["nucleus_agents"],
            "pending consent": ["nucleus_agents"],
            "critique code": ["nucleus_agents"],
            "fix code": ["nucleus_agents"],
            "session briefing": ["nucleus_agents"],
            "register session": ["nucleus_agents"],
            "handoff task": ["nucleus_agents"],
            "ingest task": ["nucleus_agents"],
            "rollback ingestion": ["nucleus_agents"],
            "ingestion stat": ["nucleus_agents"],
            "snapshot dashboard": ["nucleus_agents"],
            "list dashboard": ["nucleus_agents"],
            "get alert": ["nucleus_agents"],
            "set alert": ["nucleus_agents"],
            "alert threshold": ["nucleus_agents"],
            "code": ["nucleus_agents"],
            "critique": ["nucleus_agents"],
            "swarm": ["nucleus_agents"],
            "dashboard": ["nucleus_agents"],
            "spawn": ["nucleus_agents"],
            "ingest": ["nucleus_agents"],
            "alert": ["nucleus_agents"],
            # ── Governance (10 actions) ──
            "auto fix": ["nucleus_governance"],
            "auto_fix": ["nucleus_governance"],
            "delete file": ["nucleus_governance"],
            "list directory": ["nucleus_governance"],
            "set mode": ["nucleus_governance"],
            "pip install": ["nucleus_governance"],
            "status": ["nucleus_governance"],
            "lock": ["nucleus_governance"],
            "unlock": ["nucleus_governance"],
            "audit": ["nucleus_governance"],
            "governance": ["nucleus_governance"],
            "watch": ["nucleus_governance"],
            "curl": ["nucleus_governance"],
            # ── Sync (15 actions) ──
            "identify agent": ["nucleus_sync"],
            "sync status": ["nucleus_sync"],
            "sync now": ["nucleus_sync"],
            "sync auto": ["nucleus_sync"],
            "sync resolve": ["nucleus_sync"],
            "read artifact": ["nucleus_sync"],
            "write artifact": ["nucleus_sync"],
            "list artifact": ["nucleus_sync"],
            "trigger agent": ["nucleus_sync"],
            "get trigger": ["nucleus_sync"],
            "evaluate trigger": ["nucleus_sync"],
            "deploy poll": ["nucleus_sync"],
            "check deploy": ["nucleus_sync"],
            "complete deploy": ["nucleus_sync"],
            "sync": ["nucleus_sync"],
            "artifact": ["nucleus_sync"],
            "trigger": ["nucleus_sync"],
            # ── Features (16 actions) ──
            "mount server": ["nucleus_features"],
            "unmount server": ["nucleus_features"],
            "list mounted": ["nucleus_features"],
            "discover tool": ["nucleus_features"],
            "invoke tool": ["nucleus_features"],
            "traverse mount": ["nucleus_features"],
            "generate proof": ["nucleus_features"],
            "get proof": ["nucleus_features"],
            "list proof": ["nucleus_features"],
            "thanos snap": ["nucleus_features"],
            "validate feature": ["nucleus_features"],
            "feature": ["nucleus_features"],
            "proof": ["nucleus_features"],
            "mount": ["nucleus_features"],
            # ── Federation (7 actions) ──
            "join federation": ["nucleus_federation"],
            "leave federation": ["nucleus_federation"],
            "federation peer": ["nucleus_federation"],
            "federation health": ["nucleus_federation"],
            "federation": ["nucleus_federation"],
            "peer": ["nucleus_federation"],
            # ── Orchestration (12 actions) ──
            "scan commitment": ["nucleus_orchestration"],
            "archive stale": ["nucleus_orchestration"],
            "list commitment": ["nucleus_orchestration"],
            "close commitment": ["nucleus_orchestration"],
            "commitment health": ["nucleus_orchestration"],
            "open loop": ["nucleus_orchestration"],
            "add loop": ["nucleus_orchestration"],
            "weekly challenge": ["nucleus_orchestration"],
            "orchestrate": ["nucleus_orchestration"],
            "orchestration": ["nucleus_orchestration"],
            "satellite": ["nucleus_orchestration"],
            "commitment": ["nucleus_orchestration"],
            "loop": ["nucleus_orchestration"],
            "pattern": ["nucleus_orchestration"],
            "metric": ["nucleus_orchestration"],
            # ── Slots (11 actions) ──
            "slot complete": ["nucleus_slots"],
            "slot exhaust": ["nucleus_slots"],
            "status dashboard": ["nucleus_slots"],
            "autopilot sprint": ["nucleus_slots"],
            "force assign": ["nucleus_slots"],
            "start mission": ["nucleus_slots"],
            "mission status": ["nucleus_slots"],
            "halt sprint": ["nucleus_slots"],
            "resume sprint": ["nucleus_slots"],
            "sprint": ["nucleus_slots"],
            "mission": ["nucleus_slots"],
            "slot": ["nucleus_slots"],
            "autopilot": ["nucleus_slots"],
            # ── God Combos + Context Graph + Billing (Phase 3) ──
            "pulse and polish": ["nucleus_engrams"],
            "self healing": ["nucleus_engrams"],
            "fusion reactor": ["nucleus_engrams"],
            "god combo": ["nucleus_engrams"],
            "context graph": ["nucleus_engrams"],
            "engram neighbor": ["nucleus_engrams"],
            "render graph": ["nucleus_engrams"],
            "ascii graph": ["nucleus_engrams"],
            "billing summary": ["nucleus_engrams"],
            "billing": ["nucleus_engrams"],
            "usage cost": ["nucleus_engrams"],
            "graph": ["nucleus_engrams"],
            "combo": ["nucleus_engrams"],
            "pipeline": ["nucleus_engrams"],
            "diagnos": ["nucleus_engrams"],
            "visualization": ["nucleus_engrams"],
        }
        
        for keyword, tools in keyword_map.items():
            if keyword in request_lower:
                for tool in tools:
                    if tool in tool_names and tool not in required:
                        required.append(tool)
        
        needs_context = any(w in request_lower for w in ["advise", "configure", "how did we", "context", "history", "previous", "earlier", "why did we"])

        return IntentAnalysisResult(
            required_tools=required,
            optional_tools=optional,
            reasoning="Keyword-based fallback analysis",
            needs_context=needs_context
        )


# Singleton
_analyzer_instance: Optional[LLMIntentAnalyzer] = None

def get_intent_analyzer() -> LLMIntentAnalyzer:
    """Get singleton intent analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = LLMIntentAnalyzer()
    return _analyzer_instance
