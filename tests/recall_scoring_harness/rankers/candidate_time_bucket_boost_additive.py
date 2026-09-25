"""Candidate ranker: BM25 score + recency-tier bonus (ADDITIVE).

Production-mirror of `nucleus_wedge/bm25.py::_rerank_time_bucket` after PR_C
fix (commit 1c6cca9c). Production switched to ADDITIVE bonus (BM25 + bonus)
because BM25 scores can be NEGATIVE on small/sparse corpora — multiplying
a negative score by 3.0 inverts the intended ranking.

PR_B's `candidate_time_bucket_boost.py` uses MULTIPLICATIVE (BM25 * boost)
and won the empirical A/B at that time. PR_D re-benchmarks the ADDITIVE
production behavior against the multiplicative original to confirm
whether the winner holds OR whether the additive variant changes the
ranking meaningfully.

Bonus magnitudes match production (`bm25.py` lines 82-87 after PR_C):
- last 7 days: +10.0 (≈ 2× typical positive BM25)
- last 30 days: +3.0
- older: +0.0
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(PKG_ROOT))

LAST_7D_BONUS = 10.0
LAST_30D_BONUS = 3.0
OLDER_BONUS = 0.0


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _bucket_bonus(ts_str: str, now: datetime) -> tuple[float, str]:
    ts = _parse_ts(ts_str)
    if ts is None:
        return (OLDER_BONUS, "unparseable")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_days = (now - ts).total_seconds() / 86400.0
    if age_days <= 7.0:
        return (LAST_7D_BONUS, "last_7d")
    if age_days <= 30.0:
        return (LAST_30D_BONUS, "last_30d")
    return (OLDER_BONUS, "older")


def rank(query: str, limit: int = 5) -> list[dict]:
    import os
    from nucleus_wedge import bm25 as _bm25
    from nucleus_wedge.store import Store

    # Force production re-ranker OFF so we measure pure BM25 + this candidate's
    # additive bonus in isolation. Otherwise if env=time_bucket_boost, production
    # already applies additive +10/+3/+0 and we double-count.
    _prev = os.environ.pop("NUCLEUS_WEDGE_RANKER", None)
    try:
        store = Store(Store.brain_path(None))
        candidates = _bm25.search(store, query=query, limit=max(limit * 5, 25))
    finally:
        if _prev is not None:
            os.environ["NUCLEUS_WEDGE_RANKER"] = _prev

    now = datetime.now(timezone.utc)
    for c in candidates:
        bonus, tier = _bucket_bonus(c.get("timestamp", ""), now)
        c["score"] = c["score"] + bonus
        c["_tier"] = tier
        c["_bonus"] = bonus

    candidates.sort(key=lambda r: r["score"], reverse=True)
    return candidates[:limit]
