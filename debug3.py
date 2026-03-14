import sys
import os
import json

env = os.environ.copy()
env["FASTMCP_SHOW_CLI_BANNER"] = "False"
env["NUCLEUS_TOOL_TIER"] = "2"
os.environ.update(env)

sys.path.insert(0, os.path.abspath("src"))

from mcp_server_nucleus import mcp

for t in mcp._tools.values():
    if t.name == "nucleus_governance":
        print(t.parameters)
