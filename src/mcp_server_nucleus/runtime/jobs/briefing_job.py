"""Wraps scripts/telegram_briefing.py — morning Telegram briefing."""

import asyncio
import importlib.util
import logging
import socket
from pathlib import Path

logger = logging.getLogger("NucleusJobs.briefing")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def check_requirements() -> tuple:
    """Check network connectivity."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True, "ok"
    except OSError:
        return False, "no network"


async def run_briefing() -> dict:
    """Send the daily Telegram briefing."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    try:
        path = PROJECT_ROOT / "scripts" / "telegram_briefing.py"
        if not path.exists():
            return {"ok": False, "error": "telegram_briefing.py not found"}
        spec = importlib.util.spec_from_file_location("telegram_briefing", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = await asyncio.to_thread(mod.main)
        return {"ok": True}
    except SystemExit as e:
        logger.warning(f"Briefing script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Briefing failed: {e}")
        return {"ok": False, "error": str(e)}
