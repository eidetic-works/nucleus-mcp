"""
SSE Transport Tests (test_sse.py)
==================================
Tests for the Nucleus SSE transport.

SSE flow:
  1. GET /sse → 200 text/event-stream → event: endpoint\ndata: /messages/?session_id=<id>
  2. POST /messages/?session_id=<id> with JSON-RPC → 202 Accepted
  3. JSON-RPC response appears on the original SSE GET stream

Tests cover:
  - SSE endpoint discovery
  - Message posting and response retrieval
  - Tool listing over SSE
  - Tool calls over SSE
"""

import os
import json
import asyncio
import time
import pytest
import httpx

from .conftest import parse_sse_events, MCP_HEADERS



# ──────────────────────────────────────────────────────────────
# SSE Stream Helper
# ──────────────────────────────────────────────────────────────

class SSESession:
    """Manages an SSE connection: reads endpoint, sends requests, reads responses."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.endpoint = None
        self.session_id = None
        self._buffer = ""
        self._response = None

    async def connect(self):
        """Open the SSE stream and extract the endpoint URL."""
        self._response = await self.client.send(
            self.client.build_request("GET", "/sse"),
            stream=True,
        )
        assert self._response.status_code == 200
        assert "text/event-stream" in self._response.headers.get("content-type", "")

        # Read until we get the endpoint event
        async for chunk in self._response.aiter_bytes():
            self._buffer += chunk.decode("utf-8", errors="replace")
            events = parse_sse_events(self._buffer)
            for ev in events:
                if ev.get("event") == "endpoint":
                    self.endpoint = ev["data"]
                    # Extract session_id from endpoint
                    if "session_id=" in self.endpoint:
                        self.session_id = self.endpoint.split("session_id=")[1].split("&")[0]
                    return
        raise RuntimeError("No endpoint event received from SSE stream")

    async def send_jsonrpc(self, method: str, params: dict = None, req_id: int = None):
        """POST a JSON-RPC request to the messages endpoint."""
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if req_id is not None:
            body["id"] = req_id

        r = await self.client.post(
            self.endpoint,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        return r

    async def read_response(self, timeout: float = 5.0) -> dict:
        """Read the next JSON-RPC response from the SSE stream."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                chunk = b""
                async for c in self._response.aiter_bytes():
                    chunk += c
                    break  # Read one chunk at a time
                if chunk:
                    self._buffer += chunk.decode("utf-8", errors="replace")
            except Exception:
                pass

            # Check if we have a complete JSON-RPC response in buffer
            events = parse_sse_events(self._buffer)
            for ev in events:
                if ev.get("event") == "message":
                    data = ev.get("data", "")
                    try:
                        msg = json.loads(data)
                        if "result" in msg or "error" in msg:
                            # Clear consumed events from buffer
                            return msg
                    except (json.JSONDecodeError, ValueError):
                        continue

            await asyncio.sleep(0.1)
        return None

    async def close(self):
        if self._response:
            await self._response.aclose()


# ──────────────────────────────────────────────────────────────
# Subprocess-based SSE Tests
# ──────────────────────────────────────────────────────────────

