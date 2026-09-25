"""Tests for task-scoped comments — relay-with-task_id.

A task comment is a relay message with task_id set. It routes to
.brain/relay/task_comments/<task_id>/ instead of an agent inbox.
Anyone working on the task can see all comments. Threading via
in_reply_to still works. When the task is DONE, the comment thread
stays as a coordination record.
"""
import os
import tempfile
import pytest

from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
    yield tmpdir


def test_task_comment_routes_to_task_bucket(temp_brain):
    """A relay message with task_id goes to task_comments/<task_id>/, not agent inbox."""
    relay_post(
        to="claude_code_main",
        subject="stuck on mock",
        body="Need help with MockContext",
        sender="agy",
        task_id="task_123",
    )

    # Should NOT appear in agent inbox
    inbox = relay_inbox(unread_only=False, recipient="claude_code_main")
    assert inbox["count"] == 0

    # Should appear in task comments
    comments = relay_inbox(unread_only=False, task_id="task_123")
    assert comments["count"] == 1
    assert comments["messages"][0]["body"] == "Need help with MockContext"
    assert comments["messages"][0]["task_id"] == "task_123"
    assert comments["messages"][0]["from"] == "antigravity"  # canonicalized from "agy"


def test_task_comment_threading(temp_brain):
    """Comments on the same task thread via in_reply_to."""
    # First comment
    r1 = relay_post(
        to="task_comments",
        subject="blocker",
        body="Stuck on MockContext async pattern",
        sender="agy",
        task_id="task_456",
    )
    msg_id_1 = r1["message_id"]

    # Reply (threaded)
    relay_post(
        to="task_comments",
        subject="re: blocker",
        body="Use `async def info(self, msg): self.infos.append(msg)`",
        sender="devin",
        task_id="task_456",
        in_reply_to=msg_id_1,
    )

    comments = relay_inbox(unread_only=False, task_id="task_456")
    assert comments["count"] == 2

    # Find the reply
    reply = next(m for m in comments["messages"] if m.get("in_reply_to") == msg_id_1)
    assert reply["body"] == "Use `async def info(self, msg): self.infos.append(msg)`"
    assert reply["from"] == "devin"


def test_task_comments_visible_to_anyone(temp_brain):
    """Task comments are not scoped to one agent — anyone can read them."""
    relay_post(
        to="task_comments",
        subject="progress",
        body="Halfway done",
        sender="agy",
        task_id="task_789",
    )

    # Any "recipient" can read task comments — it's task-scoped, not agent-scoped
    comments = relay_inbox(unread_only=False, task_id="task_789", recipient="devin")
    assert comments["count"] == 1
    comments = relay_inbox(unread_only=False, task_id="task_789", recipient="cc_main")
    assert comments["count"] == 1


def test_task_comments_separate_per_task(temp_brain):
    """Comments for different tasks don't bleed into each other."""
    relay_post(to="task_comments", subject="c1", body="task A comment",
               sender="agy", task_id="task_A")
    relay_post(to="task_comments", subject="c2", body="task B comment",
               sender="agy", task_id="task_B")

    a = relay_inbox(unread_only=False, task_id="task_A")
    b = relay_inbox(unread_only=False, task_id="task_B")

    assert a["count"] == 1
    assert a["messages"][0]["body"] == "task A comment"
    assert b["count"] == 1
    assert b["messages"][0]["body"] == "task B comment"


def test_task_comment_empty_bucket(temp_brain):
    """Listing comments for a task with no comments returns empty, not error."""
    comments = relay_inbox(unread_only=False, task_id="nonexistent_task")
    assert comments["count"] == 0
    assert comments["messages"] == []


def test_no_task_id_routes_normally(temp_brain):
    """Relay messages without task_id still route to agent inboxes (backward compat)."""
    relay_post(
        to="claude_code_main",
        subject="normal relay",
        body="This is a normal relay message",
        sender="agy",
    )

    # Should appear in agent inbox
    inbox = relay_inbox(unread_only=False, recipient="claude_code_main")
    assert inbox["count"] == 1
    assert inbox["messages"][0]["body"] == "This is a normal relay message"

    # Should NOT appear in task comments
    comments = relay_inbox(unread_only=False, task_id="some_task")
    assert comments["count"] == 0
