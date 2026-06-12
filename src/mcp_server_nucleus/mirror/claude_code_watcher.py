"""Claude Code session-JSONL filesystem watcher.

Watches ``~/.claude/projects/<project-slug>/*.jsonl`` for new lines and emits
``EngramEvent`` deltas. JSONL files are append-only, so the delta strategy is
simple: track the byte offset already consumed per session file.

Hard contracts:
- READ-ONLY on ``.claude/`` paths per memory rule
  ``feedback_never_prune_claude_paths.md``. Files are opened with ``mode='r'``
  only. No move/delete/symlink/truncate operations.
- Pseudonymity: paths derived from ``pathlib.Path.home()``.

Throttle + workspace rules mirror ``cursor_watcher.CursorEventHandler``.
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
from .parsers.claude_code import parse_session_file

_LOG = logging.getLogger(__name__)

DEFAULT_CLAUDE_CODE_SUBPATH = pathlib.Path(".claude/projects")
MAX_EVENTS_PER_SEC_PER_PROJECT = 10


def default_claude_code_root() -> pathlib.Path:
    """The default Claude Code projects root for the current user.

    Derived from ``Path.home()`` so the same code runs unchanged for any
    operator.
    """
    return pathlib.Path.home() / DEFAULT_CLAUDE_CODE_SUBPATH


class _ThrottleBucket:
    """1-second token bucket. Identical contract to cursor_watcher._ThrottleBucket
    but kept separate to avoid cross-module imports of private helpers."""

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


class ClaudeCodeEventHandler(FileSystemEventHandler):
    """Watchdog handler that emits new events appended to Claude Code JSONLs.

    Strategy: track ``(line_count_already_emitted)`` per session file. On
    modify, parse the file end-to-end (cheap enough for chat-pace; the parser
    is a generator and we slice) and yield only events past the cursor. This
    is more robust than byte-offset tracking because the parser already
    handles malformed lines.
    """

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_PROJECT,
    ) -> None:
        super().__init__()
        self._queue: "Queue[EngramEvent]" = event_queue
        self._cursors: Dict[str, int] = {}  # session_file -> count of events already emitted
        self._buckets: Dict[str, _ThrottleBucket] = {}  # project_slug -> bucket
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
        # READ-ONLY contract: we never call any write/delete method on `path`.
        # The parser opens it with mode='r'. Defensive: also reject if the
        # path appears to be a symlink pointing outside .claude/ (unlikely,
        # but explicit).
        try:
            if path.is_symlink():
                resolved = path.resolve()
                if ".claude" not in resolved.parts:
                    _LOG.warning(
                        "claude_code_watcher: skipping symlink outside .claude (%s)",
                        path,
                    )
                    return
        except OSError:
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

        # Throttle key: project-slug (= parent dir name)
        project_slug = path.parent.name or "default"
        with self._lock:
            bucket = self._buckets.setdefault(
                project_slug, _ThrottleBucket(self._throttle_cap)
            )

        emitted_count = already_emitted
        for e in new_events:
            if not bucket.allow():
                if bucket.warn_once():
                    _LOG.warning(
                        "claude_code_watcher: throttle exceeded for project=%s (cap=%d/s)",
                        project_slug,
                        self._throttle_cap,
                    )
                emitted_count += 1
                continue
            try:
                self._queue.put_nowait(e)
            except QueueFull:
                _LOG.warning("claude_code_watcher: queue full, dropping event")
                continue
            emitted_count += 1

        with self._lock:
            if emitted_count > already_emitted:
                self._cursors[key] = emitted_count


class ClaudeCodeWatcher:
    """Lifecycle wrapper around a watchdog Observer for Claude Code JSONLs.

    READ-ONLY: never modifies any file under ``~/.claude/``.
    """

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        root: Optional[pathlib.Path] = None,
        throttle_cap: int = MAX_EVENTS_PER_SEC_PER_PROJECT,
    ) -> None:
        if not _WATCHDOG_AVAILABLE:
            raise RuntimeError(
                "claude_code_watcher requires the 'watchdog' package; install nucleus-mcp extras"
            )
        self.root = root or default_claude_code_root()
        self.queue = event_queue
        self.handler = ClaudeCodeEventHandler(event_queue, throttle_cap=throttle_cap)
        self._observer = Observer()

    def start(self) -> None:
        if not self.root.exists():
            _LOG.warning(
                "claude_code_watcher: root does not exist (%s); skipping start",
                self.root,
            )
            return
        self._observer.schedule(self.handler, str(self.root), recursive=True)
        self._observer.start()
        _LOG.info("claude_code_watcher: watching %s (read-only)", self.root)

    def stop(self) -> None:
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5.0)
            _LOG.info("claude_code_watcher: stopped")

    def emit_for_path(self, path: pathlib.Path) -> None:
        """Test helper: synchronous parse + emit, equivalent to a watchdog event."""
        self.handler._handle_path(path)


__all__ = [
    "ClaudeCodeWatcher",
    "ClaudeCodeEventHandler",
    "default_claude_code_root",
    "MAX_EVENTS_PER_SEC_PER_PROJECT",
]
