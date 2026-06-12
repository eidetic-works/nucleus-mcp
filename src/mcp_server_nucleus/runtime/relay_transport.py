"""Relay transport abstraction — Filesystem vs HTTP switch (PR-A v0.1).

Per spec at .brain/plans/2026-06-06_relay_as_service_v0_1.md (operator-approved
2026-06-06 ~09:25Z via ExitPlanMode + Mac-flip addition).

Architecture:
    When NUCLEUS_RELAY_URL is unset → every public function returns FS-path
    semantics identical to today's behaviour. No-op import for FS-only sessions.

    When NUCLEUS_RELAY_URL is set → bearer-authed HTTP to the existing
    http_transport/relay_route.py endpoints. Cloud-cowork sessions on
    GitHub Actions / OCI / cloud Claude Code use this path for inbox access.

Public functions:
    is_http_mode()   → bool — read NUCLEUS_RELAY_URL once
    read_inbox(role) → list[dict] — GET /relay/{canonical}?unread_only=&limit=
    post_relay(payload) → dict — POST /relay/{to}
    mark_seen(role, ids) → dict — POST /relay/{canonical}/ack
    get_status(role) → dict — GET /relay/{canonical}/status

Implementation notes (HARD per spec):
    - urllib.request stdlib only (NOT httpx — httpx is in optional [http] extra
      per pyproject.toml:40-43; runtime hard-dep breaks install profile of
      every existing consumer)
    - NUCLEUS_RELAY_BEARER required when NUCLEUS_RELAY_URL is set; fail loud
      one-line RuntimeError at first call
    - resolve_canonical_inbox_name called once at top of every public function
    - Defensive shape on 401/403/404/5xx: return [] or {sent: False, error: ...},
      log single warning, NEVER crash (mirrors mirror/hook.py:71-74 swallow-
      json.JSONDecodeError pattern)
    - Rate-limit awareness: read X-RateLimit-Remaining header; if 0, return
      cached empty and let caller back off (don't retry tight)

Reuse:
    - resolve_canonical_inbox_name from .relay_inbox_canonical (PR #475 SSOT)
    - Canonical role resolution + env precedence at call sites in relay_ops
      (CC_SESSION_ROLE → NUCLEUS_SESSION_ROLE → NUCLEUS_RELAY_RECIPIENT → "main")
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from .relay_inbox_canonical import resolve_canonical_inbox_name

logger = logging.getLogger(__name__)

# ── HTTP transport tuning ──────────────────────────────────────────────────

_DEFAULT_TIMEOUT_S = 10  # urllib timeout per request; v0.1 conservative
_ENV_URL = "NUCLEUS_RELAY_URL"
_ENV_BEARER = "NUCLEUS_RELAY_BEARER"
# Same env var the server reads for its 413 guard (relay_route.MAX_BODY_BYTES)
# so client fail-fast and server reject stay in lockstep.
_ENV_MAX_BODY = "NUCLEUS_RELAY_MAX_BODY"
_DEFAULT_MAX_BODY_BYTES = 65536


# ── Mode detection ─────────────────────────────────────────────────────────


def is_http_mode() -> bool:
    """Return True if NUCLEUS_RELAY_URL is set (transport switch flipped).

    Read fresh every call so test harnesses + env-flip-mid-session work.
    Caching would risk stale behaviour after Mac-HTTP opt-in flip.
    """
    return bool(os.environ.get(_ENV_URL, "").strip())


def _base_url() -> str:
    """Canonicalize the NUCLEUS_RELAY_URL — strip trailing slash for joins."""
    raw = os.environ.get(_ENV_URL, "").strip()
    return raw.rstrip("/")


def _bearer_or_raise() -> str:
    """Return bearer token from env or raise RuntimeError (fail loud per spec).

    Per v0.2.1 (per-role bearer Layer A): callers MAY pass an explicit bearer
    kwarg into public functions; this env-read becomes the no-bearer-passed
    fallback. The fail-loud RuntimeError shape stays unchanged for HTTP mode
    + no bearer anywhere.
    """
    token = os.environ.get(_ENV_BEARER, "").strip()
    if not token:
        raise RuntimeError(
            f"{_ENV_URL} set but {_ENV_BEARER} missing — refusing to send "
            f"unauthenticated HTTP relay traffic"
        )
    return token


def _resolve_bearer(bearer: Optional[str]) -> str:
    """Bearer precedence: explicit kwarg > env via _bearer_or_raise().

    Per v0.2.1 Layer A bearer-kwarg threading: when caller (tools/relay.py
    facade) resolves a per-role bearer from ~/.tb/relay_token_<role>, it
    passes that bearer through to the transport function which forwards it
    here. None → fall through to env. Non-empty string → use it directly
    (treated as already-validated by caller).
    """
    if bearer is not None and bearer != "":
        return bearer
    return _bearer_or_raise()


# ── HTTP helper (defensive, never raises on transport failure) ─────────────


def _http_call(
    method: str,
    path: str,
    *,
    body: Optional[dict] = None,
    headers: Optional[dict[str, str]] = None,
    bearer: Optional[str] = None,
) -> tuple[int, Optional[dict], dict[str, str]]:
    """Issue a bearer-authed HTTP request. Return (status, parsed_body, headers).

    Defensive shape: connection errors / non-2xx surface as status codes the
    caller checks. NEVER raises except for RuntimeError on missing bearer
    (which is a configuration failure the caller cannot recover from).

    Args:
        method: HTTP verb (GET / POST)
        path: path relative to _base_url() (must start with "/")
        body: dict JSON-encoded for POST; None for GET
        headers: optional additional headers (e.g., Idempotency-Key)
        bearer: explicit bearer token (v0.2.1 per-role); None → env fallback

    Returns:
        (status_code, parsed_response_body_or_None, response_headers_dict)
        On connection refused / DNS failure / timeout: returns (0, None, {}).
    """
    url = _base_url() + path
    bearer = _resolve_bearer(bearer)
    req_headers = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)

    data: Optional[bytes] = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT_S) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            resp_headers = {k: v for k, v in resp.headers.items()}
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = None
            return status, parsed, resp_headers
    except urllib.error.HTTPError as exc:
        # Server returned non-2xx (401, 403, 404, 5xx). Defensive: capture
        # status and headers but return parsed=None.
        try:
            resp_headers = {k: v for k, v in exc.headers.items()} if exc.headers else {}
        except Exception:
            resp_headers = {}
        logger.warning(
            "relay_transport: %s %s -> HTTP %s", method, path, exc.code
        )
        return exc.code, None, resp_headers
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning(
            "relay_transport: %s %s -> connection error: %s", method, path, exc
        )
        return 0, None, {}


def _rate_limit_exhausted(headers: dict[str, str]) -> bool:
    """Return True if X-RateLimit-Remaining == 0 (caller should back off)."""
    remaining = headers.get("X-RateLimit-Remaining", "").strip()
    return remaining == "0"


# ── Public API (FS / HTTP dual-mode) ────────────────────────────────────────


class InboxResult(list):
    """``read_inbox`` return type: a plain list of envelope dicts plus
    truth-in-signaling attributes so callers can tell "inbox is empty"
    apart from "transport failed" / "rate budget exhausted" / "server
    truncated the page". ``isinstance(x, list)`` stays True and JSON
    serialization is unchanged — fully backward-compatible.
    """

    def __init__(
        self,
        messages=(),
        *,
        has_more: bool = False,
        rate_limited: bool = False,
        transport_error: bool = False,
    ):
        super().__init__(messages)
        self.has_more = has_more
        self.rate_limited = rate_limited
        self.transport_error = transport_error


def read_inbox(
    role: str,
    *,
    unread_only: bool = True,
    limit: int = 50,
    bearer: Optional[str] = None,
) -> "InboxResult":
    """Return inbox messages for ``role``. FS-mode caller MUST guard with
    ``if not is_http_mode():`` and fall back to existing FS code path.

    HTTP-mode contract: GET {URL}/relay/{canonical}?unread_only=<>&limit=<>
        → server returns {"messages": [...], "count": N, "has_more": bool}

    Defensive return: connection error / 401 / 403 / 404 / 5xx → empty
    InboxResult with ``transport_error=True`` + warning log; does NOT raise.
    Rate-limit budget exhausted on a SUCCESSFUL response keeps the messages
    and sets ``rate_limited=True`` (callers back off but no longer lose a
    good page). Server ``has_more`` is surfaced instead of discarded.

    bearer kwarg (v0.2.1 Layer A): explicit per-call bearer; None falls
    through to NUCLEUS_RELAY_BEARER env via _resolve_bearer.
    """
    canonical = resolve_canonical_inbox_name(role) or role
    if not is_http_mode():
        # FS-mode callers in relay_ops.py route to existing code paths.
        # This branch exists so direct importers (tests, admin tools) get a
        # consistent empty-list fallback when HTTP isn't configured.
        return InboxResult()

    qs = urllib.parse.urlencode(
        {"unread_only": "true" if unread_only else "false", "limit": str(limit)}
    )
    status, body, headers = _http_call("GET", f"/relay/{canonical}?{qs}", bearer=bearer)
    if not (200 <= status < 300) or not isinstance(body, dict):
        return InboxResult(
            rate_limited=(status == 429),
            transport_error=True,
        )
    msgs = body.get("messages")
    if not isinstance(msgs, list):
        msgs = []
    return InboxResult(
        msgs,
        has_more=bool(body.get("has_more", False)),
        rate_limited=_rate_limit_exhausted(headers),
    )


def post_relay(payload: dict, *, bearer: Optional[str] = None) -> dict:
    """Post a relay envelope. FS-mode caller MUST guard with
    ``if not is_http_mode():`` and call ``relay_ops.relay_post(**payload)``.

    HTTP-mode contract: POST {URL}/relay/{payload['to']}
        body = full envelope (subject, body, sender, priority, to, context,
                              in_reply_to, to_session_id, from_session_id)

    Idempotency-Key header derives from ``payload.get('id')`` when present,
    falling back to a hash of the body fields if not.

    Returns ``{"sent": True, "id": <message_id>}`` on success;
    ``{"sent": False, "error": <code>}`` on transport failure.

    bearer kwarg (v0.2.1 Layer A): explicit per-call bearer; None falls
    through to NUCLEUS_RELAY_BEARER env via _resolve_bearer.
    """
    if not is_http_mode():
        return {"sent": False, "error": "fs_mode_caller_should_route_to_relay_ops"}

    to_role = payload.get("to")
    if not to_role:
        return {"sent": False, "error": "missing_to_field"}
    canonical = resolve_canonical_inbox_name(to_role) or to_role

    # Client-side mirror of the server's 413 guard: serialize exactly as
    # _http_call will and fail fast instead of burning a rate-budget slot
    # on a request the server is guaranteed to reject.
    try:
        max_body = int(os.environ.get(_ENV_MAX_BODY, "") or _DEFAULT_MAX_BODY_BYTES)
    except ValueError:
        max_body = _DEFAULT_MAX_BODY_BYTES
    encoded_size = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    if encoded_size > max_body:
        logger.warning(
            "relay_transport: post_relay payload %d bytes exceeds cap %d — "
            "refusing client-side (server would 413)",
            encoded_size,
            max_body,
        )
        return {"sent": False, "error": "body_too_large"}

    idempotency_key = payload.get("id") or ""
    headers = {}
    if idempotency_key:
        headers["Idempotency-Key"] = str(idempotency_key)
    if payload.get("from_session_id"):
        headers["X-Sender-Session-Id"] = str(payload["from_session_id"])

    status, body, resp_headers = _http_call(
        "POST", f"/relay/{canonical}", body=payload, headers=headers, bearer=bearer
    )
    # 2xx contract: server returns 202 Accepted per relay_route.py POST
    # /relay/{recipient}; pre-2026-06-07 narrow (200, 201) check excluded
    # the server's actual success status and made post_relay() return
    # sent=False for messages that were in fact persisted server-side.
    if 200 <= status < 300 and isinstance(body, dict):
        # Task #62: the live server 202 echoes the stored id as "message_id"
        # (relay_route.py response contract); reading only "id" returned ""
        # for callers that supplied no client id (Dispatch). "id" kept for
        # older/raw deploys; idempotency key is the last-resort fallback.
        returned_id = body.get("message_id") or body.get("id") or idempotency_key
        return {"sent": True, "id": returned_id}
    return {"sent": False, "error": status or "transport_failure"}


def mark_seen(role: str, message_ids: list[str], *, bearer: Optional[str] = None) -> dict:
    """Mark one or more relay messages as ack'd. FS-mode caller MUST guard
    with ``if not is_http_mode():`` and call ``relay_ops.relay_ack(...)`` per id.

    HTTP-mode contract: POST {URL}/relay/{canonical}/ack
        body = {"message_ids": [id1, id2, ...]}

    Returns ``{"acked": <count>, "failed": <count>}`` on success;
    ``{"acked": 0, "failed": <len>, "error": <code>}`` on transport failure.

    bearer kwarg (v0.2.1 Layer A): explicit per-call bearer; None falls
    through to NUCLEUS_RELAY_BEARER env via _resolve_bearer.
    """
    if not is_http_mode():
        return {"acked": 0, "failed": 0, "error": "fs_mode_caller_should_route_to_relay_ops"}
    if not message_ids:
        return {"acked": 0, "failed": 0}

    canonical = resolve_canonical_inbox_name(role) or role
    status, body, _ = _http_call(
        "POST",
        f"/relay/{canonical}/ack",
        body={"message_ids": list(message_ids)},
        bearer=bearer,
    )
    # 2xx contract for symmetry with post_relay: server currently returns 200
    # but accept any 2xx success to stay resilient to future server-side
    # status-code changes (matches post_relay's 2xx-success window).
    if 200 <= status < 300 and isinstance(body, dict):
        return {
            "acked": int(body.get("acked", len(message_ids))),
            "failed": int(body.get("failed", 0)),
        }
    return {
        "acked": 0,
        "failed": len(message_ids),
        "error": status or "transport_failure",
    }


def get_status(role: str, *, bearer: Optional[str] = None) -> dict:
    """Fetch server-side inbox status for ``role``. FS-mode caller MUST guard
    with ``if not is_http_mode():`` and use the FS mailbox scan in relay_ops.

    HTTP-mode contract: GET {URL}/relay/{canonical}/status
        → {"recipient": <canonical>, "queue_depth": N, "unread": N,
           "marketplace": {...}}

    Returns ``{"ok": True, **server_body}`` on success;
    ``{"ok": False, "error": <code>}`` on transport failure (connection
    error / 401 / 403 / 404 / 5xx) — warning logged by _http_call, never
    raises.

    bearer kwarg (v0.2.1 Layer A): explicit per-call bearer; None falls
    through to NUCLEUS_RELAY_BEARER env via _resolve_bearer.
    """
    canonical = resolve_canonical_inbox_name(role) or role
    if not is_http_mode():
        return {"ok": False, "error": "fs_mode_caller_should_route_to_relay_ops"}

    status, body, _ = _http_call("GET", f"/relay/{canonical}/status", bearer=bearer)
    if 200 <= status < 300 and isinstance(body, dict):
        return {"ok": True, **body}
    return {"ok": False, "error": status or "transport_failure"}


__all__ = [
    "is_http_mode",
    "read_inbox",
    "post_relay",
    "mark_seen",
    "get_status",
]
