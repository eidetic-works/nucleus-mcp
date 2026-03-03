import sys
import json
import subprocess
import time
import os

env = os.environ.copy()
env["FASTMCP_SHOW_CLI_BANNER"] = "False"
env["NUCLEUS_TOOL_TIER"] = "2"
env["PYTHONPATH"] = os.path.abspath("src")

p = subprocess.Popen(
    ["/opt/homebrew/opt/python@3.11/bin/python3.11", "-m", "mcp_server_nucleus"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

time.sleep(1)

req = {
    "jsonrpc": "2.0", 
    "id": 1, 
    "method": "tools/list"
}
p.stdin.write(json.dumps(req) + "\n")
p.stdin.flush()
print("Response:", p.stdout.readline())

p.terminate()
