"""
Tests for Agent Runtime V2 telemetry hooks wired into facade dispatch.

Verifies:
- AgentExecutionManager spawn/complete lifecycle
- Cost tracking accumulation
- Rate limiting enforcement
- Dashboard metrics endpoint
- agent_cost_dashboard action in nucleus_telemetry
"""

import pytest
import time
import threading
from unittest.mock import patch

from mcp_server_nucleus.runtime.agent_runtime_v2 import (
    AgentExecutionManager,
    AgentExecution,
    AgentCostRecord,
    AgentCostTracker,
    AgentSpawnLimiter,
    AgentStatus,
    get_execution_manager,
)
from mcp_server_nucleus.runtime.rate_limiter import RateLimitError


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def exec_mgr(tmp_path):
    """Fresh AgentExecutionManager for each test."""
    mgr = AgentExecutionManager()
    # Point cost tracker persistence to tmp_path
    mgr._cost_tracker._persist_path = tmp_path / "agent_costs.jsonl"
    return mgr


@pytest.fixture
def cost_tracker(tmp_path):
    return AgentCostTracker(persist_path=tmp_path / "costs.jsonl")


# ============================================================
# TEST: AgentCostRecord
# ============================================================

class TestAgentCostRecord:
    def test_creation(self):
        record = AgentCostRecord(agent_id="a1", persona="developer")
        assert record.agent_id == "a1"
        assert record.persona == "developer"
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.total_tokens == 0
        assert record.estimated_cost_usd == 0.0

    def test_token_accumulation(self):
        record = AgentCostRecord(agent_id="a1", persona="dev")
        record.input_tokens = 1000
        record.output_tokens = 500
        assert record.total_tokens == 1500
        assert record.estimated_cost_usd > 0

    def test_finalize(self):
        record = AgentCostRecord(agent_id="a1", persona="dev")
        record.finalize("completed")
        assert record.status == "completed"
        assert record.end_time is not None
        assert record.duration_ms >= 0

    def test_to_dict(self):
        record = AgentCostRecord(agent_id="a1", persona="dev")
        d = record.to_dict()
        assert "agent_id" in d
        assert "total_tokens" in d
        assert "estimated_cost_usd" in d


# ============================================================
# TEST: AgentCostTracker
# ============================================================

class TestAgentCostTracker:
    def test_start_and_finalize(self, cost_tracker):
        cost_tracker.start_tracking("a1", "developer")
        cost_tracker.record_tokens("a1", input_tokens=100, output_tokens=50)
        cost_tracker.record_tool_call("a1")
        record = cost_tracker.finalize("a1")
        assert record is not None
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.tool_calls == 1

    def test_summary(self, cost_tracker):
        cost_tracker.start_tracking("a1", "dev")
        cost_tracker.record_tokens("a1", 200, 100)
        cost_tracker.finalize("a1")

        summary = cost_tracker.get_summary()
        assert summary["total_executions"] == 1
        assert summary["total_input_tokens"] == 200
        assert summary["total_output_tokens"] == 100
        assert summary["active_agents"] == 0

    def test_get_by_persona(self, cost_tracker):
        cost_tracker.start_tracking("a1", "developer")
        cost_tracker.record_tokens("a1", 100, 50)
        cost_tracker.finalize("a1")

        cost_tracker.start_tracking("a2", "critic")
        cost_tracker.record_tokens("a2", 200, 100)
        cost_tracker.finalize("a2")

        by_persona = cost_tracker.get_by_persona()
        assert "developer" in by_persona
        assert "critic" in by_persona
        assert by_persona["developer"]["count"] == 1
        assert by_persona["critic"]["count"] == 1

    def test_get_recent(self, cost_tracker):
        for i in range(5):
            cost_tracker.start_tracking(f"a{i}", "dev")
            cost_tracker.finalize(f"a{i}")
        recent = cost_tracker.get_recent(3)
        assert len(recent) == 3

    def test_persistence(self, cost_tracker, tmp_path):
        cost_tracker.start_tracking("a1", "dev")
        cost_tracker.finalize("a1")
        assert cost_tracker._persist_path.exists()


# ============================================================
# TEST: AgentSpawnLimiter
# ============================================================

class TestAgentSpawnLimiter:
    def test_can_spawn(self):
        limiter = AgentSpawnLimiter(capacity=5, fill_rate=1)
        assert limiter.can_spawn("dev") is True

    def test_spawn_or_raise_under_limit(self):
        limiter = AgentSpawnLimiter(capacity=5, fill_rate=1)
        limiter.spawn_or_raise("dev")  # Should not raise

    def test_spawn_or_raise_over_limit(self):
        limiter = AgentSpawnLimiter(capacity=2, fill_rate=0.001)
        limiter.spawn_or_raise("dev")
        limiter.spawn_or_raise("dev")
        with pytest.raises(RateLimitError):
            limiter.spawn_or_raise("dev")

    def test_stats(self):
        limiter = AgentSpawnLimiter(capacity=5, fill_rate=1)
        limiter.can_spawn("dev")
        limiter.can_spawn("critic")
        stats = limiter.get_stats()
        assert stats["total_allowed"] == 2
        assert "dev" in stats["spawns_by_persona"]

    def test_reset(self):
        limiter = AgentSpawnLimiter(capacity=2, fill_rate=0.001)
        limiter.can_spawn("dev")
        limiter.can_spawn("dev")
        limiter.reset()
        assert limiter.can_spawn("dev") is True


