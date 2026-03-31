"""Wraps scripts/orchestrator.py — event scanning and agent triggers."""

import asyncio
import importlib.util
import logging
from pathlib import Path

logger = logging.getLogger("NucleusJobs.orchestrator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


async def run_orchestrator() -> dict:
    """Run the event orchestrator pipeline."""
    try:
        path = PROJECT_ROOT / "scripts" / "orchestrator.py"
        if not path.exists():
            return {"ok": False, "error": "orchestrator.py not found"}
        spec = importlib.util.spec_from_file_location("scripts_orchestrator", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = await mod.run_orchestrator()
        return {"ok": True, "result": result}
    except SystemExit as e:
        logger.warning(f"Orchestrator script exited with code {e.code}")
        return {"ok": False, "error": f"script sys.exit({e.code})"}
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}")
        return {"ok": False, "error": str(e)}
