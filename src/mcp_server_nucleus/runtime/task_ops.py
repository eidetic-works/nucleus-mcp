"""
Nucleus Runtime - Task Operations (V2 SCALE)
===========================================
Core logic for task management (CRUD, Claiming, Importing).
Backed by StorageBackend (SQLite/Postgres).
"""

import json
import os
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

# ── DSoR-Verifier gating seam (flag-gated; default OFF) ─────────────────
# When NUCLEUS_VERIFY_GATES is truthy, a blocker's DONE/COMPLETE status is no
# longer trusted as-is to release its dependents: the task's evidence ref
# (commit SHA / ci_run_id) must ADJUDICATE to CONFIRMED on the gate's
# load-bearing predicate (is_ancestor of origin/main — ANCHOR_DOCTRINE §3 for
# CODE-EXISTS). A raw "DONE" with no backing commit fails closed and does NOT
# release. With the flag OFF this whole path is skipped and release behavior is
# byte-identical to the legacy status-only check.
_VERIFY_GATES_ENV = "NUCLEUS_VERIFY_GATES"

# The gate's load-bearing predicate: a released blocker's commit must be in the
# authoritative history, not merely exist on some abandoned branch.
_TASK_RELEASE_PREDICATE = "is_ancestor"


def _verify_gates_enabled() -> bool:
    """Is verdict-gated task release turned on? Read live (not cached) so
    tests can flip it per-case."""
    return os.environ.get(_VERIFY_GATES_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _blocker_evidence_refs(blocker: Dict[str, Any]) -> List[str]:
    """Collect commit-SHA / ci_run_id evidence refs a blocker task carries.
    Tolerant of several field spellings and of scalar-or-list shapes."""
    refs: List[str] = []
    for key in ("evidence_ref", "evidence_refs", "commit", "commit_sha", "sha", "ci_run_id"):
        v = blocker.get(key)
        if isinstance(v, str) and v.strip():
            refs.append(v.strip())
        elif isinstance(v, (list, tuple)):
            refs.extend(str(x).strip() for x in v if str(x).strip())
    return refs


def _blocker_release_confirmed(blocker: Dict[str, Any]) -> bool:
    """Does this DONE/COMPLETE blocker's evidence ADJUDICATE to CONFIRMED on
    the release predicate? Fails CLOSED (False) on any error or missing
    evidence — an un-probed 'DONE' does not release dependents."""
    try:
        from .verify_gate import consume_if_confirmed
    except Exception as exc:  # pragma: no cover - verify_gate unavailable ⇒ deny
        logger.debug("verify gate: helper import failed, failing closed: %s", exc)
        return False
    refs = _blocker_evidence_refs(blocker)
    assertion = f"{blocker.get('description', '')} :: status={blocker.get('status', '')}"
    repo = blocker.get("repo") or os.environ.get("NUCLEUS_VERIFY_GATES_REPO")
    return consume_if_confirmed(assertion, _TASK_RELEASE_PREDICATE, refs, repo=repo)

def _list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    skill: Optional[str] = None,
    claimed_by: Optional[str] = None,
    required_role: Optional[str] = None,
    strict_role: bool = False,
) -> List[Dict]:
    """List tasks natively from DB with optional filters and external provider merging.

    ``required_role`` filters tasks by their role scope. Tasks with empty
    ``required_role`` are visible to all agents (backward compat). Tasks with
    a specific role are only visible to agents pulling with that role.

    ``strict_role=True`` disables backward compat — only tasks with
    ``required_role`` exactly matching the filter are returned. Used by
    ``wakeup_wait`` so a scoped agent doesn't get spammed by legacy
    unscoped tasks.
    """
    try:
        brain = get_brain_path()
        storage = get_storage_backend(brain)

        # Native DB filtering
        filtered = storage.list_tasks(status, priority, skill, claimed_by)

        # Role filter (post-DB — field is optional, may not exist on legacy tasks)
        if required_role:
            if strict_role:
                # Strict: only exact role match (no backward-compat fallback)
                filtered = [
                    t for t in filtered
                    if t.get("required_role") == required_role
                ]
            else:
                # Backward compat: unscoped tasks (empty required_role) match any filter
                filtered = [
                    t for t in filtered
                    if not t.get("required_role") or t.get("required_role") == required_role
                ]
        
        # Merge with Commitment Ledger (PEFS) — circuit-breaker protected
        from .circuit_breaker import get_breaker
        ledger_cb = get_breaker("commitment_ledger", failure_threshold=3, recovery_timeout=60)
        if ledger_cb.allow_request():
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
                ledger_cb.record_success()
            except Exception as e:
                ledger_cb.record_failure()
                logger.warning(f"Failed to merge commitment ledger: {e}")

        # Merge with Cloud Tasks (if available) — circuit-breaker protected
        cloud_cb = get_breaker("cloud_tasks", failure_threshold=2, recovery_timeout=120)
        if cloud_cb.allow_request():
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
                cloud_cb.record_success()
            except Exception:
                cloud_cb.record_failure()
        
        # Sort by priority (asc) — coerce to int to avoid mixed-type comparisons
        for t in filtered:
            try:
                t["priority"] = int(t.get("priority", 3))
            except Exception:
                t["priority"] = 3
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
    skip_dep_check: bool = False,
    required_role: Optional[str] = None,
    plan_ref: Optional[str] = None,
    task_type: str = "llm",
    command: str = "",
) -> Dict[str, Any]:
    """Create a new task.

    ``required_role`` scopes the task to a specific agent role (e.g. "principal",
    "peer"). ``auto_awake`` daemons poll with this filter so only the matching
    agent wakes — no cross-fire. Empty/None = any agent can pull (backward compat).

    ``plan_ref`` is a pointer to the plan section this task serves (e.g.
    "STATE.md#MOAT-§2"). The principal reads it to verify alignment before
    delegating — plan gates the task, not the secretary's narration.
    """
    try:
        if not description or not str(description).strip():
            return {"success": False, "error": "Task description cannot be empty"}

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

        existing = storage.get_task(new_task_id)
        if existing:
            # Duplicate task ID is an idempotent skip, not an error. Return the
            # existing task so callers can ack the prior relay and move on.
            return {"success": True, "duplicate": True, "task": existing}

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
            "updated_at": now,
            "required_role": required_role or "",
            "plan_ref": plan_ref or "",
            "task_type": task_type,
            "command": command,
        }
        
        storage.add_task(new_task)

        _emit_event("task_created", source, {
            "task_id": new_task_id,
            "description": description,
            "priority": priority
        })

        # Auto-notify: post a relay to the agent's own bucket with the full
        # task. The agent's existing relay_subscribe catches it — no
        # wakeup_wait call needed, no idle-state instruction needed.
        # The relay IS the task. The agent reads it and acts.
        #
        # Posture mapping: if an agent has declared posture for this role,
        # post to that agent's bucket (e.g. antigravity/). If no posture
        # declared, post to role_<required_role>/ as a fallback (any agent
        # subscribed to that role bucket catches it).
        if required_role:
            try:
                from .relay.core import relay_post
                from .posture import get_current_posture
                from .relay_inbox_canonical import resolve_canonical_inbox_name

                posture = get_current_posture()
                target = f"role_{required_role}"  # fallback: role bucket
                if posture.get("status") == "active" and posture.get("role") == required_role:
                    agent_id = posture.get("agent_id", "")
                    if agent_id:
                        target = resolve_canonical_inbox_name(agent_id)

                relay_post(
                    to=target,
                    subject=f"[TASK] {new_task_id}",
                    body=(
                        f"Task: {new_task_id}\n"
                        f"Role: {required_role}\n"
                        f"Priority: {priority}\n"
                        f"Plan ref: {plan_ref or ''}\n\n"
                        f"Description:\n{description}\n\n"
                        f"Execute this task. Gate with pytest. Commit. "
                        f"Mark DONE via nucleus_sync(action='update_task', "
                        f"params={{task_id: '{new_task_id}', status: 'DONE'}})."
                    ),
                    priority="high" if priority <= 2 else "normal",
                    sender="task_scheduler",
                )
            except Exception as exc:
                logger.debug("task arrival relay post failed (non-fatal): %s", exc)

        return {"success": True, "task": new_task}
    except Exception as e:
        err_msg = str(e).lower()
        if "unique constraint failed" in err_msg or "already exists" in err_msg or "duplicate key" in err_msg:
            try:
                existing = storage.get_task(new_task_id)
                if existing:
                    return {"success": True, "duplicate": True, "task": existing}
            except Exception:
                pass
        return {"success": False, "error": str(e)}

