"""Comprehensive tests for proposals module."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.proposals import (
    Proposal,
    ProposalOps,
)


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a temporary brain path."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "ledger").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


# ── Proposal dataclass ───────────────────────────────────────────

class TestProposal:
    def test_defaults(self):
        p = Proposal(
            id="prop_1",
            title="Test",
            description="A test proposal",
            options=[{"id": "A", "desc": "Do X"}],
            risk_level="medium",
            created_at="2024-01-01T00:00:00",
        )
        assert p.id == "prop_1"
        assert p.title == "Test"
        assert p.status == "pending"
        assert p.ratified_option_id is None

    def test_with_status(self):
        p = Proposal(
            id="prop_1",
            title="Test",
            description="desc",
            options=[],
            risk_level="low",
            created_at="2024-01-01",
            status="ratified",
            ratified_option_id="A",
        )
        assert p.status == "ratified"
        assert p.ratified_option_id == "A"


# ── ProposalOps ──────────────────────────────────────────────────

class TestProposalOps:
    def test_init_creates_dir(self, brain_path):
        ops = ProposalOps(brain_path)
        assert ops.proposals_dir.exists()
        assert ops.proposals_dir == brain_path / "ledger" / "proposals"

    # ── generate_proposal ──────────────────────────────────────

    def test_generate_proposal(self, brain_path):
        ops = ProposalOps(brain_path)
        proposal = ops.generate_proposal(
            title="Deploy to prod",
            description="Should we deploy?",
            options=[{"id": "A", "desc": "Yes"}, {"id": "B", "desc": "No"}],
            risk_level="high",
        )
        assert proposal.id.startswith("prop_")
        assert proposal.title == "Deploy to prod"
        assert proposal.description == "Should we deploy?"
        assert len(proposal.options) == 2
        assert proposal.risk_level == "high"
        assert proposal.status == "pending"
        # File should be saved
        files = list(ops.proposals_dir.glob("prop_*.json"))
        assert len(files) == 1

    def test_generate_proposal_default_risk(self, brain_path):
        ops = ProposalOps(brain_path)
        proposal = ops.generate_proposal("T", "D", [{"id": "A", "desc": "X"}])
        assert proposal.risk_level == "medium"

    def test_generate_multiple_proposals(self, brain_path):
        ops = ProposalOps(brain_path)
        p1 = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        # Add small delay to ensure different timestamp
        import time
        time.sleep(1.1)
        p2 = ops.generate_proposal("T2", "D2", [{"id": "A", "desc": "Y"}])
        assert p1.id != p2.id
        files = list(ops.proposals_dir.glob("prop_*.json"))
        assert len(files) == 2

    # ── get_pending_proposals ──────────────────────────────────

    def test_get_pending_empty(self, brain_path):
        ops = ProposalOps(brain_path)
        assert ops.get_pending_proposals() == []

    def test_get_pending_proposals(self, brain_path):
        ops = ProposalOps(brain_path)
        ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        import time
        time.sleep(1.1)
        ops.generate_proposal("T2", "D2", [{"id": "A", "desc": "Y"}])
        pending = ops.get_pending_proposals()
        assert len(pending) == 2
        assert all(p.status == "pending" for p in pending)

    def test_get_pending_excludes_non_pending(self, brain_path):
        ops = ProposalOps(brain_path)
        p = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        ops.ratify_proposal(p.id, "A")
        pending = ops.get_pending_proposals()
        assert len(pending) == 0

    def test_get_pending_skips_corrupt_file(self, brain_path):
        ops = ProposalOps(brain_path)
        ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        # Write a corrupt file
        (ops.proposals_dir / "prop_corrupt.json").write_text("not valid json{{{")
        pending = ops.get_pending_proposals()
        assert len(pending) == 1  # Only the valid one

    def test_get_pending_dir_not_exists(self, brain_path):
        ops = ProposalOps(brain_path)
        # Remove the directory
        import shutil
        shutil.rmtree(ops.proposals_dir)
        assert ops.get_pending_proposals() == []

    # ── ratify_proposal ────────────────────────────────────────

    def test_ratify_proposal(self, brain_path):
        ops = ProposalOps(brain_path)
        p = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}, {"id": "B", "desc": "Y"}])
        result = ops.ratify_proposal(p.id, "A")
        assert result is True
        # Verify saved state
        data = json.loads((ops.proposals_dir / f"{p.id}.json").read_text())
        assert data["status"] == "ratified"
        assert data["ratified_option_id"] == "A"
        assert "ratified_at" in data

    def test_ratify_proposal_not_found(self, brain_path):
        ops = ProposalOps(brain_path)
        result = ops.ratify_proposal("nonexistent", "A")
        assert result is False

    def test_ratify_proposal_already_ratified(self, brain_path):
        ops = ProposalOps(brain_path)
        p = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        ops.ratify_proposal(p.id, "A")
        # Try to ratify again
        result = ops.ratify_proposal(p.id, "A")
        assert result is False

    def test_ratify_proposal_invalid_option(self, brain_path):
        ops = ProposalOps(brain_path)
        p = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        result = ops.ratify_proposal(p.id, "Z")
        assert result is False

    def test_ratify_proposal_rejected_status(self, brain_path):
        ops = ProposalOps(brain_path)
        p = ops.generate_proposal("T1", "D1", [{"id": "A", "desc": "X"}])
        # Manually set status to rejected
        file_path = ops.proposals_dir / f"{p.id}.json"
        data = json.loads(file_path.read_text())
        data["status"] = "rejected"
        file_path.write_text(json.dumps(data))
        result = ops.ratify_proposal(p.id, "A")
        assert result is False
