"""Coordination event capture loop — Phase B sidecar.

Per .brain/research/2026-04-28_tier_architecture/09_cloud_substrate_and_router_strategy.md
§5: every Nucleus coordination decision (relay, skill pick, policy hit,
concurrence, founder override) is logged as a structured event. Schema is
router-training-ready from day-1. Capture is automatic byproduct of normal
Nucleus usage; zero extra effort from users.

Append-only with stitching: corrections/verdicts/outcomes reference the
original event by id; periodic batch jobs stitch them at training-corpus
build time. No destructive writes.

Build target validation gate (per §5.5): ≥5,000 events before fine-tuning
a router on this corpus.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Recognized event types. Strict allowlist — caller passing an unknown type
# gets a ValueError so we don't silently accumulate junk in the ledger.
EVENT_TYPES = frozenset({
    "relay_fired",
    "relay_processed",  # receive-side: message marked read by recipient (closes ack-latency loop)
    "skill_picked",
    "policy_invoked",
    "concurrence_event",
    "founder_override",
    "drift_detected",
    "cross_session_handoff",
    "correction",       # back-stitch: another agent / human corrected a prior choice
    "founder_verdict",  # back-stitch: founder approved/disagreed/commented
    "outcome",          # back-stitch: retroactively-known outcome of a prior choice
})

_KILLSWITCH_ENV = "NUCLEUS_COORD_EVENTS_DISABLED"
_LEDGER_FILENAME = "coordination_events.jsonl"

_write_lock = threading.Lock()


def _resolve_brain_path() -> Path:
    """Resolve brain path via standard runtime resolver.

    Honors NUCLEUS_BRAIN_PATH env (per cross-worktree feedback memory).
    Delegates to runtime.common.get_brain_path() for the canonical lookup.
    """
    env = os.environ.get("NUCLEUS_BRAIN_PATH")
    if env:
        return Path(env)
    from .common import get_brain_path
    return get_brain_path()


def _ledger_path() -> Path:
    return _resolve_brain_path() / "ledger" / _LEDGER_FILENAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_event_id() -> str:
    """coord_<YYYYMMDD>_<HHMMSS>_<8hex> — chronologically sortable, low collision risk."""
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    suffix = secrets.token_hex(4)
    return f"coord_{ts}_{suffix}"


def _append(record: dict[str, Any]) -> None:
    """Atomic-line append with thread-lock. ~ms latency."""
    if os.environ.get(_KILLSWITCH_ENV):
        return
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with _write_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass  # network FS may not support fsync; not fatal


def emit(
    event_type: str,
    *,
    agent: str,
    session_id: str,
    context_summary: str,
    available_options: Iterable[dict[str, str]] = (),
    chosen_option: str = "",
    reasoning_summary: str = "",
    tags: Iterable[str] = (),
) -> str:
    """Emit a coordination event. Returns event id for back-stitching.

    Per §5.2 schema. Validates event_type strictly. Returns "" if killswitch
    set or write fails (caller should not break the action loop on emit
    failure).
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown event_type: {event_type!r}")
    if os.environ.get(_KILLSWITCH_ENV):
        return ""
    eid = _new_event_id()
    record = {
        "id": eid,
        "timestamp": _now_iso(),
        "event_type": event_type,
        "agent": agent,
        "session_id": session_id,
        "context_summary": context_summary,
        "available_options": list(available_options),
        "chosen_option": chosen_option,
        "reasoning_summary": reasoning_summary,
        "correction": None,
        "founder_verdict": None,
        "outcome_known_at": None,
        "outcome": None,
        "tags": list(tags),
    }
    try:
        _append(record)
    except OSError:
        return ""
    return eid


def stitch_correction(event_id: str, *, correction: dict[str, Any]) -> str:
    """Append a correction record referencing the original event."""
    return _stitch(event_id, "correction", correction)


def stitch_verdict(event_id: str, *, verdict: dict[str, Any]) -> str:
    """Append a founder verdict referencing the original event."""
    return _stitch(event_id, "founder_verdict", verdict)


def stitch_outcome(event_id: str, *, outcome: dict[str, Any]) -> str:
    """Append outcome (known retroactively) referencing the original event."""
    return _stitch(event_id, "outcome", outcome)


def _stitch(event_id: str, kind: str, payload: dict[str, Any]) -> str:
    if os.environ.get(_KILLSWITCH_ENV):
        return ""
    eid = _new_event_id()
    record = {
        "id": eid,
        "timestamp": _now_iso(),
        "event_type": kind,
        "stitches_to": event_id,
        "payload": payload,
    }
    try:
        _append(record)
    except OSError:
        return ""
    return eid


_TRAINING_THRESHOLD = 5000


def stats() -> dict[str, Any]:
    """Quick read of the ledger for §5.5 validation gate checks."""
    path = _ledger_path()
    if not path.exists():
        return {
            "ok": True,
            "n_events": 0,
            "n_by_type": {},
            "ledger_path": str(path),
            "router_training_threshold": _TRAINING_THRESHOLD,
            "training_ready": False,
        }
    counts: dict[str, int] = {}
    n = 0
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = rec.get("event_type", "?")
                counts[t] = counts.get(t, 0) + 1
                n += 1
    except OSError:
        return {
            "ok": False,
            "n_events": n,
            "n_by_type": counts,
            "ledger_path": str(path),
            "router_training_threshold": _TRAINING_THRESHOLD,
            "training_ready": n >= _TRAINING_THRESHOLD,
        }
    return {
        "ok": True,
        "n_events": n,
        "n_by_type": counts,
        "ledger_path": str(path),
        "router_training_threshold": _TRAINING_THRESHOLD,
        "training_ready": n >= _TRAINING_THRESHOLD,
    }
