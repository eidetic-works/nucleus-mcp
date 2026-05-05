"""Session-registry primitive (T3.11) — agent presence + 3rd-writer detection.

Per-session JSON envelopes under ``${NUCLEUS_AGENT_REGISTRY}`` (fallback:
``<brain>/agent_registry/``) track which agents are alive on which worktrees.
Liveness is a heartbeat window; the registry is intentionally distinct from
``nucleus_sessions.save/resume`` (which owns user-facing session-context
snapshots under ``.brain/sessions/``).
"""

from .registry import (
    PRIMITIVE_VERSION,
    agent_registry_root,
    detect_splits,
    heartbeat,
    list_agents,
    register_session,
    unregister,
)

__all__ = [
    "PRIMITIVE_VERSION",
    "agent_registry_root",
    "detect_splits",
    "heartbeat",
    "list_agents",
    "register_session",
    "unregister",
]
