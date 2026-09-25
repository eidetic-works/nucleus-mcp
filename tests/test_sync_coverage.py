"""Coverage tests for mcp_server_nucleus.tools.sync."""
from mcp_server_nucleus.runtime.stdio_server import make_response
import json
import os
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.tools import sync as sync_mod


def _mock_helpers(tmp_path):
    """Create mock helpers dict for register()."""
    emit_event = mock.MagicMock()
    get_brain_path = mock.MagicMock(return_value=tmp_path / ".brain")
    return {"emit_event": emit_event, "get_brain_path": get_brain_path,
        # sync.py and friends require this third helper since 286928c8
        # (2026-08-04); the fixtures were never updated, which is what
        # produced KeyError: \'make_response\' -- a STALE FIXTURE, not the
        # environment fault it was first classified as. The REAL helper is
        # used rather than a MagicMock so the tests still exercise actual
        # response serialization.
        "make_response": make_response}


def _mock_mcp():
    """Create a mock MCP that captures tool registrations."""
    tools = {}

    class _McpToolDecorator:
        def __init__(self, title, annotations):
            self.title = title
            self.annotations = annotations

        def __call__(self, fn):
            tools[fn.__name__] = fn
            return fn

    mcp = mock.MagicMock()

    def tool(title="", annotations=None):
        return _McpToolDecorator(title, annotations or {})

    mcp.tool = tool
    return mcp, tools


def test_register_returns_tool_list(tmp_path):
    """register() returns a list of (name, function) tuples."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        result = sync_mod.register(mcp, helpers)
    assert isinstance(result, list)
    assert len(result) >= 3
    names = [r[0] for r in result]
    assert "nucleus_sync" in names
    assert "nucleus_relay_subscribe" in names
    assert "nucleus_ccr_arm" in names


@pytest.mark.asyncio
async def test_nucleus_sync_identify_agent_no_provider(tmp_path):
    """identify_agent without provider/session_id or agent_id returns error."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        sync_mod.register(mcp, helpers)
    nucleus_sync = tools["nucleus_sync"]
    result = await nucleus_sync("identify_agent", {})
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_nucleus_sync_identify_agent_legacy(tmp_path):
    """identify_agent with agent_id (legacy shape) works."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "test-agent", "role": ""}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=[]):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value=""):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {"agent_id": "a1", "environment": "test"})
    data = json.loads(result)
    assert data["agent_id"] == "test-agent"


@pytest.mark.asyncio
async def test_nucleus_sync_identify_agent_with_provider(tmp_path):
    """identify_agent with provider/session_id (ADR-0005 shape)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "test-agent", "role": "dev"}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=[]):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value="cc_tb"):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {
                        "role": "dev", "provider": "claude_code", "session_id": "s1"
                    })
    data = json.loads(result)
    assert data["agent_id"] == "test-agent"
    assert data["canonical_inbox"] == "cc_tb"


@pytest.mark.asyncio
async def test_nucleus_sync_identify_agent_collision(tmp_path):
    """identify_agent detects collision from recent events."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    collision_events = [
        {"type": "AGENT_REGISTERED", "data": {"session_id": "s1", "host": "other-host"}, "emitter": ""}
    ]
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "test-agent", "role": ""}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=collision_events):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value=""):
                    with mock.patch("socket.gethostname", return_value="this-host"):
                        sync_mod.register(mcp, helpers)
                        nucleus_sync = tools["nucleus_sync"]
                        result = await nucleus_sync("identify_agent", {
                            "role": "dev", "provider": "cc", "session_id": "s1"
                        })
    data = json.loads(result)
    assert "collision_warning" in data


@pytest.mark.asyncio
async def test_nucleus_sync_sync_now_disabled(tmp_path):
    """sync_now when sync is disabled returns error."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.is_sync_enabled", return_value=False):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("sync_now", {})
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_nucleus_sync_sync_now_success(tmp_path):
    """sync_now when sync is enabled performs sync."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.is_sync_enabled", return_value=True):
            with mock.patch("mcp_server_nucleus.runtime.sync_ops.sync_lock") as mock_lock:
                mock_lock.return_value.__enter__ = mock.MagicMock()
                mock_lock.return_value.__exit__ = mock.MagicMock(return_value=False)
                with mock.patch("mcp_server_nucleus.runtime.sync_ops.perform_sync", return_value={"status": "ok"}):
                    with mock.patch("mcp_server_nucleus.runtime.sync_ops.record_sync_time"):
                        with mock.patch("mcp_server_nucleus.runtime.sync_ops.get_current_agent", return_value="agent1"):
                            sync_mod.register(mcp, helpers)
                            nucleus_sync = tools["nucleus_sync"]
                            result = await nucleus_sync("sync_now", {})
    data = json.loads(result)
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_nucleus_sync_sync_now_exception(tmp_path):
    """sync_now handles exceptions."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.is_sync_enabled", return_value=True):
            with mock.patch("mcp_server_nucleus.runtime.sync_ops.sync_lock", side_effect=Exception("lock fail")):
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("sync_now", {})
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_nucleus_sync_sync_auto_enable(tmp_path):
    """sync_auto with enable=True starts file watcher."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.start_file_watcher", return_value={"status": "started"}):
            with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=tmp_path):
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("sync_auto", {"enable": True})
    data = json.loads(result)
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_nucleus_sync_sync_auto_disable(tmp_path):
    """sync_auto with enable=False stops file watcher."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.stop_file_watcher", return_value={"status": "stopped"}):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("sync_auto", {"enable": False})
    data = json.loads(result)
    assert data["status"] == "stopped"


