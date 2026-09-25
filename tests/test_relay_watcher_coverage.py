"""Coverage tests for mcp_server_nucleus.runtime.relay.watcher."""
import json
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.runtime.relay import watcher as watcher_mod


def _inject_fake_modules(stack, db_ret=None, add_task_ret=None, add_task_side_effect=None, emit_side_effect=None):
    """Inject fake db, task_ops, event_ops modules into sys.modules for relay package."""
    fake_db = types.ModuleType("mcp_server_nucleus.runtime.relay.db")
    fake_storage = mock.MagicMock()
    fake_storage.list_tasks.return_value = db_ret or []
    fake_db.get_storage_backend = mock.MagicMock(return_value=fake_storage)

    fake_task_ops = types.ModuleType("mcp_server_nucleus.runtime.relay.task_ops")
    if add_task_side_effect:
        fake_task_ops._add_task = mock.MagicMock(side_effect=add_task_side_effect)
    else:
        fake_task_ops._add_task = mock.MagicMock(return_value=add_task_ret or {"success": True, "task_id": "t1"})

    fake_event_ops = types.ModuleType("mcp_server_nucleus.runtime.relay.event_ops")
    if emit_side_effect:
        fake_event_ops._emit_event = mock.MagicMock(side_effect=emit_side_effect)
    else:
        fake_event_ops._emit_event = mock.MagicMock()

    stack.enter_context(mock.patch.dict(sys.modules, {
        "mcp_server_nucleus.runtime.relay.db": fake_db,
        "mcp_server_nucleus.runtime.relay.task_ops": fake_task_ops,
        "mcp_server_nucleus.runtime.relay.event_ops": fake_event_ops,
    }))
    return fake_db, fake_task_ops, fake_event_ops


def test_is_shipped_artifact_relay_id():
    assert watcher_mod._is_shipped_artifact("relay_20260601_120000_abc12345") is False


def test_is_shipped_artifact_normal_ref():
    assert watcher_mod._is_shipped_artifact("src/main.py") is True
    assert watcher_mod._is_shipped_artifact("feature/branch (merged)") is True


def test_is_shipped_artifact_empty():
    assert watcher_mod._is_shipped_artifact("") is False
    assert watcher_mod._is_shipped_artifact("  ") is False


def test_auto_dispatch_relay_no_brain_path(monkeypatch):
    monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    with mock.patch.object(watcher_mod, "_auto_dispatch_relay_inner"):
        watcher_mod._auto_dispatch_relay(
            {"id": "m1", "priority": "normal"}, "claude_code", brain_path=Path("/tmp/test")
        )
    assert "NUCLEUS_BRAIN_PATH" not in __import__("os").environ


def test_auto_dispatch_relay_restores_existing_brain_path(monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/original/brain")
    with mock.patch.object(watcher_mod, "_auto_dispatch_relay_inner"):
        watcher_mod._auto_dispatch_relay(
            {"id": "m1"}, "cc", brain_path=Path("/tmp/test")
        )
    assert __import__("os").environ["NUCLEUS_BRAIN_PATH"] == "/original/brain"


def test_auto_dispatch_relay_no_brain_path_arg(monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/keep")
    with mock.patch.object(watcher_mod, "_auto_dispatch_relay_inner"):
        watcher_mod._auto_dispatch_relay({"id": "m1"}, "cc", brain_path=None)
    assert __import__("os").environ["NUCLEUS_BRAIN_PATH"] == "/keep"


def test_auto_dispatch_relay_inner_normal_priority():
    """Normal priority relays are dispatched as P2 tasks."""
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(stack)
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "normal"},
            "claude_code",
        )
        fake_task_ops._add_task.assert_called_once()
        call_kwargs = fake_task_ops._add_task.call_args
        assert call_kwargs.kwargs["priority"] == 2


def test_auto_dispatch_relay_inner_high_priority():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(stack)
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "urgent", "body": "do this", "priority": "high"},
            "claude_code",
        )
        fake_task_ops._add_task.assert_called_once()
        call_kwargs = fake_task_ops._add_task.call_args
        assert call_kwargs.kwargs["priority"] == 2


def test_auto_dispatch_relay_inner_urgent_priority():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(stack)
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "urgent", "body": "do this now", "priority": "urgent"},
            "claude_code",
        )
        fake_task_ops._add_task.assert_called_once()
        call_kwargs = fake_task_ops._add_task.call_args
        assert call_kwargs.kwargs["priority"] == 1


def test_auto_dispatch_relay_inner_dedup():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(
            stack, db_ret=[{"source": "relay_dispatch:m1"}]
        )
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "high"},
            "claude_code",
        )
        fake_task_ops._add_task.assert_not_called()


def test_auto_dispatch_relay_inner_dedup_check_fails_open():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db = types.ModuleType("mcp_server_nucleus.runtime.relay.db")
        fake_db.get_storage_backend = mock.MagicMock(side_effect=Exception("db error"))
        fake_task_ops = types.ModuleType("mcp_server_nucleus.runtime.relay.task_ops")
        fake_task_ops._add_task = mock.MagicMock(return_value={"success": True, "task_id": "t1"})
        fake_event_ops = types.ModuleType("mcp_server_nucleus.runtime.relay.event_ops")
        fake_event_ops._emit_event = mock.MagicMock()
        stack.enter_context(mock.patch.dict(sys.modules, {
            "mcp_server_nucleus.runtime.relay.db": fake_db,
            "mcp_server_nucleus.runtime.relay.task_ops": fake_task_ops,
            "mcp_server_nucleus.runtime.relay.event_ops": fake_event_ops,
        }))
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "high"},
            "claude_code",
        )
        fake_task_ops._add_task.assert_called_once()


def test_auto_dispatch_relay_inner_add_task_fails():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(
            stack, add_task_ret={"success": False, "error": "bad"}
        )
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "high"},
            "claude_code",
        )
        fake_event_ops._emit_event.assert_not_called()


def test_auto_dispatch_relay_inner_add_task_exception():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(
            stack, add_task_side_effect=RuntimeError("boom")
        )
        # Should not raise
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "high"},
            "claude_code",
        )


def test_auto_dispatch_relay_inner_emit_event_fails():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(
            stack, emit_side_effect=RuntimeError("emit fail")
        )
        # Should not raise
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": "hello", "priority": "high"},
            "claude_code",
        )


def test_auto_dispatch_relay_inner_long_body_truncated():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(stack)
        long_body = "x" * 300
        watcher_mod._auto_dispatch_relay_inner(
            {"id": "m1", "from": "cowork", "subject": "hi", "body": long_body, "priority": "high"},
            "claude_code",
        )
        call_args = fake_task_ops._add_task.call_args
        desc = call_args.kwargs["description"]
        assert "..." in desc


def test_auto_dispatch_relay_inner_missing_fields():
    from contextlib import ExitStack
    with ExitStack() as stack:
        fake_db, fake_task_ops, fake_event_ops = _inject_fake_modules(stack)
        watcher_mod._auto_dispatch_relay_inner({}, "claude_code")
        fake_task_ops._add_task.assert_called_once()
