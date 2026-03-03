import subprocess
import json
import time

p = subprocess.Popen(
    ["/opt/homebrew/bin/python3.11", "-m", "mcp_server_nucleus", "--status"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env={
        "NUCLEUS_BETA_TOKEN": "titan-sovereign-godmode",
        "NUCLEUS_TOOL_TIER": "2",
        "NUCLEAR_BRAIN_PATH": "/Users/lokeshgarg/ai-mvp-backend/.brain",
        "PYTHONPATH": "/Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus/src",
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin"
    }
)

time.sleep(1)

reqs = [
    '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}\n',
    '{"jsonrpc": "2.0", "method": "notifications/initialized"}\n',
    '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}\n'
]

for req in reqs:
    p.stdin.write(req)
    
p.stdin.flush()

output_lines = []
while True:
    line = p.stdout.readline()
    if not line: break
    if '"id":2' in line or '"id": 2' in line:
        try:
            data = json.loads(line)
            print(f"✅ SUCCESS: Parsed tools/list. Total tools: {len(data['result']['tools'])}")
            break
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            break

p.terminate()
