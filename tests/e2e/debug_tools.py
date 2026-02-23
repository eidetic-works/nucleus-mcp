import subprocess, json, sys, os
env = os.environ.copy()
env["FASTMCP_SHOW_CLI_BANNER"] = "False"
env["NUCLEUS_TOOL_TIER"] = "2"
p = subprocess.Popen([sys.executable, "-m", "mcp_server_nucleus"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
p.stdin.write(json.dumps(payload) + "\n")
p.stdin.flush()
print("Sent tools/list")
print(p.stdout.readline())
p.terminate()
