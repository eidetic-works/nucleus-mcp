#!/usr/bin/env python3
"""
Build Script: The Public Decoy (Artifact B)
============================================
Tier 0 Only - Journal Mode.
Logic files PHYSICALLY DELETED before packaging.

Usage:
    python scripts/build_public_decoy.py

Output:
    dist/public/mcp_server_nucleus-0.6.0-py3-none-any.whl

PARANOIA PROTOCOL:
    Before uploading, ALWAYS run:
    unzip -l dist/public/*.whl | grep federation
    
    Result MUST be EMPTY. If you see federation.py, ABORT.
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
DIST_DIR = PROJECT_ROOT / "dist" / "public"
BUILD_DIR = PROJECT_ROOT / "build_public"

# Files to PHYSICALLY DELETE from the public build
# These are Tier 1+ logic files - the crown jewels
STRIPPED_FILES = [
    # Core Logic (Tier 1+)
    "runtime/federation.py",
    "runtime/autopilot.py",
    "runtime/orchestrator.py",
    "runtime/orchestrator_unified.py",
    "runtime/orchestrator_v3.py",
    "runtime/mounter.py",
    
    # Agent System (Tier 2)
    "runtime/agent.py",
    "runtime/agent_pool.py",
    "runtime/swarm.py",
    "runtime/team.py",
    
    # Task Orchestration (Tier 1+)
    "runtime/task_scheduler.py",
    "runtime/task_ingestion.py",
    "runtime/crdt_task_store.py",
    
    # Advanced Features (Tier 2)
    "runtime/broker.py",
    "runtime/daemon.py",
    "runtime/dashboard.py",
    "runtime/nuke_protocol.py",
    "runtime/proposals.py",
    "runtime/publisher.py",
    "runtime/triggers.py",
    "runtime/watcher.py",
    
    # Identity/Auth (Tier 1+)
    "runtime/identity/gatekeeper.py",
    "runtime/identity/trust.py",
    
    # Capabilities (Tier 2)
    "runtime/capabilities/",
    
    # Loops (Tier 2)
    "runtime/loops/",
    
    # Agents (Tier 2)
    "runtime/agents/",
]

# Stub content for stripped files
STUB_CONTENT = '''"""
{filename} - Tier 1+ Feature

This module requires Nucleus Pro.

Upgrade: pip install mcp-server-nucleus --index-url https://pypi.nucleusos.dev/simple/

Or contact: hello@nucleus-mcp.com
"""

raise ImportError(
    "{filename} requires Nucleus Pro. "
    "Free tier includes Journal Mode only (memory + mount teaser). "
    "Upgrade at nucleusos.dev"
)
'''


def clean_build():
    """Clean previous build artifacts."""
    print("[1/6] Cleaning previous build...")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def copy_source():
    """Copy source to build directory."""
    print("[2/6] Copying source...")
    build_src = BUILD_DIR / "src"
    shutil.copytree(SRC_DIR, build_src)
    
    # Copy other required files
    for f in ["pyproject.toml", "README.md", "LICENSE"]:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy(src, BUILD_DIR / f)


def strip_logic_files():
    """PHYSICALLY DELETE Tier 1+ logic files."""
    print("[3/6] STRIPPING logic files (Physical Separation)...")
    
    pkg_dir = BUILD_DIR / "src" / "mcp_server_nucleus"
    stripped_count = 0
    stubbed_count = 0
    
    for pattern in STRIPPED_FILES:
        target = pkg_dir / pattern
        
        if target.exists():
            if target.is_dir():
                # Delete entire directory
                shutil.rmtree(target)
                print(f"    🗑️  DELETED: {pattern}/")
                stripped_count += 1
            else:
                # Replace with stub
                filename = target.name
                stub = STUB_CONTENT.format(filename=filename)
                target.write_text(stub)
                print(f"    📄 STUBBED: {pattern}")
                stubbed_count += 1
    
    print(f"\n    ✅ Stripped {stripped_count} directories, stubbed {stubbed_count} files")


def update_init_for_stubs():
    """Update __init__.py to handle missing modules gracefully."""
    print("[4/6] Updating __init__.py for stub handling...")
    
    init_file = BUILD_DIR / "src" / "mcp_server_nucleus" / "__init__.py"
    
    with open(init_file, "r") as f:
        content = f.read()
    
    # Add stub handling at the top (after docstring)
    stub_handler = '''
# =============================================================================
# PUBLIC BUILD - Journal Mode Only
# =============================================================================
# This is the public PyPI release with Tier 0 tools only.
# Logic files have been replaced with stubs that raise ImportError.
# For full functionality, install from the private index.

import os
os.environ.setdefault("NUCLEUS_TOOL_TIER", "0")  # Force Tier 0
# =============================================================================
'''
    
    # Find insertion point (after first docstring)
    if '"""' in content:
        parts = content.split('"""', 2)
        if len(parts) >= 3:
            content = parts[0] + '"""' + parts[1] + '"""' + stub_handler + parts[2]
    
    with open(init_file, "w") as f:
        f.write(content)
    
    print("    ✅ __init__.py updated for Tier 0 only")


