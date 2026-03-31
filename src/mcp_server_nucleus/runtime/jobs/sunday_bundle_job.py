"""Sunday bundle — runs auto_strategy_sync + weekly_summary."""

import asyncio
import importlib.util
import logging
import socket
from pathlib import Path

logger = logging.getLogger("NucleusJobs.sunday_bundle")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def check_requirements() -> tuple:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True, "ok"
    except OSError:
        return False, "no network"


async def run_sunday_bundle() -> dict:
    """Run weekly strategy sync and summary."""
    ok, msg = check_requirements()
    if not ok:
        return {"ok": False, "error": msg}

    results = {}
    for script_name in ("auto_strategy_sync", "weekly_summary"):
        try:
            path = PROJECT_ROOT / "scripts" / f"{script_name}.py"
            if not path.exists():
                results[script_name] = "not found"
                continue
            spec = importlib.util.spec_from_file_location(script_name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            await asyncio.to_thread(mod.main)
            results[script_name] = "ok"
        except SystemExit as e:
            logger.warning(f"{script_name} script exited with code {e.code}")
            results[script_name] = f"script sys.exit({e.code})"
        except Exception as e:
            logger.error(f"{script_name} failed: {e}")
            results[script_name] = str(e)

    all_ok = all(v == "ok" for v in results.values())
    return {"ok": all_ok, "results": results}
