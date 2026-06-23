"""Brain content sync — local ↔ hosted engram synchronization.

Implements the client side of the engram sync protocol:
    1. Read local engrams from .brain/engrams/ledger.jsonl
    2. POST them to the hosted sync endpoint (NUCLEUS_SYNC_URL)
    3. Receive remote engrams that are newer or missing locally
    4. Apply remote engrams to local ledger via ADUN pipeline
    5. Persist sync state (last sync timestamp) for incremental sync

Conflict resolution is deterministic and matches the server side:
    version > timestamp > intensity (higher wins each)

Usage:
    nucleus sync                    # sync with default hosted endpoint
    nucleus sync --url URL          # explicit hosted endpoint
    nucleus sync --dry-run          # show what would sync without writing
    nucleus sync --full             # full sync (ignore since_timestamp)
    nucleus sync --status           # show sync state without syncing
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.sync")

# ── Config ────────────────────────────────────────────────────────────

SYNC_STATE_FILE = ".sync_state.json"
DEFAULT_SYNC_URL = "https://relay.nucleusos.dev/engrams/sync"
SYNC_TIMEOUT_S = 30


def _get_sync_url(explicit_url: Optional[str] = None) -> str:
    """Resolve the sync endpoint URL."""
    if explicit_url:
        return explicit_url
    return os.environ.get("NUCLEUS_SYNC_URL", DEFAULT_SYNC_URL)


def _get_sync_token() -> Optional[str]:
    """Get the bearer token for sync auth."""
    return os.environ.get("NUCLEUS_SYNC_TOKEN") or os.environ.get("NUCLEUS_RELAY_BEARER")


def _get_brain_path() -> Path:
    """Get the local brain path."""
    from mcp_server_nucleus.runtime.common import get_brain_path
    return Path(get_brain_path())


def _read_local_engrams(brain_path: Path) -> List[Dict[str, Any]]:
    """Read all engrams from local ledger, returning latest version per key."""
    ledger_path = brain_path / "engrams" / "ledger.jsonl"
    if not ledger_path.exists():
        return []

    engrams_by_key: Dict[str, Dict[str, Any]] = {}
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
        logger.warning("Failed to read local ledger: %s", e)
        return []

    return list(engrams_by_key.values())


def _engram_rank(engram: Dict[str, Any]) -> Tuple[int, float, int]:
    """Sort key for conflict resolution: (version, timestamp_epoch, intensity)."""
    version = engram.get("version", 1)
    ts = _parse_timestamp(engram.get("timestamp", ""))
    ts_epoch = ts.timestamp() if ts else 0.0
    intensity = engram.get("intensity", 5)
    return (version, ts_epoch, intensity)


def _parse_timestamp(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _load_sync_state(brain_path: Path) -> Dict[str, Any]:
    """Load persisted sync state (last sync timestamp, count, etc.)."""
    state_path = brain_path / "engrams" / SYNC_STATE_FILE
    if not state_path.exists():
        return {"last_sync_timestamp": None, "sync_count": 0, "last_sync_engrams": 0}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_sync_timestamp": None, "sync_count": 0, "last_sync_engrams": 0}


def _save_sync_state(brain_path: Path, state: Dict[str, Any]) -> None:
    """Persist sync state."""
    state_path = brain_path / "engrams" / SYNC_STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(state_path)


def _apply_remote_engrams(
    remote_engrams: List[Dict[str, Any]], brain_path: Path, dry_run: bool = False
) -> Tuple[int, int]:
    """Apply remote engrams to local ledger via ADUN pipeline.

    Returns (applied_count, skipped_count).
    """
    if dry_run:
        return len(remote_engrams), 0

    from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline

    pipeline = MemoryPipeline(brain_path)
    applied = 0
    skipped = 0

    for remote_engram in remote_engrams:
        key = remote_engram.get("key")
        if not key:
            skipped += 1
            continue

        try:
            # Use the ADUN pipeline for deterministic apply
            result = pipeline.process(
                text=remote_engram.get("value", ""),
                context=remote_engram.get("context", "Decision"),
                intensity=remote_engram.get("intensity", 5),
                source_agent=f"sync_remote:{remote_engram.get('source_agent', 'unknown')}",
                key=key,
            )
            # ADUN result has added/updated/skipped counts
            if result.get("added", 0) > 0 or result.get("updated", 0) > 0:
                applied += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning("Failed to apply remote engram %s: %s", key, e)
            skipped += 1

    # Invalidate cache after writes
    try:
        from mcp_server_nucleus.runtime.engram_cache import get_engram_cache
        get_engram_cache().invalidate()
    except Exception:
        pass

    return applied, skipped


def _post_sync(
    url: str,
    token: Optional[str],
    since_timestamp: Optional[str],
    local_engrams: List[Dict[str, Any]],
    sync_state: Dict[str, Any],
) -> Dict[str, Any]:
    """POST sync request to hosted endpoint. Returns parsed response."""
    import urllib.request
    import urllib.error

    payload = {
        "since_timestamp": since_timestamp,
        "local_engrams": local_engrams,
        "local_sync_state": sync_state,
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        url, data=body, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=SYNC_TIMEOUT_S) as resp:
            response_body = resp.read().decode("utf-8")
            return json.loads(response_body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Sync endpoint returned HTTP {e.code}: {error_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Sync endpoint unreachable: {e.reason}") from e


def perform_sync_cycle(
    url: Optional[str] = None,
    dry_run: bool = False,
    full: bool = False,
) -> Dict[str, Any]:
    """Execute a sync cycle and return stats dict (no stdout/stderr printing).

    This is the daemon-safe entry point used by the relay bridge daemon's
    background engram sync. Never raises — transport/apply errors are
    captured in the returned stats dict.

    Returns dict with keys:
        ok (bool), pushed, received, applied, skipped, conflicts,
        next_timestamp, error (str|None), transport_down (bool)
    """
    sync_url = _get_sync_url(url)
    token = _get_sync_token()
    brain_path = _get_brain_path()

    sync_state = _load_sync_state(brain_path)
    since_ts = None if full else sync_state.get("last_sync_timestamp")
    local_engrams = _read_local_engrams(brain_path)

    stats: Dict[str, Any] = {
        "ok": False, "pushed": 0, "received": 0, "applied": 0,
        "skipped": 0, "conflicts": 0, "next_timestamp": None,
        "error": None, "transport_down": False,
    }

    if dry_run:
        stats["ok"] = True
        stats["pushed"] = len(local_engrams)
        return stats

    if not token:
        stats["error"] = "no_token"
        return stats

    # POST to sync endpoint
    try:
        response = _post_sync(
            sync_url, token, since_ts, local_engrams, sync_state
        )
    except RuntimeError as e:
        stats["error"] = str(e)
        stats["transport_down"] = "unreachable" in str(e).lower()
        return stats

    if not response.get("synced"):
        stats["error"] = f"{response.get('error', 'unknown')}: {response.get('reason', '')}"
        return stats

    # Apply remote engrams to local
    remote_engrams = response.get("remote_engrams", [])
    applied, skipped = _apply_remote_engrams(remote_engrams, brain_path, dry_run)

    # Update sync state
    next_ts = response.get("next_sync_timestamp")
    new_state = {
        "last_sync_timestamp": next_ts,
        "sync_count": sync_state.get("sync_count", 0) + 1,
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "last_sync_local_pushed": len(local_engrams),
        "last_sync_local_applied": response.get("synced_count", 0),
        "last_sync_remote_received": len(remote_engrams),
        "last_sync_remote_applied": applied,
        "last_sync_remote_skipped": skipped,
        "last_sync_conflicts": response.get("conflict_count", 0),
    }
    _save_sync_state(brain_path, new_state)

    stats.update({
        "ok": True,
        "pushed": response.get("synced_count", 0),
        "received": len(remote_engrams),
        "applied": applied,
        "skipped": skipped,
        "conflicts": response.get("conflict_count", 0),
        "next_timestamp": next_ts,
    })
    return stats


def perform_sync(
    url: Optional[str] = None,
    dry_run: bool = False,
    full: bool = False,
    verbose: bool = False,
) -> int:
    """Execute a sync cycle. Returns exit code (0 = success, 1 = error)."""
    sync_url = _get_sync_url(url)
    token = _get_sync_token()
    brain_path = _get_brain_path()

    # Load sync state
    sync_state = _load_sync_state(brain_path)
    since_ts = None if full else sync_state.get("last_sync_timestamp")

    # Read local engrams
    local_engrams = _read_local_engrams(brain_path)

    if verbose:
        print(f"Sync configuration:")
        print(f"  Endpoint:    {sync_url}")
        print(f"  Brain path:  {brain_path}")
        print(f"  Local engrams: {len(local_engrams)}")
        print(f"  Since timestamp: {since_ts or '(full sync)'}")
        print(f"  Token:       {'configured' if token else 'MISSING'}")
        print()

    if dry_run:
        print(f"[DRY RUN] Would sync {len(local_engrams)} local engrams to {sync_url}")
        print(f"[DRY RUN] Would request remote engams since: {since_ts or '(full sync)'}")
        return 0

    if not token:
        print("Error: No sync token configured.", file=sys.stderr)
        print("Set NUCLEUS_SYNC_TOKEN or NUCLEUS_RELAY_BEARER env var.", file=sys.stderr)
        return 1

    # POST to sync endpoint
    try:
        response = _post_sync(
            sync_url, token, since_ts, local_engrams, sync_state
        )
    except RuntimeError as e:
        print(f"Sync failed: {e}", file=sys.stderr)
        return 1

    if not response.get("synced"):
        print(f"Sync error: {response.get('error', 'unknown')}: {response.get('reason', '')}", file=sys.stderr)
        return 1

    # Apply remote engrams to local
    remote_engrams = response.get("remote_engrams", [])
    applied, skipped = _apply_remote_engrams(remote_engrams, brain_path, dry_run)

    # Update sync state
    next_ts = response.get("next_sync_timestamp")
    new_state = {
        "last_sync_timestamp": next_ts,
        "sync_count": sync_state.get("sync_count", 0) + 1,
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "last_sync_local_pushed": len(local_engrams),
        "last_sync_local_applied": response.get("synced_count", 0),
        "last_sync_remote_received": len(remote_engrams),
        "last_sync_remote_applied": applied,
        "last_sync_remote_skipped": skipped,
        "last_sync_conflicts": response.get("conflict_count", 0),
    }
    _save_sync_state(brain_path, new_state)

    # Report
    print(f"Sync complete:")
    print(f"  Pushed to hosted:    {response.get('synced_count', 0)} engrams")
    print(f"  Received from hosted: {len(remote_engrams)} engrams")
    print(f"  Applied locally:     {applied} engrams")
    print(f"  Skipped:             {skipped} engrams")
    print(f"  Conflicts:           {response.get('conflict_count', 0)}")
    if response.get("conflicts"):
        for c in response["conflicts"][:5]:
            print(f"    - {c['key']}: local v{c['local_version']} vs remote v{c['remote_version']} → {c['resolution']}")
        if len(response["conflicts"]) > 5:
            print(f"    ... and {len(response['conflicts']) - 5} more")
    print(f"  Next sync timestamp: {next_ts}")
    print(f"  Hosted engram count: {response.get('hosted_sync_state', {}).get('engram_count', '?')}")

    return 0


def show_sync_status() -> int:
    """Show current sync state without syncing."""
    brain_path = _get_brain_path()
    state = _load_sync_state(brain_path)
    sync_url = _get_sync_url()
    token = _get_sync_token()

    print(f"Sync status:")
    print(f"  Endpoint:          {sync_url}")
    print(f"  Token configured:  {'yes' if token else 'no'}")
    print(f"  Sync count:        {state.get('sync_count', 0)}")
    print(f"  Last sync at:      {state.get('last_sync_at', 'never')}")
    print(f"  Last sync timestamp: {state.get('last_sync_timestamp', 'none')}")
    print(f"  Last pushed:       {state.get('last_sync_local_pushed', 0)} engrams")
    print(f"  Last applied:      {state.get('last_sync_local_applied', 0)} engrams")
    print(f"  Last received:     {state.get('last_sync_remote_received', 0)} engrams")
    print(f"  Last conflicts:    {state.get('last_sync_conflicts', 0)}")

    # Count local engrams
    local_engrams = _read_local_engrams(brain_path)
    print(f"  Local engrams:     {len(local_engrams)}")

    return 0


# ── CLI handler ───────────────────────────────────────────────────────


def handle_sync_command(args) -> int:
    """CLI entrypoint for `nucleus sync`."""
    verbose = getattr(args, "verbose", False)

    if getattr(args, "status", False):
        return show_sync_status()

    return perform_sync(
        url=getattr(args, "url", None),
        dry_run=getattr(args, "dry_run", False),
        full=getattr(args, "full", False),
        verbose=verbose,
    )
