"""POST /relay/{recipient} webhook — http_transport stage-2.

Implements the envelope contract from .brain/plans/a2a_envelope_alignment.md
(merged in PR #198 at sha a4c90317). Maps 1:1 to runtime.relay_ops.relay_post.

DEVIATION FROM CONTRACT: auth uses NUCLEUS_RELAY_TOKEN_MAP (JSON env var
{token: sender_owner}) instead of nucleus_telemetry.ipc_tokens. The IPC
provider issues single-use tokens (consume_token() is one-shot), which is
incompatible with webhook auth where the same caller fires many requests.
Per-deployment env-token map is the pragmatic shape; ipc_provider integration
revisits when the cross-machine deploy lands and a real token-rotation story
exists. Filed via [DEVIATION] relay before merge.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp_server_nucleus.runtime import relay_ops

# ── Config ────────────────────────────────────────────────────────────

MAX_BODY_BYTES = int(os.environ.get("NUCLEUS_RELAY_MAX_BODY", "65536"))  # 64 KiB
MAX_SUBJECT_LEN = 256
RATE_PER_MIN = int(os.environ.get("NUCLEUS_RELAY_RATE_PER_MIN", "60"))
RATE_BURST = int(os.environ.get("NUCLEUS_RELAY_RATE_BURST", "10"))
RATE_PER_RECIPIENT = int(os.environ.get("NUCLEUS_RELAY_RATE_PER_RECIPIENT", "30"))
IDEMPOTENCY_TTL_S = 24 * 3600
VALID_PRIORITIES = {"low", "normal", "high", "urgent", "critical"}
REQUIRED_FIELDS = ("subject", "body", "sender")

# ── Prompt-injection scan ─────────────────────────────────────────────────────

logger = logging.getLogger("nucleus.relay")

# Default hardcoded patterns — v1 intentional scope: case-insensitive substring match.
_DEFAULT_INJECTION_PATTERNS: List[str] = [
    "system override",
    "ignore previous instructions",
    "act as if you are",
    "<|im_start|>system",
]


def scan_injection_patterns(body: str) -> tuple[bool, str | None]:
    """Scan *body* for known prompt-injection patterns.

    Returns ``(True, pattern_name)`` on match, ``(False, None)`` if clean.

    Extensible via env var ``NUCLEUS_INJECTION_PATTERNS`` (comma-separated
    additional patterns, read at call time so tests can monkeypatch the env
    without module reload).
    """
    body_lower = body.lower()
    patterns = list(_DEFAULT_INJECTION_PATTERNS)
    extra = os.environ.get("NUCLEUS_INJECTION_PATTERNS", "")
    if extra:
        patterns.extend(p.strip() for p in extra.split(",") if p.strip())
    for pattern in patterns:
        if pattern.lower() in body_lower:
            return True, pattern
    return False, None


# ── In-memory state (per-process; OK for single-tenant or sticky-session deploys) ──

# token-bucket per (token, scope_key); scope_key is "" for global, or recipient name
_buckets: Dict[Tuple[str, str], deque] = defaultdict(deque)
# idempotency: (token, idem_key) -> (response_dict, ts)
_idem_cache: Dict[Tuple[str, str], Tuple[Dict[str, Any], float]] = {}


def _load_token_map() -> Dict[str, str]:
    """Parse NUCLEUS_RELAY_TOKEN_MAP env var. Returns {token: owner_sender}."""
    raw = os.environ.get("NUCLEUS_RELAY_TOKEN_MAP", "")
    if not raw:
        return {}
    try:
        m = json.loads(raw)
        return {str(k): str(v) for k, v in m.items()} if isinstance(m, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _check_rate(token: str, recipient: str, now: float) -> Tuple[bool, int, int]:
    """Sliding-window rate check. Returns (allowed, remaining_global, retry_after_s)."""
    capacity = RATE_PER_MIN + RATE_BURST
    window_s = 60
    bucket_global = _buckets[(token, "")]
    bucket_recipient = _buckets[(token, recipient)]

    cutoff = now - window_s
    while bucket_global and bucket_global[0] < cutoff:
        bucket_global.popleft()
    while bucket_recipient and bucket_recipient[0] < cutoff:
        bucket_recipient.popleft()

    if len(bucket_global) >= capacity:
        retry = max(1, int(window_s - (now - bucket_global[0])))
        return False, 0, retry
    if len(bucket_recipient) >= RATE_PER_RECIPIENT:
        retry = max(1, int(window_s - (now - bucket_recipient[0])))
        return False, capacity - len(bucket_global), retry

    bucket_global.append(now)
    bucket_recipient.append(now)
    return True, capacity - len(bucket_global), 0


def _idem_get(token: str, key: str, now: float) -> Optional[Dict[str, Any]]:
    if not key:
        return None
    entry = _idem_cache.get((token, key))
    if not entry:
        return None
    response, ts = entry
    if now - ts > IDEMPOTENCY_TTL_S:
        _idem_cache.pop((token, key), None)
        return None
    return response


def _idem_set(token: str, key: str, response: Dict[str, Any], now: float) -> None:
    if not key:
        return
    _idem_cache[(token, key)] = (response, now)
    # Opportunistic eviction
    if len(_idem_cache) > 10_000:
        cutoff = now - IDEMPOTENCY_TTL_S
        for k in [k for k, (_, ts) in _idem_cache.items() if ts < cutoff]:
            _idem_cache.pop(k, None)


def get_rate_limit_headers(token: str, recipient: str, now: float) -> Dict[str, str]:
    """Build X-RateLimit-* headers for the current token/recipient state without consuming quota."""
    capacity = RATE_PER_MIN + RATE_BURST
    window_s = 60
    bucket_global = _buckets[(token, "")]
    cutoff = now - window_s
    while bucket_global and bucket_global[0] < cutoff:
        bucket_global.popleft()
    remaining = max(0, capacity - len(bucket_global))
    return {
        "X-RateLimit-Limit": str(RATE_PER_MIN),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(now + window_s)),
    }


def _err(http_status: int, code: str, reason: str, retry_after_s: Optional[int] = None,
         rate_headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    body = {"sent": False, "error": code, "reason": reason, "retry_after_s": retry_after_s}
    headers = dict(rate_headers or {})
    if retry_after_s is not None and http_status == 429:
        headers["Retry-After"] = str(retry_after_s)
    return JSONResponse(body, status_code=http_status, headers=headers)


async def post_relay(request: Request) -> JSONResponse:
    """POST /relay/{recipient} — envelope contract per a2a_envelope_alignment.md."""
    now = time.time()
    recipient_raw = request.path_params.get("recipient", "")

    # Auth — Bearer token from Authorization header
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return _err(401, "auth_missing", "Authorization: Bearer <token> header required")
    token = auth_header[7:].strip()
    token_map = _load_token_map()
    if not token or token not in token_map:
        return _err(401, "auth_missing", "Token not recognised")
    token_owner = token_map[token]

    # Recipient validation (allow-list style — defer to relay_ops._sanitize_recipient)
    try:
        recipient = relay_ops._sanitize_recipient(recipient_raw)
    except ValueError as e:
        return _err(400, "invalid_recipient", str(e))

    # Body parse + size cap
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return _err(413, "body_too_large", f"Request body exceeds {MAX_BODY_BYTES} bytes")
    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError as e:
        return _err(400, "schema_violation", f"Invalid JSON: {e}")
    if not isinstance(payload, dict):
        return _err(400, "schema_violation", "Body must be a JSON object")

    # Schema validation
    for f in REQUIRED_FIELDS:
        if f not in payload or payload[f] in (None, ""):
            return _err(400, "schema_violation", f"Required field missing: {f}")
    subject = payload["subject"]
    if not isinstance(subject, str) or len(subject) > MAX_SUBJECT_LEN or "\n" in subject:
        return _err(400, "schema_violation",
                    f"subject must be a string ≤{MAX_SUBJECT_LEN} chars, no newlines")
    body_field = payload["body"]
    if not isinstance(body_field, str):
        return _err(400, "schema_violation", "body must be a string")
    sender = payload["sender"]
    if not isinstance(sender, str):
        return _err(400, "schema_violation", "sender must be a string")
    priority = payload.get("priority", "normal")
    if priority not in VALID_PRIORITIES:
        return _err(400, "schema_violation",
                    f"priority must be one of {sorted(VALID_PRIORITIES)}")

    # Prompt-injection scan (runs after body-field type validation)
    injected, matched_pattern = scan_injection_patterns(body_field)
    if injected:
        logger.warning(
            "injection blocked sender=%s pattern=%s", token_owner, matched_pattern
        )
        # Include rate-limit headers even on 403 so clients can inspect throttle state.
        # Rate counter not yet charged at this point; compute tentative headers.
        _tentative_remaining = RATE_PER_MIN + RATE_BURST - len(_buckets[(token, "")])
        _injection_rate_headers = {
            "X-RateLimit-Limit": str(RATE_PER_MIN),
            "X-RateLimit-Remaining": str(max(0, _tentative_remaining)),
            "X-RateLimit-Reset": str(int(now + 60)),
        }
        return JSONResponse(
            {"sent": False, "error": "injection_detected", "pattern": matched_pattern},
            status_code=403,
            headers=_injection_rate_headers,
        )

    # Sender-token binding
    if sender != token_owner:
        return _err(403, "sender_mismatch",
                    f"body.sender={sender!r} does not match token owner={token_owner!r}")

    # Idempotency replay check
    idem_key = request.headers.get("idempotency-key", "")
    cached = _idem_get(token, idem_key, now)
    if cached is not None:
        return _err(409, "idempotency_replay",
                    f"Idempotency-Key already used; original message_id={cached.get('message_id')}")

    # Rate limit
    allowed, remaining, retry_after = _check_rate(token, recipient, now)
    rate_headers = get_rate_limit_headers(token, recipient, now)
    if not allowed:
        return _err(429, "rate_limited", "Rate limit exceeded",
                    retry_after_s=retry_after, rate_headers=rate_headers)

    # X-Sender-Session-Id header overrides body
    from_session_id = request.headers.get("x-sender-session-id") or payload.get("from_session_id")

    # Dispatch to existing relay_post — no new write paths
    try:
        result = relay_ops.relay_post(
            to=recipient,
            subject=subject,
            body=body_field,
            priority=priority,
            context=payload.get("context"),
            sender=sender,
            to_session_id=payload.get("to_session_id"),
            from_session_id=from_session_id,
            in_reply_to=payload.get("in_reply_to"),
        )
    except ValueError as e:
        msg = str(e)
        if "artifact_refs" in msg or "shipped" in msg:
            return _err(422, "gate_rejected", msg, rate_headers=rate_headers)
        return _err(400, "schema_violation", msg, rate_headers=rate_headers)
    except OSError as e:
        return _err(503, "disk_unavailable", f"Relay write failed: {e}", rate_headers=rate_headers)

    # Successful response — 202 Accepted per contract
    response = {
        "sent": True,
        "message_id": result.get("message_id") or result.get("id"),
        "from": sender,
        "to": recipient,
        "subject": subject,
        "priority": priority,
        "path": result.get("path"),
    }
    _idem_set(token, idem_key, response, now)
    return JSONResponse(response, status_code=202, headers=rate_headers)


async def get_relay(request: Request) -> JSONResponse:
    """GET /relay/{recipient} — fetch inbox for recipient."""
    now = time.time()
    recipient_raw = request.path_params.get("recipient", "")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return _err(401, "auth_missing", "Authorization: Bearer <token> header required")
    token = auth_header[7:].strip()
    token_map = _load_token_map()
    if not token or token not in token_map:
        return _err(401, "auth_missing", "Token not recognised")

    try:
        recipient = relay_ops._sanitize_recipient(recipient_raw)
    except ValueError as e:
        return _err(400, "invalid_recipient", str(e))

    rate_headers = get_rate_limit_headers(token, recipient, now)

    try:
        limit = int(request.query_params.get("limit", "50"))
        limit = max(1, min(limit, 100))
    except (ValueError, TypeError):
        limit = 50
    unread_only = request.query_params.get("unread_only", "false").lower() in ("1", "true", "yes")

    try:
        result = relay_ops.relay_inbox(recipient=recipient, limit=limit, unread_only=unread_only)
    except Exception as e:
        return _err(503, "inbox_unavailable", f"Failed to read inbox: {e}", rate_headers=rate_headers)

    messages = result.get("messages", [])
    has_more = len(messages) >= limit
    return JSONResponse(
        {"messages": messages, "count": len(messages), "has_more": has_more},
        status_code=200,
        headers=rate_headers,
    )


async def ack_relay(request: Request) -> JSONResponse:
    """POST /relay/{recipient}/ack — acknowledge message_ids."""
    now = time.time()
    recipient_raw = request.path_params.get("recipient", "")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return _err(401, "auth_missing", "Authorization: Bearer <token> header required")
    token = auth_header[7:].strip()
    token_map = _load_token_map()
    if not token or token not in token_map:
        return _err(401, "auth_missing", "Token not recognised")

    try:
        recipient = relay_ops._sanitize_recipient(recipient_raw)
    except ValueError as e:
        return _err(400, "invalid_recipient", str(e))

    rate_headers = get_rate_limit_headers(token, recipient, now)

    raw = await request.body()
    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError as e:
        return _err(400, "schema_violation", f"Invalid JSON: {e}", rate_headers=rate_headers)
    if not isinstance(payload, dict):
        return _err(400, "schema_violation", "Body must be a JSON object", rate_headers=rate_headers)

    message_ids = payload.get("message_ids", [])
    if not isinstance(message_ids, list):
        return _err(400, "schema_violation", "message_ids must be a list", rate_headers=rate_headers)

    acked = 0
    failed = 0
    for mid in message_ids:
        try:
            result = relay_ops.relay_ack(str(mid), recipient=recipient)
            if result.get("acknowledged"):
                acked += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return JSONResponse({"acked": acked, "failed": failed}, status_code=200, headers=rate_headers)


async def get_relay_status(request: Request) -> JSONResponse:
    """GET /relay/{recipient}/status — check inbox stats for recipient."""
    now = time.time()
    recipient_raw = request.path_params.get("recipient", "")

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return _err(401, "auth_missing", "Authorization: Bearer <token> header required")
    token = auth_header[7:].strip()
    token_map = _load_token_map()
    if not token or token not in token_map:
        return _err(401, "auth_missing", "Token not recognised")

    try:
        recipient = relay_ops._sanitize_recipient(recipient_raw)
    except ValueError as e:
        return _err(400, "invalid_recipient", str(e))

    rate_headers = get_rate_limit_headers(token, recipient, now)

    try:
        status = relay_ops.relay_status()
        mailbox = status.get("mailboxes", {}).get(recipient, {})
        
        marketplace_data = None
        try:
            from mcp_server_nucleus.runtime.marketplace import lookup_by_address, ReputationSignals, TrustTier
            from datetime import datetime
            
            address = f"{recipient}@nucleus"
            card = lookup_by_address(address)
            if card is not None:
                metrics = ReputationSignals.compute_signals(address)
                tier_enum = TrustTier.evaluate(card, metrics)
                tier_badge = TrustTier.get_display_badge(tier_enum)
                
                last_seen = metrics.get("last_seen_at")
                last_interaction_at = None
                if last_seen:
                    try:
                        dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        last_interaction_at = dt.timestamp()
                    except Exception:
                        pass
                
                marketplace_data = {
                    "registered": True,
                    "tier": tier_badge,
                    "reputation_score": metrics.get("connection_count", 0),
                    "last_interaction_at": last_interaction_at
                }
        except Exception as e:
            logger.warning("Failed to lookup marketplace status for %s: %s", recipient, e)
            marketplace_data = None
        
        response = {
            "recipient": recipient,
            "queue_depth": mailbox.get("total", 0),
            "unread": mailbox.get("unread", 0),
            "marketplace": marketplace_data,
        }
        return JSONResponse(response, status_code=200, headers=rate_headers)
    except Exception as e:
        return _err(503, "status_unavailable", f"Failed to get relay status: {e}", rate_headers=rate_headers)


# Route registration helper
relay_route = Route("/relay/{recipient}", post_relay, methods=["POST"])
relay_get_route = Route("/relay/{recipient}", get_relay, methods=["GET"])
relay_ack_route = Route("/relay/{recipient}/ack", ack_relay, methods=["POST"])
relay_status_route = Route("/relay/{recipient}/status", get_relay_status, methods=["GET"])
