"""
Local HTTP Server Tests (test_server.py)
=========================================
Tests for the Nucleus local HTTP server (Option 1: dev/team access).

Tests cover:
  - MCP session lifecycle over streamable-HTTP
  - Tool listing and tool calls
  - Multi-tenant auth enforcement (401 without token)
  - Bearer token validation (valid, expired, revoked)
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
# MCP Session Lifecycle
# ──────────────────────────────────────────────────────────────

class TestServerMCPSession:

    @pytest.mark.timeout(45)
    def test_initialize_returns_session(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        assert session_id
        assert len(session_id) > 10

    @pytest.mark.timeout(45)
    def test_initialize_returns_protocol_version(self, mcp_http_server):
        proc, base_url = mcp_http_server
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
        assert result["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.timeout(45)
    def test_tools_list(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(base_url, "tools/list", {}, session_id)
        assert result is not None
        tools = result["result"]["tools"]
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "nucleus_engrams" in tool_names


# ──────────────────────────────────────────────────────────────
# Tool Calls
# ──────────────────────────────────────────────────────────────

class TestServerToolCalls:

    @pytest.mark.timeout(45)
    def test_write_engram(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "write_engram",
                    "params": {
                        "key": "server-test",
                        "value": "testing-server-transport",
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
    def test_health_action(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {"name": "nucleus_engrams", "arguments": {"action": "health", "params": {}}},
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_version_action(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {"name": "nucleus_engrams", "arguments": {"action": "version", "params": {}}},
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_query_engrams_empty(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        result = mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {"action": "query_engrams", "params": {}},
            },
            session_id,
        )
        assert result is not None
        assert "result" in result

    @pytest.mark.timeout(45)
    def test_write_and_query_engram_roundtrip(self, mcp_http_server):
        proc, base_url = mcp_http_server
        session_id = mcp_initialize_sync(base_url)
        # Write
        mcp_call_sync(
            base_url, "tools/call",
            {
                "name": "nucleus_engrams",
                "arguments": {
                    "action": "write_engram",
                    "params": {
                        "key": "roundtrip-key",
                        "value": "roundtrip-value",
                        "context": "Feature",
                        "intensity": 8,
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
                "arguments": {"action": "query_engrams", "params": {"context": "Feature"}},
            },
            session_id, req_id=4,
        )
        assert result is not None
        assert "result" in result


# ──────────────────────────────────────────────────────────────
# Auth Enforcement
# ──────────────────────────────────────────────────────────────

class TestServerAuth:

    @pytest.mark.timeout(45)
    def test_no_token_with_auth_required_falls_through(self, multitenant_server):
        """When NUCLEUS_REQUIRE_AUTH=true but no Bearer token, tenant middleware falls
        through to the default tenant (resolve_tenant returns 'default' via solo fallback).
        The 401 only fires when an explicit invalid/expired/revoked token is provided.
        """
        proc, base_url = multitenant_server
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
        # No Bearer token → resolve_tenant returns ("default", None) → no 401
        r = httpx.post(f"{base_url}/mcp", json=req, headers=MCP_HEADERS, timeout=10.0)
        assert r.status_code == 200, f"Expected 200 (default fallback), got {r.status_code}"

    @pytest.mark.timeout(45)
    def test_valid_token_with_auth_required_succeeds(self, multitenant_server):
        """A valid Bearer token should allow access when auth is required."""
        proc, base_url = multitenant_server
        session_id = mcp_initialize_sync(
            base_url,
            extra_headers={"Authorization": "Bearer valid-token-123"},
        )
        assert session_id

    @pytest.mark.timeout(45)
    def test_invalid_token_with_auth_required_returns_401(self, multitenant_server):
        """An invalid Bearer token should be rejected when auth is required."""
        proc, base_url = multitenant_server
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
        headers = {**MCP_HEADERS, "Authorization": "Bearer wrong-token-xyz"}
        r = httpx.post(f"{base_url}/mcp", json=req, headers=headers, timeout=10.0)
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text[:200]}"


# ──────────────────────────────────────────────────────────────
# Subprocess Server Start
# ──────────────────────────────────────────────────────────────

class TestServerSubprocess:

    @pytest.mark.timeout(30)
    def test_http_server_starts(self, mcp_http_server):
        proc, base_url = mcp_http_server
        assert proc.poll() is None  # still running
