"""Tests for the pending_issues closure signal (fw-1786151012).

Verifies that list_pending_tickets cross-references csr.json and
fix_description to annotate each ticket with a closure_status field,
so fixed/survived tickets can be filtered out of the actionable backlog.
"""
import json
import sys
import pytest
from pathlib import Path


@pytest.fixture
def fw_instance(tmp_path, monkeypatch):
    """Create a Flywheel instance with a temp brain."""
    brain = tmp_path / ".brain"
    fw_dir = brain / "flywheel"
    fw_dir.mkdir(parents=True)
    (fw_dir / "csr.json").write_text(json.dumps({
        "claims_total": 0,
        "claims_survived": 0,
        "claims_unsurvived": 0,
        "ratio": 0.0,
        "first_claim_at": "",
        "last_updated": "",
        "recent_claims": [],
    }))
    from mcp_server_nucleus.flywheel.core import Flywheel
    return Flywheel(brain_path=brain)


def _write_ticket(fw_dir, ticket_id, step, phase="", fix_description="", error="test"):
    """Append a ticket to pending_issues.jsonl."""
    with open(fw_dir / "pending_issues.jsonl", "a") as f:
        f.write(json.dumps({
            "ticket_id": ticket_id,
            "at": "2026-08-08T00:00:00+00:00",
            "step": step,
            "phase": phase,
            "error": error,
            "logs": "",
            "fix_description": fix_description,
        }) + "\n")


class TestListPendingTickets:
    def test_open_ticket_has_open_status(self, fw_instance):
        """A ticket with no fix_description and no survived claim → open."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-1001", "some_bug", phase="test_phase")
        tickets = fw_instance.list_pending_tickets()
        assert len(tickets) == 1
        assert tickets[0]["closure_status"] == "open"

    def test_fixed_ticket_has_fixed_status(self, fw_instance):
        """A ticket with fix_description → fixed."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-1002", "some_bug", phase="test_phase",
                      fix_description="Fixed in commit abc123")
        all_tickets = fw_instance.list_pending_tickets(include_closed=True)
        assert len(all_tickets) == 1
        assert all_tickets[0]["closure_status"] == "fixed"

    def test_fixed_ticket_filtered_by_default(self, fw_instance):
        """Fixed tickets are filtered out by default."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-1003", "some_bug", phase="test_phase",
                      fix_description="Fixed in commit abc123")
        open_tickets = fw_instance.list_pending_tickets()
        assert len(open_tickets) == 0

    def test_survived_ticket_has_survived_status(self, fw_instance):
        """A ticket matching a survived claim in csr.json → survived."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-1004", "some_bug", phase="test_phase")
        # Add a survived claim matching this ticket's label
        csr = json.loads((fw_instance.brain_path / "flywheel" / "csr.json").read_text())
        csr["recent_claims"].append({
            "at": "2026-08-08T00:00:00+00:00",
            "step": "test_phase:some_bug",
            "survived": True,
        })
        (fw_instance.brain_path / "flywheel" / "csr.json").write_text(json.dumps(csr))
        all_tickets = fw_instance.list_pending_tickets(include_closed=True)
        assert len(all_tickets) == 1
        assert all_tickets[0]["closure_status"] == "survived"

    def test_survived_ticket_filtered_by_default(self, fw_instance):
        """Survived tickets are filtered out by default."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-1005", "some_bug", phase="test_phase")
        csr = json.loads((fw_instance.brain_path / "flywheel" / "csr.json").read_text())
        csr["recent_claims"].append({
            "at": "2026-08-08T00:00:00+00:00",
            "step": "test_phase:some_bug",
            "survived": True,
        })
        (fw_instance.brain_path / "flywheel" / "csr.json").write_text(json.dumps(csr))
        open_tickets = fw_instance.list_pending_tickets()
        assert len(open_tickets) == 0

    def test_mixed_tickets(self, fw_instance):
        """A mix of open, fixed, and survived tickets."""
        fw_dir = fw_instance.brain_path / "flywheel"
        _write_ticket(fw_dir, "fw-open", "open_bug", phase="p1")
        _write_ticket(fw_dir, "fw-fixed", "fixed_bug", phase="p1",
                      fix_description="Fixed")
        _write_ticket(fw_dir, "fw-survived", "survived_bug", phase="p1")
        csr = json.loads((fw_instance.brain_path / "flywheel" / "csr.json").read_text())
        csr["recent_claims"].append({
            "at": "2026-08-08T00:00:00+00:00",
            "step": "p1:survived_bug",
            "survived": True,
        })
        (fw_instance.brain_path / "flywheel" / "csr.json").write_text(json.dumps(csr))
        # Default: only open
        open_tickets = fw_instance.list_pending_tickets()
        assert len(open_tickets) == 1
        assert open_tickets[0]["ticket_id"] == "fw-open"
        # Include all
        all_tickets = fw_instance.list_pending_tickets(include_closed=True)
        assert len(all_tickets) == 3
        statuses = {t["ticket_id"]: t["closure_status"] for t in all_tickets}
        assert statuses["fw-open"] == "open"
        assert statuses["fw-fixed"] == "fixed"
        assert statuses["fw-survived"] == "survived"

    def test_empty_backlog_returns_empty(self, fw_instance):
        """No pending_issues.jsonl → empty list."""
        tickets = fw_instance.list_pending_tickets()
        assert tickets == []

    def test_corrupt_lines_skipped(self, fw_instance):
        """Corrupt JSON lines are skipped, not crashed on."""
        fw_dir = fw_instance.brain_path / "flywheel"
        with open(fw_dir / "pending_issues.jsonl", "a") as f:
            f.write("not json\n")
            f.write(json.dumps({"ticket_id": "fw-good", "step": "bug", "phase": "p"}) + "\n")
        tickets = fw_instance.list_pending_tickets()
        assert len(tickets) == 1
        assert tickets[0]["ticket_id"] == "fw-good"
