"""Outbound I/O Subsystem — Idempotent Multi-Channel Posting via Nucleus Primitives.

The missing half of Nucleus's I/O model:
  - Internal I/O: events ✅
  - Memory I/O: engrams ✅
  - Inbound I/O: metrics fetch ✅
  - Outbound I/O: THIS MODULE ✅

Architecture:
  This module is a GATE + LEDGER, not an executor.
  Workhorses (Comet, Antigravity Chrome, scripts, manual) do the actual posting.
  Any workhorse that speaks the check → post → record protocol gets
  idempotent posting for free.

Protocol:
  1. outbound_check(channel, identifier, body)  → READY / SKIP / RETRY
  2. [workhorse posts externally — not our code]
  3. outbound_record(channel, identifier, body, permalink, workhorse)  → recorded
  4. Growth hook auto-fires on "outbound_posted" event → compounds observation

Engram Key Convention:
  outbound_{channel}_{hash}
  - channel: lowercase normalized
  - hash: sha256(channel | identifier | body)[:12]

No new tools. No new scripts. Uses existing engrams, tasks, events.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .common import get_brain_path

logger = logging.getLogger("nucleus.outbound_ops")

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

OUTBOUND_ENGRAM_PREFIX = "outbound_"
OUTBOUND_CONTEXT = "Strategy"
OUTBOUND_INTENSITY = 8  # High — these are execution records


# ═══════════════════════════════════════════════════════════════
# HASH COMPUTATION
# ═══════════════════════════════════════════════════════════════

def _compute_outbound_hash(channel: str, identifier: str, body: str) -> str:
    """Deterministic 12-char hex hash for outbound dedup.

    Hash input: channel|identifier|body (all lowercased, stripped).
    48-bit space (281 trillion values) — collision at ~16M entries.
    """
    normalized = f"{channel.strip().lower()}|{identifier.strip().lower()}|{body.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _normalize_channel(channel: str) -> str:
    """Normalize channel name: lowercase, strip, replace spaces with underscores."""
    return channel.strip().lower().replace(" ", "_").replace("/", "_")


def _make_engram_key(channel: str, hash_str: str) -> str:
    """Build the canonical engram key for an outbound record."""
    return f"{OUTBOUND_ENGRAM_PREFIX}{_normalize_channel(channel)}_{hash_str}"


# ═══════════════════════════════════════════════════════════════
# ENGRAM SEARCH (find existing outbound records)
# ═══════════════════════════════════════════════════════════════

def _find_outbound_engram(channel: str, hash_str: str) -> Optional[Dict]:
    """Search engrams for an existing outbound record by key prefix.

    Returns the parsed record dict if found, None otherwise.
    """
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"

        if not engram_path.exists():
            return None

        target_key = _make_engram_key(channel, hash_str)

        with open(engram_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    engram = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if engram.get("key", "") == target_key:
                    # Parse the value JSON if possible
                    try:
                        record = json.loads(engram.get("value", "{}"))
                        record["_engram_key"] = target_key
                        record["_intensity"] = engram.get("intensity", 0)
                        return record
                    except (json.JSONDecodeError, TypeError):
                        return {"_engram_key": target_key, "_raw_value": engram.get("value", "")}
        return None
    except Exception as e:
        logger.warning(f"Outbound engram search failed: {e}")
        return None


def _search_all_outbound_engrams(channel: Optional[str] = None) -> List[Dict]:
    """Search all outbound engrams, optionally filtered by channel.

    Returns list of parsed record dicts.
    """
    try:
        brain = get_brain_path()
        engram_path = brain / "engrams" / "ledger.jsonl"

        if not engram_path.exists():
            return []

        prefix = OUTBOUND_ENGRAM_PREFIX
        if channel:
            prefix = f"{OUTBOUND_ENGRAM_PREFIX}{_normalize_channel(channel)}_"

        results = []
        with open(engram_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    engram = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = engram.get("key", "")
                if key.startswith(prefix):
                    try:
                        record = json.loads(engram.get("value", "{}"))
                        record["_engram_key"] = key
                        return_record = record
                    except (json.JSONDecodeError, TypeError):
                        return_record = {"_engram_key": key, "_raw_value": engram.get("value", "")}
                    results.append(return_record)
        return results
    except Exception as e:
        logger.warning(f"Outbound engram search failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# OUTBOUND CHECK — the idempotency gate
# ═══════════════════════════════════════════════════════════════

def outbound_check(channel: str, identifier: str, body: str, override: bool = False) -> Dict[str, Any]:
    """Check if content has already been posted to a channel.

    Returns:
        {"status": "READY"}      — safe to post, no existing record
        {"status": "SKIP", ...}  — already posted successfully
        {"status": "RETRY", ...} — previously failed, needs explicit override
    """
    if not channel or not identifier:
        return {"status": "ERROR", "reason": "channel and identifier are required"}

    norm_channel = _normalize_channel(channel)
    hash_str = _compute_outbound_hash(norm_channel, identifier, body or "")
    engram_key = _make_engram_key(norm_channel, hash_str)

    existing = _find_outbound_engram(norm_channel, hash_str)

    if existing is None:
        return {
            "status": "READY",
            "channel": norm_channel,
            "identifier": identifier,
            "hash": hash_str,
            "engram_key": engram_key,
        }

    record_status = existing.get("status", "unknown")

    if record_status == "posted":
        return {
            "status": "SKIP",
            "reason": "already posted",
            "channel": norm_channel,
            "identifier": identifier,
            "hash": hash_str,
            "engram_key": engram_key,
            "existing_record": existing,
        }

    if record_status == "failed":
        if override:
            return {
                "status": "READY",
                "reason": "override on failed record",
                "channel": norm_channel,
                "identifier": identifier,
                "hash": hash_str,
                "engram_key": engram_key,
                "previous_failure": existing,
            }
        return {
            "status": "RETRY",
            "reason": "previously failed — pass override=true to retry",
            "channel": norm_channel,
            "identifier": identifier,
            "hash": hash_str,
            "engram_key": engram_key,
            "existing_record": existing,
        }

    # Unknown status — treat as skip to be safe
    return {
        "status": "SKIP",
        "reason": f"existing record with status '{record_status}'",
        "channel": norm_channel,
        "identifier": identifier,
        "hash": hash_str,
        "engram_key": engram_key,
        "existing_record": existing,
    }


# ═══════════════════════════════════════════════════════════════
# OUTBOUND RECORD — write the post ledger entry
# ═══════════════════════════════════════════════════════════════

def outbound_record(
    channel: str,
    identifier: str,
    body: str,
    permalink: str,
    workhorse: str,
    task_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a successful outbound post.

    Writes engram → marks task DONE (optional) → emits event.
    Growth hook fires automatically on the "outbound_posted" event.
    """
    if not channel or not identifier:
        return {"status": "error", "reason": "channel and identifier are required"}

    norm_channel = _normalize_channel(channel)
    hash_str = _compute_outbound_hash(norm_channel, identifier, body or "")
    engram_key = _make_engram_key(norm_channel, hash_str)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Build the record stored as engram value
    record = {
        "channel": norm_channel,
        "identifier": identifier,
        "title": title or identifier[:80],
        "body_hash": hash_str,
        "permalink": permalink or "",
        "status": "posted",
        "posted_at": now_iso,
        "workhorse": workhorse or "unknown",
        "task_id": task_id or "",
    }

    # 1. Write engram
    try:
        from .engram_ops import _brain_write_engram_impl

        _brain_write_engram_impl(
            key=engram_key,
            value=json.dumps(record),
            context=OUTBOUND_CONTEXT,
            intensity=OUTBOUND_INTENSITY,
        )
        logger.info(f"📤 Outbound recorded: [{norm_channel}] {identifier}")
    except Exception as e:
        logger.error(f"Outbound engram write failed: {e}")
        return {"status": "error", "reason": f"engram write failed: {e}", "engram_key": engram_key}

    # 2. Mark task DONE (if task_id provided)
    task_updated = False
    if task_id:
        try:
            from .task_ops import _update_task

            result = _update_task(task_id, {"status": "DONE"})
            task_updated = result.get("success", False)
            if task_updated:
                logger.info(f"📤 Task {task_id} marked DONE")
        except Exception as e:
            logger.warning(f"Outbound task update failed (non-fatal): {e}")

    # 3. Emit event (triggers growth hook)
    try:
        from .event_ops import _emit_event

        _emit_event(
            "outbound_posted",
            "outbound_ops",
            {
                "channel": norm_channel,
                "identifier": identifier,
                "title": record["title"],
                "permalink": permalink or "",
                "workhorse": workhorse,
                "hash": hash_str,
            },
            description=f"Posted to {norm_channel}: {record['title']}",
        )
    except Exception as e:
        logger.warning(f"Outbound event emit failed (non-fatal): {e}")

    return {
        "status": "recorded",
        "engram_key": engram_key,
        "channel": norm_channel,
        "hash": hash_str,
        "task_updated": task_updated,
        "record": record,
    }


