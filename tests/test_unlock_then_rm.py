"""Tests for Locker.unlock_then_rm — the portable governed-rotation primitive.

Covers: real chflags uchg lock + rm cycle, missing-path error, nested-dir lock.
Skips on non-macOS/non-chflags hosts (primitive is noop there — covered by
lock() method's own skip path).
"""
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

from mcp_server_nucleus.hypervisor.locker import Locker


def _has_chflags() -> bool:
    return shutil.which("chflags") is not None and sys.platform == "darwin"


@pytest.fixture
def locker():
    return Locker()


def test_unlock_then_rm_missing_path(locker):
    result = locker.unlock_then_rm("/tmp/definitely_does_not_exist_abc123xyz")
    assert result["success"] is False
    assert "path not found" in result["error"]
    assert result["bytes_freed"] == 0


@pytest.mark.skipif(not _has_chflags(), reason="chflags unavailable; primitive is noop")
def test_unlock_then_rm_locked_dir(locker, tmp_path):
    """Simulate the backup-dir scenario: dir with locked file inside."""
    target = tmp_path / "fake-backup-dir"
    target.mkdir()
    inner = target / "nucleus.json"
    inner.write_text('{"tamper": "resistant"}')

    assert locker.lock(str(target))
    assert locker.is_locked(str(target))

    result = locker.unlock_then_rm(str(target))
    assert result["success"] is True
    assert result["bytes_freed"] > 0
    assert not target.exists()
    assert result["error"] is None


@pytest.mark.skipif(not _has_chflags(), reason="chflags unavailable; primitive is noop")
def test_unlock_then_rm_plain_dir(locker, tmp_path):
    """Unlocked dir: primitive should still work (unlock is idempotent)."""
    target = tmp_path / "plain-dir"
    target.mkdir()
    (target / "a.txt").write_text("hello")

    result = locker.unlock_then_rm(str(target))
    assert result["success"] is True
    assert not target.exists()
