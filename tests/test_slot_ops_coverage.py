"""Comprehensive coverage tests for runtime/slot_ops.py."""
import json
import time
from pathlib import Path

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
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
    """Write a slot registry with active and exhausted slots."""
    reg = {
        "slots": {
            "slot_a": {
                "id": "slot_a", "tier": "standard", "status": "active",
                "model": "gpt-3.5-turbo", "current_task": None,
                "capabilities": ["python"], "success_rate": 1.0
            },
            "slot_b": {
                "id": "slot_b", "tier": "heavy", "status": "active",
                "model": "gpt-4", "current_task": None,
                "capabilities": ["python", "rust"], "success_rate": 1.0
            },
            "slot_c": {
                "id": "slot_c", "tier": "light", "status": "exhausted",
                "model": "llama-7b", "current_task": None,
                "reset_at": "2026-01-20T00:00:00+0000"
            },
        },
        "aliases": {"alpha": "slot_a", "beta": "slot_b"}
    }
    (brain / "slots" / "registry.json").write_text(json.dumps(reg))
    return reg


def _add_tasks(brain, tasks):
    """Write tasks to tasks.json (JSON backend)."""
    # Use JSON backend by writing config
    config = {"storage": {"backend": "json"}}
    (brain / "config").mkdir(exist_ok=True)
    (brain / "config" / "nucleus.yaml").write_text(
        f"storage:\n  backend: json\n"
    )
    (brain / "ledger" / "tasks.json").write_text(json.dumps(tasks))


# ─── _brain_slot_complete_impl ─────────────────────────────────────────────

class TestBrainSlotComplete:
    def test_slot_not_found(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        result = _brain_slot_complete_impl("nonexistent", "t1")
        assert "not found" in result

    def test_task_mismatch(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        # Set current_task on slot
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t_real"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("slot_a", "t_wrong")
        assert "working on" in result
        assert "t_real" in result

    def test_stale_fence_token(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        reg["slots"]["slot_a"]["fence_token"] = 200
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("slot_a", "t1", fence_token=999)
        assert "Stale fence token" in result

    def test_complete_success(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "test task", "status": "IN_PROGRESS",
             "priority": 2, "blocked_by": [], "required_skills": [], "outputs": []}
        ])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        reg["slots"]["slot_a"]["fence_token"] = 200
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("slot_a", "t1", outcome="success",
                                            outputs=["file1.py"], verification_notes="verified")
        assert "completed" in result
        assert "success" in result

        # Verify registry updated
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        assert reg["slots"]["slot_a"]["current_task"] is None
        assert reg["slots"]["slot_a"]["stats"]["tasks_completed"] == 1

    def test_complete_failure(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "test task", "status": "IN_PROGRESS",
             "priority": 2, "blocked_by": [], "required_skills": []}
        ])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("slot_a", "t1", outcome="failed")
        assert "failed" in result

        reg = json.loads((brain / "slots" / "registry.json").read_text())
        assert reg["slots"]["slot_a"]["stats"]["failures"] == 1

    def test_complete_with_alias(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "test", "status": "IN_PROGRESS",
             "priority": 2, "blocked_by": [], "required_skills": []}
        ])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("alpha", "t1")
        assert "slot_a" in result

    def test_complete_task_not_in_storage(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        _add_tasks(brain, [])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        # Task not in storage but slot has it — should still clear slot
        result = _brain_slot_complete_impl("slot_a", "t1")
        assert "completed" in result

    def test_complete_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_slot_complete_impl("slot_a", "t1")
        assert "Error" in result

    def test_complete_no_stats_init(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_complete_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "test", "status": "IN_PROGRESS",
             "priority": 2, "blocked_by": [], "required_skills": []}
        ])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        # Remove stats if present
        reg["slots"]["slot_a"].pop("stats", None)
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_slot_complete_impl("slot_a", "t1")
        assert "completed" in result
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        assert reg["slots"]["slot_a"]["stats"]["tasks_completed"] == 1


# ─── _brain_slot_exhaust_impl ──────────────────────────────────────────────

