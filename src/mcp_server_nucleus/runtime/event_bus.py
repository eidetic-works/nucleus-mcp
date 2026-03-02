"""
EventBus — Pub/Sub Event Distribution for Nucleus OS
=====================================================
Thread-safe event bus enabling decoupled communication between
Brain subsystems. Core component of the File Watcher Event Bus
(PRODUCT_SPECS Tiers 1-3).

Usage:
    from mcp_server_nucleus.runtime.event_bus import get_event_bus, BrainFileEvent

    bus = get_event_bus()
    bus.subscribe("file_modified", my_handler)
    bus.publish(BrainFileEvent(event_type="modified", path="ledger/tasks.json"))
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from collections import deque

logger = logging.getLogger("nucleus.event_bus")


@dataclass
class BrainFileEvent:
    """Represents a file change event published to the bus."""
    event_type: str  # created, modified, deleted, moved
    path: str        # Relative path within .brain/
    source: str = "FILE_MONITOR"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "path": self.path,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class EventBus:
    """
    Thread-safe pub/sub event bus.

    Features:
    - Subscribe callbacks to specific event types or wildcard "*"
    - Bounded event history for polling (default: last 200 events)
    - Non-blocking publish (errors in subscribers don't cascade)
    """

    def __init__(self, max_history: int = 200):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: deque = deque(maxlen=max_history)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[BrainFileEvent], None]) -> None:
        """
        Register a callback for a specific event type.

        Args:
            event_type: Event type to listen for (e.g., "file_modified", "*" for all)
            callback: Function to call when event is published
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscriber registered for '{event_type}'")

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """Remove a callback from a specific event type."""
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    return True
                except ValueError:
                    return False
            return False

    def publish(self, event: BrainFileEvent) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish

        Returns:
            Number of subscribers notified
        """
        notified = 0
        event_key = f"file_{event.event_type}"

        with self._lock:
            self._history.append(event)
            # Collect matching subscribers under lock
            targets = []
            if event_key in self._subscribers:
                targets.extend(self._subscribers[event_key])
            if "*" in self._subscribers:
                targets.extend(self._subscribers["*"])

        # Call subscribers outside lock to prevent deadlocks
        for cb in targets:
            try:
                cb(event)
                notified += 1
            except Exception as e:
                logger.warning(f"EventBus subscriber error: {e}")

        return notified

    def get_recent(self, n: int = 50, since: Optional[float] = None) -> List[BrainFileEvent]:
        """
        Get recent events from history.

        Args:
            n: Maximum number of events to return
            since: Optional timestamp — only return events after this time

        Returns:
            List of recent events (newest last)
        """
        with self._lock:
            if since is not None:
                return [e for e in self._history if e.timestamp > since][-n:]
            return list(self._history)[-n:]

    def get_stats(self) -> dict:
        """Get bus statistics."""
        with self._lock:
            return {
                "subscriber_count": sum(len(v) for v in self._subscribers.values()),
                "event_types": list(self._subscribers.keys()),
                "history_size": len(self._history),
                "history_capacity": self._history.maxlen,
            }


# ─── Singleton ─────────────────────────────────────────────────
_global_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Get or create the global EventBus singleton."""
    global _global_bus
    if _global_bus is None:
        with _bus_lock:
            if _global_bus is None:
                _global_bus = EventBus()
                logger.info("🚌 EventBus initialized")
    return _global_bus


# ─── Change Ledger ─────────────────────────────────────────────

# Maps .brain/ file patterns → affected brain:// resource URIs
FILE_TO_URI_MAP: Dict[str, List[str]] = {
    "state.json":    ["brain://state", "brain://context"],
    "tasks.json":    ["brain://state", "brain://context"],
    "engrams.json":  ["brain://state", "brain://context"],
    "events.jsonl":  ["brain://events"],
    "sessions/":     ["brain://context"],
    "memory/":       ["brain://state"],
    "ledger/":       ["brain://state"],
    "commitments/":  ["brain://state"],
    "config/":       ["brain://context"],
    "nucleus.db":    ["brain://state", "brain://context"],
}


class ChangeLedger:
    """
    Monotonic version tracker for brain:// resources.

    When a .brain/ file changes, the ledger maps it to the affected
    brain:// URIs and increments their version counters. MCP clients
    can read ``brain://changes`` to detect staleness across ALL
    resources in a single, cheap read.

    Thread-safe via Lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._global_version: int = 0
        self._uri_versions: Dict[str, Dict[str, Any]] = {}
        self._recent_changes: deque = deque(maxlen=50)

    def record_change(self, rel_path: str, event_type: str) -> List[str]:
        """
        Record a file change and increment affected URI versions.

        Args:
            rel_path: Relative path within .brain/ (e.g., "tasks.json")
            event_type: Type of change (created, modified, deleted)

        Returns:
            List of brain:// URIs whose versions were bumped
        """
        affected_uris: List[str] = []
        now = time.time()

        with self._lock:
            self._global_version += 1

            # Find matching URIs from the file-to-URI map
            for pattern, uris in FILE_TO_URI_MAP.items():
                if pattern in rel_path:
                    for uri in uris:
                        if uri not in affected_uris:
                            affected_uris.append(uri)
                        if uri not in self._uri_versions:
                            self._uri_versions[uri] = {"version": 0, "last_changed_at": 0.0}
                        self._uri_versions[uri]["version"] += 1
                        self._uri_versions[uri]["last_changed_at"] = now

            # Record in recent changes
            self._recent_changes.append({
                "path": rel_path,
                "event_type": event_type,
                "affected_uris": affected_uris,
                "global_version": self._global_version,
                "timestamp": now,
            })

        return affected_uris

    def get_snapshot(self) -> dict:
        """
        Get the full ledger state for the brain://changes resource.

        Returns:
            Dict with global_version, per-URI versions, and recent changes
        """
        with self._lock:
            return {
                "global_version": self._global_version,
                "uri_versions": dict(self._uri_versions),
                "recent_changes": list(self._recent_changes),
                "description": "Poll this resource to detect staleness. Compare global_version between reads.",
            }

    def get_global_version(self) -> int:
        """Get the current global version (lock-free read for primitives)."""
        return self._global_version


# ─── ChangeLedger Singleton ────────────────────────────────────
_global_ledger: Optional[ChangeLedger] = None
_ledger_lock = threading.Lock()


def get_change_ledger() -> ChangeLedger:
    """Get or create the global ChangeLedger singleton."""
    global _global_ledger
    if _global_ledger is None:
        with _ledger_lock:
            if _global_ledger is None:
                _global_ledger = ChangeLedger()
                logger.info("📋 ChangeLedger initialized")
    return _global_ledger
