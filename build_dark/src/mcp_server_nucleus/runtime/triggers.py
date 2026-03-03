"""
Nucleus Agent Runtime - Neural Triggers
========================================
The routing layer that matches events to agents.
Events trigger agents based on configurable rules.

Location: mcp_server_nucleus/runtime/triggers.py
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


def get_triggers_path(brain_path: Path) -> Path:
    """Get path to triggers configuration"""
    return brain_path / "ledger" / "triggers.json"


def load_triggers(brain_path: Path) -> Dict:
    """Load trigger definitions from disk"""
    triggers_path = get_triggers_path(brain_path)
    
    if triggers_path.exists():
        return json.loads(triggers_path.read_text())
    
    # Return default triggers
    return get_default_triggers()


def get_default_triggers() -> Dict:
    """
    Default trigger definitions based on .brain/agents/*.md protocols.
    Maps events to the agents that should handle them.
    """
    return {
        "version": "1.0",
        "triggers": [
            # Task Assignment (any agent)
            {
                "id": "task-assigned",
                "event_type": "task_assigned",
                "condition": "always",
                "activates": "{{payload.target_agent}}",  # Dynamic from payload
                "description": "Route task to specified agent"
            },
            
            # Implementation → Critic Review
            {
                "id": "impl-complete-review",
                "event_type": "implementation_complete",
                "condition": "always",
                "activates": "critic",
                "description": "Developer finished, Critic reviews"
            },
            
            # Strategy Update → Critic Validation
            {
                "id": "strategy-validation",
                "event_type": "strategy_updated",
                "condition": "always",
                "activates": "critic",
                "description": "Strategy changed, Critic validates coherence"
            },
            
            # Spec Ready → Developer Implementation
            {
                "id": "spec-to-dev",
                "event_type": "spec_ready_for_development",
                "condition": "always",
                "activates": "developer",
                "description": "Architect finished spec, Developer implements"
            },
            
            # Review Approved → DevOps Deploy
            {
                "id": "approved-to-deploy",
                "event_type": "review_approved",
                "condition": "payload.review_type == 'code'",
                "activates": "devops",
                "description": "Code approved, DevOps can deploy"
            },
            
            # Critical Events → Synthesizer Escalation
            {
                "id": "critical-escalation",
                "event_type": "*",
                "condition": "severity == 'CRITICAL'",
                "activates": "synthesizer",
                "description": "Any critical event escalates to Synthesizer"
            },
            
            # Sprint Started → Research Kick-off
            {
                "id": "sprint-research",
                "event_type": "sprint_started",
                "condition": "always",
                "activates": "researcher",
                "description": "New sprint, Researcher gathers context"
            }
        ]
    }


def save_triggers(brain_path: Path, triggers: Dict) -> None:
    """Save trigger definitions to disk"""
    triggers_path = get_triggers_path(brain_path)
    triggers_path.parent.mkdir(parents=True, exist_ok=True)
    triggers_path.write_text(json.dumps(triggers, indent=2))


def evaluate_condition(condition: str, event: Dict) -> bool:
    """
    Evaluate a trigger condition against an event.
    Supports:
    - "always" - always matches
    - "severity == 'CRITICAL'" - severity check
    - "payload.field == 'value'" - payload field check
    """
    if condition == "always":
        return True
    
    # Simple expression evaluation (safe subset)
    try:
        # Extract variables from event
        severity = event.get("severity", "ROUTINE")
        payload = event.get("payload", {})
        event_type = event.get("event_type", "")
        
        # Basic condition parsing
        if "severity ==" in condition:
            target = condition.split("==")[1].strip().strip("'\"")
            return severity == target
        
        if "payload." in condition:
            # e.g., "payload.review_type == 'code'"
            parts = condition.split("==")
            field_path = parts[0].strip().replace("payload.", "")
            target = parts[1].strip().strip("'\"")
            return payload.get(field_path) == target
        
        if "event_type ==" in condition:
            target = condition.split("==")[1].strip().strip("'\"")
            return event_type == target
        
    except Exception:
        pass
    
    return False


def resolve_agent(activates: str, event: Dict) -> Optional[str]:
    """
    Resolve the agent name from the trigger.
    Supports dynamic references like {{payload.target_agent}}
    """
    if activates.startswith("{{") and activates.endswith("}}"):
        # Dynamic reference
        path = activates[2:-2].strip()
        
        if path.startswith("payload."):
            field = path.replace("payload.", "")
            return event.get("payload", {}).get(field)
        
        return event.get(path)
    
    # Static agent name
    return activates


def match_triggers(brain_path: Path, event: Dict) -> List[Dict]:
    """
    Find all triggers that match an event.
    Returns list of matched triggers with resolved agent names.
    """
    triggers_config = load_triggers(brain_path)
    triggers = triggers_config.get("triggers", [])
    matched = []
    
    event_type = event.get("event_type") or event.get("type", "")
    
    for trigger in triggers:
        trigger_event_type = trigger.get("event_type", "")
        
        # Check event type match
        if trigger_event_type != "*" and trigger_event_type != event_type:
            continue
        
        # Check condition
        condition = trigger.get("condition", "always")
        if not evaluate_condition(condition, event):
            continue
        
        # Resolve agent
        agent = resolve_agent(trigger.get("activates", ""), event)
        if not agent:
            continue
        
        matched.append({
            "trigger_id": trigger.get("id"),
            "agent": agent,
            "description": trigger.get("description", ""),
            "event": event
        })
    
    return matched


def get_agents_for_event(brain_path: Path, event: Dict) -> List[str]:
    """
    Simple helper: get list of agent names that should be activated for an event.
    """
    matched = match_triggers(brain_path, event)
    return list(set(m["agent"] for m in matched))


def add_trigger(brain_path: Path, trigger: Dict) -> None:
    """Add a new trigger definition"""
    triggers_config = load_triggers(brain_path)
    triggers_config["triggers"].append(trigger)
    save_triggers(brain_path, triggers_config)


def remove_trigger(brain_path: Path, trigger_id: str) -> bool:
    """Remove a trigger by ID"""
    triggers_config = load_triggers(brain_path)
    original_count = len(triggers_config["triggers"])
    triggers_config["triggers"] = [
        t for t in triggers_config["triggers"] 
        if t.get("id") != trigger_id
    ]
    
    if len(triggers_config["triggers"]) < original_count:
        save_triggers(brain_path, triggers_config)
        return True
    
    return False
