"""
Tests for Agent Runtime V2 - Enhanced Agent Execution Engine
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from mcp_server_nucleus.runtime.agent_runtime_v2 import (
    AgentSpawnLimiter,
    AgentCostTracker,
    AgentCostRecord,
    AgentExecution,
    AgentExecutionManager,
    AgentStatus,
    get_execution_manager,
    with_timeout,
    check_cancellation,
    RateLimitError,
)


class TestAgentCostRecord:
    """Tests for AgentCostRecord."""
    
    def test_create_record(self):
        record = AgentCostRecord(agent_id="test-1", persona="devops")
        assert record.agent_id == "test-1"
        assert record.persona == "devops"
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.status == "pending"
    
    def test_token_tracking(self):
        record = AgentCostRecord(agent_id="test-2", persona="researcher")
        record.input_tokens = 100
        record.output_tokens = 50
        assert record.total_tokens == 150
        assert record.estimated_cost_usd > 0
    
    def test_finalize(self):
        record = AgentCostRecord(agent_id="test-3", persona="critic")
        time.sleep(0.01)  # Small delay
        record.finalize("completed")
        assert record.status == "completed"
        assert record.end_time is not None
        assert record.duration_ms > 0
    
    def test_to_dict(self):
        record = AgentCostRecord(agent_id="test-4", persona="synthesizer")
        record.input_tokens = 500
        record.output_tokens = 200
        d = record.to_dict()
        assert "agent_id" in d
        assert "total_tokens" in d
        assert "estimated_cost_usd" in d
        assert d["total_tokens"] == 700


class TestAgentSpawnLimiter:
    """Tests for AgentSpawnLimiter."""
    
    def test_basic_spawn(self):
        limiter = AgentSpawnLimiter(capacity=5, fill_rate=1)
        assert limiter.can_spawn("devops") is True
        assert limiter.can_spawn("devops") is True
    
    def test_rate_limit_exceeded(self):
        limiter = AgentSpawnLimiter(capacity=2, fill_rate=0.1)
        assert limiter.can_spawn() is True
        assert limiter.can_spawn() is True
        assert limiter.can_spawn() is False  # Exceeded
    
    def test_spawn_or_raise(self):
        limiter = AgentSpawnLimiter(capacity=1, fill_rate=0.1)
        limiter.spawn_or_raise("test")  # Should work
        with pytest.raises(RateLimitError):
            limiter.spawn_or_raise("test")  # Should raise
    
    def test_stats(self):
        limiter = AgentSpawnLimiter(capacity=10, fill_rate=1)
        limiter.can_spawn("devops")
        limiter.can_spawn("researcher")
        limiter.can_spawn("devops")
        
        stats = limiter.get_stats()
        assert stats["total_allowed"] == 3
        assert stats["spawns_by_persona"]["devops"] == 2
        assert stats["spawns_by_persona"]["researcher"] == 1
    
    def test_reset(self):
        limiter = AgentSpawnLimiter(capacity=2, fill_rate=0.1)
        limiter.can_spawn()
        limiter.can_spawn()
        limiter.reset()
        assert limiter.can_spawn() is True


class TestAgentCostTracker:
    """Tests for AgentCostTracker."""
    
    @pytest.fixture
    def tracker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield AgentCostTracker(persist_path=Path(tmpdir) / "costs.jsonl")
    
    def test_start_tracking(self, tracker):
        record = tracker.start_tracking("agent-1", "devops")
        assert record.agent_id == "agent-1"
        assert record.persona == "devops"
    
    def test_record_tokens(self, tracker):
        tracker.start_tracking("agent-2", "researcher")
        tracker.record_tokens("agent-2", input_tokens=100, output_tokens=50)
        
        summary = tracker.get_summary()
        assert summary["active_agents"] == 1
    
    def test_finalize(self, tracker):
        tracker.start_tracking("agent-3", "critic")
        tracker.record_tokens("agent-3", input_tokens=200)
        tracker.record_tool_call("agent-3")
        
        record = tracker.finalize("agent-3", "completed")
        assert record.input_tokens == 200
        assert record.tool_calls == 1
        assert record.status == "completed"
    
    def test_summary(self, tracker):
        tracker.start_tracking("a1", "devops")
        tracker.record_tokens("a1", 100, 50)
        tracker.finalize("a1")
        
        tracker.start_tracking("a2", "devops")
        tracker.record_tokens("a2", 200, 100)
        tracker.finalize("a2")
        
        summary = tracker.get_summary()
        assert summary["total_executions"] == 2
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150
    
    def test_by_persona(self, tracker):
        tracker.start_tracking("a1", "devops")
        tracker.finalize("a1")
        tracker.start_tracking("a2", "researcher")
        tracker.finalize("a2")
        tracker.start_tracking("a3", "devops")
        tracker.finalize("a3")
        
        by_persona = tracker.get_by_persona()
        assert by_persona["devops"]["count"] == 2
        assert by_persona["researcher"]["count"] == 1


class TestAgentExecution:
    """Tests for AgentExecution."""
    
    def test_create(self):
        execution = AgentExecution(
            agent_id="test-1",
            persona="devops",
            intent="deploy app"
        )
        assert execution.status == AgentStatus.PENDING
        assert execution.is_cancelled() is False
    
    def test_cancel(self):
        execution = AgentExecution(
            agent_id="test-2",
            persona="researcher",
            intent="search web"
        )
        execution.status = AgentStatus.RUNNING
        assert execution.cancel() is True
        assert execution.is_cancelled() is True
        assert execution.status == AgentStatus.CANCELLED
    
    def test_to_dict(self):
        execution = AgentExecution(
            agent_id="test-3",
            persona="critic",
            intent="review code"
        )
        d = execution.to_dict()
        assert d["agent_id"] == "test-3"
        assert d["status"] == "pending"


class TestAgentExecutionManager:
    """Tests for AgentExecutionManager."""
    
    @pytest.fixture
    def manager(self):
        mgr = AgentExecutionManager()
        mgr._spawn_limiter = AgentSpawnLimiter(capacity=100, fill_rate=10)
        return mgr
    
    def test_spawn_agent(self, manager):
        execution = manager.spawn_agent("devops", "deploy app")
        assert execution.persona == "devops"
        assert execution.intent == "deploy app"
        assert execution.status == AgentStatus.PENDING
    
    def test_spawn_rate_limited(self):
        manager = AgentExecutionManager()
        manager._spawn_limiter = AgentSpawnLimiter(capacity=1, fill_rate=0.1)
        
        manager.spawn_agent("devops", "task 1")
        with pytest.raises(RateLimitError):
            manager.spawn_agent("devops", "task 2")
    
    def test_execution_lifecycle(self, manager):
        execution = manager.spawn_agent("researcher", "search")
        agent_id = execution.agent_id
        
        manager.start_execution(agent_id)
        manager.record_tokens(agent_id, 100, 50)
        manager.record_tool_call(agent_id)
        cost = manager.complete_execution(agent_id, "completed")
        
        assert cost.input_tokens == 100
        assert cost.tool_calls == 1
        assert manager._metrics["total_completed"] == 1
    
    def test_cancel_agent(self, manager):
        execution = manager.spawn_agent("critic", "review")
        agent_id = execution.agent_id
        manager.start_execution(agent_id)
        
        assert manager.cancel_agent(agent_id) is True
        assert manager.is_cancelled(agent_id) is True
    
    def test_dashboard_metrics(self, manager):
        manager.spawn_agent("devops", "task 1")
        manager.spawn_agent("researcher", "task 2")
        
        metrics = manager.get_dashboard_metrics()
        assert "spawn_limiter" in metrics
        assert "cost_summary" in metrics
        assert "execution_metrics" in metrics
        assert len(metrics["active_agents"]) == 2
    
    def test_cleanup_completed(self, manager):
        execution = manager.spawn_agent("devops", "task")
        manager.complete_execution(execution.agent_id)
        
        # Should not clean up recent
        removed = manager.cleanup_completed(max_age_seconds=3600)
        assert removed == 0
        
        # Force cleanup
        removed = manager.cleanup_completed(max_age_seconds=0)
        assert removed == 1


class TestTimeoutAndCancellation:
    """Tests for timeout decorator and cancellation checker."""
    
    def test_timeout_decorator(self):
        """Test timeout decorator using asyncio.run."""
        @with_timeout(1)
        async def slow_task(agent_id: str):
            await asyncio.sleep(10)
            return "done"
        
        with pytest.raises(TimeoutError):
            asyncio.run(slow_task(agent_id="test"))
    
    def test_no_timeout(self):
        """Test fast task completes without timeout."""
        @with_timeout(10)
        async def fast_task(agent_id: str):
            await asyncio.sleep(0.01)
            return "done"
        
        result = asyncio.run(fast_task(agent_id="test"))
        assert result == "done"
    
    def test_check_cancellation(self):
        manager = get_execution_manager()
        execution = manager.spawn_agent("test", "task")
        manager.start_execution(execution.agent_id)
        
        # Should not raise
        check_cancellation(execution.agent_id)
        
        # Cancel and check
        manager.cancel_agent(execution.agent_id)
        with pytest.raises(InterruptedError):
            check_cancellation(execution.agent_id)
