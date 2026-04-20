"""Memories sidecar index tests — schema + history.jsonl projection.

Uses NUCLEUS_BRAIN_PATH monkeypatch fixture, mirroring test_nucleus_wedge.py.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    return brain


def _write_history(brain: Path, records: list[dict]) -> None:
    path = brain / "engrams" / "history.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


def _record(key: str, value: str, *, context: str = "note", source_agent: str = "nucleus-wedge",
            timestamp: str = "2026-04-20T10:00:00+00:00") -> dict:
    return {
        "key": key,
        "op_type": "ADD",
        "timestamp": timestamp,
        "snapshot": {
            "key": key,
            "value": value,
            "context": context,
            "intensity": 5,
            "version": 1,
            "source_agent": source_agent,
            "op_type": "ADD",
            "timestamp": timestamp,
            "deleted": False,
            "signature": None,
        },
    }


def test_schema_has_litt_five_columns(fake_brain: Path) -> None:
    from nucleus_wedge.memories import ensure_schema

    db = ensure_schema()
    with sqlite3.connect(db) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()]
    assert cols == ["id", "text", "tags", "created_at", "optional_date", "source"]


def test_build_empty_history_yields_empty_table(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index

    db = build_memories_index()
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 0


def test_build_projects_history_rows(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index

    _write_history(fake_brain, [
        _record("k1", "first note", context="note", source_agent="alpha"),
        _record("k2", "second note", context="note [#tag1,tag2]", source_agent="beta"),
    ])

    db = build_memories_index()
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT text, tags, created_at, optional_date, source "
            "FROM memories ORDER BY id"
        ).fetchall()

    assert rows == [
        ("first note", "note", "2026-04-20T10:00:00+00:00", "", "history.jsonl:alpha"),
        ("second note", "note [#tag1,tag2]", "2026-04-20T10:00:00+00:00", "", "history.jsonl:beta"),
    ]


def test_build_is_idempotent(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index

    _write_history(fake_brain, [_record("k1", "only note")])

    build_memories_index()
    db = build_memories_index()

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 1


def test_build_preserves_auto_memory_rows(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index, ensure_schema

    db = ensure_schema()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO memories (text, tags, created_at, optional_date, source) "
            "VALUES (?, ?, ?, ?, ?)",
            ("manual auto-memory", "user", "2026-04-19T00:00:00+00:00", "", "auto_memory"),
        )

    _write_history(fake_brain, [_record("k1", "history note")])
    build_memories_index()

    with sqlite3.connect(db) as conn:
        sources = sorted(r[0] for r in conn.execute("SELECT source FROM memories").fetchall())
    assert sources == ["auto_memory", "history.jsonl:nucleus-wedge"]


def test_build_skips_rows_with_empty_text(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index

    empty = _record("k1", "")
    nonempty = _record("k2", "kept")
    _write_history(fake_brain, [empty, nonempty])

    db = build_memories_index()
    with sqlite3.connect(db) as conn:
        texts = [r[0] for r in conn.execute("SELECT text FROM memories").fetchall()]
    assert texts == ["kept"]


def test_build_skips_corrupt_json_lines(fake_brain: Path) -> None:
    from nucleus_wedge.memories import build_memories_index

    path = fake_brain / "engrams" / "history.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(_record("k1", "kept")) + "\n")
        fh.write("{not json}\n")
        fh.write("\n")
        fh.write(json.dumps(_record("k2", "also kept")) + "\n")

    db = build_memories_index()
    with sqlite3.connect(db) as conn:
        texts = sorted(r[0] for r in conn.execute("SELECT text FROM memories").fetchall())
    assert texts == ["also kept", "kept"]


def test_memories_db_path_resolves_via_store(fake_brain: Path) -> None:
    from nucleus_wedge.memories import memories_db_path

    assert memories_db_path() == fake_brain / "memories.db"
