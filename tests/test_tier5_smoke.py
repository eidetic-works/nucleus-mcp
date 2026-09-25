"""GROUND Tier 5 smoke test — outcome verification with delta-based claims.

Tests _tier5_outcome_check() and _find_recent_plan() with:
  - Count claims that pass (actual delta meets threshold)
  - Count claims that fail (premature victory)
  - File existence claims
  - Edge cases (empty baseline, missing files)

All I/O uses tmp_path. No git, no subprocess.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def project(tmp_path):
    """Create a minimal project structure for Tier 5 testing."""
    root = tmp_path / "project"
    root.mkdir()
    (root / ".brain" / "driver").mkdir(parents=True)
    return root


def _write_baseline(project: Path, claims: list) -> Path:
    """Write an outcome_baseline.json with the given claims."""
    baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"
    baseline_path.write_text(json.dumps({"claims": claims}, indent=2))
    return baseline_path


def _create_test_files(project: Path, count: int):
    """Create test_*.py files with test functions for _measure_count('test')."""
    tests_dir = project / "tests"
    tests_dir.mkdir(exist_ok=True)
    for i in range(count):
        (tests_dir / f"test_module_{i}.py").write_text(
            f"def test_case_{i}_a():\n    pass\n\n"
            f"def test_case_{i}_b():\n    pass\n\n"
        )


class TestTier5OutcomeCheck:
    """Tests for _tier5_outcome_check()."""

    def test_count_claim_passes_when_delta_met(self, project):
        """A count claim passes when actual delta >= 25% of claimed delta."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        # Baseline: 10 tests existed, claim +20 more
        _write_baseline(project, [
            {
                "claim_type": "count",
                "unit": "test",
                "baseline_value": 10,
                "claimed_delta": 20,
            }
        ])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        # Create enough test files: 10 baseline + 20 new = 30 total
        # We need actual delta >= 5 (25% of 20) to pass
        _create_test_files(project, 15)  # 15 files × 2 tests = 30 tests

        signals = _tier5_outcome_check(
            plan_text="Add 20 more tests",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )

        assert len(signals) == 1
        sig = signals[0]
        assert sig["tier"] == 5
        assert sig["passed"] is True
        assert sig["actual_delta"] == 20  # 30 - 10
        assert sig["hit_ratio"] == 1.0

    def test_count_claim_fails_premature_victory(self, project):
        """A count claim fails when actual delta < 25% of claimed delta."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        # Baseline: 10 tests existed, claim +100 more
        _write_baseline(project, [
            {
                "claim_type": "count",
                "unit": "test",
                "baseline_value": 10,
                "claimed_delta": 100,
            }
        ])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        # Create only 12 test functions (delta = 2, need 25 to pass)
        _create_test_files(project, 6)  # 6 files × 2 tests = 12 tests

        signals = _tier5_outcome_check(
            plan_text="Add 100 tests",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )

        assert len(signals) == 1
        sig = signals[0]
        assert sig["passed"] is False
        assert "PREMATURE VICTORY" in sig["error"]
        assert sig["hit_ratio"] < 0.25

    def test_file_claim_passes_when_file_exists(self, project):
        """A file claim passes when the target file exists."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        target = "src/new_module.py"
        (project / "src").mkdir()
        (project / target).write_text("# new module\n")

        _write_baseline(project, [
            {
                "claim_type": "file",
                "target": target,
                "baseline_exists": False,
            }
        ])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        signals = _tier5_outcome_check(
            plan_text="Create src/new_module.py",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )

        assert len(signals) == 1
        assert signals[0]["passed"] is True
        assert signals[0]["exists_now"] is True

    def test_file_claim_fails_when_missing(self, project):
        """A file claim fails when the target file doesn't exist."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        _write_baseline(project, [
            {
                "claim_type": "file",
                "target": "src/missing_module.py",
                "baseline_exists": False,
            }
        ])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        signals = _tier5_outcome_check(
            plan_text="Create src/missing_module.py",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )

        assert len(signals) == 1
        assert signals[0]["passed"] is False
        assert "PREMATURE VICTORY" in signals[0]["error"]

    def test_empty_claims_returns_no_signals(self, project):
        """Baseline with no claims returns empty signals list."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        _write_baseline(project, [])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        signals = _tier5_outcome_check(
            plan_text="Nothing claimed",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )
        assert signals == []

    def test_corrupted_baseline_returns_empty(self, project):
        """Corrupted baseline JSON returns empty (doesn't crash)."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"
        baseline_path.write_text("NOT VALID JSON{{{")

        signals = _tier5_outcome_check(
            plan_text="anything",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )
        assert signals == []

    def test_multiple_claims_mixed_results(self, project):
        """Multiple claims can have mixed pass/fail results."""
        from mcp_server_nucleus.runtime.execution_verifier import _tier5_outcome_check

        (project / "src").mkdir()
        (project / "src" / "created.py").write_text("# exists\n")

        _create_test_files(project, 3)  # 6 tests

        _write_baseline(project, [
            {
                "claim_type": "file",
                "target": "src/created.py",
                "baseline_exists": False,
            },
            {
                "claim_type": "file",
                "target": "src/not_created.py",
                "baseline_exists": False,
            },
            {
                "claim_type": "count",
                "unit": "test",
                "baseline_value": 0,
                "claimed_delta": 6,
            },
        ])
        baseline_path = project / ".brain" / "driver" / "outcome_baseline.json"

        signals = _tier5_outcome_check(
            plan_text="Create files and tests",
            project_root=project,
            budget_s=10,
            baseline_path=baseline_path,
        )

        assert len(signals) == 3
        passed = [s for s in signals if s["passed"]]
        failed = [s for s in signals if not s["passed"]]
        assert len(passed) == 2  # created.py + 6 tests
        assert len(failed) == 1  # not_created.py


class TestFindRecentPlan:
    """Tests for _find_recent_plan()."""

    def test_finds_manual_plan(self, project, monkeypatch):
        """Should find a manual plan in .brain/driver/current_plan.md."""
        from mcp_server_nucleus.runtime.execution_verifier import _find_recent_plan

        # Mock Path.home() to an empty dir so ~/.claude/plans doesn't interfere
        fake_home = project / "_fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        plan_path = project / ".brain" / "driver" / "current_plan.md"
        plan_path.write_text("# My Plan\n\nDo stuff.\n")

        found = _find_recent_plan(project)
        assert found is not None
        assert found.name == "current_plan.md"

    def test_returns_none_when_no_plan(self, tmp_path, monkeypatch):
        """Should return None when no plan file exists."""
        from mcp_server_nucleus.runtime.execution_verifier import _find_recent_plan

        # Mock Path.home() to an empty dir
        fake_home = tmp_path / "_fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

        empty = tmp_path / "empty_project"
        empty.mkdir()
        found = _find_recent_plan(empty)
        assert found is None
