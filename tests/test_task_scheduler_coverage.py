"""Comprehensive tests for task_scheduler module."""
import time
import threading
import pytest

from mcp_server_nucleus.runtime.task_scheduler import (
    TaskStatus,
    TaskPriority,
    TaskTier,
    AgentState,
    ScheduleDecision,
    TaskScheduler,
)


# ── Enums ────────────────────────────────────────────────────────

class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.SCHEDULED.value == "SCHEDULED"
        assert TaskStatus.BLOCKED.value == "BLOCKED"
        assert TaskStatus.ASSIGNED.value == "ASSIGNED"
        assert TaskStatus.COMPLETED.value == "COMPLETED"

    def test_is_str_enum(self):
        assert isinstance(TaskStatus.PENDING, str)


class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.HIGH.value == "HIGH"
        assert TaskPriority.MEDIUM.value == "MEDIUM"
        assert TaskPriority.LOW.value == "LOW"

    def test_sort_value(self):
        assert TaskPriority.HIGH.sort_value() == 0
        assert TaskPriority.MEDIUM.sort_value() == 1
        assert TaskPriority.LOW.sort_value() == 2

    def test_high_has_lower_sort_value(self):
        assert TaskPriority.HIGH.sort_value() < TaskPriority.LOW.sort_value()


class TestTaskTier:
    def test_values(self):
        assert TaskTier.T1_PLANNING.value == "T1_PLANNING"
        assert TaskTier.T2_CODE.value == "T2_CODE"
        assert TaskTier.T3_REVIEW.value == "T3_REVIEW"
        assert TaskTier.T4_DEPLOY.value == "T4_DEPLOY"

    def test_sort_value(self):
        assert TaskTier.T1_PLANNING.sort_value() == 0
        assert TaskTier.T2_CODE.sort_value() == 1
        assert TaskTier.T3_REVIEW.sort_value() == 2
        assert TaskTier.T4_DEPLOY.sort_value() == 3


# ── AgentState ───────────────────────────────────────────────────

