"""
Nucleus Runtime - Slot Operations (Legacy Sprint & Dashboard)
===========================================================
Core logic for slot management, legacy sprinting (V3.0), and dashboard.
Moves complex orchestration logic out of __init__.py.
"""

import json
import time
import uuid
from typing import Dict, List

# Relative imports
from .. import commitment_ledger
from .common import get_brain_path
from .event_ops import _emit_event
from .db import get_storage_backend
from .orch_helpers import (
    _get_slot_registry,
    _resolve_slot_id,
    _get_tier_definitions,
    _infer_task_tier,
    _can_slot_run_task,
    _score_slot_for_task,
    _compute_dependency_graph,
    _claim_with_fence
)

def _brain_slot_complete_impl(slot_id: str, task_id: str, outcome: str = "success", 
                              outputs: List[str] = None, verification_notes: str = None, 
                              fence_token: int = None) -> str:
    """Mark a slot's current task as complete."""
    try:
        registry = _get_slot_registry()
        resolved_id = _resolve_slot_id(slot_id, registry)
        
        if resolved_id not in registry.get("slots", {}):
            return f"Error: Slot {slot_id} not found"
            
        slot = registry["slots"][resolved_id]
        
        # Verify fence token if provided
        if fence_token is not None:
             if slot.get("fence_token") != fence_token:
                 return "Error: Stale fence token. Task was likely reassigned."
        
        current_task_id = slot.get("current_task")
        if current_task_id != task_id:
             return f"Error: Slot {resolved_id} is working on {current_task_id}, not {task_id}"
            
        # Update Task Ledger
        storage = get_storage_backend(get_brain_path())
        task = storage.get_task(task_id)
        
        if task:
            updates = {
                "status": "DONE" if outcome == "success" else "FAILED",
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "completed_by": resolved_id,
                "outcome": outcome
            }
            if outputs:
                existing_outputs = task.get("outputs", [])
                updates["outputs"] = existing_outputs + outputs
            if verification_notes:
                 updates["verification"] = verification_notes
            
            storage.update_task(task_id, updates)
            
        # Update Slot Registry
        # Clear current task
        slot["current_task"] = None
        slot["fence_token"] = None
        slot["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Update stats
        if "stats" not in slot:
            slot["stats"] = {"tasks_completed": 0, "failures": 0}
            
        if outcome == "success":
            slot["stats"]["tasks_completed"] += 1
        else:
            slot["stats"]["failures"] += 1
            
        # Write back registry
        brain = get_brain_path()
        registry_path = brain / "slots" / "registry.json"
        
        # Re-read to prevent race (simple optimistic lock)
        with open(registry_path, "r") as f:
             current_reg = json.load(f)
             
        if resolved_id in current_reg["slots"]:
             current_reg["slots"][resolved_id].update(slot)
             
        with open(registry_path, "w") as f:
             json.dump(current_reg, f, indent=2)
             
        # Emit event
        _emit_event("slot_task_completed", resolved_id, {
            "task_id": task_id,
            "outcome": outcome
        })

        # Close commitment if exists
        try:
             commitment_ledger.close_commitment_with_outcome(brain, task_id, outcome)
        except Exception:
             pass # Ignore if no commitment
             
        return f"Slot {resolved_id} completed task {task_id} ({outcome})"
        
    except Exception as e:
        return f"Error completing slot task: {str(e)}"

def _brain_slot_exhaust_impl(slot_id: str, reason: str, reset_at: str) -> str:
    """Mark a slot as exhausted (rate limit hit)."""
    try:
        registry = _get_slot_registry()
        resolved_id = _resolve_slot_id(slot_id, registry)
        
        if resolved_id not in registry.get("slots", {}):
            return f"Error: Slot {slot_id} not found"
            
        slot = registry["slots"][resolved_id]
        
        slot["status"] = "exhausted"
        slot["status_message"] = reason
        slot["reset_at"] = reset_at
        
        # If working on a task, release it? 
        # For now, we keep it assigned but mark slot exhausted. 
        # The auto-assigner will skip it.
        
        brain = get_brain_path()
        registry_path = brain / "slots" / "registry.json"
        
        with open(registry_path, "w") as f:
             json.dump(registry, f, indent=2)
             
        _emit_event("slot_exhausted", resolved_id, {
             "reason": reason,
             "reset_at": reset_at
        })
        
        return f"Slot {resolved_id} marked exhausted until {reset_at}"
    except Exception as e:
        return f"Error marking slot exhausted: {str(e)}"

def _brain_status_dashboard_impl(refresh: bool = False) -> str:
    """Generate ASCII dashboard of slot status."""
    try:
        registry = _get_slot_registry()
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        now = time.strftime("%Y-%m-%d %H:%M %Z")
        
        active_slots = [s for s in registry.get("slots", {}).values() if s.get("status") == "active"]
        exhausted_slots = [s for s in registry.get("slots", {}).values() if s.get("status") == "exhausted"]
        
        pending_tasks = [t for t in tasks if t.get("status") == "PENDING"]
        in_progress_tasks = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        done_tasks = [t for t in tasks if t.get("status") == "DONE"]
        
        lines = []
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append(f"║ 🧠 NUCLEUS CONTROL PLANE - {now:<25} ║")
        lines.append("╠══════════════════════════════════════════════════════════════╣")
        
        # SLOTS SECTION
        lines.append("║ AGENT SLOTS                                                  ║")
        lines.append("╟──────────────────────────────────────────────────────────────╢")
        
        for slot in active_slots:
            sid = slot.get("id")
            tier = slot.get("tier", "standard")
            task_id = slot.get("current_task")
            model = slot.get("model", "unknown")
            
            status_icon = "🟢"
            if task_id:
                 status_icon = "▶️ "
            
            task_desc = "Idling"
            if task_id:
                 # Find task
                 t = next((x for x in tasks if x.get("id") == task_id), None)
                 if t:
                     task_desc = f"Running: {t.get('description', '')[:30]}..."
                 else:
                     task_desc = f"Running: {task_id}"
            
            lines.append(f"║ {status_icon} {sid:<15} [{tier[:3].upper()}] {task_desc:<30} ║")
            
        for slot in exhausted_slots:
            sid = slot.get("id")
            reset = slot.get("reset_at", "unknown")
            lines.append(f"║ 🔴 {sid:<15} [EXH] Reset: {reset:<30} ║")
            
        lines.append("╠══════════════════════════════════════════════════════════════╣")
        lines.append("║ TASK QUEUE                                                   ║")
        lines.append("╟──────────────────────────────────────────────────────────────╢")
        lines.append(f"║ Pending: {len(pending_tasks):<5} | In Progress: {len(in_progress_tasks):<5} | Done: {len(done_tasks):<5}       ║")
        
        if pending_tasks:
             lines.append("╟──────────────────────────────────────────────────────────────╢")
             # Show top 5 pending
             top_pending = sorted(pending_tasks, key=lambda x: x.get("priority", 99))[:5]
             for i, t in enumerate(top_pending):
                 prio = f"P{t.get('priority',3)}"
                 desc = t.get("description", "")[:45]
                 lines.append(f"║ {i+1}. [{prio}] {desc:<50} ║")
                 
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        
        # Add cost stats if available
        # Simple estimation
        total_cost = 0.0
        for slot in registry.get("slots", {}).values():
            slot_id = slot.get("id")
            # This relies on usage tracking which might not be fully implemented in registry yet
            # But let's assume we can calculate it from some ledger
            pass 

        return "\n".join(lines)
        
    except Exception as e:
        return f"Dashboard error: {str(e)}"

def _brain_autopilot_sprint_impl(slots: List[str] = None, mode: str = "auto", 
                                 halt_on_blocker: bool = True, halt_on_tier_mismatch: bool = False,
                                 max_tasks_per_slot: int = 10, budget_limit: float = None,
                                 dry_run: bool = False) -> str:
    """THE SPRINT COMMAND - Orchestrate multiple slots in parallel (Legacy V3.0)."""
    try:
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        sprint_id = f"sprint_{int(time.time())}_{str(uuid.uuid4())[:4]}"
        
        # Load data
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        all_slots = registry.get("slots", {})
        
        # PHASE 1: SELECT TARGET SLOTS
        if slots is None:
            target_slots = [s for s in all_slots.values() if s.get("status") == "active"]
        else:
            target_slots = []
            for slot_id in slots:
                resolved = _resolve_slot_id(slot_id, registry)
                if resolved in all_slots:
                    target_slots.append(all_slots[resolved])
        
        if not target_slots:
            return json.dumps({
                "sprint_id": sprint_id,
                "status": "ERROR",
                "error": "No active slots found",
                "timestamp": now
            }, indent=2)
        
        # PHASE 2: COMPUTE DEPENDENCY GRAPH
        dep_graph = _compute_dependency_graph(tasks, registry)
        
        # Check for circular dependencies
        if dep_graph["circular_deps"] and halt_on_blocker:
            return json.dumps({
                "sprint_id": sprint_id,
                "status": "HALTED",
                "reason": "Circular dependencies detected",
                "circular_deps": dep_graph["circular_deps"],
                "action": "Resolve circular dependencies before sprint",
                "timestamp": now
            }, indent=2)
        
        # PHASE 3: COMPUTE ASSIGNMENTS
        assignments = []
        total_estimated_cost = 0
        tasks_assigned = 0
        slots_blocked = 0
        
        for slot in target_slots:
            slot_id = slot.get("id")
            slot_tier = slot.get("tier", "standard")
            
            # Skip exhausted slots
            if slot.get("status") == "exhausted":
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": None,
                    "status": "EXHAUSTED",
                    "reason": f"Slot exhausted. Recovery at: {slot.get('reset_at', 'unknown')}"
                })
                continue
            
            # Find runnable tasks for this slot
            runnable_tasks = []
            blocked_reasons = []
            
            for task in tasks:
                task_id = task.get("id")
                
                # Skip non-pending tasks
                if task.get("status") not in ["PENDING", "READY"]:
                    continue
                
                # Skip already claimed tasks
                if task.get("claimed_by"):
                    continue
                
                # Check tier compatibility
                task_tier = _infer_task_tier(task, tier_defs)
                if not _can_slot_run_task(slot_tier, task_tier, tier_defs):
                    if halt_on_tier_mismatch:
                        blocked_reasons.append(f"Task {task_id} requires tier {task_tier}")
                    continue
                
                # Check dependencies
                blockers = task.get("blocked_by", [])
                all_done = True
                blocking_slots = []
                
                for dep_id in blockers:
                    dep_task = next((t for t in tasks if t.get("id") == dep_id), None)
                    if dep_task and dep_task.get("status") != "DONE":
                        all_done = False
                        if dep_task.get("claimed_by"):
                            blocking_slots.append(dep_task.get("claimed_by"))
                
                if not all_done:
                    blocked_reasons.append(f"Task {task_id} blocked by {blocking_slots or blockers}")
                    continue
                
                # Task is runnable!
                score_result = _score_slot_for_task(task, slot, tier_defs)
                runnable_tasks.append({
                    "task": task,
                    "score": score_result["score"],
                    "estimated_cost": score_result["estimated_cost"],
                    "warnings": score_result["warnings"]
                })
            
            # Sort by priority then score
            runnable_tasks.sort(key=lambda x: (x["task"].get("priority", 99), -x["score"]))
            
            if runnable_tasks:
                best = runnable_tasks[0]
                task = best["task"]
                
                # Check budget
                if budget_limit and total_estimated_cost + best["estimated_cost"] > budget_limit:
                    assignments.append({
                        "slot_id": slot_id,
                        "task_id": None,
                        "status": "BUDGET_EXCEEDED",
                        "reason": f"Would exceed budget (${total_estimated_cost:.3f} + ${best['estimated_cost']:.3f} > ${budget_limit})"
                    })
                    continue
                
                # Claim task (unless dry run)
                fence_token = None
                if mode == "auto" and not dry_run:
                    claim_result = _claim_with_fence(task.get("id"), slot_id)
                    if claim_result.get("success"):
                        fence_token = claim_result.get("fence_token")
                    else:
                        assignments.append({
                            "slot_id": slot_id,
                            "task_id": task.get("id"),
                            "status": "CLAIM_FAILED",
                            "reason": claim_result.get("error")
                        })
                        continue
                
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": task.get("id"),
                    "task_description": task.get("description", "")[:100],
                    "priority": task.get("priority"),
                    "fence_token": fence_token,
                    "status": "EXECUTING" if fence_token else "PLANNED",
                    "estimated_cost": best["estimated_cost"],
                    "score": best["score"],
                    "warnings": best["warnings"]
                })
                
                total_estimated_cost += best["estimated_cost"]
                tasks_assigned += 1
            else:
                slots_blocked += 1
                assignments.append({
                    "slot_id": slot_id,
                    "task_id": None,
                    "status": "BLOCKED" if blocked_reasons else "IDLE",
                    "reason": blocked_reasons[0] if blocked_reasons else "No tasks for this tier",
                    "blocked_reasons": blocked_reasons[:3]  # Limit to 3
                })
        
        # PHASE 4: BUILD RESPONSE
        executing_count = len([a for a in assignments if a.get("status") == "EXECUTING"])
        planned_count = len([a for a in assignments if a.get("status") == "PLANNED"])
        
        if mode == "status":
            status = "REPORT"
        elif executing_count > 0:
            status = "RUNNING"
        elif planned_count > 0:
            status = "PLANNED"
        elif slots_blocked == len(target_slots):
            status = "ALL_BLOCKED"
        else:
            status = "IDLE"
        
        # Compute next actions
        next_actions = []
        for a in assignments:
            if a.get("status") == "EXECUTING":
                next_actions.append(
                    f"{a['slot_id']}: Execute '{a.get('task_description', '')[:50]}...', "
                    f"then brain_slot_complete('{a['slot_id']}', '{a['task_id']}', fence_token={a.get('fence_token')})"
                )
            elif a.get("status") == "BLOCKED":
                next_actions.append(f"{a['slot_id']}: {a.get('reason', 'Blocked')}")
        
        response = {
            "sprint_id": sprint_id,
            "status": status,
            "mode": mode,
            "dry_run": dry_run,
            "timestamp": now,
            
            "slots_summary": {
                "total": len(target_slots),
                "executing": executing_count,
                "planned": planned_count,
                "blocked": slots_blocked,
                "exhausted": len([a for a in assignments if a.get("status") == "EXHAUSTED"])
            },
            
            "assignments": assignments,
            
            "dependency_analysis": {
                "total_tasks": len(tasks),
                "pending_tasks": len([t for t in tasks if t.get("status") == "PENDING"]),
                "blocked_tasks": len(dep_graph.get("task_to_slot", {})),
                "circular_deps": dep_graph.get("circular_deps", []),
                "longest_chain_length": max((len(c) for c in dep_graph.get("blocking_chains", {}).values()), default=0)
            },
            
            "cost_projection": {
                "estimated_total": round(total_estimated_cost, 4),
                "budget_limit": budget_limit,
                "within_budget": budget_limit is None or total_estimated_cost <= budget_limit
            },
            
            "next_actions": next_actions[:5],  # Limit to 5
            
            "autopilot_hint": {
                "continue": tasks_assigned > 0,
                "check_status": "brain_autopilot_sprint(mode='status')",
                "tasks_remaining": len([t for t in tasks if t.get("status") == "PENDING"]) - tasks_assigned
            }
        }
        
        # Emit event
        _emit_event("sprint_started", "nucleus_orchestrate", {
            "sprint_id": sprint_id,
            "mode": mode,
            "slots": [s.get("id") for s in target_slots],
            "tasks_assigned": tasks_assigned
        })
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "ERROR",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }, indent=2)

