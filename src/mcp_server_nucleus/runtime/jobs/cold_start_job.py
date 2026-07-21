"""Weekly scheduled job for the cold-start acceptance endpoint instrument.

Authority: docs/PRINCIPAL.md:71-74 (G1 criterion 2). Wraps
``cold_start_instrument.run_cold_start_instrument`` for the NucleusScheduler
daemon tick loop.
"""

import json
import logging

logger = logging.getLogger("NucleusJobs.cold_start")


async def run_cold_start_job() -> dict:
    """Run the cold-start instrument and return the verdict."""
    try:
        from mcp_server_nucleus.runtime.cold_start_instrument import (
            run_cold_start_instrument,
        )
        result = run_cold_start_instrument()
        if result.get("verdict") != "PASS":
            logger.error("cold_start_job FAIL: %s", json.dumps(result))
        else:
            logger.info(
                "cold_start_job PASS: run_id=%s wall=%.3fs recalled=%r",
                result.get("run_id"),
                result.get("wall_time_seconds"),
                result.get("recalled_value"),
            )
        return result
    except Exception as e:
        logger.error("cold_start_job crashed: %s", e)
        return {"ok": False, "error": str(e), "verdict": "FAIL"}
