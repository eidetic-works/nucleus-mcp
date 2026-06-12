"""v0.3.0 integration — AUTONOMOUS_WAKE_MAP registry.

Per cc-peer 2026-06-09T10:45Z + 11:28Z verdict batch
(actionable_follow_up_for_cc_tb section): registers roles eligible
for autonomous wake on relay arrival, mapping each role to its
inference parameters (model, max_tokens, history_limit) and the
session-identifying tuple (org_uuid, session_id) used by Layers 1/2/5.

Per cc-peer's load-bearing observation on PR #505:
  "Without (a) AUTONOMOUS_WAKE_MAP + (b) relay_inbox_hook patch +
  (c) discovery_context_fetcher, post_relay_to_role is a callable
  library — NOT yet auto-fired on relay arrival."

This module ships (a). discovery_context_fetcher is in the sibling
module sessions/discovery_context.py. The relay_inbox_hook patch (b)
is deferred to a follow-on PR — touches every session, needs explicit
pre-merge cc-peer hole-poke + session-launch smoke per HARD RULE
feedback_substrate_behavior_verify_before_next_thing.

What this module does:
  - Defines AutonomousWakeConfig (the per-role parameter bundle)
  - Exposes a module-level NUCLEUS_AUTONOMOUS_WAKE_MAP dict (starts
    empty; populated at runtime by operator config OR explicit
    register_autonomous_role calls)
  - Provides register_autonomous_role(role, config) for mutation
  - Provides get_autonomous_config(role) for lookup
  - Provides is_autonomous_role(role) for boolean check

Pseudonymity:
- session_id + org_uuid stored in plaintext in MAP entries (necessary
  for autonomous wake to know which session to fire against), but
  truncated [:12] in any log emission per PR #499 _LOG_ID_MAX
- bearer NEVER stored in MAP — fetched fresh via Layer 0
  nucleus.oauth.exchange.get_access_token(role) at fire time
"""
from __future__ import annotations

import logging
from typing import Dict, Optional


logger = logging.getLogger("nucleus.autonomous_wake_map")

_LOG_ID_MAX = 12  # PR #499 pseudonymity convention


def _truncate_id(value: str) -> str:
    return value[:_LOG_ID_MAX] if value else ""


class AutonomousWakeConfig:
    """Per-role inference parameters + session identifier bundle.

    Used by integration glue (PR #509 hook patch) to look up wake
    parameters when a relay arrives for a registered role.
    """

    __slots__ = (
        "role", "session_id", "org_uuid", "account_uuid",
        "model", "max_tokens", "history_limit", "prearm",
    )

    def __init__(
        self,
        *,
        role: str,
        session_id: str,
        org_uuid: str,
        account_uuid: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        history_limit: int = 50,
        prearm: bool = True,
    ):
        if not role:
            raise ValueError("role required")
        if not session_id:
            raise ValueError("session_id required")
        if not org_uuid:
            raise ValueError("org_uuid required")
        self.role = role
        self.session_id = session_id
        self.org_uuid = org_uuid
        # account_uuid is optional — only needed for Task #63 bespoq
        # context reconstruction from local Claude.app session files.
        # Roles without account_uuid get degraded discovery_context
        # (no system_prompt / tools from local file).
        self.account_uuid = account_uuid
        self.model = model
        self.max_tokens = max_tokens
        self.history_limit = int(history_limit)
        self.prearm = bool(prearm)

    def __repr__(self) -> str:
        """Repr truncates IDs per pseudonymity."""
        return (
            f"AutonomousWakeConfig(role={self.role!r}, "
            f"session_id={_truncate_id(self.session_id)!r}..., "
            f"org_uuid={_truncate_id(self.org_uuid)!r}..., "
            f"account_uuid={_truncate_id(self.account_uuid or '')!r}..., "
            f"model={self.model!r}, prearm={self.prearm})"
        )


# Module-level MAP. Starts empty; populated by register_autonomous_role
# at startup OR by operator config loader (separate concern).
NUCLEUS_AUTONOMOUS_WAKE_MAP: Dict[str, AutonomousWakeConfig] = {}


def register_autonomous_role(
    role: str,
    config: AutonomousWakeConfig,
) -> None:
    """Register a role as eligible for autonomous wake.

    Overwrites any existing entry for the role. Caller must ensure
    config.role matches the registry key (assert enforced).
    """
    if not role:
        raise ValueError("role required")
    if not isinstance(config, AutonomousWakeConfig):
        raise TypeError("config must be AutonomousWakeConfig instance")
    if config.role != role:
        raise ValueError(
            f"config.role={config.role!r} must match registry key role={role!r}"
        )
    NUCLEUS_AUTONOMOUS_WAKE_MAP[role] = config
    logger.info(
        "autonomous_wake_map: registered role=%s cse=%s org=%s",
        role,
        _truncate_id(config.session_id),
        _truncate_id(config.org_uuid),
    )


def unregister_autonomous_role(role: str) -> bool:
    """Remove a role from the registry. Returns True if removed."""
    if role in NUCLEUS_AUTONOMOUS_WAKE_MAP:
        del NUCLEUS_AUTONOMOUS_WAKE_MAP[role]
        logger.info("autonomous_wake_map: unregistered role=%s", role)
        return True
    return False


def get_autonomous_config(role: str) -> Optional[AutonomousWakeConfig]:
    """Lookup a role's wake config. Returns None if not registered."""
    return NUCLEUS_AUTONOMOUS_WAKE_MAP.get(role)


def is_autonomous_role(role: str) -> bool:
    """True iff role is registered for autonomous wake."""
    return role in NUCLEUS_AUTONOMOUS_WAKE_MAP


def list_autonomous_roles() -> list[str]:
    """All currently-registered autonomous roles. Caller may iterate."""
    return list(NUCLEUS_AUTONOMOUS_WAKE_MAP.keys())


def clear_registry() -> None:
    """Wipe the registry. Intended for tests + operator config reload."""
    NUCLEUS_AUTONOMOUS_WAKE_MAP.clear()
    logger.info("autonomous_wake_map: registry cleared")


__all__ = [
    "AutonomousWakeConfig",
    "NUCLEUS_AUTONOMOUS_WAKE_MAP",
    "register_autonomous_role",
    "unregister_autonomous_role",
    "get_autonomous_config",
    "is_autonomous_role",
    "list_autonomous_roles",
    "clear_registry",
]