def _brain_force_assign_impl(slot_id: str, task_id: str, acknowledge_risk: bool = False) -> str:
    """Force assign a task to a slot, overriding tier requirements."""
    try:
        registry = _get_slot_registry()
        tier_defs = _get_tier_definitions()
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        
        resolved_id = _resolve_slot_id(slot_id, registry)
        slot = registry.get("slots", {}).get(resolved_id)
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not slot:
            return json.dumps({"error": f"Slot {slot_id} not found"})
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
        
        # Check tier mismatch
        slot_tier = slot.get("tier", "standard")
        task_tier = _infer_task_tier(task, tier_defs)
        
        tiers = tier_defs.get("tiers", {})
        slot_level = tiers.get(slot_tier, {}).get("level", 3)
        task_level = tiers.get(task_tier, {}).get("level", 3)
        
        tier_gap = slot_level - task_level
        
        if tier_gap > 1 and not acknowledge_risk:
            return json.dumps({
                "error": "TIER_MISMATCH_RISK",
                "slot_tier": slot_tier,
                "task_tier": task_tier,
                "tier_gap": tier_gap,
                "message": "Task requires higher tier. Set acknowledge_risk=True to override.",
                "risk_level": "HIGH" if tier_gap > 2 else "MEDIUM"
            })
        
        # Force claim
        claim_result = _claim_with_fence(task_id, resolved_id)
        
        if claim_result.get("success"):
            warnings = []
            if tier_gap > 0:
                warnings.append(f"TIER_OVERRIDE: Slot ({slot_tier}) is {tier_gap} levels below task ({task_tier})")
            
            return json.dumps({
                "success": True,
                "slot_id": resolved_id,
                "task_id": task_id,
                "fence_token": claim_result.get("fence_token"),
                "warnings": warnings
            }, indent=2)
        else:
            return json.dumps(claim_result)
            
    except Exception as e:
        return f"Error forcing assignment: {str(e)}"

