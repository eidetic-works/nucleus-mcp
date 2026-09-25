import os
import sys
from pathlib import Path
import subprocess
import pytest

@pytest.mark.skipif(sys.platform != "darwin", reason="chflags is macOS only")
def test_uchg_functionality(tmp_path):
    p = tmp_path / "test_uchg_temp.txt"
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
            rogue = tmp_path / "test3.txt"
            rogue.write_text("rogue")
            os.rename(str(rogue), str(p))
            pytest.fail("Rename should have failed on a locked file")
        except Exception:
            pass
    finally:
        # Unlock and cleanup
        subprocess.run(["chflags", "nouchg", str(p)], check=False)
        if p.exists():
            p.unlink()
        rogue = tmp_path / "test3.txt"
        if rogue.exists():
            rogue.unlink()
