"""Coverage tests for mcp_server_nucleus.tools.sessions (facade register + dispatch)."""
import asyncio
import json
from contextlib import ExitStack
from unittest import mock

import pytest


class MockMCP:
    def __init__(self):
        self.captured = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.captured[func.__name__] = func
            return func
        return decorator


def _make_helpers(**overrides):
    base = {
        "make_response": lambda success, data=None, error=None: json.dumps(
            {"success": success, "data": data, "error": error}
        ),
        "emit_event": lambda *a, **kw: "evt-123",
        "read_events": lambda *a: [],
        "get_state": lambda *a: {},
        "update_state": lambda *a: "OK",
        "get_brain_path": lambda: "/tmp/test_brain",
    }
    base.update(overrides)
    return base


# All patches needed for register() to succeed
_PATCH_TARGETS = {
    "save": "mcp_server_nucleus.runtime.session_ops._save_session",
    "resume": "mcp_server_nucleus.runtime.session_ops._resume_session",
    "list_sessions": "mcp_server_nucleus.runtime.session_ops._list_sessions",
    "check_recent": "mcp_server_nucleus.runtime.session_ops._check_for_recent_session",
    "end": "mcp_server_nucleus.runtime.session_ops._brain_session_end_impl",
    "start": "mcp_server_nucleus.runtime.session_ops._brain_session_start_impl",
    "archive": "mcp_server_nucleus.runtime.consolidation_ops._archive_resolved_files",
    "merges": "mcp_server_nucleus.runtime.consolidation_ops._generate_merge_proposals",
    "gc": "mcp_server_nucleus.runtime.consolidation_ops._garbage_collect_tasks",
    "checkpoint": "mcp_server_nucleus.runtime.checkpoint_ops._brain_checkpoint_task_impl",
    "resume_cp": "mcp_server_nucleus.runtime.checkpoint_ops._brain_resume_from_checkpoint_impl",
    "handoff": "mcp_server_nucleus.runtime.checkpoint_ops._brain_generate_handoff_summary_impl",
    "ingest": "mcp_server_nucleus.runtime.conversation_ops.ingest_conversations",
    "search": "mcp_server_nucleus.runtime.conversation_ops.search_conversations",
    "list_conv": "mcp_server_nucleus.runtime.conversation_ops.list_conversations",
    "stats": "mcp_server_nucleus.runtime.conversation_ops.conversation_stats",
    "detect_splits": "mcp_server_nucleus.sessions.registry.detect_splits",
    "heartbeat": "mcp_server_nucleus.sessions.registry.heartbeat",
    "list_agents": "mcp_server_nucleus.sessions.registry.list_agents",
    "register_session": "mcp_server_nucleus.sessions.registry.register_session",
    "unregister": "mcp_server_nucleus.sessions.registry.unregister",
}

_DEFAULT_RETURNS = {
    "save": {"success": True, "session_id": "s1"},
    "resume": {"session_id": "s1", "context": "test"},
    "list_sessions": {"sessions": [], "total": 0},
    "check_recent": {"exists": False},
    "end": {"success": True},
    "start": "Session started",
    "archive": {"archived": 0},
    "merges": {"proposals": []},
    "gc": {"gc": True},
    "checkpoint": "checkpoint saved",
    "resume_cp": "resumed",
    "handoff": "handoff",
    "ingest": {"ingested": 0},
    "search": {"results": []},
    "list_conv": {"sessions": []},
    "stats": {"stats": {}},
    "detect_splits": [],
    "heartbeat": {"alive": True},
    "list_agents": [],
    "register_session": {"session_id": "x"},
    "unregister": True,
}


def _do_register(helpers=None, overrides=None):
    """Register sessions facade with all mocks applied. Returns (mcp, result)."""
    helpers = helpers or _make_helpers()
    overrides = overrides or {}
    mcp = MockMCP()
    with ExitStack() as stack:
        mocks = {}
        for key, target in _PATCH_TARGETS.items():
            ret = overrides.get(key, _DEFAULT_RETURNS[key])
            side_effect = overrides.get(f"{key}_side_effect")
            if side_effect is not None:
                m = stack.enter_context(mock.patch(target, side_effect=side_effect))
            else:
                m = stack.enter_context(mock.patch(target, return_value=ret))
            mocks[key] = m
        from mcp_server_nucleus.tools.sessions import register
        result = register(mcp, helpers)
    return mcp, result


