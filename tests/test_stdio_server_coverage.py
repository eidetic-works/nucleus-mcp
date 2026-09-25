"""Comprehensive tests for runtime/stdio_server.py — StdioServer, make_response,
handle_request, resource/prompt handling."""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import logging

import pytest


# ── make_response ────────────────────────────────────────────────

class TestMakeResponse:
    def test_success_only(self):
        from mcp_server_nucleus.runtime.stdio_server import make_response
        result = json.loads(make_response(True))
        assert result["success"] is True

    def test_with_data(self):
        from mcp_server_nucleus.runtime.stdio_server import make_response
        result = json.loads(make_response(True, data={"key": "val"}))
        assert result["success"] is True
        assert result["data"] == {"key": "val"}

    def test_with_error(self):
        from mcp_server_nucleus.runtime.stdio_server import make_response
        result = json.loads(make_response(False, error="oops"))
        assert result["success"] is False
        assert result["error"] == "oops"

    def test_with_both(self):
        from mcp_server_nucleus.runtime.stdio_server import make_response
        result = json.loads(make_response(True, data="ok", error="warn"))
        assert result["success"] is True
        assert result["data"] == "ok"
        assert result["error"] == "warn"

    def test_none_values_omitted(self):
        from mcp_server_nucleus.runtime.stdio_server import make_response
        result = json.loads(make_response(True, data=None, error=None))
        assert "data" not in result
        assert "error" not in result


# ── StdioServer.handle_request ───────────────────────────────────

class TestHandleRequest:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_initialize(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize"
        }))
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert "result" in result
        assert result["result"]["protocolVersion"] == "2025-03-26"
        assert result["result"]["serverInfo"]["name"] == "nucleus"

    def test_notifications_initialized(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }))
        assert result is None

    def test_ping(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "ping"
        }))
        assert result["id"] == 2
        assert "result" in result

    def test_unknown_method_with_id(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "nonexistent/method"
        }))
        assert result["error"]["code"] == -32601
        assert "Method not found" in result["error"]["message"]

    def test_unknown_method_notification(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "method": "notifications/custom"
        }))
        assert result is None

    def test_tools_list(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "tools/list"
        }))
        assert "result" in result
        tools = result["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "nucleus_governance" in tool_names
        assert "nucleus_engrams" in tool_names
        assert "nucleus_tasks" in tool_names
        # Each tool should have annotations
        for t in tools:
            assert "annotations" in t
            assert "inputSchema" in t

    def test_resources_list(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "resources/list"
        }))
        resources = result["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "brain://state" in uris
        assert "brain://events" in uris
        assert "brain://context" in uris
        assert "brain://health" in uris

    def test_prompts_list(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 6, "method": "prompts/list"
        }))
        prompts = result["result"]["prompts"]
        names = [p["name"] for p in prompts]
        assert "activate_synthesizer" in names
        assert "cold_start" in names
        assert "start_sprint" in names

    def test_prompts_get_unknown(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 7, "method": "prompts/get",
            "params": {"name": "nonexistent_prompt"}
        }))
        assert "error" in result
        assert result["error"]["code"] == -32602

    def test_tools_call_unknown_tool(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}}
        }))
        assert result["error"]["code"] == -32602
        assert "Unknown tool" in result["error"]["message"]

    def test_tools_call_nucleus_facade(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {"name": "nucleus_nonexistent", "arguments": {"action": "test", "params": {}}}
        }))
        # Should get a response (either error or result)
        assert "result" in result or "error" in result

    def test_resources_read_unknown(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 10, "method": "resources/read",
            "params": {"uri": "brain://unknown"}
        }))
        assert "error" in result
        assert result["error"]["code"] == -32602

    def test_resources_read_state(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 11, "method": "resources/read",
            "params": {"uri": "brain://state"}
        }))
        assert "result" in result
        assert "contents" in result["result"]


# ── StdioServer._get_resources_list ──────────────────────────────

class TestResourcesList:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_all_resources_have_uri(self, server):
        resources = server._get_resources_list()
        assert len(resources) == 8
        for r in resources:
            assert "uri" in r
            assert "name" in r
            assert "description" in r
            assert "mimeType" in r


# ── StdioServer._read_resource ───────────────────────────────────

