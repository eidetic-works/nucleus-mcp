"""Wraps scripts/nucleus_health_check.py — periodic health metrics."""

import asyncio
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger("NucleusJobs.health")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


async def run_health_check() -> dict:
    """Collect health metrics and return them."""
    try:
        path = PROJECT_ROOT / "scripts" / "nucleus_health_check.py"
        if not path.exists():
            return {"ok": False, "error": "nucleus_health_check.py not found"}
        spec = importlib.util.spec_from_file_location("nucleus_health_check", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        metrics = await asyncio.to_thread(mod.collect_metrics)
        return {"ok": True, "metrics": metrics}
    except SystemExit as e:
        logger.warning(f"Health check script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"ok": False, "error": str(e)}
