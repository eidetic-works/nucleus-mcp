import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus import (
    brain_thanos_snap,
    brain_discover_mounted_tools,
    brain_invoke_mounted_tool,
    get_brain_path
)

async def verify():
    print("🧪 Starting E2E Verification for Phase C...")
    
    # 1. Setup environment
    brain_path = Path("/tmp/snap_verify_brain")
    if brain_path.exists():
        import shutil
        shutil.rmtree(brain_path)
    brain_path.mkdir(parents=True, exist_ok=True)
    (brain_path / "ledger").mkdir(exist_ok=True)
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain_path)
    
    # 2. Trigger Thanos Snap
    print("\n⚡ Triggering Thanos Snap...")
    snap_res = await brain_thanos_snap()
    print(f"Snap Result: {snap_res}")
    
    if "Complete" not in snap_res:
        print("❌ Snap Failed!")
        sys.exit(1)
    
    # 3. Discovery Check
    print("\n🔍 Discovering Mounted Tools...")
    # Wait for mock servers to initialize
    await asyncio.sleep(1)
    
    discovery_res_json = await brain_discover_mounted_tools()
    discovery_res = json.loads(discovery_res_json)
    
    if not discovery_res.get("success"):
         print(f"❌ Discovery Failed: {discovery_res}")
         sys.exit(1)
         
    tools_found = discovery_res.get("data", {})
    print(f"Servers Discovered: {list(tools_found.keys())}")
    
    # 4. Execution Check (Stripe)
    print("\n📡 Testing Governed Execution (Stripe)...")
    # In the mock, we can use the name since we know it. 
    # But technically we should use the ID from brain_list_mounts.
    from mcp_server_nucleus import brain_list_mounted
    mounts = json.loads(brain_list_mounted())["data"]
    stripe_mount = next((m for m in mounts if m["name"] == "stripe"), None)
    
    if not stripe_mount:
        print("❌ Stripe mount not found in ledger!")
        sys.exit(1)
        
    invoke_res = await brain_invoke_mounted_tool(stripe_mount["id"], "list_customers", {})
    print(f"Stripe Response: {invoke_res}")
    
    if "User_A" in invoke_res:
        print("\n✅ VERIFICATION SUCCESSFUL: Recursive mesh is active and routing.")
    else:
        print("\n❌ VERIFICATION FAILED: Data mismatch.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify())
