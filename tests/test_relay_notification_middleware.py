"""Tests for relay notification middleware.

The middleware auto-surfaces unread relays on every tool call via ctx.info().
This is the client-agnostic replacement for Claude Code's SessionStart hook.
"""
import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from mcp_server_nucleus.runtime.relay_notification_middleware import (
    RelayNotificationMiddleware,
    _resolve_inbox,
    _armed_sessions,
)
from mcp_server_nucleus.runtime.relay.core import relay_post
from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture


@pytest.fixture
def temp_brain(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", tmpdir)
    monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
    yield tmpdir


def test_resolve_inbox_from_posture(temp_brain):
    """_resolve_inbox returns the agent's canonical inbox from posture."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    ctx = MagicMock()
    inbox = _resolve_inbox(ctx)
    assert inbox == "antigravity"


def test_resolve_inbox_falls_back_to_env_role(temp_brain, monkeypatch):
    """Without posture, _resolve_inbox falls back to CC_SESSION_ROLE env."""
    monkeypatch.setenv("CC_SESSION_ROLE", "agy")
    ctx = MagicMock()
    inbox = _resolve_inbox(ctx)
    assert inbox == "antigravity"


def test_resolve_inbox_returns_none_without_config(temp_brain):
    """Without posture or env role, _resolve_inbox returns None."""
    ctx = MagicMock()
    inbox = _resolve_inbox(ctx)
    assert inbox is None


def test_middleware_surfaces_unread_relay(temp_brain):
    """Middleware fires ctx.info() when unread relays exist."""
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    relay_post(
        to="antigravity",
        subject="[TASK] test_middleware",
        body="Execute this task.",
        sender="task_scheduler",
    )

    # Create mock context
    ctx = AsyncMock()
    ctx.session_id = "test-session-1"

    context = MagicMock()
    context.fastmcp_context = ctx

    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()
    result = asyncio.run(
        middleware.on_call_tool(context, call_next)
    )

    # ctx.info should have been called with relay info
    assert ctx.info.called
    info_call = ctx.info.call_args[0][0]
    assert "[relay-arrival]" in info_call
    assert "[TASK] test_middleware" in info_call
    assert "Execute this task." in info_call
    # Should include message_id and ack hint
    assert "id=" in info_call
    assert "nucleus_next_message" in info_call
    assert "relay_ack" in info_call


def test_middleware_no_info_when_no_unread(temp_brain):
    """Middleware does NOT fire relay-arrival ctx.info() when inbox is empty."""
    _armed_sessions.clear()
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    ctx = AsyncMock()
    ctx.session_id = "test-session-2"

    context = MagicMock()
    context.fastmcp_context = ctx

    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()
    result = asyncio.run(
        middleware.on_call_tool(context, call_next)
    )

    # No relay-arrival (inbox empty), no arm-directive (that's on_list_tools)
    ctx.info.assert_not_called()


def test_middleware_throttles_rapid_calls(temp_brain):
    """Middleware doesn't check more than once per 10 seconds per session."""
    from mcp_server_nucleus.runtime.relay_notification_middleware import _last_check, _surfaced_ids
    _last_check.clear()
    _surfaced_ids.clear()

    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    relay_post(
        to="antigravity",
        subject="[TASK] throttle_test",
        body="Task.",
        sender="task_scheduler",
    )

    ctx = AsyncMock()
    ctx.session_id = "test-session-3"

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()

    # First call — should fire ctx.info
    asyncio.run(
        middleware.on_call_tool(context, call_next)
    )
    first_call_count = ctx.info.call_count
    assert first_call_count > 0

    # Second call immediately — should NOT fire (throttled)
    asyncio.run(
        middleware.on_call_tool(context, call_next)
    )
    assert ctx.info.call_count == first_call_count  # no new calls


def test_middleware_does_not_renag_same_message(temp_brain):
    """Middleware doesn't re-surface the same message ID within a session."""
    from mcp_server_nucleus.runtime.relay_notification_middleware import _last_check, _surfaced_ids
    _last_check.clear()
    _surfaced_ids.clear()
    _armed_sessions.clear()

    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    relay_post(
        to="antigravity",
        subject="[TASK] no_renag",
        body="Task.",
        sender="task_scheduler",
    )

    ctx = AsyncMock()
    ctx.session_id = "test-session-renag"

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()

    # First call — surfaces the relay + arm-directive
    asyncio.run(
        middleware.on_call_tool(context, call_next)
    )
    arrival_count_1 = sum(1 for c in ctx.info.call_args_list if "[relay-arrival]" in c[0][0])
    assert arrival_count_1 == 1

    # Bypass throttle by manually resetting last_check
    _last_check.clear()

    # Second call — same message, should NOT re-surface relay-arrival
    asyncio.run(
        middleware.on_call_tool(context, call_next)
    )
    arrival_count_2 = sum(1 for c in ctx.info.call_args_list if "[relay-arrival]" in c[0][0])
    assert arrival_count_2 == 1  # still 1, no re-nag


def test_middleware_continues_on_error(temp_brain):
    """Middleware doesn't block tool execution if relay check fails."""
    ctx = AsyncMock()
    ctx.session_id = None  # will cause fallback path

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()
    result = asyncio.run(
        middleware.on_call_tool(context, call_next)
    )

    # Tool should still execute
    assert result == {"result": "ok"}


def test_on_initialize_surfaces_pending_relays(temp_brain):
    """on_list_tools surfaces pending relays + fires arm-directive at connection."""
    from mcp_server_nucleus.runtime.relay_notification_middleware import _last_check, _surfaced_ids
    _last_check.clear()
    _surfaced_ids.clear()
    _armed_sessions.clear()

    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    relay_post(
        to="antigravity",
        subject="[TASK] init_test",
        body="Task waiting at startup.",
        sender="task_scheduler",
    )

    ctx = AsyncMock()
    ctx.session_id = "test-session-init"

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()
    asyncio.run(
        middleware.on_list_tools(context, call_next)
    )

    # Should have surfaced the pending relay
    info_calls = [c[0][0] for c in ctx.info.call_args_list]
    assert any("[relay-pending]" in c for c in info_calls)
    assert any("[TASK] init_test" in c for c in info_calls)

    # Should have fired the arm directive
    assert any("[arm-directive]" in c for c in info_calls)
    assert any("nucleus_next_message" in c for c in info_calls)


def test_on_initialize_fires_arm_directive_even_when_empty(temp_brain):
    """on_list_tools fires arm directive even with no pending relays."""
    from mcp_server_nucleus.runtime.relay_notification_middleware import _last_check, _surfaced_ids
    _last_check.clear()
    _surfaced_ids.clear()
    _armed_sessions.clear()

    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    ctx = AsyncMock()
    ctx.session_id = "test-session-init-empty"

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()
    asyncio.run(
        middleware.on_list_tools(context, call_next)
    )

    # Should have fired the arm directive
    info_calls = [c[0][0] for c in ctx.info.call_args_list]
    assert any("[arm-directive]" in c for c in info_calls)
    assert any("nucleus_next_message" in c for c in info_calls)
    # Should NOT have fired relay-pending (no relays)
    assert not any("[relay-pending]" in c for c in info_calls)


def test_arm_directive_fires_only_once_per_session(temp_brain):
    """Arm-directive fires on on_list_tools, not on subsequent on_call_tool."""
    from mcp_server_nucleus.runtime.relay_notification_middleware import _last_check, _surfaced_ids
    _last_check.clear()
    _surfaced_ids.clear()
    _armed_sessions.clear()

    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    ctx = AsyncMock()
    ctx.session_id = "test-session-arm-once"

    context = MagicMock()
    context.fastmcp_context = ctx
    call_next = AsyncMock(return_value={"result": "ok"})

    middleware = RelayNotificationMiddleware()

    # on_list_tools — should fire arm-directive
    asyncio.run(
        middleware.on_list_tools(context, call_next)
    )
    arm_count = sum(1 for c in ctx.info.call_args_list if "[arm-directive]" in c[0][0])
    assert arm_count == 1

    # on_call_tool — should NOT fire arm-directive
    _last_check.clear()
    asyncio.run(
        middleware.on_call_tool(context, call_next)
    )
    total_arm = sum(1 for c in ctx.info.call_args_list if "[arm-directive]" in c[0][0])
    assert total_arm == 1  # still 1
