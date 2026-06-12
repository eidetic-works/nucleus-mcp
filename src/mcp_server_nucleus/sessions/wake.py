"""v0.3.0 Layer 1 — Session state-update + client-presence utilities.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 1 +
op-assistant 2026-06-09T03:40Z empirical findings (PUT + presence
alone do NOT wake the agent — `connection_status` stayed
`disconnected`, `worker_status` stayed `idle`, even after 10x presence
hammer with valid OAuth bearer) + op-assistant 2026-06-09T09:15Z
architectural amendment (build INTO nucleus, not standalone scripts/).

Empirical posture: this module ships PUT-session + POST-presence
helpers as session-STATE-UPDATE utilities + observability primitives,
NOT as a wake mechanism. Actual wake requires either:
  - Layer 3 finding an undocumented `/run` primitive (op-assistant
    Layer 3 NULL VERDICT 2026-06-09T03:50Z — no such primitive
    exists for operator's account), OR
  - Layer 5 full inference replay via POST /v1/messages?beta=true
    (now MANDATORY post-Layer-3-NULL)

What this layer IS useful for:
  - Updating session metadata (title) on api.anthropic.com
  - Announcing client presence on claude.ai (heartbeat + clear semantics)
  - GET-session for observability — comparing state before vs after
  - Per-process client_id persistence (caller-generated UUID v4 per
    op-assistant Q2 answer; server tracks presence per client_id)

Host-split auth (per op-assistant Q4 empirical):
  - api.anthropic.com → OAuth Bearer sk-ant-oat01-... (from Layer 0
    nucleus.oauth.exchange)
  - claude.ai → Cookies (sessionKey + lastActiveOrg + anthropic-device-id
    + cf_clearance from operator's Keychain)
  - NEITHER auth works on the other host (empirically verified
    2026-06-09T03:35Z by op-assistant)

Pseudonymity carryover:
  - OAuth bearer + cookies + client_id never logged
  - session_id truncated [:12] in logs (matches PR #499 _LOG_ID_MAX
    convention)
"""
from __future__ import annotations

import logging
import uuid as _uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from curl_cffi import requests as _curl_requests
except ImportError:  # pragma: no cover - tests stub via patch
    _curl_requests = None  # type: ignore[assignment]


logger = logging.getLogger("nucleus.session_wake")

# Hosts per op-assistant Q4 empirical
_API_ANTHROPIC = "https://api.anthropic.com"
_CLAUDE_AI = "https://claude.ai"

_ANTHROPIC_VERSION = "2023-06-01"  # per Q1 captured headers
_IMPERSONATE = "chrome120"  # curl_cffi profile (consistent with Layer 0)
_HTTP_TIMEOUT_S = 15.0
_LOG_ID_MAX = 12  # match PR #499 pseudonymity convention

# Per-process client_id persistence path (per Q2: persist per-process,
# regenerate on daemon restart per process-id-binding).
_CLIENT_ID_PATH = Path.home() / ".tb" / "wake_client_id"


# ── Exceptions ──────────────────────────────────────────────────────────


class SessionStateError(RuntimeError):
    """Raised when a session-state operation fails terminally.

    Recoverable failures (timeout / network) raise SessionStateError so
    callers can decide whether to retry. Empty-config failures (missing
    bearer / cookies / cse) also raise — caller config issue.
    """


# ── Client-ID lifecycle ─────────────────────────────────────────────────


def _get_or_create_client_id() -> str:
    """Return per-process UUID v4 client_id; create + persist on first call.

    Per op-assistant Q2: server tracks presence per client_id; persist
    per-process (regenerate on daemon restart, NOT per-call). Stored at
    ~/.tb/wake_client_id mode 600.
    """
    try:
        existing = _CLIENT_ID_PATH.read_text().strip()
        if existing and len(existing) >= 32:
            return existing
    except OSError:
        pass
    new_id = str(_uuid.uuid4())
    _CLIENT_ID_PATH.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = _CLIENT_ID_PATH.with_suffix(".tmp")
    tmp.write_text(new_id)
    tmp.chmod(0o600)
    tmp.replace(_CLIENT_ID_PATH)
    return new_id


def _truncate_id(value: str) -> str:
    """Truncate an ID for log emission (PR #499 _LOG_ID_MAX convention)."""
    return value[:_LOG_ID_MAX] if value else ""


# ── PUT session metadata (api.anthropic.com, OAuth bearer) ──────────────


