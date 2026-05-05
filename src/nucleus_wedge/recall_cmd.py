"""``nucleus-wedge recall`` CLI — SQLite-backed recall over ``memories.db``.

Pairs with ``bench first_recall`` so cold-start recall can be stopwatched
as a subprocess call (Phase 6 criterion #1, Fri acceptance).

Auto-builds ``memories.db`` on first call (history projection + auto-memory
ingest). Subsequent calls hit the populated index directly. Ranking is
case-insensitive substring match on text+tags, recency-ordered.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from nucleus_wedge.memories import (
    build_auto_memory_index,
    build_memories_index,
    memories_db_path,
)


def _ensure_populated(brain_path_arg: str | None) -> Path:
    brain = Path(brain_path_arg).expanduser() if brain_path_arg else None
    db = memories_db_path(brain)
    if db.exists():
        with sqlite3.connect(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count > 0:
            return db
    build_memories_index(brain)
    build_auto_memory_index(brain)
    return memories_db_path(brain)


def do_recall(
    query: str,
    limit: int,
    source_filter: str | None,
    brain_path_arg: str | None,
) -> int:
    if not query.strip():
        print("recall: --query must be non-empty", file=sys.stderr)
        return 2
    db = _ensure_populated(brain_path_arg)
    like = f"%{query.lower()}%"
    sql = (
        "SELECT text, tags, created_at, source FROM memories "
        "WHERE (LOWER(text) LIKE ? OR LOWER(tags) LIKE ?)"
    )
    params: list[object] = [like, like]
    if source_filter:
        sql += " AND source LIKE ?"
        params.append(source_filter)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    payload = [dict(r) for r in rows]
    print(json.dumps(payload, indent=2))
    return 0
