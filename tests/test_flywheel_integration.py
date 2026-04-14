"""Flywheel integration test — full loop from ticket to curriculum refresh.

Tests the compounding loop end-to-end:
  file_ticket() → record_survived() → CSR updated → week report → curriculum_refresh()

All file I/O uses tmp_path. No external dependencies.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def brain(tmp_path):
    """Create a minimal .brain directory for flywheel tests."""
    b = tmp_path / ".brain"
    b.mkdir(exist_ok=True)
    return b


class TestFlywheelFullLoop:
    """End-to-end: ticket → CSR bump → survived → curriculum promotion."""

    def test_file_ticket_creates_all_artifacts(self, brain):
        """file_ticket() should fire all 6 actions and create expected files."""
        from mcp_server_nucleus.flywheel import Flywheel

        fw = Flywheel(brain)
        report = fw.file_ticket(
            step="deploy_server",
            error="ConnectionRefused on port 8080",
            logs="Traceback (most recent call last):\n  ...",
            phase="ground_tier4",
        )

        assert report["ticket_id"].startswith("fw-")
        assert report["step"] == "deploy_server"
        actions = report["actions"]

        # Actions 1,2,3,4,6 should succeed (5=gh issue is queued offline)
        assert actions["memory_note"] == "ok"
        assert actions["csr_bump"] == "ok"
        assert actions["training_pair"] == "ok"
        assert actions["week_report"] == "ok"
        assert actions["task_register"] == "ok"
        assert "queued" in actions["github_issue"]

        # Verify files on disk
        fw_dir = brain / "flywheel"
        assert fw_dir.exists()
        assert (fw_dir / "pending_issues.jsonl").exists()
        assert (fw_dir / "pending_tasks.jsonl").exists()
        assert (fw_dir / "gh_issue_queue.jsonl").exists()

        # Verify pending_issues.jsonl content
        issues = (fw_dir / "pending_issues.jsonl").read_text().strip().splitlines()
        assert len(issues) == 1
        issue = json.loads(issues[0])
        assert issue["step"] == "deploy_server"
        assert issue["error"] == "ConnectionRefused on port 8080"

        # Verify training pair seeded
        dpo_path = brain / "training" / "exports" / "unified_dpo_pending.jsonl"
        assert dpo_path.exists()
        pairs = dpo_path.read_text().strip().splitlines()
        assert len(pairs) == 1
        pair = json.loads(pairs[0])
        assert pair["quality"] == "pending"
        assert pair["rejected"] == "ConnectionRefused on port 8080"
        assert pair["chosen"] == ""  # not yet filled

    def test_csr_tracks_survived_and_unsurvived(self, brain):
        """CSR ratio should reflect survived vs unsurvived claims."""
        from mcp_server_nucleus.flywheel import Flywheel

        fw = Flywheel(brain)

        # Initial state: 1/1 (founding claim)
        csr = fw.csr()
        assert csr["claims_total"] == 1
        assert csr["claims_survived"] == 1
        assert csr["ratio"] == 1.0

        # File a ticket (adds 1 unsurvived)
        fw.file_ticket(step="step_a", error="failed", phase="test")
        csr = fw.csr()
        assert csr["claims_total"] == 2
        assert csr["claims_unsurvived"] == 1
        assert csr["ratio"] == 0.5

        # Record 2 survived claims
        fw.record_survived(phase="test", step="step_b")
        fw.record_survived(phase="test", step="step_c")
        csr = fw.csr()
        assert csr["claims_total"] == 4
        assert csr["claims_survived"] == 3
        assert csr["claims_unsurvived"] == 1
        assert csr["ratio"] == 0.75

    def test_week_report_generated(self, brain):
        """generate_week_report() should produce a markdown file with CSR data."""
        from mcp_server_nucleus.flywheel import Flywheel, generate_week_report

        fw = Flywheel(brain)
        fw.file_ticket(step="auth_login", error="401 Unauthorized", phase="test")
        fw.record_survived(phase="test", step="auth_signup")

        report_path = generate_week_report(brain)
        assert report_path.exists()
        assert report_path.suffix == ".md"

        content = report_path.read_text()
        assert "## CSR" in content
        assert "Claims total" in content
        assert "## Tickets" in content

    def test_curriculum_refresh_promotes_fixed_tickets(self, brain):
        """When a ticket's step later survives, curriculum_refresh promotes the DPO pair."""
        from mcp_server_nucleus.flywheel import Flywheel, curriculum_refresh

        fw = Flywheel(brain)

        # File a ticket for step "deploy_server"
        fw.file_ticket(step="deploy_server", error="port conflict", phase="ground")

        # Verify the pending pair exists
        pending_path = brain / "training" / "exports" / "unified_dpo_pending.jsonl"
        assert pending_path.exists()
        pending_before = pending_path.read_text().strip().splitlines()
        assert len(pending_before) == 1

        # Now the same step survives
        fw.record_survived(phase="ground", step="deploy_server")

        # Run curriculum refresh
        result = curriculum_refresh(brain)
        assert result["scanned"] == 1
        assert result["ready"] == 1
        assert result["still_pending"] == 0

        # The ready file should exist with the promoted pair
        ready_path = brain / "training" / "exports" / "unified_dpo_ready.jsonl"
        assert ready_path.exists()
        ready_lines = ready_path.read_text().strip().splitlines()
        assert len(ready_lines) == 1
        pair = json.loads(ready_lines[0])
        assert pair["quality"] == "curriculum"
        assert "deploy_server" in pair["chosen"]
        assert pair["rejected"] == "port conflict"

    def test_curriculum_refresh_leaves_unfixed_pending(self, brain):
        """Tickets whose step never survived stay in pending."""
        from mcp_server_nucleus.flywheel import Flywheel, curriculum_refresh

        fw = Flywheel(brain)
        fw.file_ticket(step="broken_step", error="still broken", phase="test")

        # Survive a DIFFERENT step
        fw.record_survived(phase="test", step="other_step")

        result = curriculum_refresh(brain)
        assert result["scanned"] == 1
        assert result["ready"] == 0
        assert result["still_pending"] == 1

    def test_multiple_tickets_partial_promotion(self, brain):
        """Multiple tickets, only the fixed ones get promoted."""
        from mcp_server_nucleus.flywheel import Flywheel, curriculum_refresh

        fw = Flywheel(brain)
        fw.file_ticket(step="step_a", error="error a", phase="p1")
        fw.file_ticket(step="step_b", error="error b", phase="p2")
        fw.file_ticket(step="step_c", error="error c", phase="p3")

        # Only step_a and step_c survive
        fw.record_survived(phase="p1", step="step_a")
        fw.record_survived(phase="p3", step="step_c")

        result = curriculum_refresh(brain)
        assert result["scanned"] == 3
        assert result["ready"] == 2
        assert result["still_pending"] == 1

        # Pending should only contain step_b
        pending_path = brain / "training" / "exports" / "unified_dpo_pending.jsonl"
        remaining = [json.loads(l) for l in pending_path.read_text().strip().splitlines()]
        assert len(remaining) == 1
        assert "step_b" in remaining[0]["prompt"]