@pytest.mark.asyncio
async def test_nucleus_sync_sync_auto_gitignore_patch(tmp_path):
    """sync_auto enable patches .gitignore if not already patched."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    root = tmp_path
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules\n")
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.start_file_watcher", return_value={"status": "started"}):
            with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=tmp_path / ".brain"):
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("sync_auto", {"enable": True})
    data = json.loads(result)
    assert data.get("gitignore_patched") is True
    assert "**/*.meta" in gitignore.read_text()


@pytest.mark.asyncio
async def test_nucleus_sync_sync_resolve_no_conflict(tmp_path):
    """sync_resolve with no conflict returns error."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=brain):
            with mock.patch("mcp_server_nucleus.runtime.sync_ops.sync_lock") as mock_lock:
                mock_lock.return_value.__enter__ = mock.MagicMock()
                mock_lock.return_value.__exit__ = mock.MagicMock(return_value=False)
                with mock.patch("mcp_server_nucleus.runtime.sync_ops.detect_conflict", return_value=None):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("sync_resolve", {"file_path": "test.txt"})
    data = json.loads(result)
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_nucleus_sync_sync_resolve_with_conflict(tmp_path):
    """sync_resolve with conflict resolves it."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=brain):
            with mock.patch("mcp_server_nucleus.runtime.sync_ops.sync_lock") as mock_lock:
                mock_lock.return_value.__enter__ = mock.MagicMock()
                mock_lock.return_value.__exit__ = mock.MagicMock(return_value=False)
                with mock.patch("mcp_server_nucleus.runtime.sync_ops.detect_conflict", return_value={"conflict": True}):
                    with mock.patch("mcp_server_nucleus.runtime.sync_ops.resolve_conflict", return_value="resolved"):
                        with mock.patch("mcp_server_nucleus.runtime.sync_ops.get_current_agent", return_value="a1"):
                            sync_mod.register(mcp, helpers)
                            nucleus_sync = tools["nucleus_sync"]
                            result = await nucleus_sync("sync_resolve", {"file_path": "test.txt"})
    data = json.loads(result)
    assert data["status"] == "resolved"


@pytest.mark.asyncio
async def test_nucleus_sync_sync_resolve_exception(tmp_path):
    """sync_resolve handles exceptions."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("sync_resolve", {"file_path": "test.txt"})
    data = json.loads(result)
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_nucleus_sync_unknown_action(tmp_path):
    """Unknown action returns error from async_dispatch."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        sync_mod.register(mcp, helpers)
        nucleus_sync = tools["nucleus_sync"]
        result = await nucleus_sync("nonexistent_action", {})
    # async_dispatch returns error for unknown actions
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_sync_sync_status(tmp_path):
    """sync_status returns status."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.get_sync_status", return_value={"enabled": True}):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("sync_status", {})
    data = json.loads(result)
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_nucleus_relay_subscribe(tmp_path):
    """nucleus_relay_subscribe delegates to relay_subscribe_notifications_impl."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.relay_notify.relay_subscribe_notifications_impl",
                        new_callable=mock.AsyncMock, return_value={"status": "subscribed"}) as mock_impl:
            sync_mod.register(mcp, helpers)
            nucleus_relay_subscribe = tools["nucleus_relay_subscribe"]
            result = await nucleus_relay_subscribe(ctx=mock.MagicMock(), timeout_seconds=60)
    assert result["status"] == "subscribed"
    mock_impl.assert_called_once()


@pytest.mark.asyncio
async def test_nucleus_ccr_arm(tmp_path):
    """nucleus_ccr_arm resolves canonical inbox and subscribes."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain"), "CC_SESSION_ROLE": "dev"}):
        with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                        return_value="cc_dev"):
            with mock.patch("mcp_server_nucleus.runtime.relay_ops.detect_session_role", return_value="dev"):
                with mock.patch("mcp_server_nucleus.runtime.relay_notify.relay_subscribe_notifications_impl",
                                new_callable=mock.AsyncMock, return_value={"status": "ok"}):
                    sync_mod.register(mcp, helpers)
                    nucleus_ccr_arm = tools["nucleus_ccr_arm"]
                    result = await nucleus_ccr_arm(ctx=mock.MagicMock(), role="dev")
    assert result["canonical_inbox"] == "cc_dev"
    assert result["resolved_role"] == "dev"


