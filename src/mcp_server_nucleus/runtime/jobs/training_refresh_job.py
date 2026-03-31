"""Wraps scripts/daily_data_refresh.py — training ETL pipeline."""

import asyncio
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger("NucleusJobs.training")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def _load_module():
    path = PROJECT_ROOT / "scripts" / "daily_data_refresh.py"
    if not path.exists():
        raise FileNotFoundError(f"daily_data_refresh not found: {path}")
    spec = importlib.util.spec_from_file_location("daily_data_refresh", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def run_refresh(index: bool = True) -> dict:
    """Run full training data refresh pipeline."""
    try:
        mod = _load_module()

        def _do_refresh():
            indexed = False
            if index:
                indexed = mod.refresh_rag_index()
            stats = mod.run_pipeline()
            mod.run_export_combined()
            readiness = mod.check_retrain_readiness()
            return {"stats": stats, "indexed": indexed, "readiness": readiness}

        result = await asyncio.to_thread(_do_refresh)
        return {"ok": True, **result}
    except SystemExit as e:
        logger.warning(f"Training refresh script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Training refresh failed: {e}")
        return {"ok": False, "error": str(e)}


async def check_readiness() -> dict:
    """Just check retrain readiness without running the full pipeline."""
    try:
        mod = _load_module()
        readiness = await asyncio.to_thread(mod.check_retrain_readiness)
        return {"ok": True, "readiness": readiness}
    except SystemExit as e:
        logger.warning(f"Readiness check script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ok": False, "error": str(e)}
