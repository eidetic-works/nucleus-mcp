"""
Tests for Task Operations — CRUD, Claiming, Dependencies, Import
================================================================
Uses SQLite backend (default) via tmp_path brain directories.
"""

import json
import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def brain_path(tmp_path):
    """Get the brain directory (created by conftest autouse fixture) and add subdirs."""
    brain = Path(os.environ["NUCLEAR_BRAIN_PATH"])
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    yield brain


# ── Add Task Tests ────────────────────────────────────────────

class TestAddTask:
    def test_basic_add(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        result = _add_task("Build login page", priority=2)
        assert result["success"] is True
        assert result["task"]["description"] == "Build login page"
        assert result["task"]["priority"] == 2
        assert result["task"]["status"] == "PENDING"

    def test_add_with_custom_id(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        result = _add_task("Task A", task_id="custom-001")
        assert result["success"] is True
        assert result["task"]["id"] == "custom-001"

    def test_add_duplicate_id_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        _add_task("Task A", task_id="dup-001")
        result = _add_task("Task B", task_id="dup-001")
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_add_with_dependencies(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        _add_task("Dep task", task_id="dep-1")
        result = _add_task("Blocked task", blocked_by=["dep-1"])
        assert result["success"] is True
        assert result["task"]["status"] == "BLOCKED"

    def test_add_with_nonexistent_dependency_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        result = _add_task("Task A", blocked_by=["nonexistent"])
        assert result["success"] is False
        assert "Referential integrity" in result["error"]

    def test_add_self_blocking_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        # Self-blocking is caught either as DAG violation or referential integrity
        # (since the task doesn't exist yet when deps are checked)
        result = _add_task("Self ref", task_id="self-1", blocked_by=["self-1"])
        assert result["success"] is False

    def test_add_with_skills(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        result = _add_task("ML task", required_skills=["python", "ml"])
        assert result["success"] is True
        assert "python" in result["task"]["required_skills"]

    def test_skip_dep_check(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task
        result = _add_task("Task A", blocked_by=["phantom"], skip_dep_check=True)
        assert result["success"] is True


# ── List Tasks Tests ──────────────────────────────────────────

class TestListTasks:
    def test_empty_list(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _list_tasks
        tasks = _list_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) == 0

    def test_list_returns_added_tasks(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks
        _add_task("Task A", priority=1)
        _add_task("Task B", priority=3)
        tasks = _list_tasks()
        assert len(tasks) == 2

    def test_list_sorted_by_priority(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks
        _add_task("Low pri", priority=5)
        _add_task("High pri", priority=1)
        _add_task("Mid pri", priority=3)
        tasks = _list_tasks()
        priorities = [t["priority"] for t in tasks]
        assert priorities == sorted(priorities)

    def test_filter_by_status(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks
        _add_task("Pending", task_id="t1")
        _add_task("Dep", task_id="dep1")
        _add_task("Blocked", task_id="t2", blocked_by=["dep1"])
        pending = _list_tasks(status="PENDING")
        # dep1 and t1 are PENDING
        assert all(t["status"] == "PENDING" for t in pending)

    def test_filter_by_priority(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks
        _add_task("P1 task", priority=1)
        _add_task("P3 task", priority=3)
        tasks = _list_tasks(priority=1)
        assert len(tasks) == 1
        assert tasks[0]["priority"] == 1


# ── Update Task Tests ─────────────────────────────────────────

class TestUpdateTask:
    def test_update_status(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
        _add_task("Task A", task_id="t1")
        result = _update_task("t1", {"status": "IN_PROGRESS"})
        assert result["success"] is True
        assert result["task"]["status"] == "IN_PROGRESS"

    def test_update_nonexistent_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _update_task
        result = _update_task("fake", {"status": "DONE"})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_update_filters_invalid_keys(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
        _add_task("Task A", task_id="t1")
        result = _update_task("t1", {"status": "DONE", "invalid_field": "hack"})
        assert result["success"] is True
        assert "invalid_field" not in result["task"]

    def test_update_priority(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
        _add_task("Task A", task_id="t1", priority=3)
        result = _update_task("t1", {"priority": 1})
        assert result["success"] is True
        assert result["task"]["priority"] == 1

    def test_update_blocked_by_validates_deps(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
        _add_task("Task A", task_id="t1")
        result = _update_task("t1", {"blocked_by": ["nonexistent"]})
        assert result["success"] is False
        assert "Referential integrity" in result["error"]


# ── Claim Task Tests ──────────────────────────────────────────

class TestClaimTask:
    def test_claim_pending_task(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _claim_task
        _add_task("Task A", task_id="t1")
        result = _claim_task("t1", "agent-alpha")
        assert result["success"] is True
        assert result["task"]["claimed_by"] == "agent-alpha"
        assert result["task"]["status"] == "IN_PROGRESS"

    def test_claim_already_claimed_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _claim_task
        _add_task("Task A", task_id="t1")
        _claim_task("t1", "agent-alpha")
        result = _claim_task("t1", "agent-beta")
        assert result["success"] is False
        assert "already claimed" in result["error"]

    def test_claim_done_task_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task, _claim_task
        _add_task("Task A", task_id="t1")
        _update_task("t1", {"status": "DONE"})
        result = _claim_task("t1", "agent-alpha")
        assert result["success"] is False
        assert "cannot claim" in result["error"].lower() or "DONE" in result["error"]

    def test_claim_nonexistent_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _claim_task
        result = _claim_task("fake-id", "agent-alpha")
        assert result["success"] is False


# ── Get Next Task Tests ───────────────────────────────────────

class TestGetNextTask:
    def test_next_task_returns_highest_priority(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _get_next_task
        _add_task("Low", priority=5, task_id="low")
        _add_task("High", priority=1, task_id="high")
        task = _get_next_task(skills=[])
        assert task is not None
        assert task["id"] == "high"

    def test_next_task_skips_claimed(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _claim_task, _get_next_task
        _add_task("Claimed", priority=1, task_id="claimed")
        _add_task("Free", priority=2, task_id="free")
        _claim_task("claimed", "agent-x")
        task = _get_next_task(skills=[])
        assert task is not None
        assert task["id"] == "free"

    def test_next_task_skips_blocked(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _get_next_task
        _add_task("Dep", task_id="dep1", priority=5)
        _add_task("Blocked", task_id="blocked1", priority=1, blocked_by=["dep1"])
        _add_task("Free", task_id="free1", priority=3)
        task = _get_next_task(skills=[])
        # blocked1 is blocked by dep1 which is PENDING not DONE, so it should be skipped
        assert task is not None
        assert task["id"] in ["dep1", "free1"]

    def test_next_task_matches_skills(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _get_next_task
        _add_task("Python task", priority=1, required_skills=["python"], task_id="py1")
        _add_task("Rust task", priority=1, required_skills=["rust"], task_id="rs1")
        task = _get_next_task(skills=["python"])
        assert task is not None
        assert task["id"] == "py1"

    def test_next_task_none_when_empty(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _get_next_task
        task = _get_next_task(skills=[])
        assert task is None


# ── Escalate Task Tests ───────────────────────────────────────

class TestEscalateTask:
    def test_escalate_task(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _claim_task, _escalate_task
        _add_task("Hard task", task_id="t1")
        _claim_task("t1", "agent-a")
        result = _escalate_task("t1", "Need human review")
        assert result["success"] is True
        assert result["task"]["status"] == "ESCALATED"
        assert result["task"]["escalation_reason"] == "Need human review"
        assert result["task"]["claimed_by"] is None

    def test_escalate_nonexistent_fails(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _escalate_task
        result = _escalate_task("fake", "reason")
        assert result["success"] is False


# ── Import Tasks Tests ────────────────────────────────────────

class TestImportTasks:
    def test_import_from_jsonl(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl, _list_tasks
        jsonl_file = brain_path / "import.jsonl"
        with open(jsonl_file, "w") as f:
            f.write(json.dumps({"id": "imp-1", "description": "Imported task 1", "priority": 2}) + "\n")
            f.write(json.dumps({"id": "imp-2", "description": "Imported task 2", "priority": 3}) + "\n")
        result = _import_tasks_from_jsonl(str(jsonl_file))
        assert result["success"] is True
        assert result["imported"] == 2
        tasks = _list_tasks()
        assert len(tasks) == 2

    def test_import_skips_duplicates(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _add_task, _import_tasks_from_jsonl
        _add_task("Existing", task_id="dup-1")
        jsonl_file = brain_path / "import.jsonl"
        with open(jsonl_file, "w") as f:
            f.write(json.dumps({"id": "dup-1", "description": "Dup"}) + "\n")
            f.write(json.dumps({"id": "new-1", "description": "New"}) + "\n")
        result = _import_tasks_from_jsonl(str(jsonl_file))
        assert result["imported"] == 1
        assert result["skipped"] == 1

    def test_import_nonexistent_file(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl
        result = _import_tasks_from_jsonl("/nonexistent/file.jsonl")
        assert result["success"] is False
        assert "not found" in result["error"].lower() or "File not found" in result["error"]

    def test_import_skips_invalid_json(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl
        jsonl_file = brain_path / "bad.jsonl"
        with open(jsonl_file, "w") as f:
            f.write("NOT JSON\n")
            f.write(json.dumps({"id": "ok-1", "description": "Good task"}) + "\n")
        result = _import_tasks_from_jsonl(str(jsonl_file))
        assert result["imported"] == 1
        assert result["skipped"] == 1

    def test_import_skips_missing_description(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl
        jsonl_file = brain_path / "nodesc.jsonl"
        with open(jsonl_file, "w") as f:
            f.write(json.dumps({"id": "no-desc"}) + "\n")
        result = _import_tasks_from_jsonl(str(jsonl_file))
        assert result["skipped"] == 1

    def test_import_with_gtm_metadata(self, brain_path):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl, _list_tasks
        jsonl_file = brain_path / "gtm.jsonl"
        with open(jsonl_file, "w") as f:
            f.write(json.dumps({
                "id": "gtm-1",
                "description": "GTM task",
                "environment": "staging",
                "model": "claude-3",
                "step": "validation"
            }) + "\n")
        result = _import_tasks_from_jsonl(str(jsonl_file), merge_gtm_params=True)
        assert result["imported"] == 1
