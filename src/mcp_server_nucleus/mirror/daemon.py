"""Cowork → CC session-mirror daemon + Multi-surface engram-capture coordinator.

Two related personalities live in this module:

1. **Legacy single-shot Cowork mirror** (``main()``): Finds the peer agent's
   most-recent conversation JSONL on the host filesystem, extracts the last
   assistant turn, and writes it to ``<brain>/session_mirror/cowork_last.md``
   when content changes. CC's ``relay_inbox_hook`` surfaces the mirror as
   additionalContext on SessionStart + UserPromptSubmit. Unchanged from
   1.12.x — safe to call on any cadence; idempotent via mtime + content hash.

2. **Multi-surface coordinator** (``run_coordinator()``): Long-running
   ``watchdog`` driver that watches Cursor + Claude Code + Cowork session
   files concurrently and drains structured ``EngramEvent`` instances into a
   pluggable sink (default: an in-memory list; production override: write to
   the local engram SQLite via ``brain_rag``/``engram_ops``).

Both share the per-surface parsers in ``mirror/parsers/`` so the legacy
behavior and the new coordinator agree on schema handling.

Configuration for the coordinator lives in ``~/.config/eidetic/watchers.json``
(JSON object: ``{"cursor": true, "claude_code": true, "cowork": true,
"throttle_cap_per_sec": 10}``); fully optional, sensible defaults bake in.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import signal
import sys
import threading
from queue import Empty as QueueEmpty
from queue import Queue
from typing import Callable, Iterator, List, Optional

from mcp_server_nucleus.paths import brain_path, transcript_root

from .parsers import EngramEvent

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy single-shot mirror (preserved verbatim in behavior + signature)
# ---------------------------------------------------------------------------

JSONL_PATTERN = "*/*/local_*/.claude/projects/*/*.jsonl"
DEFAULT_COWORK_SUBPATH = "Library/Application Support/Claude/local-agent-mode-sessions"


TranscriptSource = Callable[[pathlib.Path], Iterator[dict]]


def cowork_jsonl_source(jsonl: pathlib.Path) -> Iterator[dict]:
    """Default adapter: read Cowork's JSONL conversation shape line-by-line."""
    with jsonl.open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _default_transcript_root() -> pathlib.Path:
    env = transcript_root(strict=False)
    if env is not None:
        return env
    return pathlib.Path.home() / DEFAULT_COWORK_SUBPATH


def _session_mirror_dir() -> pathlib.Path:
    return brain_path(strict=False) / "session_mirror"


def find_latest_jsonl(root: pathlib.Path) -> Optional[pathlib.Path]:
    if not root.exists():
        return None
    candidates = list(root.glob(JSONL_PATTERN))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def extract_last_assistant_text(
    jsonl: pathlib.Path,
    source: TranscriptSource = cowork_jsonl_source,
) -> Optional[str]:
    last: Optional[str] = None
    for d in source(jsonl):
        if not isinstance(d, dict) or d.get("type") != "assistant":
            continue
        m = d.get("message", {})
        content = m.get("content") if isinstance(m, dict) else None
        if isinstance(content, list):
            text_blocks = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            text = "\n".join(t for t in text_blocks if t).strip()
        elif isinstance(content, str):
            text = content.strip()
        else:
            text = ""
        if text:
            last = text
    return last


def load_state(state_path: pathlib.Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state_path: pathlib.Path, s: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(s))


def main(
    transcript_root_path: Optional[pathlib.Path] = None,
    mirror_path: Optional[pathlib.Path] = None,
    state_path: Optional[pathlib.Path] = None,
    source: TranscriptSource = cowork_jsonl_source,
) -> int:
    """Single-shot Cowork mirror — unchanged from 1.12.x."""
    root = transcript_root_path or _default_transcript_root()
    mirror_dir = _session_mirror_dir()
    mirror = mirror_path or mirror_dir / "cowork_last.md"
    state = state_path or mirror_dir / ".daemon_state.json"

    jsonl = find_latest_jsonl(root)
    if jsonl is None:
        return 0
    source_mtime = jsonl.stat().st_mtime
    current = load_state(state)
    if (
        current.get("source_path") == str(jsonl)
        and current.get("source_mtime") == source_mtime
    ):
        return 0
    text = extract_last_assistant_text(jsonl, source=source)
    new_state = {"source_path": str(jsonl), "source_mtime": source_mtime}
    if not text:
        new_state["content_hash"] = current.get("content_hash", "")
        save_state(state, new_state)
        return 0
    h = hashlib.sha256(text.encode()).hexdigest()
    new_state["content_hash"] = h
    if current.get("content_hash") == h:
        save_state(state, new_state)
        return 0
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(text)
    save_state(state, new_state)
    return 0