class TestReadResource:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_read_unknown_uri_raises(self, server):
        with pytest.raises(ValueError, match="Unknown resource URI"):
            server._read_resource("brain://unknown")

    def test_read_health(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://health")
        data = json.loads(result)
        # Should have ground/align/compound keys
        assert "ground" in data or "error" in data

    def test_read_context(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://context")
        assert isinstance(result, str)


# ── StdioServer._get_prompt ──────────────────────────────────────

class TestGetPrompt:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_unknown_prompt_raises(self, server):
        with pytest.raises(ValueError, match="Unknown prompt"):
            server._get_prompt("nonexistent", {})

    def test_cold_start_prompt(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("cold_start", {})
        assert isinstance(result, str)

    def test_start_sprint_prompt(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("start_sprint", {"goal": "test goal"})
        assert isinstance(result, str)

    def test_flywheel_brief_prompt(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("flywheel_brief", {})
        assert isinstance(result, str)

    def test_flywheel_check_prompt(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("flywheel_check", {})
        assert isinstance(result, str)


# ── StdioServer._dispatch_facade ─────────────────────────────────

class TestDispatchFacade:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_dispatch_unknown_facade(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_unknown", "test", {}))
        data = json.loads(result)
        assert "error" in data
        assert "not available" in data["error"]

    def test_dispatch_known_facade(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "list", {}))
        # Should return some JSON response
        assert isinstance(result, str)


# ── StdioServer.run ──────────────────────────────────────────────

class TestServerRun:
    def test_run_eof_breaks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            # Mock stdin to return empty (EOF)
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.return_value = ""
                asyncio.run(server.run())

    def test_run_handles_json_request(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            # Feed a ping request then EOF
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.side_effect = [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
                    "",
                ]
                with patch("builtins.print") as mock_print:
                    asyncio.run(server.run())
                    mock_print.assert_called()

    def test_run_handles_json_decode_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.side_effect = [
                    "not valid json{{{",
                    "",
                ]
                # Should not raise
                asyncio.run(server.run())

    def test_run_handles_blank_line(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.side_effect = [
                    "   \n",
                    "",
                ]
                asyncio.run(server.run())

    def test_run_handles_exception(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.side_effect = [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": None, "arguments": {}}}),
                    "",
                ]
                # Should not raise - exception is caught
                asyncio.run(server.run())


# ── StdioServer.__init__ with components ─────────────────────────

class TestStdioServerInit:
    def test_init_with_watchdog(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_wd = MagicMock()
        mock_wd.start = MagicMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", MagicMock), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", mock_wd), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", MagicMock), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            assert server.watchdog is not None
            server.watchdog.start.assert_called_once()

    def test_init_watchdog_exception(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_wd_instance = MagicMock()
        mock_wd_instance.start.side_effect = Exception("watchdog fail")
        mock_wd_class = MagicMock(return_value=mock_wd_instance)
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", MagicMock), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", mock_wd_class), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", MagicMock), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            # Watchdog was created but start() failed; error was logged
            mock_wd_instance.start.assert_called_once()

    def test_init_with_locker(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_locker = MagicMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", mock_locker), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            assert server.locker is not None

    def test_init_with_injector(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_inj = MagicMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", mock_inj), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            assert server.injector is not None
            mock_inj.assert_called_once_with(str(tmp_path))

    def test_init_with_mounter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_mounter_fn = MagicMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", mock_mounter_fn):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            assert server.mounter is not None
            mock_mounter_fn.assert_called_once()

    def test_run_with_mounter_restore(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_mounter = AsyncMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", MagicMock(return_value=mock_mounter)):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.return_value = ""
                asyncio.run(server.run())
            mock_mounter.restore_mounts.assert_called_once()


# ── tools/call with mounted tools ────────────────────────────────

class TestToolsCallMounted:
    @pytest.fixture
    def server_with_mounter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        mock_mounter = AsyncMock()
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", MagicMock(return_value=mock_mounter)):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_mounted_tool_with_content(self, server_with_mounter):
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.model_dump.return_value = {"type": "text", "text": "result"}
        mock_result.content = [mock_item]
        mock_result.isError = False
        server_with_mounter.mounter.call_tool = AsyncMock(return_value=mock_result)
        result = asyncio.run(server_with_mounter.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "mounted__tool", "arguments": {}}
        }))
        assert result["result"]["content"][0]["text"] == "result"
        assert result["result"]["isError"] is False

    def test_mounted_tool_without_content_attr(self, server_with_mounter):
        mock_result = "plain string result"
        server_with_mounter.mounter.call_tool = AsyncMock(return_value=mock_result)
        result = asyncio.run(server_with_mounter.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "mounted__tool", "arguments": {}}
        }))
        assert "text" in result["result"]["content"][0]

    def test_mounted_tool_item_without_model_dump(self, server_with_mounter):
        mock_result = MagicMock()
        mock_item = MagicMock(spec={})  # No model_dump
        mock_item.__dict__ = {"type": "text", "text": "raw"}
        mock_result.content = [mock_item]
        mock_result.isError = True
        server_with_mounter.mounter.call_tool = AsyncMock(return_value=mock_result)
        result = asyncio.run(server_with_mounter.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "mounted__tool", "arguments": {}}
        }))
        assert result["result"]["isError"] is True

    def test_tools_call_general_exception(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            # Pass a non-string name to trigger a non-ValueError exception
            result = asyncio.run(server.handle_request({
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": 123, "arguments": {}}
            }))
            assert "error" in result
            assert result["error"]["code"] == -32603


# ── resources/read for all URIs ──────────────────────────────────

class TestReadResourceAll:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_read_events(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://events")
        assert isinstance(result, str)

    def test_read_triggers(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://triggers")
        assert isinstance(result, str)

    def test_read_depth(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://depth")
        assert isinstance(result, str)

    def test_read_changes(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://changes")
        assert isinstance(result, str)

    def test_read_traces(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://traces")
        assert isinstance(result, str)

    def test_read_resource_exception(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        # Mock one of the lazy imports to raise a non-ValueError exception
        with patch("mcp_server_nucleus.runtime.common._get_state", side_effect=Exception("state error")):
            result = server._read_resource("brain://state")
            data = json.loads(result)
            assert "error" in data

    def test_read_health_resource(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_health_resource()
        data = json.loads(result)
        assert "ground" in data or "error" in data

    def test_read_health_with_verification_log(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        vlog = tmp_path / "verification_log.jsonl"
        vlog.write_text(json.dumps({"tiers_failed": []}) + "\n" + json.dumps({"tiers_failed": ["t1"]}) + "\n")
        result = server._read_health_resource()
        data = json.loads(result)
        assert "ground" in data

    def test_read_health_with_verdicts(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        vpath = tmp_path / "driver" / "human_verdicts.jsonl"
        vpath.parent.mkdir(parents=True)
        vpath.write_text(json.dumps({"verdict": "accepted"}) + "\n" + json.dumps({"verdict": "corrected"}) + "\n")
        result = server._read_health_resource()
        data = json.loads(result)
        assert "align" in data

    def test_read_health_with_deltas(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        dpath = tmp_path / "deltas" / "deltas.jsonl"
        dpath.parent.mkdir(parents=True)
        dpath.write_text(json.dumps({"delta": 1}) + "\n")
        result = server._read_health_resource()
        data = json.loads(result)
        assert "compound" in data

    def test_read_health_exception(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("brain error")):
            result = server._read_health_resource()
            data = json.loads(result)
            assert "error" in data


# ── Prompts ──────────────────────────────────────────────────────

class TestPrompts:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_get_prompt_activate_synthesizer(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("activate_synthesizer", {})
        assert isinstance(result, str)

    def test_get_prompt_start_sprint_with_goal(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("start_sprint", {"goal": "my goal"})
        assert isinstance(result, str)

    def test_get_prompt_start_sprint_default_goal(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("start_sprint", {})
        assert isinstance(result, str)

    def test_get_prompt_import_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            with patch.dict("sys.modules", {"mcp_server_nucleus.runtime.context_ops": None}):
                result = server._get_prompt("cold_start", {})
                assert isinstance(result, str)

    def test_flywheel_check_prompt_exception(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.flywheel.dashboard.render_dashboard_json", side_effect=Exception("fail")):
            result = server._flywheel_check_prompt()
            assert "Error" in result

    def test_flywheel_brief_prompt_with_file(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        from datetime import datetime, timezone
        week = datetime.now(timezone.utc).isocalendar()[1]
        flywheel_dir = tmp_path / "flywheel"
        flywheel_dir.mkdir(exist_ok=True)
        (flywheel_dir / f"week-{week}.md").write_text("# Weekly Report\n\nContent here.")
        result = server._flywheel_brief_prompt()
        assert "Weekly Report" in result

    def test_flywheel_brief_prompt_no_file(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._flywheel_brief_prompt()
        assert "No activity" in result or "Week" in result

    def test_flywheel_brief_prompt_exception(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("fail")):
            result = server._flywheel_brief_prompt()
            assert "Error" in result


# ── Facade routers ───────────────────────────────────────────────

class TestFacadeRouters:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_get_facade_routers_cached(self, server):
        routers1 = server._get_facade_routers()
        routers2 = server._get_facade_routers()
        assert routers1 is routers2  # Same object (cached)

    def test_facade_routers_has_governance(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_governance" in routers

    def test_facade_routers_has_engrams(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_engrams" in routers

    def test_facade_routers_has_tasks(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_tasks" in routers

    def test_facade_routers_has_sessions(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_sessions" in routers

    def test_facade_routers_has_telemetry(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_telemetry" in routers

    def test_dispatch_facade_governance_status(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_governance", "status", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_health(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "health", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_version(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "version", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_tasks_list(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "list", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_sessions_list(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_sessions", "list", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_telemetry_dispatch_metrics(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_telemetry", "dispatch_metrics", {}))
        assert isinstance(result, str)


# ── main() function ──────────────────────────────────────────────

class TestMain:
    def test_main_help_flag(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            with patch.object(sys, "argv", ["stdio_server", "--help"]):
                from mcp_server_nucleus.runtime.stdio_server import main
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
                captured = capsys.readouterr()
                assert "OPERATIONAL" in captured.out

    def test_main_status_flag(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            with patch.object(sys, "argv", ["stdio_server", "--status"]):
                from mcp_server_nucleus.runtime.stdio_server import main
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
                captured = capsys.readouterr()
                assert "OPERATIONAL" in captured.out

    def test_main_status_import_failure(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            with patch.object(sys, "argv", ["stdio_server", "--status"]):
                from mcp_server_nucleus.runtime.stdio_server import StdioServer, main
                server = StdioServer()
                with patch.object(StdioServer, "handle_request", side_effect=Exception("handle fail")):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                    captured = capsys.readouterr()
                    assert "FAILED" in captured.out


# ── Additional handle_request coverage ───────────────────────────

class TestHandleRequestAdditional:
    @pytest.fixture
    def server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            return StdioServer()

    def test_prompts_get(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "prompts/get",
            "params": {"name": "activate_synthesizer", "arguments": {}}
        }))
        assert result["jsonrpc"] == "2.0"
        assert "messages" in result["result"]

    def test_prompts_get_exception(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "prompts/get",
            "params": {"name": "nonexistent_prompt", "arguments": {}}
        }))
        assert "error" in result

    def test_notifications_initialized(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": None, "method": "notifications/initialized"
        }))
        assert result is None

    def test_notifications_cancelled(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": None, "method": "notifications/cancelled"
        }))
        assert result is None

    def test_unknown_method_with_id(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "unknown/method"
        }))
        assert result["error"]["code"] == -32601

    def test_unknown_method_without_id(self, server):
        result = asyncio.run(server.handle_request({
            "jsonrpc": "2.0", "id": None, "method": "unknown/method"
        }))
        assert result is None

    def test_tools_list_with_mounter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        mock_mounter = AsyncMock()
        mock_mounter.list_tools = AsyncMock(return_value=[{"name": "ext__tool1"}])
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", MagicMock(return_value=mock_mounter)):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            result = asyncio.run(server.handle_request({
                "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
            }))
            tool_names = [t["name"] for t in result["result"]["tools"]]
            assert "ext__tool1" in tool_names

    def test_tools_list_mounter_exception(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        mock_mounter = AsyncMock()
        mock_mounter.list_tools = AsyncMock(side_effect=Exception("mounter fail"))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", MagicMock(return_value=mock_mounter)):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            result = asyncio.run(server.handle_request({
                "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
            }))
            # Should still return tools even if mounter fails
            assert "tools" in result["result"]

    def test_dispatch_facade_unknown(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_unknown", "action", {}))
        data = json.loads(result)
        assert "error" in data
        assert "not available" in data["error"]

    def test_dispatch_facade_governance_unknown_action(self, server):
        result = asyncio.run(server._dispatch_facade("nucleus_governance", "nonexistent_action", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_write_engram(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "write_engram", {
            "key": "test_key", "value": "test_value"
        }))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_query_engrams(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "query_engrams", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_search_engrams(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "search_engrams", {"query": "test"}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_audit_log(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "audit_log", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_governance_status(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "governance_status", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_tasks_get_next(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "get_next", {"skills": []}))
        assert isinstance(result, str)

    def test_dispatch_facade_tasks_add(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "add", {"description": "test task"}))
        assert isinstance(result, str)

    def test_dispatch_facade_tasks_claim(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "claim", {"task_id": "nonexistent", "agent_id": "test"}))
        assert isinstance(result, str)

    def test_dispatch_facade_tasks_update(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_tasks", "update", {"task_id": "nonexistent", "updates": {}}))
        assert isinstance(result, str)

    def test_dispatch_facade_sessions_save(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_sessions", "save", {"context": "test context"}))
        assert isinstance(result, str)

    def test_dispatch_facade_sessions_resume(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_sessions", "resume", {}))
        assert isinstance(result, str)

    def test_read_resource_context(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://context")
        assert isinstance(result, str)

    def test_read_resource_unknown(self, server):
        with pytest.raises(ValueError, match="Unknown resource URI"):
            server._read_resource("brain://unknown")

    def test_read_resource_state(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://state")
        assert isinstance(result, str)

    def test_read_resource_events(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://events")
        assert isinstance(result, str)

    def test_read_resource_triggers(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://triggers")
        assert isinstance(result, str)

    def test_read_resource_depth(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://depth")
        assert isinstance(result, str)

    def test_read_resource_changes(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://changes")
        assert isinstance(result, str)

    def test_read_resource_traces(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://traces")
        assert isinstance(result, str)

    def test_read_resource_health(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._read_resource("brain://health")
        assert isinstance(result, str)

    def test_flywheel_check_with_recent_claims(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        mock_snapshot = {
            "csr": {"ratio": 0.8, "claims_survived": 8, "claims_total": 10},
            "tickets": {"open": 3},
            "curriculum": {"pending": 2, "ready": 5},
            "recent_claims": [
                {"survived": True, "step": "build", "at": "2024-01-01T12:00:00"},
                {"survived": False, "step": "test", "at": "2024-01-01T13:00:00"},
            ],
        }
        with patch("mcp_server_nucleus.flywheel.dashboard.render_dashboard_json", return_value=mock_snapshot):
            result = server._flywheel_check_prompt()
            assert "FLYWHEEL" in result
            assert "OK" in result
            assert "FAIL" in result

    def test_get_prompt_cold_start(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("cold_start", {})
        assert isinstance(result, str)

    def test_get_prompt_flywheel_check(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("flywheel_check", {})
        assert isinstance(result, str)

    def test_get_prompt_flywheel_brief(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = server._get_prompt("flywheel_brief", {})
        assert isinstance(result, str)

    def test_get_prompt_unknown(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        with pytest.raises(ValueError, match="Unknown prompt"):
            server._get_prompt("nonexistent", {})

    def test_dispatch_facade_engrams_morning_brief(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "morning_brief", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_context_graph(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "context_graph", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_engram_neighbors(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "engram_neighbors", {"key": "test"}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_render_graph(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "render_graph", {}))
        assert isinstance(result, str)

    def test_dispatch_facade_engrams_billing_summary(self, server, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        result = asyncio.run(server._dispatch_facade("nucleus_engrams", "billing_summary", {}))
        assert isinstance(result, str)

    def test_run_loop_general_exception(self, tmp_path, monkeypatch):
        """Test that a general exception in the run loop is caught."""
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        with patch("mcp_server_nucleus.runtime.stdio_server.Locker", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Watchdog", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.Injector", None), \
             patch("mcp_server_nucleus.runtime.stdio_server.get_mounter", None):
            from mcp_server_nucleus.runtime.stdio_server import StdioServer
            server = StdioServer()
            call_count = [0]
            def mock_readline():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise OSError("stdin closed")
                return ""
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.side_effect = mock_readline
                # Should not raise - exception is caught in the outer try/except
                asyncio.run(server.run())
