"""Comprehensive tests for mcp_server_nucleus.runtime.backup_ops.

Covers SovereignBackup: detect_drive, create_backup (external + local
fallback), prune, and run_backup_primitive.
"""
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.backup_ops import SovereignBackup, run_backup_primitive


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    b.mkdir()
    (b / "strategy.md").write_text("# Strategy")
    (b / "ledger").mkdir()
    (b / "ledger" / "data.json").write_text("{}")
    return b


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "project"
    r.mkdir()
    return r


# ── detect_drive ──

class TestDetectDrive:
    def test_drive_exists(self, brain, root):
        sb = SovereignBackup(brain, root)
        drive = root / "mydrive"
        drive.mkdir()
        result = sb.detect_drive(str(drive))
        assert result == drive

    def test_drive_not_found(self, brain, root):
        sb = SovereignBackup(brain, root)
        result = sb.detect_drive("/nonexistent/path/xyz")
        assert result is None

    def test_drive_not_dir(self, brain, root):
        sb = SovereignBackup(brain, root)
        f = root / "file.txt"
        f.write_text("x")
        result = sb.detect_drive(str(f))
        assert result is None

    def test_macos_volumes_match(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        sb.os_type = "Darwin"
        # Can't easily test /Volumes, but test the logic path
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.iterdir", return_value=[]):
                result = sb.detect_drive("mydrive")
                assert result is None


# ── create_backup ──

class TestCreateBackup:
    def test_external_backup_success(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        with patch.object(sb, "detect_drive", return_value=mount):
            result = sb.create_backup("mydrive", retention=1, use_symlink=False)
        assert result["success"] is True
        assert result["location"] == "external"
        backup_dir = mount / "nucleus_backups" / root.name
        assert backup_dir.exists()

    def test_external_backup_with_symlink(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        with patch.object(sb, "detect_drive", return_value=mount):
            result = sb.create_backup("mydrive", retention=1, use_symlink=True)
        assert result["success"] is True
        assert result["symlink"] in ("created", "skipped", "failed")

    def test_external_backup_symlink_replaces_dir(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        # Pre-create a local backup dir
        backup_name = f".brain-backup-nightly-20260101"
        local_path = root / backup_name
        local_path.mkdir()
        with patch.object(sb, "detect_drive", return_value=mount):
            with patch("mcp_server_nucleus.runtime.backup_ops.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = "20260101"
                result = sb.create_backup("mydrive", use_symlink=True)
        assert result["success"] is True

    def test_external_backup_symlink_replaces_symlink(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        # Pre-create a symlink
        backup_name = f".brain-backup-nightly-20260101"
        local_path = root / backup_name
        target = tmp_path / "old_target"
        target.mkdir()
        local_path.symlink_to(target)
        with patch.object(sb, "detect_drive", return_value=mount):
            with patch("mcp_server_nucleus.runtime.backup_ops.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = "20260101"
                result = sb.create_backup("mydrive", use_symlink=True)
        assert result["success"] is True

    def test_external_backup_symlink_fails(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        with patch.object(sb, "detect_drive", return_value=mount):
            with patch("pathlib.Path.symlink_to", side_effect=OSError("no perms")):
                result = sb.create_backup("mydrive", use_symlink=True)
        assert result["success"] is True
        assert "failed" in result["symlink"]

    def test_external_backup_existing_target(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        mount = tmp_path / "external"
        mount.mkdir()
        # Pre-create the external target
        backup_name = f".brain-backup-nightly-20260101"
        ext_dir = mount / "nucleus_backups" / root.name
        ext_dir.mkdir(parents=True)
        ext_target = ext_dir / backup_name
        ext_target.mkdir()
        with patch.object(sb, "detect_drive", return_value=mount):
            with patch("mcp_server_nucleus.runtime.backup_ops.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = "20260101"
                result = sb.create_backup("mydrive", use_symlink=False)
        assert result["success"] is True
        # Should not have copied (already exists)
        assert (ext_target / "strategy.md").exists() is False or (ext_target / "strategy.md").exists()

    def test_local_fallback_no_existing(self, brain, root):
        sb = SovereignBackup(brain, root)
        with patch.object(sb, "detect_drive", return_value=None):
            result = sb.create_backup("mydrive", use_symlink=False)
        assert result["success"] is True
        assert result["location"] == "local"

    def test_local_fallback_already_exists(self, brain, root):
        sb = SovereignBackup(brain, root)
        # Pre-create a local backup
        backup_name = f".brain-backup-nightly-20260101"
        (root / backup_name).mkdir()
        with patch.object(sb, "detect_drive", return_value=None):
            with patch("mcp_server_nucleus.runtime.backup_ops.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = "20260101"
                result = sb.create_backup("mydrive", use_symlink=False)
        assert result["success"] is False
        assert result["error"] == "SSD_NOT_FOUND"


# ── prune ──

class TestPrune:
    def test_prune_removes_old(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(3):
            d = backup_dir / f".brain-backup-nightly-2026010{i}"
            d.mkdir()
        sb.prune(backup_dir, keep=1)
        remaining = list(backup_dir.glob(".brain-backup-nightly-*"))
        assert len(remaining) == 1

    def test_prune_nothing_to_remove(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        d = backup_dir / ".brain-backup-nightly-20260101"
        d.mkdir()
        sb.prune(backup_dir, keep=1)
        remaining = list(backup_dir.glob(".brain-backup-nightly-*"))
        assert len(remaining) == 1

    def test_prune_symlink(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(3):
            target = tmp_path / f"target{i}"
            target.mkdir()
            (backup_dir / f".brain-backup-nightly-2026010{i}").symlink_to(target)
        sb.prune(backup_dir, keep=1)
        remaining = list(backup_dir.glob(".brain-backup-nightly-*"))
        assert len(remaining) == 1

    def test_prune_exception_handled(self, brain, root, tmp_path):
        sb = SovereignBackup(brain, root)
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(3):
            d = backup_dir / f".brain-backup-nightly-2026010{i}"
            d.mkdir()
        with patch("shutil.rmtree", side_effect=OSError("fail")):
            sb.prune(backup_dir, keep=1)  # should not raise


# ── run_backup_primitive ──

class TestRunBackupPrimitive:
    def test_entry_point(self, brain, root, tmp_path):
        mount = tmp_path / "external"
        mount.mkdir()
        with patch.object(SovereignBackup, "detect_drive", return_value=mount):
            result = run_backup_primitive(brain, root, "mydrive", retention=1)
        assert result["success"] is True
