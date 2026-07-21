"""
Nucleus Agent Runtime - Runtime Package

v0.6.0 DSoR: Added context_manager and ipc_auth for decision provenance.

PERF/ARCH (Move 1): This package __init__ is LAZY (PEP 562). Importing a single
runtime submodule (e.g. ``mcp_server_nucleus.runtime.relay_ops``) no longer drags
the whole agent-runtime / LLM / capabilities stack at import time. The public
symbols below still resolve via ``from mcp_server_nucleus.runtime import X`` and
attribute access — they are imported on first access and then cached in globals.
"""

from importlib import import_module as _import_module

# name -> (submodule, attr_in_submodule). attr defaults to the name when equal.
_LAZY_MAP = {
    # factory
    "ContextFactory": ("factory", "ContextFactory"),
    # agent
    "EphemeralAgent": ("agent", "EphemeralAgent"),
    "DecisionMade": ("agent", "DecisionMade"),
    "ActionRequested": ("agent", "ActionRequested"),
    # event_stream
    "EventSeverity": ("event_stream", "EventSeverity"),
    "EventTypes": ("event_stream", "EventTypes"),
    "emit_event": ("event_stream", "emit_event"),
    "read_events": ("event_stream", "read_events"),
    # triggers
    "match_triggers": ("triggers", "match_triggers"),
    "get_agents_for_event": ("triggers", "get_agents_for_event"),
    # profiling
    "timed": ("profiling", "timed"),
    "timed_io": ("profiling", "timed_io"),
    "timed_compute": ("profiling", "timed_compute"),
    "timed_llm": ("profiling", "timed_llm"),
    "get_metrics": ("profiling", "get_metrics"),
    "get_metrics_summary": ("profiling", "get_metrics_summary"),
    "reset_metrics": ("profiling", "reset_metrics"),
    "export_metrics_to_file": ("profiling", "export_metrics_to_file"),
    # context_manager (v0.6.0 DSoR)
    "ContextManager": ("context_manager", "ContextManager"),
    "ContextSnapshot": ("context_manager", "ContextSnapshot"),
    "StateVerificationResult": ("context_manager", "StateVerificationResult"),
    "get_context_manager": ("context_manager", "get_context_manager"),
    "compute_context_hash": ("context_manager", "compute_context_hash"),
    "verify_turn_integrity": ("context_manager", "verify_turn_integrity"),
    # auth (v0.6.0 DSoR) — IPCAuthManager is a backward-compat alias for IPCAuthProvider
    "IPCAuthManager": ("auth", "IPCAuthProvider"),
    "IPCToken": ("auth", "IPCToken"),
    "TokenMeterEntry": ("auth", "TokenMeterEntry"),
    "get_ipc_auth_manager": ("auth", "get_ipc_auth_manager"),
    "require_ipc_token": ("auth", "require_ipc_token"),
    # agent_runtime_v2 (Phase 68)
    "AgentExecutionManager": ("agent_runtime_v2", "AgentExecutionManager"),
    "AgentSpawnLimiter": ("agent_runtime_v2", "AgentSpawnLimiter"),
    "AgentCostTracker": ("agent_runtime_v2", "AgentCostTracker"),
    "AgentCostRecord": ("agent_runtime_v2", "AgentCostRecord"),
    "AgentExecution": ("agent_runtime_v2", "AgentExecution"),
    "AgentStatus": ("agent_runtime_v2", "AgentStatus"),
    "get_execution_manager": ("agent_runtime_v2", "get_execution_manager"),
    "with_timeout": ("agent_runtime_v2", "with_timeout"),
    "check_cancellation": ("agent_runtime_v2", "check_cancellation"),
    # budget_alerts (Phase 68)
    "BudgetMonitor": ("budget_alerts", "BudgetMonitor"),
    "BudgetAlert": ("budget_alerts", "BudgetAlert"),
    "get_budget_monitor": ("budget_alerts", "get_budget_monitor"),
    "BudgetOps": ("capabilities.budget_ops", "BudgetOps"),
    # Phase 71: Tool Calling Enforcement
    "LLMIntentAnalyzer": ("llm_intent_analyzer", "LLMIntentAnalyzer"),
    "IntentAnalysisResult": ("llm_intent_analyzer", "IntentAnalysisResult"),
    "get_intent_analyzer": ("llm_intent_analyzer", "get_intent_analyzer"),
    "LLMToolValidator": ("llm_tool_validator", "LLMToolValidator"),
    "ValidationResult": ("llm_tool_validator", "ValidationResult"),
    "get_tool_validator": ("llm_tool_validator", "get_tool_validator"),
    "LLMToolEnforcer": ("llm_tool_enforcer", "LLMToolEnforcer"),
    "EnforcementResult": ("llm_tool_enforcer", "EnforcementResult"),
    "get_tool_enforcer": ("llm_tool_enforcer", "get_tool_enforcer"),
    # Optional pattern learner (import may fail -> None, matching legacy try/except)
    "LLMPatternLearner": ("llm_pattern_learner", "LLMPatternLearner"),
    "LearnedPattern": ("llm_pattern_learner", "LearnedPattern"),
    "get_pattern_learner": ("llm_pattern_learner", "get_pattern_learner"),
    # Phase 72: Autonomous Tool Discovery
    "ToolRecommender": ("tool_recommender", "ToolRecommender"),
    "ToolRecommendation": ("tool_recommender", "ToolRecommendation"),
    "get_tool_recommender": ("tool_recommender", "get_tool_recommender"),
    # Phase 73: Production-Grade Hardening
    "ResilientLLMClient": ("llm_resilience", "ResilientLLMClient"),
    "CircuitBreaker": ("llm_resilience", "CircuitBreaker"),
    "CircuitState": ("llm_resilience", "CircuitState"),
    "CircuitBreakerConfig": ("llm_resilience", "CircuitBreakerConfig"),
    "RetryConfig": ("llm_resilience", "RetryConfig"),
    "ErrorCategory": ("llm_resilience", "ErrorCategory"),
    "ResilientError": ("llm_resilience", "ResilientError"),
    "get_resilient_llm_client": ("llm_resilience", "get_resilient_llm_client"),
    "categorize_exception": ("llm_resilience", "categorize_exception"),
    "extract_json_from_text": ("llm_resilience", "extract_json_from_text"),
    "validate_llm_response": ("llm_resilience", "validate_llm_response"),
    "EnvironmentDetector": ("environment_detector", "EnvironmentDetector"),
    "EnvironmentInfo": ("environment_detector", "EnvironmentInfo"),
    "OSType": ("environment_detector", "OSType"),
    "MCPHost": ("environment_detector", "MCPHost"),
    "get_environment_detector": ("environment_detector", "get_environment_detector"),
    "ResilientFileOps": ("file_resilience", "ResilientFileOps"),
    "AtomicWriter": ("file_resilience", "AtomicWriter"),
    "FileLock": ("file_resilience", "FileLock"),
    "ResilientJSONReader": ("file_resilience", "ResilientJSONReader"),
    "DiskSpaceChecker": ("file_resilience", "DiskSpaceChecker"),
    "PermissionChecker": ("file_resilience", "PermissionChecker"),
    "get_resilient_file_ops": ("file_resilience", "get_resilient_file_ops"),
    "ErrorTelemetry": ("error_telemetry", "ErrorTelemetry"),
    "StructuredError": ("error_telemetry", "StructuredError"),
    "ErrorDomain": ("error_telemetry", "ErrorDomain"),
    "ErrorAggregator": ("error_telemetry", "ErrorAggregator"),
    "AlertManager": ("error_telemetry", "AlertManager"),
    "AlertThreshold": ("error_telemetry", "AlertThreshold"),
    "get_error_telemetry": ("error_telemetry", "get_error_telemetry"),
}