def update_session_title(
    cse: str,
    title: str,
    *,
    bearer: str,
) -> Dict[str, Any]:
    """PUT api.anthropic.com/v1/code/sessions/<cse_> body={title: ...}.

    Returns parsed `session` dict from response (see Q1 response shape).
    Raises SessionStateError on non-2xx / transport failure.

    NOTE per op-assistant 2026-06-09T03:35Z empirical: this call alone
    does NOT wake the agent. It updates server-side metadata and the
    response wraps `connection_status`, `worker_status` etc which the
    caller can inspect for observability — but state changes require
    a separate run-trigger (Layer 3 NULL → Layer 5 mandatory).
    """
    if not cse or not bearer:
        raise SessionStateError("cse + bearer required")
    if _curl_requests is None:
        raise SessionStateError("curl_cffi not installed")

    url = f"{_API_ANTHROPIC}/v1/code/sessions/{cse}"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {"title": title}
    try:
        resp = _curl_requests.put(
            url, headers=headers, json=body,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning("session_wake: PUT transport class=%s", type(exc).__name__)
        raise SessionStateError(f"transport error: {type(exc).__name__}") from exc

    if not (200 <= resp.status_code < 300):
        logger.warning("session_wake: PUT rejected status=%d cse=%s",
                       resp.status_code, _truncate_id(cse))
        raise SessionStateError(f"PUT rejected status={resp.status_code}")

    parsed = resp.json()
    session = parsed.get("session") or {}
    logger.info(
        "session_wake: PUT ok cse=%s worker=%s connection=%s",
        _truncate_id(cse),
        session.get("worker_status", "?"),
        session.get("connection_status", "?"),
    )
    return session


# ── POST client presence (claude.ai, cookies) ──────────────────────────


def announce_client_presence(
    cse: str,
    *,
    cookies: Dict[str, str],
    clear: bool = True,
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """POST claude.ai/v1/code/sessions/<cse_>/client/presence.

    Body: {client_id, clear}. client_id defaults to per-process UUID v4
    persisted at ~/.tb/wake_client_id; caller can pass explicit override.

    Returns parsed response which includes `refresh_after_seconds` (per
    op-assistant Q2: server tells you when to re-fire heartbeat).

    Per op-assistant Q4 host-split: claude.ai uses COOKIES, not bearer.
    """
    if not cse:
        raise SessionStateError("cse required")
    if not cookies or not cookies.get("sessionKey"):
        raise SessionStateError("cookies (sessionKey at minimum) required for claude.ai")
    if _curl_requests is None:
        raise SessionStateError("curl_cffi not installed")

    cid = client_id or _get_or_create_client_id()
    url = f"{_CLAUDE_AI}/v1/code/sessions/{cse}/client/presence"
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": cookie_header,
    }
    body = {"client_id": cid, "clear": bool(clear)}
    try:
        resp = _curl_requests.post(
            url, headers=headers, json=body,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning("session_wake: presence transport class=%s", type(exc).__name__)
        raise SessionStateError(f"transport error: {type(exc).__name__}") from exc

    if not (200 <= resp.status_code < 300):
        logger.warning(
            "session_wake: presence rejected status=%d cse=%s",
            resp.status_code, _truncate_id(cse),
        )
        raise SessionStateError(f"presence rejected status={resp.status_code}")

    parsed = resp.json() if resp.json is not None else {}
    if not isinstance(parsed, dict):
        parsed = {}
    logger.info(
        "session_wake: presence ok cse=%s refresh_after=%s",
        _truncate_id(cse), parsed.get("refresh_after_seconds", "?"),
    )
    return parsed


# ── GET session state (observability — host-flex) ───────────────────────


def get_session_state(
    cse: str,
    *,
    bearer: str,
) -> Dict[str, Any]:
    """GET api.anthropic.com/v1/code/sessions/<cse_> → parsed session dict.

    Use for observability: compare state before vs after pre_arm or any
    other operation. Per op-assistant Q3 verification path (spec line 95):
    poll session.worker_status + session.unread to observe whether
    a state change occurred.
    """
    if not cse or not bearer:
        raise SessionStateError("cse + bearer required")
    if _curl_requests is None:
        raise SessionStateError("curl_cffi not installed")

    url = f"{_API_ANTHROPIC}/v1/code/sessions/{cse}"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "anthropic-version": _ANTHROPIC_VERSION,
        "Accept": "application/json",
    }
    try:
        resp = _curl_requests.get(
            url, headers=headers,
            impersonate=_IMPERSONATE, timeout=_HTTP_TIMEOUT_S,
        )
    except Exception as exc:
        logger.warning("session_wake: GET transport class=%s", type(exc).__name__)
        raise SessionStateError(f"transport error: {type(exc).__name__}") from exc

    if not (200 <= resp.status_code < 300):
        logger.warning("session_wake: GET rejected status=%d cse=%s",
                       resp.status_code, _truncate_id(cse))
        raise SessionStateError(f"GET rejected status={resp.status_code}")

    parsed = resp.json()
    return parsed.get("session") or parsed


# ── Orchestrator: prearm_session ───────────────────────────────────────


def prearm_session(
    cse: str,
    title: str,
    *,
    bearer: str,
    cookies: Dict[str, str],
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Orchestrate PUT-session + POST-presence; return observability bundle.

    Per spec § Layer 1 (line 83-95): pre-arm a dormant cse_ session
    by updating metadata + announcing presence. The empirical truth
    (op-assistant 2026-06-09T03:35Z) is that this does NOT wake the
    agent — it stages server-side state for whatever Layer 5 follows.

    Returns dict:
      {
        before: {<session-state-from-GET>},
        put_response: {<session-state-from-PUT>},
        presence_response: {client_id, refresh_after_seconds, ...},
        after: {<session-state-from-GET>},
        deltas: {connection_status_changed: bool, worker_status_changed: bool,
                 unread_changed: bool},
      }

    Caller (Layer 4 / Layer 5) inspects `deltas` to decide next step.
    """
    before = get_session_state(cse, bearer=bearer)
    put_response = update_session_title(cse, title, bearer=bearer)
    presence_response = announce_client_presence(
        cse, cookies=cookies, clear=True, client_id=client_id,
    )
    after = get_session_state(cse, bearer=bearer)

    def _changed(key: str) -> bool:
        return before.get(key) != after.get(key)

    deltas = {
        "connection_status_changed": _changed("connection_status"),
        "worker_status_changed": _changed("worker_status"),
        "unread_changed": _changed("unread"),
    }
    logger.info(
        "session_wake: prearm done cse=%s deltas=%s",
        _truncate_id(cse), deltas,
    )
    return {
        "before": before,
        "put_response": put_response,
        "presence_response": presence_response,
        "after": after,
        "deltas": deltas,
    }


__all__ = [
    "SessionStateError",
    "update_session_title",
    "announce_client_presence",
    "get_session_state",
    "prearm_session",
]
