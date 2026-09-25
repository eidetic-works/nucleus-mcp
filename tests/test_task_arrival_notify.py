"""Tests for auto-notify: task arrival posts relay to role bucket.

When a task with required_role is added, the system auto-posts a relay
to .brain/relay/role_<required_role>/ so any agent armed on
relay_subscribe for that role sees the task arrival instantly.

The relay tells the agent to call nucleus_wakeup_wait to pull the task.
This closes the cold-start gap — agents don't need idle-state
instructions, they just respond to relay notifications like they
already do.
"""
import os
import tempfile
import json
from pathlib import Path
import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task
from mcp_server_nucleus.runtime.common import get_brain_path


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    yield tmpdir


def test_task_arrival_posts_relay_to_role_bucket(temp_brain):
    """Adding a task with required_role posts a relay to role_<required_role>."""
    _add_task(
        "test task for principal",
        priority=3,
        source="test",
        task_id="test_arrival_1",
        required_role="principal",
    )

    # Check the role bucket got a relay
    role_bucket = Path(temp_brain) / "relay" / "role_principal"
    assert role_bucket.exists(), f"role_principal bucket not created at {role_bucket}"

    relays = list(role_bucket.glob("*.json"))
    assert len(relays) == 1, f"expected 1 relay, got {len(relays)}"

    msg = json.loads(relays[0].read_text())
    assert "[TASK]" in msg["subject"]
    assert "test_arrival_1" in msg["subject"]
    assert "test task for principal" in msg["body"]
    assert "principal" in msg["body"]


def test_task_arrival_no_relay_without_role(temp_brain):
    """Adding a task without required_role does NOT post a relay."""
    _add_task(
        "unscoped task",
        priority=3,
        source="test",
        task_id="test_no_role_1",
    )

    # No role bucket should exist
    role_bucket = Path(temp_brain) / "relay" / "role_"
    assert not role_bucket.exists()


def test_task_arrival_relay_priority_matches_task(temp_brain):
    """High-priority tasks (priority <= 2) post high-priority relays."""
    _add_task(
        "urgent task",
        priority=1,
        source="test",
        task_id="test_urgent_1",
        required_role="principal",
    )

    role_bucket = Path(temp_brain) / "relay" / "role_principal"
    relays = list(role_bucket.glob("*.json"))
    msg = json.loads(relays[0].read_text())
    assert msg["priority"] == "high"


def test_task_arrival_relay_includes_task_details(temp_brain):
    """The relay body includes task description and plan_ref."""
    _add_task(
        "write tests for new feature",
        priority=3,
        source="secretary",
        task_id="test_details_1",
        required_role="principal",
        plan_ref="AGENT_OS_STATE.md#NEXT",
    )

    role_bucket = Path(temp_brain) / "relay" / "role_principal"
    relays = list(role_bucket.glob("*.json"))
    msg = json.loads(relays[0].read_text())
    assert "write tests for new feature" in msg["body"]
    assert "AGENT_OS_STATE.md#NEXT" in msg["body"]
    assert "test_details_1" in msg["body"]


def test_task_arrival_different_roles_separate_buckets(temp_brain):
    """Tasks for different roles post to different role buckets."""
    _add_task("principal task", priority=3, source="test",
              task_id="p1", required_role="principal")
    _add_task("peer task", priority=3, source="test",
              task_id="p2", required_role="peer")

    p_bucket = Path(temp_brain) / "relay" / "role_principal"
    peer_bucket = Path(temp_brain) / "relay" / "role_peer"

    assert len(list(p_bucket.glob("*.json"))) == 1
    assert len(list(peer_bucket.glob("*.json"))) == 1


def test_task_arrival_routes_to_agent_bucket_when_posture_active(temp_brain):
    """When posture is active, task relay goes to the agent's own bucket."""
    from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture

    # Declare + approve posture: agy is principal
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    # Add a task for principal
    _add_task("test task for principal via posture",
              priority=3, source="test",
              task_id="test_posture_route_1",
              required_role="principal")

    # Should go to antigravity/ (agy's canonical bucket), NOT role_principal/
    agy_bucket = Path(temp_brain) / "relay" / "antigravity"
    role_bucket = Path(temp_brain) / "relay" / "role_principal"

    assert agy_bucket.exists(), "relay should be in agy's bucket"
    relays = list(agy_bucket.glob("*.json"))
    assert len(relays) == 1

    msg = json.loads(relays[0].read_text())
    assert "[TASK]" in msg["subject"]
    assert "test_posture_route_1" in msg["body"]
    assert "test task for principal via posture" in msg["body"]

    # role_principal should NOT exist (posture routed to agent bucket)
    assert not role_bucket.exists()


def test_task_arrival_falls_back_to_role_bucket_without_posture(temp_brain):
    """Without active posture, task relay goes to role_<required_role>/."""
    _add_task("task without posture",
              priority=3, source="test",
              task_id="test_no_posture_1",
              required_role="principal")

    role_bucket = Path(temp_brain) / "relay" / "role_principal"
    assert role_bucket.exists()
    assert len(list(role_bucket.glob("*.json"))) == 1


def test_task_arrival_relay_includes_full_description(temp_brain):
    """The relay body includes the full task description, not truncated."""
    long_desc = "A" * 500
    _add_task(long_desc, priority=3, source="test",
              task_id="test_long_desc_1",
              required_role="principal")

    role_bucket = Path(temp_brain) / "relay" / "role_principal"
    relays = list(role_bucket.glob("*.json"))
    msg = json.loads(relays[0].read_text())
    # Full description should be in the body
    assert long_desc in msg["body"]
