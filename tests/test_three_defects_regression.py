"""Regression tests for three defects fixed in mcp-server-nucleus.

(a) pulse_and_polish.py imports capture_pulse from runtime/pulse — the name
    must exist so the pulse step runs instead of being skipped on ImportError.
(b) nucleus_slots slot sorting must not throw TypeError on mixed-type
    priorities (str vs int).  Both _brain_status_dashboard_impl and
    _brain_autopilot_sprint_impl sort by priority and must normalise to int.
(c) Flywheel._try_gh_issue must not shell out to a real ``gh issue create``
    when running under pytest (PYTEST_CURRENT_TEST set) or NUCLEUS_TEST=1 —
    it should only queue to gh_issue_queue.jsonl.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Defect (a) — capture_pulse importable from runtime.pulse
# ═══════════════════════════════════════════════════════════════════════════

class TestCapturePulseImportable:
    """capture_pulse must exist in runtime.pulse so that
    god_combos.pulse_and_polish can import it without ImportError."""

    def test_capture_pulse_exists_in_pulse_module(self):
        from mcp_server_nucleus.runtime.pulse import capture_pulse
        assert callable(capture_pulse)

    def test_get_pulse_store_exists_in_pulse_module(self):
        from mcp_server_nucleus.runtime.pulse import get_pulse_store
        assert callable(get_pulse_store)

    def test_pulse_and_polish_imports_succeed(self):
        """The exact import line used by pulse_and_polish.py must work."""
        from mcp_server_nucleus.runtime.pulse import capture_pulse, get_pulse_store
        # Both must be callable — ImportError would have been raised above
        assert capture_pulse is not None
        assert get_pulse_store is not None

    def test_pulse_and_polish_step_runs(self, tmp_path, monkeypatch):
        """run_pulse_and_polish should not skip the pulse step with an
        ImportError — the step should run (ok or skipped-with-reason, but
        NOT because capture_pulse doesn't exist)."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import (
            run_pulse_and_polish,
        )
        result = run_pulse_and_polish(write_engram=False)
        pulse_step = next(
            (s for s in result["steps"] if s["name"] == "pulse"), None
        )
        assert pulse_step is not None, "pulse step should exist in results"
        # The reason must NOT mention ImportError or capture_pulse
        reason = pulse_step.get("reason", "")
        assert "capture_pulse" not in reason
        assert "ImportError" not in reason
        assert "cannot import" not in reason.lower()


# ═══════════════════════════════════════════════════════════════════════════
# Defect (b) — mixed-type priority sorting in slot_ops
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / ".brain"
    for sub in ["ledger", "slots", "protocols", "config", "artifacts"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


@pytest.fixture
def tier_defs():
    return {
        "tiers": {
            "heavy": {"level": 1, "models": ["gpt-4"]},
            "standard": {"level": 2, "models": ["gpt-3.5-turbo"]},
            "light": {"level": 3, "models": ["llama-7b"]},
        },
        "tier_priority_mapping": {"1": "heavy", "2": "standard", "3": "standard"},
        "model_costs": {"gpt_4": 0.03, "gpt_3.5_turbo": 0.002, "llama_7b": 0.001},
    }


@pytest.fixture
def tier_defs_file(brain, tier_defs):
    (brain / "protocols" / "tiers.json").write_text(json.dumps(tier_defs))
    return tier_defs


@pytest.fixture
def slot_registry(brain):
    reg = {
        "slots": {
            "slot_a": {
                "id": "slot_a", "tier": "standard", "status": "active",
                "model": "gpt-3.5-turbo", "current_task": None,
                "capabilities": ["python"], "success_rate": 1.0,
            },
        },
        "aliases": {},
    }
    (brain / "slots" / "registry.json").write_text(json.dumps(reg))
    return reg


def _add_tasks(brain, tasks):
    (brain / "config").mkdir(exist_ok=True)
    (brain / "config" / "nucleus.yaml").write_text("storage:\n  backend: json\n")
    (brain / "ledger" / "tasks.json").write_text(json.dumps(tasks))


class TestStatusDashboardMixedPriority:
    """_brain_status_dashboard_impl must not throw TypeError when tasks
    have mixed-type priorities (str and int)."""

    def test_dashboard_mixed_priorities(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING", "priority": 1},
            {"id": "t2", "description": "Task 2", "status": "PENDING", "priority": "3"},
            {"id": "t3", "description": "Task 3", "status": "PENDING", "priority": "high"},
            {"id": "t4", "description": "Task 4", "status": "PENDING", "priority": 2},
        ])
        # Must not raise TypeError
        result = _brain_status_dashboard_impl()
        assert "NUCLEUS CONTROL PLANE" in result
        assert "Pending: 4" in result


