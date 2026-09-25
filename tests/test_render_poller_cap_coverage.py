"""
Coverage tests for runtime/capabilities/render_poller_cap.py
"""
import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
import urllib.error

import pytest

from mcp_server_nucleus.runtime.capabilities import render_poller_cap
from mcp_server_nucleus.runtime.capabilities.render_poller_cap import RenderPolling, ACTIVE_POLLS


@pytest.fixture(autouse=True)
def clear_active_polls():
    """Clear global ACTIVE_POLLS before and after each test."""
    ACTIVE_POLLS.clear()
    yield
    ACTIVE_POLLS.clear()


@pytest.fixture
def poller(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    return RenderPolling()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, poller):
        assert poller.name == "render_poller"

    def test_description(self, poller):
        assert "deployment monitoring" in poller.description.lower()


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_three_tools(self, poller):
        tools = poller.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_start_deploy_poll" in names
        assert "brain_check_deploy" in names
        assert "brain_smoke_test" in names

    def test_start_poll_required(self, poller):
        tools = poller.get_tools()
        tool = [t for t in tools if t["name"] == "brain_start_deploy_poll"][0]
        assert tool["parameters"]["required"] == ["service_id"]

    def test_check_deploy_required(self, poller):
        tools = poller.get_tools()
        tool = [t for t in tools if t["name"] == "brain_check_deploy"][0]
        assert tool["parameters"]["required"] == ["service_id"]

    def test_smoke_test_required(self, poller):
        tools = poller.get_tools()
        tool = [t for t in tools if t["name"] == "brain_smoke_test"][0]
        assert tool["parameters"]["required"] == ["url"]


# ---------------------------------------------------------------------------
# _start_poll
# ---------------------------------------------------------------------------
class TestStartPoll:
    def test_start_poll_no_service_id(self, poller):
        result = poller._start_poll(None)
        assert result["error"] == "service_id required"

    def test_start_poll_empty_service_id(self, poller):
        result = poller._start_poll("")
        assert result["error"] == "service_id required"

    @pytest.mark.asyncio
    async def test_start_poll_success(self, poller):
        result = poller._start_poll("srv-abc", "abc123")
        assert result["success"] is True
        assert "srv-abc" in result["message"]
        assert "srv-abc" in ACTIVE_POLLS
        # Cleanup the task
        ACTIVE_POLLS["srv-abc"]["task"].cancel()
        try:
            await ACTIVE_POLLS["srv-abc"]["task"]
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_poll_default_commit_sha(self, poller):
        poller._start_poll("srv-def")
        assert ACTIVE_POLLS["srv-def"]["commit_sha"] == "latest"
        ACTIVE_POLLS["srv-def"]["task"].cancel()
        try:
            await ACTIVE_POLLS["srv-def"]["task"]
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_poll_cancels_existing(self, poller):
        # Start first poll
        poller._start_poll("srv-cancel", "sha1")
        first_task = ACTIVE_POLLS["srv-cancel"]["task"]
        # Start second poll for same service
        poller._start_poll("srv-cancel", "sha2")
        # Let cancellation propagate
        await asyncio.sleep(0.1)
        # First task should be cancelled or done
        assert first_task.cancelled() or first_task.done()
        # Cleanup
        ACTIVE_POLLS["srv-cancel"]["task"].cancel()
        try:
            await ACTIVE_POLLS["srv-cancel"]["task"]
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# _check_poll
# ---------------------------------------------------------------------------
class TestCheckPoll:
    def test_check_poll_not_found(self, poller):
        result = poller._check_poll("srv-nonexistent")
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_check_poll_active(self, poller):
        poller._start_poll("srv-active", "sha1")
        result = poller._check_poll("srv-active")
        assert result["status"] == "polling"
        assert "uptime_seconds" in result
        assert result["commit_sha"] == "sha1"
        # Cleanup
        ACTIVE_POLLS["srv-active"]["task"].cancel()
        try:
            await ACTIVE_POLLS["srv-active"]["task"]
        except asyncio.CancelledError:
            pass

    def test_check_poll_complete(self, poller):
        # Create a completed task manually
        async def done_task():
            return {"success": True, "url": "https://app.com"}

        loop = asyncio.new_event_loop()
        task = loop.create_task(done_task())
        # Run it to completion
        loop.run_until_complete(task)
        loop.close()

        ACTIVE_POLLS["srv-done"] = {
            "commit_sha": "sha1",
            "start_time": time.time(),
            "status": "polling",
            "task": task,
            "logs": []
        }
        result = poller._check_poll("srv-done")
        assert result["status"] == "complete"
        assert result["result"]["success"] is True

    def test_check_poll_cancelled(self, poller):
        async def cancel_task():
            await asyncio.sleep(100)

        loop = asyncio.new_event_loop()
        task = loop.create_task(cancel_task())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            loop.run_until_complete(task)
        loop.close()

        ACTIVE_POLLS["srv-cancelled"] = {
            "commit_sha": "sha1",
            "start_time": time.time(),
            "status": "polling",
            "task": task,
            "logs": []
        }
        result = poller._check_poll("srv-cancelled")
        assert result["status"] == "cancelled"

    def test_check_poll_error(self, poller):
        async def error_task():
            raise ValueError("Something went wrong")

        loop = asyncio.new_event_loop()
        task = loop.create_task(error_task())
        with pytest.raises(ValueError):
            loop.run_until_complete(task)
        loop.close()

        ACTIVE_POLLS["srv-error"] = {
            "commit_sha": "sha1",
            "start_time": time.time(),
            "status": "polling",
            "task": task,
            "logs": []
        }
        result = poller._check_poll("srv-error")
        assert result["status"] == "error"
        assert "Something went wrong" in result["error"]


