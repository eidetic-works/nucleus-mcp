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
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("nucleus.morning_brief")


def _find_engram_by_key(brain: Path, key: str) -> Optional[dict]:
    """Find a specific engram by exact key match. Returns None if not found."""
    ledger = brain / "engrams" / "ledger.jsonl"
    if not ledger.exists():
        return None
    result = None
    try:
        with open(ledger, "r") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("key") == key and not e.get("deleted", False):
                        result = e
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        return None
    return result


def _check_recommendation_followed(yesterday_rec: dict, tasks_data: dict, events_list: list) -> bool:
    """Check if yesterday's brief recommendation was acted upon."""
    rec_value = yesterday_rec.get("value", "")
    task_ref = ""
    if "]" in rec_value:
        after_bracket = rec_value.split("]", 1)[1]
        task_ref = after_bracket.split("|")[0].strip()
    if not task_ref:
        return False
    ref_words = set(task_ref.lower().split())
    if len(ref_words) < 2:
        return False
    for event in events_list:
        event_type = event.get("event", event.get("type", ""))
        if event_type in ("task_completed", "task_claimed", "slot_task_completed",
                          "task_completed_with_fence", "task_state_changed"):
            event_data = json.dumps(event.get("detail", event.get("data", {}))).lower()
            matches = sum(1 for w in ref_words if w in event_data)
            if matches >= 2:
                return True
    for status_key in ("in_progress", "pending"):
        for task in (tasks_data.get(status_key) or []):
            task_desc = task.get("description", "").lower()
            matches = sum(1 for w in ref_words if w in task_desc)
            if matches >= 2 and status_key == "in_progress":
                return True
    return False


