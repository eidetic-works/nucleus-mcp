"""
Comprehensive pytest tests for runtime/autopilot.py - targeting 90%+ coverage.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import pytest

from mcp_server_nucleus.runtime.autopilot import (
    SprintMode,
    SprintStatus,
    MissionStatus,
    HaltReason,
    BudgetState,
    SlotState,
    TaskAssignment,
    HaltCondition,
    SprintCheckpoint,
    SprintResult,
    Mission,
    RetryPolicy,
    WaveAnalyzer,
    TaskAssigner,
    AutopilotEngine,
    format_sprint_result,
)


# ============================================================================
# Enums
# ============================================================================

class TestEnums:
    def test_sprint_mode(self):
        assert SprintMode.AUTO.value == "auto"
        assert SprintMode.PLAN.value == "plan"
        assert SprintMode.GUIDED.value == "guided"
        assert SprintMode.STATUS.value == "status"

    def test_sprint_status(self):
        assert SprintStatus.PENDING.value == "pending"
        assert SprintStatus.RUNNING.value == "running"
        assert SprintStatus.HALTED.value == "halted"

    def test_mission_status(self):
        assert MissionStatus.PENDING.value == "pending"
        assert MissionStatus.RUNNING.value == "running"

    def test_halt_reason(self):
        assert HaltReason.BUDGET_EXHAUSTED.value == "budget_exhausted"
        assert HaltReason.TIER_MISMATCH.value == "tier_mismatch"


# ============================================================================
# BudgetState
# ============================================================================

class TestBudgetState:
    def test_default(self):
        b = BudgetState()
        assert b.limit == 0.0
        assert b.remaining == 0.0
        assert b.spent == 0.0

    def test_remaining(self):
        b = BudgetState(limit=100, spent=30, reserved=20)
        assert b.remaining == 50

    def test_remaining_clamped(self):
        b = BudgetState(limit=10, spent=20)
        assert b.remaining == 0

    def test_burn_rate(self):
        b = BudgetState()
        assert b.burn_rate == 0.0

    def test_can_afford(self):
        b = BudgetState(limit=100, spent=30)
        assert b.can_afford(50)
        assert not b.can_afford(80)

    def test_reserve_success(self):
        b = BudgetState(limit=100)
        assert b.reserve("t1", 30)
        assert b.reserved == 30
        assert b.reservations["t1"] == 30

    def test_reserve_fail(self):
        b = BudgetState(limit=10)
        assert not b.reserve("t1", 20)
        assert b.reserved == 0

    def test_commit(self):
        b = BudgetState(limit=100)
        b.reserve("t1", 30)
        b.commit("t1", 25, tokens=500)
        assert b.spent == 25
        assert b.reserved == 0
        assert b.tokens_used == 500
        assert "t1" not in b.reservations

    def test_commit_no_reservation(self):
        b = BudgetState(limit=100)
        b.commit("t1", 25)
        assert b.spent == 25
        assert b.reserved == 0

    def test_release(self):
        b = BudgetState(limit=100)
        b.reserve("t1", 30)
        b.release("t1")
        assert b.reserved == 0
        assert "t1" not in b.reservations

    def test_release_not_reserved(self):
        b = BudgetState(limit=100)
        b.release("nope")  # no-op


# ============================================================================
# SlotState / TaskAssignment / HaltCondition / SprintCheckpoint / SprintResult / Mission
# ============================================================================

class TestSlotState:
    def test_defaults(self):
        s = SlotState(slot_id="s1", model="m", tier="T2_CODE")
        assert s.status == "idle"
        assert s.current_task is None
        assert s.queue_depth == 0


class TestTaskAssignment:
    def test_defaults(self):
        a = TaskAssignment(task_id="t1", slot_id="s1", assigned_at="now")
        assert a.estimated_cost == 0.0
        assert a.priority == 3


class TestHaltCondition:
    def test_defaults(self):
        h = HaltCondition(reason=HaltReason.BUDGET_EXHAUSTED, message="m", recoverable=False)
        assert h.tasks_affected == []
        assert h.timestamp
        assert h.recommendation == ""


class TestSprintCheckpoint:
    def test_to_dict(self):
        c = SprintCheckpoint(
            sprint_id="sp1", timestamp="t", wave=1,
            tasks_completed=["t1"], tasks_in_progress={"t2": "s1"},
            tasks_remaining=["t3"], budget_state={"limit": 100},
            slot_states=[{"slot_id": "s1"}],
        )
        d = c.to_dict()
        assert d["sprint_id"] == "sp1"
        assert d["wave"] == 1


class TestSprintResult:
    def test_to_dict(self):
        r = SprintResult(
            sprint_id="sp1", mission_id="m1",
            status=SprintStatus.COMPLETED, mode=SprintMode.AUTO,
            started_at="t1", completed_at="t2", duration_seconds=10.0,
            tasks_total=5, tasks_completed=5, tasks_failed=0,
            tasks_skipped=0, tasks_remaining=0,
            slots_used=2, slot_utilization=1.0, slot_exhaustions=0,
            budget_limit=10.0, budget_spent=5.0, tokens_used=1000,
        )
        d = r.to_dict()
        assert d["status"] == "completed"
        assert d["mode"] == "auto"
        assert d["sprint_id"] == "sp1"


class TestMission:
    def test_defaults(self):
        m = Mission(
            id="m1", name="n", goal="g", success_criteria=["c"],
            tasks=["t1"], slots=["s1"], budget_limit=10, time_limit_hours=4,
        )
        assert m.status == MissionStatus.PENDING
        assert m.priority == 3
        assert m.started_at is None

    def test_to_dict(self):
        m = Mission(
            id="m1", name="n", goal="g", success_criteria=["c"],
            tasks=["t1"], slots=["s1"], budget_limit=10, time_limit_hours=4,
            status=MissionStatus.RUNNING,
        )
        d = m.to_dict()
        assert d["status"] == "running"
        assert d["id"] == "m1"


# ============================================================================
# RetryPolicy
# ============================================================================

class TestRetryPolicy:
    def test_get_delay(self):
        rp = RetryPolicy(max_retries=3, backoff_base=2.0, backoff_max=60.0)
        assert rp.get_delay("t1") == 1.0  # 2^0
        rp.record_attempt("t1")
        assert rp.get_delay("t1") == 2.0  # 2^1
        rp.record_attempt("t1")
        assert rp.get_delay("t1") == 4.0  # 2^2

    def test_get_delay_capped(self):
        rp = RetryPolicy(max_retries=10, backoff_base=2.0, backoff_max=10.0)
        for _ in range(10):
            rp.record_attempt("t1")
        assert rp.get_delay("t1") == 10.0  # capped

    def test_record_attempt(self):
        rp = RetryPolicy()
        assert rp.record_attempt("t1") == 1
        assert rp.record_attempt("t1") == 2

    def test_should_retry_under_max(self):
        rp = RetryPolicy(max_retries=3)
        assert rp.should_retry("t1")  # no attempts yet

    def test_should_retry_at_max(self):
        rp = RetryPolicy(max_retries=2)
        rp.record_attempt("t1")
        rp.record_attempt("t1")
        assert not rp.should_retry("t1")

    def test_should_retry_transient_error(self):
        rp = RetryPolicy(max_retries=3)
        assert rp.should_retry("t1", TimeoutError("timeout"))
        assert rp.should_retry("t1", ConnectionError("conn"))

    def test_should_retry_non_transient_error(self):
        rp = RetryPolicy(max_retries=3)
        assert not rp.should_retry("t1", ValueError("bad"))

    def test_reset(self):
        rp = RetryPolicy()
        rp.record_attempt("t1")
        rp.reset("t1")
        assert "t1" not in rp.attempts


# ============================================================================
# WaveAnalyzer
# ============================================================================

class TestWaveAnalyzer:
    def test_simple_deps(self):
        tasks = [
            {"id": "t1", "blocked_by": []},
            {"id": "t2", "blocked_by": ["t1"]},
            {"id": "t3", "blocked_by": ["t1", "t2"]},
        ]
        wa = WaveAnalyzer(tasks)
        assert wa.get_wave_count() == 3
        assert wa.get_wave(0) == ["t1"]
        assert wa.get_wave(1) == ["t2"]
        assert wa.get_wave(2) == ["t3"]

    def test_parallel_tasks(self):
        tasks = [
            {"id": "t1", "blocked_by": []},
            {"id": "t2", "blocked_by": []},
            {"id": "t3", "blocked_by": ["t1", "t2"]},
        ]
        wa = WaveAnalyzer(tasks)
        assert wa.get_wave_count() == 2
        assert set(wa.get_wave(0)) == {"t1", "t2"}
        assert wa.get_wave(1) == ["t3"]

    def test_circular_dependency(self):
        tasks = [
            {"id": "t1", "blocked_by": ["t2"]},
            {"id": "t2", "blocked_by": ["t1"]},
        ]
        wa = WaveAnalyzer(tasks)
        # Both end up in the blocked wave
        assert wa.get_wave_count() >= 1
        circular = wa.detect_circular()
        assert set(circular) == {"t1", "t2"}

    def test_depends_on_field(self):
        tasks = [
            {"id": "t1", "depends_on": []},
            {"id": "t2", "depends_on": ["t1"]},
        ]
        wa = WaveAnalyzer(tasks)
        assert wa.get_wave(0) == ["t1"]
        assert wa.get_wave(1) == ["t2"]

    def test_no_deps(self):
        tasks = [{"id": "t1"}, {"id": "t2"}]
        wa = WaveAnalyzer(tasks)
        assert wa.get_wave_count() == 1
        assert set(wa.get_wave(0)) == {"t1", "t2"}

    def test_get_wave_out_of_range(self):
        wa = WaveAnalyzer([{"id": "t1"}])
        assert wa.get_wave(99) == []
        assert wa.get_wave(-1) == []

    def test_detect_circular_none(self):
        tasks = [
            {"id": "t1", "blocked_by": []},
            {"id": "t2", "blocked_by": ["t1"]},
        ]
        wa = WaveAnalyzer(tasks)
        assert wa.detect_circular() == []

    def test_external_dep_not_circular(self):
        tasks = [
            {"id": "t1", "blocked_by": ["external"]},
        ]
        wa = WaveAnalyzer(tasks)
        # external is not in tasks, so t1 goes to blocked wave
        # but it's not circular since external isn't in tasks
        assert wa.detect_circular() == []


# ============================================================================
# TaskAssigner
# ============================================================================

class TestTaskAssigner:
    def _make_slots(self):
        return [
            SlotState(slot_id="s1", model="m1", tier="T1_RESEARCH", status="idle"),
            SlotState(slot_id="s2", model="m2", tier="T2_CODE", status="idle"),
            SlotState(slot_id="s3", model="m3", tier="T3_REVIEW", status="exhausted"),
        ]

    def test_assign_idle(self):
        ta = TaskAssigner(self._make_slots())
        task = {"id": "t1", "required_tier": "T2_CODE"}
        a = ta.assign(task)
        assert a is not None
        assert a.slot_id in ("s1", "s2")

    def test_assign_prefers_idle(self):
        slots = [
            SlotState(slot_id="s1", model="m", tier="T2_CODE", status="busy", queue_depth=3),
            SlotState(slot_id="s2", model="m", tier="T2_CODE", status="idle", queue_depth=0),
        ]
        ta = TaskAssigner(slots)
        a = ta.assign({"id": "t1", "required_tier": "T2_CODE"})
        assert a.slot_id == "s2"

    def test_assign_least_loaded(self):
        slots = [
            SlotState(slot_id="s1", model="m", tier="T2_CODE", status="busy", queue_depth=5),
            SlotState(slot_id="s2", model="m", tier="T2_CODE", status="busy", queue_depth=1),
        ]
        ta = TaskAssigner(slots)
        a = ta.assign({"id": "t1", "required_tier": "T2_CODE"})
        assert a.slot_id == "s2"

    def test_assign_no_capable(self):
        ta = TaskAssigner(self._make_slots())
        a = ta.assign({"id": "t1", "required_tier": "T4_ADMIN"})
        # T1, T2 can handle T4 (lower index = higher capability)
        # T1_RESEARCH idx=0 <= T4_ADMIN idx=3 -> capable
        assert a is not None

    def test_assign_force(self):
        slots = [SlotState(slot_id="s1", model="m", tier="T3_REVIEW", status="idle")]
        ta = TaskAssigner(slots)
        # T3 can't handle T1 (idx 2 > idx 0), but force=True
        a = ta.assign({"id": "t1", "required_tier": "T1_RESEARCH"}, force=True)
        assert a is not None
        assert a.slot_id == "s1"

    def test_assign_force_no_slots(self):
        slots = [SlotState(slot_id="s1", model="m", tier="T2_CODE", status="exhausted")]
        ta = TaskAssigner(slots)
        a = ta.assign({"id": "t1", "required_tier": "T1_RESEARCH"}, force=True)
        assert a is None

    def test_assign_all_exhausted(self):
        slots = [SlotState(slot_id="s1", model="m", tier="T2_CODE", status="exhausted")]
        ta = TaskAssigner(slots)
        a = ta.assign({"id": "t1", "required_tier": "T2_CODE"})
        assert a is None

    def test_assign_with_estimated_cost(self):
        ta = TaskAssigner(self._make_slots())
        a = ta.assign({"id": "t1", "required_tier": "T2_CODE", "estimated_cost": 0.5})
        assert a.estimated_cost == 0.5

    def test_assign_with_priority(self):
        ta = TaskAssigner(self._make_slots())
        a = ta.assign({"id": "t1", "required_tier": "T2_CODE", "priority": 1})
        assert a.priority == 1

    def test_tier_capable_unknown_tier(self):
        ta = TaskAssigner(self._make_slots())
        assert ta._tier_capable("UNKNOWN", "T2_CODE")  # default True

    def test_update_slot(self):
        ta = TaskAssigner(self._make_slots())
        ta.update_slot("s1", status="busy", current_task="t1")
        assert ta.slots["s1"].status == "busy"
        assert ta.slots["s1"].current_task == "t1"

    def test_update_slot_unknown(self):
        ta = TaskAssigner(self._make_slots())
        ta.update_slot("nope", status="busy")  # no-op

    def test_update_slot_unknown_attr(self):
        ta = TaskAssigner(self._make_slots())
        ta.update_slot("s1", unknown_attr="x")  # no-op, attr doesn't exist

    def test_get_available_count(self):
        ta = TaskAssigner(self._make_slots())
        assert ta.get_available_count() == 2  # s3 is exhausted

    def test_get_idle_count(self):
        ta = TaskAssigner(self._make_slots())
        assert ta.get_idle_count() == 2


# ============================================================================
# AutopilotEngine
# ============================================================================

class TestAutopilotEngine:
    @pytest.fixture(autouse=True)
    def _mock_dispatch(self):
        """Mock cross_vendor_enabled + dispatch_and_capture for all autopilot tests.

        _execute_task now calls real vendor_dispatch; tests that exercise
        execute_sprint need the dispatch mocked to avoid calling real CLIs.
        Individual tests can override the return_value if they need to test
        failure paths.
        """
        import unittest.mock as _mock
        with _mock.patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled", return_value=True), \
             _mock.patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={"status": "ok", "effect": "unknown", "artifact_ref": "mock_ref_123", "capture": {"relay": "ok", "engram": "ok"}}) as mock_dispatch:
            yield mock_dispatch

    def _setup_brain(self, tmp_path, tasks=None, slots=None):
        """Set up brain directory with tasks and slots."""
        tasks_path = tmp_path / "ledger" / "tasks.json"
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_path.write_text(json.dumps({"tasks": tasks or []}))

        registry_path = tmp_path / "slots" / "registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        if slots is None:
            slots_data = {
                "s1": {"model": "m1", "tier": "T2_CODE", "status": "idle"},
                "s2": {"model": "m2", "tier": "T1_RESEARCH", "status": "idle"},
            }
        else:
            slots_data = slots
        registry_path.write_text(json.dumps({"slots": slots_data}))

    def test_init_default(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng.current_sprint_id is None
        assert eng.budget is not None

    def test_init_with_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        eng = AutopilotEngine()
        assert eng.brain_path == tmp_path

    def test_execute_sprint_no_tasks(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint()
        assert result.status == SprintStatus.COMPLETED
        assert result.tasks_total == 0

    def test_execute_sprint_no_slots(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[{"id": "t1", "status": "PENDING"}], slots={})
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint()
        assert result.status == SprintStatus.FAILED

    def test_execute_sprint_auto(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint()
        assert result.status == SprintStatus.COMPLETED
        assert result.tasks_completed == 1

    def test_execute_sprint_dry_run(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE"},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(dry_run=True)
        assert result.mode == SprintMode.PLAN

    def test_execute_sprint_plan_mode(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE"},
            {"id": "t2", "status": "PENDING", "blocked_by": ["t1"]},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(mode=SprintMode.PLAN)
        assert result.mode == SprintMode.PLAN
        assert any("Wave 1" in s for s in result.next_steps)

    def test_execute_sprint_status_mode(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE"},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(mode=SprintMode.STATUS)
        assert result.mode == SprintMode.STATUS
        assert result.status == SprintStatus.PENDING

    def test_execute_sprint_circular_halt(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "blocked_by": ["t2"]},
            {"id": "t2", "status": "PENDING", "blocked_by": ["t1"]},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(halt_on_blocker=True)
        assert result.status == SprintStatus.HALTED
        assert "Circular" in result.halt_reason

    def test_execute_sprint_guided_mode(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(mode=SprintMode.GUIDED)
        assert result.mode == SprintMode.GUIDED
        assert result.tasks_completed == 1

    def test_execute_sprint_budget_limit(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 5.0},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(budget_limit=1.0)
        # Budget can't afford 5.0 -> halt
        assert result.status == SprintStatus.HALTED
        assert "Budget" in result.halt_reason

    def test_execute_sprint_tier_mismatch_halt(self, tmp_path):
        # T2_CODE (idx=1) cannot handle T1_RESEARCH (idx=0)
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T1_RESEARCH"},
        ], slots={"s1": {"model": "m", "tier": "T2_CODE", "status": "idle"}})
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(halt_on_tier_mismatch=True)
        assert result.status == SprintStatus.HALTED

    def test_execute_sprint_tier_mismatch_no_halt(self, tmp_path):
        # T2_CODE (idx=1) cannot handle T1_RESEARCH (idx=0)
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T1_RESEARCH"},
        ], slots={"s1": {"model": "m", "tier": "T2_CODE", "status": "idle"}})
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.execute_sprint(halt_on_tier_mismatch=False)
        # Task can't be assigned -> warning, not halt
        assert "Could not assign" in " ".join(result.warnings) or result.status == SprintStatus.COMPLETED

    def test_execute_sprint_with_halt_request(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        # halt_requested gets reset at start of execute_sprint, so we need
        # to set it via a mock that triggers during execution
        # Instead, test halt_sprint which sets the flag
        eng.halt_sprint("test halt")
        assert eng.halt_requested is True

    def test_execute_sprint_with_orchestrator(self, tmp_path):
        class FakeOrch:
            def get_all_tasks(self, status=None):
                return [{"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1}]
            def complete_task(self, task_id, slot_id, result):
                pass
            def update_task(self, task_id, updates):
                pass
        self._setup_brain(tmp_path)
        eng = AutopilotEngine(orchestrator=FakeOrch(), brain_path=tmp_path)
        result = eng.execute_sprint()
        assert result.tasks_completed == 1

    def test_execute_sprint_with_mission_task_filter(self, tmp_path):
        """When a mission is active with task_ids, _get_pending_tasks and
        execute_sprint filter pending tasks down to only those matching
        current_mission.tasks."""
        self._setup_brain(tmp_path, tasks=[
            {"id": "task_1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
            {"id": "task_2", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
            {"id": "task_3", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        # Mission only includes task_1 and task_3 — task_2 must be filtered out
        eng.start_mission("Filter Mission", "Goal", ["task_1", "task_3"])
        pending = eng._get_pending_tasks()
        pending_ids = {t["id"] for t in pending}
        assert pending_ids == {"task_1", "task_3"}
        assert "task_2" not in pending_ids
        # execute_sprint should only dispatch task_1 and task_3
        result = eng.execute_sprint()
        assert result.status == SprintStatus.COMPLETED
        assert result.tasks_completed == 2
        assert set(result.completed_tasks) == {"task_1", "task_3"}

    def test_start_mission(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        mission = eng.start_mission("Test Mission", "Goal", ["t1", "t2"])
        assert mission.name == "Test Mission"
        assert mission.status == MissionStatus.RUNNING
        assert eng.current_mission is not None
        # Check saved to disk
        mission_files = list((tmp_path / "missions").glob("*.json"))
        assert len(mission_files) == 1

    def test_start_mission_with_options(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        mission = eng.start_mission(
            "M", "G", ["t1"], slot_ids=["s1"],
            budget_limit=50, time_limit_hours=8,
            success_criteria=["c1"],
        )
        assert mission.budget_limit == 50
        assert mission.time_limit_hours == 8
        assert mission.success_criteria == ["c1"]

    def test_get_mission_status_no_mission(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        status = eng.get_mission_status()
        assert "error" in status

    def test_get_mission_status_current(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.start_mission("M", "G", ["t1", "t2"])
        status = eng.get_mission_status()
        assert status["name"] == "M"
        assert status["progress"]["total"] == 2

    def test_get_mission_status_by_id(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        mission = eng.start_mission("M", "G", ["t1"])
        status = eng.get_mission_status(mission.id)
        assert status["mission_id"] == mission.id

    def test_get_mission_status_not_found(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        status = eng.get_mission_status("nonexistent")
        assert "error" in status

    def test_halt_sprint(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.current_sprint_id = "sp123"
        result = eng.halt_sprint("test halt")
        assert result["status"] == "halt_requested"
        assert eng.halt_requested is True

    def test_resume_sprint_no_checkpoint(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng.resume_sprint("nonexistent")
        assert result.status == SprintStatus.FAILED
        assert "No checkpoint" in result.halt_reason

    def test_resume_sprint_with_checkpoint(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        # First run to create checkpoint
        eng.execute_sprint()
        sprint_id = eng.current_sprint_id
        # Resume
        result = eng.resume_sprint(sprint_id)
        assert result is not None

    def test_get_pending_tasks_no_orch_no_file(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng._get_pending_tasks() == []

    def test_get_slot_states_no_registry(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng._get_slot_states() == []

    def test_get_slot_states_with_filter(self, tmp_path):
        self._setup_brain(tmp_path)
        eng = AutopilotEngine(brain_path=tmp_path)
        states = eng._get_slot_states(["s1"])
        assert len(states) == 1
        assert states[0].slot_id == "s1"

    def test_get_slot_states_excludes_exhausted(self, tmp_path):
        self._setup_brain(tmp_path, slots={
            "s1": {"model": "m", "tier": "T2_CODE", "status": "idle"},
            "s2": {"model": "m", "tier": "T2_CODE", "status": "exhausted"},
        })
        eng = AutopilotEngine(brain_path=tmp_path)
        states = eng._get_slot_states()
        assert len(states) == 1

    def test_check_halt_conditions_budget(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.budget = BudgetState(limit=10, spent=10)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        halt = eng._check_halt_conditions(ta, None, time.time(), False)
        assert halt is not None
        assert halt.reason == HaltReason.BUDGET_EXHAUSTED

    def test_check_halt_conditions_all_exhausted(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.budget = BudgetState(limit=100)
        slots = [SlotState("s1", "m", "T2_CODE", "exhausted")]
        ta = TaskAssigner(slots)
        halt = eng._check_halt_conditions(ta, None, time.time(), False)
        assert halt is not None
        assert halt.reason == HaltReason.ALL_SLOTS_EXHAUSTED

    def test_check_halt_conditions_time_limit(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.budget = BudgetState(limit=100)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        # start_time in the past
        halt = eng._check_halt_conditions(ta, 0.001, time.time() - 10, False)
        assert halt is not None
        assert halt.reason == HaltReason.TIME_LIMIT

    def test_check_halt_conditions_none(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.budget = BudgetState(limit=100)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        halt = eng._check_halt_conditions(ta, None, time.time(), False)
        assert halt is None

    def test_execute_task_success(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        task = {"id": "t1"}
        assignment = TaskAssignment(task_id="t1", slot_id="s1", assigned_at="now")
        # autouse fixture mocks dispatch with status=ok
        success = eng._execute_task(task, assignment, ta)
        assert success is True
        assert ta.slots["s1"].tasks_completed == 1

    def test_execute_task_with_orchestrator(self, tmp_path):
        class FakeOrch:
            def __init__(self):
                self.completed = []
            def complete_task(self, task_id, slot_id, result):
                self.completed.append(task_id)
        eng = AutopilotEngine(orchestrator=FakeOrch(), brain_path=tmp_path)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        task = {"id": "t1"}
        assignment = TaskAssignment(task_id="t1", slot_id="s1", assigned_at="now")
        # autouse fixture mocks dispatch with status=ok
        eng._execute_task(task, assignment, ta)
        assert "t1" in eng.orch.completed

    def test_execute_task_cross_vendor_disabled(self, tmp_path, monkeypatch):
        """When cross_vendor is OFF, _execute_task fails without dispatching."""
        import unittest.mock as _mock
        eng = AutopilotEngine(brain_path=tmp_path)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        task = {"id": "t1"}
        assignment = TaskAssignment(task_id="t1", slot_id="s1", assigned_at="now")
        # Override the autouse fixture's cross_vendor_enabled to return False
        with _mock.patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled", return_value=False):
            success = eng._execute_task(task, assignment, ta)
        assert success is False
        assert ta.slots["s1"].tasks_failed == 1

    def test_execute_task_dispatch_error(self, tmp_path):
        """When dispatch returns status != 'ok', task fails."""
        import unittest.mock as _mock
        eng = AutopilotEngine(brain_path=tmp_path)
        slots = [SlotState("s1", "m", "T2_CODE", "idle")]
        ta = TaskAssigner(slots)
        task = {"id": "t1"}
        assignment = TaskAssignment(task_id="t1", slot_id="s1", assigned_at="now")
        # Override the autouse fixture's dispatch to return error
        with _mock.patch("mcp_server_nucleus.runtime.vendor_dispatch.dispatch_and_capture", return_value={"status": "error", "effect": "unknown"}):
            success = eng._execute_task(task, assignment, ta)
        assert success is False
        assert ta.slots["s1"].tasks_failed == 1

    def test_save_and_load_checkpoint(self, tmp_path):
        self._setup_brain(tmp_path, tasks=[
            {"id": "t1", "status": "PENDING", "required_tier": "T2_CODE", "estimated_cost": 0.1},
        ])
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.execute_sprint()
        sprint_id = eng.current_sprint_id
        cp = eng._load_checkpoint(sprint_id)
        assert cp is not None
        assert cp.sprint_id == sprint_id

    def test_load_checkpoint_missing(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng._load_checkpoint("nonexistent") is None

    def test_save_and_load_mission(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        mission = eng.start_mission("M", "G", ["t1"])
        loaded = eng._load_mission(mission.id)
        assert loaded is not None
        assert loaded.name == "M"
        assert loaded.status == MissionStatus.RUNNING

    def test_load_mission_missing(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng._load_mission("nonexistent") is None

    def test_calculate_elapsed(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        ts = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        elapsed = eng._calculate_elapsed(ts)
        assert "h" in elapsed and "m" in elapsed

    def test_calculate_elapsed_invalid(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        assert eng._calculate_elapsed("invalid") == "N/A"

    def test_generate_next_steps_completed(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        steps = eng._generate_next_steps(SprintStatus.COMPLETED, None)
        assert any("completed" in s.lower() for s in steps)

    def test_generate_next_steps_partial(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.failed_tasks = [{"task_id": "t1"}]
        steps = eng._generate_next_steps(SprintStatus.PARTIAL, None)
        assert any("Retry" in s for s in steps)

    def test_generate_next_steps_halted_budget(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        steps = eng._generate_next_steps(SprintStatus.HALTED, "Budget limit reached")
        assert any("budget" in s.lower() for s in steps)

    def test_generate_next_steps_halted_slot(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        steps = eng._generate_next_steps(SprintStatus.HALTED, "All slots exhausted")
        assert any("slot" in s.lower() for s in steps)

    def test_generate_next_steps_halted_circular(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        steps = eng._generate_next_steps(SprintStatus.HALTED, "Circular dependencies detected")
        assert any("circular" in s.lower() for s in steps)

    def test_generate_next_steps_halted_other(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        steps = eng._generate_next_steps(SprintStatus.HALTED, "Some other reason")
        assert any("Review" in s for s in steps)

    def test_create_result_with_mission(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        eng.start_mission("M", "G", ["t1"])
        result = eng._create_result("sp1", "2025-01-01T00:00:00Z", SprintMode.AUTO, SprintStatus.COMPLETED, None, [], [])
        assert result.mission_id is not None

    def test_create_result_invalid_timestamp(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng._create_result("sp1", "invalid", SprintMode.AUTO, SprintStatus.COMPLETED, None, [], [])
        assert result.duration_seconds == 0

    def test_create_result_with_exhausted_slots(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        slots = [SlotState("s1", "m", "T2_CODE", "exhausted")]
        result = eng._create_result("sp1", "2025-01-01T00:00:00Z", SprintMode.AUTO, SprintStatus.COMPLETED, None, [], slots)
        assert result.slot_exhaustions == 1

    def test_create_status_result(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        result = eng._create_status_result("sp1", "2025-01-01T00:00:00Z", [], [])
        assert result.mode == SprintMode.STATUS

    def test_create_plan_result(self, tmp_path):
        eng = AutopilotEngine(brain_path=tmp_path)
        wa = WaveAnalyzer([{"id": "t1"}, {"id": "t2", "blocked_by": ["t1"]}])
        result = eng._create_plan_result("sp1", "2025-01-01T00:00:00Z", [], [], wa)
        assert any("Wave 1" in s for s in result.next_steps)
        assert any("Wave 2" in s for s in result.next_steps)


# ============================================================================
# format_sprint_result
# ============================================================================

class TestFormatSprintResult:
    def test_basic(self):
        r = SprintResult(
            sprint_id="sp1", mission_id=None,
            status=SprintStatus.COMPLETED, mode=SprintMode.AUTO,
            started_at="t1", completed_at="t2", duration_seconds=10.5,
            tasks_total=5, tasks_completed=5, tasks_failed=0,
            tasks_skipped=0, tasks_remaining=0,
            slots_used=2, slot_utilization=1.0, slot_exhaustions=0,
            budget_limit=10.0, budget_spent=5.0, tokens_used=1000,
        )
        out = format_sprint_result(r)
        assert "Sprint Report" in out
        assert "COMPLETED" in out
        assert "5" in out

    def test_with_halt_reason(self):
        r = SprintResult(
            sprint_id="sp1", mission_id=None,
            status=SprintStatus.HALTED, mode=SprintMode.AUTO,
            started_at="t1", completed_at="t2", duration_seconds=5.0,
            tasks_total=3, tasks_completed=1, tasks_failed=0,
            tasks_skipped=0, tasks_remaining=2,
            slots_used=1, slot_utilization=1.0, slot_exhaustions=0,
            budget_limit=None, budget_spent=0, tokens_used=0,
            halt_reason="Budget exhausted",
        )
        out = format_sprint_result(r)
        assert "HALT REASON" in out
        assert "Budget exhausted" in out

    def test_with_next_steps(self):
        r = SprintResult(
            sprint_id="sp1", mission_id=None,
            status=SprintStatus.COMPLETED, mode=SprintMode.AUTO,
            started_at="t1", completed_at="t2", duration_seconds=5.0,
            tasks_total=1, tasks_completed=1, tasks_failed=0,
            tasks_skipped=0, tasks_remaining=0,
            slots_used=1, slot_utilization=1.0, slot_exhaustions=0,
            budget_limit=None, budget_spent=0, tokens_used=0,
            next_steps=["Step 1", "Step 2"],
        )
        out = format_sprint_result(r)
        assert "NEXT STEPS" in out
        assert "Step 1" in out
