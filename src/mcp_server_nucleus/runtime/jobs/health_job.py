"""Wraps scripts/nucleus_health_check.py — periodic health metrics."""

import asyncio
import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict

logger = logging.getLogger("NucleusJobs.health")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def scan_relay_queue_depth() -> Dict[str, int]:
    """Walk relay dirs, count unread messages per recipient bucket, emit gauges.

    Walks .brain/relay/{bucket}/*.json and counts files where read==False.
    Emits set_gauge("nucleus_relay_queue_depth", count, {"recipient": bucket})
    for each bucket found.

    Returns:
        Dict mapping recipient bucket name to unread message count.
    """
    from mcp_server_nucleus.runtime.common import get_brain_path
    from mcp_server_nucleus.runtime.prometheus import set_relay_queue_depth

    relay_root = get_brain_path() / "relay"
    depths: Dict[str, int] = {}

    if not relay_root.exists():
        logger.debug("scan_relay_queue_depth: relay dir absent, nothing to scan")
        return depths

    for bucket_dir in relay_root.iterdir():
        if not bucket_dir.is_dir():
            continue
        bucket = bucket_dir.name
        unread = 0
        for msg_file in bucket_dir.glob("*.json"):
            try:
                import json
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                if not data.get("read", False):
                    unread += 1
            except Exception as exc:
                logger.debug("scan_relay_queue_depth: skip %s: %s", msg_file.name, exc)
        depths[bucket] = unread
        set_relay_queue_depth(unread, bucket)
        logger.debug("relay queue depth: bucket=%s unread=%d", bucket, unread)

    return depths


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