@pytest.mark.asyncio
async def test_nucleus_ccr_arm_no_role(tmp_path):
    """nucleus_ccr_arm with no role uses env detection."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                        return_value="cc_default"):
            with mock.patch("mcp_server_nucleus.runtime.relay_ops.detect_session_role", return_value="default"):
                with mock.patch("mcp_server_nucleus.runtime.relay_notify.relay_subscribe_notifications_impl",
                                new_callable=mock.AsyncMock, return_value={"status": "ok"}):
                    sync_mod.register(mcp, helpers)
                    nucleus_ccr_arm = tools["nucleus_ccr_arm"]
                    result = await nucleus_ccr_arm(ctx=mock.MagicMock())
    assert result["canonical_inbox"] == "cc_default"


# ── Additional coverage tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_identify_agent_non_agent_event(tmp_path):
    """identify_agent with events that are not AGENT_REGISTERED (line 70)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    events = [{"type": "OTHER_EVENT", "data": {"session_id": "s1"}, "emitter": ""}]
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "a1", "role": ""}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=events):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value=""):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {"agent_id": "a1", "environment": "test"})
    data = json.loads(result)
    assert data["agent_id"] == "a1"


@pytest.mark.asyncio
async def test_identify_agent_collision_diff_key(tmp_path):
    """identify_agent with collision event but different key (line 76)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    events = [{"type": "AGENT_REGISTERED", "data": {"session_id": "other"}, "emitter": ""}]
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "a1", "role": ""}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=events):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value=""):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {"agent_id": "a1", "environment": "test"})
    data = json.loads(result)
    assert "collision_warning" not in data


@pytest.mark.asyncio
async def test_identify_agent_collision_exception(tmp_path):
    """identify_agent with exception in collision detection (lines 83-85)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "a1", "role": ""}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", side_effect=Exception("fail")):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                return_value=""):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {"agent_id": "a1", "environment": "test"})
    data = json.loads(result)
    assert data["agent_id"] == "a1"


@pytest.mark.asyncio
async def test_identify_agent_canonical_inbox_exception(tmp_path):
    """identify_agent with exception in canonical inbox resolution (lines 115-117)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.set_current_agent",
                        return_value={"agent_id": "a1", "role": "dev"}):
            with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=[]):
                with mock.patch("mcp_server_nucleus.runtime.relay_inbox_canonical.resolve_canonical_inbox_name",
                                side_effect=Exception("fail")):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("identify_agent", {"agent_id": "a1", "environment": "test"})
    data = json.loads(result)
    assert data["agent_id"] == "a1"


@pytest.mark.asyncio
async def test_sync_auto_gitignore_already_patched(tmp_path):
    """sync_auto enable when .gitignore already has **/*.meta (line 149->157)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    root = tmp_path
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules\n# Nucleus MCP Sync Metadata\n**/*.meta\n")
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.start_file_watcher", return_value={"status": "started"}):
            with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=tmp_path / ".brain"):
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("sync_auto", {"enable": True})
    data = json.loads(result)
    assert data.get("gitignore_patched") is not True


@pytest.mark.asyncio
async def test_sync_auto_gitignore_exception(tmp_path):
    """sync_auto enable with exception in gitignore patching (lines 153-154)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    root = tmp_path
    gitignore = root / ".gitignore"
    gitignore.write_text("node_modules\n")
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sync_ops.start_file_watcher", return_value={"status": "started"}):
            with mock.patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=tmp_path / ".brain"):
                with mock.patch("builtins.open", side_effect=Exception("write fail")):
                    sync_mod.register(mcp, helpers)
                    nucleus_sync = tools["nucleus_sync"]
                    result = await nucleus_sync("sync_auto", {"enable": True})
    data = json.loads(result)
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_saturation_baselines(tmp_path):
    """saturation_baselines action."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.saturation_telemetry.compute_baselines",
                        return_value={"baseline": 1.0}):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("saturation_baselines", {})
    data = json.loads(result)
    assert "baseline" in data


