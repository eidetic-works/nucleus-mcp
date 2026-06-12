"""v0.3.0 Layer 4 — Fallback chain orchestrator.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 4
(spec lines 137-145) + op-assistant 2026-06-09T09:15Z architectural
amendment (build INTO nucleus) + cc-peer 2026-06-09T10:45Z verdict
batch recommending unified entry-point pattern.

Provides the single function `post_relay_to_role(role, message)` that
upstream callers (relay_inbox_hook patch, daemon arrival handlers,
nucleus_relay MCP tool surface) invoke to deliver a relay to a role's
session via the most-likely-to-wake path.

Original spec § Layer 4 chain:
  try: Layer 3 run-trigger if discovered → fire one call
  else: Layer 1 prearm + Layer 5 (full inference call)
  on Layer 1+5 failure: try cookie-direct against claude.ai (legacy)
  on all failure: log WARN, return; relay still persisted

Empirical update (op-assistant 2026-06-09T03:50Z Layer 3 NULL VERDICT):
no /run primitive exists. The chain collapses to:
  Layer 1 prearm (best-effort, observability only) -> Layer 5 inference
  Cookie-direct legacy path is OUT (ADR-0037 v0.2.x deprecated per
  spec line 193).

What this module does NOT do:
- It does NOT fetch OAuth bearer (caller passes; Layer 0
  nucleus.oauth.exchange.get_access_token provides)
- It does NOT compose discovery_context (caller passes; PR #506
  integration glue will harvest from Layer 2
  nucleus.org.discovery)
- It does NOT register roles in a MAP — that's PR #506
- It does NOT touch relay files — caller persists, this just fires

Pseudonymity carryover:
- OAuth bearer never logged
- session_id + org_uuid truncated [:12] in logs (PR #499 convention)
- Message body content never logged (delegated to Layer 5)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from mcp_server_nucleus.sessions.autonomous_wake import (
    AutonomousWakeError,
    autonomous_wake_from_relay,
)
from mcp_server_nucleus.sessions.wake import (
    SessionStateError,
    prearm_session,
)

logger = logging.getLogger("nucleus.sessions_fallback")

_LOG_ID_MAX = 12  # PR #499 pseudonymity convention


class FallbackChainError(RuntimeError):
    """Raised when ALL chain steps fail terminally.

    Callers should still consider the relay persisted on disk — this
    just signals the wake attempts didn't land.
    """


def _truncate_id(value: str) -> str:
    return value[:_LOG_ID_MAX] if value else ""


def post_relay_to_role(
    *,
    role: str,
    session_id: str,
    org_uuid: str,
    bearer: str,
    relay_subject: str,
    relay_body: str,
    cookies: Optional[Dict[str, str]] = None,
    prearm: bool = True,
    discovery_context: Optional[Dict[str, Any]] = None,
    history_limit: int = 50,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Orchestrate Layer 1 best-effort prearm + Layer 5 inference fire.

    Returns dict:
      {
        ok: bool,                     # True if Layer 5 inference fired OK
        prearm_attempted: bool,
        prearm_ok: bool | None,       # None if not attempted; True/False otherwise
        prearm_error: str | None,
        wake_response: <Layer 5 result dict> | None,
        wake_error: str | None,
      }

    `prearm` defaults True; pass False to skip Layer 1 (e.g., caller
    already pre-armed via separate path, or session known to be
    already armed).

    `cookies` required only when prearm=True (Layer 1 announce_client_presence
    requires claude.ai cookies). If absent, prearm is skipped silently
    rather than raising.

    Raises FallbackChainError ONLY if Layer 5 inference fails
    terminally. Layer 1 failures are absorbed (best-effort, observability).
    """
    if not role or not session_id or not bearer:
        raise FallbackChainError("role + session_id + bearer required")

    result: Dict[str, Any] = {
        "ok": False,
        "prearm_attempted": False,
        "prearm_ok": None,
        "prearm_error": None,
        "wake_response": None,
        "wake_error": None,
    }

    # ── Step 1: Layer 1 best-effort prearm ──────────────────────────
    if prearm and cookies and cookies.get("sessionKey"):
        result["prearm_attempted"] = True
        try:
            prearm_result = prearm_session(
                session_id,
                f"autonomous wake — {role}",
                bearer=bearer,
                cookies=cookies,
            )
            result["prearm_ok"] = True
            logger.info(
                "fallback: prearm ok cse=%s deltas=%s",
                _truncate_id(session_id),
                prearm_result.get("deltas", {}),
            )
        except SessionStateError as exc:
            # Layer 1 failure is NON-blocking — Layer 5 may still succeed.
            result["prearm_ok"] = False
            result["prearm_error"] = str(exc)
            logger.warning(
                "fallback: prearm failed (non-blocking) cse=%s err=%s",
                _truncate_id(session_id), type(exc).__name__,
            )
    elif prearm:
        # cookies missing/empty — skip silently
        logger.info(
            "fallback: prearm skipped (no cookies) cse=%s",
            _truncate_id(session_id),
        )

    # ── Step 2: Layer 5 autonomous wake (load-bearing) ──────────────
    wake_kwargs: Dict[str, Any] = {
        "role": role,
        "session_id": session_id,
        "relay_subject": relay_subject,
        "relay_body": relay_body,
        "bearer": bearer,
        "org_uuid": org_uuid,
        "history_limit": history_limit,
        "discovery_context": discovery_context,
    }
    if model is not None:
        wake_kwargs["model"] = model
    if max_tokens is not None:
        wake_kwargs["max_tokens"] = max_tokens

    try:
        wake_result = autonomous_wake_from_relay(**wake_kwargs)
    except AutonomousWakeError as exc:
        result["wake_error"] = str(exc)
        logger.warning(
            "fallback: Layer 5 inference failed cse=%s role=%s err=%s",
            _truncate_id(session_id), role, type(exc).__name__,
        )
        raise FallbackChainError(
            f"Layer 5 inference failed for role={role}: {type(exc).__name__}"
        ) from exc

    result["wake_response"] = wake_result
    result["ok"] = True

    # ── Step 3: Plan B forwarder — iterate tool_use_blocks ──────────
    # Per op-assistant 17:50Z PRE-WIRE + cc-peer 18:00Z locked contract:
    # for each nucleus_relay tool_use block, call helper to POST via OCI.
    # sender_role LOCKED to `role` here (mitigation (c)) — LLM cannot
    # impersonate. Errors collected in result['relay_post_errors']; do
    # NOT raise (substrate already succeeded).
    tool_use_blocks = wake_result.get("tool_use_blocks") or []
    relay_post_results: List[Dict[str, Any]] = []
    if tool_use_blocks:
        try:
            from mcp_server_nucleus.sessions._relay_post_helper import (
                post_nucleus_relay_block,
            )
            from mcp_server_nucleus.paths import brain_path
            brain_root = brain_path(strict=False)
        except Exception as exc:
            logger.warning(
                "fallback: relay_post helper import failed err=%s — skip forward",
                type(exc).__name__,
            )
        else:
            for block in tool_use_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("name") != "nucleus_relay":
                    # Per cc-peer locked test_floor: non-nucleus_relay
                    # tool_use blocks preserved in wake_response but NOT
                    # forwarded by this helper.
                    continue
                block_id = str(block.get("id") or "")
                try:
                    posted = post_nucleus_relay_block(
                        block_input=block.get("input") or {},
                        sender_role=role,
                        block_id=block_id,
                        brain_root=brain_root,
                    )
                except Exception as exc:
                    logger.warning(
                        "fallback: relay_post helper raised err=%s — best-effort skip",
                        type(exc).__name__,
                    )
                    posted = False
                relay_post_results.append({
                    "block_id": block_id,
                    "posted": bool(posted),
                })
    result["relay_post_results"] = relay_post_results
    result["relay_post_errors"] = [
        r for r in relay_post_results if not r["posted"]
    ]

    logger.info(
        "fallback: chain ok role=%s cse=%s org=%s tool_blocks=%d posted=%d failed=%d",
        role,
        _truncate_id(session_id),
        _truncate_id(org_uuid),
        len(tool_use_blocks),
        sum(1 for r in relay_post_results if r["posted"]),
        len(result["relay_post_errors"]),
    )
    return result


__all__ = [
    "FallbackChainError",
    "post_relay_to_role",
]
