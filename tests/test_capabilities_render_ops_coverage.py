"""Tests for mcp_server_nucleus.runtime.capabilities.render_ops.

This is DIFFERENT from runtime/render_ops.py — this is the Capability-based
RenderOps class in the capabilities subpackage. Covers __init__, name,
description, get_tools, and execute_tool (all branches: no key, list
services success, deploy success, HTTP errors, unknown tool, generic
exceptions).
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.capabilities.render_ops import RenderOps


class TestInit:
    """Test RenderOps initialization."""

    def test_init_with_env_key(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "env-key-123")
        ops = RenderOps()
        assert ops.api_key == "env-key-123"
        assert ops.base_url == "https://api.render.com/v1"

    def test_init_no_key(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        assert ops.api_key is None
        assert ops.base_url == "https://api.render.com/v1"


class TestProperties:
    """Test name and description properties."""

    def test_name(self):
        ops = RenderOps()
        assert ops.name == "render_ops"

    def test_description(self):
        ops = RenderOps()
        desc = ops.description
        assert "Render.com" in desc
        assert "Deployments" in desc or "Services" in desc


class TestGetTools:
    """Test get_tools returns proper tool definitions."""

    def test_returns_list(self):
        ops = RenderOps()
        tools = ops.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 2

    def test_list_services_tool(self):
        ops = RenderOps()
        tools = ops.get_tools()
        tool = next(t for t in tools if t["name"] == "render_list_services")
        assert "description" in tool
        assert "parameters" in tool
        assert tool["parameters"]["type"] == "object"

    def test_deploy_service_tool(self):
        ops = RenderOps()
        tools = ops.get_tools()
        tool = next(t for t in tools if t["name"] == "render_deploy_service")
        assert "description" in tool
        assert "service_id" in tool["parameters"]["properties"]
        assert "service_id" in tool["parameters"]["required"]

    def test_tool_names_unique(self):
        ops = RenderOps()
        tools = ops.get_tools()
        names = [t["name"] for t in tools]
        assert len(names) == len(set(names))


class TestExecuteToolNoKey:
    """Test execute_tool when no API key is set."""

    def test_no_key_returns_error(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        result = ops.execute_tool("render_list_services", {})
        assert "RENDER_API_KEY" in result
        assert "not found" in result

    def test_no_key_deploy(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        result = ops.execute_tool("render_deploy_service", {"service_id": "srv-1"})
        assert "RENDER_API_KEY" in result


class TestExecuteListServices:
    """Test execute_tool for render_list_services."""

    def _make_mock_response(self, status, body):
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.read.return_value = json.dumps(body).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_resp)
        mock_cm.__exit__ = MagicMock(return_value=False)
        return mock_cm

    def test_list_services_success(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        data = [
            {"service": {"name": "web-app", "id": "srv-abc"}},
            {"service": {"name": "api-server", "id": "srv-def"}},
        ]
        mock_cm = self._make_mock_response(200, data)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.execute_tool("render_list_services", {})
        assert "Services:" in result
        assert "web-app" in result
        assert "srv-abc" in result
        assert "api-server" in result

    def test_list_services_non_200(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        mock_cm = self._make_mock_response(404, {})
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.execute_tool("render_list_services", {})
        assert "HTTP 404" in result

    def test_list_services_http_error(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        import urllib.error
        error = urllib.error.HTTPError(
            url="https://api.render.com/v1/services",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )
        error.read = MagicMock(return_value=b'{"error": "invalid key"}')
        with patch("urllib.request.urlopen", side_effect=error):
            result = ops.execute_tool("render_list_services", {})
        assert "Render API Error" in result
        assert "401" in result

    def test_list_services_generic_exception(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = ops.execute_tool("render_list_services", {})
        assert "Exception calling Render API" in result
        assert "connection refused" in result


class TestExecuteDeployService:
    """Test execute_tool for render_deploy_service."""

    def _make_mock_response(self, status, body):
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.read.return_value = json.dumps(body).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_resp)
        mock_cm.__exit__ = MagicMock(return_value=False)
        return mock_cm

    def test_deploy_success(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        mock_cm = self._make_mock_response(201, {"id": "dep-xyz"})
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.execute_tool("render_deploy_service", {"service_id": "srv-1"})
        assert "Deployment triggered" in result
        assert "dep-xyz" in result

    def test_deploy_non_201(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        mock_cm = self._make_mock_response(400, {})
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.execute_tool("render_deploy_service", {"service_id": "srv-1"})
        assert "HTTP 400" in result

    def test_deploy_http_error(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        import urllib.error
        error = urllib.error.HTTPError(
            url="https://api.render.com/v1/services/srv-1/deploys",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )
        error.read = MagicMock(return_value=b'forbidden')
        with patch("urllib.request.urlopen", side_effect=error):
            result = ops.execute_tool("render_deploy_service", {"service_id": "srv-1"})
        assert "Render API Error" in result
        assert "403" in result


class TestExecuteUnknownTool:
    """Test execute_tool with an unknown tool name."""

    def test_unknown_tool(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        ops = RenderOps()
        result = ops.execute_tool("nonexistent_tool", {})
        assert "not found" in result
        assert "nonexistent_tool" in result
