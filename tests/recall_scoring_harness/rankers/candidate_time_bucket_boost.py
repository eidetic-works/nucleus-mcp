"""Candidate ranker: BM25 score * recency-tier multiplier.

Hypothesis: discrete recency tiers (last-7d × 3.0, last-30d × 1.5, older × 1.0)
better-match operator's intuitive "today/this-week/older" mental model than
continuous exponential decay. Per #440 v1 fix direction (b).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(PKG_ROOT))

LAST_7D_BOOST = 3.0
LAST_30D_BOOST = 1.5
OLDER_BOOST = 1.0


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _bucket_boost(ts_str: str, now: datetime) -> tuple[float, str]:
    ts = _parse_ts(ts_str)
    if ts is None:
        return (OLDER_BOOST, "unparseable")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_days = (now - ts).total_seconds() / 86400.0
    if age_days <= 7.0:
        return (LAST_7D_BOOST, "last_7d")
    if age_days <= 30.0:
        return (LAST_30D_BOOST, "last_30d")
    return (OLDER_BOOST, "older")


def rank(query: str, limit: int = 5) -> list[dict]:
    from nucleus_wedge import bm25 as _bm25
    from nucleus_wedge.store import Store

    store = Store(Store.brain_path(None))
    candidates = _bm25.search(store, query=query, limit=max(limit * 5, 25))

    now = datetime.now(timezone.utc)
    for c in candidates:
        boost, tier = _bucket_boost(c.get("timestamp", ""), now)
        c["score"] = c["score"] * boost
        c["_tier"] = tier
        c["_boost"] = boost

    candidates.sort(key=lambda r: r["score"], reverse=True)
    return candidates[:limit]
