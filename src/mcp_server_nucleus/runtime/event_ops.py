
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .common import get_brain_path, logger


def _log_interaction(emitter: str, event_type: str, data: Dict[str, Any]) -> None:
    """Log a cryptographic hash of the interaction for user trust (V9 Security)."""
    try:
        import hashlib
        brain = get_brain_path()
        log_path = brain / "ledger" / "interaction_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

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

def _emit_event(event_type: str, emitter: str, data: Dict[str, Any] = None, description: str = "") -> str:
    """Core logic for emitting an event."""
    if data is None:
        data = {}
    try:
        brain = get_brain_path()
        events_path = brain / "ledger" / "events.jsonl"
        events_path.parent.mkdir(parents=True, exist_ok=True)

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
        logger.error(f"Error reading events: {e}")
        return []
