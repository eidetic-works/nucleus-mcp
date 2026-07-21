"""Memories sidecar index — SQLite projection over history.jsonl.

Per ADR-0033 v3 §A (Phase 0.5): adds a real `kind` column to the projection so
`nucleus_wedge__recall(kind='activity', tags=['role:main', 'domain:tb-endpoint'], since='30d')`
works as a real structured query, instead of substring-matching against the
legacy concat string `f"{kind} [#{tags}]"`.

Backfill 3-branch rule (idempotent — checks if column exists before adding):
    1. context matches `f"{kind} [#{tags}]"` → split kind + tags as-is
    2. else context matches known legacy taxonomy (Strategy|Feature|...) →
       set kind='note', legacy_context=<word>
    3. else → set kind='unknown', legacy_context=<original>
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .store import Store, _provenance_anchor_flag_on, verify_record
from .role_normalize import _normalize_role

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    tags TEXT,
    created_at TEXT,
    optional_date TEXT,
    source TEXT
);
"""

HISTORY_SOURCE_PREFIX = "history.jsonl"
AUTO_MEMORY_SOURCE = "auto_memory"

# Legacy single-word context values to coerce into kind='note' on backfill
# (per ADR-0033 v3 §A branch #2). These are the bare-word `context` values
# observed in 87% of pre-Phase-0.5 records.
_LEGACY_TAXONOMY = {"Strategy", "Feature", "Architecture", "Decision", "Brand"}

# Regex for branch #1: bracket-tag form `kind [#tag1,tag2]`
_BRACKET_TAG_RE = re.compile(r"^(?P<kind>\S+)\s*\[#(?P<tags>[^\]]*)\]\s*$")

logger = logging.getLogger("nucleus_wedge.memories")

# Primary-store concurrency posture (mirrors runtime/db.py SQLiteBackend._get_conn):
# WAL lets concurrent readers coexist with one writer, busy_timeout makes writers
# wait on a lock instead of raising immediately, synchronous=NORMAL is durable
# enough under WAL while being faster than FULL.
_HARDENING_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
)
_pragma_warned = False


def _connect(db: Path | str) -> sqlite3.Connection:
    """Open ``memories.db`` with the primary-store concurrency posture.

    ``connect(timeout=10)`` + WAL + ``busy_timeout=5000`` + ``synchronous=NORMAL``
    — the same hardening ``runtime/db.py`` applies to the primary store — so
    concurrent wedge writers wait on the lock rather than failing with
    ``database is locked``.

    PRAGMA application degrades gracefully: on a read-only filesystem WAL cannot
    create the ``-wal``/``-shm`` sidecars, so a PRAGMA failure is logged once and
    the (still usable) connection is returned in whatever journal mode the DB
    already has, rather than raising. Default ``isolation_level`` is preserved so
    ``with _connect(db) as conn:`` keeps committing on block exit as before.
    """
    conn = sqlite3.connect(str(db), timeout=10)
    global _pragma_warned
    try:
        for pragma in _HARDENING_PRAGMAS:
            conn.execute(pragma)
    except sqlite3.Error as exc:  # pragma: no cover - read-only-FS degrade path
        if not _pragma_warned:
            logger.warning("memories.db PRAGMA hardening skipped (%s); continuing", exc)
            _pragma_warned = True
    return conn


def _checkpoint(conn: sqlite3.Connection) -> None:
    """Flush the WAL into the main ``memories.db`` file after a write.

    ``recall_cmd._ensure_populated`` decides whether to rebuild the projection by
    comparing the main ``memories.db`` file mtime against ``history.jsonl``. Under
    WAL, an INSERT lands in the ``-wal`` sidecar and the main file's mtime is not
    bumped until a checkpoint — so without this flush every recall would see the
    db as stale and rebuild. Checkpoint failures (read-only FS, busy) degrade
    silently: the worst case is the pre-existing rebuild, never a raise.
    """
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:  # pragma: no cover - read-only-FS / busy degrade path
        pass


