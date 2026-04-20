"""Relay-surface engram projection — project acked relays into the engram store.

Slice Obs-2 ingest substrate. Populates `.brain/engrams/history.jsonl` from the
relay surface so RAG retrieval can find "who said what to whom" on cross-checks
(direct fix for the substrate-gap finding on 2026-04-20's 7-point RAG empty).

Fires from `relay_ops.relay_ack` AFTER a successful ack (only-on-surface gate —
un-acted-on relays do NOT project). Also exposes a backfill entrypoint for the
last N days.

Idempotence:
    - Deterministic key `relay_projection_{relay_id}` + `store.keys_present()`
      check → same relay never double-projects.
    - Backfill re-runs are no-ops (second run writes 0 new engrams).

Content shape (preserves queryable axes):
    subject, body.summary, body.tags, body.artifact_refs + envelope threading
    (from, to, in_reply_to, from_session_id). Flattened into a single value
    string so the existing BM25 / retrieval path indexes all of it.

Usage:
    python3 -m mcp_server_nucleus.runtime.relay_engram_projection --backfill --days 14
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from nucleus_wedge.store import Store

logger = logging.getLogger("nucleus.relay_engram")

PROJECTION_SOURCE = "relay_surface_projection"
LIVE_BUCKETS = ("cowork", "claude_code", "claude_code_main", "claude_code_peer")


def _parse_body(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _build_projection_payload(msg: Dict[str, Any]) -> Dict[str, Any]:
    body = _parse_body(msg.get("body"))
    subject = str(msg.get("subject") or "")
    summary = str(body.get("summary") or "")
    body_tags = body.get("tags") or []
    if not isinstance(body_tags, list):
        body_tags = []
    artifact_refs = body.get("artifact_refs") or []
    if not isinstance(artifact_refs, list):
        artifact_refs = []
    in_reply_to = body.get("in_reply_to")
    from_agent = str(msg.get("from") or "")
    to_agent = str(msg.get("to") or "")
    from_session_id = msg.get("from_session_id") or body.get("from_session_id")

    envelope = f"[{from_agent} → {to_agent}]"
    if subject:
        envelope += f" {subject}"
    parts = [envelope]
    if summary:
        parts.append(f"\n\n{summary}")
    if artifact_refs:
        refs = ", ".join(str(r) for r in artifact_refs)
        parts.append(f"\n\nartifacts: {refs}")
    if in_reply_to:
        parts.append(f"\n\nin_reply_to: {in_reply_to}")
    if from_session_id:
        parts.append(f"\n\nfrom_session_id: {from_session_id}")

    return {
        "value": "".join(parts),
        "tags": [str(t) for t in body_tags],
    }


def _projection_key(relay_id: str) -> str:
    return f"relay_projection_{relay_id}"


def project_relay_to_engram(
    msg: Dict[str, Any],
    source_agent: str = PROJECTION_SOURCE,
    brain_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Project one relay msg into the engram store. Returns append result or None."""
    relay_id = msg.get("id")
    if not relay_id:
        return None
    try:
        store = Store(brain_path=brain_path)
        key = _projection_key(str(relay_id))
        if key in store.keys_present():
            return None
        payload = _build_projection_payload(msg)
        return store.append(
            value=payload["value"],
            kind="relay",
            tags=payload["tags"],
            intensity=4,
            source_agent=source_agent,
            key=key,
        )
    except Exception as exc:
        logger.debug("relay projection skipped for %s: %s", relay_id, exc)
        return None


def _iter_bucket_files(
    relay_root: Path,
    buckets: Iterable[str] = LIVE_BUCKETS,
    cutoff: Optional[datetime] = None,
) -> Iterable[Path]:
    for b in buckets:
        bpath = relay_root / b
        if not bpath.is_dir():
            continue
        for f in sorted(bpath.glob("*.json")):
            if f.name == "pending.json":
                continue
            if cutoff is not None:
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                except OSError:
                    continue
                if mtime < cutoff:
                    continue
            yield f


def backfill_recent_relays(
    days: int = 14,
    brain_path: Optional[Path] = None,
    source_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """Project relays from the last N days. Idempotent; safe to re-run."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    resolved_source = source_agent or f"{PROJECTION_SOURCE}_backfill_{today}"
    brain = Path(brain_path) if brain_path else Store.brain_path()
    relay_root = brain / "relay"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    scanned = 0
    projected = 0
    skipped = 0
    errors = 0
    by_bucket: Dict[str, int] = {}

    for f in _iter_bucket_files(relay_root, cutoff=cutoff):
        scanned += 1
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            errors += 1
            continue
        result = project_relay_to_engram(msg, source_agent=resolved_source, brain_path=brain)
        if result:
            projected += 1
            by_bucket[f.parent.name] = by_bucket.get(f.parent.name, 0) + 1
        else:
            skipped += 1

    return {
        "scanned": scanned,
        "projected": projected,
        "skipped": skipped,
        "errors": errors,
        "by_bucket": by_bucket,
        "source_agent": resolved_source,
        "cutoff": cutoff.isoformat(),
        "days": days,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--backfill", action="store_true", help="Run the backfill")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--brain-path", default=None)
    p.add_argument("--source-agent", default=None,
                   help="Override source_agent tag (default: relay_surface_projection_backfill_<today>)")
    args = p.parse_args()
    if not args.backfill:
        p.print_help()
        return 2
    brain = Path(args.brain_path) if args.brain_path else None
    report = backfill_recent_relays(days=args.days, brain_path=brain, source_agent=args.source_agent)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
