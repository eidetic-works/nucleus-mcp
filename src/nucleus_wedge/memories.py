"""Memories sidecar index — Litt's 5-col SQLite projection over history.jsonl.

Schema + history.jsonl projection + auto-memory markdown ingest so Claude Code
can recall in <30s via SQLite instead of JSONL rescan.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .store import Store

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


def ensure_schema(brain_path: Path | None = None) -> Path:
    db = memories_db_path(brain_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.executescript(SCHEMA)
    return db


def _project_row(row: dict) -> tuple[str, str, str, str, str] | None:
    snap = row.get("snapshot") or {}
    text = snap.get("value") or row.get("value")
    if not text:
        return None
    tags = snap.get("context") or ""
    created_at = snap.get("timestamp") or row.get("timestamp") or ""
    source_agent = snap.get("source_agent") or ""
    source = f"{HISTORY_SOURCE_PREFIX}:{source_agent}" if source_agent else HISTORY_SOURCE_PREFIX
    return (text, tags, created_at, "", source)


def build_memories_index(brain_path: Path | None = None) -> Path:
    """Rebuild history-projected rows. Auto-memory rows are preserved."""
    db = ensure_schema(brain_path)
    store = Store(Store.brain_path(brain_path))
    rows = [r for r in (_project_row(row) for row in store.rows()) if r is not None]
    with sqlite3.connect(db) as conn:
        conn.execute(
            "DELETE FROM memories WHERE source = ? OR source LIKE ?",
            (HISTORY_SOURCE_PREFIX, f"{HISTORY_SOURCE_PREFIX}:%"),
        )
        conn.executemany(
            "INSERT INTO memories (text, tags, created_at, optional_date, source) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
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


def _project_memory_file(path: Path) -> tuple[str, str, str, str, str] | None:
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
    return (text, mem_type, created_at, "", AUTO_MEMORY_SOURCE)


def build_auto_memory_index(
    brain_path: Path | None = None,
    memory_root: Path | None = None,
) -> Path:
    """Ingest auto-memory markdown files. History-projected rows are preserved."""
    db = ensure_schema(brain_path)
    root = memory_root or default_auto_memory_root()
    rows: list[tuple[str, str, str, str, str]] = []
    if root.exists():
        for md in sorted(root.glob("*.md")):
            projected = _project_memory_file(md)
            if projected is not None:
                rows.append(projected)
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM memories WHERE source = ?", (AUTO_MEMORY_SOURCE,))
        conn.executemany(
            "INSERT INTO memories (text, tags, created_at, optional_date, source) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    return db
