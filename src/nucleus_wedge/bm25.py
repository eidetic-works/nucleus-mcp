"""In-memory BM25 over Store rows. Rebuild on every ``search`` call (Day-1; 2615 rows ≪ 50 ms).

#440 PR_C wire-in: NUCLEUS_WEDGE_RANKER env var selects post-BM25 re-ranker.
Default = baseline (BM25-only, no re-rank). Set NUCLEUS_WEDGE_RANKER=time_bucket_boost
to enable the empirically-winning candidate from #440 PR_B benchmark
(+12% recent@5 over baseline; matches operator 'today/this-week/older' intuition).

Allowed values:
  baseline           — BM25 only (default; preserves pre-#440 behavior)
  time_bucket_boost  — BM25 × recency tier (last-7d × 3.0, last-30d × 1.5, older × 1.0)
  bm25_time_decay    — BM25 × exp(-age_days * ln(2)/30) (30-day half-life)
  per_kind           — BM25 × kind boost (activity 3.0, feedback 2.5, etc — DEPRECATED:
                       PR_B benchmark showed this DILUTES recency, -5% vs baseline)
"""
from __future__ import annotations

import json, math, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from nucleus_wedge.store import Store

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# #440 PR_C: post-BM25 re-rank parameters (match PR_B winning candidate)
_DECAY_HALF_LIFE_DAYS = 30.0
_DECAY_RATE = math.log(2) / _DECAY_HALF_LIFE_DAYS
_TIER_LAST_7D_BOOST = 3.0
_TIER_LAST_30D_BOOST = 1.5
_TIER_OLDER_BOOST = 1.0
_KIND_BOOST = {
    "activity": 3.0,
    "feedback": 2.5,
    "decision": 2.0,
    "note": 1.5,
    "unknown": 1.0,
}


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _parse_ts(ts: str):
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t
    except (ValueError, AttributeError):
        return None


def _rerank_time_decay(ranked: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    for r in ranked:
        ts = _parse_ts(r.get("timestamp", ""))
        age_days = 365.0 if ts is None else max(0.0, (now - ts).total_seconds() / 86400.0)
        r["score"] = r["score"] * math.exp(-age_days * _DECAY_RATE)
    ranked.sort(key=lambda d: d["score"], reverse=True)
    return ranked


def _rerank_time_bucket(ranked: list[dict]) -> list[dict]:
    """Tier-based recency boost. Uses ADDITIVE bonus (not multiplicative)
    because BM25 scores can be NEGATIVE on small/sparse corpora — multiplying
    a negative score by 3.0 inverts the intended ranking. Additive bonus is
    robust to score sign. Bonus magnitudes scaled so a tier-jump exceeds
    typical BM25 score gaps (~5-10) for visible promotion."""
    now = datetime.now(timezone.utc)
    for r in ranked:
        ts = _parse_ts(r.get("timestamp", ""))
        if ts is None:
            bonus = 0.0
        else:
            age_days = (now - ts).total_seconds() / 86400.0
            if age_days <= 7.0:
                bonus = 10.0  # ~ same magnitude as 2x BM25 typical positive scores
            elif age_days <= 30.0:
                bonus = 3.0
            else:
                bonus = 0.0
        r["score"] = r["score"] + bonus
    ranked.sort(key=lambda d: d["score"], reverse=True)
    return ranked


def _rerank_per_kind(ranked: list[dict]) -> list[dict]:
    for r in ranked:
        kind = (r.get("kind") or "unknown").lower()
        if kind.startswith("["):
            kind = kind.lstrip("[").split(":", 1)[0].strip()
        boost = _KIND_BOOST.get(kind, _KIND_BOOST["unknown"])
        r["score"] = r["score"] * boost
    ranked.sort(key=lambda d: d["score"], reverse=True)
    return ranked


_RANKERS = {
    "baseline": lambda r: r,  # no-op; preserves pre-#440 behavior
    "time_bucket_boost": _rerank_time_bucket,
    "bm25_time_decay": _rerank_time_decay,
    "per_kind": _rerank_per_kind,
}


def _select_reranker():
    """Return post-BM25 re-ranker function based on NUCLEUS_WEDGE_RANKER env."""
    selected = (os.environ.get("NUCLEUS_WEDGE_RANKER") or "baseline").strip().lower()
    return _RANKERS.get(selected, _RANKERS["baseline"]), selected


def search(
    store: Store,
    query: str,
    limit: int = 5,
    kind: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """Rank history rows by BM25 on ``value``. Optional filters: ``kind`` (exact context prefix), ``since`` (ISO-8601 lex-comparable).

    #440 PR_C: post-BM25 re-rank via NUCLEUS_WEDGE_RANKER env var.
    Default = 'baseline' (no re-rank; preserves pre-#440 behavior).
    Set NUCLEUS_WEDGE_RANKER=time_bucket_boost for empirical PR_B winner.
    """
    _t0 = time.perf_counter()
    flat = [Store.extract(r) for r in store.rows()]
    if kind:
        flat = [r for r in flat if r["context"].startswith(kind)]
    if since:
        flat = [r for r in flat if r["timestamp"] >= since]
    if not flat:
        return []

    corpus: Iterable[list[str]] = [_tokenize(r["value"]) for r in flat]
    bm25 = BM25Okapi(list(corpus))
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scores = bm25.get_scores(q_tokens)

    # Over-fetch when re-ranker is active so the re-rank step can promote
    # relevant items the baseline buried below top-K. No-op for baseline.
    reranker, ranker_name = _select_reranker()
    pre_limit = max(1, int(limit)) * (5 if ranker_name != "baseline" else 1)

    ranked = sorted(
        (
            {
                "content": r["value"],
                "kind": r["kind"],
                "timestamp": r["timestamp"],
                "key": r["key"],
                "score": float(s),
            }
            for r, s in zip(flat, scores)
        ),
        key=lambda d: d["score"],
        reverse=True,
    )[:pre_limit]

    ranked = reranker(ranked)

    _p = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")) / "metrics" / "recall_timings.jsonl"; _p.parent.mkdir(parents=True, exist_ok=True)
    with _p.open("a") as _f: _f.write(json.dumps({"ts": time.time(), "query_token_count": len(q_tokens), "rows_count": len(flat), "ms": round((time.perf_counter() - _t0) * 1000.0, 3), "ranker": ranker_name}) + "\n")
    return ranked[: max(1, int(limit))]
