from __future__ import annotations
import inspect
import json
import logging
import os
import time
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from ..common import get_brain_path
from ..providers import coerce_to_tuple

logger = logging.getLogger("nucleus.relay")

_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")

def _is_shipped_artifact(ref: str) -> bool:
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    return bool(head) and not _RELAY_ID_RE.match(head)


# ── Two-axis instrumentation (override rate + skip rate) ──────────
#
# Every /to-cowork or /to-cc invocation logs one line to event_log.jsonl
# regardless of whether the relay fired. Skip events are the input to the
# v2.2 auto-fire judge decision: "should the cold-start gate have let this
# through?" Override rate is read-time analytics:
#   count(fire WHERE match=cold-start AND priority=high
#                 AND not question-to-peer) / count(fire)
# Classifications are written to a sidecar so event_log.jsonl stays
# append-only and tail-friendly.

EVENT_LOG_NAME = "event_log.jsonl"
SKIP_CLASSIFICATIONS_NAME = "skip_classifications.jsonl"

VALID_LOG_EVENTS = {"fire", "skip"}
VALID_CLASSIFICATIONS = {"should_have_fired", "rightly_skipped"}


def _event_log_path() -> Path:
    return _get_relay_dir() / EVENT_LOG_NAME


def _skip_classifications_path() -> Path:
    return _get_relay_dir() / SKIP_CLASSIFICATIONS_NAME


def relay_log_event(
    event: str,
    side: str,
    subject: str,
    tags: Optional[List[str]] = None,
    match_reason: str = "",
    priority: str = "normal",
    message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one fire/skip event to .brain/relay/event_log.jsonl.

    Called by /to-cowork and /to-cc skills on both code paths:
    - Fire path (after relay_post succeeds): event=fire, message_id=<id>
    - Skip path (cold-start gate trips): event=skip, message_id=None

    Best-effort: caller should not surface failures to the user. If the
    log can't be written, the relay fire/skip itself still happened.
    """
    if event not in VALID_LOG_EVENTS:
        return {"logged": False, "error": f"event must be one of {VALID_LOG_EVENTS}"}

    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        "side": side,
        "subject": subject,
        "tags": tags or [],
        "match_reason": match_reason,
        "priority": priority,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
    }

    try:
        path = _event_log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return {"logged": True, "event": event, "path": str(path.relative_to(get_brain_path()))}
    except Exception as e:
        return {"logged": False, "error": str(e)}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of dicts, skipping malformed lines."""
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def relay_skip_review(limit: int = 20) -> Dict[str, Any]:
    """Surface the most recent unclassified skip events for human review.

    Joins event_log.jsonl (event=skip) against skip_classifications.jsonl
    (by ts+subject as composite key — skips have no message_id). Returns
    the most recent N skips lacking a classification.
    """
    skips = [e for e in _read_jsonl(_event_log_path()) if e.get("event") == "skip"]
    classifications = _read_jsonl(_skip_classifications_path())
    classified_keys = {(c.get("ts"), c.get("subject")) for c in classifications}

    unclassified = [
        s for s in skips if (s.get("ts"), s.get("subject")) not in classified_keys
    ]
    # Most recent first
    unclassified.sort(key=lambda s: s.get("ts", ""), reverse=True)
    return {
        "total_skips": len(skips),
        "total_classified": len(classified_keys),
        "unclassified_count": len(unclassified),
        "unclassified": unclassified[:limit],
    }


def relay_classify_skip(
    ts: str,
    subject: str,
    classification: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a human classification of a skip event.

    Writes to .brain/relay/skip_classifications.jsonl. Sidecar (not inline
    rewrite) keeps event_log.jsonl strictly append-only.
    """
    if classification not in VALID_CLASSIFICATIONS:
        return {
            "classified": False,
            "error": f"classification must be one of {VALID_CLASSIFICATIONS}",
        }

    entry = {
        "ts": ts,
        "subject": subject,
        "classification": classification,
        "note": note or "",
        "classified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        path = _skip_classifications_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return {"classified": True, "classification": classification}
    except Exception as e:
        return {"classified": False, "error": str(e)}


def relay_event_stats() -> Dict[str, Any]:
    """Compute fire/skip/override counts and rates from event_log.jsonl.

    Used by the v2.2 gate decision and weekly review dashboards.
    Override rate = fires that bypassed cold-start via priority=high
    without question-to-peer in tags.
    """
    events = _read_jsonl(_event_log_path())
    fires = [e for e in events if e.get("event") == "fire"]
    skips = [e for e in events if e.get("event") == "skip"]

    cold_start_fires = [
        e for e in fires
        if "cold-start default" in (e.get("match_reason") or "")
    ]
    overrides = [
        e for e in cold_start_fires
        if e.get("priority") == "high"
        and "question-to-peer" not in (e.get("tags") or [])
    ]

    total_fires = len(fires)
    total_skips = len(skips)
    total_attempts = total_fires + total_skips

    override_rate = (len(overrides) / total_fires) if total_fires else 0.0
    skip_rate = (total_skips / total_attempts) if total_attempts else 0.0

    return {
        "total_fires": total_fires,
        "total_skips": total_skips,
        "total_attempts": total_attempts,
        "override_count": len(overrides),
        "override_rate": round(override_rate, 4),
        "skip_rate": round(skip_rate, 4),
    }





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .core import *
from .pending import *
from .briefing import *
from .watcher import *
from .daemon import *
