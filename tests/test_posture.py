"""Tests for posture — declared, confirmed, approved, persisted.

The posture is the agent's role + approach. It's declared by the agent,
approved by the operator, and persisted in .brain/posture/current.json.
Every wakeup_wait() call auto-reads it — no role strings needed.
"""
import os
import tempfile
import json
import pytest

from mcp_server_nucleus.runtime.posture import (
    declare_posture,
    approve_posture,
    get_current_posture,
    get_current_role,
    clear_posture,
)


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    yield tmpdir


def test_declare_posture_creates_pending(temp_brain):
    """Declaring a posture creates a pending_approval entry."""
    r = declare_posture(role="principal", approach="delegate", agent_id="agy")
    assert r["success"]
    assert r["posture"]["role"] == "principal"
    assert r["posture"]["approach"] == "delegate"
    assert r["posture"]["status"] == "pending_approval"
    assert r["posture"]["agent_id"] == "agy"


def test_declare_posture_persists(temp_brain):
    """The posture is written to .brain/posture/current.json."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")

    posture = get_current_posture()
    assert posture["role"] == "principal"
    assert posture["approach"] == "delegate"
    assert posture["status"] == "pending_approval"


def test_approve_posture_activates(temp_brain):
    """Approving a pending posture sets it to active."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    r = approve_posture(approved_by="operator")
    assert r["success"]
    assert r["posture"]["status"] == "active"
    assert r["posture"]["approved_by"] == "operator"
    assert r["posture"]["approved_at"] is not None


def test_get_current_role_only_when_active(temp_brain):
    """get_current_role returns role only when posture is active."""
    # No posture
    assert get_current_role() == ""

    # Pending posture — role not returned
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    assert get_current_role() == ""  # pending, not active

    # Approved posture — role returned
    approve_posture()
    assert get_current_role() == "principal"


def test_declare_posture_invalid_role(temp_brain):
    """Invalid roles are rejected."""
    r = declare_posture(role="boss", approach="delegate")
    assert not r["success"]
    assert "Invalid role" in r["error"]


def test_declare_posture_invalid_approach(temp_brain):
    """Invalid approaches are rejected."""
    r = declare_posture(role="principal", approach="wing-it")
    assert not r["success"]
    assert "Invalid approach" in r["error"]


def test_approve_without_declare(temp_brain):
    """Approving without a declared posture fails gracefully."""
    r = approve_posture()
    assert not r["success"]
    assert "No posture declared" in r["error"]


def test_clear_posture(temp_brain):
    """Clearing the posture removes it."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()
    assert get_current_role() == "principal"

    clear_posture()
    assert get_current_role() == ""
    assert get_current_posture() == {}


def test_posture_survives_restart(temp_brain):
    """The posture persists across reads (simulates restart)."""
    declare_posture(role="peer", approach="hands-on", agent_id="cc_main")
    approve_posture()

    # Simulate restart by re-reading
    posture = get_current_posture()
    assert posture["role"] == "peer"
    assert posture["status"] == "active"
    assert get_current_role() == "peer"


def test_posture_with_delegation_targets(temp_brain):
    """Posture can include delegation targets for delegate approach."""
    r = declare_posture(
        role="principal",
        approach="delegate",
        agent_id="agy",
        delegation_targets=["glm", "devin"],
    )
    assert r["success"]
    assert r["posture"]["delegation_targets"] == ["glm", "devin"]
