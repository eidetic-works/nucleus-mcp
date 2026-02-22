#!/usr/bin/env python3
"""
Build Script: The Dark Wheel (Artifact A)
==========================================
Full source code with all tiers (0-2).
Includes Poison Pill for remote kill capability.

Usage:
    python scripts/build_dark_wheel.py

Output:
    dist/dark/mcp_server_nucleus-0.6.0-py3-none-any.whl
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist" / "dark"
BUILD_DIR = PROJECT_ROOT / "build_dark"

# Poison Pill Gist URL (controlled by us)
POISON_PILL_GIST = "https://gist.githubusercontent.com/nucleusos/beta-killswitch/raw/status.txt"

POISON_PILL_CODE = '''
# =============================================================================
# DARK WHEEL POISON PILL - Remote Kill Switch
# =============================================================================
# This code is ONLY present in the Dark Wheel build.
# If the Gist returns anything other than "ACTIVE", the import fails.

import urllib.request
import os

def _verify_beta_status():
    """Check if Dark Wheel is still authorized."""
    if os.environ.get("NUCLEUS_SKIP_BETA_CHECK") == "1":
        return  # Allow local dev override
    
    try:
        GIST_URL = "{gist_url}"
        with urllib.request.urlopen(GIST_URL, timeout=3) as response:
            status = response.read().decode().strip()
            if status != "ACTIVE":
                raise ImportError(
                    "Nucleus Beta has expired. Please upgrade to the stable release: "
                    "pip install mcp-server-nucleus"
                )
    except urllib.error.URLError:
        pass  # Network error - allow offline usage

_verify_beta_status()
# =============================================================================
'''.format(gist_url=POISON_PILL_GIST)


def clean_build():
    """Clean previous build artifacts."""
    print("[1/5] Cleaning previous build...")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def copy_source():
    """Copy full source to build directory."""
    print("[2/5] Copying full source (all tiers)...")
    build_src = BUILD_DIR / "src"
    shutil.copytree(SRC_DIR, build_src)
    
    # Copy other required files
    for f in ["pyproject.toml", "README.md", "LICENSE"]:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy(src, BUILD_DIR / f)


def inject_poison_pill():
    """Inject the Poison Pill into __init__.py."""
    print("[3/5] Injecting Poison Pill (remote kill switch)...")
    init_file = BUILD_DIR / "src" / "mcp_server_nucleus" / "__init__.py"
    
    with open(init_file, "r") as f:
        content = f.read()
    
    # Insert after the first docstring/imports
    lines = content.split("\n")
    insert_index = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_index = i
            break
    
    # Insert poison pill before first import
    new_content = "\n".join(lines[:insert_index]) + "\n" + POISON_PILL_CODE + "\n" + "\n".join(lines[insert_index:])
    
    with open(init_file, "w") as f:
        f.write(new_content)
    
    print("    ✅ Poison Pill injected")


def build_wheel():
    """Build the wheel using hatch."""
    print("[4/5] Building Dark Wheel...")
    
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST_DIR)],
        cwd=BUILD_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"    ❌ Build failed: {result.stderr}")
        sys.exit(1)
    
    print("    ✅ Dark Wheel built successfully")


def verify_full_content():
    """Verify the wheel contains all logic files."""
    print("[5/5] Verifying full content...")
    
    wheel_files = list(DIST_DIR.glob("*.whl"))
    if not wheel_files:
        print("    ❌ No wheel found!")
        sys.exit(1)
    
    wheel = wheel_files[0]
    
    # Check for required files
    required = ["federation.py", "autopilot.py", "orchestrator.py", "mounter.py"]
    
    result = subprocess.run(
        ["unzip", "-l", str(wheel)],
        capture_output=True,
        text=True
    )
    
    missing = []
    for req in required:
        if req not in result.stdout:
            missing.append(req)
    
    if missing:
        print(f"    ❌ Missing required files: {missing}")
        sys.exit(1)
    
    print(f"    ✅ All logic files present")
    print(f"\n🌑 DARK WHEEL READY: {wheel}")
    print(f"\nUpload to private index:")
    print(f"    twine upload --repository-url https://pypi.nucleusos.dev/simple/ {wheel}")


def main():
    print("=" * 60)
    print("BUILDING: THE DARK WHEEL (Full Source + Poison Pill)")
    print("=" * 60)
    print()
    
    clean_build()
    copy_source()
    inject_poison_pill()
    build_wheel()
    verify_full_content()
    
    print()
    print("=" * 60)
    print("🌑 DARK WHEEL BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
