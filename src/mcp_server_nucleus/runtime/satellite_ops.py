"""Satellite View Operations — Unified status dashboard.

Extracted from __init__.py (Satellite View section).
Contains:
- _generate_sparkline
- _get_activity_sparkline
- _get_health_stats
- _get_satellite_view
- _format_satellite_cli
"""

import json
import time
from typing import Dict, List

from .common import get_brain_path


def _lazy(name):
    import mcp_server_nucleus as m
    return getattr(m, name)


def _generate_sparkline(counts: List[int], chars: str = "▁▂▃▄▅▆▇█") -> str:
    """Generate a sparkline string from a list of counts."""
    if not counts or max(counts) == 0:
        return "▁" * len(counts) if counts else "▁▁▁▁▁▁▁"
    
    max_val = max(counts)
    scale = (len(chars) - 1) / max_val
    return "".join(chars[int(c * scale)] for c in counts)


def _get_activity_sparkline(days: int = 7) -> Dict:
    """Get activity sparkline for the last N days from events.jsonl."""
    try:
        brain = get_brain_path()
        
        # Fast path: use precomputed summary if available (Tier 2)
        summary_path = brain / "ledger" / "activity_summary.json"
        if summary_path.exists():
            try:
                from datetime import datetime, timedelta
                with open(summary_path, "r") as f:
                    summary = json.load(f)
                
                # Build counts from summary
                today = datetime.now().date()
                counts = []
                day_labels = []
                for i in range(days - 1, -1, -1):
                    day = (today - timedelta(days=i)).isoformat()
                    counts.append(summary.get("days", {}).get(day, 0))
                    day_labels.append(day)
                
                if sum(counts) > 0:  # Only use if we have data
                    peak_idx = counts.index(max(counts)) if counts else 0
                    peak_day = day_labels[peak_idx] if day_labels else None
                    return {
                        "sparkline": _generate_sparkline(counts),
                        "total_events": sum(counts),
                        "peak_day": peak_day,
                        "days_covered": days,
                        "source": "precomputed"
                    }
            except Exception:
                pass  # Fall through to slow path
        
        # Slow path: read events.jsonl
        events_path = brain / "ledger" / "events.jsonl"
        
        if not events_path.exists():
            return {
                "sparkline": "▁▁▁▁▁▁▁",
                "total_events": 0,
                "peak_day": None,
                "days_covered": days
            }

        
        # Read last 500 events (performance optimization)
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        day_counts = defaultdict(int)
        today = datetime.now().date()
        
        # Read events efficiently (tail approach)
        events = []
        with open(events_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(line)
        
        # Only process last 500 events
        for line in events[-500:]:
            try:
                evt = json.loads(line)
                timestamp = evt.get("timestamp", "")
                if timestamp:
                    # Parse timestamp (format: 2026-01-06T14:00:00+0530)
                    evt_date = timestamp[:10]  # Get YYYY-MM-DD
                    day_counts[evt_date] += 1
            except Exception:
                pass
        
        # Build counts for last N days
        counts = []
        day_labels = []
        for i in range(days - 1, -1, -1):
            day = (today - timedelta(days=i)).isoformat()
            counts.append(day_counts.get(day, 0))
            day_labels.append(day)
        
        # Find peak day
        peak_idx = counts.index(max(counts)) if counts else 0
        peak_day = day_labels[peak_idx] if day_labels else None
        
        return {
            "sparkline": _generate_sparkline(counts),
            "total_events": sum(counts),
            "peak_day": peak_day,
            "days_covered": days
        }
    except Exception as e:
        return {
            "sparkline": "▁▁▁▁▁▁▁",
            "total_events": 0,
            "peak_day": None,
            "error": str(e)
        }


def _get_health_stats() -> Dict:
    """Get brain health statistics."""
    try:
        brain = get_brain_path()
        artifacts_path = brain / "artifacts"
        archive_path = brain / "archive"
        
        # Count artifacts
        artifacts_count = 0
        if artifacts_path.exists():
            artifacts_count = len(list(artifacts_path.rglob("*.md")))
        
        # Count archived files
        archive_count = 0
        if archive_path.exists():
            archive_count = len(list(archive_path.rglob("*")))
        
        # Count stale files (older than 30 days)
        stale_count = 0
        now = time.time()
        thirty_days_ago = now - (30 * 24 * 60 * 60)
        
        if artifacts_path.exists():
            for f in artifacts_path.rglob("*.md"):
                if f.stat().st_mtime < thirty_days_ago:
                    stale_count += 1
        
        return {
            "artifacts_count": artifacts_count,
            "archive_count": archive_count,
            "stale_count": stale_count
        }
    except Exception as e:
        return {
            "artifacts_count": 0,
            "archive_count": 0,
            "stale_count": 0,
            "error": str(e)
        }


def _get_satellite_view(detail_level: str = "standard") -> Dict:
    """
    Get unified satellite view of the brain.
    
    Detail levels:
    - "minimal": depth only (1 file read)
    - "standard": depth + activity + health (3 reads)
    - "full": depth + activity + health + session (4 reads)
    """
    _depth_show = _lazy("_depth_show")
    _get_state = _lazy("_get_state")
    _list_tasks = _lazy("_list_tasks")
    _list_sessions = _lazy("_list_sessions")
    commitment_ledger = _lazy("commitment_ledger")

    result = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "detail_level": detail_level
    }
    
    # Always include depth
    try:
        depth = _depth_show()
        result["depth"] = {
            "current": depth.get("current_depth", 0),
            "max": depth.get("max_safe_depth", 5),
            "breadcrumbs": depth.get("breadcrumbs", ""),
            "indicator": depth.get("indicator", "🟢 ○○○○○")
        }
    except Exception:
        result["depth"] = {
            "current": 0,
            "max": 5,
            "breadcrumbs": "(not tracked)",
            "indicator": "⚪ ○○○○○"
        }
    
    if detail_level == "minimal":
        return result
    
    # Standard: add activity and health
    result["activity"] = _get_activity_sparkline(days=7)
    result["health"] = _get_health_stats()
    
    # Add commitment health (PEFS Phase 2)
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        stats = ledger.get("stats", {})
        result["commitments"] = {
            "total_open": stats.get("total_open", 0),
            "green": stats.get("green_tier", 0),
            "yellow": stats.get("yellow_tier", 0),
            "red": stats.get("red_tier", 0),
            "last_scan": ledger.get("last_scan")
        }
    except Exception:
        result["commitments"] = None
    
    if detail_level == "standard":
        return result
    
    # Sprint: add current sprint and active tasks
    if detail_level in ("sprint", "full"):
        try:
            state = _get_state()
            sprint = state.get("sprint", {})
            result["sprint"] = {
                "name": sprint.get("name", "(no sprint)"),
                "focus": sprint.get("focus", ""),
                "status": sprint.get("status", "")
            }
            
            # Get active tasks (top 3 priority)
            try:
                tasks = _list_tasks()
                active_tasks = [t for t in tasks if t.get("status") in ("READY", "IN_PROGRESS")][:3]
                result["active_tasks"] = [
                    {"id": t.get("id", ""), "description": t.get("description", "")[:40]}
                    for t in active_tasks
                ]
            except Exception:
                result["active_tasks"] = []
        except Exception:
            result["sprint"] = None
            result["active_tasks"] = []
    
    if detail_level == "sprint":
        return result
    
    # Full: add session info
    try:
        sessions = _list_sessions()
        if sessions:
            latest = sessions[0]
            result["session"] = {
                "id": latest.get("session_id", ""),
                "context": latest.get("context", ""),
                "active_task": latest.get("active_task", ""),
                "saved_at": latest.get("saved_at", "")
            }
        else:
            result["session"] = None
    except Exception:
        result["session"] = None
    
    return result


