"""
Nucleus Agent Runtime - Event Stream
=====================================
The nervous system of the Agent Control Plane.
Events flow through here, triggering agent activation.

Location: mcp_server_nucleus/runtime/event_stream.py
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid


class EventSeverity(Enum):
    """Event severity levels per synthesizer.md protocol"""
    ROUTINE = "ROUTINE"     # Auto-approve, log only
    NOTABLE = "NOTABLE"     # Include in Daily Digest
    CRITICAL = "CRITICAL"   # IMMEDIATE escalation to founder


def get_events_path(brain_path: Path) -> Path:
    """Get path to event stream"""
    return brain_path / "ledger" / "events.jsonl"


def read_events(brain_path: Path, limit: int = 50) -> List[Dict]:
    """
    Read the last N events from the stream.
    Returns events in reverse chronological order (newest first).
    """
    events_path = get_events_path(brain_path)
    
    if not events_path.exists():
        return []
    
    # Read all events
    events = []
    with open(events_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Return last N, reversed (newest first)
    return events[-limit:][::-1]


def emit_event(
    brain_path: Path,
    event_type: str,
    emitter: str,
    payload: Dict[str, Any],
    severity: EventSeverity = EventSeverity.ROUTINE,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Emit an event to the stream.
    Returns the created event.
    """
    events_path = get_events_path(brain_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    
    event = {
        "event_id": f"{emitter[:3]}-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "emitter": emitter,
        "event_type": event_type,
        "severity": severity.value,
        "payload": payload,
        "metadata": metadata or {}
    }
    
    # Append to stream
    with open(events_path, 'a') as f:
        f.write(json.dumps(event) + '\n')
    
    # Bridge to Cloud (Fire & Forget)
    try:
        from mcp_server_nucleus.runtime.firestore_bridge import get_bridge
        get_bridge().push_event(event)
    except Exception:
        # Never block local op on cloud fail
        pass
    
    return event


def get_unprocessed_events(
    brain_path: Path, 
    last_processed_id: Optional[str] = None,
    severity_filter: Optional[EventSeverity] = None
) -> List[Dict]:
    """
    Get events that haven't been processed yet.
    Optionally filter by severity.
    """
    events = read_events(brain_path, limit=100)
    
    # If we have a last processed ID, skip events until we find it
    if last_processed_id:
        found = False
        filtered = []
        for event in events:
            if found:
                filtered.append(event)
            elif event.get('event_id') == last_processed_id:
                found = True
        events = filtered if found else events
    
    # Filter by severity if specified
    if severity_filter:
        events = [e for e in events if e.get('severity') == severity_filter.value]
    
    return events


def get_critical_events(brain_path: Path, limit: int = 10) -> List[Dict]:
    """Get CRITICAL events that need immediate attention"""
    events = read_events(brain_path, limit=limit * 5)  # Read more to find criticals
    return [e for e in events if e.get('severity') == 'CRITICAL'][:limit]


def rotate_events(brain_path: Path, keep_count: int = 1000) -> int:
    """
    Rotate event stream to prevent unbounded growth.
    Keeps the last N events, archives the rest.
    Returns count of archived events.
    """
    events_path = get_events_path(brain_path)
    archive_path = brain_path / "ledger" / "archive" / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    if not events_path.exists():
        return 0
    
    # Read all events
    events = []
    with open(events_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(line)
    
    if len(events) <= keep_count:
        return 0
    
    # Split into keep and archive
    to_archive = events[:-keep_count]
    to_keep = events[-keep_count:]
    
    # Write archive
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with open(archive_path, 'w') as f:
        f.write('\n'.join(to_archive) + '\n')
    
    # Overwrite main file with kept events
    with open(events_path, 'w') as f:
        f.write('\n'.join(to_keep) + '\n')
    
    return len(to_archive)


# ============================================================
# COMMON EVENT TYPES (for type safety)
# ============================================================

class EventTypes:
    """Standard event types in the system"""
    # Task lifecycle
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # Sprint lifecycle
    SPRINT_STARTED = "sprint_started"
    SPRINT_COMPLETED = "sprint_completed"
    
    # Agent lifecycle
    AGENT_ACTIVATED = "agent_activated"
    AGENT_TERMINATED = "agent_terminated"
    
    # Review lifecycle
    IMPLEMENTATION_COMPLETE = "implementation_complete"
    REVIEW_APPROVED = "review_approved"
    REVIEW_BLOCKED = "review_blocked"
    
    # Escalation
    FOUNDER_DECISION_NEEDED = "founder_decision_needed"
    
    # System
    BRAIN_INITIALIZED = "brain_initialized"
    DAILY_DIGEST_GENERATED = "daily_digest_generated"
    META_OPTIMIZATION_COMPLETE = "meta_optimization_complete"
    
    # v0.6.0 DSoR - Federation Events
    FEDERATION_PEER_JOINED = "federation_peer_joined"
    FEDERATION_PEER_LEFT = "federation_peer_left"
    FEDERATION_PEER_SUSPECT = "federation_peer_suspect"
    FEDERATION_LEADER_ELECTED = "federation_leader_elected"
    FEDERATION_TASK_ROUTED = "federation_task_routed"
    FEDERATION_STATE_SYNCED = "federation_state_synced"
    
    # v0.6.0 DSoR - Decision Provenance
    DECISION_MADE = "decision_made"
    CONTEXT_SNAPSHOT = "context_snapshot"
    IPC_TOKEN_ISSUED = "ipc_token_issued"
    IPC_TOKEN_CONSUMED = "ipc_token_consumed"
