"""Tests for sovereign_status module."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def brain_dir():
    """Create a temporary brain directory for testing."""
    tmp = tempfile.mkdtemp(prefix="nucleus_test_sovereign_")
    brain = Path(tmp) / ".brain"
    brain.mkdir()
    (brain / "engrams").mkdir()
    (brain / "governance").mkdir()
    (brain / "dsor").mkdir()
    (brain / "ledger").mkdir()
    yield brain
    shutil.rmtree(tmp)


@pytest.fixture
def full_brain(brain_dir):
    """Create a fully configured brain with all components."""
    # State file
    state = {"created_at": "2026-01-01T00:00:00Z", "brain_id": "test-brain", "version": "1.3.0"}
    (brain_dir / "state.json").write_text(json.dumps(state))

    # Engrams
    for i in range(5):
        engram = {
            "key": f"engram-{i}",
            "value": f"Test engram {i}",
            "context": ["Feature", "Decision", "Architecture"][i % 3],
            "intensity": i * 2 + 1,
            "created_at": f"2026-01-0{i+1}T00:00:00Z",
        }
        (brain_dir / "engrams" / f"engram_{i}.json").write_text(json.dumps(engram))

    # Compliance config
    compliance = {
        "jurisdiction": "eu-dora",
        "name": "EU DORA",
        "region": "European Union",
        "applied_at": "2026-01-01T00:00:00Z",
        "requirements": {
            "data_residency": True,
            "kill_switch_required": True,
            "audit_trail_retention_days": 2555,
        },
    }
    (brain_dir / "governance" / "compliance.json").write_text(json.dumps(compliance))

    # HITL policy
    hitl = {
        "hitl_required_for": ["financial_transactions", "customer_data_access"],
        "max_autonomous_actions": 3,
        "blocked_operations": ["delete_customer_data"],
        "required_approvals": {"production_deployment": "senior_engineer"},
    }
    (brain_dir / "governance" / "hitl_policy.json").write_text(json.dumps(hitl))

    # DSoR traces
    dsor = {"type": "KYC_REVIEW", "review_id": "KYC-TEST", "recommendation": "APPROVE"}
    (brain_dir / "dsor" / "KYC-TEST.json").write_text(json.dumps(dsor))

    # Events
    events = [
        {"event_type": "TaskClaimed", "timestamp": "2026-01-01T10:00:00Z"},
        {"event_type": "DecisionMade", "timestamp": "2026-01-01T11:00:00Z"},
    ]
    with open(brain_dir / "ledger" / "events.jsonl", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    return brain_dir


class TestSovereignStatus:
    """Tests for sovereign status report."""

    def test_generate_basic_report(self, brain_dir):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(brain_dir)

        assert "generated_at" in report
        assert "sections" in report
        assert "sovereignty_score" in report
        assert "identity" in report["sections"]
        assert "memory" in report["sections"]
        assert "governance" in report["sections"]
        assert "dsor" in report["sections"]
        assert "residency" in report["sections"]
        assert "system" in report["sections"]

    def test_full_brain_high_score(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(full_brain)

        # Should have high score with all components configured
        assert report["sovereignty_score"] >= 80

    def test_empty_brain_low_score(self, brain_dir):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(brain_dir)

        # Empty brain with no engrams, no governance = lower score
        assert report["sovereignty_score"] <= 40

    def test_brain_identity(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(full_brain)

        identity = report["sections"]["identity"]
        assert identity["exists"] is True
        assert identity["total_files"] > 0
        assert identity["total_size_bytes"] > 0

    def test_memory_health(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(full_brain)

        memory = report["sections"]["memory"]
        assert memory["status"] == "operational"
        assert memory["engram_count"] == 5
        assert len(memory["contexts"]) > 0

    def test_governance_posture(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(full_brain)

        gov = report["sections"]["governance"]
        assert gov["jurisdiction"] == "eu-dora"
        assert gov["hitl_active"] is True
        assert gov["kill_switch"] is True

    def test_dsor_integrity(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(full_brain)

        dsor = report["sections"]["dsor"]
        assert dsor["status"] == "operational"
        assert dsor["decision_count"] >= 1
        assert dsor["event_count"] >= 2

    def test_data_residency_always_sovereign(self, brain_dir):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(brain_dir)

        residency = report["sections"]["residency"]
        assert residency["status"] == "sovereign"
        assert len(residency["guarantees"]) >= 3

    def test_format_report(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import (
            generate_sovereign_status,
            format_sovereign_status,
        )
        report = generate_sovereign_status(full_brain)
        formatted = format_sovereign_status(report)

        assert "NUCLEUS — SOVEREIGN AGENT OS" in formatted
        assert "Sovereignty Score" in formatted
        assert "BRAIN IDENTITY" in formatted
        assert "GOVERNANCE" in formatted
        assert "DATA RESIDENCY" in formatted

    def test_system_info(self, brain_dir):
        from mcp_server_nucleus.runtime.sovereign_status import generate_sovereign_status
        report = generate_sovereign_status(brain_dir)

        sys_info = report["sections"]["system"]
        assert "os" in sys_info
        assert "python" in sys_info
        assert "nucleus_version" in sys_info

    def test_score_calculation(self, full_brain):
        from mcp_server_nucleus.runtime.sovereign_status import (
            generate_sovereign_status,
            _calculate_score,
        )
        report = generate_sovereign_status(full_brain)
        score = _calculate_score(report["sections"])

        # Full brain should have: identity(20) + memory(20) + gov(25) + dsor(20) + residency(15) = 100
        assert score == 100
