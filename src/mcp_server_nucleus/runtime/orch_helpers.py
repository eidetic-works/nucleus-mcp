"""Orchestration Helpers — Slot registry, tier management, dependency graph.

Extracted from __init__.py (NOP V3 orchestration support functions).
Contains:
- Slot registry I/O: _get_slot_registry, _save_slot_registry
- Tier management: _get_tier_definitions, _get_tier_for_model, _resolve_slot_id
- Task analysis: _infer_task_tier, _can_slot_run_task, _compute_slot_blockers
- Fence tokens: _increment_fence_token
- Cost tracking: _get_model_cost
- Dependency graph: _compute_dependency_graph
- Slot scoring: _score_slot_for_task
- Claim/complete: _claim_with_fence, _complete_with_fence
"""

import json
import time
from typing import Dict, List

from .common import get_brain_path
from .event_ops import _emit_event

def _lazy(name):
    import mcp_server_nucleus as m
    return getattr(m, name)


def _get_slot_registry() -> Dict:
    """Load slot registry from disk."""
    brain = get_brain_path()
    registry_path = brain / "slots" / "registry.json"
    if not registry_path.exists():
        return {"slots": {}, "aliases": {}}
    with open(registry_path) as f:
        return json.load(f)


def _save_slot_registry(registry: Dict):
    """Save slot registry to disk."""
    brain = get_brain_path()
    registry_path = brain / "slots" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def _get_tier_definitions() -> Dict:
    """Load tier definitions from disk."""
    brain = get_brain_path()
    tiers_path = brain / "protocols" / "tiers.json"
    if not tiers_path.exists():
        return {"tiers": {}, "tier_priority_mapping": {}}
    with open(tiers_path) as f:
        return json.load(f)


def _resolve_slot_id(slot_id: str, registry: Dict) -> str:
    """Resolve alias to actual slot ID."""
    if slot_id in registry.get("slots", {}):
        return slot_id
    return registry.get("aliases", {}).get(slot_id, slot_id)


def _get_tier_for_model(model: str, tier_defs: Dict) -> str:
    """Determine tier for a model."""
    model_lower = model.lower().replace(" ", "_").replace("-", "_")
    for tier_name, tier_info in tier_defs.get("tiers", {}).items():
        models = [m.lower() for m in tier_info.get("models", [])]
        if model_lower in models or any(model_lower in m or m in model_lower for m in models):
            return tier_name
    return "standard"  # Default


def _infer_task_tier(task: Dict, tier_defs: Dict) -> str:
    """Infer required tier from task metadata."""
    # Check explicit required_tier
    if task.get("required_tier"):
        return task["required_tier"]
    
    # Check environment (human tasks)
    if task.get("environment") == "human":
        return "human"
    
    # Infer from priority
    priority = task.get("priority", 3)
    mapping = tier_defs.get("tier_priority_mapping", {})
    return mapping.get(str(priority), "standard")


def _can_slot_run_task(slot_tier: str, task_tier: str, tier_defs: Dict) -> bool:
    """Check if slot tier can handle task tier."""
    if task_tier == "human":
        return False  # Human tasks can't be claimed by slots
    
    tiers = tier_defs.get("tiers", {})
    slot_level = tiers.get(slot_tier, {}).get("level", 99)
    task_level = tiers.get(task_tier, {}).get("level", 1)
    
    # Lower level = more powerful. Slot can run if its level <= task level.
    return slot_level <= task_level


def _compute_slot_blockers(task: Dict, tasks: List[Dict], registry: Dict) -> List[str]:
    """Compute which slots are blocking this task."""
    blocking_slots = set()
    blocked_by = task.get("blocked_by", [])
    
    for dep_id in blocked_by:
        # Find the dependency task
        dep_task = next((t for t in tasks if t.get("id") == dep_id), None)
        if not dep_task:
            continue
        
        # If dependency is not done, check who owns it
        if dep_task.get("status") != "DONE":
            claimed_by = dep_task.get("claimed_by")
            if claimed_by:
                blocking_slots.add(claimed_by)
    
    return list(blocking_slots)


# ============================================================================
# NOP V3.0: FENCING TOKEN SYSTEM
# ============================================================================

def _get_fence_counter() -> Dict:
    """Load fence counter from disk."""
    brain = get_brain_path()
    counter_path = brain / "ledger" / "fence_counter.json"
    if not counter_path.exists():
        return {"value": 100, "last_issued": None, "history": []}
    with open(counter_path) as f:
        return json.load(f)


