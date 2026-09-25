"""Comprehensive coverage tests for runtime/deployment_ops.py."""
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
    b = tmp_path / ".brain"
    for sub in ["ledger", "config", "artifacts"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


# ─── _get_render_config ────────────────────────────────────────────────────

class TestGetRenderConfig:
    def test_no_state_file(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _get_render_config
        result = _get_render_config()
        assert result == {}

    def test_with_render_config(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _get_render_config
        state = {"render": {"service_id": "srv-123", "url": "https://example.com"}}
        (brain / "ledger" / "state.json").write_text(json.dumps(state))
        result = _get_render_config()
        assert result["service_id"] == "srv-123"

    def test_no_render_key(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _get_render_config
        state = {"other": "value"}
        (brain / "ledger" / "state.json").write_text(json.dumps(state))
        result = _get_render_config()
        assert result == {}

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.deployment_ops import _get_render_config
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _get_render_config()
        assert result == {}


# ─── _save_render_config ───────────────────────────────────────────────────

class TestSaveRenderConfig:
    def test_save_new(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _save_render_config, _get_render_config
        config = {"service_id": "srv-1", "url": "https://example.com"}
        _save_render_config(config)
        result = _get_render_config()
        assert result["service_id"] == "srv-1"

    def test_save_overwrites_existing(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _save_render_config, _get_render_config
        state = {"render": {"old": True}, "other": "keep"}
        (brain / "ledger" / "state.json").write_text(json.dumps(state))
        _save_render_config({"new": True})
        result = _get_render_config()
        assert "new" in result
        assert "old" not in result


# ─── _run_smoke_test ───────────────────────────────────────────────────────

class TestRunSmokeTest:
    def test_blocked_localhost(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://localhost:3000")
        assert result["passed"] is False
        assert "Blocked host" in result["error"]

    def test_blocked_127(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://127.0.0.1:3000")
        assert result["passed"] is False

    def test_blocked_metadata_endpoint(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://169.254.169.254/latest/meta-data")
        assert result["passed"] is False
        assert "Blocked" in result["error"]

    def test_blocked_private_ip_10(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://10.0.0.1/api/health")
        assert result["passed"] is False
        assert "private" in result["error"]

    def test_blocked_private_ip_192(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://192.168.1.1/api/health")
        assert result["passed"] is False

    def test_blocked_private_ip_172(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://172.16.0.1/api/health")
        assert result["passed"] is False

    def test_blocked_loopback_ipv6(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("http://[::1]:3000/api/health")
        assert result["passed"] is False

    def test_no_host_in_url(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        result = _run_smoke_test("not-a-url")
        assert result["passed"] is False
        assert "Invalid URL" in result["error"]

    def test_successful_smoke_test(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "healthy"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is True
        assert result["status"] == "healthy"
        assert "latency_ms" in result

    def test_smoke_test_ok_status(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "ok"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urloon = mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is True
        assert result["status"] == "ok"

    def test_smoke_test_success_status(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "success"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is True

    def test_smoke_test_unhealthy_status(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "unhealthy"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "Health status" in result["reason"]

    def test_smoke_test_non_200(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.read.return_value = json.dumps({}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "HTTP 500" in result["reason"]

    def test_smoke_test_http_error(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        import urllib.error
        error = urllib.error.HTTPError("https://example.com", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "HTTP 404" in result["reason"]

    def test_smoke_test_url_error(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        import urllib.error
        error = urllib.error.URLError("Connection refused")
        error.reason = "Connection refused"
        with patch("urllib.request.urlopen", side_effect=error):
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "URL Error" in result["reason"]

    def test_smoke_test_timeout(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "Timeout" in result["reason"]

    def test_smoke_test_generic_exception(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            result = _run_smoke_test("https://example.com")
        assert result["passed"] is False
        assert "boom" in result["reason"]

    def test_custom_endpoint(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "healthy"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com/", "/custom/health")
        assert result["passed"] is True
        assert "/custom/health" in result["url"]

    def test_url_with_trailing_slash(self):
        from mcp_server_nucleus.runtime.deployment_ops import _run_smoke_test
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "healthy"}).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_smoke_test("https://example.com/")
        assert result["passed"] is True
        assert result["url"] == "https://example.com/api/health"


# ─── _poll_render_once ─────────────────────────────────────────────────────

class TestPollRenderOnce:
    def test_returns_unknown(self):
        from mcp_server_nucleus.runtime.deployment_ops import _poll_render_once
        result = _poll_render_once("srv-123")
        assert result["status"] == "unknown"
        assert result["service_id"] == "srv-123"
        assert "action" in result


# ─── _start_deploy_poll ────────────────────────────────────────────────────

class TestStartDeployPoll:
    def test_start_new_poll(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _start_deploy_poll
        result = _start_deploy_poll("srv-1", "abc123")
        assert result["status"] == "polling_started"
        assert result["service_id"] == "srv-1"
        assert result["commit_sha"] == "abc123"
        # Verify file written
        polls = json.loads((brain / "ledger" / "active_polls.json").read_text())
        assert len(polls["polls"]) == 1
        assert polls["polls"][0]["service_id"] == "srv-1"

    def test_start_replaces_existing(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _start_deploy_poll
        _start_deploy_poll("srv-1", "abc")
        _start_deploy_poll("srv-1", "def")
        polls = json.loads((brain / "ledger" / "active_polls.json").read_text())
        assert len(polls["polls"]) == 1
        assert polls["polls"][0]["commit_sha"] == "def"

    def test_start_no_commit_sha(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _start_deploy_poll
        result = _start_deploy_poll("srv-1")
        assert result["commit_sha"] is None

    def test_start_with_existing_file_other_services(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _start_deploy_poll
        existing = {"polls": [{"poll_id": "p1", "service_id": "srv-2", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(existing))
        _start_deploy_poll("srv-1", "abc")
        polls = json.loads((brain / "ledger" / "active_polls.json").read_text())
        assert len(polls["polls"]) == 2

    def test_start_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.deployment_ops import _start_deploy_poll
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _start_deploy_poll("srv-1")
        assert "error" in result


# ─── _check_deploy_status ──────────────────────────────────────────────────

class TestCheckDeployStatus:
    def test_no_polls_file(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        result = _check_deploy_status("srv-1")
        assert result["status"] == "no_active_poll"

    def test_no_poll_for_service(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        polls = {"polls": [{"service_id": "srv-2", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))
        result = _check_deploy_status("srv-1")
        assert result["status"] == "no_active_poll"

    def test_active_poll_found(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1",
                            "commit_sha": "abc", "started_at": started, "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))
        result = _check_deploy_status("srv-1")
        assert result["status"] == "polling"
        assert result["poll_id"] == "p1"
        assert "elapsed_minutes" in result

    def test_active_poll_no_started_at(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1",
                            "started_at": "", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))
        result = _check_deploy_status("srv-1")
        assert result["elapsed_minutes"] == 0

    def test_active_poll_bad_timestamp(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1",
                            "started_at": "bad-timestamp", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))
        result = _check_deploy_status("srv-1")
        assert result["elapsed_minutes"] == 0

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.deployment_ops import _check_deploy_status
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _check_deploy_status("srv-1")
        assert "error" in result


# ─── _complete_deploy ──────────────────────────────────────────────────────

class TestCompleteDeploy:
    def test_complete_success_with_smoke_pass(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        # Set up active poll
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))

        with patch("mcp_server_nucleus.runtime.deployment_ops._run_smoke_test",
                   return_value={"passed": True, "latency_ms": 50}):
            result = _complete_deploy("srv-1", True, deploy_url="https://example.com")
        assert result["status"] == "deploy_success_verified"
        # Verify poll removed
        polls = json.loads((brain / "ledger" / "active_polls.json").read_text())
        assert len(polls["polls"]) == 0

    def test_complete_success_smoke_failed(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))

        with patch("mcp_server_nucleus.runtime.deployment_ops._run_smoke_test",
                   return_value={"passed": False, "reason": "HTTP 500"}):
            result = _complete_deploy("srv-1", True, deploy_url="https://example.com")
        assert result["status"] == "deploy_success_smoke_failed"

    def test_complete_success_no_smoke_test(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        polls = {"polls": [{"poll_id": "p1", "service_id": "srv-1", "status": "polling"}]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))

        result = _complete_deploy("srv-1", True, deploy_url="https://example.com",
                                  run_smoke_test=False)
        assert result["status"] == "deploy_success"
        assert result["smoke_test"] is None

    def test_complete_success_no_url(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        result = _complete_deploy("srv-1", True, deploy_url=None)
        assert result["status"] == "deploy_success"

    def test_complete_failure(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        result = _complete_deploy("srv-1", False, error="Build failed")
        assert result["status"] == "deploy_failed"
        assert "Build failed" in result["message"]

    def test_complete_no_polls_file(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        result = _complete_deploy("srv-1", False, error="failed")
        assert result["status"] == "deploy_failed"

    def test_complete_removes_from_polls(self, brain):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        polls = {"polls": [
            {"poll_id": "p1", "service_id": "srv-1", "status": "polling"},
            {"poll_id": "p2", "service_id": "srv-2", "status": "polling"},
        ]}
        (brain / "ledger" / "active_polls.json").write_text(json.dumps(polls))
        _complete_deploy("srv-1", False, error="failed")
        polls = json.loads((brain / "ledger" / "active_polls.json").read_text())
        assert len(polls["polls"]) == 1
        assert polls["polls"][0]["service_id"] == "srv-2"

    def test_complete_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.deployment_ops import _complete_deploy
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _complete_deploy("srv-1", False, error="x")
        assert "error" in result
