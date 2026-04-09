"""Goal Tracker — Persistent goal tracking across verification iterations.

Tier 5 produces point-in-time signals. This module persists them across
iterations so we can measure progression: "attempt 2 got closer",
"goal finally met on attempt 5."

Storage: .brain/driver/goals.jsonl (append-only)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.goal_tracker")


def _goals_path(project_root: Path) -> Path:
    """Return path to goals JSONL file, creating dir if needed."""
    p = project_root / ".brain" / "driver" / "goals.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_goals(project_root: Path) -> list[dict]:
    """Load all goal entries from goals.jsonl."""
    gp = _goals_path(project_root)
    if not gp.exists():
        return []
    entries = []
    for line in gp.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_goal(project_root: Path, entry: dict):
    """Append a goal entry to goals.jsonl."""
    gp = _goals_path(project_root)
    with open(gp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _count_attempts(project_root: Path, goal_id: str) -> int:
    """Count existing attempts for a goal."""
    return sum(1 for g in _load_goals(project_root) if g.get("goal_id") == goal_id)


def record_goal_attempt(plan_file: str, verification_result: dict,
                        signals: list[dict], project_root: Path):
    """Called by Tier 5 after each verification. Persists goal progress.

    Args:
        plan_file: Path or name of the plan file.
        verification_result: Full verify_execution result dict.
        signals: List of Tier 5 signal dicts.
        project_root: Project root path.
    """
    for sig in signals:
        if sig.get("tier") != 5:
            continue

        metric = sig.get("metric", sig.get("check", "unknown"))
        goal_id = f"{Path(plan_file).stem}:{metric}"
        attempt = _count_attempts(project_root, goal_id) + 1

        entry = {
            "goal_id": goal_id,
            "plan_file": str(plan_file),
            "metric": metric,
            "attempt": attempt,
            "claimed_delta": sig.get("claimed_delta", 0),
            "actual_delta": sig.get("actual_delta", 0),
            "hit_ratio": sig.get("hit_ratio", 0.0),
            "passed": sig.get("passed", False),
            "ts": datetime.now().isoformat(),
        }
        _append_goal(project_root, entry)

        # Emit events via the event system (best-effort)
        try:
            from .event_ops import _emit_event
            if sig.get("passed"):
                _emit_event("goal_achieved", "goal_tracker", {
                    "goal_id": goal_id,
                    "metric": metric,
                    "attempt": attempt,
                    "hit_ratio": sig.get("hit_ratio", 0.0),
                })
                # Record DPO preference for goal achievement
                _record_goal_dpo(goal_id, plan_file, attempt, project_root)
            else:
                _emit_event("goal_progress", "goal_tracker", {
                    "goal_id": goal_id,
                    "metric": metric,
                    "attempt": attempt,
                    "hit_ratio": sig.get("hit_ratio", 0.0),
                })
                # Catalog failure pattern
                try:
                    from .failure_patterns import catalog_failure
                    catalog_failure(sig, plan_file, project_root)
                except ImportError:
                    pass  # failure_patterns not yet available
        except Exception as e:
            logger.debug(f"Goal event emission failed (non-fatal): {e}")


def _record_goal_dpo(goal_id: str, plan_file: str, attempt: int,
                     project_root: Path):
    """Record a DPO outcome preference when a goal is achieved.

    Uses the existing ArchivePipeline.record_outcome_preference().
    """
    try:
        from .archive_pipeline import ArchivePipeline
        archive = ArchivePipeline(brain_path=project_root / ".brain")
        archive.record_outcome_preference(
            event_type="governance_tier5",
            prompt=f"Goal from {plan_file}",
            response=f"Goal {goal_id} achieved on attempt {attempt}",
            success=True,
            context=goal_id,
        )
    except Exception as e:
        logger.debug(f"DPO recording failed (non-fatal): {e}")


def get_open_goals(project_root: Path) -> list[dict]:
    """Return all goals not yet achieved (latest attempt has passed=False).

    Goals stale >7 days without progress are marked as 'abandoned'.
    """
    goals = _load_goals(project_root)
    if not goals:
        return []

    # Group by goal_id, take latest attempt
    latest: dict[str, dict] = {}
    for g in goals:
        gid = g.get("goal_id", "")
        existing = latest.get(gid)
        if not existing or g.get("attempt", 0) > existing.get("attempt", 0):
            latest[gid] = g

    open_goals = []
    now = time.time()
    for gid, g in latest.items():
        if g.get("passed"):
            continue  # achieved
        # Check staleness
        try:
            ts = datetime.fromisoformat(g["ts"]).timestamp()
            stale_days = (now - ts) / 86400
        except (KeyError, ValueError):
            stale_days = 0
        status = "abandoned" if stale_days > 7 else "open"
        open_goals.append({**g, "status": status, "stale_days": round(stale_days, 1)})

    return open_goals


def get_goal_progress(goal_id: str, project_root: Path) -> list[dict]:
    """Return all attempts for a goal, showing progression."""
    return [g for g in _load_goals(project_root) if g.get("goal_id") == goal_id]


def get_all_goals(project_root: Path) -> list[dict]:
    """Return all goal entries (for CSR computation)."""
    return _load_goals(project_root)
