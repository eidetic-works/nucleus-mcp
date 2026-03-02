"""
File Monitor - Phase 50 Implementation
======================================
Watches the .brain folder for changes and emits events.

This is the core of "Native Sync" (Tiers 1-3 in NUCLEUS_PRODUCT_SPECS.md).
When a file changes, we notify all connected MCP clients.

Usage:
    monitor = FileMonitor(brain_path)
    monitor.start()
    # ... later
    monitor.stop()
"""

import os
import threading
import logging
from pathlib import Path
from typing import Callable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None

logger = logging.getLogger("nucleus.file_monitor")


@dataclass
class FileChangeEvent:
    """Represents a file change in the brain folder."""
    event_type: str  # created, modified, deleted, moved
    path: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_directory: bool = False
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "path": self.path,
            "timestamp": self.timestamp.isoformat(),
            "is_directory": self.is_directory
        }


class BrainEventHandler(FileSystemEventHandler):
    """Handles file system events in the .brain folder."""
    
    def __init__(self, callback: Callable[[FileChangeEvent], None]):
        self.callback = callback
        self._debounce_cache: dict = {}
        self._debounce_ms = 100  # Ignore duplicate events within 100ms
        
    def _should_ignore(self, path: str) -> bool:
        """Ignore temporary files, caches, and hidden files."""
        basename = os.path.basename(path)
        ignored_patterns = [
            '.DS_Store',
            '__pycache__',
            '.git',
            '*.pyc',
            '*.swp',
            '*.tmp',
            '.resolved.',  # Archive backup files
        ]
        for pattern in ignored_patterns:
            if pattern.startswith('*'):
                if basename.endswith(pattern[1:]):
                    return True
            elif pattern in basename:
                return True
        return False
    
    def _debounce(self, path: str) -> bool:
        """Return True if we should process this event (not debounced)."""
        now = datetime.now()
        key = path
        if key in self._debounce_cache:
            last_time = self._debounce_cache[key]
            if (now - last_time).total_seconds() * 1000 < self._debounce_ms:
                return False
        self._debounce_cache[key] = now
        return True
    
    def _emit(self, event_type: str, event: FileSystemEvent):
        """Emit a file change event."""
        if self._should_ignore(event.src_path):
            return
        if not self._debounce(event.src_path):
            return
            
        change = FileChangeEvent(
            event_type=event_type,
            path=event.src_path,
            is_directory=event.is_directory
        )
        logger.debug(f"File change detected: {change.event_type} -> {change.path}")
        self.callback(change)
    
    def on_created(self, event):
        self._emit("created", event)
    
    def on_modified(self, event):
        self._emit("modified", event)
    
    def on_deleted(self, event):
        self._emit("deleted", event)
    
    def on_moved(self, event):
        self._emit("moved", event)


class FileMonitor:
    """
    Monitors the .brain folder for file changes.
    
    This enables "push" notifications to MCP clients when files change,
    solving the sync problem across Chats/IDEs/CLI.
    """
    
    def __init__(self, brain_path: str, on_change: Optional[Callable[[FileChangeEvent], None]] = None):
        self.brain_path = Path(brain_path)
        self.on_change = on_change or self._default_handler
        self._observer: Optional[Observer] = None
        self._running = False
        self._event_queue: List[FileChangeEvent] = []
        self._lock = threading.Lock()
        
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog library not installed. File monitoring disabled.")
    
    def _default_handler(self, event: FileChangeEvent):
        """Default handler just logs and queues events."""
        with self._lock:
            self._event_queue.append(event)
            # Keep queue bounded
            if len(self._event_queue) > 100:
                self._event_queue = self._event_queue[-50:]
    
    def start(self) -> bool:
        """Start watching the brain folder."""
        if not WATCHDOG_AVAILABLE:
            logger.error("Cannot start file monitor: watchdog not installed.")
            return False
            
        if self._running:
            logger.warning("File monitor already running.")
            return True
            
        if not self.brain_path.exists():
            logger.warning(f"Brain path does not exist: {self.brain_path}")
            return False
        
        try:
            handler = BrainEventHandler(self.on_change)
            self._observer = Observer()
            self._observer.schedule(handler, str(self.brain_path), recursive=True)
            self._observer.start()
            self._running = True
            logger.info(f"📡 File monitor started: {self.brain_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start file monitor: {e}")
            return False
    
    def stop(self):
        """Stop watching the brain folder."""
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._running = False
            logger.info("📡 File monitor stopped.")
    
    def get_pending_events(self) -> List[FileChangeEvent]:
        """Get and clear pending events."""
        with self._lock:
            events = self._event_queue.copy()
            self._event_queue.clear()
            return events
    
    @property
    def is_running(self) -> bool:
        return self._running


# Singleton instance for global access
_global_monitor: Optional[FileMonitor] = None


def get_file_monitor() -> Optional[FileMonitor]:
    """Get the global file monitor instance."""
    return _global_monitor


def init_file_monitor(brain_path: str, on_change: Optional[Callable] = None) -> FileMonitor:
    """Initialize and return the global file monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = FileMonitor(brain_path, on_change)
    return _global_monitor
