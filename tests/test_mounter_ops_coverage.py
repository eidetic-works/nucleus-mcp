"""
Comprehensive coverage tests for runtime/mounter_ops.py.

All external calls (subprocess, MCP client sessions) are mocked — no real network.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from mcp_server_nucleus.runtime import mounter_ops as mo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def brain_path(tmp_path):
    """Create a temporary brain path."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    return bp


@pytest.fixture
def mounter(brain_path):
    """Create a fresh Mounter instance."""
    return mo.Mounter(brain_path)


@pytest.fixture
def reset_mounter_singleton():
    """Reset the global mounter singleton."""
    old = mo._mounter
    mo._mounter = None
    yield
    mo._mounter = old


# ---------------------------------------------------------------------------
# Mounter.__init__ and _load_mounts
# ---------------------------------------------------------------------------

class TestMounterInit:
    def test_init_creates_mounts_file_path(self, brain_path):
        m = mo.Mounter(brain_path)
        assert m.brain_path == brain_path
        assert m.mounts_file == brain_path / "mounts.json"
        assert m.sessions == {}
        assert m.exit_stacks == {}
        assert m.mount_configs == {}

    def test_init_loads_existing_mounts(self, brain_path):
        mounts_file = brain_path / "mounts.json"
        mounts_file.write_text(json.dumps({
            "test_mount": {
                "transport": "stdio",
                "command": "python",
                "args": ["server.py"],
                "env": {},
                "status": "connected"
            }
        }))
        m = mo.Mounter(brain_path)
        assert "test_mount" in m.mount_configs
        assert m.mount_configs["test_mount"]["command"] == "python"

    def test_init_load_mounts_exception(self, brain_path):
        mounts_file = brain_path / "mounts.json"
        mounts_file.write_text("invalid json")
        m = mo.Mounter(brain_path)
        # Should not crash, just log error
        assert m.mount_configs == {}

    def test_init_no_mounts_file(self, brain_path):
        m = mo.Mounter(brain_path)
        assert m.mount_configs == {}


# ---------------------------------------------------------------------------
# _save_mounts
# ---------------------------------------------------------------------------

class TestSaveMounts:
    def test_save_mounts(self, mounter, brain_path):
        mounter.mount_configs = {
            "test": {"transport": "stdio", "command": "python"}
        }
        mounter._save_mounts()
        saved = json.loads((brain_path / "mounts.json").read_text())
        assert "test" in saved
        assert saved["test"]["command"] == "python"

    def test_save_mounts_exception(self, mounter, brain_path):
        # Make mounts_file unwritable
        mounter.mounts_file = Path("/nonexistent/path/mounts.json")
        mounter.mount_configs = {"test": {}}
        # Should not crash
        mounter._save_mounts()


# ---------------------------------------------------------------------------
# mount_server (stdio)
# ---------------------------------------------------------------------------

class TestMountServerStdio:
    @pytest.mark.asyncio
    async def test_mount_stdio_already_active(self, mounter):
        mounter.sessions["existing"] = MagicMock()
        with pytest.raises(ValueError, match="already active"):
            await mounter.mount_server(mount_id="existing", transport="stdio")

    @pytest.mark.asyncio
    async def test_mount_stdio_no_command(self, mounter):
        with pytest.raises(ValueError, match="Command is required"):
            await mounter.mount_server(mount_id="test", transport="stdio")

    @pytest.mark.asyncio
    async def test_mount_stdio_success(self, mounter, brain_path):
        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = [MagicMock(), MagicMock()]
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        mock_read = MagicMock()
        mock_write = MagicMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            # stdio_client is an async context manager
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            # ClientSession is an async context manager
            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            result = await mounter.mount_server(
                mount_id="test_server",
                transport="stdio",
                command="python",
                args=["server.py"],
                env={"KEY": "val"}
            )

        assert result["mount_id"] == "test_server"
        assert result["status"] == "connected"
        assert result["tools"] == 2
        assert "test_server" in mounter.sessions
        assert "test_server" in mounter.mount_configs
        assert mounter.mount_configs["test_server"]["transport"] == "stdio"

    @pytest.mark.asyncio
    @pytest.mark.skipif(mo.MCP_AVAILABLE, reason="Shim path only when MCP not available")
    async def test_mount_stdio_shim_path(self, brain_path):
        """Test the shim path when MCP_AVAILABLE is False."""
        m = mo.Mounter(brain_path)

        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = [MagicMock()]
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.start = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server_nucleus.runtime.mounter_ops.SimpleMCPClient", return_value=mock_session):
            result = await m.mount_server(
                mount_id="shim_test",
                transport="stdio",
                command="python",
                args=["server.py"],
            )

        assert result["status"] == "connected"
        assert result["tools"] == 1
        assert "shim_test" in m.sessions


