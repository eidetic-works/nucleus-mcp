"""Tests for KYC demo workflow."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def brain_dir():
    """Create a temporary brain directory for testing."""
    tmp = tempfile.mkdtemp(prefix="nucleus_test_kyc_")
    brain = Path(tmp) / ".brain"
    brain.mkdir()
    (brain / "dsor").mkdir()
    yield brain
    shutil.rmtree(tmp)


class TestKYCDemo:
    """Tests for KYC review workflow."""

    def test_review_low_risk_approved(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-001", brain_dir)

        assert result["recommendation"] == "APPROVE"
        assert result["risk_level"] == "LOW"
        assert result["risk_score"] == 0
        assert result["hitl_required"] is False
        assert result["hitl_request"] is None
        assert len(result["checks"]) == 5
        assert len(result["decision_trail"]) == 6
        assert all(c["status"] == "PASS" for c in result["checks"])

    def test_review_medium_risk_escalated(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-002", brain_dir)

        assert result["recommendation"] == "ESCALATE"
        assert result["risk_level"] == "MEDIUM"
        assert result["risk_score"] > 0
        assert result["hitl_required"] is True
        assert result["hitl_request"] is not None
        assert result["hitl_request"]["recommendation"] == "ESCALATE"

        # PEP check should flag
        pep_check = [c for c in result["checks"] if c["check"] == "pep"][0]
        assert pep_check["status"] == "FLAG"

    def test_review_high_risk_rejected(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-003", brain_dir)

        assert result["recommendation"] == "REJECT"
        assert result["risk_level"] == "HIGH"
        assert result["risk_score"] >= 100
        assert result["hitl_required"] is True

        # Sanctions check should fail
        sanctions_check = [c for c in result["checks"] if c["check"] == "sanctions"][0]
        assert sanctions_check["status"] == "FAIL"

    def test_review_unknown_application(self):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-999")
        assert "error" in result
        assert "Unknown application" in result["error"]

    def test_dsor_trace_written(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-001", brain_dir, write_dsor=True)

        dsor_file = brain_dir / "dsor" / f"{result['review_id']}.json"
        assert dsor_file.exists()

        trace = json.loads(dsor_file.read_text())
        assert trace["type"] == "KYC_REVIEW"
        assert trace["review_id"] == result["review_id"]
        assert trace["recommendation"] == "APPROVE"
        assert len(trace["decision_trail"]) == 6
        assert "sovereign_guarantee" in trace

    def test_dsor_not_written_when_disabled(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-001", brain_dir, write_dsor=False)

        dsor_file = brain_dir / "dsor" / f"{result['review_id']}.json"
        assert not dsor_file.exists()

    def test_format_kyc_review(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review, format_kyc_review
        result = run_kyc_review("APP-001", brain_dir)
        formatted = format_kyc_review(result)

        assert "KYC REVIEW RESULT" in formatted
        assert "AUTOMATED CHECKS" in formatted
        assert "DECISION TRAIL" in formatted
        assert "Sovereignty" in formatted
        assert "APPROVE" in formatted

    def test_format_kyc_review_with_hitl(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review, format_kyc_review
        result = run_kyc_review("APP-003", brain_dir)
        formatted = format_kyc_review(result)

        assert "HUMAN APPROVAL REQUIRED" in formatted
        assert "REJECT" in formatted

    def test_all_demo_applications_exist(self):
        from mcp_server_nucleus.runtime.kyc_demo import DEMO_APPLICATIONS
        assert "APP-001" in DEMO_APPLICATIONS
        assert "APP-002" in DEMO_APPLICATIONS
        assert "APP-003" in DEMO_APPLICATIONS

    def test_decision_trail_has_timestamps(self, brain_dir):
        from mcp_server_nucleus.runtime.kyc_demo import run_kyc_review
        result = run_kyc_review("APP-001", brain_dir)

        for step in result["decision_trail"]:
            assert "timestamp" in step
            assert "action" in step
            assert "result" in step
            assert "reasoning" in step

    def test_sanctions_check_logic(self):
        from mcp_server_nucleus.runtime.kyc_demo import _check_sanctions
        # UK should pass
        result = _check_sanctions({"nationality": "United Kingdom"})
        assert result["status"] == "PASS"
        assert result["risk_points"] == 0

        # Russia should fail
        result = _check_sanctions({"nationality": "Russia"})
        assert result["status"] == "FAIL"
        assert result["risk_points"] == 100

    def test_pep_check_logic(self):
        from mcp_server_nucleus.runtime.kyc_demo import _check_pep
        # Unknown person should pass
        result = _check_pep({"applicant": "Unknown Person"})
        assert result["status"] == "PASS"

        # Maria Rodriguez should flag
        result = _check_pep({"applicant": "Maria Rodriguez"})
        assert result["status"] == "FLAG"
        assert result["risk_points"] > 0
