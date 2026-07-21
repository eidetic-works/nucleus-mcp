"""Source-of-record (SoR) store for the unified memory surface — Move 2 batch 1.

A WAL SQLite store-of-record, ``.brain/engrams.db``, table ``engrams`` + an FTS5
shadow (``engrams_fts``) kept in sync by triggers, plus a non-destructive
``curation_overlay`` table. This is the durable authority the ``MemoryFacade``
delegates to *when the ``NUCLEUS_MEMORY_SOR`` flag is on*; with the flag off the
facade never constructs a ``SorStore`` and this module is inert.

Design provenance (see ``scratchpad/move2_manifest.md`` Part B / Batch 0):
  - Schema mirrors ``nucleus_wedge/memories.py`` (``id, text, tags, created_at,
    optional_date, source, kind`` …) — that store is already the WAL-hardened
    read-model rebuilt from a log; Move 2 promotes the same shape into the SoR.
    Extended with ``key``, ``surface``, ``meta`` for the facade's ``capture`` API.
  - FTS5 shadow powers ranked ``recall`` (the "beats grep" product gate). Literal
    tokens containing ``.`` / ``/`` / ``-`` make FTS5 raise ``fts5: syntax
    error``; ``_fts_match`` applies the documented try-then-quote retry
    (ref: eidetic-daemon internal/store/store.go Search() PR #77, and the
    future-FTS5 note in ``runtime/vector_store.py``).
  - ``curate`` writes an overlay row pointing at the target (mirrors
    ``mcp__eidetic__nucleus_curate``); the original ``engrams`` row is never
    modified — non-destructive.

Batch 1 is scaffold only: nothing in the repo constructs an enabled facade yet,
so this store is created but not authoritative. Later batches route callers to it.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from mcp_server_nucleus.runtime.common import open_hardened_sqlite

# Valid non-destructive curation overlay actions (mirrors eidetic nucleus_curate
# plus an explicit soft ``delete``; ``delete`` is an overlay, never a row DELETE).
CURATION_ACTIONS = ("canonical", "demote", "archive", "delete")

# Curation actions that hide a row from default recall.
_HIDDEN_ACTIONS = frozenset({"archive", "delete"})

# Score deltas applied to a recall candidate by its latest overlay action.
_CANONICAL_BOOST = 10.0
_DEMOTE_PENALTY = 10.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS engrams (
    id INTEGER PRIMARY KEY,
    key TEXT,
    surface TEXT,
    text TEXT NOT NULL,
    tags TEXT,
    kind TEXT,
    meta TEXT,
    created_at TEXT,
    optional_date TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_engrams_key ON engrams(key);
CREATE INDEX IF NOT EXISTS idx_engrams_surface ON engrams(surface);
CREATE INDEX IF NOT EXISTS idx_engrams_kind ON engrams(kind);

CREATE VIRTUAL TABLE IF NOT EXISTS engrams_fts USING fts5(
    text, tags, kind, surface,
    content='engrams', content_rowid='id'
);

-- Keep the FTS5 shadow in lockstep with the engrams table.
CREATE TRIGGER IF NOT EXISTS engrams_ai AFTER INSERT ON engrams BEGIN
    INSERT INTO engrams_fts(rowid, text, tags, kind, surface)
    VALUES (new.id, new.text, new.tags, new.kind, new.surface);
END;
CREATE TRIGGER IF NOT EXISTS engrams_ad AFTER DELETE ON engrams BEGIN
    INSERT INTO engrams_fts(engrams_fts, rowid, text, tags, kind, surface)
    VALUES ('delete', old.id, old.text, old.tags, old.kind, old.surface);
END;
CREATE TRIGGER IF NOT EXISTS engrams_au AFTER UPDATE ON engrams BEGIN
    INSERT INTO engrams_fts(engrams_fts, rowid, text, tags, kind, surface)
    VALUES ('delete', old.id, old.text, old.tags, old.kind, old.surface);
    INSERT INTO engrams_fts(rowid, text, tags, kind, surface)
    VALUES (new.id, new.text, new.tags, new.kind, new.surface);
END;

CREATE TABLE IF NOT EXISTS curation_overlay (
    id INTEGER PRIMARY KEY,
    target_id INTEGER,
    target_key TEXT,
    action TEXT NOT NULL,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_curation_target ON curation_overlay(target_id);
"""

