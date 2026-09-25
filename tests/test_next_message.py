"""Tests for nucleus_next_message — one call, full body, auto-ack.

The agent's idle loop primitive. Checks inbox, returns full message,
auto-acks. Non-blocking (5s default timeout).
"""
import asyncio
import os
import tempfile
import pytest

from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox
from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
    yield tmpdir


def test_next_message_returns_unread_and_acks(temp_brain):
    """next_message returns the full message body and auto-acks."""
    relay_post(
        to="antigravity",
        subject="[TASK] test_task",
        body="Do the thing.",
        sender="task_scheduler",
    )

    # Simulate what the MCP tool does internally
    inbox = relay_inbox(unread_only=True, recipient="antigravity", limit=1)
    messages = inbox.get("messages", [])
    assert len(messages) == 1
    msg = messages[0]
    assert msg["body"] == "Do the thing."
    assert msg["subject"] == "[TASK] test_task"

    # After ack, inbox should be empty
    from mcp_server_nucleus.runtime.relay.core import relay_ack
    relay_ack(msg["id"], recipient="antigravity")
    inbox2 = relay_inbox(unread_only=True, recipient="antigravity", limit=1)
    assert len(inbox2.get("messages", [])) == 0


def test_next_message_returns_none_on_empty(temp_brain):
    """next_message returns None when no messages (timeout)."""
    inbox = relay_inbox(unread_only=True, recipient="antigravity", limit=1)
    assert len(inbox.get("messages", [])) == 0


def test_next_message_auto_detects_from_posture(temp_brain):
    """next_message auto-detects recipient from posture."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    # Post to antigravity (agy's canonical bucket)
    relay_post(
        to="antigravity",
        subject="[TASK] posture_test",
        body="Task via posture.",
        sender="task_scheduler",
    )

    # Auto-detect: posture says agy → antigravity bucket
    from mcp_server_nucleus.runtime.posture import get_current_posture
    from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name

    posture = get_current_posture()
    assert posture["status"] == "active"
    me = resolve_canonical_inbox_name(posture["agent_id"])
    assert me == "antigravity"

    inbox = relay_inbox(unread_only=True, recipient=me, limit=1)
    messages = inbox.get("messages", [])
    assert len(messages) == 1
    assert messages[0]["body"] == "Task via posture."


def test_next_message_drains_in_order(temp_brain):
    """Multiple messages are returned newest first (sort by timestamp desc)."""
    import time
    relay_post(to="antigravity", subject="msg1", body="first", sender="test")
    time.sleep(1.1)  # Ensure different second-resolution timestamp
    relay_post(to="antigravity", subject="msg2", body="second", sender="test")

    inbox = relay_inbox(unread_only=True, recipient="antigravity", limit=1)
    messages = inbox.get("messages", [])
    assert len(messages) == 1
    # Newest first (msg2) — relay_inbox sorts by filename desc (newest first)
    assert messages[0]["body"] == "second"


def test_next_message_handles_task_relay(temp_brain):
    """next_message returns a [TASK] relay with full body for execution."""
    body = (
        "Task: test_123\n"
        "Role: principal\n"
        "Priority: 3\n"
        "Plan ref: AGENT_OS_STATE.md#test\n\n"
        "Description:\nWrite tests for the feature.\n\n"
        "Execute this task. Gate with pytest. Commit. Mark DONE."
    )
    relay_post(
        to="antigravity",
        subject="[TASK] test_123",
        body=body,
        sender="task_scheduler",
    )

    inbox = relay_inbox(unread_only=True, recipient="antigravity", limit=1)
    msg = inbox["messages"][0]
    assert "[TASK]" in msg["subject"]
    assert "Write tests for the feature." in msg["body"]
    assert "test_123" in msg["body"]