def default_auto_memory_root() -> Path:
    """CC auto-memory dir for the current project: ``~/.claude/projects/<slug>/memory``.

    ``<slug>`` is the current working directory's absolute POSIX path with ``/``
    replaced by ``-`` (matches Claude Code's own slug convention).
    """
    slug = str(Path.cwd().resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug / "memory"


def memories_db_path(brain_path: Path | None = None) -> Path:
    return Store.brain_path(brain_path) / "memories.db"


def history_jsonl_path(brain_path: Path | None = None) -> Path:
    return Store.brain_path(brain_path) / "engrams" / "history.jsonl"


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())


def _ensure_kind_columns(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add `kind` + `legacy_context` columns if absent."""
    if not _column_exists(conn, "memories", "kind"):
        conn.execute("ALTER TABLE memories ADD COLUMN kind TEXT")
    if not _column_exists(conn, "memories", "legacy_context"):
        conn.execute("ALTER TABLE memories ADD COLUMN legacy_context TEXT")


def ensure_schema(brain_path: Path | None = None) -> Path:
    db = memories_db_path(brain_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db) as conn:
        conn.executescript(SCHEMA)
        _ensure_kind_columns(conn)
    return db


def _split_context(context: str) -> tuple[str, str, Optional[str]]:
    """Apply ADR-0033 v3 §A 3-branch backfill rule to a single `context` value.

    Returns:
        (kind, tags_str, legacy_context) where:
          - branch #1 (bracket form): split kind + tags as-is; legacy_context=None
          - branch #2 (legacy bare word): kind='note', tags='', legacy_context=<word>
          - branch #3 (everything else): kind='unknown', tags='', legacy_context=<original>
    """
    if context is None:
        return ("unknown", "", "")
    s = context.strip()
    m = _BRACKET_TAG_RE.match(s)
    if m:
        return (m.group("kind"), m.group("tags").strip(), None)
    if s in _LEGACY_TAXONOMY:
        return ("note", "", s)
    return ("unknown", "", s)


def _project_row(row: dict, brain_path: Path | None = None) -> tuple | None:
    """Project one history.jsonl row into the (text, tags, created_at, optional_date,
    source, kind, legacy_context) 7-tuple for the extended memories table.

    A11 (recall provenance anchoring): when ``NUCLEUS_RECALL_PROVENANCE_ANCHOR``
    is on, a row whose snapshot carries a ``signature`` that FAILS verification
    is dropped from the index entirely — this is the read-side defense against
    a record spliced directly into ``history.jsonl`` bypassing ``Store.append``
    (which cannot forge the HMAC without the server secret). A row with no
    signature at all (legacy/pre-A11) passes through unchanged — flag-ON is
    additive over legacy data, not a retroactive rejection of it. Flag-OFF is
    a byte-for-byte no-op (this check is skipped entirely).
    """
    snap = row.get("snapshot") or {}
    text = snap.get("value") or row.get("value")
    if not text:
        return None
    if _provenance_anchor_flag_on() and snap.get("signature") and not verify_record(snap, brain_path):
        return None  # forged/tampered signature — excluded from recall's index
    raw_context = snap.get("context") or ""
    kind, tags, legacy_context = _split_context(raw_context)
    # Keep the legacy `tags` column populated with the original context for
    # backward-compat with substring `LIKE` queries; new structured queries
    # use the kind / parsed-tags fields.
    tags_col = raw_context
    created_at = snap.get("timestamp") or row.get("timestamp") or ""
    source_agent = snap.get("source_agent") or ""
    source = f"{HISTORY_SOURCE_PREFIX}:{source_agent}" if source_agent else HISTORY_SOURCE_PREFIX
    return (text, tags_col, created_at, "", source, kind, legacy_context or "")


def build_memories_index(brain_path: Path | None = None) -> Path:
    """Rebuild history-projected rows. Auto-memory rows are preserved."""
    db = ensure_schema(brain_path)
    resolved_brain = Store.brain_path(brain_path)
    store = Store(resolved_brain)
    rows = [
        r for r in (_project_row(row, resolved_brain) for row in store.rows())
        if r is not None
    ]
    conn = _connect(db)
    try:
        conn.execute(
            "DELETE FROM memories WHERE source = ? OR source LIKE ?",
            (HISTORY_SOURCE_PREFIX, f"{HISTORY_SOURCE_PREFIX}:%"),
        )
        conn.executemany(
            "INSERT INTO memories "
            "(text, tags, created_at, optional_date, source, kind, legacy_context) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        _checkpoint(conn)
    finally:
        conn.close()
    return db


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content
    try:
        end = content.index("\n---\n", 4)
    except ValueError:
        return {}, content
    front = content[4:end]
    body = content[end + 5:].lstrip("\n")
    meta: dict[str, str] = {}
    for line in front.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, body


def _project_memory_file(path: Path) -> tuple | None:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    meta, body = _parse_frontmatter(content)
    mem_type = meta.get("type", "")
    if not mem_type:
        return None
    name = meta.get("name") or path.stem
    description = meta.get("description", "")
    parts = [name]
    if description:
        parts.append(description)
    body = body.strip()
    if body:
        parts.append(body)
    text = "\n\n".join(parts)
    created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    # auto_memory rows: kind = mem_type (e.g., "feedback"); legacy_context = "".
    return (text, mem_type, created_at, "", AUTO_MEMORY_SOURCE, mem_type, "")


def build_auto_memory_index(
    brain_path: Path | None = None,
    memory_root: Path | None = None,
) -> Path:
    """Ingest auto-memory markdown files. History-projected rows are preserved."""
    db = ensure_schema(brain_path)
    root = memory_root or default_auto_memory_root()
    rows: list[tuple] = []
    if root.exists():
        for md in sorted(root.glob("*.md")):
            projected = _project_memory_file(md)
            if projected is not None:
                rows.append(projected)
    conn = _connect(db)
    try:
        conn.execute("DELETE FROM memories WHERE source = ?", (AUTO_MEMORY_SOURCE,))
        conn.executemany(
            "INSERT INTO memories "
            "(text, tags, created_at, optional_date, source, kind, legacy_context) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        _checkpoint(conn)
    finally:
        conn.close()
    return db


# ---- ADR-0033 v3 §C — lazy recall MCP tool surface helpers ----------------


def _parse_since(since: str) -> str:
    """Parse a `since` token into an ISO-8601 lower bound for lex compare.

    Accepted forms:
      - Nd / Nh / Nm (relative window, e.g. `30d`, `24h`, `15m`)
      - ISO-8601 timestamp passed through unchanged
    """
    s = since.strip()
    if not s:
        return ""
    m = re.match(r"^(\d+)([dhm])$", s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
        return (datetime.now(timezone.utc) - delta).isoformat()
    return s


def recall_activity(
    role: str,
    domain: Optional[str] = None,
    since: str = "30d",
    limit: int = 10,
    brain_path: Path | None = None,
) -> dict:
    """Thin wrapper over the Phase 0.5 extended `do_recall` for activity engrams.

    Per ADR-0033 v3 §C: returns the canonicalized agent role's prior activity
    in a given domain (or all domains), within the time window.
    """
    from nucleus_wedge.recall_cmd import _do_recall_query

    canonical = _normalize_role(role)
    tags = [f"role:{canonical}"]
    if domain:
        tags.append(f"domain:{domain}")
    results = _do_recall_query(
        query="",
        limit=limit,
        kind="activity",
        tags=tags,
        since=_parse_since(since),
        source_filter=None,
        brain_path_arg=str(brain_path) if brain_path else None,
    )
    return {
        "role": canonical,
        "domain": domain,
        "since": since,
        "results": results,
    }


def recall_activity_health(
    role: Optional[str] = None,
    brain_path: Path | None = None,
) -> dict:
    """Per ADR-0033 v3 §D: report last activity-digest timestamp per role.

    For each role (all canonical roles if none specified): query the most
    recent activity engram timestamp and bucket into:
      - fresh        (<24h)
      - stale        (24-168h / 1-7d)
      - silent-fail  (>168h / 7d)
    """
    from nucleus_wedge.role_normalize import canonical_roles
    from nucleus_wedge.recall_cmd import _ensure_populated

    db = _ensure_populated(str(brain_path) if brain_path else None)
    if role is None:
        roles_to_check = [r for r in canonical_roles() if r != "unknown"]
    else:
        roles_to_check = [_normalize_role(role)]
    now = datetime.now(timezone.utc)
    out_roles: list[dict] = []
    with _connect(db) as conn:
        for r in roles_to_check:
            row = conn.execute(
                "SELECT MAX(created_at) FROM memories "
                "WHERE kind = 'activity' AND tags LIKE ?",
                (f"%role:{r}%",),
            ).fetchone()
            last = (row[0] or "") if row else ""
            if not last:
                out_roles.append({
                    "role": r,
                    "last_digest_at": None,
                    "age_hours": None,
                    "status": "silent-fail",
                })
                continue
            try:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_h = (now - last_dt).total_seconds() / 3600.0
            except ValueError:
                age_h = None
            if age_h is None:
                status = "silent-fail"
            elif age_h < 24:
                status = "fresh"
            elif age_h < 168:
                status = "stale"
            else:
                status = "silent-fail"
            out_roles.append({
                "role": r,
                "last_digest_at": last,
                "age_hours": round(age_h, 2) if age_h is not None else None,
                "status": status,
            })
    return {"roles": out_roles}


# ---- MCP tool surface aliases + write_activity helper ---------------------
# The board's runtime/board_ops.py reaches for `nucleus_wedge__recall_activity`
# and `nucleus_wedge__write_activity` via getattr — those are the canonical
# MCP-namespaced symbol names. Below: aliases for recall + a thin write
# wrapper that funnels through Store.append with the standard kind/tag shape.


def nucleus_wedge__write_activity(
    role: str,
    content: str,
    domain: Optional[str] = None,
    tags: Optional[list[str]] = None,
    extra_tags: Optional[list[str]] = None,
    brain_path: Path | None = None,
) -> dict:
    """Per ADR-0033 v3 §B: append one activity engram.

    Bridge-compatible signature: accepts either (a) `domain=` + optional
    `extra_tags=` (legacy direct caller), or (b) `tags=[...]` (board_ops
    `_try_write_activity_engram` bridge). Canonicalizes role via
    `_normalize_role` at write-time. Calls `Store.append`, which preserves
    canonical tag form via its own `_normalize_tags` helper (defense in
    depth against drift).
    """
    canonical = _normalize_role(role)
    final_tags: list[str] = [f"role:{canonical}"]
    if domain:
        final_tags.append(f"domain:{domain}")
    if tags:
        # Bridge path: tags already include role:<x> + domain:<d> + extras.
        # Dedupe role tag (we just added the canonical form) + skip dupes.
        for t in tags:
            if t.startswith("role:"):
                continue  # canonical role already added above
            if t not in final_tags:
                final_tags.append(t)
    if extra_tags:
        for t in extra_tags:
            if t not in final_tags:
                final_tags.append(t)
    store = Store(Store.brain_path(brain_path))
    return store.append(value=content, kind="activity", tags=final_tags)


# Canonical MCP symbol aliases — board_ops + future MCP registrations use these
nucleus_wedge__recall_activity = recall_activity
nucleus_wedge__recall_activity_health = recall_activity_health
