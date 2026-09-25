"""Coverage tests for mcp_server_nucleus.hypervisor.watchdog."""
import os
import time
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.hypervisor import watchdog as wd_mod
from mcp_server_nucleus.hypervisor.watchdog import (
    Watchdog,
    SecurityEventHandler,
    HAS_WATCHDOG,
)


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_watchdog_init(workspace):
    wd = Watchdog(str(workspace))
    assert wd.workspace_root == workspace
    assert wd.protected_paths == []
    assert wd.shadow_cache == {}
    assert wd.max_cache_size == 500


def test_watchdog_init_custom_cache_size(workspace):
    wd = Watchdog(str(workspace), max_cache_size=10)
    assert wd.max_cache_size == 10


def test_cache_file_new(workspace):
    wd = Watchdog(str(workspace))
    wd._cache_file("/tmp/test", b"data")
    assert wd.shadow_cache["/tmp/test"] == b"data"


def test_cache_file_existing_moves_to_end(workspace):
    wd = Watchdog(str(workspace))
    wd._cache_file("/tmp/a", b"a")
    wd._cache_file("/tmp/b", b"b")
    wd._cache_file("/tmp/a", b"a2")
    # /tmp/a should be moved to end
    keys = list(wd.shadow_cache.keys())
    assert keys[-1] == "/tmp/a"


def test_cache_file_lru_eviction(workspace):
    wd = Watchdog(str(workspace), max_cache_size=2)
    wd._cache_file("/tmp/a", b"a")
    wd._cache_file("/tmp/b", b"b")
    wd._cache_file("/tmp/c", b"c")
    # /tmp/a should be evicted (oldest)
    assert "/tmp/a" not in wd.shadow_cache
    assert "/tmp/b" in wd.shadow_cache
    assert "/tmp/c" in wd.shadow_cache


def test_protect_new_path(workspace):
    target = workspace / "file.txt"
    target.write_text("content")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    abs_path = str(target.resolve())
    assert abs_path in wd.protected_paths
    assert abs_path in wd.shadow_cache
    assert wd.shadow_cache[abs_path] == b"content"


def test_protect_duplicate_path(workspace):
    target = workspace / "file.txt"
    target.write_text("content")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    wd.protect(str(target))
    # Should not add duplicate
    assert wd.protected_paths.count(str(target.resolve())) == 1


def test_protect_nonexistent_path(workspace):
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(workspace / "nonexistent.txt"))
    abs_path = str((workspace / "nonexistent.txt").resolve())
    assert abs_path in wd.protected_paths
    # Not in shadow_cache since file doesn't exist
    assert abs_path not in wd.shadow_cache


def test_protect_directory_skipped_cache(workspace):
    """Directories are not cached."""
    d = workspace / "subdir"
    d.mkdir()
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(d))
    abs_path = str(d.resolve())
    assert abs_path in wd.protected_paths
    assert abs_path not in wd.shadow_cache


def test_protect_cache_exception_swallowed(workspace):
    """Exception during file caching is swallowed."""
    target = workspace / "file.txt"
    target.write_text("content")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    with mock.patch("builtins.open", side_effect=OSError("permission")):
        # Should not raise
        wd.protect(str(target))


def test_security_event_handler_on_modified_directory(workspace):
    """Directory modifications are ignored."""
    wd = Watchdog(str(workspace))
    handler = SecurityEventHandler(wd, mock.MagicMock())
    event = mock.MagicMock()
    event.is_directory = True
    handler.on_modified(event)  # Should not raise


def test_security_event_handler_on_modified_unprotected(workspace):
    """Modifications to unprotected files are ignored."""
    wd = Watchdog(str(workspace))
    handler = SecurityEventHandler(wd, mock.MagicMock())
    event = mock.MagicMock()
    event.is_directory = False
    event.src_path = str(workspace / "unprotected.txt")
    handler.on_modified(event)  # Should not raise


def test_security_event_handler_on_modified_protected_false_positive(workspace):
    """Modification with identical content is a false positive (ignored)."""
    target = workspace / "file.txt"
    target.write_text("content")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    abs_path = str(target.resolve())
    handler = SecurityEventHandler(wd, mock.MagicMock())
    event = mock.MagicMock()
    event.is_directory = False
    event.src_path = str(target)
    handler.on_modified(event)  # Content matches shadow cache, should return early


