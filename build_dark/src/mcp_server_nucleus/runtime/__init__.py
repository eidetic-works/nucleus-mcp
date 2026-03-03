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
from .ipc_auth import (
    IPCAuthManager, IPCToken, TokenMeterEntry,
    get_ipc_auth_manager, require_ipc_token
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
    "require_ipc_token"
]
