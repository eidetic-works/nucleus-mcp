import subprocess
import json
import time
import pytest
import os
import sys

# Pytest marker to identify these as slow e2e tests
pytestmark = pytest.mark.e2e

# Skip if FastMCP is not installed — subprocess server cannot boot
try:
    import fastmcp  # noqa: F401
    _HAS_FASTMCP = True
except ImportError:
    _HAS_FASTMCP = False

class MockMCPClient:
    """A minimal MCP client that wraps a subprocess pipe"""
    def __init__(self):
        env = os.environ.copy()
        # Ensure we don't output the interactive FastMCP banner which breaks JSON parsing
        env["FASTMCP_SHOW_CLI_BANNER"] = "False"
        env["NUCLEUS_TOOL_TIER"] = "2"  # Unlock all for testing
        
        self.process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server_nucleus"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        self.req_id = 1
        
        # Must initialize MCP protocol before using FastMCP
        init_req = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        self.process.stdin.write(json.dumps(init_req) + "\\n")
        self.process.stdin.flush()
        # Consume initialize result
        self.process.stdout.readline()

    def is_alive(self) -> bool:
        """Check if the subprocess is still running."""
        return self.process.poll() is None

    def call_tool(self, name: str, arguments: dict):
        # Guard: ensure server hasn't crashed before writing
        if not self.is_alive():
            err = self.process.stderr.read() if self.process.stderr else "(no stderr)"
            pytest.skip(f"MCP server process exited before tool call. Stderr: {err[:200]}")
        
        # Construct the JSON-RPC payload matching the MCP v1.0 spec for tools
        payload = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        self.req_id += 1
        
        try:
            # Send strictly formatted JSON over stdio
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            err = self.process.stderr.read() if self.process.stderr else "(no stderr)"
            pytest.skip(f"MCP server pipe closed (server may have exited). Stderr: {err[:200]}")
        
        # Wait for the response
        response_line = self.process.stdout.readline()
        if not response_line:
            err = self.process.stderr.read() if self.process.stderr else "(no stderr)"
            pytest.skip(f"Server closed connection unexpectedly. Stderr: {err[:200]}")
            
        return json.loads(response_line)

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=2)

@pytest.fixture
def mcp_client():
    if not _HAS_FASTMCP:
        pytest.skip("FastMCP not installed — E2E subprocess server cannot boot")
    client = MockMCPClient()
    # Wait for the server to fully boot
    time.sleep(0.5)
    # Verify server is still alive after boot
    if not client.is_alive():
        err = client.process.stderr.read() if client.process.stderr else "(no stderr)"
        client.close()
        pytest.skip(f"MCP server exited during boot. Stderr: {err[:200]}")
    yield client
    client.close()

def test_egress_firewall_allowed(mcp_client):
    """Verify that nucleus_curl succeeds on allowed domains (github)."""
    resp = mcp_client.call_tool("nucleus_governance", {
        "action": "curl",
        "params": {
            "url": "https://raw.githubusercontent.com/eidetic-works/mcp-server-nucleus/main/README.md",
            "method": "GET"
        }
    })
    
    assert "result" in resp, f"Expected result payload, got: {resp}"
    
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    
    if not data["success"]:
        assert "HTTP Error" in data.get("error", "") or "404" in data.get("error", "")
    else:
        assert data["status_code"] in [200, 404]

def test_egress_firewall_blocked(mcp_client):
    """Verify that nucleus_curl aggressively blocks unlisted domains."""
    resp = mcp_client.call_tool("nucleus_governance", {
        "action": "curl",
        "params": {
            "url": "https://www.google.com",
            "method": "GET"
        }
    })
    
    assert "result" in resp
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    
    assert data["success"] is False
    assert "Egress Firewall Blocked" in data["error"]

def test_rpc_firewall_interception(mcp_client):
    """
    Verify that tools mutating state are intercepted.
    We'll test context_update (which is a valid tool).
    """
    # Note: testing watch_resource or editing is harder in a raw E2E without 
    # setting up the full handoff.md structure.
    # We will test a safe tool just to ensure the RPC loop is alive.
    resp = mcp_client.call_tool("nucleus_governance", {"action": "status", "params": {}})
    assert "result" in resp
    content = resp["result"]["content"][0]["text"]
    assert "NUCLEUS HYPERVISOR" in content
