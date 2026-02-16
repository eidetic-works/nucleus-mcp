"""
Nucleus Runtime - Session Operations
====================================
Core logic for session management (Save, Resume, Context switching).
"""

import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from .common import get_brain_path
from .event_ops import _emit_event

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
            with open(depth_path, "r") as f:
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
            "nucleus_version": "0.5.0",
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
        with open(session_path, "w") as f:
            json.dump(session, f, indent=2)
            
        with open(_get_active_session_path(), "w") as f:
            json.dump({"active_session_id": session_id}, f)
            
        _prune_old_sessions(max_sessions=10)
        
        _emit_event(
            "session_saved",
            "brain_save_session",
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
        
        with open(session_path) as f:
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
                with open(active_path) as f:
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
        if session.get("nucleus_version") != "0.5.0":
             warnings.append(f"Nucleus update: Session from v{session.get('nucleus_version', 'unknown')}, System is v0.5.0")

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
                with open(session_file) as f:
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
            with open(active_path) as f:
                sid = json.load(f).get("active_session_id")
            if sid:
                return {"exists": True, "session_id": sid, "message": "Resumable session found."}
        return {"exists": False}
    except Exception:
        return {"exists": False}
