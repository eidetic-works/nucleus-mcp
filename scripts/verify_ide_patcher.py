
import os
import shutil
import json
from pathlib import Path
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from mcp_server_nucleus.cli import _patch_mcp_config

def test_patcher():
    test_root = Path(".test_configs_live")
    if test_root.exists():
        shutil.rmtree(test_root)
    test_root.mkdir()
    
    # Setup test cases
    configs = {
        "claude": test_root / "claude.json",
        "cursor": test_root / "cursor.json",
        "windsurf": test_root / "windsurf.json"
    }
    
    test_config = {"command": "test", "args": [], "env": {}}
    
    for name, path in configs.items():
        with open(path, 'w') as f:
            json.dump({"mcpServers": {}}, f)
        
        print(f"Testing {name} patch...")
        success = _patch_mcp_config(path, name, test_config)
        
        if success:
            print(f"  ✅ {name} patch reported success")
            # Verify backup
            backup = path.with_suffix(".json.bak")
            if backup.exists():
                print(f"  ✅ {name} backup created")
            else:
                print(f"  ❌ {name} backup MISSING")
                
            # Verify content
            with open(path, 'r') as f:
                data = json.load(f)
                if "nucleus" in data.get("mcpServers", {}):
                    print(f"  ✅ {name} nucleus config injected")
                else:
                    print(f"  ❌ {name} nucleus config MISSING")
        else:
            print(f"  ❌ {name} patch reported failure")

if __name__ == "__main__":
    test_patcher()
