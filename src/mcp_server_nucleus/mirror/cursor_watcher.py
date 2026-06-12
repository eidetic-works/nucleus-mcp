"""Cursor chat-session filesystem watcher.

Watches ``~/Library/Application Support/Cursor/User/workspaceStorage/<hash>/``
for changes to ``chatSessions/*.json`` and emits ``EngramEvent`` deltas via
the shared queue.

Key responsibilities:
- Use ``watchdog`` to observe filesystem events recursively
- On modify/create: re-parse the affected session JSON, diff against a
  per-file cursor (last-seen request_index), emit only NEW events
- Throttle: max ``MAX_EVENTS_PER_SEC_PER_WORKSPACE`` (default 10) emissions
  per workspace; excess events are dropped with a warning log
- Workspace rotation: ``workspaceStorage`` adds new ``<hash>`` dirs as the
  user opens new projects; ``watchdog`` recursive watch picks them up
  automatically
- Read-only: never writes to Cursor's storage

Pseudonymity contract: paths derived from ``pathlib.Path.home()``, never
hardcoded ``/Users/<name>/``.
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

from .parsers import EngramEvent
from .parsers.cursor import parse_session_file

_LOG = logging.getLogger(__name__)

# Cursor on macOS — overridable via env / config in the coordinator.
DEFAULT_CURSOR_SUBPATH = pathlib.Path("Library/Application Support/Cursor/User/workspaceStorage")
MAX_EVENTS_PER_SEC_PER_WORKSPACE = 10


def default_cursor_root() -> pathlib.Path:
    """The default Cursor workspaceStorage root for the current user.

    Derived from ``Path.home()`` so the same code runs unchanged for any
    operator. Never hardcoded.
    """
    return pathlib.Path.home() / DEFAULT_CURSOR_SUBPATH


class _ThrottleBucket:
    """Per-workspace token-bucket throttle. Naive but adequate for chat-pace.

    Reset window is 1 second. Within the window, emissions are counted; once
    the cap is hit, further events are dropped (with a single log warning per
    overflow burst).
    """

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


class CursorEventHandler(FileSystemEventHandler):
    """Watchdog handler that parses Cursor chat-session files on change."""

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_WORKSPACE,
    ) -> None:
        super().__init__()
        self._queue: "Queue[EngramEvent]" = event_queue
        self._cursors: Dict[str, int] = {}  # session_file -> last request_index emitted
        self._buckets: Dict[str, _ThrottleBucket] = {}  # workspace -> bucket
        self._throttle_cap = throttle_cap
        self._lock = threading.Lock()

    # -- Watchdog callbacks ----------------------------------------------

    def on_modified(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        self._handle(event)

    def on_created(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        self._handle(event)

    def on_moved(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        # On rename, treat the destination as a new/modified file
        dest = getattr(event, "dest_path", None)
        if dest:
            self._handle_path(pathlib.Path(dest))

    # -- Core dispatch ---------------------------------------------------

    def _handle(self, event: FileSystemEvent) -> None:
        if getattr(event, "is_directory", False):
            return
        src = getattr(event, "src_path", None)
        if not src:
            return
        self._handle_path(pathlib.Path(src))

    def _handle_path(self, path: pathlib.Path) -> None:
        # We only care about chatSessions/*.json
        if path.suffix.lower() != ".json":
            return
        if path.parent.name != "chatSessions":
            return
        self._emit_delta(path)

    def _emit_delta(self, path: pathlib.Path) -> None:
        """Parse + emit events strictly newer than the last cursor for this
        session file. Updates the cursor + applies throttling."""
        events = list(parse_session_file(path))
        if not events:
            return

        # request_index lives in extra; if missing, treat all as new (parser
        # always includes it for normal Cursor sessions).
        def idx_of(e: EngramEvent) -> int:
            if e.extra and isinstance(e.extra.get("request_index"), int):
                return e.extra["request_index"]
            return -1

        key = str(path)
        with self._lock:
            cursor = self._cursors.get(key, -1)
        new_events = [e for e in events if idx_of(e) > cursor]
        if not new_events:
            return

        # Throttle per workspace (or per session_file if workspace unknown)
        workspace_key = (new_events[0].workspace or key)
        with self._lock:
            bucket = self._buckets.setdefault(
                workspace_key, _ThrottleBucket(self._throttle_cap)
            )

        emitted_max_idx = cursor
        for e in new_events:
            if not bucket.allow():
                if bucket.warn_once():
                    _LOG.warning(
                        "cursor_watcher: throttle exceeded for workspace=%s (cap=%d/s)",
                        workspace_key,
                        self._throttle_cap,
                    )
                # Drop excess events but DO advance the cursor so the next
                # modify-burst doesn't re-emit them.
                emitted_max_idx = max(emitted_max_idx, idx_of(e))
                continue
            try:
                self._queue.put_nowait(e)
            except QueueFull:
                _LOG.warning("cursor_watcher: queue full, dropping event")
                continue
            emitted_max_idx = max(emitted_max_idx, idx_of(e))

        with self._lock:
            if emitted_max_idx > cursor:
                self._cursors[key] = emitted_max_idx


class CursorWatcher:
    """Lifecycle wrapper around a watchdog Observer for the Cursor surface.

    Use ``start()`` to begin watching; ``stop()`` to shut down cleanly.
    Designed to be called from the coordinator (``daemon.py``).
    """

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        root: Optional[pathlib.Path] = None,
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_WORKSPACE,
    ) -> None:
        if not _WATCHDOG_AVAILABLE:
            raise RuntimeError(
                "cursor_watcher requires the 'watchdog' package; install nucleus-mcp extras"
            )
        self.root = root or default_cursor_root()
        self.queue = event_queue
        self.handler = CursorEventHandler(event_queue, throttle_cap=throttle_cap)
        self._observer = Observer()

    def start(self) -> None:
        """Begin watching the Cursor workspaceStorage root recursively.

        If the root doesn't exist yet (Cursor not installed), logs a warning
        and does nothing — the observer is not started, so ``stop()`` is a
        no-op. The coordinator can re-attempt later.
        """
        if not self.root.exists():
            _LOG.warning(
                "cursor_watcher: root does not exist (%s); skipping start", self.root
            )
            return
        self._observer.schedule(self.handler, str(self.root), recursive=True)
        self._observer.start()
        _LOG.info("cursor_watcher: watching %s", self.root)

    def stop(self) -> None:
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5.0)
            _LOG.info("cursor_watcher: stopped")

    # -- Convenience for tests --------------------------------------------

    def emit_for_path(self, path: pathlib.Path) -> None:
        """Test helper: parse + emit deltas for a path without a live observer.

        Equivalent to what the handler does on a real filesystem event, but
        callable synchronously from tests.
        """
        self.handler._handle_path(path)


__all__ = [
    "CursorWatcher",
    "CursorEventHandler",
    "default_cursor_root",
    "MAX_EVENTS_PER_SEC_PER_WORKSPACE",
]
