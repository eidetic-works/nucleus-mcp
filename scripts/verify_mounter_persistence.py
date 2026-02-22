import asyncio
import json
import os
from pathlib import Path
from mcp_server_nucleus.runtime.mounter import get_mounter, MountedServer, RecursiveMounter

async def test_persistence():
    brain_path = Path(os.environ["NUCLEAR_BRAIN_PATH"])
    mounter = get_mounter(brain_path)
    
    print("--- 1. Mount Dummy Server ---")
    # We use 'cat' as a dummy command that just stays running
    result = await mounter.mount("dummy-server", "cat", [])
    print(result)
    
    print("\n--- 2. Check Persistence File ---")
    mounts_file = brain_path / "ledger" / "mounts.json"
    if mounts_file.exists():
        content = mounts_file.read_text()
        print(f"File content: {content}")
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["name"] == "dummy-server"
        print("✅ Persistence Verified: Server saved to disk")
    else:
        print("❌ Persistence Failed: File not found")
        return

    print("\n--- 3. Unmount Server ---")
    server_id = data[0]["id"]
    result = await mounter.unmount(server_id)
    print(result)
    
    print("\n--- 4. Verify Cleanup ---")
    content = mounts_file.read_text()
    data = json.loads(content)
    assert len(data) == 0
    print("✅ Cleanup Verified: Server removed from disk")

if __name__ == "__main__":
    # Ensure env var is set
    if "NUCLEAR_BRAIN_PATH" not in os.environ:
        os.environ["NUCLEAR_BRAIN_PATH"] = "/Users/lokeshgarg/.brain"
    
    asyncio.run(test_persistence())
