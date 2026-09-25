"""Tests for required_role + plan_ref fields on nucleus_tasks.

Role-scoped tasks prevent agent pollution: the auto_awake daemon polls
nucleus_tasks filtered by required_role, so only the matching agent wakes.
Tasks with empty required_role are visible to all agents (backward compat).
"""
import os
import tempfile
import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks, _get_next_task


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    yield tmpdir


def test_add_task_with_required_role_and_plan_ref(temp_brain):
    """required_role and plan_ref are persisted on the task."""
    result = _add_task(
        "test role task",
        priority=1,
        source="secretary_test",
        task_id="test_role_1",
        required_role="principal",
        plan_ref="STATE.md#MOAT-§2",
    )
    assert result["success"]
    tasks = _list_tasks(status="PENDING")
    t = next(t for t in tasks if t["id"] == "test_role_1")
    assert t["required_role"] == "principal"
    assert t["plan_ref"] == "STATE.md#MOAT-§2"


def test_add_task_without_required_role_defaults_empty(temp_brain):
    """Tasks without required_role get empty string (backward compat)."""
    _add_task("no role task", priority=1, source="test", task_id="test_norole_1")
    tasks = _list_tasks(status="PENDING")
    t = next(t for t in tasks if t["id"] == "test_norole_1")
    assert t["required_role"] == ""
    assert t["plan_ref"] == ""


def test_list_tasks_filters_by_required_role(temp_brain):
    """Role filter returns only matching tasks + unscoped (backward compat)."""
    _add_task("principal task", priority=1, source="test", task_id="tp", required_role="principal")
    _add_task("peer task", priority=1, source="test", task_id="tp2", required_role="peer")
    _add_task("any task", priority=1, source="test", task_id="ta")

    principal_tasks = _list_tasks(required_role="principal")
    ids = sorted(t["id"] for t in principal_tasks)
    assert ids == ["ta", "tp"]  # principal + unscoped, NOT peer

    peer_tasks = _list_tasks(required_role="peer")
    ids = sorted(t["id"] for t in peer_tasks)
    assert ids == ["ta", "tp2"]  # peer + unscoped, NOT principal


def test_get_next_task_respects_required_role(temp_brain):
    """get_next with role filter returns only matching tasks."""
    _add_task("principal task", priority=1, source="test", task_id="tp", required_role="principal")
    _add_task("peer task", priority=1, source="test", task_id="tp2", required_role="peer")

    next_principal = _get_next_task([], required_role="principal")
    assert next_principal is not None
    assert next_principal["id"] == "tp"

    next_peer = _get_next_task([], required_role="peer")
    assert next_peer is not None
    assert next_peer["id"] == "tp2"


def test_get_next_task_no_role_filter_sees_all(temp_brain):
    """get_next without role filter sees all tasks (backward compat)."""
    _add_task("principal task", priority=1, source="test", task_id="tp", required_role="principal")
    _add_task("peer task", priority=2, source="test", task_id="tp2", required_role="peer")

    # No role filter — should see the highest priority task regardless of role
    next_task = _get_next_task([])
    assert next_task is not None
    assert next_task["id"] == "tp"  # priority 1


def test_list_tasks_strict_role_excludes_unscoped(temp_brain):
    """strict_role=True excludes unscoped tasks — only exact role match.

    This is what wakeup_wait uses so a scoped agent doesn't get spammed
    by legacy unscoped tasks in the queue.
    """
    _add_task("principal task", priority=1, source="test", task_id="tp", required_role="principal")
    _add_task("unscoped task", priority=1, source="test", task_id="tu")

    # Non-strict (backward compat): unscoped tasks match any filter
    from mcp_server_nucleus.runtime.task_ops import _list_tasks
    non_strict = _list_tasks(required_role="principal", strict_role=False)
    ids = sorted(t["id"] for t in non_strict)
    assert ids == ["tp", "tu"]  # principal + unscoped

    # Strict: only exact role match
    strict = _list_tasks(required_role="principal", strict_role=True)
    ids = sorted(t["id"] for t in strict)
    assert ids == ["tp"]  # principal only, NOT unscoped