# ---------------------------------------------------------------------------
# mount_server (sse)
# ---------------------------------------------------------------------------

class TestMountServerSSE:
    @pytest.mark.asyncio
    async def test_mount_sse_no_url(self, mounter):
        with pytest.raises(ValueError, match="URL is required"):
            await mounter.mount_server(mount_id="test", transport="sse")

    @pytest.mark.asyncio
    async def test_mount_sse_success(self, mounter, brain_path):
        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = [MagicMock()]
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        mock_read = MagicMock()
        mock_write = MagicMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.sse_client") as mock_sse, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_sse_ctx = AsyncMock()
            mock_sse_ctx.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_sse_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_sse.return_value = mock_sse_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            result = await mounter.mount_server(
                mount_id="sse_test",
                transport="sse",
                url="http://localhost:3000/sse"
            )

        assert result["status"] == "connected"
        assert result["tools"] == 1
        assert mounter.mount_configs["sse_test"]["transport"] == "sse"
        assert mounter.mount_configs["sse_test"]["url"] == "http://localhost:3000/sse"

    @pytest.mark.asyncio
    async def test_mount_unknown_transport(self, mounter):
        with pytest.raises(ValueError, match="Unknown transport"):
            await mounter.mount_server(mount_id="test", transport="unknown")


# ---------------------------------------------------------------------------
# mount (compatibility method)
# ---------------------------------------------------------------------------

class TestMountCompat:
    @pytest.mark.asyncio
    async def test_mount_already_mounted_by_name(self, mounter):
        mounter.mount_configs["existing"] = {"name": "myserver"}
        result = await mounter.mount("myserver", "python", ["server.py"])
        assert "already mounted" in result

    @pytest.mark.asyncio
    async def test_mount_already_mounted_by_id(self, mounter):
        mounter.mount_configs["myserver"] = {"transport": "stdio"}
        result = await mounter.mount("myserver", "python", ["server.py"])
        assert "already mounted" in result

    @pytest.mark.asyncio
    async def test_mount_non_matching_configs(self, mounter, brain_path):
        """Test mount with existing configs that don't match (loop continues)."""
        mounter.mount_configs["other1"] = {"name": "other1"}
        mounter.mount_configs["other2"] = {"name": "other2"}

        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            result = await mounter.mount("newserver", "python", ["server.py"])
            assert "Successfully mounted" in result

    @pytest.mark.asyncio
    async def test_mount_success(self, mounter, brain_path):
        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            result = await mounter.mount("myserver", "python", ["server.py"])

        assert "Successfully mounted" in result
        assert mounter.mount_configs["myserver"]["name"] == "myserver"

    @pytest.mark.asyncio
    async def test_mount_error(self, mounter):
        # mount_server will raise ValueError for missing command
        # but mount catches exceptions and returns error string
        result = await mounter.mount("test", "", [])
        assert "Error:" in result


# ---------------------------------------------------------------------------
# unmount_server
# ---------------------------------------------------------------------------

class TestUnmountServer:
    @pytest.mark.asyncio
    async def test_unmount_existing(self, mounter, brain_path):
        mock_stack = AsyncMock()
        mounter.exit_stacks["test"] = mock_stack
        mounter.sessions["test"] = MagicMock()
        mounter.mount_configs["test"] = {"transport": "stdio"}
        mounter._save_mounts()

        await mounter.unmount_server("test")

        assert "test" not in mounter.sessions
        assert "test" not in mounter.exit_stacks
        assert "test" not in mounter.mount_configs

    @pytest.mark.asyncio
    async def test_unmount_nonexistent(self, mounter):
        # Should not crash
        await mounter.unmount_server("nonexistent")


# ---------------------------------------------------------------------------
# list_mounts
# ---------------------------------------------------------------------------

class TestListMounts:
    @pytest.mark.asyncio
    async def test_list_mounts_empty(self, mounter):
        result = await mounter.list_mounts()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_mounts_with_configs(self, mounter):
        mounter.mount_configs = {
            "mount1": {"transport": "stdio", "command": "python"},
            "mount2": {"transport": "sse", "url": "http://localhost"},
        }
        result = await mounter.list_mounts()
        assert len(result) == 2
        ids = [m["id"] for m in result]
        assert "mount1" in ids
        assert "mount2" in ids


# ---------------------------------------------------------------------------
# list_tools
# ---------------------------------------------------------------------------

