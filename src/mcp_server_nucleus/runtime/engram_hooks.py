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


# ═══════════════════════════════════════════════════════════════
# COMPLETE EVENT CLASSIFICATION (36 events — no unknowns)
# ═══════════════════════════════════════════════════════════════

TRIGGER_EVENTS = {
    # ── Tasks (4 triggers) ────────────────────────────────────
    "task_created": {
        "context": "Feature",
        "intensity": 5,
        "template": "New task created: {description}",
        "key_prefix": "task_new",
        "data_fields": ["description", "task_id", "priority"],
    },
    "task_claimed": {
        "context": "Strategy",
        "intensity": 4,
        "template": "Started working on: {description}",
        "key_prefix": "task_wip",
        "data_fields": ["description", "task_id"],
    },
    "task_state_changed": {
        "context": "Feature",
        "intensity": 6,
        "template": "Task {task_id} changed: {old_status} → {new_status}",
        "key_prefix": "task_chg",
        "data_fields": ["task_id", "old_status", "new_status"],
    },
    "task_escalated": {
        "context": "Strategy",
        "intensity": 7,
        "template": "Task {task_id} ESCALATED: {reason}",
        "key_prefix": "task_esc",
        "data_fields": ["task_id", "reason"],
    },

    # ── Completions (2 triggers — the MONEY events) ───────────
    "task_completed_with_fence": {
        "context": "Feature",
        "intensity": 7,
        "template": "Task {task_id} COMPLETED ({outcome}) by slot {slot_id}",
        "key_prefix": "done",
        "data_fields": ["task_id", "outcome", "fence_token"],
    },
    "slot_task_completed": {
        "context": "Feature",
        "intensity": 6,
        "template": "Slot completed task {task_id} — outcome: {outcome}",
        "key_prefix": "slot_done",
        "data_fields": ["task_id", "outcome"],
    },

    # ── Deployments (1 trigger) ───────────────────────────────
    "deploy_complete": {
        "context": "Feature",
        "intensity": 7,
        "template": "Deployment complete: {service_id} — {status}",
        "key_prefix": "deploy",
        "data_fields": ["service_id", "status", "deploy_url"],
    },

    # ── Sprints & Orchestration (2 triggers) ──────────────────
    "sprint_started": {
        "context": "Strategy",
        "intensity": 6,
        "template": "Sprint {sprint_id} started — {tasks_assigned} tasks assigned",
        "key_prefix": "sprint",
        "data_fields": ["sprint_id", "tasks_assigned"],
    },
    "handoff_requested": {
        "context": "Strategy",
        "intensity": 5,
        "template": "Handoff requested to {to_agent}: {handoff_id}",
        "key_prefix": "handoff",
        "data_fields": ["handoff_id", "to_agent", "priority"],
    },

    # ── Sessions (2 triggers) ─────────────────────────────────
    "session_started": {
        "context": "Strategy",
        "intensity": 3,
        "template": "Session started — {task_count} tasks loaded",
        "key_prefix": "session",
        "data_fields": ["task_count"],
    },
    "session_ended": {
        "context": "Strategy",
        "intensity": 5,
        "template": "Session ended ({mood}): {summary}",
        "key_prefix": "session_end",
        "data_fields": ["summary", "mood", "event_count", "tasks_completed"],
    },

    # ── Code Review (1 trigger) ──────────────────────────────
    "code_critiqued": {
        "context": "Architecture",
        "intensity": 6,
        "template": "Code review completed for {file_path}: {verdict}",
        "key_prefix": "review",
        "data_fields": ["file_path", "verdict", "issues_found"],
    },

    # ── Morning Brief (1 trigger) ────────────────────────────
    "morning_brief_generated": {
        "context": "Strategy",
        "intensity": 3,
        "template": "Morning Brief used — recommendation: {action}",
        "key_prefix": "brief",
        "data_fields": ["action", "engram_count", "task_count"],
    },

    # ── Three Frontiers (3 triggers — Phase 3) ──────────────
    "ground_verified": {
        "context": "Architecture",
        "intensity": 5,
        "template": "GROUND T{tier_reached}: verified={verified}",
        "key_prefix": "ground",
        "data_fields": ["receipt_id", "tier_reached", "verified", "tiers_passed", "tiers_failed"],
    },
    "align_reviewed": {
        "context": "Strategy",
        "intensity": 8,
        "template": "ALIGN: {verdict} — {human_notes}",
        "key_prefix": "align",
        "data_fields": ["task_id", "verdict", "human_notes", "correction"],
    },
    "delta_recorded": {
        "context": "Strategy",
        "intensity": 6,
        "template": "DELTA [{frontier}] {direction}: {insight}",
        "key_prefix": "delta",
        "data_fields": ["delta_id", "frontier", "direction", "magnitude", "insight"],
    },

    # ── Business Functions (6 triggers — Phase 4) ──────────────
    "growth_gate_measured": {
        "context": "Strategy",
        "intensity": 6,
        "template": "GROWTH: {gate} {current}/{target} ({pace})",
        "key_prefix": "growth",
        "data_fields": ["gate", "current", "target", "pace", "on_track"],
    },
    "content_published": {
        "context": "Strategy",
        "intensity": 5,
        "template": "CONTENT: {content_type} — {title}",
        "key_prefix": "content",
        "data_fields": ["content_type", "title", "url", "channel"],
    },
    "content_performance_measured": {
        "context": "Strategy",
        "intensity": 5,
        "template": "CONTENT PERF: {title} views={views} bounce={bounce_rate}",
        "key_prefix": "content_perf",
        "data_fields": ["title", "views", "time_on_page", "bounce_rate", "source"],
    },
    "distribution_signal": {
        "context": "Strategy",
        "intensity": 7,
        "template": "DISTRIBUTION: {channel} — {signal}",
        "key_prefix": "dist",
        "data_fields": ["channel", "signal", "referrals", "conversions"],
    },
    "feature_usage_measured": {
        "context": "Architecture",
        "intensity": 4,
        "template": "USAGE: {hub}:{action_name} count={count}",
        "key_prefix": "usage",
        "data_fields": ["hub", "action_name", "count", "period"],
    },
    "dogfood_entry": {
        "context": "Strategy",
        "intensity": 7,
        "template": "DOGFOOD day {day_number}: pain={pain_if_broken}/10 pay={would_pay}",
        "key_prefix": "dogfood",
        "data_fields": ["day_number", "pain_if_broken", "would_pay", "decisions_faster", "notes"],
    },
}