class TestBrainSlotExhaust:
    def test_exhaust_success(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_exhaust_impl
        result = _brain_slot_exhaust_impl("slot_a", "Rate limit", "2026-01-20T00:00:00+0000")
        assert "exhausted" in result
        assert "2026-01-20" in result

        reg = json.loads((brain / "slots" / "registry.json").read_text())
        assert reg["slots"]["slot_a"]["status"] == "exhausted"
        assert reg["slots"]["slot_a"]["status_message"] == "Rate limit"

    def test_exhaust_with_alias(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_exhaust_impl
        result = _brain_slot_exhaust_impl("alpha", "Limit", "2026-01-20")
        assert "slot_a" in result

    def test_exhaust_slot_not_found(self, brain, slot_registry):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_exhaust_impl
        result = _brain_slot_exhaust_impl("nonexistent", "reason", "reset")
        assert "not found" in result

    def test_exhaust_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_slot_exhaust_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_slot_exhaust_impl("slot_a", "r", "t")
        assert "Error" in result


# ─── _brain_status_dashboard_impl ──────────────────────────────────────────

class TestBrainStatusDashboard:
    def test_basic_dashboard(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING", "priority": 1},
            {"id": "t2", "description": "Task 2", "status": "IN_PROGRESS", "priority": 2},
            {"id": "t3", "description": "Task 3", "status": "DONE", "priority": 3},
        ])
        result = _brain_status_dashboard_impl()
        assert "NUCLEUS CONTROL PLANE" in result
        assert "AGENT SLOTS" in result
        assert "TASK QUEUE" in result
        assert "Pending: 1" in result

    def test_dashboard_with_active_task(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Running task A", "status": "IN_PROGRESS", "priority": 1},
        ])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "t1"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_status_dashboard_impl()
        assert "Running" in result

    def test_dashboard_with_task_not_in_list(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [])
        reg = json.loads((brain / "slots" / "registry.json").read_text())
        reg["slots"]["slot_a"]["current_task"] = "ghost_task"
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _brain_status_dashboard_impl()
        assert "ghost_task" in result

    def test_dashboard_exhausted_slot(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [])
        result = _brain_status_dashboard_impl()
        assert "EXH" in result or "Reset" in result

    def test_dashboard_pending_tasks(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [
            {"id": f"t{i}", "description": f"Task {i}", "status": "PENDING", "priority": i}
            for i in range(1, 7)
        ])
        result = _brain_status_dashboard_impl()
        assert "Pending: 6" in result

    def test_dashboard_no_tasks(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [])
        result = _brain_status_dashboard_impl()
        assert "Pending: 0" in result

    def test_dashboard_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_status_dashboard_impl()
        assert "Dashboard error" in result

    def test_dashboard_idle_slot(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_status_dashboard_impl
        _add_tasks(brain, [])
        result = _brain_status_dashboard_impl()
        assert "Idling" in result


# ─── _brain_autopilot_sprint_impl ──────────────────────────────────────────

class TestBrainAutopilotSprint:
    def test_no_active_slots(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [])
        # Empty registry
        (brain / "slots" / "registry.json").write_text(json.dumps({"slots": {}, "aliases": {}}))
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        assert data["status"] == "ERROR"
        assert "No active slots" in data["error"]

    def test_no_tasks(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [])
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        # All active slots have no runnable tasks -> ALL_BLOCKED
        assert data["status"] in ("IDLE", "ALL_BLOCKED")

    def test_with_pending_tasks(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 1000},
            {"id": "t2", "description": "Task 2", "status": "PENDING", "priority": 2,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 1000},
        ])
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        assert data["status"] == "RUNNING"
        assert len(data["assignments"]) > 0

    def test_dry_run_mode(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 1000},
        ])
        result = _brain_autopilot_sprint_impl(dry_run=True)
        data = json.loads(result)
        assert data["dry_run"] is True
        # In dry run, no fence token (PLANNED status)
        executing = [a for a in data["assignments"] if a.get("status") == "EXECUTING"]
        planned = [a for a in data["assignments"] if a.get("status") == "PLANNED"]
        assert len(executing) == 0
        assert len(planned) > 0

    def test_status_mode(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "Task 1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 1000},
        ])
        result = _brain_autopilot_sprint_impl(mode="status")
        data = json.loads(result)
        assert data["status"] == "REPORT"

    def test_circular_deps_halt(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": ["t2"], "required_skills": []},
            {"id": "t2", "description": "T2", "status": "PENDING", "priority": 1,
             "blocked_by": ["t1"], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl(halt_on_blocker=True)
        data = json.loads(result)
        assert data["status"] == "HALTED"
        assert "Circular" in data["reason"]

    def test_circular_deps_no_halt(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": ["t2"], "required_skills": []},
            {"id": "t2", "description": "T2", "status": "PENDING", "priority": 1,
             "blocked_by": ["t1"], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl(halt_on_blocker=False)
        data = json.loads(result)
        assert data["status"] != "HALTED"

    def test_blocked_by_dependency(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "IN_PROGRESS", "priority": 1,
             "blocked_by": [], "required_skills": [], "claimed_by": "slot_b"},
            {"id": "t2", "description": "T2", "status": "PENDING", "priority": 2,
             "blocked_by": ["t1"], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        # slot_a gets t2 but it's blocked
        blocked = [a for a in data["assignments"] if a.get("status") == "BLOCKED"]
        assert len(blocked) > 0

    def test_exhausted_slot_skipped(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl(slots=["slot_c"])
        data = json.loads(result)
        exhausted = [a for a in data["assignments"] if a.get("status") == "EXHAUSTED"]
        assert len(exhausted) == 1

    def test_specific_slots(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl(slots=["slot_a"])
        data = json.loads(result)
        assert data["slots_summary"]["total"] == 1

    def test_tier_mismatch_halt(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "required_tier": "heavy"},
        ])
        # slot_a is standard, task requires heavy
        result = _brain_autopilot_sprint_impl(slots=["slot_a"], halt_on_tier_mismatch=True)
        data = json.loads(result)
        blocked = [a for a in data["assignments"] if a.get("status") == "BLOCKED"]
        assert len(blocked) > 0

    def test_budget_exceeded(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 100000},
        ])
        result = _brain_autopilot_sprint_impl(slots=["slot_b"], budget_limit=0.001)
        data = json.loads(result)
        budget_exceeded = [a for a in data["assignments"] if a.get("status") == "BUDGET_EXCEEDED"]
        assert len(budget_exceeded) > 0

    def test_claim_failed(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "claimed_by": "other_slot"},
        ])
        result = _brain_autopilot_sprint_impl(slots=["slot_a"])
        data = json.loads(result)
        # Task already claimed by other, so slot_a should be idle or blocked
        # (claimed tasks are skipped)
        assert data["status"] in ("IDLE", "ALL_BLOCKED")

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        assert data["status"] == "ERROR"

    def test_next_actions(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "estimated_tokens": 1000},
        ])
        result = _brain_autopilot_sprint_impl()
        data = json.loads(result)
        assert len(data["next_actions"]) > 0

    def test_all_blocked(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_autopilot_sprint_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": ["t_missing"], "required_skills": []},
        ])
        result = _brain_autopilot_sprint_impl(slots=["slot_a"])
        data = json.loads(result)
        # t1 blocked by t_missing (not in task list), so slot_a is blocked
        assert data["status"] in ("ALL_BLOCKED", "IDLE")


