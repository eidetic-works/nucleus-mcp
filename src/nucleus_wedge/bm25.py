"""In-memory BM25 over Store rows. Rebuild on every ``search`` call (Day-1; 2615 rows ≪ 50 ms)."""
from __future__ import annotations

import json, os, re, time
from pathlib import Path
from typing import Iterable

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from nucleus_wedge.store import Store

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def search(
    store: Store,
    query: str,
    limit: int = 5,
    kind: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """Rank history rows by BM25 on ``value``. Optional filters: ``kind`` (exact context prefix), ``since`` (ISO-8601 lex-comparable)."""
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
    )
    _p = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")) / "metrics" / "recall_timings.jsonl"; _p.parent.mkdir(parents=True, exist_ok=True)
    with _p.open("a") as _f: _f.write(json.dumps({"ts": time.time(), "query_token_count": len(q_tokens), "rows_count": len(flat), "ms": round((time.perf_counter() - _t0) * 1000.0, 3)}) + "\n")
    return ranked[: max(1, int(limit))]
