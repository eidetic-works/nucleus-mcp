"""
Test Suite: AgentPool + Hardening Integration
==============================================
Tests agent_pool.py with security hardening modules applied.

Addresses Cullinan II finding: "6 critical runtime modules have ZERO test coverage"
Agent: CODE_FORCE via Windsurf
Date: Feb 24, 2026
"""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.agent_pool import (
    Agent,
    AgentPool,
    AgentStatus,
    ExhaustionReason,
    TaskTier,
    MODEL_CONFIGS,
)

# Import hardening modules
from mcp_server_nucleus.runtime.hardening import (
    safe_path,
    safe_write_json,
    safe_read_json,
    safe_error,
    PathTraversalError,
)
from mcp_server_nucleus.runtime.path_sanitizer import sanitize_filename
from mcp_server_nucleus.runtime.timeout_handler import with_timeout, TimeoutError as NucleusTimeoutError


class TestAgentLifecycle:
    """Test Agent class lifecycle and state transitions."""

    def test_agent_spawn(self):
        """Test agent spawns in AVAILABLE state."""
        agent = Agent(
            agent_id="test_agent_001",
            model="gemini_3_pro_high",
            tier="T1_PLANNING"
        )
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.id == "test_agent_001"
        assert agent.model == "gemini_3_pro_high"
        assert agent.tier == "T1_PLANNING"

    def test_agent_capacity(self):
        """Test agent capacity tracking."""
        agent = Agent("agent_002", "claude_opus_4_5", "T2_CODE", capacity=5)
        assert agent.is_available()
        assert agent.has_capacity(5)
        assert not agent.has_capacity(6)

    def test_agent_task_assignment(self):
        """Test task assignment to agent."""
        agent = Agent("agent_003", "claude_sonnet_4", "T3_REVIEW", capacity=2)
        
        # Assign first task
        assert agent.assign_task("task_001")
        assert "task_001" in agent.current_tasks
        assert agent.status == AgentStatus.AVAILABLE  # Still has capacity
        
        # Assign second task (fills capacity)
        assert agent.assign_task("task_002")
        assert agent.status == AgentStatus.BUSY  # Now at capacity
        
        # Cannot assign third task
        assert not agent.assign_task("task_003")

    def test_agent_task_completion(self):
        """Test task completion transitions."""
        agent = Agent("agent_004", "gpt_4o", "T2_CODE", capacity=2)
        agent.assign_task("task_001")
        agent.assign_task("task_002")
        assert agent.status == AgentStatus.BUSY
        
        # Complete one task
        assert agent.complete_task("task_001")
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.tasks_completed == 1

    def test_agent_reset_cycle_gemini(self):
        """Test Gemini agents have 5-hour reset cycles."""
        agent = Agent("gemini_agent", "gemini_3_pro_high", "T1_PLANNING")
        assert agent.reset_cycle is not None
        assert agent.reset_cycle["hours"] == 5

    def test_agent_reset_cycle_opus_unlimited(self):
        """Test Opus agents have unlimited reset cycles."""
        agent = Agent("opus_agent", "claude_opus_4_5", "T2_CODE")
        assert agent.reset_cycle is None
        assert agent.get_time_to_reset() is None

    def test_agent_heartbeat(self):
        """Test heartbeat tracking."""
        agent = Agent("heartbeat_agent", "claude_sonnet_4", "T1_PLANNING")
        initial_heartbeat = agent.last_heartbeat
        
        time.sleep(0.01)
        agent.update_heartbeat()
        
        assert agent.last_heartbeat > initial_heartbeat
        assert not agent.is_stale(threshold_seconds=1)

    def test_agent_cleanup_scrubs_state(self):
        """Test MDR_014 context scrub during cleanup."""
        agent = Agent("cleanup_agent", "gemini_3_pro_high", "T2_CODE")
        agent.context = {"secret_key": "should_be_scrubbed"}
        agent.total_cost = 100.0
        agent.tasks_completed = 50
        
        scrub_result = agent.cleanup()
        
        assert agent.context == {}
        assert agent.total_cost == 0.0
        assert "cleanup_agent" in scrub_result["agent_id"]