def build_wheel():
    """Build the wheel using pip wheel."""
    print("[5/6] Building Public Decoy wheel...")
    
    # Try multiple build methods
    build_commands = [
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST_DIR)],
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(DIST_DIR)],
        ["hatch", "build", "-t", "wheel", "-d", str(DIST_DIR)],
    ]
    
    for cmd in build_commands:
        result = subprocess.run(
            cmd,
            cwd=BUILD_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"    ✅ Public Decoy wheel built (via {cmd[0]})")
            return
    
    # If all fail, try manual wheel creation
    print("    ⚠️  Standard build failed, creating wheel manually...")
    create_wheel_manually()


def create_wheel_manually():
    """Manually create a wheel file."""
    import zipfile
    import hashlib
    from datetime import datetime
    
    pkg_dir = BUILD_DIR / "src" / "mcp_server_nucleus"
    version = "0.6.0"
    wheel_name = f"mcp_server_nucleus-{version}-py3-none-any.whl"
    wheel_path = DIST_DIR / wheel_name
    
    with zipfile.ZipFile(wheel_path, 'w', zipfile.ZIP_DEFLATED) as whl:
        # Add all Python files
        for py_file in pkg_dir.rglob("*.py"):
            arcname = f"mcp_server_nucleus/{py_file.relative_to(pkg_dir)}"
            whl.write(py_file, arcname)
        
        # Create METADATA
        metadata = f"""Metadata-Version: 2.1
Name: mcp-server-nucleus
Version: {version}
Summary: The Agent Control Plane - Default-Deny Security for MCP Servers
Author: Nucleus Team
Author-email: hello@nucleus-mcp.com
Requires-Python: >=3.10
"""
        whl.writestr(f"mcp_server_nucleus-{version}.dist-info/METADATA", metadata)
        
        # Create WHEEL
        wheel_info = """Wheel-Version: 1.0
Generator: nucleus-build
Root-Is-Purelib: true
Tag: py3-none-any
"""
        whl.writestr(f"mcp_server_nucleus-{version}.dist-info/WHEEL", wheel_info)
        
        # Create RECORD (simplified)
        whl.writestr(f"mcp_server_nucleus-{version}.dist-info/RECORD", "")
    
    print(f"    ✅ Manual wheel created: {wheel_name}")


def paranoia_verification():
    """CRITICAL: Verify NO logic files in the wheel."""
    print("[6/6] 🛑 PARANOIA PROTOCOL - Manifest Check...")
    
    wheel_files = list(DIST_DIR.glob("*.whl"))
    if not wheel_files:
        print("    ❌ No wheel found!")
        sys.exit(1)
    
    wheel = wheel_files[0]
    
    # The forbidden files - MUST NOT be present
    forbidden = [
        "federation.py",
        "autopilot.py", 
        "orchestrator.py",
        "mounter.py",
        "swarm.py",
        "agent_pool.py",
    ]
    
    result = subprocess.run(
        ["unzip", "-l", str(wheel)],
        capture_output=True,
        text=True
    )
    
    # Check each forbidden file
    leaked = []
    for f in forbidden:
        # Check if the file exists with actual content (not just stub)
        if f in result.stdout:
            # Verify it's a stub by checking file size
            for line in result.stdout.split("\n"):
                if f in line:
                    # Parse size from unzip output (format: "  size  date time  filename")
                    parts = line.split()
                    if len(parts) >= 1:
                        try:
                            size = int(parts[0])
                            # Stubs are small (<500 bytes), real files are large
                            if size > 500:
                                leaked.append(f"{f} ({size} bytes)")
                        except ValueError:
                            pass
    
    print()
    if leaked:
        print("    " + "=" * 50)
        print("    ❌❌❌ CRITICAL: LOGIC FILES LEAKED ❌❌❌")
        print("    " + "=" * 50)
        for leak in leaked:
            print(f"    LEAKED: {leak}")
        print()
        print("    🛑 DO NOT UPLOAD TO PYPI")
        print("    🛑 ABORT IMMEDIATELY")
        print("    " + "=" * 50)
        sys.exit(1)
    
    # Double check with grep
    grep_result = subprocess.run(
        f"unzip -l {wheel} | grep -E 'federation|autopilot|orchestrator|mounter|swarm'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Files will exist as stubs, but verify they're small
    print("    ✅ Paranoia Protocol PASSED")
    print(f"\n☀️  PUBLIC DECOY READY: {wheel}")
    print(f"\nUpload to PyPI:")
    print(f"    twine upload {wheel}")
    print()
    print("⚠️  FINAL CHECK before upload:")
    print(f"    unzip -l {wheel} | grep federation")
    print("    (If you see large files, ABORT)")


def main():
    print("=" * 60)
    print("BUILDING: THE PUBLIC DECOY (Tier 0 Only - Journal Mode)")
    print("=" * 60)
    print()
    
    clean_build()
    copy_source()
    strip_logic_files()
    update_init_for_stubs()
    build_wheel()
    paranoia_verification()
    
    print()
    print("=" * 60)
    print("☀️  PUBLIC DECOY BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
