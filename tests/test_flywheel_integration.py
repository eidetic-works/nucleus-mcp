"""Flywheel integration test — full loop from ticket to curriculum refresh.

Tests the compounding loop end-to-end:
  file_ticket() → record_survived() → CSR updated → week report → curriculum_refresh()

All file I/O uses tmp_path. No external dependencies.
"""

import json
import subprocess
import pytest
from pathlib import Path


@pytest.fixture
def brain(tmp_path):
    """Create a minimal .brain directory for flywheel tests."""
    b = tmp_path / ".brain"
    b.mkdir(exist_ok=True)
    return b


@pytest.fixture(autouse=True)
def no_live_gh(monkeypatch):
    """Never let flywheel tests shell out to a real `gh` — they must not
    create or touch live GitHub issues regardless of local `gh` auth state."""

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="https://github.com/example/repo/issues/1\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


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

        # Actions 1,2,3,4,6 should succeed; 5=gh issue is queued, not filed —
        # the test-context guard in _try_gh_issue (PYTEST_CURRENT_TEST is set
        # by pytest) skips the real gh call and only writes to the queue.
        assert actions["memory_note"] == "ok"
        assert actions["csr_bump"] == "ok"
        assert actions["training_pair"] == "ok"
        assert actions["week_report"] == "ok"
        assert actions["task_register"] == "ok"
        assert actions["github_issue"].startswith("queued:")

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

        # Now the same step survives end-to-end (task_outcome is in the
        # curriculum promotion allowlist; sub-phase claims are filtered)
        fw.record_survived(phase="task_outcome", step="deploy_server")

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

        # Only step_a and step_c survive end-to-end (task_outcome — see above)
        fw.record_survived(phase="task_outcome", step="step_a")
        fw.record_survived(phase="task_outcome", step="step_c")

        result = curriculum_refresh(brain)
        assert result["scanned"] == 3
        assert result["ready"] == 2
        assert result["still_pending"] == 1

        # Pending should only contain step_b
        pending_path = brain / "training" / "exports" / "unified_dpo_pending.jsonl"
        remaining = [json.loads(l) for l in pending_path.read_text().strip().splitlines()]
        assert len(remaining) == 1
        assert "step_b" in remaining[0]["prompt"]


class TestTryGhIssueTestContextGuard:
    """Regression: _try_gh_issue must NOT shell out to `gh` under test contexts.

    Defect (fw-1786207260): the method called ``gh issue create``
    unconditionally. Test runs filed 20k+ spam GitHub issues before this
    guard. The fix: when ``PYTEST_CURRENT_TEST`` is set (pytest sets it
    automatically) or ``NUCLEUS_TEST=1`` is set, skip the real gh call and
    only queue to ``gh_issue_queue.jsonl``.

    These tests assert the guard fires at the production-code level — not
    merely that a test fixture intercepts the call. ``subprocess.run`` is
    replaced with a bomb that raises if invoked at all; the guard must
    prevent the call from ever being attempted.
    """

    @pytest.fixture
    def no_live_gh(self):
        """Override the module-level autouse fixture.

        The module-level ``no_live_gh`` fakes a *successful* gh call. Here we
        instead make ``subprocess.run`` raise if it is ever called — the
        test-context guard must short-circuit *before* the subprocess block.
        """
        import subprocess as _sp
        original_run = _sp.run

        def _bomb(*args, **kwargs):
            raise AssertionError(
                "subprocess.run was invoked under a test context — "
                "_try_gh_issue test-context guard did not fire"
            )

        _sp.run = _bomb
        yield
        _sp.run = original_run

    def test_no_subprocess_call_under_pytest(self, brain, monkeypatch):
        """PYTEST_CURRENT_TEST (set by pytest itself) suppresses the gh call."""
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_flywheel (call)")
        from mcp_server_nucleus.flywheel import Flywheel

        fw = Flywheel(brain)
        report = fw.file_ticket(step="step_a", error="boom", phase="p")

        gh = report["actions"]["github_issue"]
        assert gh.startswith("queued:")
        assert "test" in gh  # either "test mode" or "test context" wording

        queue_path = brain / "flywheel" / "gh_issue_queue.jsonl"
        assert queue_path.exists()
        entries = [json.loads(l) for l in queue_path.read_text().strip().splitlines()]
        assert len(entries) == 1
        assert entries[0]["title"].startswith("[flywheel] step_a")

    def test_no_subprocess_call_under_nucleus_test_env(self, brain, monkeypatch):
        """NUCLEUS_TEST=1 suppresses the gh call even without PYTEST_CURRENT_TEST."""
        monkeypatch.setenv("NUCLEUS_TEST", "1")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        from mcp_server_nucleus.flywheel import Flywheel

        fw = Flywheel(brain)
        report = fw.file_ticket(step="step_b", error="boom", phase="p")

        gh = report["actions"]["github_issue"]
        assert gh.startswith("queued:")
        assert "test" in gh  # either "test mode" or "test context" wording
        assert (brain / "flywheel" / "gh_issue_queue.jsonl").exists()


class TestTryGhIssueOutsideTestContext:
    """Companion to TestTryGhIssueTestContextGuard: verifies the guard does
    NOT fire outside a test context, so the real gh call path is still
    reached. Lives in a separate class so it inherits the module-level
    ``no_live_gh`` autouse fixture (fake-success subprocess.run) rather
    than the class-level bomb in the guard class."""

    def test_gh_call_proceeds_outside_test_context(self, brain, monkeypatch):
        """With neither test env var set, subprocess.run IS invoked."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("NUCLEUS_TEST", raising=False)
        from mcp_server_nucleus.flywheel import Flywheel

        fw = Flywheel(brain)
        report = fw.file_ticket(step="step_c", error="boom", phase="p")

        # Outside a test context the (faked) gh call fires and returns ok.
        assert report["actions"]["github_issue"].startswith("ok:")


class TestPendingIssuesHomePathScrub:
    """Regression: pending_issues.jsonl must not leak absolute home paths.

    Defect (flywheel triage REAL): file_ticket wrote error + logs verbatim —
    /Users/<name>/... paths leaked the operator's username into records that
    get filed to GitHub. The fix scrubs the home prefix to ~ at write time.
    """

    def test_error_and_logs_scrub_home_prefix(self, brain):
        import json
        import os
        from mcp_server_nucleus.flywheel import Flywheel

        home = os.path.expanduser("~")
        fw = Flywheel(brain)
        fw.file_ticket(
            step="scrub_test",
            error=f"failed at {home}/secret/project/x.py",
            logs=f"trace from {home}/another/dir",
            phase="p",
        )
        pending = brain / "flywheel" / "pending_issues.jsonl"
        rows = [json.loads(l) for l in pending.read_text().splitlines() if l.strip()]
        assert rows, "ticket row was not written"
        row = rows[-1]
        assert home not in row["error"], "absolute home path leaked into error"
        assert home not in row["logs"], "absolute home path leaked into logs"
        assert "~/" in row["error"] or "~" in row["error"]
