"""Comprehensive tests for mcp_server_nucleus.daemon.safety.lock.

Covers BrainLock: __init__, _ensure_dir, _is_stale, acquire, release,
guard context manager, is_locked static method, and error paths.
"""
import errno
import os
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.daemon.safety import lock as lock_mod
from mcp_server_nucleus.daemon.safety.lock import BrainLock


class TestBrainLockInit:
    def test_init_creates_dir(self, tmp_path):
        lock_file = tmp_path / "locks" / "sub" / "state.lock"
        bl = BrainLock(str(lock_file))
        assert bl.lock_file == str(lock_file)
        assert bl.timeout == 5
        assert bl.fd is None
        assert os.path.isdir(str(lock_file.parent))

    def test_init_custom_timeout(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=10)
        assert bl.timeout == 10


class TestIsStale:
    def test_stale_missing_file(self, tmp_path):
        # Missing file = no lock to break. _is_stale returns False (not stale);
        # acquire() opens a fresh lock in that case. Reporting "stale" here
        # would be wrong — there is no owner to be dead.
        bl = BrainLock(str(tmp_path / "missing.lock"))
        assert bl._is_stale() is False

    def test_stale_corrupt_content(self, tmp_path):
        # Corrupt (non-numeric) content = INSUFFICIENT. The owner may still be
        # mid-write. Fail closed: do NOT steal a possibly-held lock.
        lock_file = tmp_path / "state.lock"
        lock_file.write_text("not-a-number")
        bl = BrainLock(str(lock_file))
        assert bl._is_stale() is None

    def test_stale_empty_file(self, tmp_path):
        # 0-byte lock file = a concurrent open('w') that has not written its
        # PID yet. INSUFFICIENT — never steal.
        lock_file = tmp_path / "state.lock"
        lock_file.write_bytes(b"")
        bl = BrainLock(str(lock_file))
        assert bl._is_stale() is None

    def test_stale_dead_pid(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        # Use a very high PID that almost certainly doesn't exist
        lock_file.write_text("99999999")
        bl = BrainLock(str(lock_file))
        assert bl._is_stale() is True

    def test_stale_alive_pid(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        lock_file.write_text(str(os.getpid()))
        bl = BrainLock(str(lock_file))
        assert bl._is_stale() is False

    def test_stale_permission_error(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        lock_file.write_text(str(os.getpid()))
        bl = BrainLock(str(lock_file))

        def fake_kill(pid, sig):
            raise PermissionError("no perms")

        with patch("os.kill", side_effect=fake_kill):
            assert bl._is_stale() is False


class TestAcquire:
    def test_acquire_success(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        assert bl.acquire() is True
        assert bl.fd is not None
        assert lock_file.read_text() == str(os.getpid())
        bl.release()

    def test_acquire_writes_pid(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        bl.acquire()
        content = lock_file.read_text()
        assert content == str(os.getpid())
        bl.release()

    def test_acquire_unexpected_ioerror_raises(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)

        real_open = open

        def fake_open(*args, **kwargs):
            raise IOError("disk full")

        with patch("builtins.open", side_effect=fake_open):
            with pytest.raises(IOError):
                bl.acquire()

    def test_acquire_timeout_stale_lock_removed(self, tmp_path):
        """When lock is held and timeout expires, check stale and remove."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=0)

        call_count = [0]
        original_flock = lock_mod.fcntl.flock

        def fake_flock(fd, op):
            call_count[0] += 1
            if call_count[0] <= 1:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return original_flock(fd, op)

        with patch.object(lock_mod.fcntl, "flock", side_effect=fake_flock):
            with patch("time.sleep"):
                with patch.object(bl, "_is_stale", return_value=True):
                    result = bl.acquire()
        assert result is True
        bl.release()

    def test_acquire_timeout_not_stale_returns_false(self, tmp_path):
        """When lock is held, timeout expires, and lock is NOT stale."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=0)

        def fake_flock(fd, op):
            raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

        with patch.object(lock_mod.fcntl, "flock", side_effect=fake_flock):
            with patch("time.sleep"):
                with patch.object(bl, "_is_stale", return_value=False):
                    result = bl.acquire()
        assert result is False
        assert bl.fd is None

    def test_acquire_timeout_stale_remove_oserror(self, tmp_path):
        """Stale lock removal fails with OSError — should still return False."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=0)

        def fake_flock(fd, op):
            raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

        # _is_stale returns True once (triggers remove), then False (gives up)
        stale_results = iter([True, False])
        with patch.object(lock_mod.fcntl, "flock", side_effect=fake_flock):
            with patch("time.sleep"):
                with patch.object(bl, "_is_stale", side_effect=lambda: next(stale_results)):
                    with patch("os.remove", side_effect=OSError("perm denied")):
                        result = bl.acquire()
        assert result is False

    def test_acquire_contention_then_success(self, tmp_path):
        """Lock is held briefly, then released — acquire succeeds after retry."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=2)

        call_count = [0]
        original_flock = lock_mod.fcntl.flock

        def fake_flock(fd, op):
            call_count[0] += 1
            if call_count[0] == 1:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return original_flock(fd, op)

        with patch.object(lock_mod.fcntl, "flock", side_effect=fake_flock):
            with patch("time.sleep"):
                result = bl.acquire()
        assert result is True
        assert call_count[0] >= 2
        bl.release()


class TestRelease:
    def test_release_no_fd(self, tmp_path):
        bl = BrainLock(str(tmp_path / "state.lock"))
        # Should not raise
        bl.release()

    def test_release_after_acquire(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        bl.acquire()
        bl.release()
        assert bl.fd is None

    def test_release_exception_handled(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        bl.acquire()

        # Force an exception during release
        with patch.object(bl.fd, "truncate", side_effect=IOError("fail")):
            bl.release()  # should not raise
        assert bl.fd is None


class TestGuard:
    def test_guard_acquires_and_releases(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        with bl.guard():
            assert bl.fd is not None
        assert bl.fd is None

    def test_guard_timeout_raises(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        with patch.object(bl, "acquire", return_value=False):
            with pytest.raises(TimeoutError, match="Could not acquire"):
                with bl.guard():
                    pass


class TestIsLocked:
    def test_not_locked_no_file(self, tmp_path):
        assert BrainLock.is_locked(str(tmp_path / "missing.lock")) is False

    def test_not_locked_file_exists_unlocked(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        lock_file.write_text("123")
        assert BrainLock.is_locked(str(lock_file)) is False

    def test_is_locked_held(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)
        bl.acquire()
        try:
            assert BrainLock.is_locked(str(lock_file)) is True
        finally:
            bl.release()

    def test_is_locked_unexpected_ioerror_raises(self, tmp_path):
        lock_file = tmp_path / "state.lock"
        lock_file.write_text("123")

        def fake_flock(fd, op):
            raise IOError("weird")

        with patch.object(lock_mod.fcntl, "flock", side_effect=fake_flock) if lock_mod.fcntl else patch("builtins.open", side_effect=IOError(errno.ENOENT, "no")):
            with pytest.raises(IOError):
                BrainLock.is_locked(str(lock_file))


# ── msvcrt (Windows) code paths ──
# On macOS/Linux, msvcrt is None. These tests inject a mock msvcrt
# to cover the Windows-specific locking paths.

class TestMsvcrtPaths:
    def test_acquire_via_msvcrt(self, tmp_path):
        """Cover msvcrt.locking path in acquire (lines 74-76)."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)

        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 1
        with patch.object(lock_mod, "fcntl", None), \
             patch.object(lock_mod, "msvcrt", mock_msvcrt):
            result = bl.acquire()
        assert result is True
        mock_msvcrt.locking.assert_called()
        bl.release()

    def test_release_via_msvcrt(self, tmp_path):
        """Cover msvcrt.locking unlock path in release (lines 118-120)."""
        lock_file = tmp_path / "state.lock"
        bl = BrainLock(str(lock_file), timeout=1)

        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 1
        mock_msvcrt.LK_UNLCK = 2
        with patch.object(lock_mod, "fcntl", None), \
             patch.object(lock_mod, "msvcrt", mock_msvcrt):
            bl.acquire()
            bl.release()
        # msvcrt.locking should have been called for unlock
        assert mock_msvcrt.locking.call_count >= 2

    def test_is_locked_via_msvcrt_not_locked(self, tmp_path):
        """Cover msvcrt path in is_locked (lines 153-157)."""
        lock_file = tmp_path / "state.lock"
        lock_file.write_text("123")

        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 1
        mock_msvcrt.LK_UNLCK = 2
        with patch.object(lock_mod, "fcntl", None), \
             patch.object(lock_mod, "msvcrt", mock_msvcrt):
            result = BrainLock.is_locked(str(lock_file))
        assert result is False

    def test_is_locked_via_msvcrt_locked(self, tmp_path):
        """Cover msvcrt path in is_locked when locked (line 160-162)."""
        lock_file = tmp_path / "state.lock"
        lock_file.write_text("123")

        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 1
        mock_msvcrt.locking.side_effect = IOError(errno.EACCES, "locked")
        with patch.object(lock_mod, "fcntl", None), \
             patch.object(lock_mod, "msvcrt", mock_msvcrt):
            result = BrainLock.is_locked(str(lock_file))
        assert result is True
