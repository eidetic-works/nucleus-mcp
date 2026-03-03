import sys
import json
import subprocess
import time
import os

env = os.environ.copy()
env["FASTMCP_SHOW_CLI_BANNER"] = "False"
env["NUCLEUS_TOOL_TIER"] = "2"

p = subprocess.Popen(
    ["/opt/homebrew/opt/python@3.11/bin/python3.11", "-m", "mcp_server_nucleus"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

time.sleep(1)

def send(req):
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    print("<-", p.stdout.readline().strip())

# 0. Initialize
send({
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
})

# 1. tools/call
send({
    "jsonrpc": "2.0", 
    "id": 1, 
    "method": "tools/call", 
    "params": {
        "name": "nucleus_governance", 
        "arguments": {
            "action": "status"
        }
    }
})

p.terminate()