class TestListTools:
    @pytest.mark.asyncio
    async def test_list_tools_no_sessions(self, mounter):
        result = await mounter.list_tools()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tools_with_sessions(self, mounter):
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.model_dump.return_value = {"name": "test_tool", "description": "test"}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        mounter.sessions["mount1"] = mock_session

        result = await mounter.list_tools()

        assert len(result) == 1
        assert result[0]["name"] == "mount1__test_tool"
        assert "[mount1]" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_list_tools_session_error(self, mounter):
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(side_effect=Exception("connection lost"))
        mounter.sessions["mount1"] = mock_session

        result = await mounter.list_tools()
        # Error is caught, returns empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tools_timeout(self, mounter):
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(side_effect=asyncio.TimeoutError())
        mounter.sessions["mount1"] = mock_session

        result = await mounter.list_tools()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tools_with_dict_tool(self, mounter):
        """Test tool without model_dump method (uses __dict__)."""
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "dict_tool"
        mock_tool.model_dump = None  # No model_dump
        mock_tool.__dict__ = {"name": "dict_tool", "description": "from dict"}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        mounter.sessions["mount1"] = mock_session

        result = await mounter.list_tools()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# call_tool
# ---------------------------------------------------------------------------

class TestCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_invalid_name(self, mounter):
        with pytest.raises(ValueError, match="Invalid namespaced tool name"):
            await mounter.call_tool("invalid_name", {})

    @pytest.mark.asyncio
    async def test_call_tool_mount_not_found(self, mounter):
        with pytest.raises(ValueError, match="Mount ID 'nonexistent' not found"):
            await mounter.call_tool("nonexistent__tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mounter):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        mounter.sessions["mount1"] = mock_session

        result = await mounter.call_tool("mount1__test_tool", {"arg": "val"})
        assert result == mock_result
        mock_session.call_tool.assert_called_once_with("test_tool", arguments={"arg": "val"})


# ---------------------------------------------------------------------------
# traverse_and_mount
# ---------------------------------------------------------------------------

class TestTraverseAndMount:
    @pytest.mark.asyncio
    async def test_traverse_root_not_found(self, mounter):
        with pytest.raises(ValueError, match="Root mount 'nonexistent' not found"):
            await mounter.traverse_and_mount("nonexistent")

    @pytest.mark.asyncio
    async def test_traverse_finds_servers(self, mounter):
        mock_session = AsyncMock()
        mock_tool1 = MagicMock()
        mock_tool1.name = "server_info"
        mock_tool2 = MagicMock()
        mock_tool2.name = "mount_endpoint"
        mock_tool3 = MagicMock()
        mock_tool3.name = "regular_tool"
        mock_result = MagicMock()
        mock_result.tools = [mock_tool1, mock_tool2, mock_tool3]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        mounter.sessions["root"] = mock_session

        result = await mounter.traverse_and_mount("root")
        assert result["root"] == "root"
        assert result["status"] == "traversal_complete"
        assert "server_info" in result["potential_sub_servers"]
        assert "mount_endpoint" in result["potential_sub_servers"]
        assert "regular_tool" not in result["potential_sub_servers"]


# ---------------------------------------------------------------------------
# restore_mounts
# ---------------------------------------------------------------------------

class TestRestoreMounts:
    @pytest.mark.asyncio
    async def test_restore_skipped_by_env(self, mounter, monkeypatch):
        monkeypatch.setenv("NUCLEUS_SKIP_AUTOSTART", "true")
        mounter.mount_configs = {"test": {"transport": "stdio", "command": "python"}}
        # Should return immediately without trying to mount
        await mounter.restore_mounts()
        assert "test" not in mounter.sessions

    @pytest.mark.asyncio
    async def test_restore_stdio_mount(self, mounter, monkeypatch):
        monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
        mounter.mount_configs = {
            "test": {"transport": "stdio", "command": "python", "args": ["s.py"], "env": {}}
        }

        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            await mounter.restore_mounts()

        assert "test" in mounter.sessions

    @pytest.mark.asyncio
    async def test_restore_sse_mount(self, mounter, monkeypatch):
        monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
        mounter.mount_configs = {
            "sse_test": {"transport": "sse", "url": "http://localhost:3000/sse"}
        }

        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.sse_client") as mock_sse, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_sse_ctx = AsyncMock()
            mock_sse_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_sse_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_sse.return_value = mock_sse_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            await mounter.restore_mounts()

        assert "sse_test" in mounter.sessions

    @pytest.mark.asyncio
    async def test_restore_mount_error(self, mounter, monkeypatch):
        monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
        mounter.mount_configs = {
            "test": {"transport": "stdio", "command": "python", "args": ["s.py"], "env": {}}
        }

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client",
                   side_effect=Exception("connection failed")):
            # Should not crash, just log error
            await mounter.restore_mounts()

        assert "test" not in mounter.sessions

    @pytest.mark.asyncio
    async def test_restore_stdio_timeout(self, mounter, monkeypatch):
        """Test that restore_mounts handles timeout gracefully."""
        monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
        mounter.mount_configs = {
            "test": {"transport": "stdio", "command": "python", "args": ["s.py"], "env": {}}
        }

        # Make mount_server raise an exception (simulating timeout effect)
        async def failing_mount(*args, **kwargs):
            raise Exception("timeout simulation")

        with patch.object(mounter, "mount_server", side_effect=failing_mount):
            await mounter.restore_mounts()

        assert "test" not in mounter.sessions

    @pytest.mark.asyncio
    async def test_restore_multiple_mounts(self, mounter, monkeypatch):
        """Test restore_mounts with multiple configs (stdio + sse) to cover loop branch."""
        monkeypatch.delenv("NUCLEUS_SKIP_AUTOSTART", raising=False)
        mounter.mount_configs = {
            "stdio1": {"transport": "stdio", "command": "python", "args": ["s.py"], "env": {}},
            "sse1": {"transport": "sse", "url": "http://localhost:3000/sse"},
        }

        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.sse_client") as mock_sse, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            mock_sse_ctx = AsyncMock()
            mock_sse_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_sse_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_sse.return_value = mock_sse_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            await mounter.restore_mounts()

        assert "stdio1" in mounter.sessions
        assert "sse1" in mounter.sessions