def test_register_returns_tool_list():
    mcp, result = _do_register()
    assert len(result) == 1
    assert result[0][0] == "nucleus_sessions"


def test_dispatch_save_success():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("save", {"context": "working on X"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_save_failure():
    mcp, result = _do_register(overrides={"save": {"success": False, "error": "bad"}})
    tool = result[0][1]
    out = asyncio.run(tool("save", {"context": "X"}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_resume_success():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("resume", {"session_id": "s1"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_resume_not_found():
    mcp, result = _do_register(overrides={"resume": None})
    tool = result[0][1]
    out = asyncio.run(tool("resume", {}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_list():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("list", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_check_recent():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("check_recent", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_current_alias():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("current", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_end_success():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("end", {"summary": "done"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_end_failure():
    mcp, result = _do_register(overrides={"end": {"success": False, "error": "bad"}})
    tool = result[0][1]
    out = asyncio.run(tool("end", {"summary": ""}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_start():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("start", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_start_error():
    mcp, result = _do_register(overrides={"start": "Error: no brain"})
    tool = result[0][1]
    out = asyncio.run(tool("start", {}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_start_error_prefix():
    mcp, result = _do_register(overrides={"start": "❌ something went wrong"})
    tool = result[0][1]
    out = asyncio.run(tool("start", {}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_emit_event():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("emit_event", {"event_type": "test", "emitter": "me", "data": {}}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_emit_event_error():
    helpers = _make_helpers(emit_event=lambda *a, **kw: "Error: failed")
    mcp, result = _do_register(helpers=helpers)
    tool = result[0][1]
    out = asyncio.run(tool("emit_event", {"event_type": "test", "emitter": "me", "data": {}}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_register_success():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("register", {"session_id": "s1", "agent": "a", "role": "r", "provider": "p"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_register_error():
    mcp, result = _do_register(overrides={"register_session_side_effect": ValueError("bad")})
    tool = result[0][1]
    out = asyncio.run(tool("register", {"session_id": "s1", "agent": "a", "role": "r", "provider": "p"}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_register_oserror():
    mcp, result = _do_register(overrides={"register_session_side_effect": OSError("bad")})
    tool = result[0][1]
    out = asyncio.run(tool("register", {"session_id": "s1", "agent": "a", "role": "r", "provider": "p"}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_heartbeat_success():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("heartbeat", {"session_id": "s1"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_heartbeat_error():
    mcp, result = _do_register(overrides={"heartbeat_side_effect": FileNotFoundError("nope")})
    tool = result[0][1]
    out = asyncio.run(tool("heartbeat", {"session_id": "s1"}))
    data = json.loads(out)
    assert data["success"] is False


def test_dispatch_unregister():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("unregister", {"session_id": "s1"}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_list_agents():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("list_agents", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_detect_splits():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("detect_splits", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_various_actions():
    mcp, result = _do_register()
    tool = result[0][1]
    for action, params in [
        ("archive_resolved", {}),
        ("propose_merges", {}),
        ("garbage_collect", {}),
        ("read_events", {}),
        ("get_state", {}),
        ("update_state", {"updates": {}}),
        ("checkpoint", {"task_id": "t1"}),
        ("resume_checkpoint", {"task_id": "t1"}),
        ("handoff_summary", {"task_id": "t1", "summary": "s"}),
        ("ingest_conversations", {}),
        ("search_conversations", {}),
        ("list_conversations", {}),
        ("conversation_stats", {}),
    ]:
        out = asyncio.run(tool(action, params))
        data = json.loads(out)
        assert data["success"] is True, f"Failed for action: {action}"


def test_dispatch_unknown_action():
    mcp, result = _do_register()
    tool = result[0][1]
    out = asyncio.run(tool("nonexistent", {}))
    data = json.loads(out)
    assert "error" in data or data.get("success") is False
