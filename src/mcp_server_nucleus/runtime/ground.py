"""
GROUND — Execution verification that goes outside the formal system.

Dr. Mann = Gödel. The system can't verify itself from within.
GROUND goes outside — execution, reality, the tesseract.

This adapter wraps scripts/execution_verifier.py (the engine) and makes
it callable from anywhere: MCP tools, CLI, CI, any ring.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def detect_project_root(start: Path = None) -> Path:
    """Walk up from start looking for .git, pyproject.toml, or package.json."""
    p = (start or Path.cwd()).resolve()
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return d
        if (d / "pyproject.toml").exists():
            return d
        if (d / "package.json").exists():
            return d
    return p  # fallback to start


def detect_python(project_root: Path) -> str:
    """Find the project's Python interpreter."""
    candidates = [
        project_root / ".venv" / "bin" / "python",
        project_root / "venv" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",  # Windows
    ]
    # Check VIRTUAL_ENV env var
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidates.insert(0, Path(venv) / "bin" / "python")

    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable  # fallback


def _import_engine():
    """Import execution_verifier — now lives in the same package."""
    from .execution_verifier import verify_execution, build_calibration_dpo
    return verify_execution, build_calibration_dpo


def _get_git_diff(project_root: Path, pre_head: str = None) -> str:
    """Get git diff text for changed files."""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_root),
        )
        return r.stdout
    except Exception:
        return ""


def run_ground(project_root: str = None, python_path: str = None,
               tiers: list = None, timeout_s: int = 30,
               pre_head: str = None) -> dict:
    """Run GROUND verification. Returns a receipt.

    Auto-detects project root and Python interpreter if not provided.
    """
    # Resolve context
    root = Path(project_root) if project_root else detect_project_root()
    python = python_path or detect_python(root)
    tier_list = tiers if tiers is not None else [0, 1, 2, 3]

    # Import engine
    verify_execution, _ = _import_engine()

    # Get git diff
    diff_text = _get_git_diff(root, pre_head)

    # Build config
    config = {
        "execution_verification_timeout_s": timeout_s,
        "execution_verification_tiers": tier_list,
        "python_path": python,
    }

    # Run verification
    result = verify_execution(diff_text, pre_head or "", config, root)

    # Wrap as receipt
    result["project_root"] = str(root)
    result["python_used"] = python
    result["timestamp"] = datetime.now().isoformat()
    result["ground_version"] = "1.0.0"

    return result