def _check_protocol_compliance(agent_id: str) -> Dict:
    """Check if agent is following multi-agent coordination protocol."""
    try:
        brain = get_brain_path()
        violations = []
        warnings = []
        
        # Load protocol
        protocol_path = brain / "protocols" / "multi_agent_mou.json"
        if not protocol_path.exists():
            return {
                "compliant": True,
                "warnings": ["Protocol definition not found - assuming compliant"]
            }
            
        with open(protocol_path, "r") as f:
            protocol = json.load(f)
            
        # Get pending tasks
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        
        # Check for claimed tasks by other agents
        other_agent_tasks = [
            t for t in tasks 
            if t.get("claimed_by") and t.get("claimed_by") != agent_id and t.get("status") == "IN_PROGRESS"
        ]
        
        if other_agent_tasks:
             warnings.append(f"Caution: {len(other_agent_tasks)} tasks currently claimed by other agents")
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "active_conflicts": [
                {"id": t.get("id"), "claimed_by": t.get("claimed_by")} 
                for t in other_agent_tasks
            ],
            "protocol_version": protocol.get("version", "unknown"),
            "message": "Protocol compliance check complete"
        }
    except Exception as e:
        return {
            "compliant": False,
            "error": str(e),
            "violations": [f"Protocol check failed: {str(e)}"],
            "warnings": []
        }