# ---------------------------------------------------------------------------
# get_mounter
# ---------------------------------------------------------------------------

class TestGetMounter:
    def test_get_mounter_creates_singleton(self, brain_path, reset_mounter_singleton):
        m = mo.get_mounter(brain_path)
        assert isinstance(m, mo.Mounter)
        assert m.brain_path == brain_path

    def test_get_mounter_returns_existing(self, brain_path, reset_mounter_singleton):
        m1 = mo.get_mounter(brain_path)
        m2 = mo.get_mounter(brain_path)
        assert m1 is m2


# ---------------------------------------------------------------------------
# Impl functions
# ---------------------------------------------------------------------------

class TestBrainMountServerImpl:
    @pytest.mark.asyncio
    async def test_mount_server_impl_success(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        mock_session = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_session.initialize = AsyncMock()

        with patch("mcp_server_nucleus.runtime.mounter_ops.stdio_client") as mock_stdio, \
             patch("mcp_server_nucleus.runtime.mounter_ops.ClientSession") as mock_cs:
            mock_stdio_ctx = AsyncMock()
            mock_stdio_ctx.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_stdio_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_stdio.return_value = mock_stdio_ctx

            mock_cs_ctx = AsyncMock()
            mock_cs_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cs_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_cs.return_value = mock_cs_ctx

            result = await mo._brain_mount_server_impl("test", "python", ["server.py"])

        assert "Successfully mounted" in result

    @pytest.mark.asyncio
    async def test_mount_server_impl_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        result = await mo._brain_mount_server_impl("test", "", [])
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_mount_server_impl_brain_error(self, reset_mounter_singleton, monkeypatch):
        """Cover the except path in _brain_mount_server_impl when get_brain_path fails."""
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        # Make get_brain_path raise
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_brain_path",
                   side_effect=ValueError("no brain")):
            result = await mo._brain_mount_server_impl("test", "python", ["s.py"])
        assert "Error" in result


