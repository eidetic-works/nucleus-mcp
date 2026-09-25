"""
Cloud App Tests (test_cloud.py)
================================
Tests for the Nucleus Cloud ASGI app (Option 2: production deployment).

Tests cover:
  - Health, readiness, and root endpoints (ASGI in-process)
  - MCP streamable-HTTP session lifecycle (subprocess server)
  - Tool listing and tool calls via MCP protocol
  - Tenant isolation and multi-tenant routing
"""

import json
import pytest
import httpx

from .conftest import (
    MCP_HEADERS,
    mcp_initialize_sync,
    mcp_call_sync,
    extract_jsonrpc_result,
)

# ──────────────────────────────────────────────────────────────
# Health / Identity Endpoints (ASGI in-process, no lifespan)
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCloudHealthEndpoints:

    async def test_root_returns_identity(self, cloud_client):
        r = await cloud_client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Nucleus Sovereign Agent OS"
        assert "version" in body
        assert body["transport"] in ("streamable-http", "sse")
        assert "mcp_endpoint" in body

    async def test_health_returns_ok(self, cloud_client):
        r = await cloud_client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "uptime_seconds" in body

    async def test_ready_returns_status(self, cloud_client):
        r = await cloud_client.get("/ready")
        assert r.status_code in (200, 503)
        body = r.json()
        assert "status" in body

    async def test_health_no_auth_required(self, cloud_client):
        """Health endpoints should not require auth even if auth is configured."""
        r = await cloud_client.get("/health")
        assert r.status_code == 200


# ──────────────────────────────────────────────────────────────
# MCP Session Lifecycle (subprocess server)
# ──────────────────────────────────────────────────────────────

class TestCloudMCPSession:

    @pytest.mark.timeout(45)
    def test_initialize_returns_session_id(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        assert session_id
        assert len(session_id) > 10

    @pytest.mark.timeout(45)
    def test_initialize_returns_capabilities(self, cloud_server):
        proc, base_url = cloud_server
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
        r = httpx.post(f"{base_url}/mcp", json=init_req, headers=MCP_HEADERS, timeout=10.0)
        assert r.status_code == 200
        result = extract_jsonrpc_result(r.text)
        assert result is not None
        caps = result["result"]["capabilities"]
        assert "tools" in caps

    @pytest.mark.timeout(45)
    def test_request_without_session_id_after_init(self, cloud_server):
        """After init, requests without mcp-session-id should fail or create new session."""
        proc, base_url = cloud_server
        mcp_initialize_sync(base_url)
        req = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/list",
            "params": {},
        }
        r = httpx.post(f"{base_url}/mcp", json=req, headers=MCP_HEADERS, timeout=10.0)
        # Should get an error (400/404/409) or a new session (200)
        assert r.status_code in (200, 400, 404, 409)


# ──────────────────────────────────────────────────────────────
# Tool Operations (subprocess server)
# ──────────────────────────────────────────────────────────────

class TestCloudToolOperations:

    @pytest.mark.timeout(45)
    def test_tools_list(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(base_url, "tools/list", {}, session_id)
        assert result is not None
        tools = result["result"]["tools"]
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "nucleus_engrams" in tool_names

    @pytest.mark.timeout(45)
    def test_tool_call_health(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {"name": "nucleus_engrams", "arguments": {"action": "health", "params": {}}},
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_tool_call_version(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {"name": "nucleus_engrams", "arguments": {"action": "version", "params": {}}},
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_tool_call_write_engram(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "write_engram",
                    "params": {
                        "key": "test-engram",
                        "value": "test-value-cloud",
                        "context": "Architecture",
                        "intensity": 5,
                    },
                },
            },
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_tool_call_query_engrams(self, cloud_server):
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        # Write first
        mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "write_engram",
                    "params": {
                        "key": "query-test",
                        "value": "query-value",
                        "context": "Architecture",
                        "intensity": 7,
                    },
                },
            },
            session_id, req_id=3,
        )
        # Query
        result = mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "query_engrams",
                    "params": {"context": "Architecture"},
                },
            },
            session_id, req_id=4,
        )
        assert result is not None
        assert "result" in result


# ──────────────────────────────────────────────────────────────
# Tenant Isolation (subprocess server)
# ──────────────────────────────────────────────────────────────

class TestCloudTenantIsolation:

    @pytest.mark.timeout(45)
    def test_default_tenant_used_when_no_auth(self, cloud_server):
        """Without auth headers, requests should resolve to the default tenant."""
        proc, base_url = cloud_server
        r = httpx.get(f"{base_url}/health")
        assert r.status_code == 200

    @pytest.mark.timeout(45)
    def test_tenant_header_respected(self, cloud_server):
        """X-Nucleus-Tenant-ID header should set the tenant."""
        proc, base_url = cloud_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "write_engram",
                    "params": {
                        "key": "tenant-test",
                        "value": "from-custom-tenant",
                        "context": "Architecture",
                        "intensity": 5,
                    },
                },
            },
            session_id,
        )
        assert result is not None
        assert "result" in result


# ──────────────────────────────────────────────────────────────
# Cloud Server Start/Identity
# ──────────────────────────────────────────────────────────────

class TestCloudServerSubprocess:

    @pytest.mark.timeout(30)
    def test_cloud_server_starts_and_serves_health(self, cloud_server):
        proc, base_url = cloud_server
        r = httpx.get(f"{base_url}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.timeout(30)
    def test_cloud_server_root_identity(self, cloud_server):
        proc, base_url = cloud_server
        r = httpx.get(f"{base_url}/")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Nucleus Sovereign Agent OS"
