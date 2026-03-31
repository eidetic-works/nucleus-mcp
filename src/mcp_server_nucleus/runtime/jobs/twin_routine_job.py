"""Wraps scripts/twin_routine.py — morning/evening lifecycle."""

import asyncio
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger("NucleusJobs.twin_routine")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def _load_module():
    path = PROJECT_ROOT / "scripts" / "twin_routine.py"
    if not path.exists():
        raise FileNotFoundError(f"twin_routine.py not found: {path}")
    spec = importlib.util.spec_from_file_location("twin_routine", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def run_morning() -> dict:
    try:
        mod = _load_module()
        await asyncio.to_thread(mod.run_morning_routine)
        return {"ok": True}
    except SystemExit as e:
        logger.warning(f"Morning routine script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Morning routine failed: {e}")
        return {"ok": False, "error": str(e)}


async def run_evening() -> dict:
    try:
        mod = _load_module()
        await asyncio.to_thread(mod.run_evening_routine)
        return {"ok": True}
    except SystemExit as e:
        logger.warning(f"Evening routine script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Evening routine failed: {e}")
        return {"ok": False, "error": str(e)}