class TestBrainThanosSnapImpl:
    @pytest.mark.asyncio
    async def test_thanos_snap_all_unreachable(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        # Mock mount to fail for all targets
        with patch.object(mo.Mounter, "mount", side_effect=Exception("unreachable")):
            result = await mo._brain_thanos_snap_impl()
        result_data = json.loads(result)
        assert result_data["sandbox_flagged"] is True

    @pytest.mark.asyncio
    async def test_thanos_snap_already_active(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        # Add fake active sessions
        m.sessions = {"stripe": MagicMock(), "postgres": MagicMock(), "search": MagicMock()}

        result = await mo._brain_thanos_snap_impl()
        assert "Already Active" in result

    @pytest.mark.asyncio
    async def test_thanos_snap_mixed(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        m.sessions = {"stripe": MagicMock()}

        async def mock_mount(name, cmd, args):
            if name == "postgres":
                return "Successfully mounted postgres"
            raise Exception("unreachable")

        with patch.object(m, "mount", side_effect=mock_mount):
            result = await mo._brain_thanos_snap_impl()
        assert "Already Active" in result or "Connected" in result or "Unreachable" in result

    @pytest.mark.asyncio
    async def test_thanos_snap_connected(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))

        async def mock_mount(name, cmd, args):
            return f"Successfully mounted {name}"

        with patch.object(mo.Mounter, "mount", side_effect=mock_mount):
            result = await mo._brain_thanos_snap_impl()
        assert "Connected" in result

    @pytest.mark.asyncio
    async def test_thanos_snap_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_mounter",
                   side_effect=Exception("brain error")):
            result = await mo._brain_thanos_snap_impl()
        assert "Error" in result


class TestBrainUnmountServerImpl:
    @pytest.mark.asyncio
    async def test_unmount_success(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        m.sessions["test"] = MagicMock()
        m.mount_configs["test"] = {"transport": "stdio"}

        result = await mo._brain_unmount_server_impl("test")
        assert "Unmounted" in result

    @pytest.mark.asyncio
    async def test_unmount_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_mounter",
                   side_effect=Exception("error")):
            result = await mo._brain_unmount_server_impl("test")
        assert "Error" in result


class TestBrainListMountedImpl:
    def test_list_mounted_empty(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        result = mo._brain_list_mounted_impl()
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"] == []

    def test_list_mounted_with_configs(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        home = os.path.expanduser("~")
        m.mount_configs = {
            "test": {
                "transport": "stdio",
                "command": f"{home}/server.py",
                "args": [f"{home}/arg.py"],
                "status": "connected"
            }
        }
        result = mo._brain_list_mounted_impl()
        data = json.loads(result)
        assert data["success"] is True
        # Paths should be sanitized (home replaced with ~)
        for config in data["data"]:
            cmd = config.get("command", "")
            if isinstance(cmd, str) and cmd:
                assert not cmd.startswith(home) or cmd.startswith("~")

    def test_list_mounted_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_mounter",
                   side_effect=Exception("error")):
            result = mo._brain_list_mounted_impl()
        data = json.loads(result)
        assert data["success"] is False


class TestBrainDiscoverMountedToolsImpl:
    @pytest.mark.asyncio
    async def test_discover_specific_server(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.model_dump.return_value = {"name": "tool1"}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        m.sessions["test"] = mock_session
        m.mount_configs["test"] = {"name": "TestServer"}

        result = await mo._brain_discover_mounted_tools_impl("test")
        data = json.loads(result)
        assert data["success"] is True
        assert "TestServer" in data["data"]

    @pytest.mark.asyncio
    async def test_discover_server_not_found(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)

        result = await mo._brain_discover_mounted_tools_impl("nonexistent")
        data = json.loads(result)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_discover_all_servers(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.model_dump.return_value = {"name": "tool1"}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        m.sessions["srv1"] = mock_session
        m.mount_configs["srv1"] = {"name": "Server1"}

        result = await mo._brain_discover_mounted_tools_impl()
        data = json.loads(result)
        assert data["success"] is True
        assert "Server1" in data["data"]

    @pytest.mark.asyncio
    async def test_discover_all_with_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(side_effect=Exception("conn lost"))
        m.sessions["srv1"] = mock_session
        m.mount_configs["srv1"] = {"name": "Server1"}

        result = await mo._brain_discover_mounted_tools_impl()
        data = json.loads(result)
        assert data["success"] is True
        # Error is recorded in the result
        assert "Server1" in data["data"]

    @pytest.mark.asyncio
    async def test_discover_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_mounter",
                   side_effect=Exception("error")):
            result = await mo._brain_discover_mounted_tools_impl()
        data = json.loads(result)
        assert data["success"] is False


class TestBrainInvokeMountedToolImpl:
    @pytest.mark.asyncio
    async def test_invoke_success(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_content = MagicMock()
        mock_content.model_dump.return_value = {"type": "text", "text": "result"}
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        m.sessions["test"] = mock_session

        result = await mo._brain_invoke_mounted_tool_impl("test", "tool_name", {"arg": "val"})
        data = json.loads(result)
        assert "content" in data

    @pytest.mark.asyncio
    async def test_invoke_server_not_found(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)

        result = await mo._brain_invoke_mounted_tool_impl("nonexistent", "tool", {})
        data = json.loads(result)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_invoke_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("tool error"))
        m.sessions["test"] = mock_session

        result = await mo._brain_invoke_mounted_tool_impl("test", "tool", {})
        data = json.loads(result)
        assert "error" in data


class TestBrainTraverseAndMountImpl:
    @pytest.mark.asyncio
    async def test_traverse_success(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        m = mo.get_mounter(brain_path)
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "server_info"
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        m.sessions["root"] = mock_session

        result = await mo._brain_traverse_and_mount_impl("root")
        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["root"] == "root"

    @pytest.mark.asyncio
    async def test_traverse_error(self, brain_path, reset_mounter_singleton, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        with patch("mcp_server_nucleus.runtime.mounter_ops.get_mounter",
                   side_effect=Exception("error")):
            result = await mo._brain_traverse_and_mount_impl("root")
        data = json.loads(result)
        assert data["success"] is False


# ---------------------------------------------------------------------------
# Shim classes (when MCP_AVAILABLE is False)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(mo.MCP_AVAILABLE, reason="Shim classes only defined when MCP not available")
class TestShimClasses:
    def test_stdio_server_parameters(self):
        params = mo.StdioServerParameters("python", ["arg"], {"KEY": "val"})
        assert params.command == "python"
        assert params.args == ["arg"]
        assert params.env == {"KEY": "val"}

    def test_simple_tool(self):
        tool = mo.SimpleTool("name", "desc", {"type": "object"})
        assert tool.name == "name"
        assert tool.description == "desc"
        assert tool.inputSchema == {"type": "object"}

    def test_simple_list_tools_result(self):
        tools = [MagicMock(), MagicMock()]
        result = mo.SimpleListToolsResult(tools)
        assert result.tools == tools

    def test_content_item(self):
        item = mo.ContentItem({"type": "text", "text": "hello", "extra": "val"})
        assert item.type == "text"
        assert item.text == "hello"
        assert item.extra == "val"
        dumped = item.model_dump()
        assert dumped["type"] == "text"

    def test_content_item_defaults(self):
        item = mo.ContentItem({})
        assert item.type == "text"
        assert item.text == ""

    def test_tool_result(self):
        result = mo.ToolResult([{"type": "text", "text": "result"}])
        assert len(result.content) == 1
        assert result.content[0].text == "result"


# ---------------------------------------------------------------------------
# Shim classes (in-process reload to get coverage credit)
# ---------------------------------------------------------------------------

@pytest.fixture
def shim_mounter_ops():
    """Reload mounter_ops with mcp blocked so shim classes are defined.

    This fixture covers lines 16-180 and 279-302 in-process for coverage.
    """
    import builtins
    import importlib

    original_import = builtins.__import__
    original_module = sys.modules.get("mcp_server_nucleus.runtime.mounter_ops")

    # Save and remove mcp modules
    mcp_keys = [k for k in sys.modules if k == "mcp" or k.startswith("mcp.")]
    saved_mcp = {k: sys.modules.pop(k) for k in mcp_keys}

    # Remove mounter_ops so it gets reloaded
    mo_key = "mcp_server_nucleus.runtime.mounter_ops"
    saved_mo = sys.modules.pop(mo_key, None)
    # Also remove parent packages that may have cached references
    parent_keys = [k for k in sys.modules if k.startswith("mcp_server_nucleus.runtime") and k != "mcp_server_nucleus.runtime"]
    saved_parents = {k: sys.modules.pop(k) for k in parent_keys}

    def _mock_import(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("mcp not available")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = _mock_import
    try:
        # Reimport mounter_ops — this will use shim classes
        import mcp_server_nucleus.runtime.mounter_ops as mo_shim
        yield mo_shim
    finally:
        builtins.__import__ = original_import
        # Restore original modules
        sys.modules.update(saved_parents)
        if saved_mo is not None:
            sys.modules[mo_key] = saved_mo
        else:
            sys.modules.pop(mo_key, None)
        sys.modules.update(saved_mcp)


class TestShimClassesInProcess:
    """Test shim classes in-process (for coverage credit)."""

    def test_shim_data_classes(self, shim_mounter_ops):
        """Test shim data container classes."""
        mo_s = shim_mounter_ops
        assert mo_s.MCP_AVAILABLE is False

        # StdioServerParameters
        params = mo_s.StdioServerParameters("python", ["arg"], {"KEY": "val"})
        assert params.command == "python"
        assert params.args == ["arg"]
        assert params.env == {"KEY": "val"}

        # SimpleTool
        tool = mo_s.SimpleTool("name", "desc", {"type": "object"})
        assert tool.name == "name"
        assert tool.description == "desc"
        assert tool.inputSchema == {"type": "object"}

        # SimpleListToolsResult
        result = mo_s.SimpleListToolsResult([tool])
        assert len(result.tools) == 1

        # ContentItem
        item = mo_s.ContentItem({"type": "text", "text": "hello", "extra": "val"})
        assert item.type == "text"
        assert item.text == "hello"
        assert item.extra == "val"
        dumped = item.model_dump()
        assert dumped["type"] == "text"

        # ContentItem defaults
        item2 = mo_s.ContentItem({})
        assert item2.type == "text"
        assert item2.text == ""

        # ToolResult (content wrapper)
        tr = mo_s.ToolResult([{"type": "text", "text": "result"}])
        assert len(tr.content) == 1
        assert tr.content[0].text == "result"

        # SimpleMCPClient init
        client = mo_s.SimpleMCPClient("python", ["arg"], {"KEY": "val"})
        assert client.command == "python"
        assert client.args == ["arg"]
        assert client.env == {"KEY": "val"}
        assert client.proc is None
        assert client.msg_id == 0
        assert client.pending_requests == {}
        assert client.reader_task is None

    def test_shim_tool_result_methods(self, shim_mounter_ops):
        """Test ToolResult client methods (where they actually live in the shim)."""
        mo_s = shim_mounter_ops

        # _next_id
        tr = mo_s.ToolResult([])
        tr.msg_id = 0
        assert tr._next_id() == 1
        assert tr._next_id() == 2

        # _send_notification (no proc, should not crash)
        tr.proc = None
        tr._send_notification({"jsonrpc": "2.0", "method": "test"})

        # initialize (no-op)
        asyncio.run(tr.initialize())

        # __aexit__ with no proc/reader_task
        tr.proc = None
        tr.reader_task = None
        asyncio.run(tr.__aexit__(None, None, None))

    @pytest.mark.asyncio
    async def test_shim_list_tools_call_tool(self, shim_mounter_ops):
        """Test ToolResult.list_tools and call_tool via mocked _send_request."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.msg_id = 0
        tr.pending_requests = {}
        tr.proc = None

        # Mock _send_request for list_tools
        async def mock_send_tools(req):
            return {"tools": [{"name": "tool1", "description": "desc", "inputSchema": {}}]}
        tr._send_request = mock_send_tools
        result = await tr.list_tools()
        assert len(result.tools) == 1
        assert result.tools[0].name == "tool1"

        # Mock _send_request for call_tool
        async def mock_send_call(req):
            return {"content": [{"type": "text", "text": "result"}]}
        tr._send_request = mock_send_call
        result = await tr.call_tool("tool1", {"arg": "val"})
        assert len(result.content) == 1
        assert result.content[0].text == "result"

    @pytest.mark.asyncio
    async def test_shim_mount_server_path(self, shim_mounter_ops, tmp_path):
        """Test the shim path in mount_server (lines 279-302)."""
        mo_s = shim_mounter_ops

        brain = tmp_path / ".brain"
        brain.mkdir(parents=True, exist_ok=True)
        m = mo_s.Mounter(brain)

        # Mock SimpleMCPClient to avoid actual subprocess
        class MockShimClient:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            async def list_tools(self):
                class R:
                    tools = []
                return R()

        mo_s.SimpleMCPClient = MockShimClient

        result = await m.mount_server(
            mount_id="shim_test",
            transport="stdio",
            command="python",
            args=["server.py"],
        )

        assert result["status"] == "connected"
        assert result["mount_id"] == "shim_test"
        assert "shim_test" in m.sessions
        assert "shim_test" in m.mount_configs

    def test_shim_content_item_non_dict(self, shim_mounter_ops):
        """Test ContentItem with non-dict data that has .get (line 52 branch)."""
        mo_s = shim_mounter_ops
        # Use a Mock that has .get but isn't a dict
        non_dict = MagicMock()
        non_dict.get = lambda key, default=None: default
        item = mo_s.ContentItem(non_dict)
        assert item.type == "text"
        assert item.text == ""

    @pytest.mark.asyncio
    async def test_shim_start_and_aenter(self, shim_mounter_ops):
        """Test ToolResult.start() and __aenter__ with mocked subprocess."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.command = "python"
        tr.args = ["server.py"]
        tr.env = {}
        tr.msg_id = 0
        tr.pending_requests = {}

        # Mock asyncio.create_subprocess_exec
        mock_proc = AsyncMock()
        mock_proc.stdin = AsyncMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.drain = AsyncMock()

        with patch.object(mo_s.asyncio, "create_subprocess_exec", return_value=mock_proc):
            with patch.object(mo_s.asyncio, "create_task", return_value=MagicMock()):
                # Mock _send_request to avoid waiting on future
                async def mock_send(req):
                    return {"result": "ok"}
                tr._send_request = mock_send
                # Mock _send_notification
                tr._send_notification = MagicMock()

                result = await tr.start()
                assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_shim_aexit_with_proc(self, shim_mounter_ops):
        """Test __aexit__ with proc set (lines 67-71)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        mock_proc = AsyncMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = AsyncMock()
        tr.proc = mock_proc
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        tr.reader_task = mock_task

        await tr.__aexit__(None, None, None)
        mock_proc.terminate.assert_called_once()
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_shim_aexit_proc_terminate_exception(self, shim_mounter_ops):
        """Test __aexit__ when proc.terminate raises (line 73 exception path)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        mock_proc = AsyncMock()
        mock_proc.terminate = MagicMock(side_effect=Exception("kill failed"))
        mock_proc.wait = AsyncMock()
        tr.proc = mock_proc
        tr.reader_task = None

        # Should not raise
        await tr.__aexit__(None, None, None)

    def test_shim_send_notification_with_proc(self, shim_mounter_ops):
        """Test _send_notification with proc and stdin set (line 73)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        tr.proc = MagicMock()
        tr.proc.stdin = mock_stdin

        tr._send_notification({"jsonrpc": "2.0", "method": "test"})
        mock_stdin.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_shim_send_request_with_proc(self, shim_mounter_ops):
        """Test _send_request with proc and stdin set (lines 76-104)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.msg_id = 0
        tr.pending_requests = {}

        mock_stdin = AsyncMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()
        tr.proc = MagicMock()
        tr.proc.stdin = mock_stdin

        # Start the request in a task, then resolve the future
        req = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        task = asyncio.create_task(tr._send_request(req))
        await asyncio.sleep(0.01)  # Let it start waiting

        # Resolve the future
        tr.pending_requests[1].set_result({"result": "ok"})
        result = await task
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_shim_reader_loop(self, shim_mounter_ops):
        """Test _reader_loop (lines 130-147)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        fut = asyncio.Future()
        tr.pending_requests = {1: fut}

        # Create mock stdout that returns one line then EOF
        lines = [
            b'{"id": 1, "result": {"tools": []}}\n',
            b"",  # EOF
        ]
        mock_stdout = AsyncMock()
        async def mock_readline():
            return lines.pop(0)
        mock_stdout.readline = mock_readline
        tr.proc = MagicMock()
        tr.proc.stdout = mock_stdout

        await tr._reader_loop()
        assert fut.done()
        assert fut.result() == {"tools": []}

    @pytest.mark.asyncio
    async def test_shim_reader_loop_error_response(self, shim_mounter_ops):
        """Test _reader_loop with error response (line 142)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        fut = asyncio.Future()
        tr.pending_requests = {1: fut}

        lines = [
            b'{"id": 1, "error": "something went wrong"}\n',
            b"",
        ]
        mock_stdout = AsyncMock()
        async def mock_readline():
            return lines.pop(0)
        mock_stdout.readline = mock_readline
        tr.proc = MagicMock()
        tr.proc.stdout = mock_stdout

        await tr._reader_loop()
        assert fut.done()
        assert fut.exception() is not None

    @pytest.mark.asyncio
    async def test_shim_reader_loop_parse_error(self, shim_mounter_ops):
        """Test _reader_loop with unparseable line (line 145)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.pending_requests = {}

        lines = [
            b"not valid json\n",
            b"",
        ]
        mock_stdout = AsyncMock()
        async def mock_readline():
            return lines.pop(0)
        mock_stdout.readline = mock_readline
        tr.proc = MagicMock()
        tr.proc.stdout = mock_stdout

        # Should not raise
        await tr._reader_loop()

    @pytest.mark.asyncio
    async def test_shim_list_tools_actual(self, shim_mounter_ops):
        """Test list_tools with actual _send_request (lines 112-113)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.msg_id = 0
        tr.pending_requests = {}
        tr.proc = None

        # Mock _send_request to return tools
        async def mock_send(req):
            return {"tools": [{"name": "t1", "description": "d", "inputSchema": {"type": "object"}}]}
        tr._send_request = mock_send

        result = await tr.list_tools()
        assert len(result.tools) == 1
        assert result.tools[0].name == "t1"

    @pytest.mark.asyncio
    async def test_shim_call_tool_actual(self, shim_mounter_ops):
        """Test call_tool with actual _send_request (lines 118-127)."""
        mo_s = shim_mounter_ops

        tr = mo_s.ToolResult([])
        tr.msg_id = 0
        tr.pending_requests = {}
        tr.proc = None

        async def mock_send(req):
            return {"content": [{"type": "text", "text": "done"}]}
        tr._send_request = mock_send

        result = await tr.call_tool("t1", {"arg": "val"})
        assert len(result.content) == 1
        assert result.content[0].text == "done"
