"""Comprehensive coverage tests for backup_job.py."""

import shutil
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.jobs import backup_job


@pytest.fixture
def setup_paths(monkeypatch, tmp_path):
    """Patch PROJECT_ROOT and BRAIN_PATH to tmp_path-based locations."""
    monkeypatch.setattr(backup_job, "PROJECT_ROOT", tmp_path)
    brain = tmp_path / ".brain"
    monkeypatch.setattr(backup_job, "BRAIN_PATH", brain)
    return tmp_path, brain


@pytest.mark.asyncio
async def test_run_backup_brain_not_found(setup_paths):
    """BRAIN_PATH missing → error."""
    tmp_path, brain = setup_paths
    result = await backup_job.run_backup()
    assert result["ok"] is False
    assert result["error"] == ".brain not found"


@pytest.mark.asyncio
async def test_run_backup_success(setup_paths):
    """Normal backup → ok True with backup name."""
    tmp_path, brain = setup_paths
    brain.mkdir()
    (brain / "data.txt").write_text("hello")
    (brain / "subdir").mkdir()
    (brain / "subdir" / "nested.txt").write_text("nested")

    result = await backup_job.run_backup(tag="weekly")
    assert result["ok"] is True
    assert result["backup"].startswith(".brain-backup-weekly-")
    assert result["pruned"] == 0

    # Verify backup was created
    backup_path = tmp_path / result["backup"]
    assert backup_path.exists()
    assert (backup_path / "data.txt").read_text() == "hello"
    assert (backup_path / "subdir" / "nested.txt").read_text() == "nested"


@pytest.mark.asyncio
async def test_run_backup_ignores_lock_and_pycache(setup_paths):
    """Lock files and __pycache__ are excluded from backup."""
    tmp_path, brain = setup_paths
    brain.mkdir()
    (brain / "data.txt").write_text("hello")
    (brain / "test.lock").write_text("lock")
    (brain / "__pycache__").mkdir()
    (brain / "__pycache__" / "cached.pyc").write_text("cache")

    result = await backup_job.run_backup(tag="daily")
    assert result["ok"] is True
    backup_path = tmp_path / result["backup"]
    assert (backup_path / "data.txt").exists()
    assert not (backup_path / "test.lock").exists()
    assert not (backup_path / "__pycache__").exists()


@pytest.mark.asyncio
async def test_run_backup_prune_old(setup_paths, monkeypatch):
    """Old backups beyond MAX_BACKUPS are pruned."""
    tmp_path, brain = setup_paths
    brain.mkdir()
    (brain / "data.txt").write_text("hello")
    monkeypatch.setattr(backup_job, "MAX_BACKUPS", 2)

    # Pre-create old backups
    for stamp in ["20240101_000000", "20240102_000000", "20240103_000000"]:
        old = tmp_path / f".brain-backup-weekly-{stamp}"
        old.mkdir()
        (old / "dummy").write_text("old")

    result = await backup_job.run_backup(tag="weekly")
    assert result["ok"] is True
    # 4 total (3 old + 1 new), MAX_BACKUPS=2, so pruned=2
    assert result["pruned"] == 2

    # Only 2 backups should remain
    remaining = sorted(tmp_path.glob(".brain-backup-weekly-*"))
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_run_backup_custom_tag(setup_paths):
    """Custom tag is used in backup name."""
    tmp_path, brain = setup_paths
    brain.mkdir()
    (brain / "data.txt").write_text("hello")

    result = await backup_job.run_backup(tag="monthly")
    assert result["ok"] is True
    assert result["backup"].startswith(".brain-backup-monthly-")


@pytest.mark.asyncio
async def test_run_backup_exception(setup_paths, monkeypatch):
    """Exception during backup → caught, returns error."""
    tmp_path, brain = setup_paths
    brain.mkdir()
    (brain / "data.txt").write_text("hello")

    def boom(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(shutil, "copytree", boom)
    result = await backup_job.run_backup()
    assert result["ok"] is False
    assert "denied" in result["error"]
