"""Memories sidecar index — Litt's 5-col SQLite projection over history.jsonl.

Slice 1 (this commit): schema + stub entrypoint + history.jsonl path, so peer's
MCP skel can wire against a stable table shape. Slice 2 populates projection
logic; Wed+ adds auto-memory markdown ingestion under ``source='auto_memory'``.
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


def build_memories_index(brain_path: Path | None = None) -> Path:
    """Slice 2 populates history.jsonl → memories projection."""
    return ensure_schema(brain_path)
