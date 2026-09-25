"""Tests for Tier 3 aggregate collection mode (fw-1786151929).

Verifies that _tier3_test_execution runs both per-file and aggregate
collection modes, and that disagreement between them is flagged.
"""
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


@pytest.fixture
def fake_project(tmp_path):
    """Create a minimal project with a test file."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("")
    (tmp_path / "tests" / "test_src.py").write_text(
        "def test_basic():\n    assert True\n"
    )
    (tmp_path / "src.py").write_text("x = 1\n")
    return tmp_path


class TestTier3Aggregate:
    def test_per_file_signal_has_collection_mode(self, fake_project):
        """Per-file signals carry collection_mode='per_file'."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier3_test_execution

        # Mock subprocess to return success
        def fake_run(cmd, **kw):
            return MagicMock(returncode=0, stdout="1 passed", stderr="")
        with patch("subprocess.run", side_effect=fake_run):
            signals = _tier3_test_execution(
                ["src.py"], {}, fake_project, budget_s=60.0
            )
        per_file = [s for s in signals if s.get("collection_mode") == "per_file"]
        assert len(per_file) > 0

    def test_aggregate_runs_after_per_file_pass(self, fake_project):
        """Aggregate signal is present when per-file tests pass."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier3_test_execution

        def fake_run(cmd, **kw):
            return MagicMock(returncode=0, stdout="1 passed", stderr="")
        with patch("subprocess.run", side_effect=fake_run):
            signals = _tier3_test_execution(
                ["src.py"], {}, fake_project, budget_s=60.0
            )
        aggregate = [s for s in signals if s.get("collection_mode") == "aggregate"]
        assert len(aggregate) == 1

    def test_aggregate_skipped_when_per_file_fails(self, fake_project):
        """Aggregate is NOT run when per-file tests fail."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier3_test_execution

        def fake_run(cmd, **kw):
            return MagicMock(returncode=1, stdout="1 failed", stderr="")
        with patch("subprocess.run", side_effect=fake_run):
            signals = _tier3_test_execution(
                ["src.py"], {}, fake_project, budget_s=60.0
            )
        aggregate = [s for s in signals if s.get("collection_mode") == "aggregate"]
        assert len(aggregate) == 0

    def test_disagreement_flagged_when_aggregate_fails(self, fake_project):
        """Per-file pass + aggregate fail → aggregate_disagreement=True."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier3_test_execution

        def fake_run(cmd, **kw):
            # Aggregate command has "-k" and "--continue-on-collection-errors"
            if "--continue-on-collection-errors" in cmd:
                return MagicMock(returncode=1, stdout="2 failed", stderr="")
            return MagicMock(returncode=0, stdout="1 passed", stderr="")
        with patch("subprocess.run", side_effect=fake_run):
            signals = _tier3_test_execution(
                ["src.py"], {}, fake_project, budget_s=60.0
            )
        aggregate = [s for s in signals if s.get("collection_mode") == "aggregate"]
        assert len(aggregate) == 1
        assert aggregate[0]["passed"] is False
        assert aggregate[0].get("aggregate_disagreement") is True
        assert aggregate[0].get("reason") == "per_file_passed_aggregate_failed"

    def test_no_disagreement_when_both_pass(self, fake_project):
        """Per-file pass + aggregate pass → no disagreement flag."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier3_test_execution

        def fake_run(cmd, **kw):
            return MagicMock(returncode=0, stdout="1 passed", stderr="")
        with patch("subprocess.run", side_effect=fake_run):
            signals = _tier3_test_execution(
                ["src.py"], {}, fake_project, budget_s=60.0
            )
        aggregate = [s for s in signals if s.get("collection_mode") == "aggregate"]
        assert len(aggregate) == 1
        assert aggregate[0]["passed"] is True
        assert "aggregate_disagreement" not in aggregate[0]
