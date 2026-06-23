"""POST /engrams/sync — bidirectional engram sync endpoint.

Implements the brain content sync protocol: local brain pushes its engrams
to the hosted store, hosted store responds with engrams the local doesn't
have (or has older versions of). Conflict resolution is deterministic:

    1. Higher version wins
    2. Same version → later timestamp wins
    3. Same version + timestamp → higher intensity wins
    4. Identical → NOOP

Auth: Bearer token via NucleusTenantMiddleware (same as relay routes).
Tenant isolation: per-tenant brain path resolved by middleware; each
tenant's engrams live in <brain_root>/<tenant_id>/.brain/engrams/ledger.jsonl.

Engram record shape (append-only JSONL):
    {
        "key": str,           # dedup key
        "value": str,         # content
        "context": str,       # Feature|Architecture|Brand|Strategy|Decision
        "intensity": int,     # 1-10
        "version": int,       # incremented on UPDATE
        "source_agent": str,  # origin agent
        "op_type": str,       # ADD|UPDATE|DELETE|NOOP
        "timestamp": str,     # ISO8601 UTC
        "deleted": bool,      # soft-delete flag
    }

Request:
    POST /engrams/sync
    Authorization: Bearer <token>
    Content-Type: application/json

    {
        "since_timestamp": "2026-06-15T10:00:00Z" | null,
        "local_engrams": [<engram_record>, ...],
        "local_sync_state": {"last_sync_timestamp": "...", "sync_count": N}
    }

Response:
    {
        "synced": <count of local engrams applied to hosted>,
        "conflicts": [{"key": ..., "local_version": N, "remote_version": M, "resolution": "remote_wins"|"local_wins"|"noop"}],
        "remote_engrams": [<engram_record>, ...],  # engrams local should apply
        "next_sync_timestamp": "2026-06-15T10:45:00Z",
        "hosted_sync_state": {"engram_count": N, "last_modified": "..."}
    }
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("nucleus.engram_sync")

# ── Config ────────────────────────────────────────────────────────────

MAX_ENGRAMS_PER_SYNC = int(os.environ.get("NUCLEUS_SYNC_MAX_ENGRAMS", "5000"))
MAX_BODY_BYTES = int(os.environ.get("NUCLEUS_SYNC_MAX_BODY", "10_000_000"))  # 10 MiB
VALID_CONTEXTS = {"Feature", "Architecture", "Brand", "Strategy", "Decision"}


# ── Helpers ───────────────────────────────────────────────────────────


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse ISO8601 timestamp; return None on failure."""
    if not ts:
        return None
    try:
        # Handle both with and without timezone suffix
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _validate_engram(engram: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate an engram record. Returns (valid, error_message)."""
    if not isinstance(engram, dict):
        return False, "Engram must be a JSON object"
    key = engram.get("key")
    if not key or not isinstance(key, str) or len(key) < 2:
        return False, f"Invalid key: {key!r}"
    if "version" not in engram or not isinstance(engram["version"], int):
        return False, f"Missing/invalid version for key={key}"
    if "timestamp" not in engram or not isinstance(engram["timestamp"], str):
        return False, f"Missing/invalid timestamp for key={key}"
    context = engram.get("context", "Decision")
    if context not in VALID_CONTEXTS:
        return False, f"Invalid context '{context}' for key={key}"
    intensity = engram.get("intensity", 5)
    if not isinstance(intensity, int) or not 1 <= intensity <= 10:
        return False, f"Invalid intensity {intensity} for key={key}"
    return True, None


def _read_hosted_engrams(ledger_path) -> Dict[str, Dict[str, Any]]:
    """Read all engrams from hosted ledger, keyed by engram key.

    Returns the LATEST version of each key (highest version, then latest timestamp).
    """
    engrams_by_key: Dict[str, Dict[str, Any]] = {}
    if not ledger_path.exists():
        return engrams_by_key
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    engram = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = engram.get("key")
                if not key:
                    continue
                existing = engrams_by_key.get(key)
                if existing is None or _engram_rank(engram) > _engram_rank(existing):
                    engrams_by_key[key] = engram
    except Exception as e:
        logger.warning("Failed to read hosted ledger %s: %s", ledger_path, e)
    return engrams_by_key


def _engram_rank(engram: Dict[str, Any]) -> Tuple[int, float, int]:
    """Sort key for conflict resolution: (version, timestamp_epoch, intensity).

    Higher tuple = wins conflict.
    """
    version = engram.get("version", 1)
    ts = _parse_timestamp(engram.get("timestamp", ""))
    ts_epoch = ts.timestamp() if ts else 0.0
    intensity = engram.get("intensity", 5)
    return (version, ts_epoch, intensity)


def _apply_engram_to_hosted(engram: Dict[str, Any], ledger_path, brain_path) -> str:
    """Apply a single engram to the hosted ledger.

    Returns: "added" | "updated" | "noop" | "skipped"
    """
    key = engram.get("key")
    if not key:
        return "skipped"

    hosted = _read_hosted_engrams(ledger_path)
    existing = hosted.get(key)

    if existing is None:
        # ADD — engram doesn't exist on hosted
        _append_to_ledger(engram, ledger_path, brain_path)
        return "added"

    # Compare ranks
    local_rank = _engram_rank(engram)
    remote_rank = _engram_rank(existing)

    if local_rank == remote_rank:
        return "noop"

    if local_rank > remote_rank:
        # Local is newer — update hosted
        _append_to_ledger(engram, ledger_path, brain_path)
        return "updated"

    # Remote is newer — local should accept remote version
    return "noop"


def _append_to_ledger(engram: Dict[str, Any], ledger_path, brain_path) -> None:
    """Append engram to the hosted ledger (file-locked)."""
    try:
        from mcp_server_nucleus.runtime.locking import get_lock

        with get_lock("engrams", brain_path).section():
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(engram, ensure_ascii=False) + "\n")
    except Exception as lock_err:
        logger.warning("Lock unavailable for sync append, falling back: %s", lock_err)
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(engram, ensure_ascii=False) + "\n")


def _filter_engrams_since(
    engrams: List[Dict[str, Any]], since_timestamp: Optional[str]
) -> List[Dict[str, Any]]:
    """Return engrams modified since the given timestamp (exclusive).

    If since_timestamp is None, return all.
    """
    if since_timestamp is None:
        return engrams

    since_dt = _parse_timestamp(since_timestamp)
    if since_dt is None:
        return engrams

    result = []
    for engram in engrams:
        engram_dt = _parse_timestamp(engram.get("timestamp", ""))
        if engram_dt and engram_dt > since_dt:
            result.append(engram)
    return result


def _err(http_status: int, code: str, reason: str) -> JSONResponse:
    return JSONResponse(
        {"synced": False, "error": code, "reason": reason},
        status_code=http_status,
    )


# ── Route handler ─────────────────────────────────────────────────────


async def engram_sync_route_handler(request: Request) -> JSONResponse:
    """POST /engrams/sync — bidirectional engram sync."""
    # Tenant + brain path already resolved by NucleusTenantMiddleware
    brain_path_str = getattr(request.state, "nucleus_brain_path", None)
    tenant_id = getattr(request.state, "nucleus_tenant_id", "default")

    if not brain_path_str:
        return _err(500, "internal_error", "Brain path not resolved by middleware")

    from pathlib import Path

    brain_path = Path(brain_path_str)
    engrams_dir = brain_path / "engrams"
    engrams_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = engrams_dir / "ledger.jsonl"

    # Body parse + size cap
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return _err(413, "body_too_large", f"Body exceeds {MAX_BODY_BYTES} bytes")

    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError as e:
        return _err(400, "schema_violation", f"Invalid JSON: {e}")

    if not isinstance(payload, dict):
        return _err(400, "schema_violation", "Body must be a JSON object")

    since_timestamp = payload.get("since_timestamp")
    local_engrams = payload.get("local_engrams", [])
    local_sync_state = payload.get("local_sync_state", {})

    if not isinstance(local_engrams, list):
        return _err(400, "schema_violation", "local_engrams must be a list")

    if len(local_engrams) > MAX_ENGRAMS_PER_SYNC:
        return _err(
            413,
            "too_many_engrams",
            f"local_engrams has {len(local_engrams)} entries; max is {MAX_ENGRAMS_PER_SYNC}",
        )

    # Validate each local engram
    valid_local: List[Dict[str, Any]] = []
    validation_errors: List[str] = []
    for i, engram in enumerate(local_engrams):
        ok, err = _validate_engram(engram)
        if ok:
            valid_local.append(engram)
        else:
            validation_errors.append(f"local_engrams[{i}]: {err}")

    if validation_errors:
        return _err(400, "schema_violation", "; ".join(validation_errors[:5]))

    # Read hosted engrams (current state)
    hosted_engrams = _read_hosted_engrams(ledger_path)

    # Phase 1: Apply local engrams to hosted
    synced_count = 0
    conflicts: List[Dict[str, Any]] = []

    for local_engram in valid_local:
        key = local_engram["key"]
        existing = hosted_engrams.get(key)

        if existing is None:
            # ADD
            _append_to_ledger(local_engram, ledger_path, brain_path)
            hosted_engrams[key] = local_engram
            synced_count += 1
        else:
            local_rank = _engram_rank(local_engram)
            remote_rank = _engram_rank(existing)

            if local_rank == remote_rank:
                conflicts.append({
                    "key": key,
                    "local_version": local_engram.get("version"),
                    "remote_version": existing.get("version"),
                    "resolution": "noop",
                })
            elif local_rank > remote_rank:
                # Local wins — append to hosted
                _append_to_ledger(local_engram, ledger_path, brain_path)
                hosted_engrams[key] = local_engram
                synced_count += 1
                conflicts.append({
                    "key": key,
                    "local_version": local_engram.get("version"),
                    "remote_version": existing.get("version"),
                    "resolution": "local_wins",
                })
            else:
                # Remote wins — local should accept remote
                conflicts.append({
                    "key": key,
                    "local_version": local_engram.get("version"),
                    "remote_version": existing.get("version"),
                    "resolution": "remote_wins",
                })

    # Phase 2: Determine remote engrams to send back to local
    # Send engrams that local doesn't have, OR where remote is newer
    local_keys = {e["key"] for e in valid_local}
    remote_to_send: List[Dict[str, Any]] = []

    for key, hosted_engram in hosted_engrams.items():
        local_match = next((e for e in valid_local if e["key"] == key), None)
        if local_match is None:
            # Local doesn't have this — send it
            remote_to_send.append(hosted_engram)
        else:
            # Both have it — send only if remote is newer
            remote_rank = _engram_rank(hosted_engram)
            local_rank = _engram_rank(local_match)
            if remote_rank > local_rank:
                remote_to_send.append(hosted_engram)

    # Filter by since_timestamp if provided (incremental sync)
    remote_to_send = _filter_engrams_since(remote_to_send, since_timestamp)

    # Build sync state
    next_sync_timestamp = _utc_now_iso()
    hosted_sync_state = {
        "engram_count": len(hosted_engrams),
        "last_modified": max(
            (e.get("timestamp", "") for e in hosted_engrams.values()),
            default="",
        ),
        "tenant_id": tenant_id,
    }

    logger.info(
        "engram_sync tenant=%s local_in=%d synced=%d conflicts=%d remote_out=%d",
        tenant_id,
        len(valid_local),
        synced_count,
        len(conflicts),
        len(remote_to_send),
    )

    return JSONResponse({
        "synced": True,
        "synced_count": synced_count,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "remote_engrams": remote_to_send,
        "remote_count": len(remote_to_send),
        "next_sync_timestamp": next_sync_timestamp,
        "hosted_sync_state": hosted_sync_state,
        "validation_errors": validation_errors,
    })


# ── Route export ──────────────────────────────────────────────────────

engram_sync_route = Route("/engrams/sync", engram_sync_route_handler, methods=["POST"])

# GET endpoint — returns hosted engram count + state (for health/preflight)
async def engram_sync_status_handler(request: Request) -> JSONResponse:
    """GET /engrams/sync — hosted brain sync status (read-only preflight)."""
    brain_path_str = getattr(request.state, "nucleus_brain_path", None)
    tenant_id = getattr(request.state, "nucleus_tenant_id", "default")

    if not brain_path_str:
        return _err(500, "internal_error", "Brain path not resolved")

    from pathlib import Path

    ledger_path = Path(brain_path_str) / "engrams" / "ledger.jsonl"
    hosted = _read_hosted_engrams(ledger_path)

    return JSONResponse({
        "status": "ok",
        "tenant_id": tenant_id,
        "engram_count": len(hosted),
        "last_modified": max(
            (e.get("timestamp", "") for e in hosted.values()),
            default="",
        ),
        "sync_endpoint": "/engrams/sync",
        "max_engrams_per_sync": MAX_ENGRAMS_PER_SYNC,
    })


engram_sync_status_route = Route("/engrams/sync/status", engram_sync_status_handler, methods=["GET"])
