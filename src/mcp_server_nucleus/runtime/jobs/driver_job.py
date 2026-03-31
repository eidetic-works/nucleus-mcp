"""Wraps scripts/third_brother_driver.py — the compound intelligence loop."""

import asyncio
import importlib.util
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("NucleusJobs.driver")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def _load_driver():
    """Import the driver module without modifying global sys.path."""
    driver_path = PROJECT_ROOT / "scripts" / "third_brother_driver.py"
    if not driver_path.exists():
        raise FileNotFoundError(f"Driver not found: {driver_path}")
    spec = importlib.util.spec_from_file_location("third_brother_driver", driver_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_requirements() -> tuple:
    """Check if driver can run. Returns (ok, message)."""
    stop_file = PROJECT_ROOT / "scripts" / "stop"
    if stop_file.exists():
        return False, "stop file present"
    try:
        subprocess.run(["ollama", "list"], capture_output=True, timeout=5, check=True)
    except Exception:
        return True, "degraded: ollama unavailable, training captures will be limited"
    return True, "ok"


async def run_compound(branch: str = "tb/nucleus-work", rounds: int = 5) -> dict:
    """Run compound mode: real tasks → sparring → export."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    try:
        driver = _load_driver()
        result = await asyncio.to_thread(driver.run_compound_mode, branch, rounds)
        return {"ok": True, "result": "compound_complete"}
    except SystemExit as e:
        logger.warning(f"Compound mode script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Compound mode failed: {e}")
        return {"ok": False, "error": str(e)}


async def run_driver_session(mode: str = "autonomous", branch: str = "tb/nucleus-work",
                             max_tasks: int = 0) -> dict:
    """Run driver in direct mode."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    try:
        driver = _load_driver()
        result = await asyncio.to_thread(driver.run_driver, "", mode=mode,
                                         branch=branch, max_tasks=max_tasks)
        return {"ok": True, "result": "driver_complete"}
    except SystemExit as e:
        logger.warning(f"Driver session script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Driver session failed: {e}")
        return {"ok": False, "error": str(e)}
