"""
Nucleus Runtime - Task Operations (V2 SCALE)
===========================================
Core logic for task management (CRUD, Claiming, Importing).
Backed by StorageBackend (SQLite/Postgres).
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Relative imports
from .common import get_brain_path
from .db import get_storage_backend
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.task_ops")

def _list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    skill: Optional[str] = None,
    claimed_by: Optional[str] = None
) -> List[Dict]:
    """List tasks natively from DB with optional filters and external provider merging."""
    try:
        brain = get_brain_path()
        storage = get_storage_backend(brain)
        
        # Native DB filtering
        filtered = storage.list_tasks(status, priority, skill, claimed_by)
        
        # Merge with Commitment Ledger (PEFS)
        try:
            from mcp_server_nucleus import commitment_ledger
            ledger = commitment_ledger.load_ledger(brain)
            
            for comm in ledger.get("commitments", []):
                comm_status = comm.get("status", "open").lower()
                task_status = "PENDING"
                if comm_status == "closed":
                    task_status = "DONE"
                
                # Apply filters manually to external tasks
                if status:
                    status_map = {"TODO": "PENDING", "COMPLETE": "DONE"}
                    target_status = status_map.get(status, status)
                    if task_status.upper() != target_status.upper() and task_status.upper() != status.upper():
                        continue
                if priority is not None and comm.get("priority", 3) != priority:
                    continue
                req_skills = [s.lower() for s in comm.get("required_skills", [])]
                if skill and skill.lower() not in req_skills:
                    continue
                if claimed_by: # Ledger tasks are never claimed
                    continue

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
                filtered.append(cm_task)
        except Exception as e:
            logger.warning(f"Failed to merge commitment ledger: {e}")

        # Merge with Cloud Tasks (if available)
        try:
            from mcp_server_nucleus.runtime.firestore_bridge import get_bridge
            cloud_tasks = get_bridge().list_cloud_tasks()
            if cloud_tasks:
                local_ids = {t["id"] for t in filtered}
                for ct in cloud_tasks:
                    if ct["id"] not in local_ids:
                        # Manual filter
                        if status and ct.get("status") != status: continue
                        if priority is not None and ct.get("priority") != priority: continue
                        if claimed_by and ct.get("claimed_by") != claimed_by: continue
                        if skill and skill not in ct.get("required_skills", []): continue
                        filtered.append(ct)
        except Exception:
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
        storage = get_storage_backend(get_brain_path())
        
        if blocked_by and not skip_dep_check:
            for dep_id in blocked_by:
                if not storage.get_task(dep_id):
                    return {
                        "success": False, 
                        "error": f"Referential integrity violation: dependency '{dep_id}' does not exist"
                    }
        
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        new_task_id = task_id if task_id else f"task-{str(uuid.uuid4())[:8]}"
        
        if storage.get_task(new_task_id):
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
        
        storage.add_task(new_task)
        
        _emit_event("task_created", source, {
            "task_id": new_task_id,
            "description": description,
            "priority": priority
        })
        
        return {"success": True, "task": new_task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_task_by_id_or_desc(storage, task_id_or_desc: str) -> Optional[Dict]:
    task = storage.get_task(task_id_or_desc)
    if task: return task
    
    # Fallback to search by description
    all_tasks = storage.list_tasks()
    for t in all_tasks:
        if t.get("description") == task_id_or_desc:
            return t
    return None

def _update_task(task_id: str, updates: Dict[str, Any]) -> Dict:
    """Update task fields."""
    try:
        storage = get_storage_backend(get_brain_path())
        task = _get_task_by_id_or_desc(storage, task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
            
        real_task_id = task["id"]
        valid_keys = ["status", "priority", "description", "blocked_by", 
                      "required_skills", "claimed_by", "escalation_reason"]
                      
        filtered_updates = {k: v for k, v in updates.items() if k in valid_keys}
        
        if "blocked_by" in filtered_updates:
            for dep_id in filtered_updates["blocked_by"]:
                if not storage.get_task(dep_id):
                     raise ValueError(f"Referential integrity violation: Dependency task '{dep_id}' does not exist")

        old_status = task.get("status")
        
        storage.update_task(real_task_id, filtered_updates)
        task.update(filtered_updates)
        task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        new_status = task.get("status")
        if old_status != new_status and "status" in filtered_updates:
             _emit_event(
                "task_state_changed",
                "brain_update_task",
                {
                    "task_id": real_task_id,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
        
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _claim_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    """Atomically claim a task."""
    try:
        storage = get_storage_backend(get_brain_path())
        task = _get_task_by_id_or_desc(storage, task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
            
        real_task_id = task["id"]
        
        if task.get("claimed_by"):
            return {"success": False, "error": f"Task already claimed by {task['claimed_by']}"}
        
        status = task.get("status", "").upper()
        if status not in ["TODO", "PENDING", "READY"]:
            return {"success": False, "error": f"Task status is {status}, cannot claim"}
        
        storage.update_task(real_task_id, {"claimed_by": agent_id, "status": "IN_PROGRESS"})
        task["claimed_by"] = agent_id
        task["status"] = "IN_PROGRESS"
        
        _emit_event("task_claimed", agent_id, {
            "task_id": real_task_id,
            "description": task.get("description")
        })
        
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_next_task(skills: List[str]) -> Optional[Dict]:
    """Get highest priority unblocked task matching skills."""
    try:
        tasks = _list_tasks() # Handles sorting and external merging
        storage = get_storage_backend(get_brain_path())
        
        actionable = []
        for task in tasks:
            status = task.get("status", "").upper()
            if status not in ["TODO", "PENDING", "READY"]:
                continue
            
            if task.get("claimed_by"):
                continue
            
            blocked_by = task.get("blocked_by", [])
            if blocked_by:
                blocking_done = True
                for blocker_id in blocked_by:
                    b_task = next((t for t in tasks if t["id"] == blocker_id), None)
                    if not b_task:
                        b_task = storage.get_task(blocker_id)
                    if not b_task or b_task.get("status", "").upper() not in ["DONE", "COMPLETE"]:
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
        storage = get_storage_backend(get_brain_path())
        task = _get_task_by_id_or_desc(storage, task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
            
        real_task_id = task["id"]
        
        storage.update_task(real_task_id, {
            "status": "ESCALATED",
            "escalation_reason": reason,
            "claimed_by": None
        })
        task["status"] = "ESCALATED"
        task["escalation_reason"] = reason
        task["claimed_by"] = None
        
        _emit_event("task_escalated", "nucleus_mcp", {
            "task_id": real_task_id,
            "reason": reason
        })
        
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _import_tasks_from_jsonl(jsonl_path: str, clear_existing: bool = False, merge_gtm_params: bool = True) -> Dict:
    """Import tasks from a JSONL file into the brain database."""
    try:
        brain = get_brain_path()
        storage = get_storage_backend(brain)
        
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
        
        existing_tasks = storage.list_tasks()
        existing_ids = {t.get("id") for t in existing_tasks if t.get("id")}
        
        if clear_existing:
            # We don't have a clear storage method natively. 
            # We could delete all or just skip.
            # In V2 Postgres/SQLite, clearing existing is generally a bad idea to do automatically.
            # We will ignore clear_existing for DB safety, just appending instead.
            pass
        
        imported = 0
        skipped = 0
        errors = []
        
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
            
            storage.add_task(task)
            existing_ids.add(task["id"])
            imported += 1
            
        if imported > 0:
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
