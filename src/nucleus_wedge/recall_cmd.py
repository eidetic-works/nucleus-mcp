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
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from nucleus_wedge.memories import (
    _connect,
    build_auto_memory_index,
    build_memories_index,
    memories_db_path,
)

logger = logging.getLogger("nucleus_wedge.recall_cmd")

# --- Move 2 batch 4: flag-gated read repoint (recall reads the unified SoR) ---
# Self-contained env check (mirrors store.py::_sor_flag_on) so the flag-OFF path
# stays a byte-for-byte no-op and imports nothing from mcp_server_nucleus.memory
# — nucleus_wedge stays importable stand-alone (see server.py docstring). The SoR
# facade is imported lazily, only inside the flag-ON branch.
_SOR_FLAG = "NUCLEUS_MEMORY_SOR"
_SOR_TRUTHY = frozenset({"1", "true", "yes", "on"})
# Process-wide log-once latch: a SoR read failure must degrade to legacy-only
# recall without spamming (fault isolation — the SoR read is purely additive).
_sor_read_warned = False


def _sor_flag_on() -> bool:
    """True iff ``NUCLEUS_MEMORY_SOR`` is set truthy (default False)."""
    return os.environ.get(_SOR_FLAG, "").strip().lower() in _SOR_TRUTHY


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

    Move 2 batch 4 note: this function intentionally still returns the
    ``memories.db`` path even under ``NUCLEUS_MEMORY_SOR`` — it is NOT hard
    re-pointed at ``engrams.db`` (the SoR). Callers such as
    ``memories.recall_activity_health`` query the ``memories`` table off this
    path directly; the SoR exposes an ``engrams`` table instead, so returning the
    SoR path here would break them. The SoR read is layered in as a UNION inside
    ``_do_recall_query`` (see ``_recall_from_sor`` / ``_merge_recall``) so recall
    gains the SoR while the legacy read-model — historically complete, pre-shim
    included — is never abandoned. Flag-ON is therefore never worse than flag-OFF.
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
            with _connect(db) as conn:
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
        with _connect(db) as conn:
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
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    legacy_rows = [dict(r) for r in rows]

    # Flag-OFF (default): byte-for-byte the pre-batch-4 path — return the legacy
    # memories.db result unchanged; nothing from the SoR layer is imported.
    if not _sor_flag_on():
        return legacy_rows

    # Flag-ON: UNION-READ. Layer the unified SoR (FTS5) candidates on top of the
    # legacy read-model, dedup, then rank with bm25.py (hybrid). The legacy rows
    # keep historical completeness (pre-shim included); the SoR adds FTS5 recall
    # power (the "beats grep" gate) + post-shim captures. Never worse than OFF.
    sor_rows = _recall_from_sor(
        query=query,
        limit=limit,
        kind=kind,
        tags=tags,
        since=since,
        source_filter=source_filter,
        brain_path_arg=brain_path_arg,
    )
    return _merge_recall(query, legacy_rows, sor_rows, limit)


def _recall_from_sor(
    query: str,
    limit: int,
    kind: Optional[str],
    tags: Optional[list[str]],
    since: Optional[str],
    source_filter: Optional[str],
    brain_path_arg: Optional[str],
) -> list[dict]:
    """Query the unified SoR (FTS5) via ``MemoryFacade`` and map hits into the
    wedge recall row shape ``{text, tags, created_at, source, kind}``.

    Fault-isolated: any failure (missing SoR db, import error, query error) logs
    once and returns ``[]`` so recall degrades to the legacy store rather than
    breaking — the SoR read is purely additive in this batch.
    """
    global _sor_read_warned
    try:
        from mcp_server_nucleus.memory.facade import MemoryFacade

        facade = MemoryFacade(brain_path=brain_path_arg, enabled=True)
        # Over-fetch: SorStore.search supports a single ``tags`` substring, so the
        # wedge multi-tag AND is post-filtered here — fetch headroom so that
        # filtering + dedup don't starve the merged result set.
        fetch = max(int(limit) * 4, 40)
        hits = facade.recall(
            query=query or "",
            kind=kind,
            since=since,
            surface=source_filter,
            limit=fetch,
        )
    except Exception as exc:  # noqa: BLE001 — additive read must not break recall
        if not _sor_read_warned:
            logger.warning(
                "SoR recall read failed; recall falling back to legacy store only "
                "(suppressing further SoR-read warnings this process): %s",
                exc,
            )
            _sor_read_warned = True
        return []

    mapped: list[dict] = []
    for h in hits:
        tags_str = h.get("tags") or ""
        # Preserve the wedge multi-tag AND semantics (each tag must be present).
        if tags and not all(t in tags_str for t in tags):
            continue
        mapped.append(
            {
                "text": h.get("text"),
                "tags": tags_str,
                "created_at": h.get("ts"),
                "source": h.get("source"),
                "kind": h.get("kind"),
            }
        )
    return mapped


def _merge_recall(
    query: str,
    legacy_rows: list[dict],
    sor_rows: list[dict],
    limit: int,
) -> list[dict]:
    """Union legacy (memories.db) + SoR (FTS5) candidates, dedup by
    ``(text, created_at)``, then rank.

    - With a query term: ``bm25.py`` is the scorer over the unioned candidates
      (hybrid — FTS5/SoR recalls, bm25.py ranks; the ``NUCLEUS_WEDGE_RANKER``
      re-rank still applies). No ranking regression versus the wedge BM25 path.
    - Without a query (e.g. ``recall_activity``): preserve the legacy recency
      order (``created_at`` DESC) so structured-only callers are unchanged.

    Dedup prefers the first occurrence; legacy rows are listed first so a
    dual-written record (same text+ts in both stores) is not duplicated.
    """
    merged: list[dict] = []
    seen: set = set()
    for row in (*legacy_rows, *sor_rows):
        dedup_key = (row.get("text"), row.get("created_at"))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        merged.append(row)

    cap = max(1, int(limit))
    if not (query or "").strip():
        merged.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
        return merged[:cap]

    from nucleus_wedge.bm25 import rank_candidates

    return rank_candidates(merged, query=query, limit=cap)


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