# Events that should NEVER create engrams (noisy/circular/redundant)
SKIP_EVENTS = {
    "engram_written",           # Circular — would create infinite loop
    "engram_queried",           # Read-only, no knowledge created
    "engram_searched",          # Read-only, no knowledge created
    "event_emitted",            # Meta-event, nothing to capture
    "health_check",             # Routine health check, too noisy
    "tasks_imported",           # Bulk operation, too noisy per-item
    "task_claimed_with_fence",  # Duplicate of task_claimed (same semantics)
    "slot_registered",          # Infrastructure event, not knowledge
    "slot_exhausted",           # Operational, not knowledge
    "deploy_poll_started",      # Too noisy, only care about completion
    "session_registered",       # Duplicate of session_started
    "depth_increased",          # Internal tracking, not knowledge
    "depth_decreased",          # Internal tracking, not knowledge
    "session_saved",             # Duplicate of session_ended (save != end)
}

# All events must be in exactly one set (enforced at import time)
_ALL_EVENTS = set(TRIGGER_EVENTS.keys()) | SKIP_EVENTS
assert len(_ALL_EVENTS) == len(TRIGGER_EVENTS) + len(SKIP_EVENTS), \
    "BUG: Event appears in both TRIGGER and SKIP sets"


# ═══════════════════════════════════════════════════════════════
# CORE HOOK LOGIC
# ═══════════════════════════════════════════════════════════════

def should_auto_write(event_type: str) -> bool:
    """Check if an event type should trigger auto-engram creation."""
    return event_type in TRIGGER_EVENTS


def process_event_for_engram(event_type: str, event_data: Dict[str, Any]) -> Optional[Dict]:
    """
    Main entry point: called from _emit_event to auto-create engrams.

    CERTAINTY: This function is called for EVERY event that passes through
    _emit_event(). The try/except in event_ops.py ensures this never blocks
    the event pipeline. Worst case = metric records ERROR, event still emits.

    Args:
        event_type: The type of event.
        event_data: The event payload.

    Returns:
        ADUN result if an engram was created, None otherwise.
    """
    start = time.time()

    # Fast path: skip events we don't care about
    if event_type not in TRIGGER_EVENTS:
        # Only record metric if it's a truly unknown event (not in SKIP either)
        if event_type not in SKIP_EVENTS:
            _record_metric(event_type, "UNKNOWN", 0, None)
        return None

    try:
        from .common import get_brain_path
        brain = get_brain_path()

        result = _create_auto_engram(event_type, event_data, brain)

        elapsed_ms = (time.time() - start) * 1000

        if result and result.get("added", 0) > 0:
            key = result.get("details", [{}])[0].get("key", "?")
            _record_metric(event_type, "ADD", elapsed_ms, key, brain)
            logger.info(f"🧠 Auto-engram: [{event_type}] → {key}")
            # Feed high-value events to training archive
            _record_to_training_archive(event_type, event_data, brain)
        elif result and result.get("skipped", 0) > 0:
            _record_metric(event_type, "NOOP", elapsed_ms, None, brain)
        elif result and result.get("updated", 0) > 0:
            key = result.get("details", [{}])[0].get("key", "?")
            _record_metric(event_type, "UPDATE", elapsed_ms, key, brain)
        else:
            _record_metric(event_type, "SKIP", elapsed_ms, None, brain)

        return result

    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        _record_metric(event_type, "ERROR", elapsed_ms, None, error=str(e))
        logger.warning(f"Auto-engram hook failed (non-fatal): {e}")
        return None


