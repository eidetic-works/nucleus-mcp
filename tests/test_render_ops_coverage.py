"""Comprehensive tests for mcp_server_nucleus.runtime.render_ops.

Covers RenderOps: __init__, is_available, list_services (API + mock
fallback), _get_mock_services, and get_render_ops.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.render_ops import RenderOps, get_render_ops


class TestInit:
    def test_init_with_api_key(self):
        ops = RenderOps(api_key="test-key")
        assert ops.api_key == "test-key"
        assert ops.base_url == "https://api.render.com/v1"

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "env-key")
        ops = RenderOps()
        assert ops.api_key == "env-key"

    def test_init_no_key(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        assert ops.api_key is None


class TestIsAvailable:
    def test_available_with_key(self):
        ops = RenderOps(api_key="key")
        assert ops.is_available is True

    def test_not_available_without_key(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        assert ops.is_available is False

    def test_not_available_empty_key(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps(api_key="")
        assert ops.is_available is False


class TestListServices:
    def test_no_key_returns_mock(self, monkeypatch):
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        ops = RenderOps()
        result = ops.list_services()
        assert result["mock"] is True
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["error_detail"] is None

    def test_api_success(self):
        ops = RenderOps(api_key="key")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps([
            {"service": {"id": "srv-1", "name": "app"}}
        ]).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_response)
        mock_cm.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.list_services()
        assert isinstance(result, list)
        assert result[0]["service"]["id"] == "srv-1"

    def test_api_non_200_raises_falls_back_to_mock(self):
        ops = RenderOps(api_key="key")
        mock_response = MagicMock()
        mock_response.status = 500
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_response)
        mock_cm.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_cm):
            result = ops.list_services()
        assert result["mock"] is True
        assert result["error_detail"] is not None

    def test_api_exception_falls_back_to_mock(self):
        ops = RenderOps(api_key="key")
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = ops.list_services()
        assert result["mock"] is True
        assert "network error" in str(result["error_detail"])


class TestGetMockServices:
    def test_mock_structure(self):
        ops = RenderOps()
        result = ops._get_mock_services()
        assert result["mock"] is True
        assert "message" in result
        assert "items" in result
        assert len(result["items"]) == 2

    def test_mock_with_error(self):
        ops = RenderOps()
        result = ops._get_mock_services(error="something failed")
        assert result["error_detail"] == "something failed"

    def test_mock_service_fields(self):
        ops = RenderOps()
        result = ops._get_mock_services()
        svc = result["items"][0]["service"]
        assert "id" in svc
        assert "name" in svc
        assert "type" in svc
        assert "repo" in svc
        assert "branch" in svc


class TestGetRenderOps:
    def test_get_render_ops(self, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "factory-key")
        ops = get_render_ops()
        assert isinstance(ops, RenderOps)
        assert ops.api_key == "factory-key"