# ---------------------------------------------------------------------------
# Multi-surface coordinator
# ---------------------------------------------------------------------------

# Default config — overridden by ~/.config/eidetic/watchers.json or env vars.
DEFAULT_WATCHER_CONFIG = {
    "cursor": True,
    "claude_code": True,
    "cowork": True,
    "throttle_cap_per_sec": 10,
    "queue_high_watermark": 10_000,
}


def _config_path() -> pathlib.Path:
    env = os.environ.get("EIDETIC_WATCHERS_CONFIG")
    if env:
        return pathlib.Path(env).expanduser()
    return pathlib.Path.home() / ".config" / "eidetic" / "watchers.json"


def load_watcher_config(path: Optional[pathlib.Path] = None) -> dict:
    """Load coordinator config, falling back to defaults for missing keys.

    Never raises on missing/malformed file — bad config = use defaults +
    log a warning.
    """
    cfg = dict(DEFAULT_WATCHER_CONFIG)
    p = path or _config_path()
    if not p.exists():
        return cfg
    try:
        loaded = json.loads(p.read_text())
        if isinstance(loaded, dict):
            cfg.update(loaded)
    except (json.JSONDecodeError, OSError) as exc:
        _LOG.warning("coordinator: failed to load %s (%s); using defaults", p, exc)
    return cfg


# Engram sink protocol --------------------------------------------------------

EngramSink = Callable[[EngramEvent], None]


def in_memory_sink() -> tuple:
    """Default sink: append to a list. Used in tests + dry-run modes.

    Returns ``(sink_fn, captured_list)`` so tests can inspect the captured
    events after exercising the coordinator.
    """
    captured: List[EngramEvent] = []

    def _sink(event: EngramEvent) -> None:
        captured.append(event)

    return _sink, captured


class Coordinator:
    """Drains EngramEvents from the shared queue into a sink.

    Lifecycle:
        coord = Coordinator(queue, sink)
        coord.start()  # spawns drain thread
        ...
        coord.stop()   # graceful: drains pending events, joins thread

    Backpressure: emits a warning every time the queue depth crosses the
    ``high_watermark`` from below. The watchers themselves drop events when
    the queue is full (they call ``put_nowait``); the coordinator just
    surfaces visibility.
    """

    def __init__(
        self,
        event_queue: "Queue[EngramEvent]",
        sink: EngramSink,
        high_watermark: int = 10_000,
        poll_interval_s: float = 0.1,
    ) -> None:
        self.queue = event_queue
        self.sink = sink
        self.high_watermark = high_watermark
        self.poll_interval_s = poll_interval_s
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._above_watermark = False
        self._processed = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._drain_loop,
            name="engram-coordinator",
            daemon=True,
        )
        self._thread.start()
        _LOG.info("coordinator: drain thread started")

    def stop(self, drain_timeout_s: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=drain_timeout_s)
            self._thread = None
        # Final drain pass for anything that landed between stop signal +
        # thread exit.
        while True:
            if not self._drain_once(blocking=False):
                break
        _LOG.info(
            "coordinator: stopped (processed=%d, queue_depth_remaining=%d)",
            self._processed,
            self.queue.qsize(),
        )

    def processed_count(self) -> int:
        return self._processed

    # -- Internals -------------------------------------------------------

    def _drain_loop(self) -> None:
        while not self._stop.is_set():
            self._drain_once(blocking=True)

    def _drain_once(self, *, blocking: bool) -> bool:
        try:
            event = self.queue.get(block=blocking, timeout=self.poll_interval_s)
        except QueueEmpty:
            return False
        try:
            self.sink(event)
            self._processed += 1
        except Exception as exc:  # noqa: BLE001 — sink errors must not kill us
            _LOG.error("coordinator: sink failed for event from %s (%s)", event.surface, exc)
        finally:
            self.queue.task_done()
        self._watermark_check()
        return True

    def _watermark_check(self) -> None:
        depth = self.queue.qsize()
        if depth >= self.high_watermark:
            if not self._above_watermark:
                _LOG.warning(
                    "coordinator: queue depth %d >= high watermark %d — backpressure",
                    depth,
                    self.high_watermark,
                )
                self._above_watermark = True
        elif depth < self.high_watermark // 2:
            self._above_watermark = False


