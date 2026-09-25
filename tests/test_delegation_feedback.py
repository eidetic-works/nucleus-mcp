"""Tests for delegation feedback — DONE posts [DONE] relay to source agent.

When a task with source=claude_code_main is marked DONE, the system
posts a [DONE] relay to claude_code_main's bucket. This closes the
delegation loop — the secretary knows when work is complete.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task, _update_task
from mcp_server_nucleus.runtime.relay.core import relay_inbox


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
    yield tmpdir


def test_done_posts_relay_to_source_agent(temp_brain):
    """Marking a task DONE posts [DONE] relay to the source agent's bucket."""
    _add_task(
        "test task for delegation",
        priority=3,
        source="claude_code_main",
        task_id="del_1",
        required_role="principal",
    )

    # Mark DONE
    result = _update_task("del_1", {"status": "DONE"})
    assert result["success"]

    # Check claude_code_main bucket for [DONE] relay
    cc_bucket = Path(temp_brain) / "relay" / "claude_code_main"
    assert cc_bucket.exists(), "claude_code_main bucket should exist"

    relays = list(cc_bucket.glob("*.json"))
    done_relays = []
    for r in relays:
        msg = json.loads(r.read_text())
        if "[DONE]" in msg.get("subject", ""):
            done_relays.append(msg)

    assert len(done_relays) >= 1, "should have at least one [DONE] relay"
    assert "del_1" in done_relays[0]["subject"]
    assert "test task for delegation" in done_relays[0]["body"]


def test_done_does_not_post_for_system_source(temp_brain):
    """Tasks with source='secretary' (system) don't post [DONE] relay."""
    _add_task(
        "system task",
        priority=3,
        source="secretary",
        task_id="sys_1",
        required_role="principal",
    )

    result = _update_task("sys_1", {"status": "DONE"})
    assert result["success"]

    # No [DONE] relay should be posted (secretary is a system source)
    cc_bucket = Path(temp_brain) / "relay" / "claude_code_main"
    if cc_bucket.exists():
        for r in cc_bucket.glob("*.json"):
            msg = json.loads(r.read_text())
            assert "[DONE]" not in msg.get("subject", ""), "system source should not get [DONE] relay"


def test_done_does_not_post_for_empty_source(temp_brain):
    """Tasks with empty source don't post [DONE] relay."""
    _add_task(
        "no source task",
        priority=3,
        source="",
        task_id="nosrc_1",
    )

    result = _update_task("nosrc_1", {"status": "DONE"})
    assert result["success"]


def test_non_done_update_does_not_post_relay(temp_brain):
    """Updating status to IN_PROGRESS doesn't post [DONE] relay."""
    _add_task(
        "test task",
        priority=3,
        source="claude_code_main",
        task_id="nodel_1",
    )

    result = _update_task("nodel_1", {"status": "IN_PROGRESS"})
    assert result["success"]

    # No [DONE] relay
    cc_bucket = Path(temp_brain) / "relay" / "claude_code_main"
    if cc_bucket.exists():
        for r in cc_bucket.glob("*.json"):
            msg = json.loads(r.read_text())
            assert "[DONE]" not in msg.get("subject", "")


def test_done_relay_includes_task_id_and_description(temp_brain):
    """The [DONE] relay includes the task ID and description for the delegator."""
    _add_task(
        "write tests for feature X",
        priority=3,
        source="claude_code_main",
        task_id="del_detail_1",
        required_role="principal",
    )

    _update_task("del_detail_1", {"status": "DONE"})

    cc_bucket = Path(temp_brain) / "relay" / "claude_code_main"
    for r in cc_bucket.glob("*.json"):
        msg = json.loads(r.read_text())
        if "[DONE]" in msg.get("subject", ""):
            assert "del_detail_1" in msg["subject"]
            assert "write tests for feature X" in msg["body"]
            assert "Queue the next task" in msg["body"]
            return
    pytest.fail("No [DONE] relay found")