# ─── _brain_force_assign_impl ──────────────────────────────────────────────

class TestBrainForceAssign:
    def test_slot_not_found(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": []},
        ])
        result = json.loads(_brain_force_assign_impl("nonexistent", "t1"))
        assert "error" in result

    def test_task_not_found(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [])
        result = json.loads(_brain_force_assign_impl("slot_a", "nonexistent"))
        assert "error" in result

    def test_tier_mismatch_no_acknowledge(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "required_tier": "heavy"},
        ])
        result = json.loads(_brain_force_assign_impl("slot_c", "t1"))
        assert result["error"] == "TIER_MISMATCH_RISK"
        assert "risk_level" in result

    def test_tier_mismatch_with_acknowledge(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 1,
             "blocked_by": [], "required_skills": [], "required_tier": "heavy"},
        ])
        result = json.loads(_brain_force_assign_impl("slot_c", "t1", acknowledge_risk=True))
        assert result["success"] is True
        assert len(result["warnings"]) > 0

    def test_no_tier_mismatch(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 2,
             "blocked_by": [], "required_skills": []},
        ])
        result = json.loads(_brain_force_assign_impl("slot_a", "t1"))
        assert result["success"] is True
        assert result["warnings"] == []

    def test_with_alias(self, brain, slot_registry, tier_defs_file):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "PENDING", "priority": 2,
             "blocked_by": [], "required_skills": []},
        ])
        result = json.loads(_brain_force_assign_impl("alpha", "t1"))
        assert result["success"] is True
        assert result["slot_id"] == "slot_a"

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_force_assign_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_force_assign_impl("slot_a", "t1")
        assert "Error" in result


# ─── _check_protocol_compliance ────────────────────────────────────────────