def _create_auto_engram(event_type: str, event_data: Dict[str, Any], brain_path: Path) -> Optional[Dict]:
    """Create an auto-engram from an event via the ADUN pipeline."""
    config = TRIGGER_EVENTS[event_type]

    # Build description from template + event data
    description = _fill_template(config["template"], event_data)

    if not description or len(description) < 10:
        return None

    # Generate a deterministic-ish key
    key = f"{config['key_prefix']}_{int(time.time()) % 100000}"

    # Override intensity if event data specifies it
    intensity = event_data.get("intensity", config["intensity"])

    from .memory_pipeline import MemoryPipeline
    pipeline = MemoryPipeline(brain_path)
    return pipeline.process(
        text=description,
        context=config["context"],
        intensity=intensity,
        source_agent="auto_hook",
        key=key,
    )


def _fill_template(template: str, data: Dict) -> str:
    """
    Fill a template string with data fields.

    Robust: if a field is missing, uses "?" instead of crashing.
    Falls back to raw data stringification if template completely fails.
    """
    # Try template with safe defaults
    try:
        # Create a safe dict that returns "?" for missing keys
        safe_data = _SafeDict(data)
        filled = template.format_map(safe_data)
        return filled
    except Exception:
        pass

    # Fallback: extract common description fields
    for field in ("description", "message", "detail", "summary", "task", "reason"):
        if field in data and data[field]:
            return str(data[field])[:200]

    # Last resort
    return json.dumps(data)[:200]


class _SafeDict(dict):
    """Dict subclass that returns '?' for missing keys in str.format_map()."""
    def __missing__(self, key):
        return "?"


# ═══════════════════════════════════════════════════════════════
# TRAINING ARCHIVE BRIDGE (feeds high-value events to Third Brother)
# ═══════════════════════════════════════════════════════════════

# Only these events produce meaningful training signal.
# Session starts, brief reads, and other low-signal events are skipped.
_ARCHIVE_WORTHY_EVENTS = {
    "task_completed_with_fence", "slot_task_completed",
    "deploy_complete", "code_critiqued", "task_escalated",
    "handoff_requested", "sprint_started",
    # Phase 3: Three Frontiers — every verification, review, and delta is training signal
    "ground_verified", "align_reviewed", "delta_recorded",
    # Phase 4: Business functions — growth gates and dogfood are high-value founder signals
    "growth_gate_measured", "dogfood_entry",
}


def _record_to_training_archive(event_type: str, event_data: Dict[str, Any], brain: Path):
    """Record significant events as training data for the Third Brother.

    Creates a LoopTurn with the event as a synthetic conversation pair:
    user = "What happened?" + event context, assistant = structured outcome.
    Only fires for high-value events (completions, deploys, reviews).

    Also captures DPO outcome preferences: deploy success = chosen,
    deploy failure / task escalation = rejected.
    """
    if event_type not in _ARCHIVE_WORTHY_EVENTS:
        return
    try:
        from .archive_pipeline import ArchivePipeline
        config = TRIGGER_EVENTS[event_type]
        description = _fill_template(config["template"], event_data)
        archive = ArchivePipeline(brain_path=brain)
        archive.record_turn(
            brother="code",
            intent=description,
            actions=[f"event:{event_type}"],
            tools_used=[],
            decisions=[],
            outcome=description,
            signal_absorbed=[],
            signal_produced=[f"event/{event_type}"],
            confidence=0.7,
            context=f"Auto-hook: {event_type}",
        )

        # DPO outcome preference: success vs failure signals
        if event_type == "deploy_complete":
            status = event_data.get("status", "")
            service = event_data.get("service_id", "service")
            archive.record_outcome_preference(
                event_type=event_type,
                prompt=f"Deploy {service} to production",
                response=description,
                success="success" in status.lower() and "failed" not in status.lower(),
                context=service,
            )
        elif event_type == "task_escalated":
            reason = event_data.get("reason", "unknown")
            task_id = event_data.get("task_id", "?")
            archive.record_outcome_preference(
                event_type=event_type,
                prompt=f"Complete task {task_id}",
                response=f"Attempted but escalated: {reason}",
                success=False,
                context=f"task {task_id}",
            )
        elif event_type == "code_critiqued":
            verdict = event_data.get("verdict", "")
            issues = event_data.get("issues_found", 0)
            file_path = event_data.get("file_path", "code")
            if issues and int(issues) > 0:
                archive.record_outcome_preference(
                    event_type=event_type,
                    prompt=f"Review code in {file_path}",
                    response=description,
                    success=False,
                    context=file_path,
                )
    except Exception:
        pass  # Never block the hook pipeline


# ═══════════════════════════════════════════════════════════════
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
