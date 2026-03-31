"""Brain backup — replaces scripts/backup-brain.sh in Python."""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("NucleusJobs.backup")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
BRAIN_PATH = PROJECT_ROOT / ".brain"
MAX_BACKUPS = 3


async def run_backup(tag: str = "weekly") -> dict:
    """Create a timestamped brain backup. Prune old ones."""
    try:
        def _backup():
            if not BRAIN_PATH.exists():
                return {"ok": False, "error": ".brain not found"}

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f".brain-backup-{tag}-{stamp}"
            backup_path = PROJECT_ROOT / backup_name

            # Copy brain, ignore errors on special files
            shutil.copytree(
                BRAIN_PATH, backup_path,
                ignore=shutil.ignore_patterns("*.lock", "__pycache__"),
                dirs_exist_ok=False,
            )
            logger.info(f"Brain backed up to {backup_name}")

            # Prune old backups of same tag
            pattern = f".brain-backup-{tag}-*"
            backups = sorted(PROJECT_ROOT.glob(pattern))
            if len(backups) > MAX_BACKUPS:
                for old in backups[:-MAX_BACKUPS]:
                    shutil.rmtree(old, ignore_errors=True)
                    logger.info(f"Pruned old backup: {old.name}")

            return {"ok": True, "backup": backup_name, "pruned": max(0, len(backups) - MAX_BACKUPS)}

        return await asyncio.to_thread(_backup)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"ok": False, "error": str(e)}