# ---------------------------------------------------------------------------
# _fetch_url
# ---------------------------------------------------------------------------
class TestFetchUrl:
    def test_fetch_url_success(self, poller):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=json.dumps([{"deploy": {"status": "live"}}]).encode())

        with patch("urllib.request.urlopen", return_value=mock_response):
            req = MagicMock()
            result = poller._fetch_url(req)
            assert "json" in result
            assert result["json"][0]["deploy"]["status"] == "live"

    def test_fetch_url_non_200(self, poller):
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            req = MagicMock()
            result = poller._fetch_url(req)
            assert "error" in result
            assert "404" in result["error"]

    def test_fetch_url_exception(self, poller):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            req = MagicMock()
            result = poller._fetch_url(req)
            assert "error" in result
            assert "Connection refused" in result["error"]


# ---------------------------------------------------------------------------
# _smoke_test
# ---------------------------------------------------------------------------
class TestSmokeTest:
    def test_smoke_test_success(self, poller):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=json.dumps({"status": "healthy"}).encode())

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = poller._smoke_test("https://app.com", "/api/health")
            assert result["passed"] is True
            assert result["status_code"] == 200
            assert "latency_ms" in result

    def test_smoke_test_http_error(self, poller):
        error = urllib.error.HTTPError(
            "https://app.com/api/health", 500, "Server Error", {}, None
        )
        with patch("urllib.request.urlopen", side_effect=error):
            result = poller._smoke_test("https://app.com")
            assert result["passed"] is False
            assert result["status_code"] == 500

    def test_smoke_test_connection_error(self, poller):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            result = poller._smoke_test("https://app.com")
            assert result["passed"] is False
            assert "Connection refused" in result["error"]

    def test_smoke_test_strips_trailing_slash(self, poller):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=b"not json")

        captured_url = []

        def mock_urlopen(req, **kwargs):
            captured_url.append(req.full_url)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            poller._smoke_test("https://app.com/", "/api/health")
            assert captured_url[0] == "https://app.com/api/health"

    def test_smoke_test_non_200_status(self, poller):
        mock_response = MagicMock()
        mock_response.status = 503
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=b"{}")

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = poller._smoke_test("https://app.com")
            assert result["passed"] is False
            assert result["status_code"] == 503

    def test_smoke_test_default_endpoint(self, poller):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read = MagicMock(return_value=b"{}")

        captured_url = []

        def mock_urlopen(req, **kwargs):
            captured_url.append(req.full_url)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            poller._smoke_test("https://app.com")
            assert captured_url[0] == "https://app.com/api/health"


