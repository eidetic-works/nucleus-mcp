"""Tests for tools/relay.py — nucleus_relay facade.

Per ADR-0036 amendment c068abc1: facade wraps runtime/relay_transport.py.
relay_transport itself is exhaustively tested in test_relay_transport.py
(41/41 GREEN post PR #493 e4e5e817). This file covers the FACADE layer:
- action dispatch routes to correct relay_transport function
- CC_SESSION_ROLE auto-fill for inbox/ack/status
- payload assembly for post (explicit kwargs → dict)
- json.dumps response shape
- status action is diagnostic-only (does NOT call server)
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────


class _FakeMCP:
    """Stand-in for FastMCP. Captures registered tool function."""
    def __init__(self):
        self._registered = []

    def tool(self, **kwargs):
        def decorator(fn):
            self._registered.append(fn)
            return fn
        return decorator


@pytest.fixture
def relay_tool():
    """Register tools/relay.py against a FakeMCP and return the facade fn."""
    from mcp_server_nucleus.tools import relay as relay_mod
    mcp = _FakeMCP()
    pairs = relay_mod.register(mcp, helpers=None)
    assert len(pairs) == 1
    name, fn = pairs[0]
    assert name == "nucleus_relay"
    return fn


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    """Reset envs each test + isolate HOME so per-role files (v0.2.1) don't
    collide with operator's real ~/.tb/relay_token_* during tests.

    PR #494 facade tests focus on action-dispatch + routing concerns; v0.2.1
    bearer-resolution paths are exercised in test_v021_per_role_bearer.py.
    To keep dispatch flowing past _resolve_bearer here, install a default
    NUCLEUS_RELAY_BEARER so the facade's bearer-resolution succeeds via
    env-fallback. Tests that explicitly assert bearer-precedence override
    this via their own monkeypatch.setenv calls.
    """
    for k in ("NUCLEUS_RELAY_URL", "NUCLEUS_RELAY_BEARER", "CC_SESSION_ROLE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "pr494-test-default-bearer")


# ── Action: post ─────────────────────────────────────────────────────────


async def test_post_forwards_to_relay_transport_post_relay(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "msg-1"},
    ) as mock_post:
        result = await relay_tool(
            "post",
            {"to": "main", "subject": "hi", "body": {"text": "hello"}},
        )
    parsed = json.loads(result)
    assert parsed == {"sent": True, "id": "msg-1"}
    assert mock_post.call_count == 1
    payload = mock_post.call_args[0][0]
    assert payload["to"] == "main"
    assert payload["subject"] == "hi"
    assert payload["body"] == {"text": "hello"}
    assert payload["priority"] == "normal"


async def test_post_missing_to_short_circuits_no_call(relay_tool):
    with patch("mcp_server_nucleus.runtime.relay_transport.post_relay") as mock_post:
        result = await relay_tool("post", {"subject": "no-recipient"})
    parsed = json.loads(result)
    assert parsed == {"sent": False, "error": "missing_to_field"}
    mock_post.assert_not_called()


async def test_post_omits_optional_fields_when_unset(relay_tool):
    """in_reply_to/context/id/from_session_id stay omitted when unset.

    sender is the Task #62 exception: it now auto-fills from the resolved
    role (env unset here → 'main') instead of being omitted, because the
    server REQUIRES sender and enforces sender == token_owner (403).
    """
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool("post", {"to": "tb", "subject": "x"})
    payload = mock_post.call_args[0][0]
    assert "in_reply_to" not in payload
    assert "context" not in payload
    assert "id" not in payload
    assert "from_session_id" not in payload
    assert payload["sender"] == "main"


async def test_post_includes_optional_fields_when_set(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool(
            "post",
            {
                "to": "peer",
                "subject": "x",
                "body": {},
                "sender": "tb",
                "in_reply_to": "prev-id",
                "context": {"thread": "abc"},
                "id": "my-idem-key",
                "from_session_id": "sess-1",
                "priority": "high",
            },
        )
    payload = mock_post.call_args[0][0]
    assert payload["sender"] == "tb"
    assert payload["in_reply_to"] == "prev-id"
    assert payload["context"] == {"thread": "abc"}
    assert payload["id"] == "my-idem-key"
    assert payload["from_session_id"] == "sess-1"
    assert payload["priority"] == "high"


async def test_post_body_defaults_to_empty_dict(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool("post", {"to": "main", "subject": "x"})
    payload = mock_post.call_args[0][0]
    assert payload["body"] == {}


async def test_post_passes_through_relay_transport_error(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": False, "error": 500},
    ):
        result = await relay_tool("post", {"to": "main", "subject": "x"})
    parsed = json.loads(result)
    assert parsed == {"sent": False, "error": 500}


# ── Action: post — Task #62 sender auto-fill ────────────────────────────


async def test_post_sender_auto_fills_from_cc_session_role(relay_tool, monkeypatch):
    """Omitted sender defaults to the SAME role string that selects the
    bearer — authenticated-default attribution, not the R6.1-banned
    detect_session_type() heuristic (server still 403s a mismatch)."""
    monkeypatch.setenv("CC_SESSION_ROLE", "bespoq_cowork")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool("post", {"to": "ops", "subject": "x"})
    payload = mock_post.call_args[0][0]
    assert payload["sender"] == "bespoq_cowork"


async def test_post_sender_auto_fill_follows_explicit_role_param(relay_tool, monkeypatch):
    """role param outranks CC_SESSION_ROLE for both bearer AND sender."""
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool("post", {"to": "peer", "subject": "x", "role": "tb"})
    payload = mock_post.call_args[0][0]
    assert payload["sender"] == "tb"


async def test_post_explicit_sender_overrides_auto_fill(relay_tool, monkeypatch):
    """Explicit sender param is preserved verbatim (back-compat with all
    existing callers that pass sender)."""
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay",
        return_value={"sent": True, "id": "x"},
    ) as mock_post:
        await relay_tool("post", {"to": "peer", "subject": "x", "sender": "cc_tb"})
    payload = mock_post.call_args[0][0]
    assert payload["sender"] == "cc_tb"


# ── Action: inbox ────────────────────────────────────────────────────────


async def test_inbox_role_auto_fills_from_cc_session_role(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[{"id": "m1"}],
    ) as mock_read:
        result = await relay_tool("inbox", {})
    parsed = json.loads(result)
    # v0.2 Seq-3: truth-in-signaling flags surfaced; plain-list return
    # (no InboxResult attrs) degrades to all-False via getattr defaults.
    assert parsed == {
        "messages": [{"id": "m1"}],
        "role": "tb",
        "has_more": False,
        "rate_limited": False,
        "transport_error": False,
    }
    mock_read.assert_called_once_with("tb", unread_only=True, limit=50, bearer="pr494-test-default-bearer")


async def test_inbox_explicit_role_param_overrides_env(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {"role": "peer"})
    mock_read.assert_called_once_with("peer", unread_only=True, limit=50, bearer="pr494-test-default-bearer")


async def test_inbox_role_defaults_to_main_when_env_unset(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {})
    mock_read.assert_called_once_with("main", unread_only=True, limit=50, bearer="pr494-test-default-bearer")


async def test_inbox_unread_only_false_passes_through(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {"unread_only": False, "limit": 10})
    mock_read.assert_called_once_with("main", unread_only=False, limit=10, bearer="pr494-test-default-bearer")


async def test_inbox_limit_coerced_to_int(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=[],
    ) as mock_read:
        await relay_tool("inbox", {"limit": "25"})
    mock_read.assert_called_once_with("main", unread_only=True, limit=25, bearer="pr494-test-default-bearer")


async def test_inbox_surfaces_inbox_result_flags(relay_tool):
    """v0.2 Seq-3 (peer follow-up a): InboxResult truth-in-signaling flags
    reach the MCP client JSON instead of being dropped at the facade."""
    from mcp_server_nucleus.runtime.relay_transport import InboxResult

    result_obj = InboxResult(
        [{"id": "m1"}], has_more=True, rate_limited=True, transport_error=False
    )
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=result_obj,
    ):
        result = await relay_tool("inbox", {})
    parsed = json.loads(result)
    assert parsed["messages"] == [{"id": "m1"}]
    assert parsed["has_more"] is True
    assert parsed["rate_limited"] is True
    assert parsed["transport_error"] is False


async def test_inbox_transport_error_flag_distinguishes_failure_from_empty(relay_tool):
    from mcp_server_nucleus.runtime.relay_transport import InboxResult

    with patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox",
        return_value=InboxResult(transport_error=True),
    ):
        result = await relay_tool("inbox", {})
    parsed = json.loads(result)
    assert parsed["messages"] == []
    assert parsed["transport_error"] is True


# ── Action: ack ──────────────────────────────────────────────────────────


async def test_ack_forwards_message_ids(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.mark_seen",
        return_value={"acked": 2, "failed": 0},
    ) as mock_ack:
        result = await relay_tool("ack", {"message_ids": ["m1", "m2"]})
    parsed = json.loads(result)
    assert parsed == {"acked": 2, "failed": 0}
    mock_ack.assert_called_once_with("tb", ["m1", "m2"], bearer="pr494-test-default-bearer")


async def test_ack_role_explicit_overrides_env(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.mark_seen",
        return_value={"acked": 1, "failed": 0},
    ) as mock_ack:
        await relay_tool("ack", {"message_ids": ["m1"], "role": "main"})
    mock_ack.assert_called_once_with("main", ["m1"], bearer="pr494-test-default-bearer")


async def test_ack_empty_message_ids_still_calls(relay_tool):
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.mark_seen",
        return_value={"acked": 0, "failed": 0},
    ) as mock_ack:
        await relay_tool("ack", {})
    mock_ack.assert_called_once_with("main", [], bearer="pr494-test-default-bearer")


# ── Action: status (diagnostic, no server call) ─────────────────────────


async def test_status_returns_env_shape_no_server_call(relay_tool):
    """status MUST NOT call relay_transport functions that hit HTTP."""
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.post_relay"
    ) as mock_post, patch(
        "mcp_server_nucleus.runtime.relay_transport.read_inbox"
    ) as mock_read, patch(
        "mcp_server_nucleus.runtime.relay_transport.mark_seen"
    ) as mock_ack:
        result = await relay_tool("status", {})
    parsed = json.loads(result)
    assert "is_http_mode" in parsed
    assert "relay_url_set" in parsed
    assert "bearer_set" in parsed
    assert "canonical_role" in parsed
    assert "resolved_inbox_dir" in parsed
    mock_post.assert_not_called()
    mock_read.assert_not_called()
    mock_ack.assert_not_called()


async def test_status_reports_http_mode_off_when_url_unset(relay_tool, monkeypatch):
    """When URL is unset, is_http_mode + url_set are False regardless of bearer.

    NB: autouse _clean_env sets a default NUCLEUS_RELAY_BEARER so PR #494's
    inbox/post/ack facade tests pass through v0.2.1 _resolve_bearer; here we
    explicitly clear it to assert the no-bearer-anywhere status shape.
    """
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    result = await relay_tool("status", {})
    parsed = json.loads(result)
    assert parsed["is_http_mode"] is False
    assert parsed["relay_url_set"] is False
    assert parsed["bearer_set"] is False


async def test_status_reports_http_mode_on_with_url_and_bearer(relay_tool, monkeypatch):
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "test-token")
    result = await relay_tool("status", {})
    parsed = json.loads(result)
    assert parsed["is_http_mode"] is True
    assert parsed["relay_url_set"] is True
    assert parsed["bearer_set"] is True


async def test_status_canonical_role_from_env(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "tb")
    result = await relay_tool("status", {})
    parsed = json.loads(result)
    assert parsed["canonical_role"] == "tb"
    assert parsed["resolved_inbox_dir"] == "cc_tb"


async def test_status_canonical_role_explicit_override(relay_tool, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "main")
    result = await relay_tool("status", {"role": "peer"})
    parsed = json.loads(result)
    assert parsed["canonical_role"] == "peer"


async def test_status_bearer_set_does_not_leak_value(relay_tool, monkeypatch):
    """Crack 1 from cc-peer hole-poke-invited areas: status must not echo bearer."""
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://r.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "sk-very-secret-token-xyz")
    result = await relay_tool("status", {})
    assert "sk-very-secret-token-xyz" not in result
    parsed = json.loads(result)
    assert parsed["bearer_set"] is True
    assert "bearer" not in {k.lower() for k in parsed.keys() if k != "bearer_set"}


# ── Dispatch + registration ─────────────────────────────────────────────


async def test_register_returns_single_facade_tuple(relay_tool):
    """register() returns [("nucleus_relay", fn)]."""
    assert callable(relay_tool)


async def test_unknown_action_dispatched_via_dispatch_helper(relay_tool):
    """Unknown action goes through dispatch — surfaces error envelope (not raise)."""
    result = await relay_tool("nonexistent_action", {})
    # Result is a JSON string from dispatch's error envelope; just assert it's a string
    # and doesn't crash. Dispatch returns its own shape (likely error/unknown_action).
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
