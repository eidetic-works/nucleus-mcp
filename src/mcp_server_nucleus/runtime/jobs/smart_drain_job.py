"""Smart drain — wraps smart-drain.sh via subprocess."""

import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("NucleusJobs.smart_drain")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def check_requirements() -> tuple:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        if result.returncode != 0:
            return False, "docker daemon not running"
        return True, "ok"
    except Exception:
        return False, "docker unavailable"


async def run_smart_drain() -> dict:
    """Run smart drain if docker is available."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    script = PROJECT_ROOT / "scripts" / "smart-drain.sh"
    if not script.exists():
        return {"ok": False, "error": "smart-drain.sh not found"}

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["bash", str(script)],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        return {"ok": proc.returncode == 0, "output": proc.stdout[:500]}
    except Exception as e:
        logger.error(f"Smart drain failed: {e}")
        return {"ok": False, "error": str(e)}
