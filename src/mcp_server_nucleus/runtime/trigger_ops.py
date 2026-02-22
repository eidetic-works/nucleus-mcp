from typing import List, Dict, Any
import time
import json
from .common import get_brain_path, logger
from .event_ops import _emit_event

def _trigger_agent_impl(agent: str, task_description: str, context_files: List[str] = None) -> str:
    """Core logic for triggering an agent."""
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
            
        with open(triggers_path, "r") as f:
            triggers_data = json.load(f)
        
        # Return list of trigger definitions
        return triggers_data.get("triggers", [])
    except Exception as e:
        logger.error(f"Error reading triggers: {e}")
        return []

def _evaluate_triggers_impl(event_type: str, emitter: str) -> List[str]:
    """Core logic for evaluating which agents should activate."""
    try:
        triggers = _get_triggers_impl()
        matching_agents = []
        
        for trigger in triggers:
            # Check if this trigger matches the event
            if trigger.get("event_type") == event_type:
                # Check emitter filter if specified
                emitter_filter = trigger.get("emitter_filter")
                if emitter_filter is None or emitter in emitter_filter:
                    matching_agents.append(trigger.get("target_agent"))
        
        return list(set(matching_agents))  # Dedupe
    except Exception as e:
        logger.error(f"Error evaluating triggers: {e}")
        return []
