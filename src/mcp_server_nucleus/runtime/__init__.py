"""
Nucleus Agent Runtime - Runtime Package

v0.6.0 DSoR: Added context_manager and ipc_auth for decision provenance.
"""

from .factory import ContextFactory
from .agent import EphemeralAgent, DecisionMade, ActionRequested
from .event_stream import EventSeverity, EventTypes, emit_event, read_events
from .triggers import match_triggers, get_agents_for_event
from .profiling import (
    timed, timed_io, timed_compute, timed_llm,
    get_metrics, get_metrics_summary, reset_metrics, export_metrics_to_file
)
# v0.6.0 DSoR Components
from .context_manager import (
    ContextManager, ContextSnapshot, StateVerificationResult,
    get_context_manager, compute_context_hash, verify_turn_integrity
)
from .auth import (
    IPCAuthProvider as IPCAuthManager,  # Backward compat alias
    IPCToken, TokenMeterEntry,
    get_ipc_auth_manager, require_ipc_token
)
# Agent Runtime V2 (Phase 68)
from .agent_runtime_v2 import (
    AgentExecutionManager, AgentSpawnLimiter, AgentCostTracker,
    AgentCostRecord, AgentExecution, AgentStatus,
    get_execution_manager, with_timeout, check_cancellation
)
from .budget_alerts import BudgetMonitor, BudgetAlert, get_budget_monitor
from .capabilities.budget_ops import BudgetOps
# Phase 71: Tool Calling Enforcement
from .llm_intent_analyzer import LLMIntentAnalyzer, IntentAnalysisResult, get_intent_analyzer
from .llm_tool_validator import LLMToolValidator, ValidationResult, get_tool_validator
from .llm_tool_enforcer import LLMToolEnforcer, EnforcementResult, get_tool_enforcer
from .llm_pattern_learner import LLMPatternLearner, LearnedPattern, get_pattern_learner
# Phase 72: Autonomous Tool Discovery
from .tool_recommender import ToolRecommender, ToolRecommendation, get_tool_recommender
# Phase 73: Production-Grade Hardening
from .llm_resilience import (
    ResilientLLMClient, CircuitBreaker, CircuitState, CircuitBreakerConfig,
    RetryConfig, ErrorCategory, ResilientError,
    get_resilient_llm_client, categorize_exception, extract_json_from_text,
    validate_llm_response
)
from .environment_detector import (
    EnvironmentDetector, EnvironmentInfo, OSType, MCPHost,
    get_environment_detector
)
from .file_resilience import (
    ResilientFileOps, AtomicWriter, FileLock, ResilientJSONReader,
    DiskSpaceChecker, PermissionChecker, get_resilient_file_ops
)
from .error_telemetry import (
    ErrorTelemetry, StructuredError, ErrorDomain, ErrorAggregator,
    AlertManager, AlertThreshold, get_error_telemetry
)

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
