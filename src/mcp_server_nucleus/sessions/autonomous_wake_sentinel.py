"""v0.3.0 — FallbackChainError → sentinel relay writer.

Per cc-peer 2026-06-09T11:55Z sketch SIGNOFF (Q4 STRONG-CONCUR):
when post_relay_to_role raises FallbackChainError, write a sentinel
JSON to .brain/relay/claude_code_operator_assistant/ so the operator
sees the failure on next op-assistant session surface.

Per cc-peer augmentation, sentinel JSON MUST include:
- error_class_name (str)
- original_relay_filenames (list[str]) — so operator can re-fire manually
- truncated_subjects (list[str]) — ≤80 chars each
- NO bearer, NO cookies, NO full body content

Per cc-peer test floor:
- test_sentinel_does_not_leak_bearer_or_body
- test_sentinel_filename_is_canonical_pattern

PushNotification REJECTED (operator stepped-away autonomous-mandate
posture). Sentinel-relay is the ONLY primary failure channel.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("nucleus.autonomous_wake_sentinel")

_OP_ASSISTANT_INBOX_NAME = "claude_code_operator_assistant"
_SUBJECT_TRUNCATE = 80


def _utc_ts() -> str:
    """20260609T120000Z format for canonical filename."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_failure_sentinel(
    *,
    role: str,
    error_class_name: str,
    original_relay_filenames: List[str],
    relay_subjects: List[str],
    brain_root: Path,
    timestamp: Optional[str] = None,
) -> Path:
    """Write sentinel JSON to op-assistant inbox; return written path.

    `brain_root` is the .brain/ directory absolute path. Inbox is
    brain_root / "relay" / claude_code_operator_assistant /.

    Truncates subjects to 80 chars each (per cc-peer locked contract).
    Does NOT log relay subject content (only canonical filename pattern).
    """
    if not role:
        raise ValueError("role required")
    if not error_class_name:
        raise ValueError("error_class_name required")
    if not brain_root:
        raise ValueError("brain_root required")

    ts = timestamp if timestamp is not None else _utc_ts()
    inbox = brain_root / "relay" / _OP_ASSISTANT_INBOX_NAME
    inbox.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{ts}_cc_tb_autonomous_wake_FAILED_role_{role}_err_{error_class_name}.json"
    )
    path = inbox / filename

    truncated_subjects = [
        (subj or "")[:_SUBJECT_TRUNCATE] for subj in (relay_subjects or [])
    ]

    body = {
        "schema": "relay/v1",
        "id": f"sentinel_{ts}_cc_tb_autonomous_wake_FAILED_{role}",
        "ts": _utc_ts_iso(ts),
        "from": "cc_tb",
        "from_role": "tb",
        "to": _OP_ASSISTANT_INBOX_NAME,
        "to_role": "operator_assistant",
        "subject": (
            f"[AUTONOMOUS-WAKE FAILED] role={role} err={error_class_name}"
        ),
        "priority": "high",
        "body": {
            "kind": "autonomous_wake_failure_sentinel",
            "role": role,
            "error_class_name": error_class_name,
            "original_relay_filenames": list(original_relay_filenames or []),
            "truncated_subjects": truncated_subjects,
            "remediation_hint": (
                "Relay file(s) still persisted in inbox. Re-fire manually "
                "via direct CC session OR re-queue via nucleus_relay MCP "
                "tool. No bearer / body content included by design."
            ),
        },
    }

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2))
    tmp.replace(path)

    logger.info(
        "autonomous_wake_sentinel: written role=%s err=%s relays=%d",
        role, error_class_name, len(original_relay_filenames or []),
    )
    return path


def _utc_ts_iso(compact_ts: str) -> str:
    """Convert 20260609T120000Z → 2026-06-09T12:00:00Z."""
    if len(compact_ts) >= 16:
        return (
            f"{compact_ts[0:4]}-{compact_ts[4:6]}-{compact_ts[6:8]}T"
            f"{compact_ts[9:11]}:{compact_ts[11:13]}:{compact_ts[13:15]}Z"
        )
    return compact_ts


__all__ = [
    "write_failure_sentinel",
]
