"""Memories sidecar index — Litt's 5-col SQLite projection over history.jsonl.

Schema + history.jsonl projection so Claude Code can recall in <30s via SQLite
instead of JSONL rescan. Auto-memory markdown ingest lands in a later slice
under ``source='auto_memory'``.
"""
from __future__ import annotations

import sqlite3
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
