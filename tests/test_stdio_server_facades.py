"""
Tests for the stdio_server.py facade rewrite.

Verifies:
- tools/list returns 12 facade tools with correct schema
- tools/call routes to facade dispatchers correctly
- Unknown facades return informative errors
- Backward compatibility with mounter dispatch
- Facade router lazy initialization
"""

import pytest
import json
import asyncio
import os
import sys

from mcp_server_nucleus.runtime.stdio_server import StdioServer


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def server(tmp_path, monkeypatch):
    """Create a StdioServer with a temporary brain path."""
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
    # Create minimal brain structure
    (tmp_path / "ledger").mkdir(parents=True, exist_ok=True)
    (tmp_path / "engrams").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    s = StdioServer()
    return s


# ============================================================
# TEST: tools/list — 12 facade tools
# ============================================================

class TestToolsList:
    @pytest.mark.asyncio
    async def test_tools_list_returns_12_facades(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        })
        tools = resp["result"]["tools"]
        facade_names = [t["name"] for t in tools if t["name"].startswith("nucleus_")]
        assert len(facade_names) == 12

    @pytest.mark.asyncio
    async def test_tools_list_facade_names(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        })
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools if t["name"].startswith("nucleus_")}
        expected = {
            "nucleus_governance", "nucleus_engrams", "nucleus_tasks",
            "nucleus_sessions", "nucleus_sync", "nucleus_features",
            "nucleus_federation", "nucleus_orchestration", "nucleus_telemetry",
            "nucleus_slots", "nucleus_infra", "nucleus_agents",
        }
        assert names == expected

    @pytest.mark.asyncio
    async def test_tools_list_facade_schema(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        })
        tools = resp["result"]["tools"]
        for tool in tools:
            if tool["name"].startswith("nucleus_"):
                schema = tool["inputSchema"]
                assert schema["type"] == "object"
                assert "action" in schema["properties"]
                assert "params" in schema["properties"]
                assert "action" in schema["required"]

    @pytest.mark.asyncio
    async def test_tools_list_no_old_brain_tools(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        })
        tools = resp["result"]["tools"]
        old_names = [t["name"] for t in tools if t["name"].startswith("brain_")]
        assert old_names == [], f"Found stale brain_* tools: {old_names}"


# ============================================================
# TEST: tools/call — facade dispatch
# ============================================================

class TestToolsCallFacadeDispatch:
    @pytest.mark.asyncio
    async def test_governance_status(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "nucleus_governance",
                "arguments": {"action": "status", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        assert "NUCLEUS HYPERVISOR" in content

    @pytest.mark.asyncio
    async def test_engrams_health(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "health", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("status") == "healthy" or "status" in parsed

    @pytest.mark.asyncio
    async def test_tasks_list(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "nucleus_tasks",
                "arguments": {"action": "list", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True

    @pytest.mark.asyncio
    async def test_telemetry_dispatch_metrics(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {
                "name": "nucleus_telemetry",
                "arguments": {"action": "dispatch_metrics", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert "total_dispatches" in parsed

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {
                "name": "nucleus_governance",
                "arguments": {"action": "nonexistent_action", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert "error" in parsed
        assert "available_actions" in parsed

    @pytest.mark.asyncio
    async def test_unavailable_facade_returns_error(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {
                "name": "nucleus_federation",
                "arguments": {"action": "status", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert "error" in parsed
        assert "stdio fallback mode" in parsed["error"]
        assert "available_facades" in parsed

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {
                "name": "brain_old_tool",
                "arguments": {}
            }
        })
        assert "error" in resp
        assert resp["error"]["code"] == -32000
        assert "Unknown tool" in resp["error"]["message"]

    @pytest.mark.asyncio
    async def test_empty_action_returns_available_actions(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {
                "name": "nucleus_tasks",
                "arguments": {"action": "", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert "error" in parsed
        assert "available_actions" in parsed


# ============================================================
# TEST: Facade router caching
# ============================================================

class TestFacadeRouterCaching:
    def test_routers_are_cached(self, server):
        r1 = server._get_facade_routers()
        r2 = server._get_facade_routers()
        assert r1 is r2

    def test_cached_routers_have_expected_facades(self, server):
        routers = server._get_facade_routers()
        assert "nucleus_governance" in routers
        assert "nucleus_engrams" in routers
        assert "nucleus_tasks" in routers
        assert "nucleus_sessions" in routers
        assert "nucleus_telemetry" in routers


# ============================================================
# TEST: initialize and notifications
# ============================================================

class TestPhase3StdioActions:
    """Test Phase 3 actions routed through stdio_server engrams facade."""

    @pytest.mark.asyncio
    async def test_context_graph(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 20, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "context_graph", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True
        assert "nodes" in parsed["data"]
        assert "stats" in parsed["data"]

    @pytest.mark.asyncio
    async def test_render_graph(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 21, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "render_graph", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True
        assert "ascii" in parsed["data"]
        assert "NUCLEUS ENGRAM CONTEXT GRAPH" in parsed["data"]["ascii"]

    @pytest.mark.asyncio
    async def test_billing_summary_tool(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 22, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "billing_summary", "params": {}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True
        assert "total_cost_units" in parsed["data"]

    @pytest.mark.asyncio
    async def test_billing_session_grouping(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 23, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "billing_summary", "params": {"group_by": "session"}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed["data"]["group_by"] == "session"

    @pytest.mark.asyncio
    async def test_engram_neighbors_missing_key(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 24, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "engram_neighbors", "params": {"key": "nonexistent_xyz"}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True
        assert "error" in parsed["data"]

    @pytest.mark.asyncio
    async def test_pulse_and_polish_combo(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 25, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "pulse_and_polish", "params": {"write_engram": False}}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True
        assert "pipeline" in parsed["data"]

    @pytest.mark.asyncio
    async def test_fusion_reactor_combo(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 26, "method": "tools/call",
            "params": {
                "name": "nucleus_engrams",
                "arguments": {"action": "fusion_reactor", "params": {
                    "observation": "test observation for stdio",
                    "write_engrams": False
                }}
            }
        })
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        parsed = json.loads(content)
        assert parsed.get("success") is True


class TestProtocolHandshake:
    @pytest.mark.asyncio
    async def test_initialize(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {}
        })
        assert resp["result"]["serverInfo"]["name"] == "nucleus"
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_initialized_notification(self, server):
        resp = await server.handle_request({
            "jsonrpc": "2.0", "id": None, "method": "notifications/initialized"
        })
        assert resp is None
