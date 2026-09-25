"""Tests for the Cowork watcher + parser + coordinator wiring.

Covers:
- Cowork parser emits user + assistant turns (skips other envelopes)
- Cowork parser tolerates malformed lines + empty files
- Cowork watcher delta behavior (similar to Claude Code)
- Coordinator drains EngramEvents from queue into sink
- Coordinator graceful shutdown with SIGINT semantics
- Coordinator backpressure / watermark warning
- Legacy ``main()`` single-shot still works (regression coverage for the
  Cowork-mirror compat path)
- ``load_watcher_config()`` defaults + override behavior
- ``build_watchers()`` honors enabled-flags
"""

from __future__ import annotations

import json
import pathlib
import shutil
import time
from queue import Queue
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.mirror import daemon as daemon_mod
from mcp_server_nucleus.mirror.cowork_watcher import (
    CoworkEventHandler,
    CoworkWatcher,
    default_cowork_root,
)
from mcp_server_nucleus.mirror.daemon import (
    DEFAULT_WATCHER_CONFIG,
    Coordinator,
    build_watchers,
    in_memory_sink,
    load_watcher_config,
)
from mcp_server_nucleus.mirror.parsers import EngramEvent
from mcp_server_nucleus.mirror.parsers.cowork import parse_session_file

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "parsers" / "cowork"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parser_basic_session_emits_user_and_assistant():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    assert len(events) == 4
    roles = [e.role for e in events]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert all(e.surface == "cowork" for e in events)


def test_parser_extracts_string_and_list_content():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    assert events[0].content == "cowork user prompt"
    assert events[1].content == "cowork assistant reply"
    assert events[2].content == "second user message"
    assert events[3].content == "plain string reply"


def test_parser_session_id_from_filename():
    events = list(parse_session_file(FIXTURES / "basic_session.jsonl"))
    # session_id = path.stem
    assert all(e.session_id == "basic_session" for e in events)


def test_parser_skips_malformed_keeps_valid():
    events = list(parse_session_file(FIXTURES / "malformed.jsonl"))
    contents = [e.content for e in events]
    assert "valid" in contents
    assert "empty role still ok" in contents


