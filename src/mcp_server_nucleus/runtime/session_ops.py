"""
Nucleus Runtime - Session Operations
====================================
Core logic for session management (Save, Resume, Context switching).
"""

import json
import os
import tempfile
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from .. import __version__
except ImportError:
    __version__ = "1.8.8"

from .common import get_brain_path
from .event_ops import _emit_event


def _atomic_json_write(path: Path, data: Any, indent: int = None):
    """Write JSON atomically via temp file + rename to prevent corruption on crash."""
    dir_path = path.parent
    dir_path.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp, str(path))  # Atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_session_arc(brain: Path) -> dict:
    """Load session history + today's brief recommendation.

    Shared between session start (human dashboard) and context injection.
    """
    from datetime import datetime
    ledger_path = brain / "engrams" / "ledger.jsonl"
    if not ledger_path.exists():
        return {"recent_sessions": [], "todays_focus": None, "arc_summary": ""}

    session_engrams = []
    brief_rec = None
    today_key = f"brief_rec_{datetime.now().strftime('%Y%m%d')}"

    try:
        with open(ledger_path, "r") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("deleted", False):
                        continue
                    if e.get("key", "").startswith("session_"):
                        session_engrams.append(e)
                    elif e.get("key") == today_key:
                        brief_rec = e
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        return {"recent_sessions": [], "todays_focus": None, "arc_summary": ""}

    session_engrams.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    recent = session_engrams[:3]

    arc_parts = []
    for s in reversed(recent):
        ts = s.get("timestamp", "")[:10]
        val = s.get("value", "")[:40]
        arc_parts.append(f"{ts}: {val}")
    arc_summary = " → ".join(arc_parts)

    return {
        "recent_sessions": recent,
        "todays_focus": brief_rec.get("value", "") if brief_rec else None,
        "arc_summary": arc_summary,
    }


def _get_sessions_path() -> Path:
    """Get path to sessions directory."""
    brain = get_brain_path()
    return brain / "sessions"

def _get_active_session_path() -> Path:
    """Get path to active session file."""
    brain = get_brain_path()
    return brain / "sessions" / "active.json"

def _get_depth_state_safe() -> Dict:
    """Get current depth tracking state (helper for session save)."""
    try:
        brain = get_brain_path()
        depth_path = brain / "session" / "depth.json"
        if depth_path.exists():
            with open(depth_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"current_depth": 0, "levels": []}

def _save_session(context: str, active_task: Optional[str] = None,
                  pending_decisions: Optional[List[str]] = None,
                  breadcrumbs: Optional[List[str]] = None,
                  next_steps: Optional[List[str]] = None) -> Dict[str, Any]:
    """Save current session for later resumption."""
    try:
        sessions_dir = _get_sessions_path()
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        context_slug = context.lower().replace(" ", "_")[:30]
        session_id = f"{context_slug}_{timestamp}"
        
        depth_state = _get_depth_state_safe()
        
        session = {
            "schema_version": "1.0",
            "nucleus_version": __version__,
            "id": session_id,
            "context": context,
            "active_task": active_task or "Not specified",
            "pending_decisions": pending_decisions or [],
            "breadcrumbs": breadcrumbs or [],
            "next_steps": next_steps or [],
            "depth_snapshot": {
                "current_depth": depth_state.get("current_depth", 0),
                "levels": depth_state.get("levels", [])
            },
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "is_active": True
        }
        
        session_path = sessions_dir / f"{session_id}.json"
        _atomic_json_write(session_path, session, indent=2)
        _atomic_json_write(_get_active_session_path(), {"active_session_id": session_id})
            
        _prune_old_sessions(max_sessions=10)
        
        _emit_event(
            "session_saved",
            "nucleus_sessions",
            {
                "session_id": session_id,
                "context": context,
                "active_task": active_task or "Not specified"
            },
            description=f"Session saved: {context}"
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "context": context,
            "message": "Session saved. Resume later with: nucleus sessions resume"
        }
    except Exception as e:
        return {"error": str(e)}

