"""Tests for nucleus_wakeup_wait — MCP-native pull-and-return primitive.

wakeup_wait returns the task directly. One call = one task. The agent's
loop is: call → execute → gate → commit → mark DONE → call again.
No separate get_next + claim dance. Auto-claims the task before returning
so two agents don't race on the same task.
"""
import os
import tempfile
import time
import threading
import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task, _get_next_task, _claim_task


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    yield tmpdir


def _poll_for_task(required_role, timeout=5):
    """Simulate what wakeup_wait does internally: poll + claim + return."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = _get_next_task([], required_role=required_role)
        if task and not task.get("claimed_by"):
            claim = _claim_task(task["id"], "test_agent")
            if claim.get("success"):
                task["claimed_by"] = "test_agent"
                return task
        time.sleep(0.2)
    return None


def test_wakeup_wait_returns_task_directly(temp_brain):
    """wakeup_wait returns the task dict, not just a notification."""
    _add_task("principal task", priority=1, source="test", task_id="p1",
              required_role="principal")

    task = _poll_for_task("principal", timeout=2)
    assert task is not None
    assert task["id"] == "p1"
    assert task["description"] == "principal task"
    assert task["claimed_by"] == "test_agent"


def test_wakeup_wait_auto_claims(temp_brain):
    """The returned task is already claimed — no separate claim needed."""
    _add_task("principal task", priority=1, source="test", task_id="p1",
              required_role="principal")

    task = _poll_for_task("principal", timeout=2)
    assert task is not None
    assert task["claimed_by"] == "test_agent"

    # Verify in the DB that it's actually claimed (status changes to IN_PROGRESS)
    from mcp_server_nucleus.runtime.task_ops import _list_tasks
    tasks = _list_tasks(status="IN_PROGRESS")
    t = next(t for t in tasks if t["id"] == "p1")
    assert t["claimed_by"] == "test_agent"


def test_wakeup_wait_returns_none_on_timeout(temp_brain):
    """When no matching task exists, returns None on timeout."""
    _add_task("peer task", priority=1, source="test", task_id="peer_1",
              required_role="peer")

    task = _poll_for_task("principal", timeout=2)
    assert task is None  # peer task is invisible to principal


def test_wakeup_wait_respects_required_role(temp_brain):
    """wakeup_wait with required_role only sees tasks for that role."""
    _add_task("principal task", priority=1, source="test", task_id="p1",
              required_role="principal")
    _add_task("peer task", priority=1, source="test", task_id="p2",
              required_role="peer")

    # Principal poll finds principal task
    task = _poll_for_task("principal", timeout=2)
    assert task and task["id"] == "p1"

    # Peer poll finds peer task
    task = _poll_for_task("peer", timeout=2)
    assert task and task["id"] == "p2"


def test_wakeup_wait_finds_task_added_during_poll(temp_brain):
    """The polling loop finds a task added after the poll starts."""
    def add_later():
        time.sleep(0.5)
        _add_task("delayed task", priority=1, source="test", task_id="delayed_1",
                  required_role="principal")

    t = threading.Thread(target=add_later, daemon=True)
    t.start()

    task = _poll_for_task("principal", timeout=5)
    assert task is not None
    assert task["id"] == "delayed_1"


def test_wakeup_wait_no_races(temp_brain):
    """Once a task is claimed by one agent, another agent doesn't get it."""
    _add_task("shared task", priority=1, source="test", task_id="s1",
              required_role="principal")

    # First agent claims it
    task1 = _poll_for_task("principal", timeout=2)
    assert task1 is not None
    assert task1["id"] == "s1"

    # Second agent polls — should get None (task already claimed)
    task2 = _poll_for_task("principal", timeout=1)
    assert task2 is None  # already claimed by first agent

import asyncio

class MockContext:
    def __init__(self):
        self.infos = []
    async def info(self, msg):
        self.infos.append(msg)

@pytest.mark.anyio
async def test_mcp_tool_wakeup_wait_fires_info(temp_brain):
    """Verifies the actual MCP tool fires ctx.info() when a task is found."""
    from mcp_server_nucleus.tools.sync import register
    
    # Extract the nucleus_wakeup_wait function
    class MockMCP:
        def tool(self, title=None, annotations=None):
            def decorator(func):
                return func
            return decorator
    
    mock_mcp = MockMCP()
    tools = register(mock_mcp, {
        "make_response": lambda *args, **kwargs: None,
        "emit_event": lambda *args, **kwargs: None,
        "get_state": lambda *args, **kwargs: {},
        "set_state": lambda *args, **kwargs: None,
        "get_brain_path": lambda *args, **kwargs: temp_brain
    })
    wakeup_tool = dict(tools)["nucleus_wakeup_wait"]
    
    ctx = MockContext()
    
    def add_later():
        time.sleep(0.5)
        _add_task("async task", priority=1, source="test", task_id="async_1",
                  required_role="principal")
                  
    t = threading.Thread(target=add_later, daemon=True)
    t.start()
    
    result = await wakeup_tool(ctx, required_role="principal", timeout_seconds=5)
    
    assert result["task"] is not None
    assert result["task"]["id"] == "async_1"
    
    # Check that ctx.info() was called to push the notification
    assert len(ctx.infos) > 0
    assert any("claimed task async_1" in info for info in ctx.infos)