def build_watchers(
    event_queue: "Queue[EngramEvent]",
    config: dict,
) -> list:
    """Construct enabled watchers per config. Returns list of watcher objects
    with ``.start()`` + ``.stop()`` methods. Import is lazy so a missing
    ``watchdog`` install only breaks the surfaces that need it."""
    cap = int(config.get("throttle_cap_per_sec", 10))
    watchers: list = []
    if config.get("cursor", True):
        from .cursor_watcher import CursorWatcher
        watchers.append(CursorWatcher(event_queue, throttle_cap=cap))
    if config.get("claude_code", True):
        from .claude_code_watcher import ClaudeCodeWatcher
        watchers.append(ClaudeCodeWatcher(event_queue, throttle_cap=cap))
    if config.get("cowork", True):
        from .cowork_watcher import CoworkWatcher
        watchers.append(CoworkWatcher(event_queue, throttle_cap=cap))
    return watchers


def run_coordinator(
    sink: Optional[EngramSink] = None,
    config: Optional[dict] = None,
    queue_maxsize: int = 0,  # 0 = unbounded; production sets ~50_000
) -> int:
    """Long-running daemon entrypoint for the multi-surface coordinator.

    Blocks until SIGINT/SIGTERM. Returns 0 on clean shutdown.

    Args:
        sink: per-event handler. Defaults to in-memory list (dry-run); for
            production pass a sink that writes to the engram SQLite.
        config: watcher config dict (else loaded from
            ``~/.config/eidetic/watchers.json``).
        queue_maxsize: max queue size; 0 = unbounded. Watchers use
            ``put_nowait`` and drop on Full.
    """
    cfg = config or load_watcher_config()
    event_queue: "Queue[EngramEvent]" = Queue(maxsize=queue_maxsize)
    actual_sink = sink or in_memory_sink()[0]

    coord = Coordinator(
        event_queue,
        actual_sink,
        high_watermark=int(cfg.get("queue_high_watermark", 10_000)),
    )

    try:
        watchers = build_watchers(event_queue, cfg)
    except RuntimeError as exc:
        _LOG.error("coordinator: cannot build watchers (%s)", exc)
        return 1

    shutdown = threading.Event()

    def _handler(signum, _frame):  # noqa: ANN001 - signal protocol
        _LOG.info("coordinator: received signal %s; initiating shutdown", signum)
        shutdown.set()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    coord.start()
    for w in watchers:
        try:
            w.start()
        except Exception as exc:  # noqa: BLE001
            _LOG.error("coordinator: failed to start %s (%s)", type(w).__name__, exc)

    _LOG.info("coordinator: running (%d watchers); awaiting signal", len(watchers))
    try:
        while not shutdown.is_set():
            shutdown.wait(timeout=1.0)
    finally:
        for w in watchers:
            try:
                w.stop()
            except Exception as exc:  # noqa: BLE001
                _LOG.error("coordinator: error stopping %s (%s)", type(w).__name__, exc)
        coord.stop()
        _LOG.info("coordinator: shutdown complete")
    return 0


# ---------------------------------------------------------------------------
# CLI entry: legacy single-shot is default; ``--coordinator`` runs long-form.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--coordinator" in sys.argv:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )
        sys.exit(run_coordinator())
    sys.exit(main())