class TestAgentState:
    def test_init(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        assert agent.id == "a1"
        assert agent.tier == "T2_CODE"
        assert agent.capacity == 3
        assert agent.current_tasks == set()
        assert agent.available is True
        assert agent.tasks_completed == 0
        assert agent.last_heartbeat > 0

    def test_is_available_empty(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        assert agent.is_available() is True

    def test_is_available_full(self):
        agent = AgentState("a1", "T2_CODE", capacity=2)
        agent.assign_task("t1")
        agent.assign_task("t2")
        assert agent.is_available() is False

    def test_assign_task_success(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        assert agent.assign_task("t1") is True
        assert "t1" in agent.current_tasks

    def test_assign_task_full(self):
        agent = AgentState("a1", "T2_CODE", capacity=1)
        agent.assign_task("t1")
        assert agent.assign_task("t2") is False
        assert "t2" not in agent.current_tasks

    def test_complete_task_success(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        agent.assign_task("t1")
        assert agent.complete_task("t1") is True
        assert "t1" not in agent.current_tasks
        assert agent.tasks_completed == 1

    def test_complete_task_not_found(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        assert agent.complete_task("nonexistent") is False
        assert agent.tasks_completed == 0

    def test_to_dict(self):
        agent = AgentState("a1", "T2_CODE", capacity=3)
        agent.assign_task("t1")
        d = agent.to_dict()
        assert d["id"] == "a1"
        assert d["tier"] == "T2_CODE"
        assert d["capacity"] == 3
        assert "t1" in d["current_tasks"]
        assert d["available"] is True
        assert d["tasks_completed"] == 0
        assert "last_heartbeat" in d


# ── ScheduleDecision ─────────────────────────────────────────────

class TestScheduleDecision:
    def test_init_defaults(self):
        sd = ScheduleDecision("t1")
        assert sd.task_id == "t1"
        assert sd.agent_id is None
        assert sd.reason == "queued"
        assert sd.scheduled_at > 0

    def test_init_with_agent(self):
        sd = ScheduleDecision("t1", agent_id="a1", reason="assigned")
        assert sd.agent_id == "a1"
        assert sd.reason == "assigned"

    def test_to_dict(self):
        sd = ScheduleDecision("t1", agent_id="a1", reason="assigned")
        d = sd.to_dict()
        assert d["task_id"] == "t1"
        assert d["agent_id"] == "a1"
        assert d["reason"] == "assigned"
        assert "scheduled_at" in d


# ── TaskScheduler ────────────────────────────────────────────────

class TestTaskScheduler:
    def test_init(self):
        ts = TaskScheduler(max_agents=500)
        assert ts.max_agents == 500
        assert ts.agent_registry == {}
        assert ts.task_states == {}
        assert ts.stats["scheduled"] == 0
        assert ts.stats["blocked"] == 0
        assert ts.stats["queued"] == 0
        assert ts.stats["completed"] == 0

    def test_init_default(self):
        ts = TaskScheduler()
        assert ts.max_agents == 1000

    # ── register_agent ─────────────────────────────────────────

    def test_register_agent(self):
        ts = TaskScheduler()
        result = ts.register_agent("a1", "T2_CODE", capacity=3)
        assert result["id"] == "a1"
        assert result["tier"] == "T2_CODE"
        assert result["capacity"] == 3
        assert "a1" in ts.agent_registry

    def test_register_agent_duplicate_raises(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        with pytest.raises(ValueError, match="already registered"):
            ts.register_agent("a1", "T2_CODE")

    def test_register_agent_default_capacity(self):
        ts = TaskScheduler()
        result = ts.register_agent("a1", "T2_CODE")
        assert result["capacity"] == 5

    # ── unregister_agent ───────────────────────────────────────

    def test_unregister_agent(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        assert ts.unregister_agent("a1") is True
        assert "a1" not in ts.agent_registry

    def test_unregister_agent_not_found(self):
        ts = TaskScheduler()
        assert ts.unregister_agent("nonexistent") is False

    def test_unregister_agent_frees_tasks(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        ts.unregister_agent("a1")
        assert ts.task_states["t1"]["assigned_to"] is None
        assert ts.task_states["t1"]["status"] == TaskStatus.PENDING.value

    # ── mark_task_done ─────────────────────────────────────────

    def test_mark_task_done(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        result = ts.mark_task_done("t1", "a1")
        assert result is True
        assert ts.task_states["t1"]["status"] == TaskStatus.COMPLETED.value
        assert ts.stats["completed"] == 1

    def test_mark_task_done_agent_not_found(self):
        ts = TaskScheduler()
        assert ts.mark_task_done("t1", "nonexistent") is False

    def test_mark_task_done_task_not_assigned(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        # Try to mark a different task as done
        assert ts.mark_task_done("nonexistent", "a1") is False

    # ── resolve_dependencies ───────────────────────────────────

    def test_resolve_dependencies_no_deps(self):
        ts = TaskScheduler()
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        assert ts.resolve_dependencies("t1") is True

    def test_resolve_dependencies_not_found(self):
        ts = TaskScheduler()
        assert ts.resolve_dependencies("nonexistent") is False

    def test_resolve_dependencies_uncompleted_blocker(self):
        ts = TaskScheduler()
        ts.schedule_batch([
            {"id": "t1", "tier": "T2_CODE", "priority": "HIGH"},
            {"id": "t2", "tier": "T2_CODE", "priority": "HIGH", "blocked_by": ["t1"]},
        ])
        assert ts.resolve_dependencies("t2") is False

    def test_resolve_dependencies_completed_blocker(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        ts.mark_task_done("t1", "a1")
        ts.schedule_batch([{"id": "t2", "tier": "T2_CODE", "priority": "HIGH", "blocked_by": ["t1"]}])
        assert ts.resolve_dependencies("t2") is True

    def test_resolve_dependencies_blocker_not_in_scheduler(self):
        ts = TaskScheduler()
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH", "blocked_by": ["unknown_blocker"]}])
        # Blocker not in scheduler -> skipped -> deps resolved
        assert ts.resolve_dependencies("t1") is True

    # ── schedule_batch ─────────────────────────────────────────

    def test_schedule_batch_empty(self):
        ts = TaskScheduler()
        decisions = ts.schedule_batch([])
        assert decisions == []

    def test_schedule_batch_assign(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        decisions = ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        assert len(decisions) == 1
        assert decisions[0]["reason"] == "assigned"
        assert decisions[0]["agent_id"] == "a1"
        assert ts.stats["scheduled"] == 1

    def test_schedule_batch_queued_no_agent(self):
        ts = TaskScheduler()
        decisions = ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        assert len(decisions) == 1
        assert decisions[0]["reason"] == "queued"
        assert ts.stats["queued"] == 1

    def test_schedule_batch_queued_wrong_tier(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T1_PLANNING")
        decisions = ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        assert decisions[0]["reason"] == "queued"

    def test_schedule_batch_blocked(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        decisions = ts.schedule_batch([
            {"id": "t1", "tier": "T2_CODE", "priority": "HIGH"},
            {"id": "t2", "tier": "T2_CODE", "priority": "HIGH", "blocked_by": ["t1"]},
        ])
        # t1 should be assigned, t2 should be blocked
        reasons = {d["task_id"]: d["reason"] for d in decisions}
        assert reasons["t1"] == "assigned"
        assert reasons["t2"] == "blocked"
        assert ts.stats["blocked"] == 1

    def test_schedule_batch_duplicate_task_skipped(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        # Phase 1 skips adding to task_states, but Phase 2 still processes
        # the task and generates a decision (it's already assigned)
        decisions = ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        # Task is already assigned, so it gets re-assigned decision
        assert len(decisions) == 1

    def test_schedule_batch_priority_ordering(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=1)
        decisions = ts.schedule_batch([
            {"id": "t_low", "tier": "T2_CODE", "priority": "LOW"},
            {"id": "t_high", "tier": "T2_CODE", "priority": "HIGH"},
        ])
        # HIGH should be assigned first, LOW queued
        reasons = {d["task_id"]: d["reason"] for d in decisions}
        assert reasons["t_high"] == "assigned"
        assert reasons["t_low"] == "queued"

    def test_schedule_batch_deadline_ordering(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=1)
        decisions = ts.schedule_batch([
            {"id": "t_late", "tier": "T2_CODE", "priority": "HIGH", "deadline": 1000},
            {"id": "t_early", "tier": "T2_CODE", "priority": "HIGH", "deadline": 100},
        ])
        # Same priority, earlier deadline should be assigned first
        reasons = {d["task_id"]: d["reason"] for d in decisions}
        assert reasons["t_early"] == "assigned"
        assert reasons["t_late"] == "queued"

    def test_schedule_batch_fifo_ordering(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=1)
        decisions = ts.schedule_batch([
            {"id": "t1", "tier": "T2_CODE", "priority": "HIGH", "created_at": 100},
            {"id": "t2", "tier": "T2_CODE", "priority": "HIGH", "created_at": 50},
        ])
        # Same priority, no deadline, earlier created_at first
        reasons = {d["task_id"]: d["reason"] for d in decisions}
        assert reasons["t2"] == "assigned"
        assert reasons["t1"] == "queued"

    def test_schedule_batch_capacity_exhausted_mid_assign(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=1)
        # Assign first task
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        # Second task should be queued (agent full)
        decisions = ts.schedule_batch([{"id": "t2", "tier": "T2_CODE", "priority": "HIGH"}])
        assert decisions[0]["reason"] == "queued"

    def test_schedule_batch_defaults(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T1_PLANNING")
        decisions = ts.schedule_batch([{"id": "t1"}])
        # Default tier is T1_PLANNING, default priority is MEDIUM
        assert decisions[0]["reason"] == "assigned"
        assert ts.task_states["t1"]["tier"] == "T1_PLANNING"
        assert ts.task_states["t1"]["priority"] == "MEDIUM"

    # ── get_agent_state ────────────────────────────────────────

    def test_get_agent_state(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=3)
        state = ts.get_agent_state("a1")
        assert state["id"] == "a1"
        assert state["tier"] == "T2_CODE"

    def test_get_agent_state_not_found(self):
        ts = TaskScheduler()
        assert ts.get_agent_state("nonexistent") is None

    # ── get_all_agents ─────────────────────────────────────────

    def test_get_all_agents_empty(self):
        ts = TaskScheduler()
        assert ts.get_all_agents() == []

    def test_get_all_agents(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.register_agent("a2", "T1_PLANNING")
        agents = ts.get_all_agents()
        assert len(agents) == 2
        ids = [a["id"] for a in agents]
        assert "a1" in ids
        assert "a2" in ids

    # ── get_pending_tasks ──────────────────────────────────────

    def test_get_pending_tasks(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE", capacity=3)
        ts.schedule_batch([
            {"id": "t1", "tier": "T2_CODE", "priority": "HIGH"},
            {"id": "t2", "tier": "T2_CODE", "priority": "MEDIUM"},
        ])
        pending = ts.get_pending_tasks("a1")
        assert len(pending) == 2
        task_ids = [t["id"] for t in pending]
        assert "t1" in task_ids
        assert "t2" in task_ids

    def test_get_pending_tasks_agent_not_found(self):
        ts = TaskScheduler()
        assert ts.get_pending_tasks("nonexistent") == []

    def test_get_pending_tasks_empty(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        assert ts.get_pending_tasks("a1") == []

    def test_get_pending_tasks_returns_deepcopy(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        pending = ts.get_pending_tasks("a1")
        pending[0]["status"] = "MODIFIED"
        # Original should be unchanged
        assert ts.task_states["t1"]["status"] != "MODIFIED"

    # ── get_scheduling_stats ───────────────────────────────────

    def test_get_scheduling_stats(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        stats = ts.get_scheduling_stats()
        assert stats["scheduled"] == 1
        assert stats["blocked"] == 0
        assert stats["queued"] == 0
        assert stats["completed"] == 0
        assert stats["total_agents"] == 1
        assert stats["total_tasks"] == 1

    # ── get_task_state ─────────────────────────────────────────

    def test_get_task_state(self):
        ts = TaskScheduler()
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        state = ts.get_task_state("t1")
        assert state["id"] == "t1"
        assert state["tier"] == "T2_CODE"

    def test_get_task_state_not_found(self):
        ts = TaskScheduler()
        assert ts.get_task_state("nonexistent") is None

    def test_get_task_state_returns_deepcopy(self):
        ts = TaskScheduler()
        ts.schedule_batch([{"id": "t1", "tier": "T2_CODE", "priority": "HIGH"}])
        state = ts.get_task_state("t1")
        state["status"] = "MODIFIED"
        assert ts.task_states["t1"]["status"] != "MODIFIED"

    # ── get_fairness_metrics ───────────────────────────────────

    def test_get_fairness_metrics_empty(self):
        ts = TaskScheduler()
        assert ts.get_fairness_metrics() == {}

    def test_get_fairness_metrics_no_tasks(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.register_agent("a2", "T2_CODE")
        metrics = ts.get_fairness_metrics()
        assert "T2_CODE" in metrics
        assert metrics["T2_CODE"]["agents"] == 2
        assert metrics["T2_CODE"]["avg_tasks_per_agent"] == 0.0
        assert metrics["T2_CODE"]["variance"] == 0.0

    def test_get_fairness_metrics_with_tasks(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.register_agent("a2", "T2_CODE")
        ts.schedule_batch([
            {"id": "t1", "tier": "T2_CODE", "priority": "HIGH"},
            {"id": "t2", "tier": "T2_CODE", "priority": "HIGH"},
        ])
        metrics = ts.get_fairness_metrics()
        assert "T2_CODE" in metrics
        assert metrics["T2_CODE"]["agents"] == 2
        assert metrics["T2_CODE"]["avg_tasks_per_agent"] == 1.0

    def test_get_fairness_metrics_multiple_tiers(self):
        ts = TaskScheduler()
        ts.register_agent("a1", "T2_CODE")
        ts.register_agent("a2", "T1_PLANNING")
        metrics = ts.get_fairness_metrics()
        assert "T2_CODE" in metrics
        assert "T1_PLANNING" in metrics

    # ── Thread safety ──────────────────────────────────────────

    def test_thread_safety_register(self):
        ts = TaskScheduler()
        counter = [0]
        counter_lock = threading.Lock()
        errors = []
        def register_agents():
            try:
                for i in range(10):
                    with counter_lock:
                        idx = counter[0]
                        counter[0] += 1
                    ts.register_agent(f"agent_{idx}", "T2_CODE")
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=register_agents) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(ts.agent_registry) == 50