def _morning_brief_impl() -> Dict:
    """
    Generate the Nucleus Morning Brief.

    The brief answers the core question:
    "What should I work on? What happened yesterday?

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

    # ── SECTION 5: ADHD GUARDRAIL STATUS ────────────────────────
    brief["sections"]["adhd_status"] = _retrieve_adhd_status()

    # ── SECTION 6: THIRD BROTHER TRAINING STATUS ─────────────
    try:
        from .archive_pipeline import ArchivePipeline
        ap = ArchivePipeline(brain_path=brain)
        brief["sections"]["training"] = ap.should_retrain()
    except Exception:
        brief["sections"]["training"] = {}

    # ── SECTION 7: GROWTH (Phase 4 — Business Functions) ─────
    brief["sections"]["growth"] = _retrieve_growth_status(brain)

    # ── SECTION 8: FRONTIER HEALTH (Phase 4 — Three Frontiers) ─
    brief["sections"]["frontier_health"] = _retrieve_frontier_health(brain)

    # ── SECTION 9: RECOMMENDATION ──────────────────────────────
    brief["recommendation"] = _generate_recommendation(brief["sections"])

    # ── ARTERY 1: Persist recommendation as Strategy engram ───
    if not os.environ.get("NUCLEUS_DISABLE_ARTERY_1"):
        try:
            from .memory_pipeline import MemoryPipeline
            today_str = datetime.now().strftime('%Y%m%d')
            rec = brief["recommendation"]
            rec_key = f"brief_rec_{today_str}"
            rec_value = f"[{rec.get('action', '?')}] {rec.get('task', '')}"
            if rec.get("context_reminder"):
                rec_value += f" | Context: {rec['context_reminder'][:80]}"

            pipeline = MemoryPipeline(brain_path=brain)
            pipeline.process(
                text=rec_value,
                context="Strategy",
                intensity=7,
                source_agent="morning_brief",
                key=rec_key,
            )

            # Compare to yesterday's recommendation
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            yesterday_rec = _find_engram_by_key(brain, f"brief_rec_{yesterday_str}")
            if yesterday_rec:
                events_list = brief["sections"].get("yesterday", {}).get("events", [])
                tasks_data = brief["sections"].get("tasks", {})
                followed = _check_recommendation_followed(yesterday_rec, tasks_data, events_list)
                brief["sections"]["yesterday_recommendation"] = {
                    "recommendation": yesterday_rec.get("value", ""),
                    "followed": followed,
                    "delta": "ALIGNED" if followed else "DIVERGED",
                }
        except Exception:
            pass  # Never let recommendation persistence break the brief

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


def _retrieve_adhd_status() -> Dict:
    """Retrieve ADHD guardrail status (context switches + depth)."""
    try:
        from .depth_ops import _context_switch_status, _depth_show
        
        context_status = _context_switch_status()
        depth_status = _depth_show()
        
        return {
            "focus_status": context_status.get("status", "🟢 FOCUSED"),
            "switch_count": context_status.get("switch_count", 0),
            "max_switches": context_status.get("max_switches", 5),
            "depth": depth_status.get("current_depth", 0),
            "max_depth": depth_status.get("max_safe_depth", 5),
            "depth_status": depth_status.get("status", "🟢 SAFE"),
            "recommendation": context_status.get("recommendation", ""),
        }
    except Exception:
        return {"focus_status": "🟢 FOCUSED", "switch_count": 0, "message": "ADHD metrics unavailable"}


def _retrieve_growth_status(brain: Path) -> Dict:
    """Retrieve latest growth gate metrics for the brief (Phase 4)."""
    try:
        from .growth_ops import capture_metrics, GATES
        # Read the most recent growth metrics engram instead of hitting APIs
        ledger = brain / "engrams" / "ledger.jsonl"
        if not ledger.exists():
            return {"message": "No growth data yet"}

        latest = None
        with open(ledger, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                        if e.get("key", "").startswith("growth_metrics_"):
                            latest = e
                    except json.JSONDecodeError:
                        continue

        if not latest:
            return {"message": "No growth metrics engrams found. Run growth_pulse first."}

        # Parse the engram value for gate status
        return {
            "latest_date": latest.get("key", "").replace("growth_metrics_", ""),
            "value": latest.get("value", "")[:200],
            "gates_target": GATES,
        }
    except Exception as e:
        return {"message": f"Growth data unavailable: {e}"}


def _retrieve_frontier_health(brain: Path) -> Dict:
    """Retrieve Three Frontiers health summary for the brief (Phase 4)."""
    try:
        from .hardening import safe_read_jsonl
        from .delta_ops import extract_patterns

        result = {}

        # GROUND: verification pass rate
        vlog = brain / "verification_log.jsonl"
        if vlog.exists():
            receipts = safe_read_jsonl(vlog)
            if receipts:
                passed = sum(1 for r in receipts if not r.get("tiers_failed"))
                result["ground"] = {
                    "total": len(receipts),
                    "pass_rate": round(passed / len(receipts) * 100, 1),
                }

        # ALIGN: review counts
        vpath = brain / "driver" / "human_verdicts.jsonl"
        if vpath.exists():
            verdicts = safe_read_jsonl(vpath)
            non_pending = [v for v in verdicts if v.get("verdict") != "pending"]
            if non_pending:
                result["align"] = {
                    "total_reviews": len(non_pending),
                    "pending": len(verdicts) - len(non_pending),
                }

        # COMPOUND: delta count + rate
        try:
            patterns = extract_patterns(since="7d")
            if patterns.get("total_deltas", 0) > 0:
                result["compound"] = {
                    "deltas_7d": patterns["total_deltas"],
                    "compound_rate": patterns.get("compound_rate", 0),
                }
        except Exception:
            pass

        return result if result else {"message": "No frontier data yet"}
    except Exception as e:
        return {"message": f"Frontier health unavailable: {e}"}


def _retrieve_top_engrams(brain: Path, limit: int = 10) -> Dict:
    """Retrieve top engrams by intensity, with recency bonus."""
    engram_path = brain / "engrams" / "ledger.jsonl"
    if not engram_path.exists():
        return {"engrams": [], "count": 0, "message": "No engrams yet. Start writing decisions!"}

    engrams = []
    now = datetime.now()

    with open(engram_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    e = json.loads(line)
                    if e.get("deleted", False) or e.get("quarantined", False):
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

    with open(tasks_path, "r", encoding="utf-8") as f:
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

    # On Monday, look back to Friday (72h) to cover the weekend gap
    lookback_hours = 72 if datetime.now().weekday() == 0 else 24
    cutoff = datetime.now() - timedelta(hours=lookback_hours)
    recent = []

    with open(events_path, "r", encoding='utf-8') as f:
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

    # ADHD Guardrail section
    adhd = brief["sections"].get("adhd_status", {})
    switch_count = adhd.get("switch_count", 0)
    depth = adhd.get("depth", 0)
    if switch_count > 0 or depth > 0:
        lines.append(f"\n🧠 ADHD GUARDRAIL")
        lines.append("-" * 40)
        focus = adhd.get("focus_status", "🟢 FOCUSED")
        depth_status = adhd.get("depth_status", "🟢 SAFE")
        lines.append(f"  Focus: {focus}  |  Depth: {depth_status}")
        lines.append(f"  Context switches: {switch_count}/{adhd.get('max_switches', 5)}  |  Depth: {depth}/{adhd.get('max_depth', 5)}")
        if adhd.get("recommendation"):
            lines.append(f"  {adhd['recommendation']}")

    # Training status
    training = brief["sections"].get("training", {})
    if training.get("total_turns", 0) > 0:
        lines.append(f"\n🧬 THIRD BROTHER TRAINING")
        lines.append("-" * 40)
        lines.append(f"  Archive: {training.get('total_turns', 0)} turns  |  New: {training.get('new_turns', 0)}")
        if training.get("should_retrain"):
            lines.append(f"  ✅ RETRAIN RECOMMENDED — {training.get('reason', '')}")
        else:
            lines.append(f"  ⏳ {training.get('reason', 'waiting for data')}")

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
