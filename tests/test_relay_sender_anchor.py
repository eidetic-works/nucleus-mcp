"""Forge tests for the relay-sender anchor stone.

PRINCIPAL.md §G1 (0b): "relay-sender (PID-ancestry sender binding — closes
the census's forgeable ``from``)".

Per the principal's requirement: "each stone byte-identical flag-OFF +
adversarially forge-verified with the closed forge angles landed as
committed regression tests — 'forge corpus present and passing'".

Forge angles:
  F1: process with token for role A posts with sender_anchor claiming
      role B → rejected (role mismatch)
  F2: process posts with a fabricated sender_anchor (no real session in
      the registry) → rejected (session not found)
  F3: process posts with a recycled PID whose create_time doesn't match
      → rejected (create_time mismatch)
  F4: flag OFF → all envelopes accepted, no anchor required
  F5: flag ON, no session registered → stamp returns no anchor → server
      rejects (fail-closed)
  F6: flag ON, valid anchor → accepted
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_registry(monkeypatch, tmp_path):
    """Isolate the session registry to a temp dir."""
    registry_dir = tmp_path / "agent_registry"
    registry_dir.mkdir()
    monkeypatch.setenv("NUCLEUS_AGENT_REGISTRY", str(registry_dir))
    # Also isolate brain path for _iter_envelopes
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    return registry_dir


@pytest.fixture
def anchor_on(monkeypatch):
    """Enable the relay-sender anchor flag."""
    monkeypatch.setenv("NUCLEUS_RELAY_SENDER_ANCHOR", "1")


@pytest.fixture
def anchor_off(monkeypatch):
    """Disable the relay-sender anchor flag (default)."""
    monkeypatch.delenv("NUCLEUS_RELAY_SENDER_ANCHOR", raising=False)


# ── stamp_sender_anchor ───────────────────────────────────────────────


def test_stamp_no_op_when_flag_off(anchor_off, isolated_registry):
    """F4: flag OFF → stamp is a no-op, payload unchanged."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import stamp_sender_anchor

    payload = {"to": "main", "subject": "test", "sender": "cc_main"}
    result = stamp_sender_anchor(payload)
    assert result == payload  # byte-identical
    assert "sender_anchor" not in result


def test_stamp_adds_anchor_when_session_registered(anchor_on, isolated_registry):
    """F6: flag ON + registered session → anchor stamped."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import stamp_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session

    # Register a session for the current process's parent
    register_session(
        session_id="test-sess-1",
        agent="claude_code",
        role="claude_code_main",
        provider="test",
        pid=os.getppid(),
    )

    payload = {"to": "main", "subject": "test", "sender": "claude_code_main"}
    result = stamp_sender_anchor(payload)
    assert "sender_anchor" in result
    assert result["sender_anchor"]["session_id"] == "test-sess-1"
    assert result["sender_anchor"]["role"] == "claude_code_main"


def test_stamp_no_anchor_when_no_session_registered(anchor_on, isolated_registry):
    """F5: flag ON + no registered session → no anchor (server will reject)."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import stamp_sender_anchor

    payload = {"to": "main", "subject": "test", "sender": "claude_code_main"}
    result = stamp_sender_anchor(payload)
    assert "sender_anchor" not in result  # no session found → no anchor


# ── verify_sender_anchor ──────────────────────────────────────────────


def test_verify_no_op_when_flag_off(anchor_off, isolated_registry):
    """F4: flag OFF → verify always returns (True, None)."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor

    ok, err = verify_sender_anchor({}, "claude_code_main")
    assert ok is True
    assert err is None


def test_verify_rejects_missing_anchor_when_flag_on(anchor_on, isolated_registry):
    """F5: flag ON + no sender_anchor → rejected (fail-closed)."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor

    ok, err = verify_sender_anchor({"sender": "claude_code_main"}, "claude_code_main")
    assert ok is False
    assert err == "sender_anchor_missing"


def test_verify_rejects_role_mismatch(anchor_on, isolated_registry):
    """F1: anchor claims role B but token is for role A → rejected."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session

    register_session(
        session_id="sess-role-a",
        agent="claude_code",
        role="claude_code_main",
        provider="test",
        pid=os.getppid(),
    )

    payload = {
        "sender": "claude_code_main",
        "sender_anchor": {
            "session_id": "sess-role-a",
            "pid": os.getppid(),
            "create_time": "",
            "role": "claude_code_peer",  # WRONG role
        },
    }
    ok, err = verify_sender_anchor(payload, "claude_code_main")
    assert ok is False
    assert err == "sender_anchor_role_mismatch"


def test_verify_rejects_fabricated_session(anchor_on, isolated_registry):
    """F2: anchor references a session that doesn't exist → rejected."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor

    payload = {
        "sender": "claude_code_main",
        "sender_anchor": {
            "session_id": "nonexistent-session",
            "pid": 99999,
            "create_time": "fake",
            "role": "claude_code_main",
        },
    }
    ok, err = verify_sender_anchor(payload, "claude_code_main")
    assert ok is False
    assert err == "sender_anchor_session_not_found"


