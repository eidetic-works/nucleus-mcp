"""Dog Food Test Tracker — 30-Day Self-Validation Experiment.

Tracks daily usage metrics for the Nucleus Agent OS as part of the
MVE-1 validation experiment (Experiment 1 from Stage 5).

Metrics tracked:
- pain_if_broken: 1-10 scale (would I miss this if it broke?)
- would_pay: Y/N (would I pay $29/mo for this?)
- decisions_faster: count of decisions made faster via engrams today
- notes: freeform daily notes

Data stored in .brain/experiments/dogfood/daily_log.json
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("nucleus.dogfood")


def get_dogfood_dir(brain_path: Optional[Path] = None) -> Path:
    """Get or create the dogfood experiment directory."""
    if brain_path is None:
        from mcp_server_nucleus.runtime.common import get_brain_path
        brain_path = get_brain_path()
    d = Path(brain_path) / "experiments" / "dogfood"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_daily(
    pain_score: int,
    would_pay: bool = False,
    decisions_faster: int = 0,
    notes: str = "",
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Log a daily dogfood entry.

    Args:
        pain_score: 1-10 scale (how much would it hurt if broken?)
        would_pay: Would you pay $29/mo for this? (Y/N)
        decisions_faster: Number of decisions made faster via engrams today
        notes: Freeform daily notes

    Returns:
        Dict with the logged entry and running averages
    """
    if not 1 <= pain_score <= 10:
        return {"error": "pain_score must be between 1 and 10"}

    d = get_dogfood_dir(brain_path)
    log_file = d / "daily_log.json"

    # Load existing log
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text())
        except (json.JSONDecodeError, Exception):
            entries = []

    today = date.today().isoformat()

    # Check if already logged today — update instead of duplicate
    existing_idx = None
    for i, e in enumerate(entries):
        if e.get("date") == today:
            existing_idx = i
            break

    entry = {
        "date": today,
        "day_number": len(set(e["date"] for e in entries)) + (0 if existing_idx is not None else 1),
        "pain_if_broken": pain_score,
        "would_pay": would_pay,
        "decisions_faster": decisions_faster,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if existing_idx is not None:
        entry["day_number"] = entries[existing_idx]["day_number"]
        entries[existing_idx] = entry
    else:
        entry["day_number"] = len(entries) + 1
        entries.append(entry)

    # Write back
    log_file.write_text(json.dumps(entries, indent=2))

    # Compute running averages
    pain_scores = [e["pain_if_broken"] for e in entries]
    pay_yes = sum(1 for e in entries if e.get("would_pay"))
    total_faster = sum(e.get("decisions_faster", 0) for e in entries)

    avg_pain = sum(pain_scores) / len(pain_scores) if pain_scores else 0
    trend = "↑" if len(pain_scores) >= 3 and pain_scores[-1] > pain_scores[-3] else (
        "↓" if len(pain_scores) >= 3 and pain_scores[-1] < pain_scores[-3] else "→"
    )

    return {
        "entry": entry,
        "summary": {
            "total_days": len(entries),
            "avg_pain_score": round(avg_pain, 1),
            "pain_trend": trend,
            "would_pay_rate": f"{pay_yes}/{len(entries)} ({round(pay_yes/len(entries)*100)}%)" if entries else "0/0",
            "total_decisions_faster": total_faster,
            "target_pain": 8,
            "on_track": avg_pain >= 6,
        },
        "kill_gate": {
            "status": "SAFE" if avg_pain >= 5 else "AT RISK",
            "threshold": "Pain < 5/10 after 30 days = KILL",
            "current_avg": round(avg_pain, 1),
            "days_remaining": max(0, 30 - len(entries)),
        },
    }


def get_status(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get the current dogfood experiment status."""
    d = get_dogfood_dir(brain_path)
    log_file = d / "daily_log.json"

    if not log_file.exists():
        return {
            "status": "NOT STARTED",
            "message": "Run `nucleus dogfood log <score>` to start the 30-day test.",
            "total_days": 0,
        }

    try:
        entries = json.loads(log_file.read_text())
    except (json.JSONDecodeError, Exception):
        return {"status": "ERROR", "message": "Corrupted log file"}

    if not entries:
        return {"status": "NOT STARTED", "total_days": 0}

    pain_scores = [e["pain_if_broken"] for e in entries]
    pay_yes = sum(1 for e in entries if e.get("would_pay"))
    avg_pain = sum(pain_scores) / len(pain_scores)
    total_faster = sum(e.get("decisions_faster", 0) for e in entries)

    # Build sparkline
    sparkline = ""
    bars = "▁▂▃▄▅▆▇█"
    for score in pain_scores[-14:]:  # last 14 days
        idx = min(int((score - 1) / 9 * 8), 7)
        sparkline += bars[idx]

    status = "RUNNING" if len(entries) < 30 else "COMPLETE"
    verdict = None
    if len(entries) >= 30:
        verdict = "GO ✅" if avg_pain >= 8 else ("BORDERLINE ⚠️" if avg_pain >= 5 else "KILL ❌")

    return {
        "status": status,
        "total_days": len(entries),
        "days_remaining": max(0, 30 - len(entries)),
        "avg_pain_score": round(avg_pain, 1),
        "latest_pain": pain_scores[-1] if pain_scores else 0,
        "sparkline": sparkline,
        "would_pay_rate": f"{pay_yes}/{len(entries)}",
        "total_decisions_faster": total_faster,
        "kill_gate": {
            "threshold": 5,
            "current": round(avg_pain, 1),
            "status": "SAFE" if avg_pain >= 5 else "AT RISK",
        },
        "verdict": verdict,
        "last_entry": entries[-1] if entries else None,
    }


def format_status(status: Dict) -> str:
    """Format dogfood status for terminal output."""
    lines = []
    lines.append("=" * 60)
    lines.append("  🐕 DOG FOOD TEST — 30-Day Experiment")
    lines.append("=" * 60)
    lines.append("")

    if status["status"] == "NOT STARTED":
        lines.append("  Status: NOT STARTED")
        lines.append("  Run: nucleus dogfood log <score> to begin")
        lines.append("=" * 60)
        return "\n".join(lines)

    day = status["total_days"]
    remaining = status["days_remaining"]
    avg = status["avg_pain_score"]
    spark = status.get("sparkline", "")
    gate = status["kill_gate"]

    lines.append(f"  Day: {day}/30 ({remaining} remaining)")
    lines.append(f"  Avg Pain Score: {avg}/10 (target: ≥8)")
    lines.append(f"  Latest: {status['latest_pain']}/10")
    lines.append(f"  Trend: {spark}")
    lines.append(f"  Would Pay: {status['would_pay_rate']}")
    lines.append(f"  Decisions Faster: {status['total_decisions_faster']}")
    lines.append("")
    lines.append(f"  Kill Gate: {'🟢 SAFE' if gate['status'] == 'SAFE' else '🔴 AT RISK'}")
    lines.append(f"    Threshold: Pain < {gate['threshold']}/10 = KILL")
    lines.append(f"    Current:   {gate['current']}/10")

    if status.get("verdict"):
        lines.append("")
        lines.append(f"  🏁 VERDICT: {status['verdict']}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
