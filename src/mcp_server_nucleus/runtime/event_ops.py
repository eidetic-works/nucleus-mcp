"""
Nucleus Runtime - Event Operations
==================================
Core logic for event stream management.
"""

import json
import os
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

from .common import get_brain_path, logger

# Artery 5: Extensible event hook registry
_event_hooks: list = []

def register_event_hook(callback):
    """Register a callback to be called on every emitted event.
    Callback signature: (event_type: str, emitter: str, data: dict) -> None
    """
    _event_hooks.append(callback)

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
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
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
        
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        # Log interaction for security audit (Trust Signal)
        _log_interaction(emitter, event_type, data)
        
        # Update activity summary for fast satellite view (Tier 2 precomputation)
        try:
            summary_path = brain / "ledger" / "activity_summary.json"
            summary = {}
            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            
            summary["last_event"] = event
            summary["updated_at"] = timestamp
            summary["event_count"] = summary.get("event_count", 0) + 1
            
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Don't fail event emit if summary update fails

        # MDR_016: Auto-write engram hook
        # Significant events auto-generate engrams via ADUN pipeline
        try:
            from .engram_hooks import process_event_for_engram
            process_event_for_engram(event_type, data)
        except Exception:
            pass  # Never let auto-engram break event emission

        # Proactive hook: signal ChangeLedger immediately (bypasses Watchdog latency)
        try:
            from .event_bus import get_change_ledger
            get_change_ledger().record_change("events.jsonl", event_type)
        except Exception:
            pass  # Never let ledger updates break event emission

        # Evaluate triggers for this event (Artery 4: alive nervous system)
        if not os.environ.get("NUCLEUS_DISABLE_ARTERY_4"):
            try:
                from .trigger_ops import _evaluate_triggers_impl
                matching_agents = _evaluate_triggers_impl(event_type, emitter)
                if matching_agents:
                    logger.info(f"Triggers matched: {matching_agents} for {event_type}")
                    try:
                        summary_path = brain / "ledger" / "activity_summary.json"
                        if summary_path.exists():
                            with open(summary_path, "r") as f:
                                summary = json.load(f)
                            summary["last_trigger_match"] = {
                                "event_type": event_type,
                                "matched_agents": matching_agents,
                                "timestamp": timestamp
                            }
                            summary["trigger_match_count"] = summary.get("trigger_match_count", 0) + 1
                            with open(summary_path, "w") as f:
                                json.dump(summary, f, indent=2)
                    except Exception:
                        pass
            except Exception:
                pass  # Never let trigger evaluation break event emission

        # Artery 5: Fire registered event hooks
        for hook in _event_hooks:
            try:
                hook(event_type, emitter, data)
            except Exception:
                pass  # Never let hooks break event emission

        # Substrate auto-wiring: make the organism REACT to its own events
        _substrate_react(event_type, data)

        return event_id
    except Exception as e:
        return f"Error emitting event: {str(e)}"

def _substrate_react(event_type: str, data: Dict[str, Any]):
    """Auto-wire substrate reactions to lifecycle events.

    This is what makes the substrate ALIVE — not just callable, but reactive.
    Each reaction is guarded: failures never break event emission.
    """
    # Growth hook: compound growth signals on trigger events
    try:
        from .growth_ops import process_event_for_growth
        process_event_for_growth(event_type, data)
    except Exception:
        pass

    # Cycle bootstrap: ensure compounding_cycle.json exists on session start
    if event_type == "session_started":
        try:
            brain = get_brain_path()
            cycle_path = brain / "meta" / "compounding_cycle.json"
            if not cycle_path.exists():
                from .compounding_loop import _load_or_create_cycle, _save_cycle
                cycle = _load_or_create_cycle(brain, cycle_path)
                _save_cycle(cycle, cycle_path)
        except Exception:
            pass

    # EOD capture: persist learnings when session ends
    if event_type == "session_ended":
        try:
            from .compounding_loop import _end_of_day_capture_impl
            summary = data.get("summary", "Session ended")
            _end_of_day_capture_impl(summary=summary)
        except Exception:
            pass

    # Weekly consolidation: auto-run on Sunday morning brief
    if event_type == "morning_brief_generated":
        try:
            if datetime.now().weekday() == 6:  # Sunday
                brain = get_brain_path()
                lock = brain / "meta" / ".weekly_consolidation_done"
                week_str = datetime.now().strftime("%Y-W%W")
                if not lock.exists() or lock.read_text().strip() != week_str:
                    from .compounding_loop import _weekly_consolidation_impl
                    _weekly_consolidation_impl(dry_run=False)
                    lock.parent.mkdir(parents=True, exist_ok=True)
                    lock.write_text(week_str)
        except Exception:
            pass


def _read_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Core logic for reading events."""
    try:
        brain = get_brain_path()
        events_path = brain / "ledger" / "events.jsonl"
        
        if not events_path.exists():
            return []
            
        events = []
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        return events[-limit:]
    except Exception as e:
        import sys
        sys.stderr.write(f"Error reading events: {e}\n"); sys.stderr.flush()
        return []