class TestAgentPoolOperations:
    """Test AgentPool orchestration."""

    def test_pool_spawn_agent(self):
        """Test spawning agents in pool."""
        pool = AgentPool()
        
        result = pool.spawn_agent(
            agent_id="pool_agent_001",
            model="claude_opus_4_5",
            tier="T2_CODE"
        )
        
        # spawn_agent returns agent.to_dict() on success
        assert result["id"] == "pool_agent_001"
        assert result["model"] == "claude_opus_4_5"
        assert pool.get_pool_status()["total_agents"] == 1

    def test_pool_prevent_duplicate_spawn(self):
        """Test duplicate agent ID prevention."""
        pool = AgentPool()
        pool.spawn_agent("duplicate_test", "claude_sonnet_4", "T1_PLANNING")
        
        # spawn_agent raises ValueError on duplicate
        with pytest.raises(ValueError) as exc_info:
            pool.spawn_agent("duplicate_test", "claude_sonnet_4", "T1_PLANNING")
        
        assert "already exists" in str(exc_info.value)

    def test_pool_assign_task(self):
        """Test task assignment through pool."""
        pool = AgentPool()
        pool.spawn_agent("worker_001", "claude_opus_4_5", "T2_CODE")
        
        result = pool.assign_task(
            task_id="task_abc",
            agent_id="worker_001",
            tier="T2_CODE"
        )
        
        assert result["success"]
        assert result["agent_id"] == "worker_001"

    def test_pool_complete_task(self):
        """Test task completion through pool."""
        pool = AgentPool()
        pool.spawn_agent("completer_001", "gpt_4o", "T3_REVIEW")
        pool.assign_task("complete_me", agent_id="completer_001", tier="T3_REVIEW")
        
        result = pool.complete_task("complete_me", "completer_001", cost=0.05)
        
        assert result["success"]
        assert result["agent_total_cost"] == 0.05

    def test_pool_status_metrics(self):
        """Test pool status metrics."""
        pool = AgentPool()
        pool.spawn_agent("metrics_001", "gemini_3_pro_high", "T1_PLANNING", capacity=10)
        pool.spawn_agent("metrics_002", "claude_opus_4_5", "T2_CODE", capacity=5)
        
        status = pool.get_pool_status()
        
        assert status["total_agents"] == 2
        assert status["total_capacity"] == 15
        assert status["utilization"] == 0.0


class TestAgentPoolConcurrency:
    """Test concurrent operations with hardening."""

    def test_concurrent_task_assignment(self):
        """Test thread-safe task assignment."""
        pool = AgentPool()
        pool.spawn_agent("concurrent_agent", "claude_opus_4_5", "T2_CODE", capacity=100)
        
        errors = []
        successes = []
        
        def assign_task(task_num):
            try:
                result = pool.assign_task(
                    f"concurrent_task_{task_num}",
                    agent_id="concurrent_agent",
                    tier="T2_CODE"
                )
                if result["success"]:
                    successes.append(task_num)
                return result
            except Exception as e:
                errors.append(str(e))
                return {"success": False, "error": str(e)}
        
        # Run 50 concurrent assignments
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(assign_task, i) for i in range(50)]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(successes) == 50

    def test_concurrent_spawn_and_assign(self):
        """Test mixed spawn and assign operations."""
        pool = AgentPool()
        
        def spawn_and_assign(agent_num):
            agent_id = f"mixed_agent_{agent_num}"
            try:
                spawn_result = pool.spawn_agent(agent_id, "gemini_3_pro_low", "T1_PLANNING")
                # spawn_agent returns agent.to_dict() on success
                if spawn_result.get("id") == agent_id:
                    assign_result = pool.assign_task(f"mixed_task_{agent_num}", agent_id=agent_id, tier="T1_PLANNING")
                    return assign_result.get("success", False)
            except ValueError:
                pass
            return False
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(spawn_and_assign, range(20)))
        
        assert all(results), "All spawn+assign operations should succeed"
        assert pool.get_pool_status()["total_agents"] == 20


