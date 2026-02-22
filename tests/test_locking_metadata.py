import os
import time
import shutil
import shutil
# import pytest
from mcp_server_nucleus.hypervisor.locker import Locker

def test_lock_metadata():
    locker = Locker()
    test_file = "test_metadata.lock"
    
    # ensure clean state
    if os.path.exists(test_file):
        locker.unlock(test_file)
        os.remove(test_file)
        
    with open(test_file, "w") as f:
        f.write("content")
        
    # Test Metadata
    metadata = {
        "reason": "Unit Testing",
        "agent_id": "test-agent-001",
        "custom_field": "custom_value"
    }
    
    print(f"Locking {test_file} with metadata...")
    success = locker.lock(test_file, metadata=metadata)
    assert success, "Failed to lock file"
    assert locker.is_locked(test_file), "File should be locked"
    
    # Read Metadata
    print("Reading metadata...")
    read_meta = locker.get_metadata(test_file)
    print(f"Read Metadata: {read_meta}")
    
    assert read_meta.get("reason") == "Unit Testing"
    assert read_meta.get("agent_id") == "test-agent-001"
    assert read_meta.get("custom_field") == "custom_value"
    assert "timestamp" in read_meta
    
    # Cleanup
    locker.unlock(test_file)
    os.remove(test_file)
    print("Test Passed!")

if __name__ == "__main__":
    if shutil.which("xattr"):
        test_lock_metadata()
    else:
        print("Skipping test: xattr not found")
