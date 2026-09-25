"""Comprehensive tests for mcp_server_nucleus.commitment_core.

Covers _scan_commitments, _list_commitments, _close_commitment,
and _get_commitment_health.
"""
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus import commitment_core


# ── _scan_commitments ──

class TestScanCommitments:
    def test_scan_success_no_artifacts(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        result = commitment_core._scan_commitments()
        assert result["success"] is True
        assert "stats" in result
        assert "last_scan" in result

    def test_scan_with_checklist_items(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        artifacts = brain / "artifacts"
        artifacts.mkdir()
        (artifacts / "doc.md").write_text("- [ ] Do something important here\n")
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)

        mock_result = MagicMock()
        mock_result.stdout = f"{artifacts / 'doc.md'}:1:- [ ] Do something important here\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = commitment_core._scan_commitments()
        assert result["success"] is True

    def test_scan_checklist_exception_handled(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        artifacts = brain / "artifacts"
        artifacts.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)

        with patch("subprocess.run", side_effect=RuntimeError("rg not found")):
            result = commitment_core._scan_commitments()
        # Should still succeed (checklist scan failure is caught)
        assert result["success"] is True

    def test_scan_general_exception_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            commitment_core,
            "get_brain_path",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        result = commitment_core._scan_commitments()
        assert " error" in result or "error" in result
        assert "boom" in str(result)


# ── _list_commitments ──

class TestListCommitments:
    def test_list_all(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        # Inject get_open_commitments (not present in ledger module)
        commitment_core.commitment_ledger.get_open_commitments = (
            lambda brain_path, tier=None: [{"id": "c1"}]
        )
        try:
            result = commitment_core._list_commitments()
        finally:
            del commitment_core.commitment_ledger.get_open_commitments
        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["commitments"]) == 1

    def test_list_with_tier(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        commitment_core.commitment_ledger.get_open_commitments = (
            lambda brain_path, tier=None: []
        )
        try:
            result = commitment_core._list_commitments(tier="red")
        finally:
            del commitment_core.commitment_ledger.get_open_commitments
        assert result["success"] is True
        assert result["count"] == 0

    def test_list_exception_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            commitment_core,
            "get_brain_path",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        result = commitment_core._list_commitments()
        assert "error" in result
        assert "boom" in result["error"]


# ── _close_commitment ──

class TestCloseCommitment:
    def test_close_success(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        closed_comm = {"id": "c1", "description": "Do a thing"}
        with patch.object(
            commitment_core.commitment_ledger,
            "close_commitment",
            return_value=closed_comm,
        ):
            result = commitment_core._close_commitment("c1", "completed")
        assert result["success"] is True
        assert result["commitment"] == closed_comm

    def test_close_exception_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            commitment_core,
            "get_brain_path",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        result = commitment_core._close_commitment("c1", "completed")
        assert "error" in result
        assert "boom" in result["error"]


# ── _get_commitment_health ──

class TestGetCommitmentHealth:
    def test_healthy_green(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        ledger = {
            "stats": {"total_open": 2, "green_tier": 2, "yellow_tier": 0, "red_tier": 0},
            "last_scan": "2026-01-01T00:00:00",
        }
        with patch.object(
            commitment_core.commitment_ledger, "load_ledger", return_value=ledger
        ):
            result = commitment_core._get_commitment_health()
        assert result["health_status"] == "🟢 HEALTHY"
        assert result["total_open"] == 2
        assert result["green"] == 2

    def test_watch_yellow(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        ledger = {
            "stats": {"total_open": 3, "green_tier": 0, "yellow_tier": 3, "red_tier": 0},
            "last_scan": None,
        }
        with patch.object(
            commitment_core.commitment_ledger, "load_ledger", return_value=ledger
        ):
            result = commitment_core._get_commitment_health()
        assert result["health_status"] == "🟡 WATCH"
        assert result["yellow"] == 3

    def test_needs_attention_red(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        ledger = {
            "stats": {"total_open": 1, "green_tier": 0, "yellow_tier": 0, "red_tier": 1},
            "last_scan": "2026-01-01",
        }
        with patch.object(
            commitment_core.commitment_ledger, "load_ledger", return_value=ledger
        ):
            result = commitment_core._get_commitment_health()
        assert result["health_status"] == "🔴 NEEDS ATTENTION"
        assert result["red"] == 1

    def test_empty_stats(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setattr(commitment_core, "get_brain_path", lambda: brain)
        ledger = {"stats": {}, "last_scan": None}
        with patch.object(
            commitment_core.commitment_ledger, "load_ledger", return_value=ledger
        ):
            result = commitment_core._get_commitment_health()
        assert result["health_status"] == "🟢 HEALTHY"
        assert result["total_open"] == 0

    def test_exception_returns_error(self, monkeypatch):
        monkeypatch.setattr(
            commitment_core,
            "get_brain_path",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        result = commitment_core._get_commitment_health()
        assert "error" in result
        assert "boom" in result["error"]