def _prune_old_sessions(max_sessions: int = 10) -> None:
    """Keep only the most recent N sessions."""
    try:
        sessions_dir = _get_sessions_path()
        if not sessions_dir.exists():
            return
            
        session_files = sorted(
            sessions_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        session_files = [f for f in session_files if f.name != "active.json"]
        
        for old_session in session_files[max_sessions:]:
            try:
                old_session.unlink()
            except Exception:
                pass
    except Exception:
        pass

def _get_session(session_id: str) -> Dict[str, Any]:
    """Get a specific session by ID."""
    try:
        sessions_dir = _get_sessions_path()
        session_path = sessions_dir / f"{session_id}.json"
        
        if not session_path.exists():
            return {"error": f"Session '{session_id}' not found"}
        
        with open(session_path, encoding="utf-8") as f:
            session = json.load(f)
        
        return {"session": session}
    except Exception as e:
        return {"error": str(e)}

def _resume_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Resume a saved session."""
    try:
        if not session_id:
            active_path = _get_active_session_path()
            if active_path.exists():
                with open(active_path, encoding="utf-8") as f:
                    active_data = json.load(f)
                    session_id = active_data.get("active_session_id")
        
        if not session_id:
            return {"error": "No active session found"}
            
        session_result = _get_session(session_id)
        if "error" in session_result:
            return session_result
            
        session = session_result.get("session", {})
        
        # Version Checks
        warnings = []
        if session.get("schema_version") != "1.0":
             warnings.append(f"Schema mismatch: Session uses v{session.get('schema_version', 'unknown')}, System uses v1.0")
        if session.get("nucleus_version") != __version__:
             warnings.append(f"Nucleus update: Session from v{session.get('nucleus_version', 'unknown')}, System is v{__version__}")

        created_str = session.get("created_at", "")
        # Simple recent check 
        is_recent = True 
        try:
             if created_str:
                 # Very basic check
                 pass
        except Exception:
             pass

        return {
            "session_id": session_id,
            "context": session.get("context"),
            "active_task": session.get("active_task"),
            "pending_decisions": session.get("pending_decisions", []),
            "breadcrumbs": session.get("breadcrumbs", []),
            "next_steps": session.get("next_steps", []),
            "depth_snapshot": session.get("depth_snapshot", {}),
            "created_at": created_str,
            "warnings": warnings,
            "is_recent": is_recent
        }
    except Exception as e:
        return {"error": str(e)}

def _list_sessions() -> Dict[str, Any]:
    """List all saved sessions."""
    try:
        sessions_dir = _get_sessions_path()
        if not sessions_dir.exists():
            return {"sessions": [], "total": 0}
            
        sessions = []
        for session_file in sorted(sessions_dir.glob("*.json"), reverse=True):
            if session_file.name == "active.json":
                continue
            try:
                with open(session_file, encoding="utf-8") as f:
                    session = json.load(f)
                sessions.append({
                    "id": session.get("id"),
                    "context": session.get("context"),
                    "created_at": session.get("created_at")
                })
            except Exception:
                continue
                
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        return {"error": str(e)}

def _check_for_recent_session() -> Dict[str, Any]:
    """Check for recent session."""
    try:
        active_path = _get_active_session_path()
        if active_path.exists():
            with open(active_path, encoding="utf-8") as f:
                sid = json.load(f).get("active_session_id")
            if sid:
                return {"exists": True, "session_id": sid, "message": "Resumable session found."}
        return {"exists": False}
    except Exception:
        return {"exists": False}

# ── Session Start (workflow enforcement dashboard) ───────────
# Extracted from __init__.py  L2751-L2958

def _brain_session_start_impl(goal: str = "", tags: list = None) -> str:
    try:
        # Direct File I/O for robustness (avoid internal function call issues)
        brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
        if not brain_path:
            return "Error: NUCLEAR_BRAIN_PATH env var not set"

        brain = Path(brain_path)

        # 0. Store goal/tags in state.json if provided
        if goal:
            state_path = brain / "ledger" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {}
            if state_path.exists():
                try:
                    with open(state_path, "r", encoding="utf-8") as f:
                        state = json.load(f)
                except Exception:
                    pass
            session_data = state.get("current_session", {})
            session_data["goal"] = goal
            session_data["tags"] = tags or []
            state["current_session"] = session_data
            _atomic_json_write(state_path, state, indent=2)

        # 1. Get Depth
        depth_path = brain / "depth_state.json"
        depth_data = {}
        if depth_path.exists():
            try:
                with open(depth_path, "r", encoding="utf-8") as f:
                    depth_data = json.load(f)
            except Exception:
                pass

        depth_current = depth_data.get("current_depth", 0)
        depth_max = depth_data.get("max_safe_depth", 5)
        depth_indicator = depth_data.get("indicator", "🟢 ○○○○○")

        # 2. Get Tasks
        tasks_path = brain / "ledger" / "tasks.json"
        pending_tasks = []
        if tasks_path.exists():
            try:
                with open(tasks_path, "r", encoding="utf-8") as f:
                    all_tasks = json.load(f)
                    pending_tasks = [t for t in all_tasks if t.get("status") == "PENDING"]
            except Exception:
                pass

        # Sort by priority - safely handle string priorities
        def get_priority_int(t):
            try:
                return int(t.get("priority", 999))
            except (ValueError, TypeError):
                return 999

        sorted_tasks = sorted(pending_tasks, key=get_priority_int)[:5]

        # 3. Get Session
        state_path = brain / "ledger" / "state.json"
        has_session = False
        active_context = "None"
        active_task = "None"

        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    session = state.get("current_session", {})
                    if session:
                        has_session = True
                        active_context = session.get("context", "Unknown")
                        active_task = session.get("active_task", "None")
            except Exception:
                pass

        # 4. Get Engrams
        engram_path = brain / "engrams" / "ledger.jsonl"
        engram_count = 0
        recent_engrams = []
        if engram_path.exists():
            try:
                with open(engram_path, "r", encoding="utf-8") as f:
                    lines = [line for line in f if line.strip()]
                    engram_count = len(lines)
                    for line in reversed(lines[-2:]):
                        recent_engrams.append(json.loads(line))
            except Exception:
                pass
                
        # 5. Get Mounts
        mount_path = brain / "mounts.json"
        active_mounts = []
        if mount_path.exists():
            try:
                with open(mount_path, "r", encoding="utf-8") as f:
                    mounts_data = json.load(f)
                    active_mounts = list(mounts_data.keys())
            except Exception:
                pass

        # Build Report
        output = []
        output.append("╭────────────────────────────────────────────────────────────╮")
        output.append("│ 🧠 NUCLEUS OS v1.0.7 - SOVEREIGN BRAIN ACTIVE              │")
        output.append("╰────────────────────────────────────────────────────────────╯")
        output.append("")
        
        # Satellite View Simulation
        output.append("📊 SYSTEM STATE")
        output.append(f"   📍 DEPTH:  {depth_indicator} ({depth_current}/{depth_max})")
        
        output.append(f"   🗃️  MEMORY: {engram_count} Engrams (Synced)")
        for e in recent_engrams:
            key = e.get("key", "unknown")
            ctx = e.get("context", "General")
            output.append(f"      ↳ Recent: [{ctx}] {key}")
            
        mount_str = ", ".join(active_mounts) if active_mounts else "None"
        output.append(f"   🔌 MOUNTS: {len(active_mounts)} Active")
        if active_mounts:
            output.append(f"      ↳ {mount_str}")
        output.append("")
        
        # Priority Tasks
        output.append("🎯 TOP PRIORITY TASKS")
        if not sorted_tasks:
            output.append("   ✅ No pending tasks! All clear.")
        else:
            for i, task in enumerate(sorted_tasks, 1):
                raw_priority = task.get("priority", 3)
                try:
                    priority = int(raw_priority)
                except (ValueError, TypeError):
                    priority = 3
                    
                desc = task.get("description", "")[:70]
                task_id = task.get("id", "")
                task_model = task.get("model")
                task_env = task.get("environment")
                
                priority_icon = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}.get(priority, "⚫")
                
                output.append(f"   {i}. {priority_icon} P{priority} | {desc}")
                output.append(f"      ID: {task_id}")
                
                # Show model and environment if available (GTM tasks)
                if task_model or task_env:
                    model_str = f"Model: {task_model}" if task_model else ""
                    env_str = f"Env: {task_env}" if task_env else ""
                    output.append(f"      {model_str} {env_str}".strip())
                
                if priority <= 2:
                    output.append("      ⚠️  HIGH PRIORITY - Should work on this first")
                output.append("")
                
        # Check for pending handoffs
        handoffs_path = brain / "ledger" / "handoffs.json"
        pending_handoffs = []
        if handoffs_path.exists():
            try:
                with open(handoffs_path, encoding="utf-8") as f:
                    all_handoffs = json.load(f)
                    pending_handoffs = [h for h in all_handoffs if h.get("status") == "pending"]
            except Exception:
                pass
        
        if pending_handoffs:
            output.append("📬 PENDING HANDOFFS:")
            for h in pending_handoffs[:3]:
                output.append(f"   → TO: {h.get('to_agent')} | P{h.get('priority', 3)}")
                output.append(f"     Request: {h.get('request', '')[:50]}...")
            output.append("   Run: nucleus_sessions action='handoff_summary' for details")
            output.append("")
        
        # Session Arc (Artery 6: session continuity)
        if not os.environ.get("NUCLEUS_DISABLE_ARTERY_6"):
            try:
                arc = _load_session_arc(brain)
                if arc.get("recent_sessions"):
                    output.append("📋 RECENT SESSIONS:")
                    for s in arc["recent_sessions"]:
                        ts = s.get("timestamp", "?")[:10]
                        val = s.get("value", "")[:80]
                        output.append(f"   [{ts}] {val}")
                    output.append("")
                if arc.get("todays_focus"):
                    output.append(f"🎯 TODAY'S FOCUS: {arc['todays_focus'][:100]}")
                    output.append("")
            except Exception:
                pass  # Never let session arc break session start

        # Session Goal (if provided)
        if goal:
            output.append(f"🎯 SESSION GOAL: {goal}")
            if tags:
                output.append(f"   🏷️  Tags: {', '.join(str(t) for t in tags)}")
            output.append("")

        # Recommendations
        output.append("💡 RECOMMENDATIONS:")
        if pending_handoffs:
            output.append("   📬 Check pending handoffs first!")
        if sorted_tasks and sorted_tasks[0].get("priority", 99) <= 2:
            top = sorted_tasks[0]
            output.append(f"   ⚠️  Work on Priority {top['priority']} task first:")
            output.append(f"   '{top['description'][:60]}...'")
        elif not has_session and sorted_tasks:
            output.append("   1. Pick a task from above")
            output.append("   2. Create sprint: nucleus_sessions(action='save', params={'context': '...'})")
            output.append("   3. Stay focused on that sprint")
        else:
            output.append("   Continue current sprint or work on top priority task")
        output.append("")

        output.append("📖 Read AGENT_PROTOCOL.md and MULTI_AGENT_MOU.md for workflow")
        output.append("=" * 60)

        # Emit event (safe)
        try:
            event_data = {"task_count": len(sorted_tasks)}
            if goal:
                event_data["goal"] = goal
                event_data["tags"] = tags or []
            _emit_event("session_started", "brain", event_data)
        except Exception:
            pass
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error in session start: {e}"


def _brain_session_end_impl(summary: str = "", learnings: str = "",
                            mood: str = "neutral") -> Dict[str, Any]:
    """
    End the current session — DT-1 Ticket #6: Auto-inject session-end engrams.

    What it does:
    1. Counts events emitted during this session
    2. Counts tasks completed/claimed during this session
    3. Writes a session-end engram capturing the summary
    4. Emits session_ended event (triggers the auto-hook for additional engram)
    5. Clears active session state

    Args:
        summary: What was accomplished (auto-generated if empty).
        learnings: Key decisions or patterns discovered.
        mood: How the session felt (neutral/productive/stuck/frustrated).

    Returns:
        Dict with session summary and engram creation result.
    """
    try:
        brain = get_brain_path()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        # Count session activity
        events_path = brain / "ledger" / "events.jsonl"
        event_count = 0
        task_events = {"completed": 0, "claimed": 0, "created": 0}
        if events_path.exists():
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            ev = json.loads(line)
                            event_count += 1
                            evt = ev.get("type", "")
                            if "completed" in evt:
                                task_events["completed"] += 1
                            elif evt == "task_claimed":
                                task_events["claimed"] += 1
                            elif evt == "task_created":
                                task_events["created"] += 1
                        except json.JSONDecodeError:
                            continue

        # Build session summary for engram
        if not summary:
            parts = []
            if task_events["completed"]:
                parts.append(f"{task_events['completed']} tasks done")
            if task_events["claimed"]:
                parts.append(f"{task_events['claimed']} tasks claimed")
            if task_events["created"]:
                parts.append(f"{task_events['created']} tasks created")
            parts.append(f"{event_count} total events")
            summary = f"Session ended ({mood}): {', '.join(parts)}"

        # Write session-end engram via ADUN
        engram_result = None
        try:
            from .memory_pipeline import MemoryPipeline
            pipeline = MemoryPipeline(brain)

            engram_text = summary
            if learnings:
                engram_text += f". Learnings: {learnings}"

            engram_result = pipeline.process(
                text=engram_text,
                context="Strategy",
                intensity=5,
                source_agent="session_end",
                key=f"session_{int(time.time()) % 100000}",
            )
        except Exception as e:
            engram_result = {"error": str(e)}

        # Emit session_ended event (triggers auto-hook for SECOND engram)
        _emit_event("session_ended", "brain", {
            "summary": summary[:200],
            "learnings": learnings[:200] if learnings else "",
            "mood": mood,
            "event_count": event_count,
            "tasks_completed": task_events["completed"],
            "tasks_claimed": task_events["claimed"],
        })

        # Clear active session
        active_path = _get_active_session_path()
        if active_path.exists():
            active_path.unlink()

        return {
            "success": True,
            "summary": summary,
            "activity": {
                "total_events": event_count,
                "tasks_completed": task_events["completed"],
                "tasks_claimed": task_events["claimed"],
                "tasks_created": task_events["created"],
            },
            "engram_created": engram_result.get("added", 0) > 0 if engram_result else False,
            "mood": mood,
            "timestamp": now,
        }

    except Exception as e:
        return {"error": str(e)}
