"""v0.3.x — `nucleus_relay` tool-use forwarder with 6 LLM-agency mitigations.

Per op-assistant 2026-06-09T17:50Z PRE-WIRE + cc-peer 18:00Z locked
contract Q4: substrate-injected nucleus_relay tool gives autonomous-wake
LLM the ability to write arbitrary content to fleet inboxes. The 6
defense-in-depth mitigations (cc-peer LOCKED — load-bearing trio is
(b)+(c)+(e), do NOT ship without all three):

  (a) Recipient ENUM-constrained in tool input_schema (autonomous_wake.py)
  (b) Subject prefix '[AUTONOMOUS]' forced (this module)
  (c) Sender-role LOCKED at helper call site, NOT from LLM input
      (this module signature requires sender_role kwarg from caller)
  (d) Body length cap 4096 chars + truncation flag (this module)
  (e) Rate limit 20/hr per role disk-persistent (this module)
  (f) Audit log .brain/ledger/autonomous_relay_posts.jsonl with
      body_hash NOT body content (this module)

Body shape per cc-peer Q5 LOCKED:
  - str → passthrough
  - dict/list → json.dumps(body, ensure_ascii=False)
  - None → warn + skip
  - unsupported type → warn + skip

Bearer per cc-peer Q3 LOCKED-COMPATIBLE: read ~/.tb/relay_token_<sender_role>
at call time; if absent, write failure sentinel + skip POST (lazy check).
Startup-time check lives in autonomous_wake_loader.

Pseudonymity discipline:
- Bearer token VALUE never logged at any level
- Body content NEVER logged (audit captures body_hash + body_chars only)
- Recipient + subject (truncated [:80]) logged for ops visibility
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.relay_post_helper")

# Mitigation (d): body length cap per cc-peer locked contract
_BODY_LENGTH_CAP = 4096

# Mitigation (b): forced subject prefix per cc-peer locked contract
_SUBJECT_PREFIX = "[AUTONOMOUS]"

# Mitigation (e): rate limit per cc-peer locked contract
_RATE_LIMIT_PER_HOUR = 20
_RATE_LIMIT_WINDOW_S = 3600.0
_RATE_LIMIT_DIR = Path.home() / ".tb"

# Audit log path
_AUDIT_LOG_DIR_REL = "ledger"
_AUDIT_LOG_FILE_REL = "autonomous_relay_posts.jsonl"

# OCI relay-as-a-service endpoint
_OCI_RELAY_BASE = "https://relay.nucleusos.dev/relay"
_OCI_HTTP_TIMEOUT_S = 15.0

# Subject truncation for log/audit visibility (NOT for transport)
_SUBJECT_LOG_TRUNCATE = 80


class RelayPostError(RuntimeError):
    """Raised when the helper cannot complete a post (config-level only).

    Per-call best-effort failures (transport timeout, OCI 4xx) log a
    warning + return False; they do NOT raise.
    """


def _bearer_file(sender_role: str) -> Path:
    return Path.home() / ".tb" / f"relay_token_{sender_role}"


def _rate_limit_file(sender_role: str) -> Path:
    return _RATE_LIMIT_DIR / f"relay_post_rate_{sender_role}.json"


def _read_rate_state(sender_role: str) -> list:
    """Return list of monotonic timestamps within window. Empty on missing."""
    path = _rate_limit_file(sender_role)
    try:
        raw = path.read_text()
        parsed = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [t for t in parsed if isinstance(t, (int, float))]


def _write_rate_state_atomic(sender_role: str, timestamps: list) -> None:
    _RATE_LIMIT_DIR.mkdir(mode=0o700, exist_ok=True)
    path = _rate_limit_file(sender_role)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(timestamps))
    tmp.chmod(0o600)
    tmp.replace(path)


def _check_and_record_rate(sender_role: str) -> bool:
    """Mitigation (e): atomic check + record. True if under rate limit."""
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW_S
    state = _read_rate_state(sender_role)
    pruned = [t for t in state if t >= cutoff]
    if len(pruned) >= _RATE_LIMIT_PER_HOUR:
        logger.warning(
            "relay_post: rate limit exceeded role=%s posts_in_window=%d cap=%d",
            sender_role, len(pruned), _RATE_LIMIT_PER_HOUR,
        )
        return False
    pruned.append(now)
    _write_rate_state_atomic(sender_role, pruned)
    return True


def _coerce_body_to_string(body: Any) -> Optional[str]:
    """Mitigation Q5: body shape handler. None on warn-skip cases."""
    if isinstance(body, str):
        return body
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii=False)
    if body is None:
        logger.warning("relay_post: body None — skip")
        return None
    logger.warning(
        "relay_post: body unsupported type=%s — skip",
        type(body).__name__,
    )
    return None


def _force_subject_prefix(subject: str) -> str:
    """Mitigation (b): force [AUTONOMOUS] prefix if missing."""
    if not isinstance(subject, str):
        subject = ""
    s = subject.strip()
    if s.startswith(_SUBJECT_PREFIX):
        return s
    return f"{_SUBJECT_PREFIX} {s}" if s else _SUBJECT_PREFIX


def _cap_body_length(body_str: str) -> tuple[str, bool]:
    """Mitigation (d): truncate at cap. Returns (body, truncated_flag)."""
    if len(body_str) <= _BODY_LENGTH_CAP:
        return body_str, False
    return body_str[:_BODY_LENGTH_CAP], True


def _audit_log_entry(
    *,
    brain_root: Path,
    sender_role: str,
    recipient_role: str,
    subject: str,
    body_str: str,
    truncated: bool,
    tool_use_block_id: str,
    posted: bool,
    error_class: str = "",
) -> None:
    """Mitigation (f): append-only audit at .brain/ledger/autonomous_relay_posts.jsonl.

    Body CONTENT never written — only sha256 hash + char count + truncation flag.
    Pseudonymity preserved.
    """
    try:
        ledger_dir = brain_root / _AUDIT_LOG_DIR_REL
        ledger_dir.mkdir(parents=True, exist_ok=True)
        path = ledger_dir / _AUDIT_LOG_FILE_REL
        body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
        entry = {
            "ts": time.time(),
            "sender_role": sender_role,
            "recipient_role": recipient_role,
            "subject_first_80": subject[:_SUBJECT_LOG_TRUNCATE],
            "body_hash": body_hash,
            "body_chars": len(body_str),
            "truncated": truncated,
            "tool_use_block_id": tool_use_block_id,
            "posted": posted,
            "error_class": error_class,
        }
        with path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        # Audit failure must NEVER block the forward — log + continue
        logger.warning(
            "relay_post: audit write failed err=%s", type(exc).__name__,
        )


def post_nucleus_relay_block(
    *,
    block_input: Dict[str, Any],
    sender_role: str,
    block_id: str,
    brain_root: Path,
) -> bool:
    """Forward a single nucleus_relay tool_use block to OCI relay endpoint.

    Returns True on POST success; False on best-effort failure (rate limit
    exceeded / bearer missing / OCI rejected / body unsupported). Never
    raises (cc-peer + op-assistant: best-effort forward; substrate already
    succeeded by the time we get here).

    `sender_role` is LOCKED at this call site — taken from the running
    role's name (NOT from block_input). Mitigation (c) per cc-peer Q4.
    """
    if not sender_role:
        logger.warning("relay_post: sender_role required — skip")
        return False
    if not isinstance(block_input, dict):
        logger.warning("relay_post: block_input not dict — skip")
        return False

    recipient = block_input.get("recipient")
    raw_subject = block_input.get("subject") or ""
    raw_body = block_input.get("body")
    raw_priority = block_input.get("priority") or "normal"

    if not isinstance(recipient, str) or not recipient:
        logger.warning("relay_post: missing recipient — skip")
        return False

    # Mitigation (b): force [AUTONOMOUS] prefix
    subject = _force_subject_prefix(raw_subject)

    # Mitigation Q5: body shape
    body_str = _coerce_body_to_string(raw_body)
    if body_str is None:
        # Audit the skip
        _audit_log_entry(
            brain_root=brain_root,
            sender_role=sender_role,
            recipient_role=recipient,
            subject=subject,
            body_str="",
            truncated=False,
            tool_use_block_id=block_id,
            posted=False,
            error_class="body_shape_unsupported",
        )
        return False

    # Mitigation (d): body length cap
    body_str, truncated = _cap_body_length(body_str)

    # Mitigation (e): rate limit
    if not _check_and_record_rate(sender_role):
        _audit_log_entry(
            brain_root=brain_root,
            sender_role=sender_role,
            recipient_role=recipient,
            subject=subject,
            body_str=body_str,
            truncated=truncated,
            tool_use_block_id=block_id,
            posted=False,
            error_class="rate_limit_exceeded",
        )
        return False

    # cc-peer Q3 lazy check: bearer file existence
    bearer_path = _bearer_file(sender_role)
    try:
        bearer = bearer_path.read_text().strip()
    except OSError:
        logger.warning(
            "relay_post: bearer file missing role=%s — skip",
            sender_role,
        )
        _audit_log_entry(
            brain_root=brain_root,
            sender_role=sender_role,
            recipient_role=recipient,
            subject=subject,
            body_str=body_str,
            truncated=truncated,
            tool_use_block_id=block_id,
            posted=False,
            error_class="bearer_missing",
        )
        return False

    if not bearer:
        logger.warning(
            "relay_post: bearer empty role=%s — skip", sender_role,
        )
        return False

    # POST to OCI relay endpoint
    try:
        try:
            from curl_cffi import requests as _curl_requests
        except ImportError:
            # Fallback to stdlib if curl_cffi unavailable
            import urllib.request
            import urllib.error
            url = f"{_OCI_RELAY_BASE}/{recipient}"
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "sender": sender_role,
                    "recipient": recipient,
                    "subject": subject,
                    "body": body_str,
                    "priority": raw_priority if raw_priority in ("low", "normal", "high") else "normal",
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {bearer}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=_OCI_HTTP_TIMEOUT_S) as resp:
                    status = resp.status
            except urllib.error.HTTPError as exc:
                status = exc.code
        else:
            url = f"{_OCI_RELAY_BASE}/{recipient}"
            resp = _curl_requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {bearer}",
                    "Content-Type": "application/json",
                },
                json={
                    "sender": sender_role,
                    "recipient": recipient,
                    "subject": subject,
                    "body": body_str,
                    "priority": raw_priority if raw_priority in ("low", "normal", "high") else "normal",
                },
                timeout=_OCI_HTTP_TIMEOUT_S,
            )
            status = resp.status_code
    except Exception as exc:
        logger.warning(
            "relay_post: transport class=%s role=%s recipient=%s",
            type(exc).__name__, sender_role, recipient,
        )
        _audit_log_entry(
            brain_root=brain_root,
            sender_role=sender_role,
            recipient_role=recipient,
            subject=subject,
            body_str=body_str,
            truncated=truncated,
            tool_use_block_id=block_id,
            posted=False,
            error_class=type(exc).__name__,
        )
        return False

    posted = 200 <= status < 300
    if posted:
        logger.info(
            "relay_post: forwarded role=%s recipient=%s subject=%s",
            sender_role, recipient, subject[:_SUBJECT_LOG_TRUNCATE],
        )
    else:
        logger.warning(
            "relay_post: OCI rejected status=%d role=%s recipient=%s",
            status, sender_role, recipient,
        )

    _audit_log_entry(
        brain_root=brain_root,
        sender_role=sender_role,
        recipient_role=recipient,
        subject=subject,
        body_str=body_str,
        truncated=truncated,
        tool_use_block_id=block_id,
        posted=posted,
        error_class="" if posted else f"oci_status_{status}",
    )
    return posted


__all__ = [
    "RelayPostError",
    "post_nucleus_relay_block",
]
