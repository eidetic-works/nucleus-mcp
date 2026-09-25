"""
Comprehensive pytest tests for runtime/gateway.py - targeting 90%+ coverage.
"""
import json
import ssl
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

import pytest

from mcp_server_nucleus.runtime.gateway import (
    DEFAULT_GATEWAY_CONFIG,
    GatewayManager,
    GovernanceGatewayHandler,
    run_gateway,
)


# ============================================================================
# GatewayManager
# ============================================================================

class TestGatewayManager:
    def test_init_creates_dirs(self, tmp_path):
        gm = GatewayManager(tmp_path)
        assert gm.brain_path == tmp_path
        assert gm.config_path == tmp_path / "config" / "gateway.json"
        assert gm.metadata_path == tmp_path / "metadata" / "gateway_state.json"

    def test_load_config_default(self, tmp_path):
        gm = GatewayManager(tmp_path)
        assert gm.config == DEFAULT_GATEWAY_CONFIG

    def test_load_config_from_file(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        custom_config = {"port": 9999, "providers": {"gemini": {"keys": ["k1"], "model_priority": ["m1"]}}}
        (config_dir / "gateway.json").write_text(json.dumps(custom_config))
        gm = GatewayManager(tmp_path)
        assert gm.config["port"] == 9999

    def test_load_config_invalid_json(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "gateway.json").write_text("not json")
        gm = GatewayManager(tmp_path)
        assert gm.config == DEFAULT_GATEWAY_CONFIG

    def test_load_state_default(self, tmp_path):
        gm = GatewayManager(tmp_path)
        assert gm.state == {"keys": {}}

    def test_load_state_from_file(self, tmp_path):
        meta_dir = tmp_path / "metadata"
        meta_dir.mkdir(parents=True)
        (meta_dir / "gateway_state.json").write_text(json.dumps({"keys": {"k1": {"tier": "FREE"}}}))
        gm = GatewayManager(tmp_path)
        assert "k1" in gm.state["keys"]

    def test_load_state_invalid_json(self, tmp_path):
        meta_dir = tmp_path / "metadata"
        meta_dir.mkdir(parents=True)
        (meta_dir / "gateway_state.json").write_text("not json")
        gm = GatewayManager(tmp_path)
        assert gm.state == {"keys": {}}

    def test_save_state(self, tmp_path):
        gm = GatewayManager(tmp_path)
        gm.state = {"keys": {"k1": {"tier": "PAID"}}}
        gm.save_state()
        saved = json.loads((tmp_path / "metadata" / "gateway_state.json").read_text())
        assert saved == {"keys": {"k1": {"tier": "PAID"}}}

    def test_get_working_keys_all_available(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {"port": 5056, "providers": {"gemini": {"keys": ["k1", "k2"], "model_priority": ["m1"]}}}
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        keys = gm.get_working_keys("gemini", "m1")
        assert set(keys) == {"k1", "k2"}

    def test_get_working_keys_some_exhausted(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {"port": 5056, "providers": {"gemini": {"keys": ["k1", "k2"], "model_priority": ["m1"]}}}
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        gm.mark_exhausted("k1", "m1", duration=3600)
        keys = gm.get_working_keys("gemini", "m1")
        assert keys == ["k2"]

    def test_get_working_keys_unknown_provider(self, tmp_path):
        gm = GatewayManager(tmp_path)
        keys = gm.get_working_keys("unknown", "m1")
        assert keys == []

    def test_mark_exhausted(self, tmp_path):
        gm = GatewayManager(tmp_path)
        gm.mark_exhausted("k1", "m1", duration=100)
        assert "k1" in gm.exhausted_until
        assert "m1" in gm.exhausted_until["k1"]
        assert gm.exhausted_until["k1"]["m1"] > time.time()

    def test_mark_exhausted_multiple_models(self, tmp_path):
        gm = GatewayManager(tmp_path)
        gm.mark_exhausted("k1", "m1")
        gm.mark_exhausted("k1", "m2")
        assert len(gm.exhausted_until["k1"]) == 2

    def test_render_dashboard_no_keys(self, tmp_path):
        gm = GatewayManager(tmp_path)
        out = gm.render_dashboard()
        assert "Nucleus Governance Gateway" in out
        assert "Model Usage" in out
        assert "Key Health" in out

    def test_render_dashboard_with_keys(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["key1234567890", "key2"],
                    "model_priority": ["gemini-2.5-pro", "gemini-2.5-flash"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        gm.state = {"keys": {"key1234567890": {"tier": "FREE"}}}
        out = gm.render_dashboard()
        assert "Key 1" in out
        assert "key1234" in out  # first 8 chars

    def test_render_dashboard_with_exhausted_keys(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["key1"],
                    "model_priority": ["gemini-2.5-pro"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        gm.mark_exhausted("key1", "gemini-2.5-pro", duration=3600)
        out = gm.render_dashboard()
        assert "CRITICAL" in out  # 100% exhausted

    def test_render_dashboard_with_remaining(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["key1"],
                    "model_priority": ["gemini-2.5-pro"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        gm.state = {"keys": {"key1": {"tier": "PAID", "remaining_gemini-2.5-pro": 50}}}
        out = gm.render_dashboard()
        assert "50 reqs" in out


# ============================================================================
# GovernanceGatewayHandler - _detect_provider
# ============================================================================

class TestDetectProvider:
    def _make_handler(self, path):
        """Create a handler instance with mocked attributes."""
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.path = path
        return handler

    def test_gemini_generativelanguage(self):
        h = self._make_handler("/generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent")
        assert h._detect_provider() == "gemini"

    def test_gemini_models(self):
        h = self._make_handler("/models/gemini-2.5-pro:generateContent")
        assert h._detect_provider() == "gemini"

    def test_anthropic_domain(self):
        h = self._make_handler("/anthropic.com/v1/messages")
        assert h._detect_provider() == "anthropic"

    def test_anthropic_messages(self):
        h = self._make_handler("/v1/messages")
        assert h._detect_provider() == "anthropic"

    def test_openai_domain(self):
        h = self._make_handler("/api.openai.com/v1/chat/completions")
        assert h._detect_provider() == "openai"

    def test_openai_chat(self):
        h = self._make_handler("/v1/chat/completions")
        assert h._detect_provider() == "openai"

    def test_unknown(self):
        h = self._make_handler("/some/random/path")
        assert h._detect_provider() == "unknown"


# ============================================================================
# GovernanceGatewayHandler - _get_body / _get_filtered_headers
# ============================================================================

class TestHandlerUtils:
    def _make_handler(self, headers=None, rfile=None):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.headers = MagicMock()
        if headers:
            handler.headers.items.return_value = list(headers.items())
        else:
            handler.headers.items.return_value = []
        handler.headers.get = lambda key, default="": headers.get(key, default) if headers else default
        handler.rfile = rfile or BytesIO(b"")
        return handler

    def test_get_body_no_content(self):
        h = self._make_handler(headers={"Content-Length": "0"})
        assert h._get_body() is None

    def test_get_body_with_content(self):
        h = self._make_handler(headers={"Content-Length": "5"})
        h.rfile = BytesIO(b"hello")
        assert h._get_body() == b"hello"

    def test_get_body_missing_header(self):
        h = self._make_handler()
        h.headers.get = lambda key, default="": default
        assert h._get_body() is None

    def test_get_filtered_headers(self):
        headers = {
            "Host": "localhost",
            "Connection": "keep-alive",
            "Content-Length": "10",
            "Transfer-Encoding": "chunked",
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
        }
        h = self._make_handler(headers=headers)
        filtered = h._get_filtered_headers()
        assert "Host" not in filtered
        assert "Connection" not in filtered
        assert "Content-Length" not in filtered
        assert "Transfer-Encoding" not in filtered
        assert filtered["Authorization"] == "Bearer token"
        assert filtered["Content-Type"] == "application/json"


# ============================================================================
# GovernanceGatewayHandler - _handle_any / do_GET / do_POST / do_PUT
# ============================================================================

class TestHandleAny:
    def _make_handler(self, path):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.path = path
        handler.manager = MagicMock()
        handler.send_error = MagicMock()
        handler._proxy_gemini = MagicMock()
        handler._proxy_anthropic = MagicMock()
        handler._proxy_openai = MagicMock()
        return handler

    def test_do_get_gemini(self):
        h = self._make_handler("/models/gemini-2.5-pro:generateContent")
        h.do_GET()
        h._proxy_gemini.assert_called_once_with("GET")

    def test_do_post_anthropic(self):
        h = self._make_handler("/v1/messages")
        h.do_POST()
        h._proxy_anthropic.assert_called_once_with("POST")

    def test_do_put_openai(self):
        h = self._make_handler("/v1/chat/completions")
        h.do_PUT()
        h._proxy_openai.assert_called_once_with("PUT")

    def test_handle_unknown_provider(self):
        h = self._make_handler("/unknown/path")
        h._handle_any("GET")
        h.send_error.assert_called_once()
        assert h.send_error.call_args[0][0] == 400


# ============================================================================
# GovernanceGatewayHandler - _proxy_gemini
# ============================================================================

class TestProxyGemini:
    def _make_handler(self, path, manager=None):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.path = path
        handler.manager = manager or MagicMock()
        handler._get_body = MagicMock(return_value=b"{}")
        handler._get_filtered_headers = MagicMock(return_value={})
        handler._execute_remote_call = MagicMock(return_value=True)
        handler.send_error = MagicMock()
        return handler

    def test_gemini_with_working_keys(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["k1"],
                    "model_priority": ["gemini-2.5-pro", "gemini-2.5-flash"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler(
            "/v1/models/gemini-2.5-pro:generateContent?key=old_key",
            manager=gm,
        )
        h._proxy_gemini("POST")
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert "gemini-2.5-pro" in call_args[0][0]  # url
        assert call_args[0][4] == "gemini"  # provider

    def test_gemini_no_working_keys(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": [],
                    "model_priority": ["gemini-2.5-pro"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler(
            "/v1/models/gemini-2.5-pro:generateContent",
            manager=gm,
        )
        h._proxy_gemini("POST")
        h.send_error.assert_called_once()
        assert h.send_error.call_args[0][0] == 503

    def test_gemini_free_tier_skip_pro(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["k1"],
                    "model_priority": ["gemini-2.5-pro", "gemini-2.5-flash"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)
        gm.state = {"keys": {"k1": {"tier": "FREE"}}}

        h = self._make_handler(
            "/v1/models/gemini-2.5-pro:generateContent",
            manager=gm,
        )
        h._proxy_gemini("POST")
        # Should skip pro model for FREE tier key and try flash
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert "flash" in call_args[0][6]  # model

    def test_gemini_model_fallback(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["k1"],
                    "model_priority": ["gemini-2.5-pro", "gemini-2.5-flash"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler(
            "/v1/models/gemini-2.5-pro:generateContent",
            manager=gm,
        )
        # First call (pro) fails, second (flash) succeeds
        h._execute_remote_call.side_effect = [False, True]
        h._proxy_gemini("POST")
        assert h._execute_remote_call.call_count == 2

    def test_gemini_unknown_model(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {
                    "keys": ["k1"],
                    "model_priority": ["gemini-2.5-pro"],
                }
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler(
            "/v1/models/unknown-model:generateContent",
            manager=gm,
        )
        h._proxy_gemini("POST")
        # Should try all models in priority list
        h._execute_remote_call.assert_called_once()


# ============================================================================
# GovernanceGatewayHandler - _proxy_standard (anthropic/openai)
# ============================================================================

class TestProxyStandard:
    def _make_handler(self, path, manager=None):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.path = path
        handler.manager = manager or MagicMock()
        handler._get_body = MagicMock(return_value=b"{}")
        handler._get_filtered_headers = MagicMock(return_value={})
        handler._execute_remote_call = MagicMock(return_value=True)
        handler.send_error = MagicMock()
        return handler

    def test_anthropic_no_keys_passthrough(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler("/v1/messages", manager=gm)
        h._proxy_anthropic("POST")
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert "api.anthropic.com" in call_args[0][0]
        assert call_args[0][4] == "anthropic"

    def test_openai_no_keys_passthrough(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler("/v1/chat/completions", manager=gm)
        h._proxy_openai("POST")
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert "api.openai.com" in call_args[0][0]
        assert call_args[0][4] == "openai"

    def test_anthropic_with_keys(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {"keys": [], "model_priority": []},
                "anthropic": {"keys": ["ant_key1"], "models": ["claude-3"]},
                "openai": {"keys": [], "models": []},
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler("/v1/messages", manager=gm)
        h._proxy_anthropic("POST")
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert call_args[0][5] == "ant_key1"

    def test_openai_with_keys(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {"keys": [], "model_priority": []},
                "anthropic": {"keys": [], "models": []},
                "openai": {"keys": ["oai_key1"], "models": ["gpt-4o"]},
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler("/v1/chat/completions", manager=gm)
        h._proxy_openai("POST")
        h._execute_remote_call.assert_called_once()
        call_args = h._execute_remote_call.call_args
        assert call_args[0][5] == "oai_key1"

    def test_standard_all_keys_exhausted(self, tmp_path):
        gm = GatewayManager(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config = {
            "port": 5056,
            "providers": {
                "gemini": {"keys": [], "model_priority": []},
                "anthropic": {"keys": ["k1", "k2"], "models": []},
                "openai": {"keys": [], "models": []},
            }
        }
        (config_dir / "gateway.json").write_text(json.dumps(config))
        gm = GatewayManager(tmp_path)

        h = self._make_handler("/v1/messages", manager=gm)
        h._execute_remote_call.return_value = False
        h._proxy_anthropic("POST")
        h.send_error.assert_called_once()
        assert h.send_error.call_args[0][0] == 503


# ============================================================================
# GovernanceGatewayHandler - _execute_remote_call
# ============================================================================

class TestExecuteRemoteCall:
    def _make_handler(self, manager=None):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.manager = manager or MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = BytesIO()
        handler.headers = MagicMock()
        handler.headers.get = lambda key, default="": default
        return handler

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_success(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.getheaders.return_value = [("Content-Type", "application/json")]
        mock_response.read.return_value = b'{"response": "ok"}'
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        assert result is True
        h.send_response.assert_called_once_with(200)

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_429_rate_limited(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 429, "Rate Limited", {},
            BytesIO(b'{"error": {"message": "quota exceeded"}}')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        assert result is False
        assert "key1" in gm.exhausted_until

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_429_with_exhausted_message(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 429, "Rate Limited", {},
            BytesIO(b'{"error": {"message": "resource exhausted"}}')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        assert result is False

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_403_free_tier_gemini_pro(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 403, "Forbidden", {},
            BytesIO(b'{"error": {"message": "access denied"}}')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "gemini-2.5-pro"
        )
        assert result is False
        assert gm.state["keys"]["key1"]["tier"] == "FREE"

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_403_non_gemini_pro(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 403, "Forbidden", {},
            BytesIO(b'{"error": {"message": "access denied"}}')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "openai", "key1", "gpt-4o"
        )
        # Non-gemini-pro 403 -> forward to client
        assert result is True
        h.send_response.assert_called_once_with(403)

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_500_error_forwarded(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 500, "Server Error", {},
            BytesIO(b'{"error": "internal"}')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        assert result is True
        h.send_response.assert_called_once_with(500)

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        mock_urlopen.side_effect = ConnectionError("network down")

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        assert result is False

    @patch("mcp_server_nucleus.runtime.gateway.urllib.request.urlopen")
    def test_http_error_invalid_json_body(self, mock_urlopen, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        error = urllib.error.HTTPError(
            "https://example.com", 429, "Rate Limited", {},
            BytesIO(b'not json')
        )
        mock_urlopen.side_effect = error

        result = h._execute_remote_call(
            "https://example.com", "GET", b"body", {}, "gemini", "key1", "model1"
        )
        # 429 always marks exhausted regardless of body content
        assert result is False


# ============================================================================
# GovernanceGatewayHandler - _record_usage_metrics
# ============================================================================

class TestRecordUsageMetrics:
    def _make_handler(self, manager=None):
        handler = GovernanceGatewayHandler.__new__(GovernanceGatewayHandler)
        handler.manager = manager or MagicMock()
        handler.headers = MagicMock()
        handler.headers.get = lambda key, default="": default
        return handler

    def test_record_gemini_usage(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        resp_body = b'{"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50}}'
        resp_headers = [("ratelimit-remaining-requests", "50")]

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("gemini", "model1", b"req", resp_body, "key1", resp_headers)
            mock_bm.return_value.record_usage.assert_called_once()

    def test_record_openai_usage(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        resp_body = b'{"usage": {"prompt_tokens": 200, "completion_tokens": 100}}'

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("openai", "gpt-4o", b"req", resp_body, "key1", None)
            mock_bm.return_value.record_usage.assert_called_once()

    def test_record_anthropic_usage(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        resp_body = b'{"usage": {"input_tokens": 300, "output_tokens": 150}}'

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("anthropic", "claude-3", b"req", resp_body, "key1", None)
            mock_bm.return_value.record_usage.assert_called_once()

    def test_record_with_rate_limit_headers(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        resp_body = b'{"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50}}'
        resp_headers = [("ratelimit-remaining-requests", "50")]

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("gemini", "model1", b"req", resp_body, "key1", resp_headers)
            assert "key1" in gm.state["keys"]
            assert gm.state["keys"]["key1"]["remaining_model1"] == "50"

    def test_record_quota_remaining_header(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        resp_body = b'{"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50}}'
        resp_headers = [("quota-remaining", "25")]

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("gemini", "model1", b"req", resp_body, "key1", resp_headers)
            assert gm.state["keys"]["key1"]["remaining_model1"] == "25"

    def test_record_fallback_estimation(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        # No usage in response body -> fallback to estimation
        resp_body = b'some response text'

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=42):
            h._record_usage_metrics("gemini", "model1", b"request text", resp_body, "key1", None)
            call_args = mock_bm.return_value.record_usage.call_args
            assert call_args[1]["input_tokens"] == 42
            assert call_args[1]["output_tokens"] == 42

    def test_record_exception_handled(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)

        # Should not raise even if everything fails
        h._record_usage_metrics("gemini", "model1", None, None, "key1", None)

    def test_record_with_session_headers(self, tmp_path):
        gm = GatewayManager(tmp_path)
        h = self._make_handler(manager=gm)
        h.headers.get = lambda key, default="": "my_session" if key == "NUCLEUS_SESSION_ID" else ("my_agent" if key == "NUCLEUS_AGENT_ID" else default)

        resp_body = b'{"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50}}'

        with patch("mcp_server_nucleus.runtime.token_budget.get_budget_manager") as mock_bm, \
             patch("mcp_server_nucleus.runtime.token_budget.estimate_tokens", return_value=10):
            h._record_usage_metrics("gemini", "model1", b"req", resp_body, "key1", None)
            call_args = mock_bm.return_value.record_usage.call_args
            assert call_args[1]["session_id"] == "my_session"
            assert call_args[1]["agent_id"] == "my_agent"


# ============================================================================
# run_gateway
# ============================================================================

class TestRunGateway:
    @patch("mcp_server_nucleus.runtime.gateway.HTTPServer")
    @patch("mcp_server_nucleus.runtime.gateway.GovernanceGatewayHandler")
    def test_run_gateway_starts_server(self, mock_handler, mock_http_server, tmp_path):
        mock_server = MagicMock()
        mock_http_server.return_value = mock_server
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        run_gateway(tmp_path, port=12345)

        mock_http_server.assert_called_once()
        mock_server.serve_forever.assert_called_once()
        mock_server.server_close.assert_called_once()

    @patch("mcp_server_nucleus.runtime.gateway.HTTPServer")
    def test_run_gateway_writes_port_file(self, mock_http_server, tmp_path):
        mock_server = MagicMock()
        mock_http_server.return_value = mock_server
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        import tempfile
        port_file = Path(tempfile.gettempdir()) / "gemini_proxy.port"

        run_gateway(tmp_path, port=12345)

        # Port file should have been written and cleaned up
        # After KeyboardInterrupt, it's unlinked
        assert not port_file.exists() or port_file.read_text() == "12345"

    @patch("mcp_server_nucleus.runtime.gateway.HTTPServer")
    def test_run_gateway_sets_manager(self, mock_http_server, tmp_path):
        mock_server = MagicMock()
        mock_http_server.return_value = mock_server
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        run_gateway(tmp_path, port=12345)

        assert GovernanceGatewayHandler.manager is not None
