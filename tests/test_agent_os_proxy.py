from __future__ import annotations

import json
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.agent_os.proxy import ProxyHandler


@pytest.fixture
def proxy_server():
    """Starts the ProxyHandler HTTPServer on a free local port in a background thread."""
    server = HTTPServer(("127.0.0.1", 0), ProxyHandler)
    port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    t.join()


def test_proxy_chat_completions_endpoint(proxy_server):
    """Test the /v1/chat/completions endpoint with a mock scheduler (no network or real provider calls)."""
    with patch("mcp_server_nucleus.runtime.agent_os.proxy._try_providers") as mock_try:
        mock_try.return_value = ("Test completed successfully by mock provider.", "mock-engine-v1", "mock-provider-x")

        url = f"{proxy_server}/v1/chat/completions"
        payload = {
            "model": "nucleus-auto",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            "max_tokens": 100
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            assert response.status == 200

            # Assert: headers x-nucleus-provider and x-nucleus-engine are present
            headers = response.info()
            assert "x-nucleus-provider" in headers
            assert "x-nucleus-engine" in headers
            assert headers["x-nucleus-provider"] == "mock-provider-x"
            assert headers["x-nucleus-engine"] == "mock-engine-v1"

            # Assert: response has choices[0].message.content
            body = json.loads(response.read().decode("utf-8"))
            assert "choices" in body
            assert len(body["choices"]) > 0
            assert "message" in body["choices"][0]
            assert "content" in body["choices"][0]["message"]
            assert body["choices"][0]["message"]["content"] == "Test completed successfully by mock provider."

            # Verify that our mocked scheduler was called with mapped capability and details
            mock_try.assert_called_once_with(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, world!"}
                ],
                "nucleus-auto",
                100,
                "any"
            )


def test_proxy_health_and_models(proxy_server):
    """Test health and models listing endpoints to ensure server responds properly on HTTP GET."""
    # Health endpoint
    with urllib.request.urlopen(f"{proxy_server}/health") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data == {"status": "ok"}

    # Models endpoint
    with urllib.request.urlopen(f"{proxy_server}/v1/models") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "data" in data
        assert any(model["id"] == "nucleus-auto" for model in data["data"])
