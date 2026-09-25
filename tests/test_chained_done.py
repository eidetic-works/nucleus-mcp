"""Tests for chained DONE — update_task(DONE) returns next message.

When an agent marks a task DONE, the response includes the next unread
relay message. This eliminates the idle gap — the agent never stops
to decide what to do next. Each task naturally chains to the next.
"""
import os
import tempfile
import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox
from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
    yield tmpdir


def test_update_done_returns_next_message(temp_brain):
    """Marking a task DONE returns the next relay message in the response."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    # Add and claim a task
    _add_task("task 1", priority=3, source="test", task_id="chain_1", required_role="principal")

    # Post a relay that should be returned as next_message
    relay_post(
        to="antigravity",
        subject="[TASK] chain_2",
        body="Next task to execute.",
        sender="task_scheduler",
    )

    # Mark task 1 as DONE — should return next_message
    result = _update_task("chain_1", {"status": "DONE"})
    assert result["success"]


def test_update_done_with_next_message(temp_brain):
    """Full flow: add task, post relay, mark DONE, verify next_message."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    _add_task("task 1", priority=3, source="test", task_id="chain_1", required_role="principal")

    # Drain the auto-notify relay from _add_task
    from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
    from mcp_server_nucleus.runtime.relay.core import relay_ack
    me = resolve_canonical_inbox_name("agy")
    inbox = relay_inbox(unread_only=True, recipient=me, limit=10)
    for msg in inbox.get("messages", []):
        relay_ack(msg.get("id", ""), recipient=me)

    relay_post(
        to="antigravity",
        subject="[TASK] chain_2",
        body="Next task to execute.",
        sender="task_scheduler",
    )

    # Simulate what _h_update does
    result = _update_task("chain_1", {"status": "DONE"})
    assert result["success"]

    # Now check the relay inbox (what _h_update does internally)
    inbox = relay_inbox(unread_only=True, recipient=me, limit=1)
    messages = inbox.get("messages", [])
    assert len(messages) == 1
    assert messages[0]["body"] == "Next task to execute."
    assert messages[0]["subject"] == "[TASK] chain_2"


def test_update_done_no_next_message(temp_brain):
    """Marking DONE with no pending relays returns next_message=None."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    _add_task("task 1", priority=3, source="test", task_id="chain_1", required_role="principal")

    # Drain the auto-notify relay from _add_task
    from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
    from mcp_server_nucleus.runtime.relay.core import relay_ack
    me = resolve_canonical_inbox_name("agy")
    inbox = relay_inbox(unread_only=True, recipient=me, limit=10)
    for msg in inbox.get("messages", []):
        relay_ack(msg.get("id", ""), recipient=me)

    result = _update_task("chain_1", {"status": "DONE"})
    assert result["success"]

    inbox = relay_inbox(unread_only=True, recipient=me, limit=1)
    assert len(inbox.get("messages", [])) == 0


def test_update_not_done_no_next_message(temp_brain):
    """Updating a task without DONE doesn't check for next_message."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    _add_task("task 1", priority=3, source="test", task_id="chain_1", required_role="principal")
    relay_post(to="antigravity", subject="[TASK] chain_2", body="Next.", sender="test")

    # Update with non-DONE status
    result = _update_task("chain_1", {"status": "IN_PROGRESS"})
    assert result["success"]
    # next_message should NOT be in the raw _update_task result
    assert "next_message" not in result
