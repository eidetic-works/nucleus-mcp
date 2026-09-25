"""Candidate ranker: BM25 score * per-kind weight.

Hypothesis: agent-authored 'activity' engrams + 'feedback' memory files are
typically MORE relevant for recall than ambient capture (cursor / claude_code
session transcripts). Per #440 v1 fix direction (c).

Boost map (kind → multiplier):
  activity   3.0   (agent-authored activity engrams — high signal)
  feedback   2.5   (auto-memory feedback files — operator-curated rules)
  decision   2.0   (decisions / ADRs)
  note       1.5
  unknown    1.0   (fallback)
"""

from __future__ import annotations

import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(PKG_ROOT))

KIND_BOOST = {
    "activity": 3.0,
    "feedback": 2.5,
    "decision": 2.0,
    "note": 1.5,
    "unknown": 1.0,
}


def _extract_kind(record: dict) -> str:
    """Recover kind from record. Tries common shapes; falls back to 'unknown'."""
    kind = record.get("kind") or ""
    if not kind:
        return "unknown"
    # kind may be bracketed like "[note: foo]" or bare "note"
    if isinstance(kind, str) and kind.startswith("["):
        # extract leading word before ':'
        kind = kind.lstrip("[").split(":", 1)[0].strip()
    return kind.lower() or "unknown"


def rank(query: str, limit: int = 5) -> list[dict]:
    from nucleus_wedge import bm25 as _bm25
    from nucleus_wedge.store import Store

    store = Store(Store.brain_path(None))
    candidates = _bm25.search(store, query=query, limit=max(limit * 5, 25))

    for c in candidates:
        kind = _extract_kind(c)
        boost = KIND_BOOST.get(kind, KIND_BOOST["unknown"])
        c["score"] = c["score"] * boost
        c["_kind_extracted"] = kind
        c["_kind_boost"] = boost

    candidates.sort(key=lambda r: r["score"], reverse=True)
    return candidates[:limit]
