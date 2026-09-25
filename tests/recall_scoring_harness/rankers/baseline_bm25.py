"""Baseline ranker: current production BM25 (mcp-server-nucleus/src/nucleus_wedge/bm25.py).

Wraps the production bm25.search so the harness measures EXACTLY what runs
in production. Any ranking-quality regression vs baseline shows up immediately
in harness numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(PKG_ROOT))


def rank(query: str, limit: int = 5) -> list[dict]:
    """Run current production BM25 ranker; return [{key, score, ...}]."""
    from nucleus_wedge import bm25 as _bm25
    from nucleus_wedge.store import Store

    store = Store(Store.brain_path(None))
    return _bm25.search(store, query=query, limit=limit)