@pytest.mark.asyncio
async def test_saturation_check(tmp_path):
    """saturation_check action."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.saturation_telemetry.check_saturation",
                        return_value={"saturated": False}):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("saturation_check", {})
    data = json.loads(result)
    assert "saturated" in data


@pytest.mark.asyncio
async def test_channel_notify(tmp_path):
    """notify action sends to channels."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    mock_router.notify.return_value = {"telegram": True}
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("notify", {"title": "Test", "message": "Hello"})
    data = json.loads(result)
    assert data["channels_reached"] == 1


@pytest.mark.asyncio
async def test_channel_list(tmp_path):
    """list_channels action."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    mock_router.list_channels.return_value = [{"type": "telegram", "configured": True}]
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("list_channels", {})
    data = json.loads(result)
    assert len(data["channels"]) == 1


@pytest.mark.asyncio
async def test_channel_add_telegram(tmp_path):
    """add_channel with telegram type."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            with mock.patch("mcp_server_nucleus.runtime.channels.telegram.TelegramChannel") as mock_ch:
                mock_ch.return_value.is_configured.return_value = True
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("add_channel", {"channel_type": "telegram", "token": "t", "chat_id": "c"})
    data = json.loads(result)
    assert data["added"] == "telegram"


@pytest.mark.asyncio
async def test_channel_add_slack(tmp_path):
    """add_channel with slack type."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            with mock.patch("mcp_server_nucleus.runtime.channels.slack.SlackChannel") as mock_ch:
                mock_ch.return_value.is_configured.return_value = True
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("add_channel", {"channel_type": "slack", "webhook_url": "http://hook"})
    data = json.loads(result)
    assert data["added"] == "slack"


@pytest.mark.asyncio
async def test_channel_add_discord(tmp_path):
    """add_channel with discord type."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            with mock.patch("mcp_server_nucleus.runtime.channels.discord.DiscordChannel") as mock_ch:
                mock_ch.return_value.is_configured.return_value = True
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("add_channel", {"channel_type": "discord", "webhook_url": "http://hook"})
    data = json.loads(result)
    assert data["added"] == "discord"


@pytest.mark.asyncio
async def test_channel_add_whatsapp(tmp_path):
    """add_channel with whatsapp type."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            with mock.patch("mcp_server_nucleus.runtime.channels.whatsapp.WhatsAppChannel") as mock_ch:
                mock_ch.return_value.is_configured.return_value = True
                sync_mod.register(mcp, helpers)
                nucleus_sync = tools["nucleus_sync"]
                result = await nucleus_sync("add_channel", {"channel_type": "whatsapp", "token": "t", "phone_id": "p", "to_number": "n"})
    data = json.loads(result)
    assert data["added"] == "whatsapp"


@pytest.mark.asyncio
async def test_channel_add_unknown(tmp_path):
    """add_channel with unknown type."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("add_channel", {"channel_type": "unknown_type"})
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_channel_test_specific(tmp_path):
    """test_channel with specific channel name."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    mock_ch = mock.MagicMock()
    mock_ch.test.return_value = True
    mock_router.get_channel.return_value = mock_ch
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("test_channel", {"channel_name": "telegram"})
    data = json.loads(result)
    assert data["success"] is True


@pytest.mark.asyncio
async def test_channel_test_not_found(tmp_path):
    """test_channel with channel not found."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    mock_router.get_channel.return_value = None
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("test_channel", {"channel_name": "nonexistent"})
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_channel_test_all(tmp_path):
    """test_channel with no specific name tests all configured channels."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_router = mock.MagicMock()
    mock_router.list_channels.return_value = [{"type": "telegram", "configured": True}]
    mock_ch = mock.MagicMock()
    mock_ch.is_configured.return_value = True
    mock_ch.test.return_value = True
    mock_router.get_channel.return_value = mock_ch
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.channels.get_channel_router", return_value=mock_router):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("test_channel", {})
    data = json.loads(result)
    assert "results" in data


@pytest.mark.asyncio
async def test_relay_inbox_with_safe_int(tmp_path):
    """relay_inbox with non-numeric limit exercises _safe_int (lines 21-24)."""
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.relay_ops.relay_inbox", return_value={"messages": []}):
            sync_mod.register(mcp, helpers)
            nucleus_sync = tools["nucleus_sync"]
            result = await nucleus_sync("relay_inbox", {"limit": "not_a_number"})
    data = json.loads(result)
    assert "messages" in data
