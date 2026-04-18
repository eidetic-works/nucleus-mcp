"""
LLM-Based Tool Call Enforcer
==============================
Phase 71: Tool Calling Enforcement Layer

Orchestrates the full enforcement flow:
1. Pre-flight: Analyze intent → determine required tools
2. Execution: Run agent with enhanced system prompt
3. Post-flight: Validate tool calls
4. Retry: If validation fails, retry with stronger enforcement
5. Learn: Record failures for pattern learning

This is the core mechanism that brings Nucleus tools to life.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path

from .llm_intent_analyzer import LLMIntentAnalyzer, IntentAnalysisResult, get_intent_analyzer
from .llm_tool_validator import LLMToolValidator, ValidationResult, get_tool_validator

logger = logging.getLogger("nucleus.tool_enforcer")

# Phase 73: Resilience imports (lazy)
def _get_file_ops():
    from .file_resilience import get_resilient_file_ops
    return get_resilient_file_ops()

def _get_telemetry():
    from .error_telemetry import get_error_telemetry
    return get_error_telemetry()


class EnforcementResult:
    """Result of an enforced agent execution."""
    
    def __init__(self, success: bool, tools_required: List[str],
                 tools_called: List[str], attempts: int,
                 validation: Optional[ValidationResult] = None,
                 intent_analysis: Optional[IntentAnalysisResult] = None,
                 enforcement_prompt: str = ""):
        self.success = success
        self.tools_required = tools_required
        self.tools_called = tools_called
        self.attempts = attempts
        self.validation = validation
        self.intent_analysis = intent_analysis
        self.enforcement_prompt = enforcement_prompt
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tools_required": self.tools_required,
            "tools_called": self.tools_called,
            "attempts": self.attempts,
            "validation": self.validation.to_dict() if self.validation else None,
            "intent_analysis": self.intent_analysis.to_dict() if self.intent_analysis else None,
            "timestamp": self.timestamp
        }


class LLMToolEnforcer:
    """
    Orchestrates tool calling enforcement using LLM-based analysis.
    
    Flow:
    1. Analyze intent (LLM determines required tools)
    2. Generate enforcement prompt (tell agent which tools to call)
    3. After execution, validate tool calls
    4. If validation fails, provide retry guidance
    5. Record outcomes for pattern learning
    
    This does NOT execute the agent itself - it provides:
    - Pre-execution: system prompt enhancement
    - Post-execution: validation and retry guidance
    """
    
    def __init__(self, max_retries: int = 2):
        self.analyzer = get_intent_analyzer()
        self.validator = get_tool_validator()
        self.max_retries = max_retries
        self._failure_log: List[Dict[str, Any]] = []
        self._success_count = 0
        self._failure_count = 0
        self._enforcement_log_path = Path(
            os.getenv("NUCLEAR_BRAIN_PATH", "./.brain")
        ) / "metrics" / "tool_enforcement.jsonl"
    
    def pre_flight(self, user_request: str, 
                   available_tools: List[Dict[str, Any]]) -> IntentAnalysisResult:
        """
        Pre-flight check: Analyze user request to determine required tools.
        
        Call this BEFORE agent execution to get the enforcement prompt.
        
        Args:
            user_request: The user's request
            available_tools: Available MCP tools
            
        Returns:
            IntentAnalysisResult with required tools
        """
        return self.analyzer.analyze(user_request, available_tools)
    
    def generate_enforcement_prompt(self, intent: IntentAnalysisResult) -> str:
        """
        Generate system prompt enhancement that tells the agent which tools to call.
        
        This prompt is injected into the agent's system prompt before execution.
        """
        if not intent.has_requirements():
            return ""
        
        tools_list = ", ".join(intent.required_tools)
        
        return f"""
TOOL CALLING ENFORCEMENT (Nucleus OS):
You MUST call these tools to fulfill the user's request: {tools_list}
Do NOT just say you did something - you MUST actually call the tool.
If you claim to perform an action without calling the corresponding tool, your response will be REJECTED and you will be asked to retry.
Reasoning: {intent.reasoning}
"""
    
    def generate_retry_prompt(self, validation: ValidationResult, attempt: int) -> str:
        """
        Generate a stronger enforcement prompt after a validation failure.
        
        Each retry gets progressively more forceful.
        """
        missing = ", ".join(validation.missing_tools)
        
        if attempt == 1:
            return f"""
CRITICAL - TOOL CALL ENFORCEMENT (Attempt 2):
Your previous response was REJECTED because you did NOT call required tools.
Missing tools: {missing}
You MUST call these tools NOW. Do not just say you did it.
Output a JSON tool call block for each required tool.
"""
        else:
            return f"""
FINAL WARNING - TOOL CALL ENFORCEMENT (Attempt {attempt + 1}):
This is your LAST chance. You have repeatedly failed to call required tools.
MISSING: {missing}
You MUST output a JSON tool call block. Example:
```json
{{"tool": "{validation.missing_tools[0] if validation.missing_tools else 'tool_name'}", "args": {{}}}}
```
DO IT NOW.
"""
    
    def post_flight(self, user_request: str, required_tools: List[str],
                    tools_called: List[str], agent_response: str) -> ValidationResult:
        """
        Post-flight check: Validate that required tools were called.
        
        Call this AFTER agent execution.
        
        Args:
            user_request: Original request
            required_tools: Tools that should have been called
            tools_called: Tools that were actually called
            agent_response: Agent's text response
            
        Returns:
            ValidationResult
        """
        return self.validator.validate(
            user_request, required_tools, tools_called, agent_response
        )
    
    def record_outcome(self, user_request: str, intent: IntentAnalysisResult,
                       tools_called: List[str], success: bool, attempts: int):
        """
        Record execution outcome for pattern learning.
        
        Args:
            user_request: Original request
            intent: Intent analysis result
            tools_called: Tools that were called
            success: Whether enforcement succeeded
            attempts: Number of attempts needed
        """
        outcome = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_request": user_request[:200],
            "required_tools": intent.required_tools,
            "tools_called": tools_called,
            "success": success,
            "attempts": attempts,
            "reasoning": intent.reasoning
        }
        
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1
            self._failure_log.append(outcome)
        
        # Phase 73: Persist with resilient file ops
        try:
            _get_file_ops().append_jsonl(self._enforcement_log_path, outcome)
        except Exception as e:
            try:
                _get_telemetry().record_error("E200", f"Enforcement log write: {e}", "llm_tool_enforcer")
            except Exception:
                pass
            logger.warning(f"Failed to persist enforcement outcome: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enforcement statistics."""
        total = self._success_count + self._failure_count
        return {
            "total_enforcements": total,
            "successes": self._success_count,
            "failures": self._failure_count,
            "success_rate": self._success_count / total if total > 0 else 0.0,
            "recent_failures": len(self._failure_log),
            "log_path": str(self._enforcement_log_path)
        }
    
    def get_failure_log(self) -> List[Dict[str, Any]]:
        """Get recent failure log for pattern learning."""
        return self._failure_log[-20:]  # Last 20 failures


# Singleton
_enforcer_instance: Optional[LLMToolEnforcer] = None

def get_tool_enforcer() -> LLMToolEnforcer:
    """Get singleton tool enforcer instance."""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = LLMToolEnforcer()
    return _enforcer_instance
