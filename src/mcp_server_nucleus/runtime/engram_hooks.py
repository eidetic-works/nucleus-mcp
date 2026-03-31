"""Engram Auto-Write Hooks — MDR_016: Automatic Memory from Activity.

HARDENED VERSION — Answers to the 3 critical questions:

Q1: CERTAINTY — "With what certainty will the hook get called?"
    ANSWER: 100% for all events that go through _emit_event().
    This hook is wired INLINE in event_ops._emit_event (line ~83).
    Every single event in Nucleus passes through that function.
    There are 21 unique event types across 13 source files.
    All 21 are classified below (trigger OR skip — no unknowns).
    The hook uses try/except pass, so it NEVER blocks event emission.

Q2: CROSS-PLATFORM — "How will this work across platforms?"
    ANSWER: This is pure Python. No OS-specific code, no file watchers,
    no subprocess calls, no platform-specific APIs. It reads/writes
    JSONL files using pathlib (cross-platform by design).
    Works on: macOS, Linux, Windows, Docker, Cloud Run, Render.
    Works via: Claude Desktop, Cursor, VS Code, any MCP client.
    The MCP protocol is the distribution layer — hooks fire server-side.

Q3: METRICS — "How do we monitor efficiency?"
    ANSWER: Every hook call writes to engrams/hook_metrics.jsonl.
    Metrics tracked: event_type, outcome (ADD/NOOP/SKIP/ERROR),
    latency_ms, engram_key (if created), timestamp.
    brain_morning_brief can read these to report hook health.
    Metric summary available via brain_hook_metrics() tool.

Architecture:
    _emit_event() → process_event_for_engram() → ADUN pipeline → ledger
                  ↘ record_metric()            → hook_metrics.jsonl

COMPLETE EVENT REGISTRY (21 events, audited Feb 19 2026):
    ┌────────────────────────────┬───────────┬──────────────────────────────┐
    │ Event Type                 │ Action    │ Source File                  │
    ├────────────────────────────┼───────────┼──────────────────────────────┤
    │ task_created               │ TRIGGER   │ task_ops.py:207              │
    │ task_claimed               │ TRIGGER   │ task_ops.py:281              │
    │ task_state_changed         │ TRIGGER   │ task_ops.py:245              │
    │ task_escalated             │ TRIGGER   │ task_ops.py:345              │
    │ tasks_imported             │ SKIP      │ task_ops.py:437              │
    │ task_claimed_with_fence    │ SKIP(dup) │ orch_helpers.py:435          │
    │ task_completed_with_fence  │ TRIGGER   │ orch_helpers.py:488          │
    │ slot_task_completed        │ TRIGGER   │ slot_ops.py:100              │
    │ slot_exhausted             │ SKIP      │ slot_ops.py:141              │
    │ slot_registered            │ SKIP      │ orchestrate_ops.py:141       │
    │ sprint_started             │ TRIGGER   │ slot_ops.py:466              │
    │ handoff_requested          │ TRIGGER   │ slot_ops.py:620              │
    │ deploy_poll_started        │ SKIP      │ deployment_ops.py:101        │
    │ deploy_complete            │ TRIGGER   │ deployment_ops.py:232        │
    │ session_started            │ TRIGGER   │ session_ops.py:427           │
    │ session_registered         │ SKIP      │ __init__.py:3107             │
    │ engram_written             │ SKIP      │ engram_ops.py:61             │
    │ code_critiqued             │ TRIGGER   │ __init__.py:2847             │
    │ depth_increased            │ SKIP      │ depth_ops.py:108             │
    │ depth_decreased            │ SKIP      │ depth_ops.py:156             │
    │ morning_brief_generated    │ TRIGGER   │ morning_brief_ops.py (new)   │
    └────────────────────────────┴───────────┴──────────────────────────────┘
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("nucleus.engram_hooks")


# METRICS & MONITORING (Q3 answer)
# ═══════════════════════════════════════════════════════════════

def _record_metric(
    event_type: str,
    outcome: str,
    latency_ms: float,
    engram_key: Optional[str],
    brain_path: Optional[Path] = None,
    error: Optional[str] = None,
):
    """
    Record a hook execution metric to hook_metrics.jsonl.

    Schema:
    {
        "timestamp": ISO8601,
        "event_type": str,
        "outcome": "ADD" | "UPDATE" | "NOOP" | "SKIP" | "ERROR" | "UNKNOWN",
        "latency_ms": float,
        "engram_key": str | null,
        "error": str | null
    }
    """
    try:
        if brain_path is None:
            from .common import get_brain_path
            brain_path = get_brain_path()

        metrics_path = brain_path / "engrams" / "hook_metrics.jsonl"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)

        metric = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "outcome": outcome,
            "latency_ms": round(latency_ms, 2),
            "engram_key": engram_key,
            "error": error,
        }

        with open(metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, ensure_ascii=False) + "\n")

    except Exception:
        pass  # Metrics must NEVER break anything


def get_hook_metrics_summary(brain_path: Optional[Path] = None) -> Dict:
    """
    Compute a summary of hook metrics for monitoring.

    Returns:
    {
        "total_executions": int,
        "outcomes": {"ADD": n, "NOOP": n, "SKIP": n, "ERROR": n, "UPDATE": n, "UNKNOWN": n},
        "by_event_type": {event_type: {"count": n, "avg_latency_ms": f}},
        "error_rate": float (0.0-1.0),
        "avg_latency_ms": float,
        "efficiency": float (ADD+UPDATE / total, excluding SKIP),
        "last_24h": {...same structure for last 24h only...}
    }
    """
    try:
        if brain_path is None:
            from .common import get_brain_path
            brain_path = get_brain_path()

        metrics_path = brain_path / "engrams" / "hook_metrics.jsonl"
        if not metrics_path.exists():
            return {"total_executions": 0, "message": "No metrics yet"}

        metrics = []
        with open(metrics_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        metrics.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if not metrics:
            return {"total_executions": 0, "message": "No metrics yet"}

        # Overall summary
        total = len(metrics)
        outcomes = {}
        by_event = {}
        total_latency = 0.0

        for m in metrics:
            outcome = m.get("outcome", "?")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

            evt = m.get("event_type", "?")
            if evt not in by_event:
                by_event[evt] = {"count": 0, "total_latency": 0.0}
            by_event[evt]["count"] += 1
            by_event[evt]["total_latency"] += m.get("latency_ms", 0)

            total_latency += m.get("latency_ms", 0)

        # Compute averages
        for evt in by_event:
            c = by_event[evt]["count"]
            by_event[evt]["avg_latency_ms"] = round(by_event[evt]["total_latency"] / c, 2) if c else 0
            del by_event[evt]["total_latency"]

        errors = outcomes.get("ERROR", 0)
        adds = outcomes.get("ADD", 0)
        updates = outcomes.get("UPDATE", 0)
        non_skip = total - outcomes.get("SKIP", 0) - outcomes.get("UNKNOWN", 0)

        return {
            "total_executions": total,
            "outcomes": outcomes,
            "by_event_type": by_event,
            "error_rate": round(errors / total, 4) if total else 0,
            "avg_latency_ms": round(total_latency / total, 2) if total else 0,
            "efficiency": round((adds + updates) / non_skip, 4) if non_skip else 0,
            "coverage": {
                "trigger_events": len(TRIGGER_EVENTS),
                "skip_events": len(SKIP_EVENTS),
                "total_classified": len(TRIGGER_EVENTS) + len(SKIP_EVENTS),
                "unclassified_seen": [
                    evt for evt in by_event if evt not in TRIGGER_EVENTS and evt not in SKIP_EVENTS
                ],
            },
        }

    except Exception as e:
        return {"error": str(e), "total_executions": 0}