# ═══════════════════════════════════════════════════════════════
# OUTBOUND FAIL — record a failed post attempt
# ═══════════════════════════════════════════════════════════════

def outbound_fail(
    channel: str,
    identifier: str,
    body: str,
    error: str,
    workhorse: str,
) -> Dict[str, Any]:
    """Record a failed outbound post attempt.

    Writes engram with status="failed". Next outbound_check returns RETRY.
    """
    if not channel or not identifier:
        return {"status": "error", "reason": "channel and identifier are required"}

    norm_channel = _normalize_channel(channel)
    hash_str = _compute_outbound_hash(norm_channel, identifier, body or "")
    engram_key = _make_engram_key(norm_channel, hash_str)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    record = {
        "channel": norm_channel,
        "identifier": identifier,
        "body_hash": hash_str,
        "status": "failed",
        "failed_at": now_iso,
        "error": str(error)[:500],
        "workhorse": workhorse or "unknown",
    }

    # Write failure engram
    try:
        from .engram_ops import _brain_write_engram_impl

        _brain_write_engram_impl(
            key=engram_key,
            value=json.dumps(record),
            context=OUTBOUND_CONTEXT,
            intensity=4,  # Lower intensity for failures
        )
        logger.info(f"📤❌ Outbound failure recorded: [{norm_channel}] {identifier}")
    except Exception as e:
        logger.error(f"Outbound failure engram write failed: {e}")
        return {"status": "error", "reason": f"engram write failed: {e}"}

    # Emit failure event
    try:
        from .event_ops import _emit_event

        _emit_event(
            "outbound_failed",
            "outbound_ops",
            {
                "channel": norm_channel,
                "identifier": identifier,
                "error": str(error)[:200],
                "workhorse": workhorse,
            },
            description=f"Failed to post to {norm_channel}: {str(error)[:100]}",
        )
    except Exception as e:
        logger.warning(f"Outbound failure event emit failed (non-fatal): {e}")

    return {
        "status": "failed_recorded",
        "engram_key": engram_key,
        "channel": norm_channel,
        "hash": hash_str,
        "record": record,
    }


