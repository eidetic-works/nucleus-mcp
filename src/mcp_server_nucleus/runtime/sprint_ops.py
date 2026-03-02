"""Sprint / Mission Operations — Autopilot sprint MCP tool implementations.

Extracted from __init__.py (Phase 4 Autopilot Sprint tools).
Contains:
- _get_autopilot_engine: Singleton for AutopilotEngine
- _brain_autopilot_sprint_v2_impl
- _brain_start_mission_impl
- _brain_mission_status_impl
- _brain_halt_sprint_impl
- _brain_resume_sprint_impl
"""

import logging
from pathlib import Path
import sys
from typing import List

from .common import get_brain_path

logger = logging.getLogger("mcp_server_nucleus")


# Lazy import helper (get_orch lives in __init__.py)
def _get_orch():
    from mcp_server_nucleus import get_orch
    return get_orch()


# ── Singleton ────────────────────────────────────────────────────
_autopilot_engine = None


def _get_autopilot_engine():
    """Get or create AutopilotEngine singleton."""
    global _autopilot_engine
    if _autopilot_engine is None:
        try:
            nop_path = Path(__file__).parent.parent.parent.parent.parent / "nop_v3_refactor"
            if str(nop_path) not in sys.path:
                sys.path.insert(0, str(nop_path))
            
            from nop_core.autopilot import AutopilotEngine
            orch = _get_orch()
            _autopilot_engine = AutopilotEngine(
                orchestrator=orch,
                brain_path=get_brain_path()
            )
        except ImportError:
            _autopilot_engine = None
    return _autopilot_engine


# ── Implementations ──────────────────────────────────────────────

def _brain_autopilot_sprint_v2_impl(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    time_limit_hours: float = None,
    dry_run: bool = False,
) -> str:
    """Internal implementation of enhanced autopilot sprint."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available. Install nop_v3_refactor."
        
        from nop_core.autopilot import SprintMode, format_sprint_result
        
        mode_enum = SprintMode(mode.lower())
        
        result = engine.execute_sprint(
            slots=slots,
            mode=mode_enum,
            halt_on_blocker=halt_on_blocker,
            halt_on_tier_mismatch=halt_on_tier_mismatch,
            max_tasks_per_slot=max_tasks_per_slot,
            budget_limit=budget_limit,
            time_limit_hours=time_limit_hours,
            dry_run=dry_run,
        )
        
        return format_sprint_result(result)
        
    except Exception as e:
        return f"❌ Sprint error: {str(e)}"


def _brain_start_mission_impl(
    name: str,
    goal: str,
    task_ids: List[str],
    slot_ids: List[str] = None,
    budget_limit: float = 10.0,
    time_limit_hours: float = 4.0,
    success_criteria: List[str] = None,
) -> str:
    """Internal implementation of mission start."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        mission = engine.start_mission(
            name=name,
            goal=goal,
            task_ids=task_ids,
            slot_ids=slot_ids,
            budget_limit=budget_limit,
            time_limit_hours=time_limit_hours,
            success_criteria=success_criteria,
        )
        
        return f"""✅ Mission Started
   ID: {mission.id}
   Name: {mission.name}
   Goal: {mission.goal}
   Tasks: {len(mission.tasks)}
   Budget: ${mission.budget_limit:.2f}
   Time Limit: {mission.time_limit_hours}h
   
💡 Use brain_mission_status() to track progress"""
        
    except Exception as e:
        return f"❌ Mission error: {str(e)}"


def _brain_mission_status_impl(mission_id: str = None) -> str:
    """Internal implementation of mission status."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        status = engine.get_mission_status(mission_id)
        
        if "error" in status:
            return f"❌ {status['error']}"
        
        progress = status["progress"]
        budget = status["budget"]
        
        return f"""🎯 Mission Status: {status['name']}
═══════════════════════════════════════
ID: {status['mission_id']}
Status: {status['status'].upper()}

📊 PROGRESS
   ├── Completed: {progress['completed']}/{progress['total']} ({progress['percent']}%)
   └── Elapsed: {status['elapsed']}

💰 BUDGET
   ├── Limit: ${budget['limit']:.2f}
   ├── Spent: ${budget['spent']:.2f}
   └── Remaining: ${budget['remaining']:.2f}"""
        
    except Exception as e:
        return f"❌ Status error: {str(e)}"


def _brain_halt_sprint_impl(reason: str = "User requested halt") -> str:
    """Internal implementation of sprint halt."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        result = engine.halt_sprint(reason)
        
        return f"""⛔ Sprint Halt Requested
   Sprint ID: {result.get('sprint_id', 'N/A')}
   Reason: {result['reason']}
   Status: {result['status']}
   
💡 Sprint will complete current task then stop gracefully"""
        
    except Exception as e:
        return f"❌ Halt error: {str(e)}"


def _brain_resume_sprint_impl(sprint_id: str = None) -> str:
    """Internal implementation of sprint resume."""
    try:
        engine = _get_autopilot_engine()
        if engine is None:
            return "❌ AutopilotEngine not available."
        
        from nop_core.autopilot import format_sprint_result
        
        result = engine.resume_sprint(sprint_id)
        
        return format_sprint_result(result)
        
    except Exception as e:
        return f"❌ Resume error: {str(e)}"
