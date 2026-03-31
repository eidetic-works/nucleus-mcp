"""Wraps scripts/meta_optimizer.py — self-improvement every 72h."""

import asyncio
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger("NucleusJobs.meta_optimizer")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


async def run_optimizer() -> dict:
    """Run the meta-optimization cycle."""
    try:
        path = PROJECT_ROOT / "scripts" / "meta_optimizer.py"
        if not path.exists():
            return {"ok": False, "error": "meta_optimizer.py not found"}
        spec = importlib.util.spec_from_file_location("meta_optimizer", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = await asyncio.to_thread(mod.run_meta_optimizer)
        return {"ok": True, "result": result}
    except SystemExit as e:
        logger.warning(f"Meta optimizer script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Meta optimizer failed: {e}")
        return {"ok": False, "error": str(e)}