# ---------------------------------------------------------------------------
# execute_tool dispatch
# ---------------------------------------------------------------------------
class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_dispatch_start_poll(self, poller):
        result = poller.execute_tool("brain_start_deploy_poll", {"service_id": "srv-test2"})
        assert result["success"] is True
        # Cleanup
        ACTIVE_POLLS["srv-test2"]["task"].cancel()
        try:
            await ACTIVE_POLLS["srv-test2"]["task"]
        except asyncio.CancelledError:
            pass

    def test_dispatch_check_deploy(self, poller):
        result = poller.execute_tool("brain_check_deploy", {"service_id": "srv-none"})
        assert result["status"] == "not_found"

    def test_dispatch_smoke_test(self, poller):
        with patch("urllib.request.urlopen", side_effect=Exception("fail")):
            result = poller.execute_tool("brain_smoke_test", {"url": "https://app.com"})
            assert result["passed"] is False

    def test_dispatch_unknown_tool(self, poller):
        result = poller.execute_tool("nonexistent", {})
        assert "not found" in result

    def test_dispatch_exception_handled(self, poller):
        """When _start_poll raises, execute_tool catches it."""
        with patch.object(poller, "_start_poll", side_effect=Exception("Boom")):
            result = poller.execute_tool("brain_start_deploy_poll", {"service_id": "srv-x"})
            assert "Error" in result


# ---------------------------------------------------------------------------
# _poll_loop (simulation mode - no API key)
# ---------------------------------------------------------------------------
class TestPollLoop:
    @pytest.mark.asyncio
    async def test_poll_loop_simulation_test_service(self, poller):
        """srv-test returns simulated success in simulation mode."""
        result = await poller._poll_loop("srv-test", None)
        assert result["success"] is True
        assert result["simulated"] is True

    @pytest.mark.asyncio
    async def test_poll_loop_simulation_no_key_non_test(self, poller):
        """Non-test service without API key raises ValueError."""
        with pytest.raises(ValueError, match="RENDER_API_KEY"):
            await poller._poll_loop("srv-real", None)

    @pytest.mark.asyncio
    async def test_poll_loop_with_api_key_live(self, poller, monkeypatch):
        """Test poll loop with API key and live status."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        # Mock _fetch_url to return live deploy
        def mock_fetch(req):
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc123"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                result = await poller._poll_loop("srv-live", "abc123")
                assert result["success"] is True
                assert "url" in result

    @pytest.mark.asyncio
    async def test_poll_loop_build_failed(self, poller, monkeypatch):
        """Test poll loop with build_failed status."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        def mock_fetch(req):
            return {"json": [{"deploy": {"status": "build_failed", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            result = await poller._poll_loop("srv-fail", None)
            assert result["success"] is False
            assert result["status"] == "build_failed"

    @pytest.mark.asyncio
    async def test_poll_loop_canceled_status(self, poller, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        def mock_fetch(req):
            return {"json": [{"deploy": {"status": "canceled", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            result = await poller._poll_loop("srv-cancel", None)
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_poll_loop_update_failed(self, poller, monkeypatch):
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        def mock_fetch(req):
            return {"json": [{"deploy": {"status": "update_failed", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            result = await poller._poll_loop("srv-ufail", None)
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_poll_loop_commit_mismatch_then_match(self, poller, monkeypatch):
        """When commit doesn't match, poll continues. Then matches and goes live."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        call_count = {"n": 0}

        def mock_fetch(req):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"json": [{"deploy": {"status": "live", "commit": {"id": "wrong"}}}]}
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc123"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await poller._poll_loop("srv-mismatch", "abc123")
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_poll_loop_fetch_error(self, poller, monkeypatch):
        """When _fetch_url returns error, poll continues."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        call_count = {"n": 0}

        def mock_fetch(req):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return {"error": "Network error"}
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await poller._poll_loop("srv-err", None)
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_poll_loop_empty_data(self, poller, monkeypatch):
        """When API returns empty data list, poll continues."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        call_count = {"n": 0}

        def mock_fetch(req):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return {"json": []}
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await poller._poll_loop("srv-empty", None)
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_poll_loop_no_deploy_key(self, poller, monkeypatch):
        """When data item has no 'deploy' key, poll continues."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        call_count = {"n": 0}

        def mock_fetch(req):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return {"json": [{"other": "data"}]}
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await poller._poll_loop("srv-nodeploy", None)
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_poll_loop_exception_in_fetch(self, poller, monkeypatch):
        """When _fetch_url raises exception, poll loop catches it."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key")
        poller._api_key = "test-key"

        call_count = {"n": 0}

        def mock_fetch(req):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                raise Exception("Unexpected error")
            return {"json": [{"deploy": {"status": "live", "commit": {"id": "abc"}}}]}

        with patch.object(poller, "_fetch_url", side_effect=mock_fetch):
            with patch.object(poller, "_smoke_test", return_value={"passed": True}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await poller._poll_loop("srv-exc", None)
                    assert result["success"] is True
