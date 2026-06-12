"""Cowork (Claude Desktop ``local-agent-mode-sessions``) filesystem watcher.

Wraps the existing single-shot ``daemon.main()`` Cowork-mirror logic into the
same coordinator-friendly ``Watcher`` interface used by the Cursor + Claude
Code surfaces. This lets the multi-surface coordinator treat all three
surfaces uniformly.

The legacy ``daemon.main()`` entrypoint (which writes the LAST assistant turn
to ``session_mirror/cowork_last.md`` for the relay-inbox hook) is preserved
verbatim in ``daemon.py`` and is unaffected by this watcher.
"""

from __future__ import annotations

import logging
import pathlib
import threading
import time
from queue import Full as QueueFull
from queue import Queue
from typing import Dict, Optional

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover - watchdog is a declared dep
    _WATCHDOG_AVAILABLE = False
    FileSystemEvent = object  # type: ignore[assignment,misc]
    FileSystemEventHandler = object  # type: ignore[assignment,misc]
    Observer = None  # type: ignore[assignment]

from mcp_server_nucleus.paths import transcript_root

from .parsers import EngramEvent
from .parsers.cowork import parse_session_file

_LOG = logging.getLogger(__name__)

DEFAULT_COWORK_SUBPATH = pathlib.Path(
    "Library/Application Support/Claude/local-agent-mode-sessions"
)
MAX_EVENTS_PER_SEC_PER_SESSION = 10


def default_cowork_root() -> pathlib.Path:
    """The default Cowork transcript root for the current user.

    Honours ``NUCLEUS_TRANSCRIPT_ROOT`` (matching the legacy
    ``daemon._default_transcript_root``) so existing config keeps working.
    """
    env = transcript_root(strict=False)
    if env is not None:
        return env
    return pathlib.Path.home() / DEFAULT_COWORK_SUBPATH


class _ThrottleBucket:
    __slots__ = ("_count", "_window_start", "_cap", "_warned")

    def __init__(self, cap: int) -> None:
        self._count = 0
        self._window_start = time.monotonic()
        self._cap = cap
        self._warned = False

    def allow(self) -> bool:
        now = time.monotonic()
        if now - self._window_start >= 1.0:
            self._count = 0
            self._window_start = now
            self._warned = False
        if self._count < self._cap:
            self._count += 1
            return True
        return False

    def warn_once(self) -> bool:
        if not self._warned:
            self._warned = True
            return True
        return False


class CoworkEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_SESSION,
    ) -> None:
        super().__init__()
        self._queue: "Queue[EngramEvent]" = event_queue
        self._cursors: Dict[str, int] = {}
        self._buckets: Dict[str, _ThrottleBucket] = {}
        self._throttle_cap = throttle_cap
        self._lock = threading.Lock()

    def on_modified(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        self._handle(event)

    def on_created(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        self._handle(event)

    def on_moved(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        dest = getattr(event, "dest_path", None)
        if dest:
            self._handle_path(pathlib.Path(dest))

    def _handle(self, event: FileSystemEvent) -> None:
        if getattr(event, "is_directory", False):
            return
        src = getattr(event, "src_path", None)
        if not src:
            return
        self._handle_path(pathlib.Path(src))

    def _handle_path(self, path: pathlib.Path) -> None:
        if path.suffix.lower() != ".jsonl":
            return
        self._emit_delta(path)

    def _emit_delta(self, path: pathlib.Path) -> None:
        events = list(parse_session_file(path))
        if not events:
            return
        key = str(path)
        with self._lock:
            already_emitted = self._cursors.get(key, 0)
        new_events = events[already_emitted:]
        if not new_events:
            return

        session_key = new_events[0].session_id or key
        with self._lock:
            bucket = self._buckets.setdefault(
                session_key, _ThrottleBucket(self._throttle_cap)
            )

        emitted_count = already_emitted
        for e in new_events:
            if not bucket.allow():
                if bucket.warn_once():
                    _LOG.warning(
                        "cowork_watcher: throttle exceeded for session=%s (cap=%d/s)",
                        session_key,
                        self._throttle_cap,
                    )
                emitted_count += 1
                continue
            try:
                self._queue.put_nowait(e)
            except QueueFull:
                _LOG.warning("cowork_watcher: queue full, dropping event")
                continue
            emitted_count += 1

        with self._lock:
            if emitted_count > already_emitted:
                self._cursors[key] = emitted_count


class CoworkWatcher:
    """Lifecycle wrapper around a watchdog Observer for the Cowork surface."""

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        root: Optional[pathlib.Path] = None,
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_SESSION,
    ) -> None:
        if not _WATCHDOG_AVAILABLE:
            raise RuntimeError(
                "cowork_watcher requires the 'watchdog' package; install nucleus-mcp extras"
            )
        self.root = root or default_cowork_root()
        self.queue = event_queue
        self.handler = CoworkEventHandler(event_queue, throttle_cap=throttle_cap)
        self._observer = Observer()

    def start(self) -> None:
        if not self.root.exists():
            _LOG.warning(
                "cowork_watcher: root does not exist (%s); skipping start", self.root
            )
            return
        self._observer.schedule(self.handler, str(self.root), recursive=True)
        self._observer.start()
        _LOG.info("cowork_watcher: watching %s", self.root)

    def stop(self) -> None:
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5.0)
            _LOG.info("cowork_watcher: stopped")

    def emit_for_path(self, path: pathlib.Path) -> None:
        """Test helper: synchronous parse + emit."""
        self.handler._handle_path(path)


__all__ = [
    "CoworkWatcher",
    "CoworkEventHandler",
    "default_cowork_root",
    "MAX_EVENTS_PER_SEC_PER_SESSION",
]
