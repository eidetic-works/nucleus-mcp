"""Tests for mcp-server-nucleus core functions.

Note: These tests require pytest. Run with: pytest tests/test_tools.py
Skip gracefully when pytest is not installed.
"""

import unittest
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy pytest module for decorators
    class DummyPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        @staticmethod
        def mark(*args, **kwargs):
            return lambda f: f
    pytest = DummyPytest()

import json
import tempfile
import os
from pathlib import Path

# Skip all tests if pytest not available
if not PYTEST_AVAILABLE:
    raise unittest.SkipTest("pytest not installed - skipping test_tools.py")

# Set up test brain path before importing
TEST_BRAIN = None

@pytest.fixture(autouse=True)
def setup_test_brain(tmp_path):
    """Create a temporary .brain/ structure for testing."""
    global TEST_BRAIN
    
    # Create brain structure
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    (brain / "artifacts").mkdir()
    (brain / "artifacts" / "research").mkdir()
    
    # Create initial files
    (brain / "ledger" / "events.jsonl").write_text("")
    (brain / "ledger" / "state.json").write_text(json.dumps({
        "current_sprint": {"name": "Test Sprint", "focus": "Testing"}
    }))
    (brain / "ledger" / "triggers.json").write_text(json.dumps({
        "triggers": [
            {"event_type": "task_completed", "target_agent": "synthesizer"},
            {"event_type": "research_done", "target_agent": "architect"}
        ]
    }))
    
    # Set environment variable
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)
    TEST_BRAIN = brain
    
    yield brain
    
    # Cleanup
    del os.environ["NUCLEAR_BRAIN_PATH"]


class TestEventTools:
    """Tests for event emission and reading."""
    
    def test_emit_event(self, setup_test_brain):
        from mcp_server_nucleus.runtime.event_ops import _emit_event
        
        event_id = _emit_event(
            event_type="test_event",
            emitter="pytest",
            data={"key": "value"},
            description="Test description"
        )
        
        assert event_id.startswith("evt-")
        
        # Verify event was written
        events_file = setup_test_brain / "ledger" / "events.jsonl"
        content = events_file.read_text()
        assert "test_event" in content
        assert "pytest" in content
    
    def test_read_events(self, setup_test_brain):
        from mcp_server_nucleus.runtime.event_ops import _emit_event, _read_events
        
        # Emit a few events
        _emit_event("event1", "test", {}, "")
        _emit_event("event2", "test", {}, "")
        _emit_event("event3", "test", {}, "")
        
        events = _read_events(limit=2)
        assert len(events) == 2
        assert events[-1]["type"] == "event3"


class TestStateTools:
    """Tests for state get/update."""
    
    def test_get_state(self, setup_test_brain):
        from mcp_server_nucleus import _get_state
        
        state = _get_state()
        assert "current_sprint" in state
        assert state["current_sprint"]["name"] == "Test Sprint"
    
    def test_get_state_path(self, setup_test_brain):
        from mcp_server_nucleus import _get_state
        
        focus = _get_state("current_sprint.focus")
        assert focus == "Testing"
    
    def test_update_state(self, setup_test_brain):
        from mcp_server_nucleus import _update_state, _get_state
        
        result = _update_state({"new_key": "new_value"})
        assert "success" in result.lower()
        
        state = _get_state()
        assert state["new_key"] == "new_value"


class TestTriggerTools:
    """Tests for trigger functions."""
    
    def test_get_triggers(self, setup_test_brain):
        from mcp_server_nucleus.runtime.trigger_ops import _get_triggers_impl as _get_triggers
        
        triggers = _get_triggers()
        assert len(triggers) == 2
        assert triggers[0]["target_agent"] == "synthesizer"
    
    def test_evaluate_triggers(self, setup_test_brain):
        from mcp_server_nucleus.runtime.trigger_ops import _evaluate_triggers_impl as _evaluate_triggers
        
        agents = _evaluate_triggers("task_completed", "any")
        assert "synthesizer" in agents
        
        agents = _evaluate_triggers("research_done", "any")
        assert "architect" in agents
        
        agents = _evaluate_triggers("unknown_event", "any")
        assert len(agents) == 0


