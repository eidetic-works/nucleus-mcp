"""Tests for job_error_sample utility (fw-1786179343).

Verifies that build_job_response always includes bounded error samples
when errors > 0, so a job response never reports a failure count without
explaining what failed.
"""
import sys
import pytest
from pathlib import Path

# scripts/ lives at the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class TestJobErrorResponse:
    def test_includes_sample_errors_when_errors_present(self):
        """A response with errors MUST include sampleErrors."""
        from scripts.job_error_sample import build_job_response
        errors = [
            {"item": "a", "error": "cannot set path in scalar"},
            {"item": "b", "error": "cannot set path in scalar"},
            {"item": "c", "error": "connection refused"},
        ]
        resp = build_job_response(total=100, marked=97, errors=errors)
        assert resp["success"] is False
        assert resp["errors"] == 3
        assert "sampleErrors" in resp
        assert len(resp["sampleErrors"]) > 0

    def test_no_sample_errors_when_no_errors(self):
        """A successful response has empty sampleErrors."""
        from scripts.job_error_sample import build_job_response
        resp = build_job_response(total=100, marked=100, errors=[])
        assert resp["success"] is True
        assert resp["errors"] == 0
        assert resp["sampleErrors"] == []

    def test_dedupes_errors_by_message(self):
        """Repeated error messages are deduped with a count."""
        from scripts.job_error_sample import build_job_response
        errors = [
            {"item": f"item_{i}", "error": "cannot set path in scalar"}
            for i in range(20)
        ]
        resp = build_job_response(total=100, marked=80, errors=errors)
        # All 20 errors have the same message → 1 unique sample
        assert len(resp["sampleErrors"]) == 1
        assert resp["sampleErrors"][0]["count"] == 20
        assert "cannot set path in scalar" in resp["sampleErrors"][0]["error"]

    def test_sample_size_caps_samples(self):
        """sample_size limits the number of unique error samples."""
        from scripts.job_error_sample import build_job_response
        errors = [
            {"item": f"item_{i}", "error": f"error_type_{i}"}
            for i in range(50)
        ]
        resp = build_job_response(total=100, marked=50, errors=errors, sample_size=5)
        assert len(resp["sampleErrors"]) <= 5

    def test_includes_error_breakdown(self):
        """errorBreakdown shows count per unique message."""
        from scripts.job_error_sample import build_job_response
        errors = [
            {"item": "a", "error": "type_a"},
            {"item": "b", "error": "type_a"},
            {"item": "c", "error": "type_b"},
        ]
        resp = build_job_response(total=10, marked=7, errors=errors)
        assert "errorBreakdown" in resp
        assert resp["errorBreakdown"]["type_a"] == 2
        assert resp["errorBreakdown"]["type_b"] == 1

    def test_sample_actions_capped(self):
        """sampleActions is capped at sample_size."""
        from scripts.job_error_sample import build_job_response
        actions = [{"item": f"item_{i}"} for i in range(50)]
        resp = build_job_response(
            total=100, marked=100, errors=[],
            sample_actions=actions, sample_size=10,
        )
        assert len(resp["sampleActions"]) <= 10

    def test_7142_errors_scenario(self):
        """The exact scenario from the ticket: 7142 errors, no detail."""
        from scripts.job_error_sample import build_job_response
        errors = [
            {"item": f"rakuten-49384-{i}", "error": "u: cannot set path in scalar"}
            for i in range(7142)
        ]
        resp = build_job_response(
            total=1000, marked=12, errors=errors, sample_size=10,
        )
        # The response MUST now explain the 7142 errors
        assert resp["errors"] == 7142
        assert resp["success"] is False
        assert len(resp["sampleErrors"]) == 1  # all same message
        assert resp["sampleErrors"][0]["count"] == 7142
        assert "cannot set path in scalar" in resp["sampleErrors"][0]["error"]