class TestCheckProtocolCompliance:
    def test_no_protocol_file(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _check_protocol_compliance
        _add_tasks(brain, [])
        result = _check_protocol_compliance("agent_1")
        assert result["compliant"] is True
        assert "Protocol definition not found" in result["warnings"][0]

    def test_compliant_no_conflicts(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _check_protocol_compliance
        protocol = {"version": "1.0", "rules": []}
        (brain / "protocols" / "multi_agent_mou.json").write_text(json.dumps(protocol))
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "IN_PROGRESS",
             "claimed_by": "agent_1", "priority": 1, "blocked_by": [], "required_skills": []},
        ])
        result = _check_protocol_compliance("agent_1")
        assert result["compliant"] is True
        assert result["protocol_version"] == "1.0"

    def test_with_other_agent_tasks(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _check_protocol_compliance
        protocol = {"version": "2.0"}
        (brain / "protocols" / "multi_agent_mou.json").write_text(json.dumps(protocol))
        _add_tasks(brain, [
            {"id": "t1", "description": "T1", "status": "IN_PROGRESS",
             "claimed_by": "agent_2", "priority": 1, "blocked_by": [], "required_skills": []},
        ])
        result = _check_protocol_compliance("agent_1")
        assert result["compliant"] is True
        assert len(result["active_conflicts"]) == 1
        assert any("Caution" in w for w in result["warnings"])

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _check_protocol_compliance
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _check_protocol_compliance("agent_1")
        assert result["compliant"] is False
        assert "error" in result


# ─── _brain_request_handoff_impl ───────────────────────────────────────────

class TestBrainRequestHandoff:
    def test_basic_handoff(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        result = _brain_request_handoff_impl("agent_b", "sprint context", "do task X")
        assert "HANDOFF" in result
        assert "agent_b" in result
        assert "do task X" in result

        # Verify file written
        handoffs = json.loads((brain / "ledger" / "handoffs.json").read_text())
        assert len(handoffs) == 1
        assert handoffs[0]["to_agent"] == "agent_b"

    def test_with_artifacts(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        result = _brain_request_handoff_impl("agent_b", "ctx", "req",
                                              artifacts=["doc1.md", "doc2.md"])
        assert "doc1.md" in result
        assert "doc2.md" in result

    def test_no_artifacts(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        result = _brain_request_handoff_impl("agent_b", "ctx", "req")
        assert "None" in result

    def test_with_priority(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        result = _brain_request_handoff_impl("agent_b", "ctx", "req", priority=1)
        assert "P1" in result

    def test_append_to_existing(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        existing = [{"id": "h1", "status": "pending"}]
        (brain / "ledger" / "handoffs.json").write_text(json.dumps(existing))
        _brain_request_handoff_impl("agent_b", "ctx", "req")
        handoffs = json.loads((brain / "ledger" / "handoffs.json").read_text())
        assert len(handoffs) == 2

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_request_handoff_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _brain_request_handoff_impl("agent_b", "ctx", "req")
        assert "Error" in result


# ─── _brain_get_handoffs_impl ──────────────────────────────────────────────

class TestBrainGetHandoffs:
    def test_no_file(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_get_handoffs_impl
        result = json.loads(_brain_get_handoffs_impl())
        assert result["handoffs"] == []
        assert "No handoffs" in result["message"]

    def test_with_pending_handoffs(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_get_handoffs_impl
        handoffs = [
            {"id": "h1", "to_agent": "agent_a", "status": "pending", "context": "ctx"},
            {"id": "h2", "to_agent": "agent_b", "status": "pending", "context": "ctx2"},
            {"id": "h3", "to_agent": "agent_a", "status": "completed", "context": "ctx3"},
        ]
        (brain / "ledger" / "handoffs.json").write_text(json.dumps(handoffs))
        result = json.loads(_brain_get_handoffs_impl())
        assert result["count"] == 2  # only pending

    def test_filter_by_agent(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_get_handoffs_impl
        handoffs = [
            {"id": "h1", "to_agent": "agent_a", "status": "pending"},
            {"id": "h2", "to_agent": "agent_b", "status": "pending"},
        ]
        (brain / "ledger" / "handoffs.json").write_text(json.dumps(handoffs))
        result = json.loads(_brain_get_handoffs_impl("agent_a"))
        assert result["count"] == 1
        assert result["handoffs"][0]["to_agent"] == "agent_a"

    def test_no_pending(self, brain):
        from mcp_server_nucleus.runtime.slot_ops import _brain_get_handoffs_impl
        handoffs = [{"id": "h1", "status": "completed"}]
        (brain / "ledger" / "handoffs.json").write_text(json.dumps(handoffs))
        result = json.loads(_brain_get_handoffs_impl())
        assert result["count"] == 0

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.slot_ops import _brain_get_handoffs_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = json.loads(_brain_get_handoffs_impl())
        assert "error" in result