# Names whose backing module is optional: a failed import yields None (parity
# with the historical ``try/except ImportError`` around llm_pattern_learner).
_OPTIONAL = frozenset({"LLMPatternLearner", "LearnedPattern", "get_pattern_learner"})


def __getattr__(name):
    """PEP 562 lazy attribute resolution for the runtime package."""
    entry = _LAZY_MAP.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    submod, attr = entry
    try:
        module = _import_module("." + submod, __name__)
        value = getattr(module, attr)
    except ImportError:
        if name in _OPTIONAL:
            value = None
        else:
            raise
    globals()[name] = value  # cache — __getattr__ won't fire again for this name
    return value


def __dir__():
    return sorted(set(list(globals().keys()) + __all__))


__all__ = [
    "ContextFactory",
    "EphemeralAgent",
    "DecisionMade",
    "ActionRequested",
    "EventSeverity",
    "EventTypes",
    "emit_event",
    "read_events",
    "match_triggers",
    "get_agents_for_event",
    # Profiling (AG-014)
    "timed",
    "timed_io",
    "timed_compute",
    "timed_llm",
    "get_metrics",
    "get_metrics_summary",
    "reset_metrics",
    "export_metrics_to_file",
    # v0.6.0 DSoR - Context Manager
    "ContextManager",
    "ContextSnapshot",
    "StateVerificationResult",
    "get_context_manager",
    "compute_context_hash",
    "verify_turn_integrity",
    # v0.6.0 DSoR - IPC Auth
    "IPCAuthManager",
    "IPCToken",
    "TokenMeterEntry",
    "get_ipc_auth_manager",
    "require_ipc_token",
    # Agent Runtime V2 (Phase 68)
    "AgentExecutionManager",
    "AgentSpawnLimiter",
    "AgentCostTracker",
    "AgentCostRecord",
    "AgentExecution",
    "AgentStatus",
    "get_execution_manager",
    "with_timeout",
    "check_cancellation",
    # Budget Monitoring (Phase 68)
    "BudgetMonitor",
    "BudgetAlert",
    "get_budget_monitor",
    "BudgetOps",
    # Phase 71: Tool Calling Enforcement
    "LLMIntentAnalyzer",
    "IntentAnalysisResult",
    "get_intent_analyzer",
    "LLMToolValidator",
    "ValidationResult",
    "get_tool_validator",
    "LLMToolEnforcer",
    "EnforcementResult",
    "get_tool_enforcer",
    "LLMPatternLearner",
    "LearnedPattern",
    "get_pattern_learner",
    # Phase 72: Autonomous Tool Discovery
    "ToolRecommender",
    "ToolRecommendation",
    "get_tool_recommender",
    # Phase 73: Production-Grade Hardening
    "ResilientLLMClient",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerConfig",
    "RetryConfig",
    "ErrorCategory",
    "ResilientError",
    "get_resilient_llm_client",
    "categorize_exception",
    "extract_json_from_text",
    "validate_llm_response",
    "EnvironmentDetector",
    "EnvironmentInfo",
    "OSType",
    "MCPHost",
    "get_environment_detector",
    "ResilientFileOps",
    "AtomicWriter",
    "FileLock",
    "ResilientJSONReader",
    "DiskSpaceChecker",
    "PermissionChecker",
    "get_resilient_file_ops",
    "ErrorTelemetry",
    "StructuredError",
    "ErrorDomain",
    "ErrorAggregator",
    "AlertManager",
    "AlertThreshold",
    "get_error_telemetry",
]
