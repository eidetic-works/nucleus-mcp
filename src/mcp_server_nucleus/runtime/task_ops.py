"""
Nucleus Runtime - Task Operations (V2)
=====================================
Core logic for task management (CRUD, Claiming, Importing).
Moves task orchestration out of the monolith.
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

# Relative imports assuming this is in mcp_server_nucleus.runtime
from .common import get_brain_path, _get_state
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.task_ops")

def _get_tasks_list() -> List[Dict]:
    """Get the tasks array from tasks.json (V2) or fallback to state.json (V1)."""
    try:
        brain = get_brain_path()
        tasks_path = brain / "ledger" / "tasks.json"

        # Priority 1: Read V2 tasks.json
        if tasks_path.exists():
            with open(tasks_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "tasks" in data:
                    return data["tasks"]
                return data
                
        # Priority 2: Fallback to V1 state.json
        state = _get_state()
        current_sprint = state.get("current_sprint", {})
        return current_sprint.get("tasks", [])
    except Exception as e:
        logger.error(f"Error getting tasks list: {e}")
        return []

def _save_tasks_list(tasks: List[Dict]) -> str:
    """Save the tasks array (prefers V2 tasks.json if it exists)."""
    try:
        brain = get_brain_path()
        tasks_path = brain / "ledger" / "tasks.json"
        
        # Priority 1: Write to V2 tasks.json if it exists (or create it)
        if not tasks_path.exists():
             tasks_path.parent.mkdir(parents=True, exist_ok=True)
             
        with open(tasks_path, "w") as f:
            json.dump(tasks, f, indent=2)
        return "Tasks saved (V2)"
        
    except Exception as e:
        logger.error(f"Error saving tasks list: {e}")
        return f"Error saving tasks: {str(e)}"

def _list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    skill: Optional[str] = None,
    claimed_by: Optional[str] = None
) -> List[Dict]:
    """List tasks with optional filters and external provider merging."""
    try:
        tasks = _get_tasks_list()
        
        # Ensure all tasks have V2 fields (backward compat)
        for task in tasks:
            if "id" not in task:
                task["id"] = f"task-{str(uuid.uuid4())[:8]}"
            if "priority" not in task:
                task["priority"] = 3  # Default medium
            if "blocked_by" not in task:
                task["blocked_by"] = []
            if "required_skills" not in task:
                # Migrate from preferred_role
                if "preferred_role" in task:
                    task["required_skills"] = [task["preferred_role"].lower()]
                else:
                    task["required_skills"] = []
            if "source" not in task:
                task["source"] = "synthesizer"
            if "created_at" not in task:
                task["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            if "updated_at" not in task:
                task["updated_at"] = task["created_at"]
        
        # Merge with Commitment Ledger (PEFS)
        try:
            from mcp_server_nucleus import commitment_ledger
            brain = get_brain_path()
            ledger = commitment_ledger.load_ledger(brain)
            
            for comm in ledger.get("commitments", []):
                comm_status = comm.get("status", "open").lower()
                task_status = "PENDING"
                if comm_status == "closed":
                    task_status = "DONE"
                
                cm_task = {
                    "id": comm["id"],
                    "description": comm["description"],
                    "status": task_status,
                    "priority": comm.get("priority", 3),
                    "blocked_by": [],
                    "required_skills": comm.get("required_skills", []),
                    "source": f"ledger:{comm.get('source', 'unknown')}",
                    "created_at": comm.get("created"),
                    "claimed_by": None
                }
                tasks.append(cm_task)
        except Exception as e:
            logger.warning(f"Failed to merge commitment ledger: {e}")

        # Apply filters
        filtered = tasks
        
        if status:
            status_map = {"TODO": "PENDING", "COMPLETE": "DONE"}
            target_status = status_map.get(status, status)
            filtered = [t for t in filtered if t.get("status", "").upper() == target_status.upper() 
                       or t.get("status", "").upper() == status.upper()]
        
        if priority is not None:
            filtered = [t for t in filtered if t.get("priority") == priority]
        
        if skill:
            filtered = [t for t in filtered if skill.lower() in 
                       [s.lower() for s in t.get("required_skills", [])]]
        
        if claimed_by:
            filtered = [t for t in filtered if claimed_by in str(t.get("claimed_by", ""))]
        
        # Merge with Cloud Tasks (if available)
        try:
            from mcp_server_nucleus.runtime.firestore_bridge import get_bridge
            cloud_tasks = get_bridge().list_cloud_tasks()
            if cloud_tasks:
                local_ids = {t["id"] for t in filtered}
                for ct in cloud_tasks:
                    if ct["id"] not in local_ids:
                        filtered.append(ct)
        except Exception as e:
            logger.warning(f"Failed to merge cloud tasks: {e}")
            pass
        
        # Sort by priority (asc)
        filtered.sort(key=lambda x: x.get("priority", 3))
        
        return filtered
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return []

def _add_task(
    description: str,
    priority: int = 3,
    blocked_by: Optional[List[str]] = None,
    required_skills: Optional[List[str]] = None,
    source: str = "synthesizer",
    task_id: Optional[str] = None,
    skip_dep_check: bool = False
) -> Dict[str, Any]:
    """Create a new task."""
    try:
        tasks = _get_tasks_list()
        task_ids = {t.get("id") for t in tasks if t.get("id")}
        
        if blocked_by and not skip_dep_check:
            for dep_id in blocked_by:
                if dep_id not in task_ids:
                    return {
                        "success": False, 
                        "error": f"Referential integrity violation: dependency '{dep_id}' does not exist"
                    }
        
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        new_task_id = task_id if task_id else f"task-{str(uuid.uuid4())[:8]}"
        
        if new_task_id in task_ids:
            return {"success": False, "error": f"Task ID '{new_task_id}' already exists"}
        
        if blocked_by and new_task_id in blocked_by:
            return {"success": False, "error": "DAG violation: task cannot block itself"}
            
        new_task = {
            "id": new_task_id,
            "description": description,
            "status": "PENDING" if not blocked_by else "BLOCKED",
            "priority": priority,
            "blocked_by": blocked_by or [],
            "required_skills": required_skills or [],
            "claimed_by": None,
            "source": source,
            "escalation_reason": None,
            "created_at": now,
            "updated_at": now
        }
        
        tasks.append(new_task)
        _save_tasks_list(tasks)
        
        _emit_event("task_created", source, {
            "task_id": new_task_id,
            "description": description,
            "priority": priority
        })
        
        return {"success": True, "task": new_task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _update_task(task_id: str, updates: Dict[str, Any]) -> Dict:
    """Update task fields."""
    try:
        tasks = _get_tasks_list()
        
        for task in tasks:
            if task.get("id") == task_id or task.get("description") == task_id:
                valid_keys = ["status", "priority", "description", "blocked_by", 
                              "required_skills", "claimed_by"]
                
                if "blocked_by" in updates:
                    all_ids = {t["id"] for t in tasks}
                    for dep_id in updates["blocked_by"]:
                        if dep_id not in all_ids:
                             raise ValueError(f"Referential integrity violation: Dependency task '{dep_id}' does not exist")

                old_status = task.get("status")
                
                for key, value in updates.items():
                    if key in valid_keys:
                        task[key] = value
                
                task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                
                _save_tasks_list(tasks)
                
                new_status = task.get("status")
                if old_status != new_status and "status" in updates:
                     _emit_event(
                        "task_state_changed",
                        "brain_update_task",
                        {
                            "task_id": task.get("id"),
                            "old_status": old_status,
                            "new_status": new_status
                        }
                    )
                
                return {"success": True, "task": task}
        
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _claim_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    """Atomically claim a task."""
    try:
        tasks = _get_tasks_list()
        
        for task in tasks:
            if task.get("id") == task_id or task.get("description") == task_id:
                if task.get("claimed_by"):
                    return {"success": False, "error": f"Task already claimed by {task['claimed_by']}"}
                
                status = task.get("status", "").upper()
                if status not in ["TODO", "PENDING", "READY"]:
                    return {"success": False, "error": f"Task status is {status}, cannot claim"}
                
                task["claimed_by"] = agent_id
                task["status"] = "IN_PROGRESS"
                task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                
                _save_tasks_list(tasks)
                
                _emit_event("task_claimed", agent_id, {
                    "task_id": task.get("id", task_id),
                    "description": task.get("description")
                })
                
                return {"success": True, "task": task}
        
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_next_task(skills: List[str]) -> Optional[Dict]:
    """Get highest priority unblocked task matching skills."""
    try:
        tasks = _list_tasks() # This handles sorting and external merging
        
        actionable = []
        for task in tasks:
            status = task.get("status", "").upper()
            if status not in ["TODO", "PENDING", "READY"]:
                continue
            
            if task.get("claimed_by"):
                continue
            
            blocked_by = task.get("blocked_by", [])
            if blocked_by:
                all_tasks = _get_tasks_list()
                blocking_done = True
                for blocker_id in blocked_by:
                    for t in all_tasks:
                        if t.get("id") == blocker_id:
                            if t.get("status", "").upper() not in ["DONE", "COMPLETE"]:
                                blocking_done = False
                                break
                if not blocking_done:
                    continue
            
            required = [s.lower() for s in task.get("required_skills", [])]
            available = [s.lower() for s in skills]
            
            if not required or any(r in available for r in required):
                actionable.append(task)
        
        actionable.sort(key=lambda t: t.get("priority", 3))
        return actionable[0] if actionable else None
    except Exception as e:
        logger.error(f"Error getting next task: {e}")
        return None

def _escalate_task(task_id: str, reason: str) -> Dict[str, Any]:
    """Escalate a task to request human help."""
    try:
        tasks = _get_tasks_list()
        
        for task in tasks:
            if task.get("id") == task_id or task.get("description") == task_id:
                task["status"] = "ESCALATED"
                task["escalation_reason"] = reason
                task["claimed_by"] = None  # Unclaim
                task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                
                _save_tasks_list(tasks)
                
                _emit_event("task_escalated", "nucleus_mcp", {
                    "task_id": task.get("id", task_id),
                    "reason": reason
                })
                
                return {"success": True, "task": task}
        
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _import_tasks_from_jsonl(jsonl_path: str, clear_existing: bool = False, merge_gtm_params: bool = True) -> Dict:
    """Import tasks from a JSONL file into the brain database."""
    try:
        brain = get_brain_path()
        
        jsonl_file = Path(jsonl_path)
        if not jsonl_file.is_absolute():
            jsonl_file = brain / jsonl_path
        
        if not jsonl_file.exists():
            return {
                "success": False,
                "error": f"File not found: {jsonl_path}",
                "imported": 0,
                "skipped": 0
            }
        
        existing_tasks = _get_tasks_list()
        existing_ids = {t.get("id") for t in existing_tasks if t.get("id")}
        
        if clear_existing:
            existing_tasks = []
            existing_ids = set()
        
        imported = 0
        skipped = 0
        errors = []
        new_tasks = []
        
        for line_num, line in enumerate(jsonl_file.read_text().splitlines(), 1):
            if not line.strip():
                continue
            
            try:
                task_data = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: Invalid JSON - {str(e)}")
                skipped += 1
                continue
            
            task_id = task_data.get("id")
            if not clear_existing and task_id in existing_ids:
                skipped += 1
                continue
                
            if not task_data.get("description"):
                errors.append(f"Line {line_num}: Missing description")
                skipped += 1
                continue
            
            now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            task = {
                "id": task_id or f"task-{str(uuid.uuid4())[:8]}",
                "description": task_data.get("description"),
                "status": task_data.get("status", "PENDING").upper(),
                "priority": int(task_data.get("priority", 3)),
                "blocked_by": task_data.get("blocked_by", []),
                "required_skills": task_data.get("required_skills", []),
                "claimed_by": task_data.get("claimed_by"),
                "source": f"import:{jsonl_file.name}",
                "created_at": task_data.get("created_at", now),
                "updated_at": now
            }
            
            # GTM Metadata Merging
            if merge_gtm_params:
                if "environment" in task_data:
                    task["environment"] = task_data["environment"]
                if "model" in task_data:
                    task["model"] = task_data["model"]
                if "step" in task_data:
                    task["step"] = task_data["step"]
            
            new_tasks.append(task)
            existing_ids.add(task["id"])
            imported += 1
            
        if imported > 0:
            final_tasks = existing_tasks + new_tasks
            _save_tasks_list(final_tasks)
            
            _emit_event("tasks_imported", "nucleus_mcp", {
                "source": str(jsonl_file),
                "count": imported
            })
            
        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }
    except Exception as e:
        return {"success": False, "error": str(e), "imported": 0, "skipped": 0}