def test_security_event_handler_on_modified_breach(workspace):
    """Modification with different content triggers revert."""
    target = workspace / "file.txt"
    target.write_text("original")
    wd = Watchdog(str(workspace))
    # Mock locker so protect() doesn't actually lock the file
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    # Now modify the file
    target.write_text("modified")
    abs_path = str(target.resolve())

    fake_locker = mock.MagicMock()
    handler = SecurityEventHandler(wd, fake_locker)
    event = mock.MagicMock()
    event.is_directory = False
    event.src_path = str(target)
    handler.on_modified(event)
    # Should have called revert -> unlock, write, lock
    fake_locker.unlock.assert_called_once()
    fake_locker.lock.assert_called_once_with(abs_path)
    # File should be reverted to original
    assert target.read_text() == "original"


def test_security_event_handler_revert_ddos_circuit_breaker(workspace):
    """DDoS circuit breaker trips after 10 rapid reverts."""
    target = workspace / "file.txt"
    target.write_text("original")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    abs_path = str(target.resolve())

    fake_locker = mock.MagicMock()
    handler = SecurityEventHandler(wd, fake_locker)

    # Simulate 10 rapid reverts to fill the deque
    for i in range(10):
        handler.revert_timestamps.append(time.time())

    # Now trigger one more — should trip circuit breaker
    # The handler should sleep and return without reverting
    with mock.patch("time.sleep") as fake_sleep:
        handler.revert(abs_path)
        fake_sleep.assert_called_once_with(1)


def test_security_event_handler_revert_no_shadow_cache(workspace):
    """Revert without shadow cache entry does nothing."""
    wd = Watchdog(str(workspace))
    fake_locker = mock.MagicMock()
    handler = SecurityEventHandler(wd, fake_locker)
    handler.revert("/nonexistent/in/cache")
    fake_locker.unlock.assert_not_called()


def test_security_event_handler_revert_exception(workspace):
    """A failed revert raises, and still re-locks on the way out."""
    target = workspace / "file.txt"
    target.write_text("original")
    wd = Watchdog(str(workspace))
    wd.locker = mock.MagicMock()
    wd.protect(str(target))
    abs_path = str(target.resolve())

    fake_locker = mock.MagicMock()
    fake_locker.unlock.side_effect = RuntimeError("unlock fail")
    handler = SecurityEventHandler(wd, fake_locker)
    # A FAILED security-breach revert must RAISE (watchdog.py:98, hardened in
    # 8d11e6e4). Swallowing it leaves a detected breach unreverted while the
    # caller sees success -- the failure mode this hypervisor exists to stop.
    with pytest.raises(RuntimeError, match="Security breach revert failed"):
        handler.revert(abs_path)
    # ...and the `finally` must still re-lock, so a raise does not leave the
    # file unprotected. This is the half that makes raising safe.
    fake_locker.lock.assert_called_once_with(abs_path)


def test_watchdog_start_no_watchdog_package(workspace, monkeypatch):
    """Watchdog.start() is a no-op when watchdog package not installed."""
    wd = Watchdog(str(workspace))
    wd.observer = None
    # Should not raise
    wd.start()


def test_watchdog_start_already_alive(workspace, monkeypatch):
    """Watchdog.start() is a no-op when observer is already alive."""
    wd = Watchdog(str(workspace))
    wd.observer = mock.MagicMock()
    wd.observer.is_alive.return_value = True
    wd.start()
    # Should not schedule again
    wd.observer.schedule.assert_not_called()


def test_watchdog_start_success(workspace, monkeypatch):
    """Watchdog.start() schedules handler and starts observer."""
    wd = Watchdog(str(workspace))
    wd.observer = mock.MagicMock()
    wd.observer.is_alive.return_value = False
    # Make sys.argv look like a non-quiet invocation
    monkeypatch.setattr("sys.argv", ["pytest", "-v"])
    wd.start()
    wd.observer.schedule.assert_called_once()
    wd.observer.start.assert_called_once()
    assert wd.observer.daemon is True


def test_watchdog_start_exception(workspace, monkeypatch):
    """Watchdog.start() handles RuntimeError gracefully."""
    wd = Watchdog(str(workspace))
    wd.observer = mock.MagicMock()
    wd.observer.is_alive.return_value = False
    wd.observer.start.side_effect = RuntimeError("already running")
    monkeypatch.setattr("sys.argv", ["pytest", "-v"])
    # Should not raise
    wd.start()


def test_watchdog_stop(workspace):
    """Watchdog.stop() stops and joins observer."""
    wd = Watchdog(str(workspace))
    wd.observer = mock.MagicMock()
    wd.stop()
    wd.observer.stop.assert_called_once()
    wd.observer.join.assert_called_once()


def test_watchdog_stop_no_observer(workspace):
    """Watchdog.stop() is a no-op when observer is None."""
    wd = Watchdog(str(workspace))
    wd.observer = None
    wd.stop()  # Should not raise