class TestArtifactTools:
    """Tests for artifact read/write/list."""
    
    def test_write_artifact(self, setup_test_brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact
        
        result = _write_artifact("research/test.md", "# Test Content")
        # Check the operation succeeded (returns success message or path)
        assert "test.md" in result or "success" in result.lower() or "written" in result.lower()
    
    def test_read_artifact(self, setup_test_brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact, _read_artifact
        
        _write_artifact("research/read_test.md", "Hello World")
        content = _read_artifact("research/read_test.md")
        assert content == "Hello World"
    
    def test_list_artifacts(self, setup_test_brain):
        from mcp_server_nucleus.runtime.artifact_ops import _write_artifact, _list_artifacts
        
        _write_artifact("research/file1.md", "content")
        _write_artifact("research/file2.md", "content")
        
        artifacts = _list_artifacts("research")
        assert "research/file1.md" in artifacts or "file1.md" in str(artifacts)


class TestAgentTools:
    """Tests for agent triggering."""
    
    def test_trigger_agent(self, setup_test_brain):
        from mcp_server_nucleus.runtime.trigger_ops import _trigger_agent_impl as _trigger_agent
        from mcp_server_nucleus.runtime.event_ops import _read_events
        
        result = _trigger_agent(
            agent="researcher",
            task_description="Test task",
            context_files=None
        )
        
        assert "researcher" in result.lower()
        
        # Verify event was emitted
        events = _read_events(limit=1)
        assert len(events) == 1
        assert events[0]["type"] == "task_assigned"


# ============================================================
# V2 TASK MANAGEMENT TESTS
# ============================================================

@pytest.fixture
def setup_tasks(setup_test_brain):
    """Set up test brain with sample tasks - module level fixture."""
    state_file = setup_test_brain / "ledger" / "state.json"
    state = {
        "current_sprint": {
            "name": "Test Sprint",
            "focus": "Testing V2",
            "tasks": [
                {
                    "id": "task-001",
                    "description": "High priority Python task",
                    "status": "PENDING",
                    "priority": 1,
                    "blocked_by": [],
                    "required_skills": ["python"],
                    "claimed_by": None,
                    "source": "user",
                    "escalation_reason": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00"
                },
                {
                    "id": "task-002",
                    "description": "Low priority marketing task",
                    "status": "PENDING",
                    "priority": 5,
                    "blocked_by": [],
                    "required_skills": ["marketing"],
                    "claimed_by": None,
                    "source": "synthesizer",
                    "escalation_reason": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00"
                },
                {
                    "id": "task-003",
                    "description": "Blocked task",
                    "status": "BLOCKED",
                    "priority": 2,
                    "blocked_by": ["task-001"],
                    "required_skills": ["python"],
                    "claimed_by": None,
                    "source": "synthesizer",
                    "escalation_reason": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00"
                },
                {
                    "id": "task-004",
                    "description": "Already claimed task",
                    "status": "IN_PROGRESS",
                    "priority": 1,
                    "blocked_by": [],
                    "required_skills": ["python"],
                    "claimed_by": "agent-999",
                    "source": "user",
                    "escalation_reason": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00"
                },
                {
                    "description": "Legacy TODO task",
                    "status": "TODO",
                    "preferred_role": "Researcher"
                }
            ]
        }
    }
    state_file.write_text(json.dumps(state, indent=2))
    return setup_test_brain


class TestListTasks:
    """Tests for brain_list_tasks."""
    
    def test_list_all_tasks(self, setup_tasks):
        from mcp_server_nucleus import _list_tasks
        
        tasks = _list_tasks()
        assert len(tasks) == 5
    
    def test_filter_by_status(self, setup_tasks):
        from mcp_server_nucleus import _list_tasks
        
        pending = _list_tasks(status="PENDING")
        assert len(pending) == 2
        
        blocked = _list_tasks(status="BLOCKED")
        assert len(blocked) == 1
    
    def test_filter_by_priority(self, setup_tasks):
        from mcp_server_nucleus import _list_tasks
        
        high_priority = _list_tasks(priority=1)
        assert len(high_priority) == 2  # task-001 and task-004
    
    def test_filter_by_skill(self, setup_tasks):
        from mcp_server_nucleus import _list_tasks
        
        python_tasks = _list_tasks(skill="python")
        assert len(python_tasks) >= 2
        
        marketing_tasks = _list_tasks(skill="marketing")
        assert len(marketing_tasks) == 1
    
    def test_backward_compat_legacy_tasks(self, setup_tasks):
        from mcp_server_nucleus import _list_tasks
        
        # Legacy TODO tasks should be returned and have V2 fields added
        tasks = _list_tasks(status="TODO")
        assert len(tasks) >= 1
        
        # Should have auto-generated fields
        legacy = [t for t in tasks if "Legacy" in t.get("description", "")]
        if legacy:
            assert "id" in legacy[0]
            assert "priority" in legacy[0]


class TestGetNextTask:
    """Tests for brain_get_next_task."""
    
    def test_get_next_matching_skill(self, setup_tasks):
        from mcp_server_nucleus import _get_next_task
        
        # Should return highest priority unclaimed Python task
        task = _get_next_task(["python"])
        assert task is not None
        assert task["id"] == "task-001"  # Priority 1, unclaimed
    
    def test_get_next_different_skill(self, setup_tasks):
        from mcp_server_nucleus import _get_next_task
        
        task = _get_next_task(["marketing"])
        assert task is not None
        assert task["id"] == "task-002"
    
    def test_get_next_no_match(self, setup_tasks):
        from mcp_server_nucleus import _get_next_task
        
        task = _get_next_task(["nonexistent_skill"])
        # Should return None or a task without required skills
        # (tasks without required skills match any agent)
    
    def test_skips_claimed_tasks(self, setup_tasks):
        from mcp_server_nucleus import _get_next_task
        
        # task-004 is priority 1 but claimed, should not be returned
        task = _get_next_task(["python"])
        assert task is None or task["claimed_by"] is None
    
    def test_skips_blocked_tasks(self, setup_tasks):
        from mcp_server_nucleus import _get_next_task
        
        # task-003 is priority 2 but blocked, should not be returned
        task = _get_next_task(["python"])
        if task:
            assert task["id"] != "task-003"


class TestClaimTask:
    """Tests for brain_claim_task."""
    
    def test_claim_success(self, setup_tasks):
        from mcp_server_nucleus import _claim_task, _list_tasks
        
        result = _claim_task("task-001", "test-agent")
        
        assert result["success"] is True
        assert result["task"]["claimed_by"] == "test-agent"
        assert result["task"]["status"] == "IN_PROGRESS"
    
    def test_claim_already_claimed(self, setup_tasks):
        from mcp_server_nucleus import _claim_task
        
        # task-004 is already claimed
        result = _claim_task("task-004", "another-agent")
        
        assert result["success"] is False
        assert "already claimed" in result["error"].lower()
    
    def test_claim_by_description(self, setup_tasks):
        from mcp_server_nucleus import _claim_task
        
        # Should work with description too (backward compat)
        result = _claim_task("High priority Python task", "test-agent")
        assert result["success"] is True
    
    def test_claim_nonexistent(self, setup_tasks):
        from mcp_server_nucleus import _claim_task
        
        result = _claim_task("nonexistent-task-id", "test-agent")
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_claim_emits_event(self, setup_tasks):
        from mcp_server_nucleus import _claim_task, _read_events
        
        _claim_task("task-002", "test-agent")
        
        events = _read_events(limit=5)
        claim_events = [e for e in events if e["type"] == "task_claimed"]
        assert len(claim_events) >= 1


class TestUpdateTask:
    """Tests for brain_update_task."""
    
    def test_update_status(self, setup_tasks):
        from mcp_server_nucleus import _update_task, _list_tasks
        
        result = _update_task("task-001", {"status": "DONE"})
        
        assert result["success"] is True
        assert result["task"]["status"] == "DONE"
    
    def test_update_priority(self, setup_tasks):
        from mcp_server_nucleus import _update_task
        
        result = _update_task("task-002", {"priority": 1})
        
        assert result["success"] is True
        assert result["task"]["priority"] == 1
    
    def test_update_multiple_fields(self, setup_tasks):
        from mcp_server_nucleus import _update_task
        
        result = _update_task("task-001", {
            "status": "IN_PROGRESS",
            "priority": 2,
            "claimed_by": "new-agent"
        })
        
        assert result["success"] is True
        assert result["task"]["status"] == "IN_PROGRESS"
        assert result["task"]["priority"] == 2
        assert result["task"]["claimed_by"] == "new-agent"
    
    def test_update_nonexistent(self, setup_tasks):
        from mcp_server_nucleus import _update_task
        
        result = _update_task("fake-id", {"status": "DONE"})
        assert result["success"] is False


class TestAddTask:
    """Tests for brain_add_task."""
    
    def test_add_basic_task(self, setup_tasks):
        from mcp_server_nucleus import _add_task, _list_tasks
        
        result = _add_task("New test task")
        
        assert result["success"] is True
        assert result["task"]["description"] == "New test task"
        assert result["task"]["status"] == "PENDING"
        assert result["task"]["priority"] == 3  # Default
        assert result["task"]["id"].startswith("task-")
    
    def test_add_with_priority(self, setup_tasks):
        from mcp_server_nucleus import _add_task
        
        result = _add_task("Urgent task", priority=1)
        
        assert result["success"] is True
        assert result["task"]["priority"] == 1
    
    def test_add_with_skills(self, setup_tasks):
        from mcp_server_nucleus import _add_task
        
        result = _add_task(
            "Python task",
            required_skills=["python", "testing"]
        )
        
        assert result["success"] is True
        assert "python" in result["task"]["required_skills"]
    
    def test_add_with_dependencies(self, setup_tasks):
        from mcp_server_nucleus import _add_task
        
        result = _add_task(
            "Dependent task",
            blocked_by=["task-001"]
        )
        
        assert result["success"] is True
        assert result["task"]["status"] == "BLOCKED"
        assert "task-001" in result["task"]["blocked_by"]
    
    def test_add_user_source(self, setup_tasks):
        from mcp_server_nucleus import _add_task
        
        result = _add_task("User task", source="user")
        
        assert result["success"] is True
        assert result["task"]["source"] == "user"
    
    def test_add_emits_event(self, setup_tasks):
        from mcp_server_nucleus import _add_task, _read_events
        
        _add_task("Event test task")
        
        events = _read_events(limit=5)
        create_events = [e for e in events if e["type"] == "task_created"]
        assert len(create_events) >= 1
    
    def test_add_referential_integrity_violation(self, setup_tasks):
        """Test that adding a task with non-existent dependency fails."""
        from mcp_server_nucleus import _add_task
        
        result = _add_task(
            "Task with bad dependency",
            blocked_by=["nonexistent-task-id"]
        )
        
        assert result["success"] is False
        assert "referential integrity" in result["error"].lower()
    
    def test_add_valid_dependencies(self, setup_tasks):
        """Test that adding a task with valid dependency succeeds."""
        from mcp_server_nucleus import _add_task
        
        # task-001 exists in setup_tasks
        result = _add_task(
            "Task with valid dependency",
            blocked_by=["task-001"]
        )
        
        assert result["success"] is True
        assert result["task"]["status"] == "BLOCKED"


class TestEscalateTask:
    """Tests for brain_escalate."""
    
    def test_escalate_success(self, setup_tasks):
        from mcp_server_nucleus import _escalate_task
        
        result = _escalate_task("task-001", "I need human help with this")
        
        assert result["success"] is True
        assert result["task"]["status"] == "ESCALATED"
        assert result["task"]["escalation_reason"] == "I need human help with this"
        assert result["task"]["claimed_by"] is None  # Unclaimed
    
    def test_escalate_emits_event(self, setup_tasks):
        from mcp_server_nucleus import _escalate_task, _read_events
        
        _escalate_task("task-002", "Stuck on this")
        
        events = _read_events(limit=5)
        escalate_events = [e for e in events if e["type"] == "task_escalated"]
        assert len(escalate_events) >= 1
    
    def test_escalate_nonexistent(self, setup_tasks):
        from mcp_server_nucleus import _escalate_task
        
        result = _escalate_task("fake-task", "help")
        assert result["success"] is False


class TestTaskWorkflow:
    """Integration tests for complete task workflows."""
    
    def test_full_lifecycle(self, setup_tasks):
        """Test: Add -> Get Next -> Claim -> Update -> Complete"""
        from mcp_server_nucleus import (
            _add_task, _get_next_task, _claim_task, 
            _update_task, _list_tasks
        )
        
        # 1. Add a new high-priority task
        add_result = _add_task(
            "Lifecycle test task",
            priority=1,
            required_skills=["testing"]
        )
        task_id = add_result["task"]["id"]
        
        # 2. Get next task (should be our new one due to priority)
        next_task = _get_next_task(["testing"])
        assert next_task["id"] == task_id
        
        # 3. Claim it
        claim_result = _claim_task(task_id, "lifecycle-agent")
        assert claim_result["success"] is True
        
        # 4. Verify it's no longer available
        next_task = _get_next_task(["testing"])
        assert next_task is None or next_task["id"] != task_id
        
        # 5. Mark as done
        update_result = _update_task(task_id, {"status": "DONE"})
        assert update_result["success"] is True
        
        # 6. Verify final state
        all_tasks = _list_tasks()
        our_task = [t for t in all_tasks if t["id"] == task_id][0]
        assert our_task["status"] == "DONE"
    
    def test_escalation_workflow(self, setup_tasks):
        """Test: Claim -> Work -> Get Stuck -> Escalate"""
        from mcp_server_nucleus import (
            _claim_task, _escalate_task, _get_next_task
        )
        
        # 1. Claim a task
        claim_result = _claim_task("task-001", "stuck-agent")
        assert claim_result["success"] is True
        
        # 2. Escalate it
        escalate_result = _escalate_task("task-001", "API docs unclear")
        assert escalate_result["success"] is True
        assert escalate_result["task"]["status"] == "ESCALATED"
        
        # 3. Task should not appear in get_next (it's escalated)
        next_task = _get_next_task(["python"])
        assert next_task is None or next_task["id"] != "task-001"
    
    def test_dependency_unblocking(self, setup_tasks):
        """Test: Complete blocker -> Blocked task becomes available"""
        from mcp_server_nucleus import (
            _update_task, _get_next_task, _list_tasks
        )
        
        # task-003 is blocked by task-001
        # Initially task-003 should not be returned
        
        # 1. Complete the blocker
        _update_task("task-001", {"status": "DONE"})
        
        # 2. Now task-003 should be available (if we update status)
        _update_task("task-003", {"status": "PENDING"})
        
        # 3. Get next Python task
        next_task = _get_next_task(["python"])
        # Should be task-003 (priority 2, now unblocked)
        # (task-001 is DONE, task-004 is claimed)
        assert next_task is not None
