"""Relay-as-Service v0.1 → v0.2.1 — client HTTP transport layer.

When ``NUCLEUS_RELAY_URL`` is set, relay reads/writes route through the
canonical HTTP relay service (ADR-0039) instead of the local filesystem.
When unset, every call returns a marker-shape so the caller can route
to the existing FS code path — zero behaviour change.

Contract mirrors ``http_transport/relay_route.py`` exactly:
  - POST   /relay/{recipient}          → post_relay
  - GET    /relay/{recipient}          → read_inbox
  - POST   /relay/{recipient}/ack      → mark_seen
  - GET    /relay/{recipient}/status   → get_status

v0.2.1 Layer A: per-role bearer. Callers resolve the bearer per-call
from ``~/.tb/relay_token_<role>`` (or ``NUCLEUS_RELAY_BEARER`` env fallback)
and pass it via the ``bearer=`` kwarg.

Uses stdlib ``urllib.request`` only — httpx is in the optional ``[http]``
extra and must not be a hard dependency of runtime.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .relay_inbox_canonical import resolve_canonical_inbox_name

__all__ = [
    "is_http_mode",
    "post_relay",
    "read_inbox",
    "mark_seen",
    "get_status",
    "_bearer_or_raise",
    "_http_call",
    "InboxResult",
]

_DEFAULT_MAX_BODY = 65536


# ---------------------------------------------------------------------------
# InboxResult — list subclass with truth-in-signaling flags (PR #540)
# ---------------------------------------------------------------------------

class InboxResult(list):
    """A list of relay messages with signaling flags.

    ``isinstance(result, list)`` is True — all existing callers that
    iterate or index work unchanged. The flags let new callers
    distinguish "genuinely empty" from "transport failed" or "page
    truncated by rate-limit budget".

    Attributes:
        has_more: Server signalled more messages exist beyond this page.
        rate_limited: Rate budget exhausted (X-RateLimit-Remaining: 0
            or HTTP 429).
        transport_error: HTTP-level or connection error occurred;
            the returned list may be empty or partial.
    """

    _has_more: bool = False
    _rate_limited: bool = False
    _transport_error: bool = False

    def __init__(self, iterable=(), *, has_more=False, rate_limited=False, transport_error=False):
        super().__init__(iterable)
        self._has_more = bool(has_more)
        self._rate_limited = bool(rate_limited)
        self._transport_error = bool(transport_error)

    @property
    def has_more(self) -> bool:
        return self._has_more

    @has_more.setter
    def has_more(self, v: bool) -> None:
        self._has_more = bool(v)

    @property
    def rate_limited(self) -> bool:
        return self._rate_limited

    @rate_limited.setter
    def rate_limited(self, v: bool) -> None:
        self._rate_limited = bool(v)

    @property
    def transport_error(self) -> bool:
        return self._transport_error

    @transport_error.setter
    def transport_error(self, v: bool) -> None:
        self._transport_error = bool(v)


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def is_http_mode() -> bool:
    """True when ``NUCLEUS_RELAY_URL`` is set to a non-blank value."""
    return bool(os.environ.get("NUCLEUS_RELAY_URL", "").strip())


def _base_url() -> str:
    url = os.environ.get("NUCLEUS_RELAY_URL", "").strip()
    if not url:
        raise RuntimeError("is_http_mode() is False but _base_url() called")
    return url.rstrip("/")


def _bearer_or_raise(bearer: Optional[str] = None) -> str:
    """Resolve the bearer token for a relay call.

    Explicit ``bearer`` arg wins (per-role token from the caller).
    Falls through to ``NUCLEUS_RELAY_BEARER`` env.
    Raises ``RuntimeError`` mentioning ``NUCLEUS_RELAY_BEARER missing``
    if neither is set.
    """
    if bearer and bearer.strip():
        return bearer.strip()
    token = os.environ.get("NUCLEUS_RELAY_BEARER", "").strip()
    if not token:
        raise RuntimeError(
            "NUCLEUS_RELAY_URL set but NUCLEUS_RELAY_BEARER missing"
        )
    return token


def _max_body_bytes() -> int:
    raw = os.environ.get("NUCLEUS_RELAY_MAX_BODY", "").strip()
    if not raw:
        return _DEFAULT_MAX_BODY
    try:
        return int(raw)
    except ValueError:
        return _DEFAULT_MAX_BODY


def _extract_rate_limit(headers) -> Optional[int]:
    """Parse X-RateLimit-Remaining from response headers (case-insensitive)."""
    if not headers:
        return None
    try:
        val = headers.get("X-RateLimit-Remaining")
    except (AttributeError, TypeError):
        return None
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# HTTP helper — single I/O seam (monkeypatched in self-recursion tests)
# ---------------------------------------------------------------------------

def _http_call(
    method: str,
    path: str,
    *,
    bearer: Optional[str] = None,
    body: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 15,
) -> tuple[int, Optional[dict], Any, Optional[int]]:
    """Issue an HTTP request to the relay service.

    Returns ``(status_code, parsed_json_or_None, error, rate_limit_remaining)``.
    error is ``None`` on success, ``int`` (status code) for HTTP errors,
    or ``"transport_failure"`` for connection errors.
    rate_limit_remaining is parsed from ``X-RateLimit-Remaining`` header
    or ``None`` if absent.

    This is the single HTTP I/O seam. Tests monkeypatch this to ``_boom``
    as a self-recursion tripwire (see test_relay_route_self_recursion.py).
    """
    url = _base_url() + path
    if params:
        qs = "&".join(
            f"{k}={urllib.parse.quote(str(v), safe='')}"
            for k, v in params.items()
            if v is not None
        )
        if qs:
            url += f"?{qs}"

    data = None
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {_bearer_or_raise(bearer)}",
        "Accept": "application/json",
    }

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
            if raw:
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    parsed = None
            else:
                parsed = None
            rl = _extract_rate_limit(resp.headers)
            return status, parsed, None, rl
    except urllib.error.HTTPError as e:
        raw = e.read()
        if raw:
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                parsed = None
        else:
            parsed = None
        rl = _extract_rate_limit(e.headers) if e.headers else None
        return e.code, parsed, e.code, rl
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None, "transport_failure", None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FS_MARKER = "fs_mode_caller_should_route_to_relay_ops"


def read_inbox(
    role: str,
    *,
    unread_only: bool = True,
    limit: int = 50,
    bearer: Optional[str] = None,
) -> InboxResult:
    """GET /relay/{canonical} → list of messages.

    FS mode: returns empty ``InboxResult`` (caller routes to relay_ops).
    HTTP mode: returns messages from server, or empty on error.
    """
    if not is_http_mode():
        return InboxResult()

    canonical = resolve_canonical_inbox_name(role)
    if not canonical:
        return InboxResult()

    status, parsed, err, rl_remaining = _http_call(
        "GET",
        f"/relay/{canonical}",
        bearer=bearer,
        params={"unread_only": str(unread_only).lower(), "limit": limit},
    )

    result = InboxResult()

    if err:
        result.transport_error = True
        if status == 429:
            result.rate_limited = True
        return result

    if parsed is None or not isinstance(parsed, dict):
        result.transport_error = True
        return result

    if 200 <= status < 300:
        msgs = parsed.get("messages", [])
        if isinstance(msgs, list):
            result.extend(msgs)
        result.has_more = bool(parsed.get("has_more", False))
        result.transport_error = False
        result.rate_limited = bool(parsed.get("rate_limited", False)) or (rl_remaining == 0)
        return result

    # Non-2xx with parseable body
    result.transport_error = True
    if status == 429:
        result.rate_limited = True
    return result


def post_relay(payload: dict, *, bearer: Optional[str] = None) -> dict:
    """POST /relay/{to} → send a relay envelope.

    FS mode: returns ``{"sent": False, "error": _FS_MARKER}``.
    HTTP mode: returns ``{"sent": True, "id": ...}`` on 2xx or
    ``{"sent": False, "error": ...}`` on failure.

    Relay-sender anchor stone: when ``NUCLEUS_RELAY_SENDER_ANCHOR=1``,
    stamps the payload with ``sender_anchor`` from the session registry
    before posting. No-op when the flag is OFF (byte-identical).
    """
    if not is_http_mode():
        return {"sent": False, "error": _FS_MARKER}

    # Relay-sender anchor stone: stamp payload with session anchor
    from ..sessions.relay_sender_anchor import stamp_sender_anchor
    payload = stamp_sender_anchor(payload)

    recipient = payload.get("to") or payload.get("recipient") or ""
    if not recipient:
        return {"sent": False, "error": "missing_to_field"}

    canonical = resolve_canonical_inbox_name(recipient)

    # Client-side body cap (matches server 413 guard)
    body_bytes = json.dumps(payload).encode("utf-8")
    if len(body_bytes) > _max_body_bytes():
        return {"sent": False, "error": "body_too_large"}

    # Idempotency-Key: use payload id if provided, else mint UUID
    idem_key = payload.get("id") or str(uuid4())

    # Extra headers from payload
    extra_headers: Dict[str, str] = {"Idempotency-Key": str(idem_key)}
    if payload.get("from_session_id"):
        extra_headers["X-Sender-Session-Id"] = str(payload["from_session_id"])

    # Build a custom _http_call with extra headers
    # We inline the HTTP call here to pass extra headers cleanly
    url = _base_url() + f"/relay/{canonical}"
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {_bearer_or_raise(bearer)}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        **extra_headers,
    }
    req = urllib.request.Request(
        url, data=body_bytes, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
        try:
            parsed = json.loads(raw) if raw else None
        except (json.JSONDecodeError, ValueError):
            parsed = None
    except (urllib.error.URLError, OSError, TimeoutError):
        return {"sent": False, "error": "transport_failure"}

    if 200 <= status < 300:
        # message_id wins over id (server-canonical)
        msg_id = ""
        if parsed and isinstance(parsed, dict):
            msg_id = parsed.get("message_id") or parsed.get("id") or ""
        if not msg_id:
            msg_id = str(idem_key)
        return {"sent": True, "id": msg_id}

    return {"sent": False, "error": status}


def mark_seen(
    role: str,
    message_ids: List[str],
    *,
    bearer: Optional[str] = None,
) -> dict:
    """POST /relay/{canonical}/ack → mark messages as seen.

    FS mode: returns ``{"acked": 0, "failed": 0, "error": _FS_MARKER}``.
    HTTP mode: returns ``{"acked": N, "failed": N}``.
    Empty list short-circuits without HTTP call.
    """
    if not message_ids:
        return {"acked": 0, "failed": 0}

    if not is_http_mode():
        return {"acked": 0, "failed": 0, "error": _FS_MARKER}

    canonical = resolve_canonical_inbox_name(role)
    if not canonical:
        return {"acked": 0, "failed": len(message_ids)}

    status, parsed, err, _ = _http_call(
        "POST",
        f"/relay/{canonical}/ack",
        bearer=bearer,
        body={"message_ids": message_ids},
    )

    if err:
        return {
            "acked": 0,
            "failed": len(message_ids),
            "error": err,
        }

    if 200 <= status < 300:
        if parsed and isinstance(parsed, dict):
            return {
                "acked": int(parsed.get("acked", len(message_ids))),
                "failed": int(parsed.get("failed", 0)),
            }
        return {"acked": len(message_ids), "failed": 0}

    return {
        "acked": 0,
        "failed": len(message_ids),
        "error": status,
    }


def get_status(canonical: str, *, bearer: Optional[str] = None) -> dict:
    """GET /relay/{canonical}/status → best-effort status.

    FS mode: returns ``{"ok": False, "error": _FS_MARKER}``.
    HTTP mode: returns server body merged with ``ok: True`` on 2xx or
    ``{"ok": False, "error": <status>}`` on failure.
    """
    if not is_http_mode():
        return {"ok": False, "error": _FS_MARKER}

    resolved = resolve_canonical_inbox_name(canonical)
    if not resolved:
        return {"ok": False, "error": "missing_role"}

    status, parsed, err, _ = _http_call(
        "GET",
        f"/relay/{resolved}/status",
        bearer=bearer,
    )

    if err:
        return {"ok": False, "error": err}

    if 200 <= status < 300 and parsed and isinstance(parsed, dict):
        result = dict(parsed)
        result["ok"] = True
        return result

    return {"ok": False, "error": status}