def _increment_fence_token() -> int:
    """Atomically increment and return the next fence token."""
    brain = get_brain_path()
    counter_path = brain / "ledger" / "fence_counter.json"
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    
    counter = _get_fence_counter()
    counter["value"] += 1
    counter["last_issued"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    with open(counter_path, "w") as f:
        json.dump(counter, f, indent=2)
    
    return counter["value"]


def _get_model_cost(model: str) -> float:
    """Get cost per 1K tokens for a model."""
    tier_defs = _get_tier_definitions()
    model_costs = tier_defs.get("model_costs", {})
    
    # Normalize model name
    model_lower = model.lower().replace(" ", "_").replace("-", "_")
    
    # Direct lookup
    if model_lower in model_costs:
        return model_costs[model_lower]
    
    # Fuzzy match
    for cost_model, cost in model_costs.items():
        if model_lower in cost_model or cost_model in model_lower:
            return cost
    
    return 0.010  # Default cost


# ============================================================================
# NOP V3.0: DEPENDENCY GRAPH COMPUTATION
# ============================================================================

def _compute_dependency_graph(tasks: List[Dict], registry: Dict) -> Dict:
    """
    Compute full dependency graph with slot-level blocking.
    
    Returns:
        {
            "task_to_task": {task_id: [blocking_task_ids]},
            "task_to_slot": {task_id: [blocking_slot_ids]},
            "slot_to_slot": {slot_id: [blocked_by_slot_ids]},
            "circular_deps": [[cycle_path]],
            "blocking_chains": {task_id: [full_chain]},
            "computed_at": timestamp
        }
    """
    from collections import defaultdict
    
    graph = {
        "task_to_task": {},
        "task_to_slot": {},
        "slot_to_slot": defaultdict(set),
        "circular_deps": [],
        "blocking_chains": {},
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    
    # Build task assignments map
    task_assignments = {}
    for task in tasks:
        task_id = task.get("id")
        assigned = task.get("assigned_slot") or task.get("claimed_by")
        if task_id and assigned:
            task_assignments[task_id] = assigned
    
    # Step 1: Build task-to-task graph
    for task in tasks:
        task_id = task.get("id")
        blockers = task.get("blocked_by", [])
        graph["task_to_task"][task_id] = blockers
        
        # Step 2: Compute task-to-slot (which slots are blocking this task)
        blocking_slots = set()
        for blocker_id in blockers:
            blocker_task = next((t for t in tasks if t.get("id") == blocker_id), None)
            if blocker_task and blocker_task.get("status") != "DONE":
                blocker_slot = task_assignments.get(blocker_id)
                if blocker_slot:
                    blocking_slots.add(blocker_slot)
        
        if blocking_slots:
            graph["task_to_slot"][task_id] = list(blocking_slots)
        
        # Step 3: Compute slot-to-slot
        my_slot = task_assignments.get(task_id)
        if my_slot:
            for blocking_slot in blocking_slots:
                if blocking_slot != my_slot:
                    graph["slot_to_slot"][my_slot].add(blocking_slot)
    
    # Convert defaultdict to regular dict with lists
    graph["slot_to_slot"] = {k: list(v) for k, v in graph["slot_to_slot"].items()}
    
    # Step 4: Detect circular dependencies (DFS)
    visited = set()
    path = []
    
    def dfs_cycle(task_id):
        if task_id in path:
            cycle_start = path.index(task_id)
            cycle = path[cycle_start:] + [task_id]
            if cycle not in graph["circular_deps"]:
                graph["circular_deps"].append(cycle)
            return
        if task_id in visited:
            return
        
        visited.add(task_id)
        path.append(task_id)
        
        for blocker in graph["task_to_task"].get(task_id, []):
            dfs_cycle(blocker)
        
        path.pop()
    
    for task in tasks:
        dfs_cycle(task.get("id"))
    
    # Step 5: Compute blocking chains (transitive closure)
    def get_full_chain(task_id, seen=None):
        if seen is None:
            seen = set()
        if task_id in seen:
            return []
        seen.add(task_id)
        
        chain = []
        for blocker in graph["task_to_task"].get(task_id, []):
            chain.append(blocker)
            chain.extend(get_full_chain(blocker, seen))
        return chain
    
    for task in tasks:
        task_id = task.get("id")
        graph["blocking_chains"][task_id] = get_full_chain(task_id)
    
    return graph


# ============================================================================
# NOP V3.0: MULTI-FACTOR SLOT SCORING
# ============================================================================

def _score_slot_for_task(task: Dict, slot: Dict, tier_defs: Dict) -> Dict:
    """
    Score a slot for a task using multi-factor analysis.
    
    Returns:
        {
            "score": 0-100,
            "breakdown": {factor: points},
            "warnings": [],
            "recommendation": str
        }
    """
    score = 0
    breakdown = {}
    warnings = []
    
    tiers = tier_defs.get("tiers", {})
    task_tier = _infer_task_tier(task, tier_defs)
    slot_tier = slot.get("tier", "standard")
    
    task_level = tiers.get(task_tier, {}).get("level", 3)
    slot_level = tiers.get(slot_tier, {}).get("level", 3)
    
    # 1. TIER MATCH (0-30 points)
    if slot_level == task_level:
        breakdown["tier_match"] = 30
        score += 30
    elif slot_level < task_level:
        breakdown["tier_match"] = 25  # Overpowered
        score += 25
    elif slot_level == task_level + 1:
        breakdown["tier_match"] = 10  # Slightly underpowered
        score += 10
        warnings.append(f"Slot tier ({slot_tier}) is 1 level below task tier ({task_tier})")
    else:
        breakdown["tier_match"] = 0  # Too weak
        warnings.append(f"TIER_MISMATCH: Slot ({slot_tier}) cannot handle task ({task_tier})")
    
    # 2. AVAILABILITY (0-25 points)
    if slot.get("status") == "active" and not slot.get("current_task"):
        breakdown["availability"] = 25
        score += 25
    elif slot.get("status") == "active":
        breakdown["availability"] = 10
        score += 10
    else:
        breakdown["availability"] = 0
        warnings.append(f"Slot status: {slot.get('status')}")
    
    # 3. CAPABILITY MATCH (0-20 points)
    task_skills = set(task.get("required_skills", []))
    slot_caps = set(slot.get("capabilities", []))
    if task_skills:
        overlap = len(task_skills & slot_caps) / len(task_skills)
        cap_score = int(overlap * 20)
        breakdown["capability"] = cap_score
        score += cap_score
    else:
        breakdown["capability"] = 15  # No specific skills required
        score += 15
    
    # 4. COST EFFICIENCY (0-15 points)
    model = slot.get("model", "")
    cost = _get_model_cost(model)
    if cost <= 0.005:
        breakdown["cost"] = 15
        score += 15
    elif cost <= 0.015:
        breakdown["cost"] = 10
        score += 10
    elif cost <= 0.030:
        breakdown["cost"] = 5
        score += 5
    else:
        breakdown["cost"] = 0
    
    # 5. HEALTH (0-10 points)
    success_rate = slot.get("success_rate", 1.0)
    health_score = int(success_rate * 10)
    breakdown["health"] = health_score
    score += health_score
    
    # Generate recommendation
    if score >= 80:
        recommendation = "EXCELLENT match"
    elif score >= 60:
        recommendation = "GOOD match"
    elif score >= 40:
        recommendation = "ACCEPTABLE with warnings"
    else:
        recommendation = "NOT RECOMMENDED"
    
    return {
        "score": score,
        "breakdown": breakdown,
        "warnings": warnings,
        "recommendation": recommendation,
        "slot_id": slot.get("id"),
        "estimated_cost": _get_model_cost(slot.get("model", "")) * task.get("estimated_tokens", 5000) / 1000
    }


# ============================================================================
# NOP V3.0: CLAIM WITH FENCING
# ============================================================================

def _claim_with_fence(task_id: str, slot_id: str) -> Dict:
    """
    Atomically claim a task with fencing token.
    
    Returns:
        {"success": bool, "fence_token": int, "error": str}
    """
    try:
        from .db import get_storage_backend
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Check if already claimed by someone else
        if task.get("claimed_by") and task.get("claimed_by") != slot_id:
            return {
                "success": False,
                "error": f"Task already claimed by {task['claimed_by']}",
                "current_fence": task.get("fence_token")
            }
        
        # Issue new fence token
        fence_token = _increment_fence_token()
        
        # Update task
        task["claimed_by"] = slot_id
        task["fence_token"] = fence_token
        task["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        task["status"] = "IN_PROGRESS"
        
        storage.update_task(task["id"], task)
        
        # Update slot
        registry = _get_slot_registry()
        if slot_id in registry.get("slots", {}):
            registry["slots"][slot_id]["current_task"] = task_id
            registry["slots"][slot_id]["fence_token"] = fence_token
            _save_slot_registry(registry)
        
        _emit_event("task_claimed_with_fence", slot_id, {
            "task_id": task_id,
            "fence_token": fence_token
        })
        
        return {
            "success": True,
            "fence_token": fence_token,
            "task_id": task_id,
            "slot_id": slot_id
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def _complete_with_fence(task_id: str, slot_id: str, fence_token: int, outcome: str = "success") -> Dict:
    """
    Complete a task with fence token validation.
    
    Returns:
        {"success": bool, "error": str}
    """
    try:
        from .db import get_storage_backend
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Validate fence token
        if task.get("fence_token") != fence_token:
            return {
                "success": False,
                "error": "Stale fence token - task was reassigned",
                "expected_fence": fence_token,
                "current_fence": task.get("fence_token")
            }
        
        # Validate claimer
        if task.get("claimed_by") != slot_id:
            return {
                "success": False,
                "error": f"Task claimed by different slot: {task['claimed_by']}"
            }
        
        # Complete the task
        task["status"] = "DONE" if outcome == "success" else "FAILED"
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        task["completed_by"] = slot_id
        
        storage.update_task(task["id"], task)
        
        _emit_event("task_completed_with_fence", slot_id, {
            "task_id": task_id,
            "fence_token": fence_token,
            "outcome": outcome
        })
        
        return {"success": True, "task_id": task_id, "outcome": outcome}
        
    except Exception as e:
        return {"success": False, "error": str(e)}



