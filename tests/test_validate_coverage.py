"""Comprehensive tests for mcp_server_nucleus.validate.

Covers H1TestResult, H1Validator: run_offline_validation, _evaluate_scenario,
_get_raw_logs_content, _compute_report, _save_report, and run_validate.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.validate import (
    H1TestResult,
    H1Validator,
    GOLDEN_SCENARIOS,
    run_validate,
)


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    b.mkdir()
    return b


@pytest.fixture
def validator(brain):
    return H1Validator(brain_path=brain)


@pytest.fixture
def sample_atoms():
    return [
        {
            "decision": "Three-layer architecture: Core, Audit, Governance orchestrator",
            "rationale": "For multi-tool coordination",
            "evidence": [],
            "confidence": 0.9,
            "tags": ["architecture"],
            "sha256": "abc123",
            "source_tool": "claude",
            "source_session": "s1",
        },
        {
            "decision": "Deployment platform configured via environment render service",
            "rationale": "For deployment",
            "evidence": [],
            "confidence": 0.8,
            "tags": ["deployment"],
            "sha256": "def456",
            "source_tool": "ag",
            "source_session": "s2",
        },
    ]


# ── H1TestResult ──

class TestH1TestResult:
    def test_init(self):
        result = H1TestResult(
            scenario_id="S01",
            scenario_name="Test",
            mode="dca",
            keyword_hits=3,
            keyword_total=5,
            characters_provided=1000,
            recovery_score=0.6,
        )
        assert result.scenario_id == "S01"
        assert result.mode == "dca"
        assert result.keyword_hits == 3
        assert result.recovery_score == 0.6
        assert result.timestamp is not None

    def test_to_dict(self):
        result = H1TestResult(
            scenario_id="S01",
            scenario_name="Test",
            mode="raw",
            keyword_hits=2,
            keyword_total=5,
            characters_provided=500,
            recovery_score=0.4,
        )
        d = result.to_dict()
        assert d["scenario_id"] == "S01"
        assert d["mode"] == "raw"
        assert d["keyword_hits"] == 2
        assert d["recovery_score"] == 0.4
        assert "timestamp" in d


# ── GOLDEN_SCENARIOS ──

class TestGoldenScenarios:
    def test_scenarios_exist(self):
        assert len(GOLDEN_SCENARIOS) == 5

    def test_scenario_structure(self):
        for s in GOLDEN_SCENARIOS:
            assert "id" in s
            assert "name" in s
            assert "question" in s
            assert "expected_keywords" in s
            assert "expected_decision" in s
            assert "difficulty" in s


# ── H1Validator.__init__ ──

class TestValidatorInit:
    def test_init_creates_results_dir(self, brain):
        v = H1Validator(brain_path=brain)
        assert v.brain_path == brain
        assert v.results_dir.exists()
        assert v.results_dir == brain / "validation"


# ── _evaluate_scenario ──

class TestEvaluateScenario:
    def test_all_hits(self, validator):
        scenario = {
            "id": "S01",
            "name": "Test",
            "expected_keywords": ["three-layer", "core", "audit"],
        }
        context = "three-layer core audit architecture"
        result = validator._evaluate_scenario(scenario, context, "dca")
        assert result.keyword_hits == 3
        assert result.recovery_score == 1.0
        assert result.mode == "dca"

    def test_no_hits(self, validator):
        scenario = {
            "id": "S01",
            "name": "Test",
            "expected_keywords": ["python", "java"],
        }
        context = "nothing relevant here"
        result = validator._evaluate_scenario(scenario, context, "raw")
        assert result.keyword_hits == 0
        assert result.recovery_score == 0.0

    def test_partial_hits(self, validator):
        scenario = {
            "id": "S01",
            "name": "Test",
            "expected_keywords": ["python", "java", "go"],
        }
        context = "python and java are languages"
        result = validator._evaluate_scenario(scenario, context, "dca")
        assert result.keyword_hits == 2
        assert result.recovery_score == pytest.approx(2/3)

    def test_empty_keywords(self, validator):
        scenario = {
            "id": "S01",
            "name": "Test",
            "expected_keywords": [],
        }
        result = validator._evaluate_scenario(scenario, "context", "dca")
        assert result.recovery_score == 0.0


# ── _get_raw_logs_content ──

class TestGetRawLogsContent:
    def test_empty(self, validator, brain):
        # brain.parent has no dirs with .md files
        result = validator._get_raw_logs_content()
        assert isinstance(result, str)

    def test_with_siphon(self, validator, brain):
        siphon = brain / "siphon"
        siphon.mkdir()
        (siphon / "log.md").write_text("some log content about architecture")
        result = validator._get_raw_logs_content()
        assert "architecture" in result

    def test_with_md_in_parent(self, validator, brain, tmp_path):
        # Create a dir in brain.parent with .md files
        d = brain.parent / "session1"
        d.mkdir()
        (d / "notes.md").write_text("some notes about the project")
        result = validator._get_raw_logs_content()
        assert "notes" in result

    def test_skips_large_files(self, validator, brain):
        siphon = brain / "siphon"
        siphon.mkdir()
        (siphon / "big.md").write_text("x" * 600_000)
        result = validator._get_raw_logs_content()
        # Large file should be skipped
        assert "x" * 600_000 not in result


# ── _compute_report ──

class TestComputeReport:
    def test_report_structure(self, validator):
        dca_results = [
            H1TestResult("S01", "Test1", "dca", 3, 5, 100, 0.6),
            H1TestResult("S02", "Test2", "dca", 5, 5, 200, 1.0),
        ]
        raw_results = [
            H1TestResult("S01", "Test1", "raw", 1, 5, 1000, 0.2),
            H1TestResult("S02", "Test2", "raw", 2, 5, 2000, 0.4),
        ]
        report = validator._compute_report(dca_results, raw_results, "dca_ctx", "raw_ctx")
        assert report["hypothesis"] is not None
        assert report["scenarios_tested"] == 2
        assert "dca_metrics" in report
        assert "raw_metrics" in report
        assert "comparison" in report
        assert "per_scenario" in report
        assert len(report["per_scenario"]) == 2

    def test_efficiency_ratio_inf(self, validator):
        dca_results = [H1TestResult("S01", "T", "dca", 1, 5, 100, 0.2)]
        raw_results = [H1TestResult("S01", "T", "raw", 0, 5, 100, 0.0)]
        report = validator._compute_report(dca_results, raw_results, "dca", "raw")
        # raw_density = 0, so efficiency_ratio = inf
        assert report["comparison"]["efficiency_ratio"] == float("inf")
        assert report["comparison"]["dca_advantage_pct"] == "N/A"

    def test_h1_validated(self, validator):
        dca_results = [H1TestResult("S01", "T", "dca", 5, 5, 50, 1.0)]
        raw_results = [H1TestResult("S01", "T", "raw", 1, 5, 5000, 0.2)]
        report = validator._compute_report(dca_results, raw_results, "dca", "raw")
        assert report["comparison"]["h1_validated"] is True

    def test_h1_not_validated(self, validator):
        dca_results = [H1TestResult("S01", "T", "dca", 1, 5, 100, 0.2)]
        raw_results = [H1TestResult("S01", "T", "raw", 1, 5, 100, 0.2)]
        report = validator._compute_report(dca_results, raw_results, "same", "same")
        assert report["comparison"]["h1_validated"] is False

    def test_no_raw_baseline_not_a_phantom_win(self, validator):
        """Empty raw_context (no raw logs found) must NOT report a validated
        win. efficiency_ratio is 'N/A (no raw baseline)', h1_validated is
        False — a comparison with no baseline is an unmeasurable claim, not
        an infinite-efficiency win."""
        dca_results = [H1TestResult("S01", "T", "dca", 5, 5, 100, 1.0)]
        raw_results = [H1TestResult("S01", "T", "raw", 0, 5, 0, 0.0)]
        report = validator._compute_report(dca_results, raw_results, "dca_ctx", "")
        assert report["comparison"]["h1_validated"] is False
        assert report["comparison"]["efficiency_ratio"] == "N/A (no raw baseline)"
        assert report["comparison"]["dca_advantage_pct"] == "N/A"

    def test_empty_dca_results(self, validator):
        report = validator._compute_report([], [], "dca", "raw")
        assert report["dca_metrics"]["avg_recovery_score"] == 0
        assert report["raw_metrics"]["avg_recovery_score"] == 0

    def test_empty_context(self, validator):
        dca_results = [H1TestResult("S01", "T", "dca", 1, 5, 100, 0.2)]
        raw_results = [H1TestResult("S01", "T", "raw", 1, 5, 100, 0.2)]
        report = validator._compute_report(dca_results, raw_results, "", "raw")
        assert report["dca_metrics"]["information_density"] == 0
        assert report["comparison"]["compression_ratio"] == 0


# ── _save_report ──

class TestSaveReport:
    def test_save_json_and_md(self, validator, brain):
        report = {
            "hypothesis": "H1: test",
            "timestamp": "2026-01-01T00:00:00",
            "scenarios_tested": 2,
            "dca_metrics": {
                "avg_recovery_score": 0.8,
                "information_density": 5.0,
                "context_length_chars": 100,
            },
            "raw_metrics": {
                "avg_recovery_score": 0.4,
                "information_density": 1.0,
                "context_length_chars": 500,
            },
            "comparison": {
                "efficiency_ratio": 5.0,
                "compression_ratio": 5.0,
                "dca_advantage_pct": 400.0,
                "h1_validated": True,
            },
            "per_scenario": [
                {"id": "S01", "name": "Test1", "dca_recovery": 0.8, "raw_recovery": 0.4, "delta": 0.4},
                {"id": "S02", "name": "Test2", "dca_recovery": 0.6, "raw_recovery": 0.6, "delta": 0.0},
            ],
        }
        md_path = validator._save_report(report)
        json_files = list(validator.results_dir.glob("h1_validation_*.json"))
        md_files = list(validator.results_dir.glob("h1_validation_*.md"))
        assert len(json_files) == 1
        assert len(md_files) == 1
        md_content = md_path.read_text()
        assert "H1 Validation Report" in md_content
        assert "H1 VALIDATED" in md_content

    def test_save_not_validated(self, validator):
        report = {
            "hypothesis": "H1: test",
            "timestamp": "2026-01-01T00:00:00",
            "scenarios_tested": 1,
            "dca_metrics": {
                "avg_recovery_score": 0.3,
                "information_density": 1.0,
                "context_length_chars": 100,
            },
            "raw_metrics": {
                "avg_recovery_score": 0.3,
                "information_density": 1.0,
                "context_length_chars": 100,
            },
            "comparison": {
                "efficiency_ratio": 1.0,
                "compression_ratio": 1.0,
                "dca_advantage_pct": 0.0,
                "h1_validated": False,
            },
            "per_scenario": [
                {"id": "S01", "name": "Test1", "dca_recovery": 0.3, "raw_recovery": 0.3, "delta": 0.0},
            ],
        }
        md_path = validator._save_report(report)
        md_content = md_path.read_text()
        assert "NOT YET VALIDATED" in md_content

    def test_save_negative_delta(self, validator):
        report = {
            "hypothesis": "H1: test",
            "timestamp": "2026-01-01T00:00:00",
            "scenarios_tested": 1,
            "dca_metrics": {
                "avg_recovery_score": 0.2,
                "information_density": 1.0,
                "context_length_chars": 100,
            },
            "raw_metrics": {
                "avg_recovery_score": 0.5,
                "information_density": 2.0,
                "context_length_chars": 100,
            },
            "comparison": {
                "efficiency_ratio": 0.5,
                "compression_ratio": 1.0,
                "dca_advantage_pct": -50.0,
                "h1_validated": False,
            },
            "per_scenario": [
                {"id": "S01", "name": "Test1", "dca_recovery": 0.2, "raw_recovery": 0.5, "delta": -0.3},
            ],
        }
        md_path = validator._save_report(report)
        md_content = md_path.read_text()
        assert "🔴" in md_content


# ── run_offline_validation ──

class TestRunOfflineValidation:
    def test_no_atoms(self, validator, brain):
        result = validator.run_offline_validation()
        assert "error" in result
        assert "No DCAs" in result["error"]

    def test_with_atoms(self, validator, brain, sample_atoms):
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = validator.run_offline_validation()
        assert "error" not in result
        assert "dca_metrics" in result
        assert "raw_metrics" in result
        assert "comparison" in result
        # Reports should be saved
        json_files = list(validator.results_dir.glob("h1_validation_*.json"))
        assert len(json_files) == 1

    def test_with_custom_scenarios(self, validator, brain, sample_atoms):
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        custom = [GOLDEN_SCENARIOS[0]]
        result = validator.run_offline_validation(scenarios=custom)
        assert result["scenarios_tested"] == 1


# ── run_validate ──

class TestRunValidate:
    def test_unknown_test(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = run_validate(test="h2")
        assert "error" in result
        assert "Unknown test" in result["error"]

    def test_no_atoms(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        result = run_validate(test="h1")
        assert "error" in result
        assert "No DCAs" in result["error"]

    def test_with_atoms(self, brain, monkeypatch, sample_atoms):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        distill = brain / "distill"
        distill.mkdir(exist_ok=True)
        with open(distill / "dca_20260101_000000.jsonl", "w") as f:
            for atom in sample_atoms:
                f.write(json.dumps(atom) + "\n")
        result = run_validate(test="h1", scenarios=2)
        assert "dca_metrics" in result
