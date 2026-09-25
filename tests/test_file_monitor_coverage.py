"""Comprehensive coverage tests for runtime/file_monitor.py.

Tests FileChangeEvent, BrainEventHandler (ignore/debounce/emit/on_*),
FileMonitor lifecycle, and the global singleton helpers. Watchdog is
available in this env, so the real Observer path is exercised against
a tmp_path brain directory. No real network.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import file_monitor as fm
from mcp_server_nucleus.runtime.file_monitor import (
    BrainEventHandler,
    FileChangeEvent,
    FileMonitor,
    get_file_monitor,
    init_file_monitor,
)


# ---------------------------------------------------------------------------
# FileChangeEvent
# ---------------------------------------------------------------------------
class TestFileChangeEvent:
    def test_defaults(self):
        ev = FileChangeEvent(event_type="created", path="/x/y")
        assert ev.event_type == "created"
        assert ev.path == "/x/y"
        assert ev.is_directory is False
        assert isinstance(ev.timestamp, datetime)

    def test_to_dict(self):
        ts = datetime(2024, 1, 1, 12, 0, 0)
        ev = FileChangeEvent(event_type="modified", path="/a/b", timestamp=ts, is_directory=True)
        d = ev.to_dict()
        assert d == {
            "event_type": "modified",
            "path": "/a/b",
            "timestamp": "2024-01-01T12:00:00",
            "is_directory": True,
        }

    def test_to_dict_iso_format(self):
        ev = FileChangeEvent(event_type="deleted", path="/p")
        d = ev.to_dict()
        # timestamp is ISO format string
        "T" in d["timestamp"] or "-" in d["timestamp"]


# ---------------------------------------------------------------------------
# BrainEventHandler
# ---------------------------------------------------------------------------
def _make_event(src_path: str, is_directory: bool = False):
    """Create a minimal fake watchdog event."""
    ev = MagicMock()
    ev.src_path = src_path
    ev.is_directory = is_directory
    return ev


class TestShouldIgnore:
    def test_ignores_ds_store(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/.DS_Store") is True

    def test_ignores_pycache(self):
        h = BrainEventHandler(lambda e: None)
        # basename must contain the pattern
        assert h._should_ignore("/p/some__pycache__file") is True

    def test_ignores_git(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/.git_backup") is True

    def test_ignores_pyc(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/foo.pyc") is True

    def test_ignores_swp(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/.foo.swp") is True

    def test_ignores_tmp(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/foo.tmp") is True

    def test_ignores_resolved(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/foo.resolved.bak") is True

    def test_allows_normal_file(self):
        h = BrainEventHandler(lambda e: None)
        assert h._should_ignore("/p/engrams/abc.md") is False


class TestDebounce:
    def test_first_event_processes(self):
        h = BrainEventHandler(lambda e: None)
        assert h._debounce("/x") is True

    def test_rapid_duplicate_debounced(self):
        h = BrainEventHandler(lambda e: None)
        assert h._debounce("/x") is True
        assert h._debounce("/x") is False  # within 100ms

    def test_after_window_processes(self):
        h = BrainEventHandler(lambda e: None)
        h._debounce("/x")
        # Force the cached time far into the past
        h._debounce_cache["/x"] = datetime.now() - timedelta(seconds=1)
        assert h._debounce("/x") is True


class TestEmit:
    def test_emit_ignored_no_callback(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h._emit("created", _make_event("/p/.DS_Store"))
        assert called == []

    def test_emit_debounced_no_callback(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h._emit("created", _make_event("/p/a.txt"))
        h._emit("created", _make_event("/p/a.txt"))  # debounced
        assert len(called) == 1

    def test_emit_calls_callback_with_change(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h._emit("modified", _make_event("/p/foo.md", is_directory=False))
        assert len(called) == 1
        change = called[0]
        assert change.event_type == "modified"
        assert change.path == "/p/foo.md"
        assert change.is_directory is False

    def test_emit_directory_flag_propagates(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h._emit("created", _make_event("/p/dir", is_directory=True))
        assert called[0].is_directory is True


class TestOnHandlers:
    def test_on_created(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h.on_created(_make_event("/p/new.txt"))
        assert called[0].event_type == "created"

    def test_on_modified(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h.on_modified(_make_event("/p/new.txt"))
        assert called[0].event_type == "modified"

    def test_on_deleted(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h.on_deleted(_make_event("/p/new.txt"))
        assert called[0].event_type == "deleted"

    def test_on_moved(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h.on_moved(_make_event("/p/new.txt"))
        assert called[0].event_type == "moved"

    def test_on_handlers_ignore_temp(self):
        called = []
        h = BrainEventHandler(lambda e: called.append(e))
        h.on_created(_make_event("/p/.DS_Store"))
        assert called == []


# ---------------------------------------------------------------------------
# FileMonitor
# ---------------------------------------------------------------------------
class TestFileMonitor:
    def test_init_default_handler(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        assert m.brain_path == tmp_path
        assert m.on_change == m._default_handler
        assert m.is_running is False
        assert m._event_queue == []

    def test_init_custom_handler(self, tmp_path):
        cb = lambda e: None
        m = FileMonitor(str(tmp_path), on_change=cb)
        assert m.on_change is cb

    def test_default_handler_queues_and_trims(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        # Add 101 events to trigger trimming
        for i in range(101):
            ev = FileChangeEvent(event_type="created", path=f"/p/{i}")
            m._default_handler(ev)
        assert len(m._event_queue) == 50  # trimmed to last 50

    def test_default_handler_under_limit_no_trim(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        for i in range(50):
            ev = FileChangeEvent(event_type="created", path=f"/p/{i}")
            m._default_handler(ev)
        assert len(m._event_queue) == 50

    def test_get_pending_events_clears(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        ev = FileChangeEvent(event_type="created", path="/p/a")
        m._default_handler(ev)
        pending = m.get_pending_events()
        assert len(pending) == 1
        assert m.get_pending_events() == []

    def test_start_already_running(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        m._running = True
        assert m.start() is True

    def test_start_missing_path(self, tmp_path):
        m = FileMonitor(str(tmp_path / "nope"))
        assert m.start() is False

    def test_start_and_stop_lifecycle(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        assert m.start() is True
        assert m.is_running is True
        m.stop()
        assert m.is_running is False

    def test_start_exception_returns_false(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        with patch.object(fm, "Observer", side_effect=RuntimeError("boom")):
            assert m.start() is False
        assert m.is_running is False

    def test_stop_without_running_is_noop(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        m.stop()  # should not raise
        assert m.is_running is False

    def test_stop_with_observer(self, tmp_path):
        m = FileMonitor(str(tmp_path))
        m._observer = MagicMock()
        m._running = True
        m.stop()
        m._observer.stop.assert_called_once()
        m._observer.join.assert_called_once_with(timeout=2)
        assert m.is_running is False

    def test_start_when_watchdog_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fm, "WATCHDOG_AVAILABLE", False)
        m = FileMonitor(str(tmp_path))
        assert m.start() is False


# ---------------------------------------------------------------------------
# Global singleton helpers
# ---------------------------------------------------------------------------
class TestGlobalMonitor:
    def test_get_file_monitor_default_none(self, monkeypatch):
        monkeypatch.setattr(fm, "_global_monitor", None)
        assert get_file_monitor() is None

    def test_init_file_monitor_creates_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fm, "_global_monitor", None)
        m = init_file_monitor(str(tmp_path))
        assert isinstance(m, FileMonitor)
        assert get_file_monitor() is m

    def test_init_file_monitor_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fm, "_global_monitor", None)
        m1 = init_file_monitor(str(tmp_path))
        m2 = init_file_monitor(str(tmp_path / "other"))
        assert m1 is m2

    def test_init_file_monitor_with_custom_handler(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fm, "_global_monitor", None)
        cb = lambda e: None
        m = init_file_monitor(str(tmp_path), on_change=cb)
        assert m.on_change is cb
