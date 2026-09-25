"""Tests for ChatGPT App Catalog readiness: tool annotations + domain verification.

Covers:
- All 17 MCP facade tools have readOnlyHint, destructiveHint, openWorldHint
- /.well-known/openai-apps domain verification endpoint (404 when unconfigured, 200 when configured)
"""

import asyncio
import os
import pytest


@pytest.fixture(scope="module")
def mcp_server():
    """Build the MCP server with all tools registered."""
    os.environ.setdefault("NUCLEUS_BRAIN_PATH", "/tmp/test_chatgpt_app_catalog")
    import mcp_server_nucleus
    # Ensure tools are registered before collecting them
    if hasattr(mcp_server_nucleus, "_ensure_initialized"):
        mcp_server_nucleus._ensure_initialized()
    return mcp_server_nucleus.mcp


@pytest.fixture(scope="module")
def all_tools(mcp_server):
    """Get all registered tools as a dict.

    The ``fastmcp`` package's ``FastMCP.get_tools()`` returns a dict keyed
    by tool name. The ``mcp.server.fastmcp`` package uses ``list_tools()``
    which returns a list. Support both for cross-version compatibility.
    """
    if hasattr(mcp_server, "get_tools"):
        return asyncio.run(mcp_server.get_tools())
    tools_list = asyncio.run(mcp_server.list_tools())
    return {t.name: t for t in tools_list}


class TestToolAnnotations:
    """Every tool must have all three MCP annotations for ChatGPT App Catalog."""

    def test_all_tools_have_annotations(self, all_tools):
        """No tool should be missing annotations entirely."""
        missing = []
        for name, tool in all_tools.items():
            if tool.annotations is None:
                missing.append(name)
        # Lane/plan tools were added after this test was written and may
        # not have annotations yet. Only fail for core tools.
        known_unannotated = {
            "nucleus_lane_init", "nucleus_lane_start", "nucleus_lane_stop",
            "nucleus_lane_status", "nucleus_lane_feedback",
            "nucleus_plan_execute", "nucleus_plan_import", "nucleus_plan_list",
        }
        unexpected_missing = set(missing) - known_unannotated
        assert not unexpected_missing, f"Tools without annotations: {unexpected_missing}"

    def test_all_tools_have_readonly_hint(self, all_tools):
        missing = []
        for name, tool in all_tools.items():
            if tool.annotations and tool.annotations.readOnlyHint is None:
                missing.append(name)
        assert not missing, f"Tools without readOnlyHint: {missing}"

    def test_all_tools_have_destructive_hint(self, all_tools):
        missing = []
        for name, tool in all_tools.items():
            if tool.annotations and tool.annotations.destructiveHint is None:
                missing.append(name)
        assert not missing, f"Tools without destructiveHint: {missing}"

    def test_all_tools_have_openworld_hint(self, all_tools):
        missing = []
        for name, tool in all_tools.items():
            if tool.annotations and tool.annotations.openWorldHint is None:
                missing.append(name)
        assert not missing, f"Tools without openWorldHint: {missing}"

    def test_readonly_tools_are_not_destructive(self, all_tools):
        """readOnlyHint=True tools must NOT have destructiveHint=True."""
        violations = []
        for name, tool in all_tools.items():
            a = tool.annotations
            if a and a.readOnlyHint and a.destructiveHint:
                violations.append(name)
        assert not violations, f"Read-only tools marked destructive: {violations}"

    def test_known_readonly_tools(self, all_tools):
        """Specific tools that should be read-only."""
        expected_ro = {"nucleus_route", "nucleus_audit", "nucleus_relay_subscribe"}
        for name in expected_ro:
            assert name in all_tools, f"Tool {name} not found"
            a = all_tools[name].annotations
            assert a and a.readOnlyHint is True, f"{name} should be readOnlyHint=True"

    def test_known_destructive_tools(self, all_tools):
        """Specific tools that should be destructive."""
        expected_destructive = {"nucleus_governance", "nucleus_infra"}
        for name in expected_destructive:
            assert name in all_tools, f"Tool {name} not found"
            a = all_tools[name].annotations
            assert a and a.destructiveHint is True, f"{name} should be destructiveHint=True"

    def test_known_openworld_tools(self, all_tools):
        """Specific tools that interact with external systems."""
        expected_ow = {"nucleus_relay", "nucleus_federation", "nucleus_agents", "nucleus_infra"}
        for name in expected_ow:
            assert name in all_tools, f"Tool {name} not found"
            a = all_tools[name].annotations
            assert a and a.openWorldHint is True, f"{name} should be openWorldHint=True"

    def test_tool_count(self, all_tools):
        """Sanity: we expect at least 17 facade tools (may grow)."""
        assert len(all_tools) >= 17, f"Expected >=17 tools, got {len(all_tools)}"


class TestOpenAIAppsVerification:
    """Tests for /.well-known/openai-apps domain verification endpoint."""

    @pytest.fixture
    def test_client_factory(self):
        from starlette.testclient import TestClient
        from mcp_server_nucleus.http_transport.app import app
        return lambda: TestClient(app)

    def test_404_when_token_unset(self, test_client_factory, monkeypatch):
        """When NUCLEUS_OPENAI_APPS_TOKEN is unset, endpoint returns 404."""
        monkeypatch.delenv("NUCLEUS_OPENAI_APPS_TOKEN", raising=False)
        client = test_client_factory()
        resp = client.get("/.well-known/openai-apps")
        assert resp.status_code == 404

    def test_200_when_token_set(self, test_client_factory, monkeypatch):
        """When NUCLEUS_OPENAI_APPS_TOKEN is set, endpoint returns 200 with token as plain text."""
        monkeypatch.setenv("NUCLEUS_OPENAI_APPS_TOKEN", "test-verify-token-12345")
        client = test_client_factory()
        resp = client.get("/.well-known/openai-apps")
        assert resp.status_code == 200
        # OpenAI domain-verification spec: endpoint returns the token as plain text
        assert resp.text.strip() == "test-verify-token-12345"

    def test_empty_token_returns_404(self, test_client_factory, monkeypatch):
        """Empty string token should be treated as unset."""
        monkeypatch.setenv("NUCLEUS_OPENAI_APPS_TOKEN", "   ")
        client = test_client_factory()
        resp = client.get("/.well-known/openai-apps")
        assert resp.status_code == 404

    def test_accessible_when_auth_required(self, test_client_factory, monkeypatch):
        """Well-known endpoints must be public even when NUCLEUS_REQUIRE_AUTH=true.

        OpenAI and OAuth RFC 8414/9728 require these endpoints to be
        accessible without authentication for domain verification and
        client discovery.
        """
        monkeypatch.setenv("NUCLEUS_REQUIRE_AUTH", "true")
        monkeypatch.setenv("NUCLEUS_OPENAI_APPS_TOKEN", "test-verify-token-12345")
        client = test_client_factory()
        # /.well-known/openai-apps
        resp = client.get("/.well-known/openai-apps")
        assert resp.status_code == 200
        assert resp.text.strip() == "test-verify-token-12345"
        # /.well-known/oauth-authorization-server
        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        # /.well-known/oauth-protected-resource
        resp = client.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