class TestAutopilotSprintMixedPriority:
    """_brain_autopilot_sprint_impl must not throw TypeError when tasks
    have mixed-type priorities (str and int)."""

    def test_sprint_mixed_priorities(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING",
             "priority": 1, "blocked_by": [], "required_skills": []},
            {"id": "t2", "description": "Task 2", "status": "PENDING",
             "priority": "3", "blocked_by": [], "required_skills": []},
            {"id": "t3", "description": "Task 3", "status": "PENDING",
             "priority": "high", "blocked_by": [], "required_skills": []},
            {"id": "t4", "description": "Task 4", "status": "PENDING",
             "priority": 2, "blocked_by": [], "required_skills": []},
        ])
        # Must not raise TypeError
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        assert data["status"] in ("RUNNING", "PLANNED", "IDLE", "ALL_BLOCKED")


# ═══════════════════════════════════════════════════════════════════════════
# Defect (c) — _try_gh_issue skips real gh under test mode
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def fw_brain(tmp_path):
    b = tmp_path / ".brain"
    b.mkdir(exist_ok=True)
    return b


class TestTryGhIssueTestModeGuard:
    """_try_gh_issue must not call subprocess.run when PYTEST_CURRENT_TEST
    is set or NUCLEUS_TEST=1 — it should only queue to gh_issue_queue.jsonl."""

    def test_skips_gh_when_pytest_current_test_set(self, fw_brain, monkeypatch):
        """PYTEST_CURRENT_TEST is automatically set by pytest itself, but we
        set it explicitly to be deterministic."""
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_session::test_func (call)")

        # Track if subprocess.run is called
        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        from mcp_server_nucleus.flywheel import Flywheel
        fw = Flywheel(fw_brain)
        result = fw._try_gh_issue("test_step", "test error", "logs", "fw-test-1")

        assert "queued" in result
        assert "test mode" in result
        assert call_count["n"] == 0, "subprocess.run must not be called under PYTEST_CURRENT_TEST"

        # Verify the issue was queued
        queue_path = fw_brain / "flywheel" / "gh_issue_queue.jsonl"
        assert queue_path.exists()
        lines = queue_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["ticket_id"] == "fw-test-1"
        assert "test_step" in entry["title"]

    def test_skips_gh_when_nucleus_test_set(self, fw_brain, monkeypatch):
        # Ensure PYTEST_CURRENT_TEST doesn't interfere — clear it and set NUCLEUS_TEST
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("NUCLEUS_TEST", "1")

        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        from mcp_server_nucleus.flywheel import Flywheel
        fw = Flywheel(fw_brain)
        result = fw._try_gh_issue("step_x", "err", "", "fw-test-2")

        assert "queued" in result
        assert "test mode" in result
        assert call_count["n"] == 0, "subprocess.run must not be called when NUCLEUS_TEST=1"

    def test_calls_gh_when_no_test_env(self, fw_brain, monkeypatch):
        """When neither PYTEST_CURRENT_TEST nor NUCLEUS_TEST=1 is set, the
        real gh call path is taken (mocked here to avoid live GitHub)."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("NUCLEUS_TEST", raising=False)

        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            return subprocess.CompletedProcess(
                cmd, returncode=0,
                stdout="https://github.com/example/repo/issues/1\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        from mcp_server_nucleus.flywheel import Flywheel
        fw = Flywheel(fw_brain)
        result = fw._try_gh_issue("step_y", "err", "", "fw-test-3")

        assert result.startswith("ok:")
        assert call_count["n"] == 1, "subprocess.run should be called when no test env is set"

    def test_file_ticket_queues_without_subprocess(self, fw_brain, monkeypatch):
        """End-to-end: file_ticket under PYTEST_CURRENT_TEST should queue
        the gh issue without any subprocess call."""
        # PYTEST_CURRENT_TEST is already set by pytest, but set explicitly
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_session (call)")

        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        from mcp_server_nucleus.flywheel import Flywheel
        fw = Flywheel(fw_brain)
        report = fw.file_ticket(
            step="deploy_step",
            error="something broke",
            logs="traceback...",
            phase="test",
        )

        assert report["actions"]["github_issue"].startswith("queued")
        assert "test mode" in report["actions"]["github_issue"]
        assert call_count["n"] == 0, "no subprocess calls allowed under test mode"

        # Verify queue file has the entry
        queue_path = fw_brain / "flywheel" / "gh_issue_queue.jsonl"
        assert queue_path.exists()
        lines = queue_path.read_text().strip().splitlines()
        assert len(lines) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