def test_parser_empty_file_yields_nothing(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    assert list(parse_session_file(f)) == []


def test_parser_nonexistent_file_yields_nothing():
    assert list(parse_session_file(FIXTURES / "does-not-exist.jsonl")) == []


def test_default_cowork_root_uses_home(monkeypatch, tmp_path):
    """Pseudonymity contract; also respects NUCLEUS_TRANSCRIPT_ROOT."""
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("NUCLEUS_TRANSCRIPT_ROOT", raising=False)
    root = default_cowork_root()
    assert str(tmp_path) in str(root)
    import re
    user_segments = re.findall(r"/Users/([^/]+)", str(root))
    assert all(seg == tmp_path.parts[-1] for seg in user_segments), (
        f"Unexpected hardcoded user segment in {root!r}"
    )


def test_default_cowork_root_honors_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom_transcript"
    custom.mkdir()
    monkeypatch.setenv("NUCLEUS_TRANSCRIPT_ROOT", str(custom))
    root = default_cowork_root()
    assert root == custom


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------


def _make_fs_event(src_path: str, is_dir: bool = False):
    e = MagicMock()
    e.src_path = src_path
    e.is_directory = is_dir
    del e.dest_path
    return e


def test_cowork_handler_emits_for_jsonl(tmp_path):
    q: Queue = Queue()
    h = CoworkEventHandler(q)
    f = tmp_path / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    assert q.qsize() == 4


def test_cowork_handler_delta_no_duplicates(tmp_path):
    q: Queue = Queue()
    h = CoworkEventHandler(q)
    f = tmp_path / "session.jsonl"
    shutil.copy(FIXTURES / "basic_session.jsonl", f)
    h.on_modified(_make_fs_event(str(f)))
    first = q.qsize()
    h.on_modified(_make_fs_event(str(f)))
    assert q.qsize() == first


def test_cowork_handler_ignores_non_jsonl():
    q: Queue = Queue()
    h = CoworkEventHandler(q)
    h.on_modified(_make_fs_event("/tmp/foo.json"))
    assert q.empty()


def test_cowork_watcher_construct(tmp_path):
    q: Queue = Queue()
    w = CoworkWatcher(q, root=tmp_path)
    assert w.root == tmp_path


def test_cowork_watcher_skips_when_root_missing(tmp_path):
    q: Queue = Queue()
    w = CoworkWatcher(q, root=tmp_path / "nope")
    w.start()
    w.stop()


# ---------------------------------------------------------------------------
# Coordinator tests
# ---------------------------------------------------------------------------


def test_coordinator_drains_to_sink():
    q: Queue = Queue()
    sink, captured = in_memory_sink()
    coord = Coordinator(q, sink)
    coord.start()
    try:
        for i in range(5):
            q.put(EngramEvent(surface="test", role="user", content=f"msg{i}"))
        time.sleep(0.3)  # allow drain thread to run
    finally:
        coord.stop()
    assert len(captured) == 5
    assert coord.processed_count() == 5


def test_coordinator_graceful_shutdown_drains_pending():
    q: Queue = Queue()
    sink, captured = in_memory_sink()
    coord = Coordinator(q, sink, poll_interval_s=0.01)
    coord.start()
    for i in range(3):
        q.put(EngramEvent(surface="test", role="user", content=f"m{i}"))
    coord.stop()
    assert len(captured) == 3


def test_coordinator_sink_failure_does_not_kill_drain():
    """If sink raises, the coordinator keeps draining subsequent events."""
    q: Queue = Queue()
    call_count = {"n": 0}

    def bad_sink(event):
        call_count["n"] += 1
        if event.content == "boom":
            raise RuntimeError("sink down")

    coord = Coordinator(q, bad_sink)
    coord.start()
    try:
        q.put(EngramEvent(surface="test", role="user", content="ok1"))
        q.put(EngramEvent(surface="test", role="user", content="boom"))
        q.put(EngramEvent(surface="test", role="user", content="ok2"))
        time.sleep(0.3)
    finally:
        coord.stop()
    assert call_count["n"] == 3


def test_coordinator_watermark_warning(caplog):
    """Filling the queue past high_watermark emits a single warning."""
    import logging

    q: Queue = Queue()
    sink, captured = in_memory_sink()
    coord = Coordinator(q, sink, high_watermark=5)
    # Pre-fill queue above watermark
    for i in range(10):
        q.put(EngramEvent(surface="test", role="user", content=str(i)))

    with caplog.at_level(logging.WARNING, logger="mcp_server_nucleus.mirror.daemon"):
        coord.start()
        time.sleep(0.3)
        coord.stop()

    assert any("backpressure" in r.message for r in caplog.records)


def test_in_memory_sink_collects_events():
    sink, captured = in_memory_sink()
    e = EngramEvent(surface="s", role="user", content="hi")
    sink(e)
    sink(e)
    assert captured == [e, e]


def test_load_watcher_config_defaults_when_missing(tmp_path):
    cfg = load_watcher_config(tmp_path / "nonexistent.json")
    assert cfg == DEFAULT_WATCHER_CONFIG


def test_load_watcher_config_overrides(tmp_path):
    cfg_file = tmp_path / "watchers.json"
    cfg_file.write_text(json.dumps({"cursor": False, "throttle_cap_per_sec": 50}))
    cfg = load_watcher_config(cfg_file)
    assert cfg["cursor"] is False
    assert cfg["throttle_cap_per_sec"] == 50
    # Untouched keys remain
    assert cfg["claude_code"] is True
    assert cfg["cowork"] is True


def test_load_watcher_config_malformed_falls_back(tmp_path):
    cfg_file = tmp_path / "bad.json"
    cfg_file.write_text("{not json")
    cfg = load_watcher_config(cfg_file)
    assert cfg == DEFAULT_WATCHER_CONFIG


def test_build_watchers_respects_enabled_flags():
    q: Queue = Queue()
    cfg = {"cursor": True, "claude_code": False, "cowork": True, "throttle_cap_per_sec": 5}
    watchers = build_watchers(q, cfg)
    type_names = {type(w).__name__ for w in watchers}
    assert "CursorWatcher" in type_names
    assert "CoworkWatcher" in type_names
    assert "ClaudeCodeWatcher" not in type_names


def test_build_watchers_all_enabled_by_default():
    q: Queue = Queue()
    watchers = build_watchers(q, DEFAULT_WATCHER_CONFIG)
    type_names = {type(w).__name__ for w in watchers}
    assert type_names == {"CursorWatcher", "ClaudeCodeWatcher", "CoworkWatcher"}


# ---------------------------------------------------------------------------
# Legacy main() regression
# ---------------------------------------------------------------------------


def test_legacy_main_unchanged_with_empty_root(tmp_path, monkeypatch):
    """Legacy single-shot main() returns 0 when no JSONL is found — same as 1.12.x."""
    monkeypatch.setenv("NUCLEUS_BRAIN", str(tmp_path / "brain"))
    rc = daemon_mod.main(
        transcript_root_path=tmp_path / "no_such_root",
        mirror_path=tmp_path / "mirror.md",
        state_path=tmp_path / "state.json",
    )
    assert rc == 0


def test_legacy_main_writes_mirror_when_content_changes(tmp_path, monkeypatch):
    """Regression: legacy mirror behavior still works end-to-end."""
    monkeypatch.setenv("NUCLEUS_BRAIN", str(tmp_path / "brain"))
    # Build a synthetic Cowork-shape JSONL at the path the glob expects
    root = tmp_path / "transcripts"
    target = root / "a" / "b" / "local_x" / ".claude" / "projects" / "p"
    target.mkdir(parents=True)
    jsonl = target / "session.jsonl"
    jsonl.write_text(
        json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                      "content": [{"type": "text", "text": "hello"}]}})
        + "\n"
    )

    mirror_file = tmp_path / "mirror.md"
    state_file = tmp_path / "state.json"
    rc = daemon_mod.main(
        transcript_root_path=root,
        mirror_path=mirror_file,
        state_path=state_file,
    )
    assert rc == 0
    assert mirror_file.exists()
    assert mirror_file.read_text() == "hello"


# ---------------------------------------------------------------------------
# Integration smoke (no real Cursor / Claude Code needed)
# ---------------------------------------------------------------------------


def test_end_to_end_cowork_handler_to_coordinator_to_sink(tmp_path):
    """Wire a CoworkEventHandler -> Queue -> Coordinator -> sink."""
    q: Queue = Queue()
    sink, captured = in_memory_sink()
    coord = Coordinator(q, sink, poll_interval_s=0.01)
    coord.start()
    try:
        h = CoworkEventHandler(q)
        f = tmp_path / "session.jsonl"
        shutil.copy(FIXTURES / "basic_session.jsonl", f)
        h.on_modified(_make_fs_event(str(f)))
        time.sleep(0.3)
    finally:
        coord.stop()
    assert len(captured) == 4
    surfaces = {e.surface for e in captured}
    assert surfaces == {"cowork"}
