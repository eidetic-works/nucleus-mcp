import sys
import os
import json
import asyncio

env = os.environ.copy()
env["FASTMCP_SHOW_CLI_BANNER"] = "False"
env["NUCLEUS_TOOL_TIER"] = "2"
os.environ.update(env)

sys.path.insert(0, os.path.abspath("src"))

from mcp_server_nucleus import mcp

async def main():
    tools = await mcp.list_tools()
    for t in tools:
        if t.name == "nucleus_governance":
            print(json.dumps(t.inputSchema, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
