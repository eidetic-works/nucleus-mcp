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


def test_schema_has_extended_columns(fake_brain: Path) -> None:
    """Every column recall depends on exists after the idempotent migration.

    Asserts a SUPERSET, not exact equality. The previous version compared the
    column list for equality, so it failed on any ADDITIVE migration — it broke
    when origin_repo/origin_session were added (fw-1786153512 defect 3) even
    though nothing it actually protects had regressed. A schema test should
    fail when a required column DISAPPEARS, which is the real regression;
    failing when a new one appears just trains people to edit the test.
    """
    from nucleus_wedge.memories import ensure_schema

    db = ensure_schema()
    with sqlite3.connect(db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()}
    required = {
        "id", "text", "tags", "created_at", "optional_date", "source",
        "kind", "legacy_context", "origin_repo", "origin_session",
    }
    missing = required - cols
    assert not missing, f"memories schema is missing required columns: {sorted(missing)}"


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


def _write_memory_file(root: Path, stem: str, *, name: str, description: str,
                       mem_type: str, body: str) -> Path:
    path = root / f"{stem}.md"
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def test_auto_memory_ingest_populates_table(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index

    mem_root = tmp_path / "memory"
    mem_root.mkdir()
    _write_memory_file(mem_root, "feedback_alpha",
                       name="Alpha rule", description="Short desc.",
                       mem_type="feedback", body="Body of alpha.")
    _write_memory_file(mem_root, "project_beta",
                       name="Beta project", description="Project desc.",
                       mem_type="project", body="Project body text.")

    db = build_auto_memory_index(memory_root=mem_root)
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT text, tags, source FROM memories ORDER BY tags, text"
        ).fetchall()

    assert len(rows) == 2
    assert all(row[2] == "auto_memory" for row in rows)
    assert rows[0][1] == "feedback"
    assert "Alpha rule" in rows[0][0] and "Short desc." in rows[0][0] and "Body of alpha." in rows[0][0]
    assert rows[1][1] == "project"


def test_auto_memory_skips_files_without_frontmatter_type(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index

    mem_root = tmp_path / "memory"
    mem_root.mkdir()
    (mem_root / "MEMORY.md").write_text("# Index\n\n- pointer-a\n- pointer-b\n", encoding="utf-8")
    _write_memory_file(mem_root, "user_lokesh",
                       name="Lokesh profile", description="Founder.",
                       mem_type="user", body="Body.")

    db = build_auto_memory_index(memory_root=mem_root)
    with sqlite3.connect(db) as conn:
        tags = [r[0] for r in conn.execute("SELECT tags FROM memories").fetchall()]
    assert tags == ["user"]


def test_auto_memory_ingest_is_idempotent(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index

    mem_root = tmp_path / "memory"
    mem_root.mkdir()
    _write_memory_file(mem_root, "feedback_x",
                       name="X", description="", mem_type="feedback", body="only")

    build_auto_memory_index(memory_root=mem_root)
    db = build_auto_memory_index(memory_root=mem_root)

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 1


def test_auto_memory_preserves_history_rows(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index, build_memories_index

    _write_history(fake_brain, [_record("k1", "history row")])
    build_memories_index()

    mem_root = tmp_path / "memory"
    mem_root.mkdir()
    _write_memory_file(mem_root, "user_x",
                       name="User note", description="", mem_type="user", body="body")

    db = build_auto_memory_index(memory_root=mem_root)
    with sqlite3.connect(db) as conn:
        sources = sorted(r[0] for r in conn.execute("SELECT source FROM memories").fetchall())
    assert sources == ["auto_memory", "history.jsonl:nucleus-wedge"]


def test_auto_memory_missing_root_is_noop(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index

    db = build_auto_memory_index(memory_root=tmp_path / "does-not-exist")
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    assert count == 0


def test_auto_memory_falls_back_to_stem_when_name_missing(fake_brain: Path, tmp_path: Path) -> None:
    from nucleus_wedge.memories import build_auto_memory_index

    mem_root = tmp_path / "memory"
    mem_root.mkdir()
    (mem_root / "feedback_nameless.md").write_text(
        "---\ndescription: no name key\ntype: feedback\n---\n\nbody\n", encoding="utf-8"
    )

    db = build_auto_memory_index(memory_root=mem_root)
    with sqlite3.connect(db) as conn:
        text = conn.execute("SELECT text FROM memories").fetchone()[0]
    assert text.startswith("feedback_nameless")


# ---------------------------------------------------------------------------
# Concurrency — WAL + busy_timeout prevents lost-write / database-locked race
# ---------------------------------------------------------------------------


class TestMemoriesConcurrency:
    """Fire N threads x M writes at ONE memories.db through the wedge store
    connection factory (`_connect`) and assert zero 'database is locked' errors
    and the full additive row count.

    Modeled on tests/test_hook.py::TestConcurrency (rabbithole store). Without
    the primary-store hardening (WAL + busy_timeout=5000) concurrent writers
    raise sqlite3.OperationalError('database is locked') on the very first lock
    contention -> lost rows. With the hardening, writers wait -> no losses.
    """

    def test_concurrent_writes_lose_zero_rows(self, fake_brain: Path) -> None:
        import threading

        from nucleus_wedge.memories import _connect, ensure_schema

        db = ensure_schema()  # public API: creates memories.db + table
        n_threads = 20
        n_per_thread = 5  # total = 100 rows
        errors: list[str] = []
        err_lock = threading.Lock()

        def worker(tid: int) -> None:
            try:
                conn = _connect(db)  # each thread owns its connection
                for i in range(n_per_thread):
                    conn.execute(
                        "INSERT INTO memories "
                        "(text, tags, created_at, optional_date, source, kind, legacy_context) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (f"row-{tid}-{i}", "", "2026-07-02T00:00:00+00:00", "",
                         "concurrency-test", "note", ""),
                    )
                    conn.commit()
                conn.close()
            except sqlite3.OperationalError as exc:  # database is locked
                with err_lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"database-locked errors under contention: {errors}"

        with _connect(db) as conn:
            actual = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE source = 'concurrency-test'"
            ).fetchone()[0]
        expected = n_threads * n_per_thread
        assert actual == expected, (
            f"LOST WRITES: expected {expected}, got {actual} "
            f"(lost {expected - actual} — busy_timeout not working)"
        )