# ═══════════════════════════════════════════════════════════════
# OUTBOUND STATUS — observable state for all channels
# ═══════════════════════════════════════════════════════════════

def outbound_status(channel: Optional[str] = None) -> Dict[str, Any]:
    """Get outbound posting status grouped by channel.

    Returns counts of posted/failed/total per channel.
    """
    records = _search_all_outbound_engrams(channel)

    channels: Dict[str, Dict[str, int]] = {}
    total_posted = 0
    total_failed = 0

    for record in records:
        ch = record.get("channel", "unknown")
        if ch not in channels:
            channels[ch] = {"posted": 0, "failed": 0, "total": 0}

        status = record.get("status", "unknown")
        channels[ch]["total"] += 1

        if status == "posted":
            channels[ch]["posted"] += 1
            total_posted += 1
        elif status == "failed":
            channels[ch]["failed"] += 1
            total_failed += 1

    return {
        "channels": channels,
        "total_posted": total_posted,
        "total_failed": total_failed,
        "total_records": len(records),
        "filter": channel or "all",
    }


# ═══════════════════════════════════════════════════════════════
# OUTBOUND PLAN — what's ready to post
# ═══════════════════════════════════════════════════════════════

def outbound_plan(channel: Optional[str] = None) -> Dict[str, Any]:
    """Show what's ready to post vs already posted vs failed.

    Cross-references outbound engrams with growth/outbound tasks.
    """
    # Get all outbound engrams
    records = _search_all_outbound_engrams(channel)
    posted_keys = set()
    failed_keys = set()

    posted_list = []
    failed_list = []

    for record in records:
        key = record.get("_engram_key", "")
        status = record.get("status", "unknown")
        summary = {
            "channel": record.get("channel", "?"),
            "identifier": record.get("identifier", "?"),
            "title": record.get("title", record.get("identifier", "?")),
            "status": status,
            "engram_key": key,
        }

        if status == "posted":
            summary["posted_at"] = record.get("posted_at", "?")
            summary["permalink"] = record.get("permalink", "")
            posted_list.append(summary)
            posted_keys.add(key)
        elif status == "failed":
            summary["failed_at"] = record.get("failed_at", "?")
            summary["error"] = record.get("error", "?")
            failed_list.append(summary)
            failed_keys.add(key)

    # Get tasks that look like outbound tasks (not yet DONE)
    ready_list = []
    try:
        from .task_ops import _list_tasks

        all_tasks = _list_tasks()
        for task in all_tasks:
            desc = task.get("description", "")
            task_status = task.get("status", "")
            source = task.get("source", "")

            # Match tasks that are outbound-related and not done
            if task_status == "DONE":
                continue
            if "outbound" in source.lower() or "post" in desc.lower() or "launch" in desc.lower():
                if channel:
                    if _normalize_channel(channel) not in desc.lower():
                        continue
                ready_list.append({
                    "task_id": task.get("id", "?"),
                    "description": desc,
                    "status": task_status,
                    "priority": task.get("priority", 3),
                })
    except Exception as e:
        logger.warning(f"Outbound plan task scan failed: {e}")

    return {
        "ready": ready_list,
        "already_posted": posted_list,
        "failed": failed_list,
        "summary": {
            "ready_count": len(ready_list),
            "posted_count": len(posted_list),
            "failed_count": len(failed_list),
        },
        "filter": channel or "all",
    }
