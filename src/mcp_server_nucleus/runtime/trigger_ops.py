"""
Trigger Operations — Event-driven dispatch with safety layers.

Phase 1 (shipped): Log-only matching. Events match triggers, results logged.
Phase 2 (this): Task-based dispatch with 3 safety layers:
  Layer 1 — Chain depth tracking: max 3 cascading event→trigger→event chains
  Layer 2 — Task-based dispatch: triggers create tasks (async, deduped)
  Layer 3 — Per-trigger opt-in: only triggers with "dispatch": true fire tasks
"""

from typing import List, Dict, Optional
import threading
import time
import json
from .common import get_brain_path, logger

# ── Layer 1: Chain Depth Tracking ──
# Prevents event→trigger→task→event cascades from running away.
_chain_depth = threading.local()
_MAX_CHAIN_DEPTH = 3


def _get_chain_depth() -> int:
    return getattr(_chain_depth, "depth", 0)


def _increment_chain_depth() -> int:
    depth = _get_chain_depth() + 1
    _chain_depth.depth = depth
    return depth


def _decrement_chain_depth():
    _chain_depth.depth = max(0, _get_chain_depth() - 1)


def _trigger_agent_impl(agent: str, task_description: str, context_files: List[str] = None) -> str:
    """Core logic for triggering an agent."""
    from .event_ops import _emit_event

    data = {
        "task_id": f"task-{int(time.time())}",
        "target_agent": agent,
        "description": task_description,
        "context_files": context_files or [],
        "status": "pending"
    }

    event_id = _emit_event(
        event_type="task_assigned",
        emitter="nucleus_mcp",
        data=data,
        description=f"Manual trigger for {agent}"
    )

    return f"Triggered {agent} with event {event_id}"


def _get_triggers_impl() -> List[Dict]:
    """Core logic for getting all triggers."""
    try:
        brain = get_brain_path()
        triggers_path = brain / "ledger" / "triggers.json"

        if not triggers_path.exists():
            return []

        with open(triggers_path, "r", encoding='utf-8') as f:
            triggers_data = json.load(f)

        return triggers_data.get("triggers", [])
    except Exception as e:
        logger.error(f"Error reading triggers: {e}")
        return []


def _evaluate_triggers_impl(event_type: str, emitter: str) -> List[str]:
    """
    Evaluate which agents should activate for an event.

    Phase 2: Also dispatches tasks for triggers with "dispatch": true,
    respecting chain depth limits and dedup.
    """
    try:
        triggers = _get_triggers_impl()
        matching_agents = []

        for trigger in triggers:
            if trigger.get("event_type") != event_type:
                continue

            emitter_filter = trigger.get("emitter_filter")
            if emitter_filter is not None and emitter not in emitter_filter:
                continue

            agent = trigger.get("target_agent")
            if agent:
                matching_agents.append(agent)

            # Layer 3: Only dispatch if trigger opts in
            if trigger.get("dispatch"):
                _dispatch_trigger(trigger, event_type, emitter)

        return list(set(matching_agents))
    except Exception as e:
        logger.error(f"Error evaluating triggers: {e}")
        return []


def _dispatch_trigger(trigger: Dict, event_type: str, emitter: str):
    """
    Layer 2: Create a task for a matched trigger.

    Safety:
    - Chain depth check (Layer 1): skip if cascade too deep
    - Dedup: skip if pending task already exists for same trigger+event
    """
    trigger_id = trigger.get("id", "unknown")
    agent = trigger.get("target_agent", "unknown")

    # Layer 1: Chain depth guard
    depth = _get_chain_depth()
    if depth >= _MAX_CHAIN_DEPTH:
        logger.warning(
            f"[trigger_dispatch] Chain depth {depth} >= {_MAX_CHAIN_DEPTH} — "
            f"skipping dispatch for {trigger_id} (prevents cascade)"
        )
        return

    _increment_chain_depth()
    try:
        # Layer 2: Dedup — check for existing pending task with same trigger
        task_key = f"trigger:{trigger_id}:{event_type}"
        if _has_pending_task(task_key):
            logger.info(
                f"[trigger_dispatch] Skipped {trigger_id} — pending task already exists"
            )
            return

        # Create the task
        desc_text = trigger.get("description", f"Dispatched by {trigger_id}")
        task_desc = f"[auto] {agent}: {desc_text}"

        try:
            from .task_ops import _add_task
            result = _add_task(
                description=task_desc,
                priority=trigger.get("priority", 3),
                source=f"trigger_dispatch:{task_key}",
            )
            if result.get("success"):
                logger.info(
                    f"[trigger_dispatch] Created task for {trigger_id} → {agent} "
                    f"(depth={depth + 1}, event={event_type})"
                )
            else:
                logger.warning(
                    f"[trigger_dispatch] Task creation returned: {result.get('error')}"
                )
        except Exception as e:
            logger.error(f"[trigger_dispatch] Failed to create task for {trigger_id}: {e}")
    finally:
        _decrement_chain_depth()


def _has_pending_task(task_key: str) -> bool:
    """Check if a pending task already exists for this trigger+event combo."""
    try:
        from .db import get_storage_backend
        storage = get_storage_backend(get_brain_path())
        tasks = storage.list_tasks()
        source_prefix = f"trigger_dispatch:{task_key}"
        for task in tasks:
            if task.get("status") in ("PENDING", "TODO", "READY"):
                if task.get("source", "").startswith(source_prefix):
                    return True
        return False
    except Exception:
        return False  # On error, allow dispatch (fail open for liveness)