_RELATIVE_SINCE_RE = re.compile(r"^(\d+)([dhm])$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_tags(tags: Union[None, str, Iterable[str]]) -> str:
    """Coerce ``tags`` (None | str | iterable) into a single stored string."""
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags
    return ",".join(str(t) for t in tags)


def _normalize_meta(meta: Union[None, str, dict]) -> Optional[str]:
    if meta is None:
        return None
    if isinstance(meta, str):
        return meta
    return json.dumps(meta, ensure_ascii=False, sort_keys=True)


def _parse_since(since: Union[None, str]) -> Optional[str]:
    """Return an ISO lower bound for ``created_at`` from ``since``.

    Accepts a relative window ``Nd`` / ``Nh`` / ``Nm`` (computed against now) or a
    literal ISO-8601 string (returned unchanged). ``created_at`` is stored as an
    ISO-8601 UTC string, so a lexicographic ``created_at >= since`` compares
    correctly for same-shaped timestamps.
    """
    if not since:
        return None
    s = str(since).strip()
    m = _RELATIVE_SINCE_RE.match(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
        return (datetime.now(timezone.utc) - delta).isoformat()
    return s


class SorStore:
    """WAL SQLite source-of-record with an FTS5 shadow and curation overlays."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    # -- connection / schema ------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        # Inherit the shared primary-store concurrency posture
        # (WAL + busy_timeout + synchronous=NORMAL) from runtime/common.py.
        conn = open_hardened_sqlite(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # -- write --------------------------------------------------------------
    def insert(
        self,
        surface: str,
        text: str,
        *,
        kind: str = "note",
        tags: Union[None, str, Iterable[str]] = None,
        meta: Union[None, str, dict] = None,
        ts: Optional[str] = None,
        key: Optional[str] = None,
        source: str = "facade",
    ) -> dict:
        """Insert one engram into the SoR. Returns ``{id, key, ts}``."""
        if not text:
            raise ValueError("SorStore.insert: text (payload) is required")
        created_at = ts or _now_iso()
        key = key or uuid.uuid4().hex
        tags_str = _normalize_tags(tags)
        meta_str = _normalize_meta(meta)
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO engrams "
                "(key, surface, text, tags, kind, meta, created_at, optional_date, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (key, surface, text, tags_str, kind, meta_str, created_at, "", source),
            )
            row_id = cur.lastrowid
        return {"id": row_id, "key": key, "ts": created_at}

    # -- read ---------------------------------------------------------------
    def _fts_match(self, conn: sqlite3.Connection, sql: str, match_expr: str, tail_params: tuple):
        """Run an FTS5 MATCH query with the try-then-quote retry.

        Literal tokens containing ``.`` / ``/`` / ``-`` are parsed as FTS5 syntax
        and raise ``fts5: syntax error``; retry once phrase-quoting the whole
        expression (with ``"``-escape doubling). FTS5's own error string is the
        discriminator; any other OperationalError propagates unchanged.
        """
        try:
            return conn.execute(sql, (match_expr, *tail_params)).fetchall()
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "fts5" in msg or "syntax error" in msg or "no such column" in msg:
                quoted = '"' + match_expr.replace('"', '""') + '"'
                return conn.execute(sql, (quoted, *tail_params)).fetchall()
            raise

    def _latest_overlays(self, conn: sqlite3.Connection) -> dict:
        """Map ``target_id`` -> latest overlay action (by overlay row id)."""
        rows = conn.execute(
            "SELECT target_id, action FROM curation_overlay co "
            "WHERE co.id = (SELECT MAX(id) FROM curation_overlay WHERE target_id = co.target_id)"
        ).fetchall()
        return {r["target_id"]: r["action"] for r in rows}

    def search(
        self,
        query: str = "",
        *,
        kind: Optional[str] = None,
        tags: Optional[str] = None,
        since: Union[None, str] = None,
        surface: Optional[str] = None,
        limit: int = 10,
        include_archived: bool = False,
    ) -> list:
        """Ranked recall over the SoR. FTS5 when ``query`` is non-empty, else a
        structured scan; both apply the same structured filters and curation
        overlay. Returns ``[{id, key, text, kind, tags, surface, ts, score,
        source, curation}]`` sorted best-first."""
        filters = []
        filter_params: list = []
        if kind is not None:
            filters.append("e.kind = ?")
            filter_params.append(kind)
        if surface is not None:
            filters.append("e.surface = ?")
            filter_params.append(surface)
        if tags:
            filters.append("e.tags LIKE ?")
            filter_params.append(f"%{tags}%")
        since_iso = _parse_since(since)
        if since_iso:
            filters.append("e.created_at >= ?")
            filter_params.append(since_iso)
        where_extra = (" AND " + " AND ".join(filters)) if filters else ""

        # Fetch headroom so curation-hidden rows don't starve the result set.
        fetch_cap = max(limit * 4, 40)
        rows: list = []
        with self._connect() as conn:
            if query:
                sql = (
                    "SELECT e.id, e.key, e.surface, e.text, e.tags, e.kind, "
                    "e.created_at, e.source, bm25(engrams_fts) AS rank "
                    "FROM engrams_fts JOIN engrams e ON e.id = engrams_fts.rowid "
                    "WHERE engrams_fts MATCH ?" + where_extra +
                    " ORDER BY rank LIMIT ?"
                )
                raw = self._fts_match(conn, sql, query, (*filter_params, fetch_cap))
                # bm25: lower is more relevant → negate so higher == better.
                candidates = [(r, -float(r["rank"])) for r in raw]
            else:
                sql = (
                    "SELECT e.id, e.key, e.surface, e.text, e.tags, e.kind, "
                    "e.created_at, e.source "
                    "FROM engrams e WHERE 1=1" + where_extra +
                    " ORDER BY e.id DESC LIMIT ?"
                )
                raw = conn.execute(sql, (*filter_params, fetch_cap)).fetchall()
                candidates = [(r, 1.0) for r in raw]
            overlays = self._latest_overlays(conn)

        results = []
        for row, base_score in candidates:
            action = overlays.get(row["id"])
            if action in _HIDDEN_ACTIONS and not include_archived:
                continue
            score = base_score
            if action == "canonical":
                score += _CANONICAL_BOOST
            elif action == "demote":
                score -= _DEMOTE_PENALTY
            results.append({
                "id": row["id"],
                "key": row["key"],
                "text": row["text"],
                "kind": row["kind"],
                "tags": row["tags"],
                "surface": row["surface"],
                "ts": row["created_at"],
                "score": score,
                "source": row["source"],
                "curation": action,
            })
        results.sort(key=lambda d: (d["score"], d["id"]), reverse=True)
        return results[:limit]

    # -- curate (non-destructive overlay) -----------------------------------
    def curate(self, target: Union[int, str], action: str) -> dict:
        """Attach a non-destructive curation overlay to ``target`` (id or key).

        The ``engrams`` row is never modified; an overlay row records the action.
        ``action`` ∈ {canonical, demote, archive, delete}.
        """
        if action not in CURATION_ACTIONS:
            raise ValueError(
                f"SorStore.curate: action must be one of {CURATION_ACTIONS}, got {action!r}"
            )
        with self._connect() as conn:
            if isinstance(target, int):
                row = conn.execute(
                    "SELECT id, key FROM engrams WHERE id = ?", (target,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, key FROM engrams WHERE key = ? ORDER BY id DESC LIMIT 1",
                    (target,),
                ).fetchone()
            if row is None:
                return {"ok": False, "reason": "target not found", "target": target}
            conn.execute(
                "INSERT INTO curation_overlay (target_id, target_key, action, created_at) "
                "VALUES (?, ?, ?, ?)",
                (row["id"], row["key"], action, _now_iso()),
            )
        return {"ok": True, "id": row["id"], "key": row["key"], "action": action}

    # -- introspection ------------------------------------------------------
    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM engrams").fetchone()[0])
