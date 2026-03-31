"""Wraps scripts/analytics_dashboard.py — GA4 analytics report."""

import asyncio
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("NucleusJobs.analytics")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def check_requirements() -> tuple:
    """Check if GA4 credentials are available."""
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        cred_path = PROJECT_ROOT / "key.json"
        if cred_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)
        else:
            return False, "no GA4 credentials"
    return True, "ok"


async def run_analytics() -> dict:
    """Run the GA4 analytics dashboard report via subprocess."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    try:
        script = PROJECT_ROOT / "scripts" / "analytics_dashboard.py"
        if not script.exists():
            return {"ok": False, "error": "analytics_dashboard.py not found"}

        proc = await asyncio.to_thread(
            subprocess.run,
            ["python3", str(script), "--json"],
            capture_output=True, text=True, timeout=300,
            cwd=str(PROJECT_ROOT),
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr[:500]}
        return {"ok": True}
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        return {"ok": False, "error": str(e)}