def _brain_request_handoff_impl(to_agent: str, context: str, request: str, 
                                priority: int = 3, artifacts: List[str] = None) -> str:
    """Create a handoff request."""
    try:
        brain = get_brain_path()
        
        # Create handoff request
        handoff = {
            "id": f"handoff-{int(time.time())}-{str(uuid.uuid4())[:4]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "from_agent": "current_session",  # Will be filled by caller
            "to_agent": to_agent,
            "priority": priority,
            "context": context,
            "request": request,
            "artifacts": artifacts or [],
            "status": "pending"
        }
        
        # Save to handoffs file
        handoffs_path = brain / "ledger" / "handoffs.json"
        handoffs = []
        if handoffs_path.exists():
            with open(handoffs_path) as f:
                handoffs = json.load(f)
        
        handoffs.append(handoff)
        
        with open(handoffs_path, "w") as f:
            json.dump(handoffs, f, indent=2)
        
        # Emit event
        _emit_event("handoff_requested", "nucleus_mcp", {
            "handoff_id": handoff["id"],
            "to_agent": to_agent,
            "priority": priority
        })
        
        # Format for human visibility
        formatted = f"""
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: {to_agent}
PRIORITY: P{priority}
CONTEXT: {context}
REQUEST: {request}
ARTIFACTS: {', '.join(artifacts) if artifacts else 'None'}
━━━━━━━━━━━━━━━━━━
ID: {handoff['id']}
Status: Pending - will appear in target agent's session_start
"""
        return formatted
        
    except Exception as e:
        return f"Error creating handoff: {str(e)}"

def _brain_get_handoffs_impl(agent_id: str = None) -> str:
    """Get pending handoffs."""
    try:
        brain = get_brain_path()
        handoffs_path = brain / "ledger" / "handoffs.json"
        
        if not handoffs_path.exists():
            return json.dumps({"handoffs": [], "message": "No handoffs found"})
        
        with open(handoffs_path) as f:
            handoffs = json.load(f)
        
        # Filter to pending
        pending = [h for h in handoffs if h.get("status") == "pending"]
        
        # Filter by agent if specified
        if agent_id:
            pending = [h for h in pending if h.get("to_agent") == agent_id]
        
        return json.dumps({
            "handoffs": pending,
            "count": len(pending),
            "message": f"Found {len(pending)} pending handoff(s)"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e), "handoffs": []})
