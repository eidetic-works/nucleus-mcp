
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.mounter import get_mounter, MountedServer, RecursiveMounter

async def test_tool_discovery():
    brain_path = Path(os.environ["NUCLEAR_BRAIN_PATH"])
    mounter = get_mounter(brain_path)
    
    print("--- 1. Mount Dummy Server (Python Simple MCP) ---")
    # We use a python one-liner that acts as a minimal MCP server responding to tools/list
    # This is tricky without a real server.
    # Alternatively, we can mock the process or use a known simple server.
    # For this test, we'll try to mount 'echo' or similar, but echo doesn't speak JSON-RPC.
    
    # Better approach: We'll subclass MountedServer to mock the process interaction 
    # since we don't have a real external MCP server installed in the environment guaranteed.
    # BUT, we want to verify the 'list_tools' integration.
    
    # Let's try to mock the processIO in a real integration style if possible, 
    # or just assume we can mount *ourselves*? No, that's complex.
    
    # Let's create a tiny python script that speaks MCP tools/list
    mock_server_code = """
import sys
import json

while True:
    try:
        line = sys.stdin.readline()
        if not line: break
        request = json.loads(line)
        if request.get("method") == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {"name": "mock_tool", "description": "A mock tool for testing"}
                    ]
                }
            }
            sys.stdout.write(json.dumps(response) + "\\n")
            sys.stdout.flush()
    except Exception:
        break
"""
    mock_server_path = brain_path / "mock_mcp_server.py"
    mock_server_path.write_text(mock_server_code)
    
    print(f"Created mock server at {mock_server_path}")
    
    # Mount it
    server_id = None
    try:
        result = await mounter.mount("mock-server", "python3", [str(mock_server_path)])
        print(f"Mount Result: {result}")
        if "Successfully mounted" in result:
            server_id = result.split(" as ")[1]
    except Exception as e:
        print(f"❌ Mount failed: {e}")
        return

    print("\n--- 2. Discover Tools ---")
    if server_id:
        server = mounter.mounted_servers[server_id]
        tools = await server.list_tools()
        print(f"Discovered Tools: {json.dumps(tools, indent=2)}")
        
        assert len(tools) == 1
        assert tools[0]["name"] == "mock_tool"
        print("✅ Tool Discovery Verified")
        
        # Clean up
        await mounter.unmount(server_id)
        print("✅ Unmounted mock server")
    else:
        print("❌ Could not get server ID")

    # Cleanup file
    if mock_server_path.exists():
        mock_server_path.unlink()

if __name__ == "__main__":
    if "NUCLEAR_BRAIN_PATH" not in os.environ:
        os.environ["NUCLEAR_BRAIN_PATH"] = "/Users/lokeshgarg/.brain"
    
    asyncio.run(test_tool_discovery())
