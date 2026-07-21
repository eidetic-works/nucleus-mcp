"""Weekly scheduled job for the self-digest instrument.

Authority: docs/PRINCIPAL.md:86,129,149 (G1 criterion 5). Wraps
``self_digest_instrument.run_self_digest_instrument`` for the
NucleusScheduler daemon tick loop.

Failure handling: on any exception the job returns ``{"ok": False,
"verdict": "FAIL"}`` so the daemon's ``_run_job_safe`` calls
``notifier.send`` (failure alerts without counting as a successful firing).
"""

import json
import logging

logger = logging.getLogger("NucleusJobs.self_digest")


async def run_self_digest_job() -> dict:
    """Run the weekly self-digest instrument and return the verdict."""
    try:
        from mcp_server_nucleus.runtime.self_digest_instrument import (
            run_self_digest_instrument,
        )
        result = run_self_digest_instrument()
        if result.get("verdict") != "PASS":
            logger.error("self_digest_job FAIL: %s", json.dumps(result))
        else:
            logger.info(
                "self_digest_job PASS: run_id=%s engrams_in_window=%s relay_total=%s",
                result.get("run_id"),
                (result.get("digest") or {}).get("engrams", {}).get("count_in_window"),
                (result.get("digest") or {}).get("relay", {}).get("total_messages"),
            )
        return result
    except Exception as e:
        logger.error("self_digest_job crashed: %s", e)
        return {"ok": False, "error": str(e), "verdict": "FAIL"}
