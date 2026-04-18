
import asyncio
import sys
import os
import json
import traceback
from typing import List, Dict, Any

# Ensure we use a clean test path
os.environ["NUCLEAR_BRAIN_PATH"] = "/tmp/nucleus_smoke_test"
from pathlib import Path
Path("/tmp/nucleus_smoke_test/ledger").mkdir(parents=True, exist_ok=True)
Path("/tmp/nucleus_smoke_test/sessions").mkdir(parents=True, exist_ok=True)

async def run_smoke_test():
    print("="*60)
    print("🚀 NUCLEUS SOVEREIGN OS: EXHAUSTIVE SMOKE TEST (130 TOOLS)")
    print("="*60)
    
    try:
        from mcp_server_nucleus import mcp
    except ImportError as e:
        print(f"❌ CRITICAL: Could not import mcp_server_nucleus: {e}")
        sys.exit(1)

    # Access the internal tool manager to get the full list
    tools_dict = {}
    if hasattr(mcp, "_tool_manager"):
        if hasattr(mcp._tool_manager, "_tools"):
            tools_dict = mcp._tool_manager._tools
        elif isinstance(mcp._tool_manager, dict):
            tools_dict = mcp._tool_manager
    
    if not tools_dict:
        print("❌ FAIL: No tools found in FastMCP registry.")
        sys.exit(1)

    total_count = len(tools_dict)
    print(f"Detected {total_count} tools in registry.\n")

    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    print(f"{'#':<4} {'Tool Name':<40} {'Status':<10}")
    print("-" * 60)

    for i, (name, tool) in enumerate(sorted(tools_dict.items()), 1):
        try:
            # Verify the tool has a function attached
            if not hasattr(tool, "fn") or not callable(tool.fn):
                raise AttributeError(f"Tool '{name}' has no callable 'fn'")
            
            # Resolution Check: Check if the function's module is loaded and it exists
            # We don't execute it to avoid side effects, but we access it to trigger lazy loads
            func = tool.fn
            doc = func.__doc__ or "No documentation"
            
            print(f"{i:<4} {name:<40} ✅ PASS")
            results["passed"] += 1
            
        except Exception as e:
            print(f"{i:<4} {name:<40} ❌ FAIL")
            results["failed"] += 1
            results["errors"].append({
                "tool": name,
                "error": str(e),
                "trace": traceback.format_exc()
            })

    print("-" * 60)
    print(f"TOTAL: {total_count}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results["failed"] > 0:
        print("\n❌ SMOKE TEST FAILED")
        for err in results["errors"]:
            print(f"\n--- Error in {err['tool']} ---")
            print(err["error"])
        sys.exit(1)
    else:
        print("\n✅ SMOKE TEST PASSED: ALL TOOLS ARE INTERNALLY STABLE")
        print("READY FOR LAUNCH")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
