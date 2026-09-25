"""
Coverage tests for mcp_server_nucleus.runtime.watcher.AsyncFileWatcher.

Targets 90%+ line coverage. Uses tmp_path for filesystem, monkeypatch for
env vars, and mocks watchdog import paths. No real network/subprocess.
"""
import asyncio
import sys
import types
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import watcher as watcher_mod
from mcp_server_nucleus.runtime.watcher import AsyncFileWatcher


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a clean event loop is available before each test.

    Other test modules (e.g. test_mounter_coverage) create and close event
    loops manually, which can leave asyncio without a usable loop. This
    fixture sets a fresh loop before each watcher test runs.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    if not loop.is_closed():
        loop.close()


# ──────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ──────────────────────────────────────────────────────────────────────

def _make_fake_watchdog():
    """Build a fake `watchdog` package + `watchdog.observers` + events."""
    fake_pkg = types.ModuleType("watchdog")
    fake_observers = types.ModuleType("watchdog.observers")
    fake_events = types.ModuleType("watchdog.events")

    class FileSystemEventHandler:
        def __init__(self, *a, **kw):
            pass

    class FakeObserver:
        def __init__(self):
            self.started = False
            self.stopped = False
            self.scheduled = []
            self._start_raises = False

        def schedule(self, handler, path, recursive=False):
            self.scheduled.append((handler, path, recursive))

        def start(self):
            if self._start_raises:
                raise RuntimeError("boom")
            self.started = True

        def stop(self):
            self.stopped = True

        def join(self):
            pass

    fake_events.FileSystemEventHandler = FileSystemEventHandler
    fake_observers.Observer = FakeObserver
    fake_pkg.observers = fake_observers
    fake_pkg.events = fake_events
    return fake_pkg, FakeObserver


@pytest.fixture
def with_fake_watchdog(monkeypatch):
    fake_pkg, FakeObserver = _make_fake_watchdog()
    monkeypatch.setitem(sys.modules, "watchdog", fake_pkg)
    monkeypatch.setitem(sys.modules, "watchdog.observers", fake_pkg.observers)
    monkeypatch.setitem(sys.modules, "watchdog.events", fake_pkg.events)
    return FakeObserver


@pytest.fixture
def without_watchdog(monkeypatch):
    """Force the ImportError fallback path."""
    for name in ("watchdog", "watchdog.observers", "watchdog.events"):
        monkeypatch.setitem(sys.modules, name, None)
    return None


# ──────────────────────────────────────────────────────────────────────
# Construction
# ──────────────────────────────────────────────────────────────────────

def test_init_defaults_polling(without_watchdog):
    w = AsyncFileWatcher([Path("/tmp/x")], lambda p: None)
    assert w.use_watchdog is False
    assert w.running is False
    assert w.polling_interval == 2.0
    assert w._last_mtimes == {}
    assert not hasattr(w, "observer")


def test_init_custom_interval(without_watchdog):
    w = AsyncFileWatcher([Path("/tmp/x")], lambda p: None, polling_interval=0.5)
    assert w.polling_interval == 0.5


def test_init_with_watchdog(with_fake_watchdog):
    FakeObserver = with_fake_watchdog
    w = AsyncFileWatcher([Path("/tmp/x")], lambda p: None)
    assert w.use_watchdog is True
    assert isinstance(w.observer, FakeObserver)
    assert w._handler is not None


def test_create_handler_invokes_callback(with_fake_watchdog):
    w = AsyncFileWatcher([Path("/tmp/x")], lambda p: None)
    handler = w._create_handler()
    # Handler stores the callback
    assert handler.cb is w.callback


# ──────────────────────────────────────────────────────────────────────
# start() — watchdog path
# ──────────────────────────────────────────────────────────────────────

def test_start_watchdog_existing_file(tmp_path, with_fake_watchdog):
    target = tmp_path / "directives.md"
    target.write_text("hi")
    w = AsyncFileWatcher([target], lambda p: None)
    asyncio.run(w.start())
    assert w.running is True
    assert w.observer.started is True
    assert len(w.observer.scheduled) == 1
    asyncio.run(w.stop())


def test_start_watchdog_existing_dir(tmp_path, with_fake_watchdog):
    d = tmp_path / "subdir"
    d.mkdir()
    w = AsyncFileWatcher([d], lambda p: None)
    asyncio.run(w.start())
    # dir itself is scheduled
    assert any(path == str(d) for _, path, _ in w.observer.scheduled)
    asyncio.run(w.stop())


def test_start_watchdog_missing_path_skipped(tmp_path, with_fake_watchdog):
    missing = tmp_path / "nope.md"
    w = AsyncFileWatcher([missing], lambda p: None)
    asyncio.run(w.start())
    assert w.observer.scheduled == []
    asyncio.run(w.stop())


