"""Weekly scheduled job for the seeded cross-project block instrument.

Authority: docs/PRINCIPAL.md:67-73,149 (G1 workstream 2; named seeded-block
instrument). Wraps ``seeded_block_instrument.run_seeded_block_instrument`` for
the NucleusScheduler daemon tick loop.
"""

import json
import logging

logger = logging.getLogger("NucleusJobs.seeded_block")


async def run_seeded_block_job() -> dict:
    """Run the weekly seeded-block instrument and return the verdict."""
    try:
        from mcp_server_nucleus.runtime.seeded_block_instrument import (
            run_seeded_block_instrument,
        )
        result = run_seeded_block_instrument()
        if result.get("verdict") != "PASS":
            logger.error("seeded_block_job FAIL: %s", json.dumps(result))
        else:
            logger.info("seeded_block_job PASS: run_id=%s", result.get("run_id"))
        return result
    except Exception as e:
        logger.error("seeded_block_job crashed: %s", e)
        return {"ok": False, "error": str(e), "verdict": "FAIL"}
