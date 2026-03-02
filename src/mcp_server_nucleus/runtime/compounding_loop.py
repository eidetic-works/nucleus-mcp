"""Compounding v0 Loop — The 7-Day Automated Workflow.

MDR_017: The system that makes Nucleus self-improving.

Design Thinking Output Reference:
  "Each cycle starts faster because memory improves context."
  — DT1_SWARM_SESSION_DELIVERABLES.md, Section F

The Loop:
  INPUT (Founder: 3-5 line intent)
    ↓
  NUCLEUS ACTION (Execute tool calls with bounded autonomy)
    ↓
  OUTPUT (One artifact)
    ↓
  ENGRAM OPS (Write stable deltas via ADUN)
    ↓
  NEXT SESSION (Retrieve engrams + rolling summary)
    ↓
  [REPEAT — compounding effect]

Daily Plan:
  Mon: Gap analysis → alive_moment_definition
  Tue: Build the gap → feature_x_implemented
  Wed: Test the build → feature_x_verified
  Thu: Reflect → week_N_synthesis
  Fri: Ship it → release_vX.Y.Z
  Sat: Review telemetry → telemetry_week_N
  Sun: Auto-consolidate → consolidation_week_N
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger("nucleus.compounding")


def _get_day_of_week() -> str:
    """Get current day of week."""
    return datetime.now().strftime("%A")


def _get_week_number() -> int:
    """Get current ISO week number."""
    return datetime.now().isocalendar()[1]


def _compounding_loop_status_impl() -> Dict:
    """
    Get the current status of the Compounding v0 Loop.
    
    Shows:
    - What day of the loop we're on
    - What the founder should do today
    - Progress metrics (engrams written this week, tasks completed)
    - Compounding score (Day 7 output quality vs Day 1)
    """
    from .common import get_brain_path
    from .morning_brief_ops import _morning_brief_impl
    
    brain = get_brain_path()
    day = _get_day_of_week()
    week = _get_week_number()
    
    # Day-specific actions from the design thinking deliverables
    day_actions = {
        "Monday": {
            "action": "GAP_ANALYSIS",
            "task": "Identify what's missing to make Nucleus feel alive",
            "engram_key": "alive_moment_definition",
            "output": "1-page gap analysis",
        },
        "Tuesday": {
            "action": "BUILD",
            "task": "Implement the top gap from yesterday's analysis",
            "engram_key": "feature_x_implemented",
            "output": "Working PR or script",
        },
        "Wednesday": {
            "action": "TEST",
            "task": "Verify yesterday's build with tests and smoke tests",
            "engram_key": "feature_x_verified",
            "output": "Test report",
        },
        "Thursday": {
            "action": "REFLECT",
            "task": "Synthesize learnings from this week so far",
            "engram_key": f"week_{week}_synthesis",
            "output": "Weekly learning summary",
        },
        "Friday": {
            "action": "SHIP",
            "task": "Deploy and release the week's work",
            "engram_key": f"release_v1_0_X",
            "output": "Deployed version",
        },
        "Saturday": {
            "action": "AUDIT",
            "task": "Review telemetry and tool usage metrics",
            "engram_key": f"telemetry_week_{week}",
            "output": "Telemetry report",
        },
        "Sunday": {
            "action": "CONSOLIDATE",
            "task": "Auto-consolidate engrams and prune stale memory",
            "engram_key": f"consolidation_week_{week}",
            "output": "Clean ledger",
        },
    }
    
    today = day_actions.get(day, day_actions["Monday"])
    
    # Get morning brief data for metrics
    brief = _morning_brief_impl()
    memory = brief.get("sections", {}).get("memory", {})
    tasks = brief.get("sections", {}).get("tasks", {})
    hooks = brief.get("sections", {}).get("hook_health", {})
    
    # Calculate week's engram writes
    engram_count = memory.get("count", 0)
    
    # Calculate compounding score (rough metric)
    # Higher score = more engrams, more auto-writes, fewer errors
    auto_writes = hooks.get("outcomes", {}).get("ADD", 0)
    errors = hooks.get("outcomes", {}).get("ERROR", 0)
    efficiency = hooks.get("efficiency", 0) if isinstance(hooks.get("efficiency"), (int, float)) else 0
    
    compounding_score = min(100, int(
        (engram_count * 0.5) +
        (auto_writes * 2) +
        (efficiency * 50) -
        (errors * 5)
    ))
    
    return {
        "day_of_week": day,
        "week_number": week,
        "today": today,
        "metrics": {
            "total_engrams": engram_count,
            "auto_writes_this_session": auto_writes,
            "error_count": errors,
            "compounding_score": compounding_score,
        },
        "recommendation": brief.get("recommendation", {}),
        "formatted": _format_loop_status(day, week, today, compounding_score, brief),
    }


def _format_loop_status(day: str, week: int, today: Dict, score: int, brief: Dict) -> str:
    """Format the loop status as a readable output."""
    lines = []
    lines.append("=" * 60)
    lines.append("🔄 COMPOUNDING v0 LOOP STATUS")
    lines.append(f"   Week {week} | {day}")
    lines.append("=" * 60)
    
    lines.append(f"\n📅 TODAY'S ACTION: {today['action']}")
    lines.append("-" * 40)
    lines.append(f"  Task: {today['task']}")
    lines.append(f"  Output: {today['output']}")
    lines.append(f"  Engram to write: {today['engram_key']}")
    
    memory = brief.get("sections", {}).get("memory", {})
    hooks = brief.get("sections", {}).get("hook_health", {})
    
    lines.append(f"\n📊 COMPOUNDING METRICS")
    lines.append("-" * 40)
    lines.append(f"  Total engrams: {memory.get('count', 0)}")
    lines.append(f"  Auto-writes: {hooks.get('outcomes', {}).get('ADD', 0)}")
    lines.append(f"  Compounding score: {score}/100")
    
    # Score interpretation
    if score >= 80:
        interpretation = "🚀 EXCELLENT — Nucleus is compounding rapidly"
    elif score >= 50:
        interpretation = "📈 GOOD — Keep writing engrams daily"
    elif score >= 20:
        interpretation = "⚠️ SLOW — Need more consistent daily use"
    else:
        interpretation = "🔴 COLD — Nucleus isn't being used. Start with morning_brief!"
    lines.append(f"  {interpretation}")
    
    lines.append(f"\n🎯 MORNING BRIEF RECOMMENDATION")
    lines.append("-" * 40)
    rec = brief.get("recommendation", {})
    if rec:
        lines.append(f"  Action: {rec.get('action', '?')}")
        lines.append(f"  Task: {rec.get('task', 'No task')[:70]}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def _end_of_day_capture_impl(
    summary: str,
    key_decisions: List[str] = None,
    blockers: List[str] = None,
) -> Dict:
    """
    Capture end-of-day learnings as engrams.
    
    This is the ENGRAM OPS step of the Compounding Loop.
    Run this at the end of each work session to persist learnings.
    
    Args:
        summary: What was accomplished today (2-3 sentences)
        key_decisions: List of decisions made (auto-written as engrams)
        blockers: List of blockers encountered (for tomorrow's context)
    
    Returns:
        Dict with written engrams and next-day priming info.
    """
    from .common import get_brain_path
    from .engram_ops import _brain_write_engram_impl
    from .event_ops import _emit_event
    
    brain = get_brain_path()
    day = _get_day_of_week()
    week = _get_week_number()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    written_engrams = []
    
    # Write daily summary engram
    summary_key = f"daily_summary_{timestamp}"
    result = _brain_write_engram_impl(
        key=summary_key,
        value=summary,
        context="Decision",
        intensity=7,
    )
    written_engrams.append({"key": summary_key, "result": result})
    
    # Write each key decision as a separate engram
    if key_decisions:
        for i, decision in enumerate(key_decisions):
            decision_key = f"decision_{timestamp}_{i+1}"
            result = _brain_write_engram_impl(
                key=decision_key,
                value=decision,
                context="Decision",
                intensity=8,
            )
            written_engrams.append({"key": decision_key, "result": result})
    
    # Write blockers for tomorrow's context
    if blockers:
        blocker_key = f"blockers_{timestamp}"
        result = _brain_write_engram_impl(
            key=blocker_key,
            value="; ".join(blockers),
            context="Decision",
            intensity=9,  # High intensity so it surfaces tomorrow
        )
        written_engrams.append({"key": blocker_key, "result": result})
    
    # Emit event for the capture
    _emit_event("end_of_day_captured", "compounding_loop", {
        "day": day,
        "week": week,
        "summary_length": len(summary),
        "decisions_count": len(key_decisions) if key_decisions else 0,
        "blockers_count": len(blockers) if blockers else 0,
    })
    
    return {
        "success": True,
        "day": day,
        "week": week,
        "engrams_written": len(written_engrams),
        "details": written_engrams,
        "next_step": "Run brain_morning_brief tomorrow to see these learnings applied.",
    }


def _session_start_inject_impl() -> Dict:
    """
    Session-start auto-injection of top engrams.
    
    This is the NEXT SESSION step of the Compounding Loop.
    Automatically retrieves and injects the most relevant context
    at the start of each session.
    
    Returns:
        Dict with injected context ready to be used.
    """
    from .common import get_brain_path
    from .morning_brief_ops import _retrieve_top_engrams, _retrieve_tasks
    
    brain = get_brain_path()
    
    # Get top 10 engrams by scoring
    memory = _retrieve_top_engrams(brain, limit=10)
    tasks = _retrieve_tasks(brain)
    
    # Format as injection context
    context_lines = []
    
    context_lines.append("=== SESSION START CONTEXT ===")
    context_lines.append("")
    
    # Top memories
    engrams = memory.get("engrams", [])
    if engrams:
        context_lines.append("📝 KEY MEMORIES:")
        for e in engrams[:5]:
            context_lines.append(f"  • {e['key']}: {e['value'][:100]}")
        context_lines.append("")
    
    # Current tasks
    in_progress = tasks.get("in_progress", [])
    pending = tasks.get("pending", [])
    
    if in_progress:
        context_lines.append("🔵 IN PROGRESS:")
        for t in in_progress[:3]:
            context_lines.append(f"  • [{t['id']}] {t['description'][:80]}")
        context_lines.append("")
    
    if pending:
        context_lines.append("⚪ PENDING:")
        for t in pending[:3]:
            context_lines.append(f"  • [{t['id']}] {t['description'][:80]}")
        context_lines.append("")
    
    context_lines.append("=== END CONTEXT ===")
    
    return {
        "injected": True,
        "engram_count": len(engrams),
        "task_count": len(in_progress) + len(pending),
        "context": "\n".join(context_lines),
        "top_engrams": engrams[:5],
        "active_tasks": in_progress[:3],
    }


def _weekly_consolidation_impl(dry_run: bool = True) -> Dict:
    """
    Weekly consolidation — Sunday's automated task.
    
    What it does:
    1. Archive old engrams with TTL expiry
    2. Compute NOOP ratio and flag if > 50%
    3. Generate weekly synthesis engram
    4. Clean up stale tasks
    
    Args:
        dry_run: If True, preview without making changes
    
    Returns:
        Dict with consolidation results.
    """
    from .common import get_brain_path
    from .consolidation_ops import _garbage_collect_tasks, _archive_resolved_files
    from .engram_ops import _brain_query_engrams_impl
    
    brain = get_brain_path()
    week = _get_week_number()
    
    results = {
        "week": week,
        "dry_run": dry_run,
        "actions": [],
    }
    
    # 1. Archive old tasks
    try:
        gc_result = _garbage_collect_tasks(max_age_hours=168, dry_run=dry_run)  # 7 days
        results["actions"].append({
            "action": "garbage_collect_tasks",
            "archived": gc_result.get("archived_count", 0),
            "kept": gc_result.get("kept_count", 0),
        })
    except Exception as e:
        results["actions"].append({
            "action": "garbage_collect_tasks",
            "error": str(e),
        })
    
    # 2. Archive resolved files
    try:
        archive_result = _archive_resolved_files()
        results["actions"].append({
            "action": "archive_resolved_files",
            "archived": archive_result.get("archived_count", 0),
        })
    except Exception as e:
        results["actions"].append({
            "action": "archive_resolved_files",
            "error": str(e),
        })
    
    # 3. Compute NOOP ratio from hook metrics
    try:
        from .engram_hooks import get_hook_metrics_summary
        hooks = get_hook_metrics_summary(brain)
        outcomes = hooks.get("outcomes", {})
        total = sum(outcomes.values())
        noops = outcomes.get("NOOP", 0)
        noop_ratio = noops / total if total > 0 else 0
        
        results["noop_ratio"] = noop_ratio
        if noop_ratio > 0.5:
            results["warning"] = f"NOOP ratio is {noop_ratio:.0%} — tighten write triggers"
    except Exception as e:
        results["noop_ratio"] = None
        results["noop_error"] = str(e)
    
    # 4. Generate weekly synthesis (summary of top engrams this week)
    try:
        from .morning_brief_ops import _retrieve_top_engrams
        top = _retrieve_top_engrams(brain, limit=20)
        engrams = top.get("engrams", [])
        
        if engrams and not dry_run:
            from .engram_ops import _brain_write_engram_impl
            synthesis = "; ".join([e["key"] for e in engrams[:10]])
            _brain_write_engram_impl(
                key=f"week_{week}_synthesis",
                value=f"Week {week} top themes: {synthesis}",
                context="Strategy",
                intensity=8,
            )
            results["actions"].append({
                "action": "weekly_synthesis",
                "written": True,
                "themes_count": len(engrams[:10]),
            })
    except Exception as e:
        results["actions"].append({
            "action": "weekly_synthesis",
            "error": str(e),
        })
    
    return results