def _format_satellite_cli(view: Dict) -> str:
    """Format satellite view for CLI output."""
    lines = []
    
    # Header
    lines.append("╭─────────────────────────────────────────────────────────╮")
    lines.append("│  🧠 NUCLEUS SATELLITE VIEW                              │")
    lines.append("├─────────────────────────────────────────────────────────┤")
    lines.append("│                                                         │")
    
    # Depth
    depth = view.get("depth", {})
    indicator = depth.get("indicator", "⚪ ○○○○○")
    breadcrumbs = depth.get("breadcrumbs", "(not tracked)")
    # Truncate breadcrumbs if too long
    if len(breadcrumbs) > 45:
        breadcrumbs = breadcrumbs[:42] + "..."
    lines.append(f"│  📍 DEPTH: {indicator:<45} │")
    lines.append(f"│     {breadcrumbs:<52} │")
    lines.append("│                                                         │")
    
    # Activity (if present)
    activity = view.get("activity")
    if activity:
        sparkline = activity.get("sparkline", "▁▁▁▁▁▁▁")
        total = activity.get("total_events", 0)
        peak = activity.get("peak_day", "")
        if peak:
            peak_short = peak[5:]  # Remove year, show MM-DD
        else:
            peak_short = "N/A"
        lines.append(f"│  📈 ACTIVITY (7d): {sparkline}  ({total} events, peak: {peak_short:<5}) │")
        lines.append("│                                                         │")
    
    # Sprint (if present)
    sprint = view.get("sprint")
    if sprint:
        sprint_name = sprint.get("name", "(no sprint)")[:40]
        sprint_focus = sprint.get("focus", "")[:40]
        lines.append(f"│  🎯 SPRINT: {sprint_name:<45} │")
        if sprint_focus:
            lines.append(f"│     Focus: {sprint_focus:<46} │")
        
        # Active tasks (if present)
        active_tasks = view.get("active_tasks", [])
        if active_tasks:
            lines.append("│     Tasks:                                              │")
            for task in active_tasks[:3]:
                task_desc = task.get("description", "")[:42]
                lines.append(f"│       • {task_desc:<49} │")
        lines.append("│                                                         │")
    
    # Session (if present)
    session = view.get("session")
    if session:
        context = session.get("context", "(none)")[:40]
        task = session.get("active_task", "(none)")[:40]
        lines.append(f"│  🔥 SESSION: {context:<44} │")
        lines.append(f"│     Task: {task:<47} │")
        lines.append("│                                                         │")
    
    # Health (if present)
    health = view.get("health")
    if health:
        artifacts = health.get("artifacts_count", 0)
        archived = health.get("archive_count", 0)
        stale = health.get("stale_count", 0)
        lines.append("│  🏥 HEALTH                                              │")
        lines.append(f"│     Artifacts: {artifacts} active | {archived} archived{' ' * (28 - len(str(artifacts)) - len(str(archived)))} │")
        if stale > 0:
            lines.append(f"│     ⚠️  {stale} stale files (30+ days){' ' * (36 - len(str(stale)))} │")
        lines.append("│                                                         │")
    
    # Commitments (PEFS - if present)
    commitments = view.get("commitments")
    if commitments:
        total = commitments.get("total_open", 0)
        green = commitments.get("green", 0)
        yellow = commitments.get("yellow", 0)
        red = commitments.get("red", 0)
        
        # Mental load indicator
        if red > 0:
            load = "🔴"
        elif yellow > 2:
            load = "🟡"
        elif total == 0:
            load = "✨"
        else:
            load = "🟢"
        
        lines.append(f"│  🎯 COMMITMENTS {load}                                       │")
        lines.append(f"│     Open loops: {total} (🟢{green} 🟡{yellow} 🔴{red}){' ' * (27 - len(str(total)) - len(str(green)) - len(str(yellow)) - len(str(red)))} │")
        lines.append("│                                                         │")
    
    # Footer
    lines.append("╰─────────────────────────────────────────────────────────╯")
    
    return "\n".join(lines)
