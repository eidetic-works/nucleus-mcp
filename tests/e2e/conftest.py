"""
Phase 3 E2E conftest — shared fixtures for live-process E2E tests.

All tests in this directory exercise REAL subprocess servers / daemons over
real HTTP transport (httpx). No in-process FastMCP mocks.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

import httpx
import pytest

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

PY = sys.executable


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _free_port() -> int:
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 20.0):
    """Block until a TCP connection succeeds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"Server at {host}:{port} did not start within {timeout}s")


def _stop_server(proc):
    """Terminate a server subprocess."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def extract_jsonrpc_result(text: str):
    """Extract JSON-RPC result from SSE-formatted or plain JSON response."""
    try:
        body = json.loads(text)
        if "result" in body or "error" in body:
            return body
    except (json.JSONDecodeError, ValueError):
        pass
    # Parse as SSE events
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("data:"):
            try:
                body = json.loads(line[len("data:"):].strip())
                if "result" in body or "error" in body:
                    return body
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def mcp_initialize(base_url: str, path: str = "/mcp") -> str:
    """Perform MCP initialize handshake and return the session ID."""
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "e2e-test-client", "version": "0.1.0"},
        },
    }
    r = httpx.post(f"{base_url}{path}", json=init_req, headers=MCP_HEADERS, timeout=15.0)
    assert r.status_code == 200, f"Initialize failed: {r.status_code} {r.text[:200]}"
    session_id = r.headers.get("mcp-session-id", "")
    assert session_id, "No mcp-session-id in initialize response"
    # Send initialized notification
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    hdrs = {**MCP_HEADERS, "mcp-session-id": session_id}
    httpx.post(f"{base_url}{path}", json=notif, headers=hdrs, timeout=10.0)
    return session_id


def mcp_call(base_url: str, method: str, params: dict,
             session_id: str, req_id: int = 2, path: str = "/mcp"):
    """Send a JSON-RPC request and return the parsed result."""
    headers = {**MCP_HEADERS, "mcp-session-id": session_id}
    req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    r = httpx.post(f"{base_url}{path}", json=req, headers=headers, timeout=30.0)
    assert r.status_code == 200, f"MCP call {method} failed: {r.status_code} {r.text[:300]}"
    return extract_jsonrpc_result(r.text)


def mcp_tool_call(base_url: str, tool_name: str, action: str, params: dict,
                  session_id: str, req_id: int = 2):
    """Call an MCP tool by name with action+params and return parsed JSON content."""
    result = mcp_call(
        base_url, "tools/call",
        {"name": tool_name, "arguments": {"action": action, "params": params}},
        session_id, req_id=req_id,
    )
    assert result is not None, f"No JSON-RPC result for {tool_name}/{action}"
    if "error" in result:
        return {"_rpc_error": result["error"]}
    content = result["result"]["content"][0]["text"]
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"_raw": content}


# ──────────────────────────────────────────────────────────────
# Server fixtures
# ──────────────────────────────────────────────────────────────

def _start_http_server(tmp_path, extra_env=None, transport="streamable-http"):
    """Start a real Nucleus HTTP MCP server subprocess and return (proc, base_url)."""
    port = _free_port()
    brain_root = tmp_path / "brains"
    brain_root.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "NUCLEUS_BRAIN_ROOT": str(brain_root),
        "NUCLEUS_LOG_LEVEL": "WARNING",
        "NUCLEUS_HTTP_HOST": "127.0.0.1",
        "NUCLEUS_HTTP_PORT": str(port),
        "NUCLEUS_HTTP_TRANSPORT": transport,
        "FASTMCP_SHOW_CLI_BANNER": "False",
        "NUCLEUS_TOOL_TIER": "2",
    }
    env.pop("NUCLEUS_BRAIN_PATH", None)
    env.pop("NUCLEAR_BRAIN_PATH", None)
    env.pop("NUCLEUS_TENANT_ID", None)
    env.pop("NUCLEUS_RELAY_URL", None)
    env.pop("NUCLEUS_RELAY_BEARER", None)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [PY, "-m", "mcp_server_nucleus.http_transport.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server("127.0.0.1", port)
    except TimeoutError:
        proc.kill()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Server failed to start: {stderr[-800:]}")
    return proc, f"http://127.0.0.1:{port}"


@pytest.fixture
def http_server(tmp_path):
    """Start a real HTTP MCP server subprocess (streamable-http)."""
    proc, base_url = _start_http_server(tmp_path)
    yield proc, base_url
    _stop_server(proc)


def _start_cloud_server(tmp_path, extra_env=None):
    """Start the cloud app (http_transport.app) which has ALL routes: health, relay, MCP."""
    port = _free_port()
    brain_root = tmp_path / "brains"
    brain_root.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "NUCLEUS_BRAIN_ROOT": str(brain_root),
        "NUCLEUS_LOG_LEVEL": "WARNING",
        "NUCLEUS_HTTP_HOST": "127.0.0.1",
        "PORT": str(port),
        "NUCLEUS_TRANSPORT": "streamable-http",
        "FASTMCP_SHOW_CLI_BANNER": "False",
        "NUCLEUS_TOOL_TIER": "2",
    }
    env.pop("NUCLEUS_BRAIN_PATH", None)
    env.pop("NUCLEAR_BRAIN_PATH", None)
    env.pop("NUCLEUS_TENANT_ID", None)
    env.pop("NUCLEUS_RELAY_URL", None)
    env.pop("NUCLEUS_RELAY_BEARER", None)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [PY, "-m", "mcp_server_nucleus.http_transport.app"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server("127.0.0.1", port)
    except TimeoutError:
        proc.kill()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloud server failed to start: {stderr[-800:]}")
    return proc, f"http://127.0.0.1:{port}"


@pytest.fixture
def http_server_with_relay(tmp_path):
    """Start the cloud app with relay routes + token map configured (all routes available).

    Includes NUCLEUS_TENANT_MAP so the tenant middleware routes each token to a
    separate brain directory, enabling multi-tenant isolation testing.
    """
    relay_token_map = json.dumps({
        "tok-tenant-a": "tenant-a-sender",
        "tok-tenant-b": "tenant-b-sender",
    })
    tenant_map = json.dumps({
        "tok-tenant-a": "tenant-a",
        "tok-tenant-b": "tenant-b",
    })
    proc, base_url = _start_cloud_server(
        tmp_path,
        extra_env={
            "NUCLEUS_RELAY_TOKEN_MAP": relay_token_map,
            "NUCLEUS_TENANT_MAP": tenant_map,
            "NUCLEUS_RELAY_RATE_PER_MIN": "200",
            "NUCLEUS_RELAY_RATE_BURST": "50",
            "NUCLEUS_RELAY_MAX_BODY": str(200 * 1024),  # 200 KiB for large payload tests
        },
    )
    yield proc, base_url
    _stop_server(proc)


@pytest.fixture
def http_server_multitenant(tmp_path):
    """Start the cloud app with NUCLEUS_REQUIRE_AUTH=true and a tenant map for isolation tests."""
    tenant_map = json.dumps({
        "tok-tenant-a": "tenant-a",
        "tok-tenant-b": "tenant-b",
    })
    proc, base_url = _start_cloud_server(
        tmp_path,
        extra_env={
            "NUCLEUS_REQUIRE_AUTH": "true",
            "NUCLEUS_TENANT_MAP": tenant_map,
        },
    )
    yield proc, base_url
    _stop_server(proc)


@pytest.fixture
def isolated_brain(tmp_path):
    """Provide an isolated brain directory for direct FS tests."""
    brain = tmp_path / ".brain"
    for subdir in [
        "engrams", "ledger", "sessions", "memory", "tasks",
        "artifacts", "proofs", "strategy", "governance", "channels",
        "federation", "deltas", "training", "meta", "driver", "relay",
    ]:
        (brain / subdir).mkdir(parents=True, exist_ok=True)
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
    os.environ.pop("NUCLEUS_RELAY_URL", None)
    os.environ.pop("NUCLEUS_RELAY_BEARER", None)
    yield brain
    os.environ.pop("NUCLEUS_BRAIN_PATH", None)
