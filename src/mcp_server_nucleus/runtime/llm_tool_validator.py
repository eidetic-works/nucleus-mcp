"""
LLM-Based Tool Call Validator
==============================
Phase 71: Tool Calling Enforcement Layer

Uses LLM to validate whether an agent actually called the required tools.
This is the "post-flight check" after agent execution.

Catches the common failure: Agent says "I did it" but didn't call any tool.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("nucleus.tool_validator")

DEFAULT_VALIDATION_MODEL = "gemini-2.0-flash-exp"

# Phase 73: Resilience imports (lazy)
def _get_resilient_client():
    from .llm_resilience import get_resilient_llm_client
    return get_resilient_llm_client()

def _get_telemetry():
    from .error_telemetry import get_error_telemetry
    return get_error_telemetry()

VALIDATION_PROMPT = """You are a tool call validator for the Nucleus AI Agent OS.

An agent was given a request and a set of REQUIRED tools to call. Your job is to check if the agent actually called them.

USER REQUEST:
"{user_request}"

REQUIRED TOOLS (must be called):
{required_tools}

TOOLS ACTUALLY CALLED BY AGENT:
{tools_called}

AGENT'S RESPONSE:
"{agent_response}"

Did the agent call all required tools? Analyze carefully:
- If the agent claims to have done something but didn't call the corresponding tool, that's a FAILURE
- If no tools were required and none were called, that's a PASS
- If the agent called the required tools, that's a PASS

Respond with ONLY valid JSON (no markdown, no explanation):
{{"validation_passed": true, "missing_tools": [], "hallucinated_actions": [], "reasoning": "brief explanation"}}

Set hallucinated_actions to any actions the agent CLAIMED to do but didn't actually call a tool for.
"""


class ValidationResult:
    """Result of tool call validation."""
    
    def __init__(self, passed: bool, missing_tools: List[str],
                 hallucinated_actions: List[str], reasoning: str,
                 raw_response: str = ""):
        self.passed = passed
        self.missing_tools = missing_tools
        self.hallucinated_actions = hallucinated_actions
        self.reasoning = reasoning
        self.raw_response = raw_response
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_passed": self.passed,
            "missing_tools": self.missing_tools,
            "hallucinated_actions": self.hallucinated_actions,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }


class LLMToolValidator:
    """
    Uses LLM to validate if an agent called the required tools.
    
    Post-flight check that catches:
    - Agent claiming to do something without calling a tool
    - Agent skipping required tools
    - Agent hallucinating actions
    """
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv(
            "NUCLEUS_VALIDATOR_MODEL", DEFAULT_VALIDATION_MODEL
        )
        self._client = None
        self._use_resilient = True  # Phase 73
    
    def _get_client(self):
        """Lazy-init LLM client."""
        if self._client is not None:
            return self._client
        
        try:
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self._client = genai.Client(api_key=api_key)
            else:
                project_id = os.environ.get("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
                if not project_id:
                    raise ValueError("GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT is required for Vertex AI mode.")
                self._client = genai.Client(vertexai=True, project=project_id, location="us-central1")
            return self._client
        except Exception as e:
            logger.warning(f"Failed to init genai client for validator: {e}")
            return None
    
    def validate(self, user_request: str, required_tools: List[str],
                 tools_called: List[str], agent_response: str) -> ValidationResult:
        """
        Validate if agent called required tools.
        
        Args:
            user_request: Original user request
            required_tools: Tools that should have been called
            tools_called: Tools that were actually called
            agent_response: Agent's text response
            
        Returns:
            ValidationResult
        """
        # Short-circuit: no requirements means auto-pass
        if not required_tools:
            return ValidationResult(
                passed=True,
                missing_tools=[],
                hallucinated_actions=[],
                reasoning="No tools required for this request"
            )
        
        # Quick deterministic check first (no LLM needed)
        missing = [t for t in required_tools if t not in tools_called]
        if not missing:
            return ValidationResult(
                passed=True,
                missing_tools=[],
                hallucinated_actions=[],
                reasoning="All required tools were called"
            )
        
        # If there are missing tools, use LLM for nuanced analysis
        # (maybe the request changed mid-execution, or agent used alternative)
        prompt = VALIDATION_PROMPT.format(
            user_request=user_request,
            required_tools=json.dumps(required_tools),
            tools_called=json.dumps(tools_called) if tools_called else "[]  (NO TOOLS WERE CALLED)",
            agent_response=agent_response[:1000]  # Truncate
        )
        
        # Phase 73: Deterministic fallback function
        def _deterministic_fallback(p):
            return {
                "validation_passed": False,
                "missing_tools": missing,
                "hallucinated_actions": [],
                "reasoning": f"Deterministic fallback: missing {missing}"
            }
        
        try:
            if self._use_resilient:
                resilient = _get_resilient_client()
                result = resilient.generate_json(
                    prompt,
                    model_override=self.model_name,
                    fallback_fn=_deterministic_fallback
                )
                if result is None:
                    result = _deterministic_fallback(prompt)
            else:
                client = self._get_client()
                if client is None:
                    return ValidationResult(
                        passed=False, missing_tools=missing,
                        hallucinated_actions=[],
                        reasoning=f"Deterministic check: missing {missing}"
                    )
                response = client.models.generate_content(
                    model=self.model_name, contents=prompt
                )
                text = getattr(response, 'text', '') or ''
                json_text = text.strip()
                if json_text.startswith("```"):
                    lines = json_text.split("\n")
                    json_lines = [l for l in lines if not l.strip().startswith("```")]
                    json_text = "\n".join(json_lines).strip()
                result = json.loads(json_text)
            
            return ValidationResult(
                passed=result.get("validation_passed", False),
                missing_tools=result.get("missing_tools", missing),
                hallucinated_actions=result.get("hallucinated_actions", []),
                reasoning=result.get("reasoning", ""),
                raw_response=str(result)
            )
            
        except Exception as e:
            _get_telemetry().record_error("E601", f"Validation: {e}", "llm_tool_validator", exception=e)
            return ValidationResult(
                passed=False,
                missing_tools=missing,
                hallucinated_actions=[],
                reasoning=f"Validation error, deterministic fallback: missing {missing}"
            )
    
    def validate_deterministic(self, required_tools: List[str], 
                                tools_called: List[str]) -> ValidationResult:
        """
        Pure deterministic validation - no LLM call.
        Faster but less nuanced.
        """
        missing = [t for t in required_tools if t not in tools_called]
        return ValidationResult(
            passed=len(missing) == 0,
            missing_tools=missing,
            hallucinated_actions=[],
            reasoning="Deterministic check" if not missing else f"Missing: {missing}"
        )


# Singleton
_validator_instance: Optional[LLMToolValidator] = None

def get_tool_validator() -> LLMToolValidator:
    """Get singleton tool validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = LLMToolValidator()
    return _validator_instance
