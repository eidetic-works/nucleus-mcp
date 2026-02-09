
import os
import platform
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.cli import get_claude_config_path, get_cursor_config_path, get_windsurf_config_path

def test_windows_paths():
    print("🪟 Mocking Windows environment...")
    
    # Save original
    orig_system = platform.system
    orig_environ = os.environ.copy()
    
    try:
        # Mock platform.system()
        platform.system = lambda: "Windows"
        os.environ["APPDATA"] = "C:\\Users\\Test\\AppData\\Roaming"
        os.environ["LOCALAPPDATA"] = "C:\\Users\\Test\\AppData\\Local"
        
        print(f"System: {platform.system()}")
        
        claude = get_claude_config_path()
        print(f"Claude: {claude}")
        assert "AppData\\Roaming\\Claude" in str(claude)
        
        cursor = get_cursor_config_path()
        print(f"Cursor: {cursor}")
        assert "AppData\\Roaming\\Cursor" in str(cursor)
        
        windsurf = get_windsurf_config_path()
        print(f"Windsurf: {windsurf}")
        assert "AppData\\Roaming\\Codeium\\windsurf" in str(windsurf)
        
        print("\n✅ Windows path resolution looks CORRECT.")
        
    finally:
        # Restore
        platform.system = orig_system
        os.environ.clear()
        os.environ.update(orig_environ)

if __name__ == "__main__":
    test_windows_paths()
