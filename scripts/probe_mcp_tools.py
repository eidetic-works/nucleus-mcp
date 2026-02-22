
import sys
import os

# Set dummy brain path so import doesn't fail
os.environ["NUCLEAR_BRAIN_PATH"] = "/tmp/nucleus_probe"

try:
    from mcp_server_nucleus import mcp
    print("MCP Object Type:", type(mcp))
    print("\nDir(mcp):")
    for d in dir(mcp):
        if not d.startswith("__"):
            print(f"- {d}")
    
    # Try to find tools
    if hasattr(mcp, "_tools"):
        print(f"\n_tools count: {len(mcp._tools)}")
        print("Sample tools:", list(mcp._tools.keys())[:5])
    elif hasattr(mcp, "tools"):
        print(f"\ntools count: {len(mcp.tools)}")
    
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