def test_verify_rejects_create_time_mismatch(anchor_on, isolated_registry, monkeypatch):
    """F3: anchor's create_time doesn't match the registered session → rejected.
    Requires the identity anchor (NUCLEUS_IDENTITY_ANCHOR) to be ON so that
    register_session stamps create_time."""
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")  # dependency
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session

    register_session(
        session_id="sess-ct-test",
        agent="claude_code",
        role="claude_code_main",
        provider="test",
        pid=os.getppid(),
    )

    payload = {
        "sender": "claude_code_main",
        "sender_anchor": {
            "session_id": "sess-ct-test",
            "pid": os.getppid(),
            "create_time": "WRONG_CREATE_TIME",
            "role": "claude_code_main",
        },
    }
    ok, err = verify_sender_anchor(payload, "claude_code_main")
    assert ok is False
    assert err == "sender_anchor_create_time_mismatch"


def test_verify_accepts_valid_anchor(anchor_on, isolated_registry):
    """F6: flag ON + valid anchor matching registered session → accepted."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session, _envelope_path

    register_session(
        session_id="sess-valid",
        agent="claude_code",
        role="claude_code_main",
        provider="test",
        pid=os.getppid(),
    )

    # Read the actual registered envelope to get the real create_time
    env_path = _envelope_path("sess-valid")
    registered = json.loads(env_path.read_text())

    payload = {
        "sender": "claude_code_main",
        "sender_anchor": {
            "session_id": "sess-valid",
            "pid": registered.get("pid"),
            "create_time": registered.get("create_time", ""),
            "role": "claude_code_main",
        },
    }
    ok, err = verify_sender_anchor(payload, "claude_code_main")
    assert ok is True
    assert err is None


def test_verify_rejects_session_role_mismatch(anchor_on, isolated_registry):
    """F1 deep: anchor role matches token, but the registered session's
    role doesn't match → rejected (catches a stolen token posting as
    another session)."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session

    # Register a session for role B
    register_session(
        session_id="sess-peer",
        agent="claude_code",
        role="claude_code_peer",
        provider="test",
        pid=os.getppid(),
    )

    # Attacker has token for role A, but references role B's session
    # with anchor role set to A (lying)
    payload = {
        "sender": "claude_code_main",
        "sender_anchor": {
            "session_id": "sess-peer",
            "pid": os.getppid(),
            "create_time": "",
            "role": "claude_code_main",  # claims role A
        },
    }
    ok, err = verify_sender_anchor(payload, "claude_code_main")
    # The anchor role matches the token owner, but the registered session's
    # role (peer) doesn't match → rejected
    assert ok is False
    assert "mismatch" in err


def test_verify_http_mode_skips_registry_check():
    """F5 (HTTP): anchor with transport='http' skips F2/F3 — bearer token
    is the cross-machine anchor. F1 (role match) still applies."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor

    os.environ["NUCLEUS_RELAY_SENDER_ANCHOR"] = "1"
    try:
        # HTTP-mode anchor with a session_id that doesn't exist in the local
        # registry — the server should accept it because the bearer token
        # already verified the sender's identity (F1 passed).
        payload = {
            "sender": "devin",
            "sender_anchor": {
                "session_id": "remote-devin-sess-xyz",
                "pid": 99999,
                "create_time": "remote-machine-time",
                "role": "devin",
                "transport": "http",
            },
        }
        ok, err = verify_sender_anchor(payload, "devin")
        assert ok is True
        assert err is None
    finally:
        os.environ.pop("NUCLEUS_RELAY_SENDER_ANCHOR", None)


def test_verify_http_mode_still_rejects_role_mismatch():
    """F6 (HTTP): even in HTTP mode, a role mismatch is rejected — the
    bearer token binds the sender to a role, and the anchor's role must
    match."""
    from mcp_server_nucleus.sessions.relay_sender_anchor import verify_sender_anchor

    os.environ["NUCLEUS_RELAY_SENDER_ANCHOR"] = "1"
    try:
        payload = {
            "sender": "devin",
            "sender_anchor": {
                "session_id": "remote-sess-xyz",
                "pid": 99999,
                "create_time": "remote-time",
                "role": "claude_code_main",  # claims to be cc_main
                "transport": "http",
            },
        }
        # Token owner is devin — anchor claims claude_code_main → rejected
        ok, err = verify_sender_anchor(payload, "devin")
        assert ok is False
        assert err == "sender_anchor_role_mismatch"
    finally:
        os.environ.pop("NUCLEUS_RELAY_SENDER_ANCHOR", None)


def test_stamp_http_mode_when_relay_url_set(tmp_path, monkeypatch):
    """When NUCLEUS_RELAY_URL is set, stamp_sender_anchor adds
    transport='http' to the anchor."""
    import uuid
    from mcp_server_nucleus.sessions.relay_sender_anchor import stamp_sender_anchor
    from mcp_server_nucleus.sessions.registry import register_session

    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_SENDER_ANCHOR", "1")
    monkeypatch.setenv("NUCLEUS_IDENTITY_ANCHOR", "1")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))

    register_session(
        session_id=f"http-sess-{uuid.uuid4().hex[:8]}",
        agent="devin",
        role="devin",
        provider="devin",
        pid=os.getppid(),
    )

    payload = {"sender": "devin", "to": "claude_code_main", "subject": "test"}
    stamped = stamp_sender_anchor(payload)
    assert "sender_anchor" in stamped
    assert stamped["sender_anchor"]["transport"] == "http"
