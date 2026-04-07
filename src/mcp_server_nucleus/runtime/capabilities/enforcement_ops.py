"""
Enforcement Operations Capability - MCP Tools for Tool Calling Enforcement
===========================================================================
Phase 71: Tool Calling Enforcement Layer

Provides MCP tools for monitoring and managing tool calling enforcement.
"""

from typing import Dict, Any, List
from .base import Capability
from ..llm_tool_enforcer import get_tool_enforcer
try:
    from ..llm_pattern_learner import get_pattern_learner
except ImportError:
    get_pattern_learner = None
from ..llm_intent_analyzer import get_intent_analyzer


class EnforcementOps(Capability):
    """
    MCP tools for tool calling enforcement monitoring.
    
    Tools:
    - brain_enforcement_stats: Get enforcement statistics
    - brain_enforcement_patterns: Get learned patterns from failures
    - brain_enforcement_analyze: Trigger pattern learning from recent failures
    - brain_enforcement_test: Test intent analysis on a sample request
    """
    
    @property
    def name(self) -> str:
        return "enforcement_ops"
    
    @property
    def description(self) -> str:
        return "Tool calling enforcement monitoring and pattern learning"
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_enforcement_stats",
                "description": "Get tool calling enforcement statistics (success rate, failures, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_enforcement_patterns",
                "description": "Get learned patterns from tool calling failures",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_enforcement_analyze",
                "description": "Trigger pattern learning from recent tool calling failures",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_enforcement_test",
                "description": "Test intent analysis on a sample request to see which tools would be required",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": "Sample user request to analyze"
                        }
                    },
                    "required": ["request"]
                }
            }
        ]
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "brain_enforcement_stats":
            return self._get_stats()
        elif tool_name == "brain_enforcement_patterns":
            return self._get_patterns()
        elif tool_name == "brain_enforcement_analyze":
            return self._analyze()
        elif tool_name == "brain_enforcement_test":
            return self._test_intent(args.get("request", ""))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _get_stats(self) -> Dict[str, Any]:
        enforcer = get_tool_enforcer()
        learner = get_pattern_learner()
        return {
            "enforcer": enforcer.get_stats(),
            "learner": learner.get_stats()
        }
    
    def _get_patterns(self) -> Dict[str, Any]:
        learner = get_pattern_learner()
        patterns = learner.get_patterns()
        prompt_enhancement = learner.get_system_prompt_enhancement()
        return {
            "patterns": patterns,
            "pattern_count": len(patterns),
            "system_prompt_enhancement": prompt_enhancement[:500] if prompt_enhancement else ""
        }
    
    def _analyze(self) -> Dict[str, Any]:
        enforcer = get_tool_enforcer()
        learner = get_pattern_learner()
        failures = enforcer.get_failure_log()
        if not failures:
            return {"status": "no_failures", "message": "No failures to analyze"}
        return learner.analyze_failures(failures)
    
    def _test_intent(self, request: str) -> Dict[str, Any]:
        if not request:
            return {"error": "Request is required"}
        analyzer = get_intent_analyzer()
        # Use keyword-based fallback for testing (no LLM call needed)
        result = analyzer.analyze_without_llm(request, [
            {"name": "nucleus_tasks", "description": "Task + depth management facade"},
            {"name": "nucleus_engrams", "description": "Memory, health, version, morning brief facade"},
            {"name": "nucleus_governance", "description": "Governance, lock, audit, hypervisor facade"},
            {"name": "nucleus_sessions", "description": "Session management facade"},
            {"name": "nucleus_sync", "description": "Multi-agent sync facade"},
            {"name": "nucleus_orchestration", "description": "Core orchestration facade"},
            {"name": "nucleus_telemetry", "description": "Telemetry and metering facade"},
            {"name": "nucleus_slots", "description": "Slot management and sprints facade"},
            {"name": "nucleus_infra", "description": "Infrastructure and deployment facade"},
            {"name": "nucleus_agents", "description": "Agent management and code ops facade"},
            {"name": "nucleus_features", "description": "Feature map, mounter, proofs facade"},
            {"name": "nucleus_federation", "description": "Federation networking facade"},
        ])
        return result.to_dict()
