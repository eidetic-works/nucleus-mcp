"""Ambient conversation ingestion — processes new Claude Code sessions every 6h."""

import asyncio
import logging

logger = logging.getLogger("NucleusJobs.conversation_ingest")


async def run_conversation_ingest() -> dict:
    """Run incremental conversation ingestion."""
    try:
        from ..conversation_ops import ingest_conversations

        result = await asyncio.to_thread(ingest_conversations, mode="incremental")
        sessions = result.get("sessions_processed", 0)
        turns = result.get("turns_created", 0)
        prefs = result.get("preferences_found", 0)
        chains = result.get("chains_extracted", 0)
        logger.info(
            "Conversation ingest: %d sessions, %d turns, %d prefs, %d chains",
            sessions, turns, prefs, chains,
        )
        return {"ok": True, **result}
    except Exception as e:
        logger.error("Conversation ingest failed: %s", e)
        return {"ok": False, "error": str(e)}
