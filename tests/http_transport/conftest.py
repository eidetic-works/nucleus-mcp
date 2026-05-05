"""
HTTP Transport Test Suite — conftest.py
========================================
Fixtures for testing Nucleus HTTP/SSE/Cloud transports.

Strategy:
  - Health/identity endpoints: ASGI transport (no lifespan needed)
  - MCP protocol endpoints: subprocess-based servers (lifespan requires anyio)
  - Auth enforcement: subprocess-based servers with env vars
"""

import os
import sys
import json
import time
import socket
import subprocess

import httpx
import pytest
import pytest_asyncio


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 15.0):
    """Block until a TCP connection succeeds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"Server at {host}:{port} did not start within {timeout}s")


def parse_sse_events(text: str) -> list:
    """Parse SSE text into a list of {event, data} dicts."""
    events = []
    current = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def extract_jsonrpc_result(text: str):
    """Extract JSON-RPC result from SSE-formatted or plain JSON response."""
    # Try plain JSON first
    try:
        body = json.loads(text)
        if "result" in body or "error" in body:
            return body
    except (json.JSONDecodeError, ValueError):
        pass

    # Parse as SSE events
    events = parse_sse_events(text)
    for ev in events:
        data = ev.get("data", "")
        try:
            body = json.loads(data)
            if "result" in body or "error" in body:
                return body
        except (json.JSONDecodeError, ValueError):
            continue
    return None


MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _start_server(tmp_path, module, extra_env=None, transport=None):
    """Start a Nucleus server subprocess and return (proc, base_url)."""
    port = _free_port()
    env = {
        **os.environ,
        "NUCLEUS_BRAIN_ROOT": str(tmp_path / "brains"),
        "NUCLEUS_LOG_LEVEL": "WARNING",
        "NUCLEUS_HTTP_HOST": "127.0.0.1",
    }
    env.pop("NUCLEAR_BRAIN_PATH", None)
    env.pop("NUCLEUS_TENANT_ID", None)

    if module == "mcp_server_nucleus.http_transport.app":
        env["PORT"] = str(port)
    else:
        env["NUCLEUS_HTTP_PORT"] = str(port)

    if transport:
        env["NUCLEUS_HTTP_TRANSPORT"] = transport

    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server("127.0.0.1", port)
    except TimeoutError:
        proc.kill()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Server failed to start: {stderr[-500:]}")
    return proc, f"http://127.0.0.1:{port}"


def _stop_server(proc):
    """Terminate a server subprocess."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# ──────────────────────────────────────────────────────────────
# ASGI-based fixtures (no lifespan, for health/identity only)
# ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def cloud_client(tmp_path):
    """Async httpx client for cloud app — health/identity endpoints only (no lifespan)."""
    old_brain_root = os.environ.get("NUCLEUS_BRAIN_ROOT")
    old_brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
    os.environ["NUCLEUS_BRAIN_ROOT"] = str(tmp_path / "brains")
    os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    from mcp_server_nucleus.http_transport.app import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    if old_brain_root is not None:
        os.environ["NUCLEUS_BRAIN_ROOT"] = old_brain_root
    else:
        os.environ.pop("NUCLEUS_BRAIN_ROOT", None)
    if old_brain_path is not None:
        os.environ["NUCLEAR_BRAIN_PATH"] = old_brain_path


# ──────────────────────────────────────────────────────────────
# Subprocess-based server fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def cloud_server(tmp_path):
    """Start a real cloud server subprocess and yield (process, base_url)."""
    proc, base_url = _start_server(tmp_path, "mcp_server_nucleus.http_transport.app")
    yield proc, base_url
    _stop_server(proc)


@pytest.fixture
def mcp_http_server(tmp_path):
    """Start a real HTTP MCP server subprocess (streamable-http)."""
    proc, base_url = _start_server(
        tmp_path, "mcp_server_nucleus.http_transport.server",
        transport="streamable-http",
    )
    yield proc, base_url
    _stop_server(proc)


@pytest.fixture
def mcp_sse_server(tmp_path):
    """Start a real SSE MCP server subprocess."""
    proc, base_url = _start_server(
        tmp_path, "mcp_server_nucleus.http_transport.server",
        transport="sse",
    )
    yield proc, base_url
    _stop_server(proc)


@pytest.fixture
def multitenant_server(tmp_path):
    """Start a server with NUCLEUS_REQUIRE_AUTH=true and a tenant map."""
    tenant_map = json.dumps({
        "valid-token-123": "tenant-a",
        "valid-token-456": {"tenant": "tenant-b", "expires": "2099-12-31T00:00:00Z"},
    })
    proc, base_url = _start_server(
        tmp_path, "mcp_server_nucleus.http_transport.server",
        transport="streamable-http",
        extra_env={
            "NUCLEUS_REQUIRE_AUTH": "true",
            "NUCLEUS_TENANT_MAP": tenant_map,
        },
    )
    yield proc, base_url
    _stop_server(proc)


# ──────────────────────────────────────────────────────────────
# Sync MCP session helpers (for subprocess-based tests)
# ──────────────────────────────────────────────────────────────

def mcp_initialize_sync(base_url: str, path: str = "/mcp",
                        extra_headers: dict = None) -> str:
    """Perform MCP initialize handshake and return the session ID."""
    headers = {**MCP_HEADERS}
    if extra_headers:
        headers.update(extra_headers)

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
    r = httpx.post(f"{base_url}{path}", json=init_req, headers=headers, timeout=10.0)
    assert r.status_code == 200, f"Initialize failed: {r.status_code} {r.text[:200]}"
    session_id = r.headers.get("mcp-session-id", "")
    assert session_id, "No mcp-session-id in initialize response"

    result = extract_jsonrpc_result(r.text)
    assert result is not None, f"No JSON-RPC result in initialize response: {r.text[:200]}"

    # Send initialized notification
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    hdrs = {**headers, "mcp-session-id": session_id}
    r2 = httpx.post(f"{base_url}{path}", json=notif, headers=hdrs, timeout=10.0)
    assert r2.status_code in (200, 202, 204), f"Initialized notification failed: {r2.status_code}"

    return session_id


def mcp_call_sync(base_url: str, method: str, params: dict,
                  session_id: str, req_id: int = 2, path: str = "/mcp",
                  extra_headers: dict = None):
    """Send a JSON-RPC request and return the parsed result."""
    headers = {**MCP_HEADERS, "mcp-session-id": session_id}
    if extra_headers:
        headers.update(extra_headers)

    req = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params,
    }
    r = httpx.post(f"{base_url}{path}", json=req, headers=headers, timeout=30.0)
    assert r.status_code == 200, f"MCP call {method} failed: {r.status_code} {r.text[:300]}"
    return extract_jsonrpc_result(r.text)