def _get_task(task_id: str) -> Optional[Dict]:
    """Get a single task by ID. Convenience wrapper around _get_task_by_id_or_desc."""
    try:
        storage = get_storage_backend(get_brain_path())
        return _get_task_by_id_or_desc(storage, task_id)
    except Exception:
        return None


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
                      "required_skills", "claimed_by", "escalation_reason",
                      "verification_status", "verified_by", "verified_at",
                      "verification_note", "chief_review_note",
                      "retry_count", "duration_s"]
                      
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

             # Delegation feedback: when a task is marked DONE, post a [DONE]
             # relay to the task's source agent so the delegator knows the work
             # is complete. This closes the delegation loop — the secretary
             # (source) sees [DONE] in its inbox and can queue the next task.
             #
             # Only fires when source is a real agent (not "secretary" or
             # "test" or "synthesizer" — those are system sources, not
             # delegators with relay buckets).
             if new_status and new_status.upper() == "DONE":
                 delegator = task.get("source", "")
                 _system_sources = {"test", "synthesizer", "system", "brain_update_task", ""}
                 if delegator and delegator not in _system_sources:
                     try:
                         from .relay.core import relay_post
                         from .relay_inbox_canonical import resolve_canonical_inbox_name
                         target = resolve_canonical_inbox_name(delegator)
                         relay_post(
                             to=target,
                             subject=f"[DONE] {real_task_id}",
                             body=(
                                 f"Task {real_task_id} marked DONE by executor.\n"
                                 f"Description: {task.get('description', '')[:200]}\n"
                                 f"Source: {delegator}\n\n"
                                 f"Queue the next task if available."
                             ),
                             priority="normal",
                             sender="task_scheduler",
                         )
                     except Exception as exc:
                         logger.debug("delegation DONE relay failed (non-fatal): %s", exc)

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
        if status not in ["TODO", "PENDING", "READY", "BLOCKED"]:
            return {"success": False, "error": f"Task status is {status}, cannot claim"}
        
        if status == "BLOCKED":
            blocked_by = task.get("blocked_by", [])
            for blocker_id in blocked_by:
                b_task = storage.get_task(blocker_id)
                if not b_task or b_task.get("status", "").upper() not in ["DONE", "COMPLETE"]:
                    return {"success": False, "error": f"Task is blocked by '{blocker_id}' which is not DONE"}
                if _verify_gates_enabled() and not _blocker_release_confirmed(b_task):
                    return {"success": False, "error": f"Task is blocked by '{blocker_id}' (gate verification failed)"}

        # Use atomic claim if available (prevents TOCTOU race)
        if hasattr(storage, 'claim_task_atomic'):
            won = storage.claim_task_atomic(real_task_id, agent_id)
            if not won:
                return {"success": False, "error": "Task was claimed by another executor (atomic race prevented)"}
        else:
            now_ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            storage.update_task(real_task_id, {"claimed_by": agent_id, "status": "IN_PROGRESS", "claimed_at": now_ts})
        task["claimed_by"] = agent_id
        task["status"] = "IN_PROGRESS"
        task["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        _emit_event("task_claimed", agent_id, {
            "task_id": real_task_id,
            "description": task.get("description")
        })
        
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_next_task(skills: List[str], required_role: Optional[str] = None,
                   agent_id: Optional[str] = None) -> Optional[Dict]:
    """Get highest priority unblocked task matching skills and role scope.

    Fix #7: If agent_id is provided, skip tasks if this executor already has
    an IN_PROGRESS task — prevents one executor from hoarding all PENDING tasks.
    """
    try:
        tasks = _list_tasks(required_role=required_role)  # Handles sorting + role filter
        storage = get_storage_backend(get_brain_path())

        # Fix #7: Executor starvation prevention — 1 task per executor
        if agent_id:
            already_claimed = sum(
                1 for t in tasks
                if t.get("status", "").upper() == "IN_PROGRESS"
                and t.get("claimed_by") == agent_id
            )
            if already_claimed > 0:
                logger.info(f"Executor {agent_id} already has {already_claimed} IN_PROGRESS task(s) — skipping task assignment")
                return None

        actionable = []
        for task in tasks:
            status = task.get("status", "").upper()
            if status not in ["TODO", "PENDING", "READY", "BLOCKED"]:
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
                    # Flag-gated (default OFF): a DONE/COMPLETE status alone is a
                    # forgeable claim. When gate-verification is on, the blocker
                    # releases dependents only if its evidence ref adjudicates to
                    # CONFIRMED on the release predicate (③ + G2). Fails closed.
                    if _verify_gates_enabled() and not _blocker_release_confirmed(b_task):
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
