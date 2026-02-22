"""Orchestrate Operations — Multi-agent task orchestration logic.

Extracted from __init__.py (brain_orchestrate).
Contains:
- _brain_orchestrate_impl (278 lines — the largest single _impl function)
"""

import json
import time
import uuid

from .common import get_brain_path
from .db import get_storage_backend


# ── Lazy imports (live in __init__.py) ─────────────────────────

def _lazy(name):
    import mcp_server_nucleus as m
    return getattr(m, name)


# ── Implementation ─────────────────────────────────────────────

def _brain_orchestrate_impl(
    slot_id: str = None,
    model: str = None,
    alias: str = None,
    mode: str = "auto"
) -> str:
    """
    Internal implementation of brain_orchestrate - directly callable.
    
    This function contains the actual orchestration logic and can be called
    directly from other Python code without going through MCP protocol.
    """
    _get_slot_registry = _lazy("_get_slot_registry")
    _get_tier_definitions = _lazy("_get_tier_definitions")
    _get_tier_for_model = _lazy("_get_tier_for_model")
    _save_slot_registry = _lazy("_save_slot_registry")
    _emit_event = _lazy("_emit_event")
    _resolve_slot_id = _lazy("_resolve_slot_id")
    _infer_task_tier = _lazy("_infer_task_tier")
    _can_slot_run_task = _lazy("_can_slot_run_task")
    _compute_slot_blockers = _lazy("_compute_slot_blockers")
    _claim_task = _lazy("_claim_task")

    try:
        brain = get_brain_path()
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Load registries
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        tasks = get_storage_backend(brain).list_tasks()
        
        # Build response structure
        response = {
            "meta": {
                "timestamp": now,
                "protocol_version": "2.0.0",
                "mode": mode
            },
            "slot": None,
            "protocol_status": {
                "compliant": True,
                "violations": [],
                "warnings": []
            },
            "handoffs": {
                "pending_for_me": [],
                "sent_by_me": []
            },
            "action": {
                "type": "WAIT",
                "task_id": None,
                "task_description": None,
                "task_priority": None,
                "claimed": False,
                "reason": "Initializing..."
            },
            "queue": {
                "assigned_to_me": [],
                "blocked": [],
                "available_for_claim": []
            },
            "system": {
                "active_slots": len([s for s in registry.get("slots", {}).values() if s.get("status") == "active"]),
                "total_pending": len([t for t in tasks if t.get("status") == "PENDING"]),
                "total_in_progress": len([t for t in tasks if t.get("status") == "IN_PROGRESS"]),
                "total_blocked": len([t for t in tasks if t.get("status") == "BLOCKED"]),
                "total_done": len([t for t in tasks if t.get("status") == "DONE"])
            }
        }
        
        # REGISTRATION MODE
        if mode == "register":
            if not model:
                response["action"] = {
                    "type": "ERROR",
                    "reason": "model parameter required for registration"
                }
                return json.dumps(response, indent=2)
            
            # Generate slot ID if not provided
            if not slot_id:
                slot_id = f"slot_{int(time.time())}_{str(uuid.uuid4())[:4]}"
            
            # Determine tier
            tier = _get_tier_for_model(model, tier_defs)
            
            # Create slot entry
            new_slot = {
                "id": slot_id,
                "alias": alias,
                "ide": "unknown",
                "model": model,
                "tier": tier,
                "capabilities": [],
                "status": "active",
                "current_task": None,
                "registered_at": now,
                "last_heartbeat": now,
                "tasks_completed": 0,
                "reset_at": None
            }
            
            registry["slots"][slot_id] = new_slot
            if alias:
                registry["aliases"][alias] = slot_id
            
            _save_slot_registry(registry)
            
            response["slot"] = new_slot
            response["action"] = {
                "type": "REGISTERED",
                "reason": f"Slot {slot_id} registered with tier {tier}"
            }
            
            _emit_event("slot_registered", "nucleus_orchestrate", {
                "slot_id": slot_id,
                "model": model,
                "tier": tier
            })
            
            return json.dumps(response, indent=2)
        
        # RESOLVE SLOT ID
        if not slot_id:
            response["action"] = {
                "type": "ERROR",
                "reason": "slot_id required (use mode='register' to create new slot)"
            }
            return json.dumps(response, indent=2)
        
        resolved_id = _resolve_slot_id(slot_id, registry)
        slot = registry.get("slots", {}).get(resolved_id)
        
        if not slot:
            response["action"] = {
                "type": "REGISTER_REQUIRED",
                "reason": f"Slot '{slot_id}' not found. Use mode='register' with model parameter."
            }
            return json.dumps(response, indent=2)
        
        # Update heartbeat
        slot["last_heartbeat"] = now
        registry["slots"][resolved_id] = slot
        _save_slot_registry(registry)
        
        response["slot"] = slot
        
        # CHECK FOR EXHAUSTION
        if slot.get("status") == "exhausted":
            response["action"] = {
                "type": "EXHAUSTED",
                "reason": f"Slot exhausted. Reset at: {slot.get('reset_at', 'unknown')}"
            }
            return json.dumps(response, indent=2)
        
        # CHECK HANDOFFS
        handoffs_path = brain / "ledger" / "handoffs.json"
        if handoffs_path.exists():
            with open(handoffs_path) as f:
                all_handoffs = json.load(f)
            response["handoffs"]["pending_for_me"] = [
                h for h in all_handoffs 
                if h.get("to_agent") == resolved_id and h.get("status") == "pending"
            ]
        
        # PROTOCOL COMPLIANCE
        in_progress = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        other_agent_tasks = [
            t for t in in_progress 
            if t.get("claimed_by") and t.get("claimed_by") != resolved_id
        ]
        
        for t in other_agent_tasks:
            response["protocol_status"]["warnings"].append(
                f"Task '{t.get('id')}' claimed by {t.get('claimed_by')} - do not overlap"
            )
        
        # FIND AVAILABLE TASKS
        slot_tier = slot.get("tier", "standard")
        available = []
        blocked = []
        
        for task in tasks:
            if task.get("status") not in ["PENDING", "READY"]:
                continue
            if task.get("claimed_by"):
                continue
            
            task_tier = _infer_task_tier(task, tier_defs)
            
            # Check tier compatibility
            if not _can_slot_run_task(slot_tier, task_tier, tier_defs):
                continue
            
            # Check dependencies
            slot_blockers = _compute_slot_blockers(task, tasks, registry)
            task_blockers = task.get("blocked_by", [])
            
            # Check if all blocking tasks are done
            all_done = True
            for dep_id in task_blockers:
                dep = next((t for t in tasks if t.get("id") == dep_id), None)
                if dep and dep.get("status") != "DONE":
                    all_done = False
                    break
            
            if not all_done or slot_blockers:
                blocked.append({
                    "id": task.get("id"),
                    "blocked_by_slots": slot_blockers,
                    "blocked_by_tasks": task_blockers
                })
            else:
                available.append(task)
        
        response["queue"]["blocked"] = blocked
        response["queue"]["available_for_claim"] = [t.get("id") for t in available]
        
        # SORT BY PRIORITY
        available.sort(key=lambda t: t.get("priority", 99))
        
        # HANDLE MODES
        if mode == "report":
            response["action"] = {
                "type": "REPORT",
                "reason": f"{len(available)} tasks available, {len(blocked)} blocked"
            }
            return json.dumps(response, indent=2)
        
        if not available:
            if blocked:
                response["action"] = {
                    "type": "BLOCKED",
                    "reason": f"All {len(blocked)} available tasks are blocked by other slots"
                }
            else:
                response["action"] = {
                    "type": "WAIT",
                    "reason": "No tasks available for your tier"
                }
            return json.dumps(response, indent=2)
        
        # BEST TASK
        best_task = available[0]
        
        if mode == "guided":
            response["action"] = {
                "type": "CHOOSE",
                "task_id": best_task.get("id"),
                "task_description": best_task.get("description"),
                "task_priority": best_task.get("priority"),
                "claimed": False,
                "reason": f"Recommended: {best_task.get('id')}. {len(available)} total available."
            }
            return json.dumps(response, indent=2)
        
        # AUTO MODE - CLAIM THE TASK
        claim_result = _claim_task(best_task.get("id"), resolved_id)
        
        if claim_result.get("success"):
            response["action"] = {
                "type": "WORK",
                "task_id": best_task.get("id"),
                "task_description": best_task.get("description"),
                "task_priority": best_task.get("priority"),
                "claimed": True,
                "reason": "Claimed highest priority unblocked task"
            }
            response["autopilot_hint"] = {
                "continue": len(available) > 1,
                "next_call": f"brain_orchestrate('{resolved_id}') after completing this task",
                "remaining_tasks": len(available) - 1
            }
        else:
            response["action"] = {
                "type": "ERROR",
                "reason": f"Claim failed: {claim_result.get('error')}"
            }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({
            "meta": {"error": str(e)},
            "action": {"type": "ERROR", "reason": str(e)}
        }, indent=2)
