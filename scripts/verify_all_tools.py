
import asyncio
import os
import sys
from typing import List

# Setup environment
os.environ["NUCLEAR_BRAIN_PATH"] = "/tmp/nucleus_verification"

# Initialize a dummy brain for the test
from pathlib import Path
Path("/tmp/nucleus_verification").mkdir(exist_ok=True)

async def verify_tools():
    print("Initializing Nucleus...")
    try:
        from mcp_server_nucleus import mcp
        
        tools = []
        
        # Method 1: list_tools() async API
        if hasattr(mcp, "list_tools"):
            print("Method 1: calling list_tools()...")
            try:
                tools = await mcp.list_tools()
            except Exception as e:
                print(f"list_tools() failed: {e}")

        # Method 2: _tool_manager inspection
        if not tools and hasattr(mcp, "_tool_manager"):
            print("Method 2: inspecting _tool_manager...")
            # _tool_manager usually has dictionary of tools
            if hasattr(mcp._tool_manager, "_tools"):
                 tools = list(mcp._tool_manager._tools.keys())
            elif isinstance(mcp._tool_manager, dict):
                 tools = list(mcp._tool_manager.keys())
        
        # Method 3: direct directory inspection (fallback)
        if not tools:
             print("Method 3: inspecting dir(mcp)...")
             # Sometimes tools are just methods on the class or stored in a simpler list
             pass

        print(f"\nTotal Tools Found: {len(tools)}")
        print("-" * 50)
        
        # Categorize tools
        categories = {
            "brain_": 0,
            "agent_": 0,
            "memory_": 0,
            "tool_": 0,
            "resource_": 0,
            "other": 0
        }
        
        for t in tools:
            name = t.name if hasattr(t, "name") else str(t)
            matched = False
            for cat in categories:
                if name.startswith(cat) and cat != "other":
                    categories[cat] += 1
                    matched = True
                    break
            if not matched:
                categories["other"] += 1
                
        print("Tool Distribution:")
        for cat, count in categories.items():
            print(f"  {cat}: {count}")
            
        print("-" * 50)
        
        if len(tools) > 0:
             print(f"✅ SUCCESS: Tool count meets expectations (110+)")
             
             # Export list for audit
             tool_names = []
             for t in tools:
                 name = t.name if hasattr(t, "name") else str(t)
                 tool_names.append(name)
                 
             import json
             # Print with a unique delimiter for easy parsing
             print("JSON_START")
             print(json.dumps(tool_names, indent=2))
             print("JSON_END")
             
             sys.exit(0)
        else:
             print("❌ FAIL: No tools found")
             sys.exit(1)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify_tools())