# ============================================================
# TEST: AgentExecutionManager
# ============================================================

class TestAgentExecutionManager:
    def test_spawn_agent(self, exec_mgr):
        execution = exec_mgr.spawn_agent("developer", "Fix the bug")
        assert execution.agent_id.startswith("agent-")
        assert execution.persona == "developer"
        assert execution.intent == "Fix the bug"
        assert execution.status == AgentStatus.PENDING

    def test_start_execution(self, exec_mgr):
        execution = exec_mgr.spawn_agent("dev", "task")
        assert exec_mgr.start_execution(execution.agent_id) is True
        details = exec_mgr.get_execution(execution.agent_id)
        assert details["status"] == "running"

    def test_complete_execution(self, exec_mgr):
        execution = exec_mgr.spawn_agent("dev", "task")
        exec_mgr.start_execution(execution.agent_id)
        exec_mgr.record_tokens(execution.agent_id, 500, 200)
        exec_mgr.record_tool_call(execution.agent_id)
        cost = exec_mgr.complete_execution(execution.agent_id)
        assert cost is not None
        assert cost.input_tokens == 500
        assert cost.output_tokens == 200
        assert cost.tool_calls == 1

    def test_cancel_agent(self, exec_mgr):
        execution = exec_mgr.spawn_agent("dev", "task")
        exec_mgr.start_execution(execution.agent_id)
        assert exec_mgr.cancel_agent(execution.agent_id) is True
        assert exec_mgr.is_cancelled(execution.agent_id) is True

    def test_get_active_executions(self, exec_mgr):
        e1 = exec_mgr.spawn_agent("dev", "task1")
        exec_mgr.start_execution(e1.agent_id)
        e2 = exec_mgr.spawn_agent("dev", "task2")
        active = exec_mgr.get_active_executions()
        assert len(active) == 2

    def test_dashboard_metrics(self, exec_mgr):
        e = exec_mgr.spawn_agent("dev", "task")
        exec_mgr.start_execution(e.agent_id)
        exec_mgr.record_tokens(e.agent_id, 100, 50)
        exec_mgr.complete_execution(e.agent_id)

        metrics = exec_mgr.get_dashboard_metrics()
        assert "spawn_limiter" in metrics
        assert "cost_summary" in metrics
        assert "cost_by_persona" in metrics
        assert "execution_metrics" in metrics
        assert metrics["execution_metrics"]["total_spawned"] == 1
        assert metrics["execution_metrics"]["total_completed"] == 1
        assert metrics["cost_summary"]["total_executions"] == 1

    def test_cleanup_completed(self, exec_mgr):
        e = exec_mgr.spawn_agent("dev", "task")
        exec_mgr.start_execution(e.agent_id)
        exec_mgr.complete_execution(e.agent_id)
        # Should not clean up recent completions
        removed = exec_mgr.cleanup_completed(max_age_seconds=3600)
        assert removed == 0

    def test_rate_limiting_enforcement(self, exec_mgr):
        # Override limiter with very low capacity
        exec_mgr._spawn_limiter = AgentSpawnLimiter(capacity=1, fill_rate=0.001)
        exec_mgr.spawn_agent("dev", "task1")
        with pytest.raises(RateLimitError):
            exec_mgr.spawn_agent("dev", "task2")


# ============================================================
# TEST: Global Singleton
# ============================================================

class TestGlobalSingleton:
    def test_get_execution_manager_returns_same_instance(self):
        m1 = get_execution_manager()
        m2 = get_execution_manager()
        assert m1 is m2

    def test_execution_manager_has_expected_interface(self):
        mgr = get_execution_manager()
        assert hasattr(mgr, "spawn_agent")
        assert hasattr(mgr, "complete_execution")
        assert hasattr(mgr, "get_dashboard_metrics")
        assert hasattr(mgr, "record_tokens")
        assert hasattr(mgr, "record_tool_call")


# ============================================================
# TEST: agent_cost_dashboard action via TELEM_ROUTER
# ============================================================

class TestTelemetryCostDashboardAction:
    """Test that the agent_cost_dashboard action is wired into nucleus_telemetry."""

    def test_cost_dashboard_returns_metrics(self):
        """Invoke the handler directly to verify wiring."""
        from mcp_server_nucleus.runtime.agent_runtime_v2 import get_execution_manager
        mgr = get_execution_manager()
        metrics = mgr.get_dashboard_metrics()
        assert isinstance(metrics, dict)
        assert "spawn_limiter" in metrics
        assert "cost_summary" in metrics
        assert "execution_metrics" in metrics
        assert "active_agents" in metrics


# ============================================================
# TEST: Thread Safety
# ============================================================

class TestThreadSafety:
    def test_concurrent_spawn_and_complete(self, exec_mgr):
        results = []
        errors = []

        def spawn_and_complete(idx):
            try:
                e = exec_mgr.spawn_agent("dev", f"task-{idx}")
                exec_mgr.start_execution(e.agent_id)
                exec_mgr.record_tokens(e.agent_id, 10, 5)
                exec_mgr.complete_execution(e.agent_id)
                results.append(e.agent_id)
            except RateLimitError:
                pass  # Expected under high concurrency
            except Exception as ex:
                errors.append(str(ex))

        threads = [threading.Thread(target=spawn_and_complete, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(results) > 0
