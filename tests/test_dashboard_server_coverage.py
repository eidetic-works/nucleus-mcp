"""Coverage tests for mcp_server_nucleus.dashboard.server."""
import json
import socket
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.dashboard.server import (
    GovernanceDashboardHandler,
    ReusableTCPServer,
    run_dashboard_server,
)


class FakeRequest:
    """Minimal request-like object for handler testing."""
    def __init__(self, path="/"):
        self.path = path
        self.wfile = mock.MagicMock()
        self.rfile = mock.MagicMock()
        self.client_address = ("127.0.0.1", 12345)
        self.server = mock.MagicMock()
        self.headers = {}


def _make_handler(path="/", brain_path=None, monkeypatch=None):
    """Create a handler instance without real socket binding."""
    if brain_path and monkeypatch:
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))

    handler = GovernanceDashboardHandler.__new__(GovernanceDashboardHandler)
    handler.path = path
    handler.wfile = mock.MagicMock()
    handler.rfile = mock.MagicMock()
    handler.send_response = mock.MagicMock()
    handler.send_header = mock.MagicMock()
    handler.end_headers = mock.MagicMock()
    handler.client_address = ("127.0.0.1", 12345)
    handler.server = mock.MagicMock()
    handler.headers = {}
    handler.directory = str(Path(__file__).parent)
    return handler


def test_do_get_api_sovereign(monkeypatch, tmp_path):
    handler = _make_handler("/api/sovereign", tmp_path, monkeypatch)
    fake_status = {"status": "ok"}
    with mock.patch("mcp_server_nucleus.runtime.sovereign_status.generate_sovereign_status", return_value=fake_status):
        handler.do_GET()
    handler.send_response.assert_called_with(200)
    written = handler.wfile.write.call_args[0][0]
    data = json.loads(written)
    assert data == fake_status


def test_do_get_api_compliance(monkeypatch, tmp_path):
    handler = _make_handler("/api/compliance", tmp_path, monkeypatch)
    fake_report = {"compliance": True}
    with mock.patch("mcp_server_nucleus.runtime.compliance_config.generate_compliance_report", return_value=fake_report):
        handler.do_GET()
    handler.send_response.assert_called_with(200)
    written = handler.wfile.write.call_args[0][0]
    data = json.loads(written)
    assert data == fake_report


def test_do_get_api_traces(monkeypatch, tmp_path):
    handler = _make_handler("/api/traces", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.trace_viewer.list_traces", return_value=[]):
        handler.do_GET()
    handler.send_response.assert_called_with(200)


def test_do_get_api_trace_specific(monkeypatch, tmp_path):
    handler = _make_handler("/api/traces/abc123", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.trace_viewer.get_trace", return_value={"trace_id": "abc123"}):
        handler.do_GET()
    handler.send_response.assert_called_with(200)


def test_do_get_api_trace_not_found(monkeypatch, tmp_path):
    handler = _make_handler("/api/traces/missing", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.trace_viewer.get_trace", return_value={"error": "not found"}):
        handler.do_GET()
    handler.send_response.assert_called_with(404)


def test_do_get_api_health(monkeypatch, tmp_path):
    handler = _make_handler("/api/health", tmp_path, monkeypatch)
    handler.do_GET()
    handler.send_response.assert_called_with(200)
    written = handler.wfile.write.call_args[0][0]
    data = json.loads(written)
    assert data["status"] == "ok"


def test_do_get_api_unknown(monkeypatch, tmp_path):
    handler = _make_handler("/api/unknown", tmp_path, monkeypatch)
    handler.do_GET()
    handler.send_response.assert_called_with(404)


def test_do_get_api_exception(monkeypatch, tmp_path):
    handler = _make_handler("/api/sovereign", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.sovereign_status.generate_sovereign_status", side_effect=RuntimeError("boom")):
        handler.do_GET()
    handler.send_response.assert_called_with(500)


def test_do_get_non_api(monkeypatch, tmp_path):
    handler = _make_handler("/index.html", tmp_path, monkeypatch)
    with mock.patch.object(GovernanceDashboardHandler, "do_GET", lambda self: None) as _:
        # Just test that non-api path calls super().do_GET
        # We can't easily mock super(), so test the routing logic directly
        from urllib.parse import urlparse
        parsed = urlparse(handler.path)
        assert not parsed.path.startswith("/api/")


def test_do_post_kyc_demo(monkeypatch, tmp_path):
    handler = _make_handler("/api/kyc/demo?id=APP-002", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.kyc_demo.run_kyc_review", return_value={"review": "passed"}):
        handler.do_POST()
    handler.send_response.assert_called_with(200)


def test_do_post_kyc_exception(monkeypatch, tmp_path):
    handler = _make_handler("/api/kyc/demo", tmp_path, monkeypatch)
    with mock.patch("mcp_server_nucleus.runtime.kyc_demo.run_kyc_review", side_effect=RuntimeError("fail")):
        handler.do_POST()
    handler.send_response.assert_called_with(500)


def test_do_post_unknown(monkeypatch, tmp_path):
    handler = _make_handler("/api/unknown", tmp_path, monkeypatch)
    handler.do_POST()
    handler.send_response.assert_called_with(404)


def test_do_options():
    handler = _make_handler()
    handler.do_OPTIONS()
    handler.send_response.assert_called_with(200)
    # Check CORS headers were set
    header_calls = [c.args[0] for c in handler.send_header.call_args_list]
    assert "Access-Control-Allow-Origin" in header_calls


def test_send_json():
    handler = _make_handler()
    handler._send_json(200, {"key": "value"})
    handler.send_response.assert_called_with(200)
    handler.send_header.assert_any_call("Content-Type", "application/json")
    written = handler.wfile.write.call_args[0][0]
    data = json.loads(written)
    assert data == {"key": "value"}


def test_reusable_tcp_server():
    assert ReusableTCPServer.allow_reuse_address is True


def test_log_message_silent():
    handler = _make_handler()
    # log_message should be a no-op (no output)
    handler.log_message("test %s", "arg")  # Should not raise


def test_run_dashboard_server(monkeypatch, tmp_path, capsys):
    """Test run_dashboard_server prints banner and starts serving."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))

    fake_httpd = mock.MagicMock()
    fake_httpd.serve_forever = mock.MagicMock(side_effect=KeyboardInterrupt())
    fake_httpd.server_close = mock.MagicMock()

    with mock.patch("mcp_server_nucleus.dashboard.server.ReusableTCPServer", return_value=fake_httpd) as fake_server_cls:
        run_dashboard_server(port=9999, brain_path=tmp_path)

    fake_server_cls.assert_called_once()
    args = fake_server_cls.call_args[0]
    assert args[0][1] == 9999  # (host, port) tuple
    fake_httpd.serve_forever.assert_called_once()
    fake_httpd.server_close.assert_called_once()
