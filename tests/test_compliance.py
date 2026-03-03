"""Tests for compliance_config and audit_report modules."""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def brain_dir():
    """Create a temporary brain directory for testing."""
    tmp = tempfile.mkdtemp(prefix="nucleus_test_brain_")
    brain = Path(tmp) / ".brain"
    brain.mkdir()
    # Create directories
    (brain / "ledger").mkdir()
    (brain / "engrams").mkdir()
    (brain / "governance").mkdir()
    yield brain
    shutil.rmtree(tmp)


@pytest.fixture
def brain_with_data(brain_dir):
    """Create a brain with sample data."""
    # Write some events
    events_file = brain_dir / "ledger" / "events.jsonl"
    events = [
        {"event_type": "TaskClaimed", "timestamp": "2026-01-01T10:00:00Z", "emitter": "agent-1", "description": "Claimed task T001"},
        {"event_type": "DecisionMade", "timestamp": "2026-01-01T11:00:00Z", "emitter": "agent-1", "description": "Decided to use Python", "data": {"decision": "Python"}},
        {"event_type": "HITLApproval", "timestamp": "2026-01-01T12:00:00Z", "emitter": "human", "description": "Approved deployment", "data": {"approved": True}},
    ]
    with open(events_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Write some engrams
    engram_file = brain_dir / "engrams" / "test_engram.json"
    with open(engram_file, "w") as f:
        json.dump({
            "key": "python-choice",
            "value": "Python was chosen for backend because of Flask ecosystem",
            "context": "Decision",
            "intensity": 7,
            "created_at": "2026-01-01T11:00:00Z",
        }, f)

    return brain_dir


# ============================================================
# COMPLIANCE CONFIG TESTS
# ============================================================


class TestComplianceConfig:
    """Tests for compliance_config module."""

    def test_list_jurisdictions(self):
        from mcp_server_nucleus.runtime.compliance_config import list_jurisdictions
        result = list_jurisdictions()
        assert "eu-dora" in result
        assert "sg-mas-trm" in result
        assert "us-soc2" in result
        assert "global-default" in result
        assert len(result) == 4

    def test_get_jurisdiction_known(self):
        from mcp_server_nucleus.runtime.compliance_config import get_jurisdiction
        result = get_jurisdiction("eu-dora")
        assert result is not None
        assert result["name"] == "EU DORA (Digital Operational Resilience Act)"
        assert result["region"] == "European Union"
        assert result["requirements"]["data_residency"] is True

    def test_get_jurisdiction_unknown(self):
        from mcp_server_nucleus.runtime.compliance_config import get_jurisdiction
        result = get_jurisdiction("unknown-jurisdiction")
        assert result is None

    def test_apply_jurisdiction_eu_dora(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import apply_jurisdiction
        result = apply_jurisdiction(brain_dir, "eu-dora")

        assert result["status"] == "applied"
        assert result["jurisdiction"] == "eu-dora"
        assert result["name"] == "EU DORA (Digital Operational Resilience Act)"
        assert result["region"] == "European Union"

        # Check files were written
        assert len(result["files_written"]) == 3
        for f_path in result["files_written"]:
            assert Path(f_path).exists()

        # Check compliance.json content
        compliance = json.loads((brain_dir / "governance" / "compliance.json").read_text())
        assert compliance["jurisdiction"] == "eu-dora"
        assert compliance["requirements"]["audit_trail_retention_days"] == 2555

        # Check hitl_policy.json content
        hitl = json.loads((brain_dir / "governance" / "hitl_policy.json").read_text())
        assert len(hitl["hitl_required_for"]) == 5
        assert hitl["max_autonomous_actions"] == 3

        # Check audit_policy.json content
        audit = json.loads((brain_dir / "governance" / "audit_policy.json").read_text())
        assert audit["retention_days"] == 2555
        assert audit["dsor_format"] == "eu-dora-v1"

    def test_apply_jurisdiction_sg_mas_trm(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import apply_jurisdiction
        result = apply_jurisdiction(brain_dir, "sg-mas-trm")

        assert result["status"] == "applied"
        assert result["jurisdiction"] == "sg-mas-trm"
        assert result["key_requirements"]["max_autonomous_actions"] == 2  # Stricter than DORA

    def test_apply_jurisdiction_us_soc2(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import apply_jurisdiction
        result = apply_jurisdiction(brain_dir, "us-soc2")

        assert result["status"] == "applied"
        assert result["key_requirements"]["data_residency"] is False
        assert result["key_requirements"]["max_autonomous_actions"] == 5

    def test_apply_jurisdiction_unknown(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import apply_jurisdiction
        result = apply_jurisdiction(brain_dir, "unknown")
        assert "error" in result
        assert "Unknown jurisdiction" in result["error"]

    def test_generate_compliance_report_no_jurisdiction(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import generate_compliance_report
        report = generate_compliance_report(brain_dir)

        assert report["status"] in ("non_compliant", "partially_compliant")
        assert "No jurisdiction configured" in str(report["issues"])

    def test_generate_compliance_report_with_jurisdiction(self, brain_with_data):
        from mcp_server_nucleus.runtime.compliance_config import (
            apply_jurisdiction,
            generate_compliance_report,
        )
        apply_jurisdiction(brain_with_data, "eu-dora")
        report = generate_compliance_report(brain_with_data)

        assert report["checks"]["jurisdiction"]["status"] == "configured"
        assert report["checks"]["hitl_policy"]["status"] == "active"
        assert report["checks"]["memory"]["engram_count"] == 1

    def test_format_compliance_report(self, brain_dir):
        from mcp_server_nucleus.runtime.compliance_config import (
            generate_compliance_report,
            format_compliance_report,
        )
        report = generate_compliance_report(brain_dir)
        formatted = format_compliance_report(report)

        assert "NUCLEUS COMPLIANCE REPORT" in formatted
        assert "CHECKS:" in formatted

    def test_dora_specific_requirements(self):
        from mcp_server_nucleus.runtime.compliance_config import get_jurisdiction
        dora = get_jurisdiction("eu-dora")
        reqs = dora["requirements"]

        assert reqs["incident_reporting_hours"] == 4
        assert reqs["kill_switch_required"] is True
        assert reqs["testing_frequency"] == "annual"
        assert "financial_transactions" in reqs["hitl_required_for"]

    def test_mas_trm_specific_requirements(self):
        from mcp_server_nucleus.runtime.compliance_config import get_jurisdiction
        mas = get_jurisdiction("sg-mas-trm")
        reqs = mas["requirements"]

        assert reqs["incident_reporting_hours"] == 1  # Stricter than DORA
        assert reqs["audit_trail_retention_days"] == 1825  # 5 years
        assert "credit_decisions" in reqs["hitl_required_for"]


# ============================================================
# AUDIT REPORT TESTS
# ============================================================


class TestAuditReport:
    """Tests for audit_report module."""

    def test_generate_audit_report_empty_brain(self, brain_dir):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_dir)

        assert report["title"] == "Nucleus Agent OS — Audit Trail Report"
        assert "decisions" in report["sections"]
        assert "events" in report["sections"]
        assert "approvals" in report["sections"]
        assert "compliance_checklist" in report["sections"]
        assert "formatted" in report

    def test_generate_audit_report_with_data(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data)

        assert report["sections"]["decisions"]["count"] == 1
        assert report["sections"]["events"]["count"] == 3
        assert report["sections"]["approvals"]["count"] == 1
        assert report["sections"]["memory_context"]["count"] == 1

    def test_generate_audit_report_text_format(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data, report_format="text")

        formatted = report["formatted"]
        assert "AUDIT TRAIL REPORT" in formatted
        assert "DECISIONS" in formatted
        assert "EVENTS" in formatted
        assert "COMPLIANCE CHECKLIST" in formatted
        assert "sovereignty" in formatted.lower()

    def test_generate_audit_report_json_format(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data, report_format="json")

        formatted = report["formatted"]
        parsed = json.loads(formatted)
        assert parsed["title"] == "Nucleus Agent OS — Audit Trail Report"

    def test_generate_audit_report_html_format(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data, report_format="html")

        formatted = report["formatted"]
        assert "<!DOCTYPE html>" in formatted
        assert "Nucleus Audit Report" in formatted
        assert "Sovereignty Guarantee" in formatted

    def test_audit_report_with_jurisdiction(self, brain_with_data):
        from mcp_server_nucleus.runtime.compliance_config import apply_jurisdiction
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report

        apply_jurisdiction(brain_with_data, "sg-mas-trm")
        report = generate_audit_report(brain_with_data)

        assert report["jurisdiction"]["id"] == "sg-mas-trm"
        assert report["jurisdiction"]["name"] == "Singapore MAS TRM (Technology Risk Management)"

    def test_compliance_checklist_with_data(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data)

        checklist = report["sections"]["compliance_checklist"]
        assert checklist["passed"] >= 2  # At minimum: events + sovereignty
        assert checklist["total"] == 5

    def test_audit_report_includes_engrams(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data, include_engrams=True)

        memory = report["sections"]["memory_context"]
        assert memory["count"] == 1
        assert memory["records"][0]["key"] == "python-choice"
        assert memory["records"][0]["intensity"] == 7

    def test_audit_report_excludes_engrams(self, brain_with_data):
        from mcp_server_nucleus.runtime.audit_report import generate_audit_report
        report = generate_audit_report(brain_with_data, include_engrams=False)

        assert "memory_context" not in report["sections"]
