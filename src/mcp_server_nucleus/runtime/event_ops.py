"""
Nucleus Runtime - Event Operations
==================================
Core logic for event stream management.
"""

import json
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

from .common import get_brain_path, logger

def _log_interaction(emitter: str, event_type: str, data: Dict[str, Any]) -> None:
    """Log a cryptographic hash of the interaction for user trust (V9 Security)."""
    try:
        import hashlib
        brain = get_brain_path()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        
        # Create a stable string representation for hashing
        payload = json.dumps({"type": event_type, "emitter": emitter, "data": data}, sort_keys=True)
        h = hashlib.sha256(payload.encode()).hexdigest()
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "emitter": emitter,
            "type": event_type,
            "hash": h,
            "alg": "sha256"
        }
        
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Failed to log interaction trust signal: {e}")

def _emit_event(event_type: str, emitter: str, data: Dict[str, Any], description: str = "") -> str:
    """Core logic for emitting an event."""
    try:
        brain = get_brain_path()
        events_path = brain / "ledger" / "events.jsonl"
        
        event_id = f"evt-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        event = {
            "event_id": event_id,
            "timestamp": timestamp,
            "type": event_type,
            "emitter": emitter,
            "data": data,
            "description": description
        }
        
        with open(events_path, "a") as f:
            f.write(json.dumps(event) + "\n")

        # Log interaction for security audit (Trust Signal)
        _log_interaction(emitter, event_type, data)
        
        # Update activity summary for fast satellite view (Tier 2 precomputation)
        try:
            summary_path = brain / "ledger" / "activity_summary.json"
            summary = {}
            if summary_path.exists():
                with open(summary_path, "r") as f:
                    summary = json.load(f)
            
            summary["last_event"] = event
            summary["updated_at"] = timestamp
            summary["event_count"] = summary.get("event_count", 0) + 1
            
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass  # Don't fail event emit if summary update fails
            
        return event_id
    except Exception as e:
        return f"Error emitting event: {str(e)}"

def _read_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Core logic for reading events."""
    try:
        brain = get_brain_path()
        events_path = brain / "ledger" / "events.jsonl"
        
        if not events_path.exists():
            return []
            
        events = []
        with open(events_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        return events[-limit:]
    except Exception as e:
        # Avoid logger dependency here if possible, or print
        print(f"Error reading events: {e}")
        return []
