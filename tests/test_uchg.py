import os
import sys
from pathlib import Path
import subprocess
import pytest

@pytest.mark.skipif(sys.platform != "darwin", reason="chflags is macOS only")
def test_uchg_functionality():
    p = Path("test_uchg_temp.txt")
    p.write_text("initial")
    
    try:
        # Lock file
        subprocess.run(["chflags", "uchg", str(p)], check=True)
        
        # Test deletion protection
        try:
            p.unlink()
            pytest.fail("Unlink should have failed on a locked file")
        except Exception:
            pass
            
        # Test rename protection
        try:
            Path("test3.txt").write_text("rogue")
            os.rename("test3.txt", str(p))
            pytest.fail("Rename should have failed on a locked file")
        except Exception:
            pass
    finally:
        # Unlock and cleanup
        subprocess.run(["chflags", "nouchg", str(p)], check=False)
        if p.exists():
            p.unlink()
        if Path("test3.txt").exists():
            Path("test3.txt").unlink()