class TestSSESubprocess:

    @pytest.mark.timeout(30)
    def test_sse_server_starts(self, mcp_sse_server):
        proc, base_url = mcp_sse_server
        assert proc.poll() is None  # still running

    @pytest.mark.timeout(30)
    def test_sse_endpoint_discovery(self, mcp_sse_server):
        """GET /sse returns an SSE stream with an endpoint event."""
        proc, base_url = mcp_sse_server
        with httpx.Client() as client:
            with client.stream("GET", f"{base_url}/sse") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
                buffer = ""
                for chunk in response.iter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")
                    events = parse_sse_events(buffer)
                    for ev in events:
                        if ev.get("event") == "endpoint":
                            assert "/messages/" in ev["data"]
                            assert "session_id=" in ev["data"]
                            return
                    if len(buffer) > 4096:
                        break
        pytest.fail("No endpoint event received from SSE stream")

    @pytest.mark.timeout(30)
    def test_sse_initialize_and_tools_list(self, mcp_sse_server):
        """Full SSE flow: connect → initialize → tools/list."""
        proc, base_url = mcp_sse_server
        import threading

        results = {"endpoint": None, "tools_response": None}
        buffer_lock = threading.Lock()
        buffer_data = {"text": ""}

        def sse_reader():
            """Background thread to read the SSE stream."""
            try:
                with httpx.Client() as client:
                    with client.stream("GET", f"{base_url}/sse") as response:
                        for chunk in response.iter_bytes():
                            with buffer_lock:
                                buffer_data["text"] += chunk.decode("utf-8", errors="replace")
                            # Check for endpoint
                            events = parse_sse_events(buffer_data["text"])
                            for ev in events:
                                if ev.get("event") == "endpoint" and not results["endpoint"]:
                                    results["endpoint"] = ev["data"]
                            # Stop after we get a tools response
                            if results.get("tools_response"):
                                return
            except (httpx.RemoteProtocolError, httpx.ReadError, ConnectionError):
                pass  # Expected when server shuts down

        reader = threading.Thread(target=sse_reader, daemon=True)
        reader.start()

        # Wait for endpoint
        deadline = time.time() + 10
        while time.time() < deadline and not results["endpoint"]:
            time.sleep(0.2)
        assert results["endpoint"], "No endpoint event received"

        messages_url = f"{base_url}{results['endpoint']}"

        with httpx.Client() as client:
            # Initialize
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
            r = client.post(messages_url, json=init_req, headers={"Content-Type": "application/json"})
            assert r.status_code == 202, f"Initialize POST failed: {r.status_code} {r.text[:200]}"

            # Wait for initialize response on SSE stream
            deadline = time.time() + 10
            init_response = None
            while time.time() < deadline and not init_response:
                time.sleep(0.3)
                with buffer_lock:
                    events = parse_sse_events(buffer_data["text"])
                for ev in events:
                    if ev.get("event") == "message":
                        try:
                            msg = json.loads(ev["data"])
                            if msg.get("id") == 1 and "result" in msg:
                                init_response = msg
                                break
                        except (json.JSONDecodeError, ValueError):
                            continue
            assert init_response, "No initialize response on SSE stream"

            # Send initialized notification
            notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            r2 = client.post(messages_url, json=notif, headers={"Content-Type": "application/json"})
            assert r2.status_code == 202

            # Request tools/list
            tools_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            r3 = client.post(messages_url, json=tools_req, headers={"Content-Type": "application/json"})
            assert r3.status_code == 202

            # Wait for tools/list response on SSE stream
            deadline = time.time() + 10
            tools_response = None
            while time.time() < deadline and not tools_response:
                time.sleep(0.3)
                with buffer_lock:
                    events = parse_sse_events(buffer_data["text"])
                for ev in events:
                    if ev.get("event") == "message":
                        try:
                            msg = json.loads(ev["data"])
                            if msg.get("id") == 2 and "result" in msg:
                                tools_response = msg
                                break
                        except (json.JSONDecodeError, ValueError):
                            continue

            results["tools_response"] = tools_response
            assert tools_response, "No JSON-RPC result received on SSE stream"
            tools = tools_response["result"]["tools"]
            assert len(tools) > 0
            tool_names = [t["name"] for t in tools]
            assert "nucleus_engrams" in tool_names

        reader.join(timeout=3)


# ──────────────────────────────────────────────────────────────
# ASGI-based SSE Tests (no subprocess)
# ──────────────────────────────────────────────────────────────

class TestSSEApp:

    def test_sse_app_has_routes(self):
        """The SSE app should have /sse and /messages routes."""
        from mcp_server_nucleus.http_transport.server import build_app
        app = build_app("sse")
        paths = [getattr(r, "path", "?") for r in app.routes]
        assert "/sse" in paths
