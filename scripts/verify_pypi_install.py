#!/usr/bin/env python3
import os
import subprocess
import shutil
import tempfile
import sys
import argparse

def run_cmd(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
    return result

def verify_install(source=None):
    """
    source: path to .whl file or 'pypi'
    """
    temp_dir = tempfile.mkdtemp(prefix="nucleus_verify_")
    print(f"🚀 Created cleanroom: {temp_dir}")

    try:
        # 1. Create venv
        venv_dir = os.path.join(temp_dir, ".venv")
        run_cmd([sys.executable, "-m", "venv", venv_dir])
        
        # Get venv python path
        if os.name == 'nt':
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
            pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            python_exe = os.path.join(venv_dir, "bin", "python")
            pip_exe = os.path.join(venv_dir, "bin", "pip")

        # 2. Install package
        print(f"📦 Installing from {source}...")
        if source == "pypi":
            run_cmd([pip_exe, "install", "nucleus-mcp"])
        elif source.endswith(".whl"):
            run_cmd([pip_exe, "install", source])
        else:
            # Assume local directory
            run_cmd([pip_exe, "install", source])

        # 3. Verify Importability
        print("🔍 Verifying importability...")
        res = run_cmd([python_exe, "-c", "import mcp_server_nucleus; print('✅ Import Success')"])
        if "✅ Import Success" not in res.stdout:
            print("❌ Import failed")
            return False

        # 4. Verify Server Runtime Discovery
        print("🔍 Verifying server runtime...")
        res = run_cmd([python_exe, "-m", "mcp_server_nucleus.runtime.stdio_server", "--help"])
        if "usage:" in res.stdout.lower() or "options:" in res.stdout.lower():
            print("✅ Server runtime verified")
        else:
            print("❌ Server runtime failure")
            return False

        print("\n✨ Nucleus Installation Verified Successfully! ✨")
        return True

    finally:
        print(f"🧹 Cleaning up: {temp_dir}")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Nucleus installation in a cleanroom.")
    parser.add_argument("--source", default=".", help="Source to install from (path to .whl, directory, or 'pypi')")
    args = parser.parse_args()

    success = verify_install(args.source)
    sys.exit(0 if success else 1)
