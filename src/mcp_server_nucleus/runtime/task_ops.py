
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .common import get_brain_path
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.task_ops")

def _get_tasks_list() -> List[Dict]:
    try:
        brain = get_brain_path()
        tasks_path = brain / "ledger" / "tasks.json"
        if tasks_path.exists():
            with open(tasks_path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("tasks", [])
        return []
    except Exception as e:
        logger.error(f"Error getting tasks list: {e}")
        return []

def _save_tasks_list(tasks: List[Dict]) -> str:
    try:
        brain = get_brain_path()
        tasks_path = brain / "ledger" / "tasks.json"
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tasks_path, "w") as f:
            json.dump(tasks, f, indent=2)
        return "Tasks saved"
    except Exception as e:
        logger.error(f"Error saving tasks list: {e}")
        return f"Error saving tasks: {str(e)}"

def _list_tasks(status: Optional[str] = None, priority: Optional[int] = None) -> List[Dict]:
    tasks = _get_tasks_list()
    if status:
        tasks = [t for t in tasks if t.get("status", "").upper() == status.upper()]
    if priority is not None:
        tasks = [t for t in tasks if t.get("priority") == priority]
    tasks.sort(key=lambda x: x.get("priority", 3))
    return tasks

def _add_task(description: str, priority: int = 3, blocked_by: Optional[List[str]] = None) -> Dict[str, Any]:
    tasks = _get_tasks_list()
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    task_id = f"task-{str(uuid.uuid4())[:8]}"
    new_task = {
        "id": task_id,
        "description": description,
        "status": "PENDING" if not blocked_by else "BLOCKED",
        "priority": priority,
        "blocked_by": blocked_by or [],
        "created_at": now,
        "updated_at": now
    }
    tasks.append(new_task)
    _save_tasks_list(tasks)
    _emit_event("task_created", "nucleus_mcp", {"task_id": task_id, "description": description})
    return {"success": True, "task": new_task}

def _update_task(task_id: str, updates: Dict[str, Any]) -> Dict:
    tasks = _get_tasks_list()
    for task in tasks:
        if task.get("id") == task_id or task.get("description") == task_id:
            for key, value in updates.items():
                if key in ["status", "priority", "description", "blocked_by"]:
                    task[key] = value
            task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            _save_tasks_list(tasks)
            return {"success": True, "task": task}
    return {"success": False, "error": "Task not found"}

def _claim_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    tasks = _get_tasks_list()
    for task in tasks:
        if task.get("id") == task_id or task.get("description") == task_id:
            if task.get("claimed_by"):
                return {"success": False, "error": f"Task already claimed by {task['claimed_by']}"}
            task["claimed_by"] = agent_id
            task["status"] = "IN_PROGRESS"
            task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            _save_tasks_list(tasks)
            _emit_event("task_claimed", agent_id, {"task_id": task_id})
            return {"success": True, "task": task}
    return {"success": False, "error": "Task not found"}

def _get_next_task(skills: List[str] = None) -> Optional[Dict]:
    tasks = _list_tasks(status="PENDING")
    return tasks[0] if tasks else None
