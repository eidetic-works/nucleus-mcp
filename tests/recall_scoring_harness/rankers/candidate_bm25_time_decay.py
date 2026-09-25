"""Candidate ranker: BM25 score * exp(-age_days * decay_rate).

Hypothesis: exponential time decay penalizes older content; recent relevant
content surfaces above older generic content. Decay rate tuned to halve score
at half-life days (default 30 days → 30d-old content has ~50% original BM25;
60d-old has ~25%; 7d-old has ~85%).

Per #440 v1 fix direction (a).
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(PKG_ROOT))

DECAY_HALF_LIFE_DAYS = 30.0
DECAY_RATE = math.log(2) / DECAY_HALF_LIFE_DAYS  # so score halves at half_life_days


def _parse_ts(ts: str) -> datetime | None:
    """Parse ISO-8601 timestamp; return None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _age_days(ts_str: str, now: datetime) -> float:
    """Age in days; large fallback for unparseable timestamps."""
    ts = _parse_ts(ts_str)
    if ts is None:
        return 365.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ts).total_seconds() / 86400.0)


def rank(query: str, limit: int = 5) -> list[dict]:
    """BM25 score * exp(-age_days * decay_rate). Fetch limit*5 from baseline
    then re-rank — gives time-decay a chance to surface relevant older content
    that baseline ranked below top-K."""
    from nucleus_wedge import bm25 as _bm25
    from nucleus_wedge.store import Store

    store = Store(Store.brain_path(None))
    # Over-fetch to give re-ranker room
    candidates = _bm25.search(store, query=query, limit=max(limit * 5, 25))

    now = datetime.now(timezone.utc)
    for c in candidates:
        age = _age_days(c.get("timestamp", ""), now)
        decay = math.exp(-age * DECAY_RATE)
        c["score"] = c["score"] * decay
        c["_age_days"] = round(age, 2)
        c["_decay_factor"] = round(decay, 3)

    candidates.sort(key=lambda r: r["score"], reverse=True)
    return candidates[:limit]
