"""Morning Brief Operations — The Alive Workflow.

MDR_015: The ONE workflow that makes Nucleus a living OS.

Design Thinking Output Reference:
  "Nucleus will not come alive through more tools, more memory, or more architecture.
   It will come alive through ONE provable workflow that the founder uses every day."
  — EXHAUSTIVE_DESIGN_THINKING_OUTPUT.md, Stage 4

What it does:
  1. RETRIEVE — Top engrams by intensity + recency
  2. ORIENT   — Current tasks from the task ledger (pending, in-progress)
  3. SCAN     — Yesterday's audit events (what happened in the last session)
  4. RECOMMEND — "Today you should do X" based on context
  5. OUTPUT   — A concise daily brief, ready in < 60 seconds

Usage via MCP:
  brain_morning_brief()
  → Returns a structured daily brief with memory, tasks, and recommendation.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

logger = logging.getLogger("nucleus.morning_brief")


def _morning_brief_impl() -> Dict:
    """
    Generate the Nucleus Morning Brief.

    The brief answers the founder's core question:
    "I just opened my IDE. What should I work on? What did I do yesterday?
     What does Nucleus remember?"

    Returns:
        Dict with sections: memory, tasks, yesterday, recommendation, meta.
    """
    from .common import get_brain_path

    brain = get_brain_path()
    brief = {
        "timestamp": datetime.now().isoformat(),
        "sections": {},
        "recommendation": None,
        "meta": {"generation_time_ms": 0},
    }
    start = time.time()

    # ── SECTION 1: MEMORY (Top Engrams) ────────────────────────
    brief["sections"]["memory"] = _retrieve_top_engrams(brain)

    # ── SECTION 2: TASKS (Current Work) ────────────────────────
    brief["sections"]["tasks"] = _retrieve_tasks(brain)

    # ── SECTION 3: YESTERDAY (Recent Activity) ─────────────────
    brief["sections"]["yesterday"] = _retrieve_yesterday(brain)

    # ── SECTION 4: HOOK HEALTH (Auto-Write Metrics) ───────────
    brief["sections"]["hook_health"] = _retrieve_hook_health(brain)

    # ── SECTION 5: RECOMMENDATION ──────────────────────────────
    brief["recommendation"] = _generate_recommendation(brief["sections"])

    # ── META ────────────────────────────────────────────────────
    elapsed = (time.time() - start) * 1000
    brief["meta"]["generation_time_ms"] = round(elapsed, 1)

    # ── FORMAT AS READABLE BRIEF ───────────────────────────────
    brief["formatted"] = _format_brief(brief)

    # ── EMIT EVENT (feeds back into auto-hook system) ──────────
    try:
        from .event_ops import _emit_event
        rec = brief.get("recommendation", {})
        _emit_event("morning_brief_generated", "morning_brief", {
            "action": rec.get("action", "?"),
            "engram_count": brief["sections"].get("memory", {}).get("count", 0),
            "task_count": brief["sections"].get("tasks", {}).get("total_tasks", 0),
            "generation_time_ms": brief["meta"]["generation_time_ms"],
        })
    except Exception:
        pass  # Never let event emission break the brief

    return brief


def _retrieve_hook_health(brain: Path) -> Dict:
    """Retrieve auto-write hook metrics for the brief."""
    try:
        from .engram_hooks import get_hook_metrics_summary
        return get_hook_metrics_summary(brain)
    except Exception:
        return {"total_executions": 0, "message": "Hook metrics unavailable"}


def _retrieve_top_engrams(brain: Path, limit: int = 10) -> Dict:
    """Retrieve top engrams by intensity, with recency bonus."""
    engram_path = brain / "engrams" / "ledger.jsonl"
    if not engram_path.exists():
        return {"engrams": [], "count": 0, "message": "No engrams yet. Start writing decisions!"}

    engrams = []
    now = datetime.now()

    with open(engram_path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    e = json.loads(line)
                    if e.get("deleted", False):
                        continue

                    # Compute score: intensity × 2 + recency_bonus + context_bonus
                    intensity = e.get("intensity", 5)
                    score = intensity * 2

                    # Recency bonus
                    ts = e.get("timestamp", "")
                    if ts:
                        try:
                            age = now - datetime.fromisoformat(ts)
                            if age.days < 7:
                                score += 2
                            elif age.days < 30:
                                score += 1
                        except (ValueError, TypeError):
                            pass

                    e["_score"] = score
                    engrams.append(e)
                except json.JSONDecodeError:
                    continue

    # Sort by score DESC, take top N
    engrams.sort(key=lambda x: x.get("_score", 0), reverse=True)
    top = engrams[:limit]

    return {
        "engrams": [
            {
                "key": e.get("key", "?"),
                "value": e.get("value", "")[:200],  # Truncate for brief
                "context": e.get("context", "?"),
                "intensity": e.get("intensity", 5),
                "version": e.get("version", 1),
                "score": e.get("_score", 0),
            }
            for e in top
        ],
        "count": len(engrams),
        "showing": len(top),
    }


def _retrieve_tasks(brain: Path) -> Dict:
    """Retrieve current tasks from the task ledger."""
    tasks_path = brain / "ledger" / "tasks.jsonl"
    if not tasks_path.exists():
        return {"pending": [], "in_progress": [], "count": 0, "message": "No tasks in ledger."}

    pending = []
    in_progress = []
    total = 0

    with open(tasks_path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    t = json.loads(line)
                    total += 1
                    status = t.get("status", "pending").lower()
                    entry = {
                        "id": t.get("id", t.get("task_id", "?")),
                        "description": t.get("description", "")[:150],
                        "priority": t.get("priority", 5),
                        "status": status,
                    }
                    if status in ("pending", "open", "todo"):
                        pending.append(entry)
                    elif status in ("in_progress", "in-progress", "claimed", "active"):
                        in_progress.append(entry)
                except json.JSONDecodeError:
                    continue

    # Sort by priority (highest first)
    pending.sort(key=lambda x: x.get("priority", 5), reverse=True)
    in_progress.sort(key=lambda x: x.get("priority", 5), reverse=True)

    return {
        "in_progress": in_progress[:5],
        "pending": pending[:5],
        "total_tasks": total,
    }


def _retrieve_yesterday(brain: Path) -> Dict:
    """Retrieve recent activity from the event log (last 24h)."""
    events_path = brain / "ledger" / "events.jsonl"
    if not events_path.exists():
        return {"events": [], "count": 0, "message": "No events logged yet."}

    cutoff = datetime.now() - timedelta(hours=24)
    recent = []

    with open(events_path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    ev = json.loads(line)
                    ts = ev.get("timestamp", "")
                    if ts:
                        try:
                            event_time = datetime.fromisoformat(ts)
                            if event_time >= cutoff:
                                recent.append({
                                    "event": ev.get("event_type", ev.get("event", "?")),
                                    "emitter": ev.get("emitter", "?"),
                                    "time": ts,
                                    "detail": str(ev.get("data", ev.get("metadata", "")))[:100],
                                })
                        except (ValueError, TypeError):
                            pass
                except json.JSONDecodeError:
                    continue

    # Most recent first
    recent.reverse()

    return {
        "events": recent[:15],
        "count": len(recent),
    }


def _generate_recommendation(sections: Dict) -> Dict:
    """
    Generate a "Today you should..." recommendation.

    Logic (deterministic, no LLM needed):
    1. If there are in-progress tasks → continue highest priority one
    2. If no in-progress but pending → start highest priority pending
    3. If no tasks at all → suggest writing engrams from yesterday's events
    4. Always include context from top engram as a reminder
    """
    tasks = sections.get("tasks", {})
    memory = sections.get("memory", {})
    yesterday = sections.get("yesterday", {})

    in_progress = tasks.get("in_progress", [])
    pending = tasks.get("pending", [])
    top_engrams = memory.get("engrams", [])
    recent_events = yesterday.get("events", [])

    if in_progress:
        top_task = in_progress[0]
        return {
            "action": "CONTINUE",
            "task": top_task["description"],
            "task_id": top_task["id"],
            "reason": f"You have an in-progress task (priority {top_task['priority']}). Finish it before starting new work.",
            "context_reminder": top_engrams[0]["value"] if top_engrams else None,
        }
    elif pending:
        top_task = pending[0]
        return {
            "action": "START",
            "task": top_task["description"],
            "task_id": top_task["id"],
            "reason": f"No in-progress work. Pick up the highest priority pending task (priority {top_task['priority']}).",
            "context_reminder": top_engrams[0]["value"] if top_engrams else None,
        }
    elif recent_events:
        return {
            "action": "REFLECT",
            "task": "Review yesterday's activity and write engrams for key decisions",
            "task_id": None,
            "reason": f"No tasks in ledger, but {len(recent_events)} events from yesterday. Capture learnings as engrams.",
            "context_reminder": top_engrams[0]["value"] if top_engrams else None,
        }
    else:
        return {
            "action": "BOOTSTRAP",
            "task": "Add your first task via brain_add_task and your first engram via brain_write_engram",
            "task_id": None,
            "reason": "Nucleus has no tasks and no recent activity. Start by telling it what you're working on.",
            "context_reminder": None,
        }


def _format_brief(brief: Dict) -> str:
    """Format the brief into a human-readable terminal output."""
    lines = []
    lines.append("=" * 60)
    lines.append("🧠 NUCLEUS MORNING BRIEF")
    lines.append(f"   {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}")
    lines.append("=" * 60)

    # Memory section
    memory = brief["sections"].get("memory", {})
    engrams = memory.get("engrams", [])
    lines.append(f"\n📝 MEMORY ({memory.get('showing', 0)}/{memory.get('count', 0)} engrams)")
    lines.append("-" * 40)
    if engrams:
        for e in engrams[:5]:
            intensity_bar = "█" * e["intensity"] + "░" * (10 - e["intensity"])
            lines.append(f"  [{intensity_bar}] {e['key']}: {e['value'][:80]}")
    else:
        lines.append("  (empty — write your first engram!)")

    # Tasks section
    tasks = brief["sections"].get("tasks", {})
    in_prog = tasks.get("in_progress", [])
    pend = tasks.get("pending", [])
    lines.append(f"\n📋 TASKS ({len(in_prog)} active, {len(pend)} pending)")
    lines.append("-" * 40)
    if in_prog:
        for t in in_prog[:3]:
            lines.append(f"  🔵 [P{t['priority']}] {t['description'][:70]}")
    if pend:
        for t in pend[:3]:
            lines.append(f"  ⚪ [P{t['priority']}] {t['description'][:70]}")
    if not in_prog and not pend:
        lines.append("  (no tasks — add one with brain_add_task)")

    # Yesterday section
    yesterday = brief["sections"].get("yesterday", {})
    events = yesterday.get("events", [])
    lines.append(f"\n⏪ YESTERDAY ({yesterday.get('count', 0)} events)")
    lines.append("-" * 40)
    if events:
        for ev in events[:5]:
            lines.append(f"  • {ev['event']} ({ev['emitter']})")
    else:
        lines.append("  (no recent activity)")

    # Hook Health section
    hook = brief["sections"].get("hook_health", {})
    if hook.get("total_executions", 0) > 0:
        lines.append(f"\n🪝 HOOK HEALTH ({hook.get('total_executions', 0)} executions)")
        lines.append("-" * 40)
        outcomes = hook.get("outcomes", {})
        adds = outcomes.get("ADD", 0)
        noops = outcomes.get("NOOP", 0)
        errors = outcomes.get("ERROR", 0)
        lines.append(f"  Engrams auto-created: {adds}  |  Dedups: {noops}  |  Errors: {errors}")
        eff = hook.get("efficiency", 0)
        err_rate = hook.get("error_rate", 0)
        lines.append(f"  Efficiency: {eff:.0%}  |  Error rate: {err_rate:.1%}  |  Avg: {hook.get('avg_latency_ms', 0):.1f}ms")

    # Recommendation
    rec = brief.get("recommendation", {})
    if rec:
        lines.append(f"\n🎯 TODAY YOU SHOULD: {rec.get('action', '?')}")
        lines.append("=" * 60)
        lines.append(f"  → {rec.get('task', 'No recommendation')}")
        if rec.get('reason'):
            lines.append(f"  💡 {rec['reason']}")
        if rec.get('context_reminder'):
            lines.append(f"  🧠 Remember: {rec['context_reminder'][:80]}")

    # Meta
    lines.append(f"\n⚡ Generated in {brief['meta']['generation_time_ms']}ms")
    lines.append("=" * 60)

    return "\n".join(lines)
