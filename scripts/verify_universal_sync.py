import os
import time
import shutil
import sys
from mcp_server_nucleus.hypervisor.locker import Locker

def verify_sync():
    locker = Locker()
    test_file = "universal_sync_test.lock"
    
    # Ensure clean state
    if os.path.exists(test_file):
        locker.unlock(test_file)
        os.remove(test_file)
        
    with open(test_file, "w") as f:
        f.write("Universal Sync Test Artifact")
        
    # Agent A (This Script) Locks the file
    print(f"\nLocked by: verify_universal_sync.py (PID: {os.getpid()})")
    print(f"Target: {os.path.abspath(test_file)}")
    
    metadata = {
        "reason": "Demonstrating Universal Sync",
        "agent_id": "verify-script",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    
    if locker.lock(test_file, metadata=metadata):
        print("\n✅ LOCK ACQUIRED with Metadata.")
        print("---------------------------------------------------")
        print("🔍 ACTION REQUIRED: Verify from your Terminal (Agent B)")
        print(f"Run:  xattr -l {test_file}")
        print("---------------------------------------------------")
        print("You should see:")
        print("nucleus.lock.reason: Demonstrating Universal Sync")
        print("nucleus.lock.agent_id: verify-script")
        print("---------------------------------------------------")
        
        # Keep alive for verification details
        print("\n⏳ Sleeping for 30 seconds to allow verification...")
        time.sleep(30)
        # try:
        #     input("\nPress ENTER after you have verified the xattrs in your terminal... ")
        # except KeyboardInterrupt:
        #     pass
            
        print("\nCleaning up...")
        locker.unlock(test_file)
        os.remove(test_file)
        print("✅ Cleanup Complete.")
    else:
        print("❌ Failed to acquire lock.")

if __name__ == "__main__":
    # Ensure we can import mcp_server_nucleus
    sys.path.append(os.path.abspath("src"))
    if shutil.which("xattr"):
        verify_sync()
    else:
        print("Skipping test: xattr not found")
