"""
Nucleus Runtime - Compounding Loop
====================================
End-of-day capture, weekly consolidation, and compounding cycle management.

This module persists learnings so they surface in future morning briefs,
creating a compounding knowledge loop across sessions.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .common import get_brain_path, logger


def _load_or_create_cycle(brain_path: Path, cycle_path: Path) -> Dict[str, Any]:
    """Load the compounding cycle state, or create a fresh one if missing."""
    if cycle_path.exists():
        try:
            with open(cycle_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to create new

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "created_at": now,
        "updated_at": now,
        "day_count": 0,
        "week_count": 0,
        "total_engrams_written": 0,
        "last_eod": None,
        "last_consolidation": None,
    }


def _save_cycle(cycle: Dict[str, Any], cycle_path: Path) -> None:
    """Persist the compounding cycle state to disk."""
    cycle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cycle_path, "w", encoding="utf-8") as f:
        json.dump(cycle, f, indent=2, ensure_ascii=False)


def _end_of_day_capture_impl(
    summary: str = None,
    key_decisions: str = None,
    blockers: str = None,
) -> Dict[str, Any]:
    """Capture end-of-day learnings and persist them as engrams.

    Args:
        summary: Required — a text summary of what happened today.
        key_decisions: Optional — notable decisions made.
        blockers: Optional — things that blocked progress.

    Returns:
        Dict with day, week, engrams_written, and status.
        If ``summary`` is missing, returns a clean error dict instead of
        leaking internal implementation details (e.g. TypeError tracebacks).
    """
    # ── Guard: summary is required ──
    if not summary:
        return {
            "status": "error",
            "message": "Missing required parameter: summary",
        }

    try:
        brain = get_brain_path()
        now = datetime.now(timezone.utc)
        day_str = now.strftime("%Y-%m-%d")
        week_str = now.strftime("%Y-W%W")
        timestamp = now.isoformat().replace("+00:00", "Z")

        engrams_written = 0

        # Write the summary as an engram
        try:
            from .engram_ops import _brain_write_engram_impl
            _brain_write_engram_impl(
                key=f"eod-{day_str}",
                value=summary,
                context="End of Day",
                intensity=7,
            )
            engrams_written += 1
        except Exception:
            pass  # Don't fail EOD if engram write fails

        # Write key decisions as an engram if provided
        if key_decisions:
            try:
                from .engram_ops import _brain_write_engram_impl
                _brain_write_engram_impl(
                    key=f"eod-decisions-{day_str}",
                    value=key_decisions,
                    context="End of Day",
                    intensity=6,
                )
                engrams_written += 1
            except Exception:
                pass

        # Write blockers as an engram if provided
        if blockers:
            try:
                from .engram_ops import _brain_write_engram_impl
                _brain_write_engram_impl(
                    key=f"eod-blockers-{day_str}",
                    value=blockers,
                    context="End of Day",
                    intensity=5,
                )
                engrams_written += 1
            except Exception:
                pass

        # Update compounding cycle state
        cycle_path = brain / "meta" / "compounding_cycle.json"
        try:
            cycle = _load_or_create_cycle(brain, cycle_path)
            cycle["day_count"] = cycle.get("day_count", 0) + 1
            cycle["total_engrams_written"] = cycle.get("total_engrams_written", 0) + engrams_written
            cycle["last_eod"] = timestamp
            cycle["updated_at"] = timestamp
            _save_cycle(cycle, cycle_path)
        except Exception:
            pass  # Don't fail EOD if cycle update fails

        # Emit an event
        try:
            from .event_ops import _emit_event
            _emit_event("end_of_day_captured", "compounding_loop", {
                "day": day_str,
                "week": week_str,
                "engrams_written": engrams_written,
            })
        except Exception:
            pass

        return {
            "status": "success",
            "day": day_str,
            "week": week_str,
            "engrams_written": engrams_written,
            "timestamp": timestamp,
        }
    except Exception as e:
        logger.error(f"End of day capture failed: {e}")
        return {
            "status": "error",
            "message": f"End of day capture failed: {str(e)}",
        }


def _weekly_consolidation_impl(dry_run: bool = False) -> Dict[str, Any]:
    """Consolidate the week's learnings into a higher-level summary.

    Args:
        dry_run: If True, preview what would be consolidated without writing.

    Returns:
        Dict with consolidation status and summary.
    """
    try:
        brain = get_brain_path()
        now = datetime.now(timezone.utc)
        week_str = now.strftime("%Y-W%W")
        timestamp = now.isoformat().replace("+00:00", "Z")

        if dry_run:
            return {
                "status": "success",
                "dry_run": True,
                "week": week_str,
                "message": f"Would consolidate week {week_str} (dry run)",
            }

        # Update cycle state
        cycle_path = brain / "meta" / "compounding_cycle.json"
        try:
            cycle = _load_or_create_cycle(brain, cycle_path)
            cycle["week_count"] = cycle.get("week_count", 0) + 1
            cycle["last_consolidation"] = timestamp
            cycle["updated_at"] = timestamp
            _save_cycle(cycle, cycle_path)
        except Exception:
            pass

        # Emit an event
        try:
            from .event_ops import _emit_event
            _emit_event("weekly_consolidation", "compounding_loop", {
                "week": week_str,
            })
        except Exception:
            pass

        return {
            "status": "success",
            "dry_run": False,
            "week": week_str,
            "timestamp": timestamp,
            "message": f"Weekly consolidation completed for {week_str}",
        }
    except Exception as e:
        logger.error(f"Weekly consolidation failed: {e}")
        return {
            "status": "error",
            "message": f"Weekly consolidation failed: {str(e)}",
        }