def test_start_watchdog_dedup_dirs(tmp_path, with_fake_watchdog):
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text("a")
    f2.write_text("b")
    w = AsyncFileWatcher([f1, f2], lambda p: None)
    asyncio.run(w.start())
    # Both files share parent — only one schedule call
    assert len(w.observer.scheduled) == 1
    asyncio.run(w.stop())


def test_start_watchdog_failure_falls_back_to_polling(tmp_path, with_fake_watchdog, monkeypatch):
    target = tmp_path / "f.md"
    target.write_text("x")
    w = AsyncFileWatcher([target], lambda p: None)
    w.observer._start_raises = True
    # Prevent poll loop task from lingering
    asyncio.run(w.start())
    assert w.use_watchdog is False
    # cleanup the created task
    asyncio.run(w.stop())


# ──────────────────────────────────────────────────────────────────────
# start() — polling path
# ──────────────────────────────────────────────────────────────────────

def test_start_polling_creates_task(tmp_path, without_watchdog):
    target = tmp_path / "t.md"
    target.write_text("x")
    w = AsyncFileWatcher([target], lambda p: None, polling_interval=0.01)

    async def run():
        await w.start()
        assert w.running is True
        # poll task created
        await asyncio.sleep(0.02)
        await w.stop()

    asyncio.run(run())


# ──────────────────────────────────────────────────────────────────────
# _poll_loop — sync + async callbacks, change detection, OSError
# ──────────────────────────────────────────────────────────────────────

def test_poll_loop_detects_change_sync_callback(tmp_path, without_watchdog):
    target = tmp_path / "t.md"
    target.write_text("init")
    seen = []

    def cb(p):
        seen.append(p)

    w = AsyncFileWatcher([target], cb, polling_interval=0.01)

    async def run():
        await w.start()
        # wait for initial mtime capture
        await asyncio.sleep(0.02)
        # modify file
        target.write_text("changed")
        # wait for detection
        await asyncio.sleep(0.05)
        await w.stop()

    asyncio.run(run())
    assert target in seen


def test_poll_loop_detects_change_async_callback(tmp_path, without_watchdog):
    target = tmp_path / "t.md"
    target.write_text("init")
    seen = []

    async def cb(p):
        seen.append(p)

    w = AsyncFileWatcher([target], cb, polling_interval=0.01)

    async def run():
        await w.start()
        await asyncio.sleep(0.02)
        target.write_text("changed")
        await asyncio.sleep(0.05)
        await w.stop()

    asyncio.run(run())
    assert target in seen


def test_poll_loop_handles_missing_path(tmp_path, without_watchdog):
    missing = tmp_path / "nope.md"
    w = AsyncFileWatcher([missing], lambda p: None, polling_interval=0.01)

    async def run():
        await w.start()
        await asyncio.sleep(0.02)
        await w.stop()

    # Should not raise
    asyncio.run(run())
    assert w.running is False


def test_poll_loop_oserror_swallowed(tmp_path, without_watchdog, monkeypatch):
    target = tmp_path / "t.md"
    target.write_text("x")
    w = AsyncFileWatcher([target], lambda p: None, polling_interval=0.01)

    # Force stat() to raise OSError after first capture
    real_stat = Path.stat

    def bad_stat(self, *a, **kw):
        if self == target:
            raise OSError("nope")
        return real_stat(self, *a, **kw)

    monkeypatch.setattr(Path, "stat", bad_stat)

    async def run():
        await w.start()
        await asyncio.sleep(0.03)
        await w.stop()

    asyncio.run(run())  # should not raise


def test_poll_loop_stops_when_running_false(tmp_path, without_watchdog):
    target = tmp_path / "t.md"
    target.write_text("x")
    w = AsyncFileWatcher([target], lambda p: None, polling_interval=0.01)

    async def run():
        await w.start()
        await asyncio.sleep(0.01)
        await w.stop()
        # extra await to confirm loop exited
        await asyncio.sleep(0.02)

    asyncio.run(run())
    assert w.running is False


# ──────────────────────────────────────────────────────────────────────
# stop()
# ──────────────────────────────────────────────────────────────────────

def test_stop_polling(without_watchdog):
    w = AsyncFileWatcher([Path("/tmp/x")], lambda p: None)
    asyncio.run(w.stop())
    assert w.running is False


def test_stop_watchdog_calls_observer(tmp_path, with_fake_watchdog):
    target = tmp_path / "f.md"
    target.write_text("x")
    w = AsyncFileWatcher([target], lambda p: None)
    asyncio.run(w.start())
    asyncio.run(w.stop())
    assert w.observer.stopped is True
    assert w.running is False
