"""``nucleus-wedge recall`` CLI — SQLite-backed recall over ``memories.db``.

Pairs with ``bench first_recall`` so cold-start recall can be stopwatched
as a subprocess call (Phase 6 criterion #1, Fri acceptance).

Auto-builds ``memories.db`` on first call (history projection + auto-memory
ingest). Subsequent calls hit the populated index directly. Ranking is
case-insensitive substring match on text+tags, recency-ordered.

ADR-0033 v3 Phase 0.5 extension: `do_recall` accepts structured `kind` /
`tags` / `since` filters. When at least one structured filter is present,
the empty-query assertion is relaxed (recall_cmd.py:42/43 historical line).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from nucleus_wedge.memories import (
    build_auto_memory_index,
    build_memories_index,
    memories_db_path,
)


def _ensure_populated(brain_path_arg: str | None) -> Path:
    """Return the memories.db path, rebuilding the projection if stale.

    The projection is rebuilt when ANY of:
      - memories.db does not exist
      - memories.db table is empty
      - history.jsonl has been modified at-or-after memories.db
        (PR #437 v1 used `>`; #447 v2 uses `>=` per cc-main Loop #6 finding
        — same-second write+recall was silently swallowed when stat()
        precision couldn't distinguish them within float-second quantum)
      - history.jsonl line count > projected history-source row count
        (#447 v2 row-count sanity check — defensive against rsync-preserved-
        mtime imports, coarse fs mtime, edge cases where mtime doesn't
        reflect content. Cost ~50ms on 8K-line file; acceptable as safety
        net on per-call path that could otherwise silently return stale data)

    The mtime check is fast path; row-count is safety net.
    """
    from nucleus_wedge.memories import history_jsonl_path

    brain = Path(brain_path_arg).expanduser() if brain_path_arg else None
    db = memories_db_path(brain)
    history = history_jsonl_path(brain)

    # #447 v2: `>=` not `>` so same-second write+recall doesn't get swallowed.
    # After build, db.mtime > history.mtime (build wrote later), so `>=` still
    # returns False on no-write case. New write at T_remember updates
    # history.mtime ≥ db.mtime → check fires.
    stale_vs_history_mtime = (
        db.exists()
        and history.exists()
        and history.stat().st_mtime >= db.stat().st_mtime
    )

    # #447 v2: row-count sanity check catches edges mtime misses.
    # Match HISTORY_SOURCE_PREFIX = "history.jsonl" (memories.py L36); rows
    # are written with source = "history.jsonl" or "history.jsonl:<agent>".
    stale_vs_history_rowcount = False
    if db.exists() and history.exists() and not stale_vs_history_mtime:
        try:
            with open(history, "rb") as fh:
                history_lines = sum(1 for _ in fh)
            with sqlite3.connect(db, timeout=5.0) as conn:
                projected_rows = conn.execute(
                    "SELECT COUNT(*) FROM memories "
                    "WHERE source = 'history.jsonl' OR source LIKE 'history.jsonl:%'"
                ).fetchone()[0]
            if history_lines > projected_rows:
                stale_vs_history_rowcount = True
        except (OSError, sqlite3.Error):
            # Defensive: any I/O or DB error → fall through to rebuild.
            stale_vs_history_rowcount = True

    if db.exists() and not stale_vs_history_mtime and not stale_vs_history_rowcount:
        with sqlite3.connect(db, timeout=5.0) as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count > 0:
            return db
    build_memories_index(brain)
    build_auto_memory_index(brain)
    return memories_db_path(brain)


def _do_recall_query(
    query: str,
    limit: int,
    kind: Optional[str],
    tags: Optional[list[str]],
    since: Optional[str],
    source_filter: Optional[str],
    brain_path_arg: Optional[str],
) -> list[dict]:
    """Execute one structured recall query and return rows as a list of dicts.

    Used by both the CLI `do_recall` and the `recall_activity` MCP wrapper.
    """
    db = _ensure_populated(brain_path_arg)
    sql_parts: list[str] = [
        "SELECT text, tags, created_at, source, kind FROM memories WHERE 1=1"
    ]
    params: list[object] = []
    q = (query or "").strip()
    if q:
        like = f"%{q.lower()}%"
        sql_parts.append("AND (LOWER(text) LIKE ? OR LOWER(tags) LIKE ?)")
        params.extend([like, like])
    if kind:
        sql_parts.append("AND kind = ?")
        params.append(kind)
    if tags:
        for tag in tags:
            sql_parts.append("AND tags LIKE ?")
            params.append(f"%{tag}%")
    if since:
        sql_parts.append("AND created_at >= ?")
        params.append(since)
    if source_filter:
        sql_parts.append("AND source LIKE ?")
        params.append(source_filter)
    sql_parts.append("ORDER BY created_at DESC LIMIT ?")
    params.append(limit)
    sql = " ".join(sql_parts)
    with sqlite3.connect(db, timeout=5.0) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def do_recall(
    query: str = "",
    limit: int = 5,
    source_filter: Optional[str] = None,
    brain_path_arg: Optional[str] = None,
    kind: Optional[str] = None,
    tags: Optional[list[str]] = None,
    since: Optional[str] = None,
) -> int:
    """CLI entry point — extended signature per ADR-0033 v3 §A.

    Backward-compat: existing callers passing only `query` still work
    unchanged; the empty-query assertion is relaxed only when at least one
    structured filter (`kind`, `tags`, or `since`) is present.
    """
    has_structured_filter = bool(kind or tags or since)
    if not query or not query.strip():
        if not has_structured_filter:
            print(
                "recall: --query must be non-empty (or pass --kind/--tags/--since)",
                file=sys.stderr,
            )
            return 2
    payload = _do_recall_query(
        query=query or "",
        limit=limit,
        kind=kind,
        tags=tags,
        since=since,
        source_filter=source_filter,
        brain_path_arg=brain_path_arg,
    )
    print(json.dumps(payload, indent=2))
    return 0
