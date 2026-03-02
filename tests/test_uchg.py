import os
from pathlib import Path
import subprocess

p = Path("test2.txt")
p.write_text("initial")
subprocess.run(["chflags", "uchg", str(p)])

try:
    p.unlink()
    print("unlink succeeded")
except Exception as e:
    print(f"unlink failed: {e}")

try:
    Path("test3.txt").write_text("rogue")
    os.rename("test3.txt", "test2.txt")
    print("rename succeeded")
except Exception as e:
    print(f"rename failed: {e}")

subprocess.run(["chflags", "nouchg", str(p)])
try:
    p.unlink()
except:
    pass