class TestAgentIdSanitization:
    """Test agent ID sanitization using hardening modules."""

    def test_agent_id_path_traversal_prevention(self):
        """Prevent path traversal in agent IDs when persisting state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir) / "agents"
            base_dir.mkdir()
            
            # Malicious agent ID
            malicious_id = "../../../etc/passwd"
            
            # Should sanitize to safe filename
            safe_id = sanitize_filename(malicious_id)
            assert ".." not in safe_id
            assert "/" not in safe_id
            
            # Safe path resolution should work
            with pytest.raises(PathTraversalError):
                safe_path(malicious_id, base_dir)

    def test_agent_id_special_characters(self):
        """Test agent IDs with special characters."""
        special_ids = [
            "agent<script>alert('xss')</script>",
            "agent\x00null",
            "agent%2F%2e%2e",
            "agent with spaces",
        ]
        
        for malicious_id in special_ids:
            safe_id = sanitize_filename(malicious_id)
            assert "<" not in safe_id
            assert "\x00" not in safe_id
            assert ".." not in safe_id


class TestAgentStatePersistence:
    """Test agent state persistence with hardening."""

    def test_safe_agent_state_write(self):
        """Test atomic agent state writes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "agent_state.json"
            
            agent = Agent("persist_agent", "claude_opus_4_5", "T2_CODE")
            state = agent.to_dict()
            
            safe_write_json(state_file, state)
            
            loaded = safe_read_json(state_file)
            assert loaded["id"] == "persist_agent"
            assert loaded["model"] == "claude_opus_4_5"

    def test_unicode_agent_state(self):
        """Test agent state with unicode content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "unicode_state.json"
            
            state = {
                "agent_id": "unicode_agent_中文",
                "context": {"hindi": "हिंदी", "emoji": "🚀"},
            }
            
            safe_write_json(state_file, state)
            loaded = safe_read_json(state_file)
            
            assert loaded["context"]["hindi"] == "हिंदी"
            assert loaded["context"]["emoji"] == "🚀"


class TestAgentPoolErrorHandling:
    """Test error handling with sanitization."""

    def test_error_sanitization(self):
        """Test that internal errors are sanitized."""
        try:
            # Simulate internal error with sensitive path
            raise FileNotFoundError("/Users/secret/internal/agent_config.json")
        except Exception as e:
            sanitized = safe_error(e, "agent_pool")
        
        assert "/Users/secret" not in sanitized
        assert "internal" not in sanitized.lower() or "internal error" in sanitized.lower()

    def test_pool_invalid_agent_error(self):
        """Test pool handles invalid agent gracefully."""
        pool = AgentPool()
        
        result = pool.assign_task("task_001", agent_id="nonexistent_agent", tier="T2_CODE")
        
        assert not result["success"]
        assert "not found" in result["error"].lower()


class TestAgentPoolScaling:
    """Test scaling to Antigravity specifications (1→100→1000 agents)."""

    def test_scale_100_agents(self):
        """Test pool with 100 agents."""
        pool = AgentPool()
        
        for i in range(100):
            result = pool.spawn_agent(
                f"scale_agent_{i:03d}",
                "gemini_3_pro_low",
                "T1_PLANNING"
            )
            # spawn_agent returns agent.to_dict() on success
            assert result["id"] == f"scale_agent_{i:03d}", f"Failed to spawn agent {i}"
        
        status = pool.get_pool_status()
        assert status["total_agents"] == 100

    def test_task_distribution_100_agents(self):
        """Test task distribution across 100 agents."""
        pool = AgentPool()
        
        # Spawn 100 agents
        for i in range(100):
            pool.spawn_agent(f"dist_agent_{i:03d}", "claude_sonnet_4", "T2_CODE")
        
        # Assign 500 tasks (5 per agent)
        for i in range(500):
            agent_id = f"dist_agent_{i % 100:03d}"
            result = pool.assign_task(f"dist_task_{i:03d}", agent_id=agent_id, tier="T2_CODE")
            assert result["success"], f"Failed to assign task {i}"
        
        status = pool.get_pool_status()
        assert status["active_tasks"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
