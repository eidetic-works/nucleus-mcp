"""SoR store tests — Move 2 batch 1 (MemoryFacade scaffold).

Exercises the WAL SQLite source-of-record directly: schema build, capture/recall
round-trip, the FTS5 literal-token try-then-quote retry, non-destructive curation
overlays, and structured filters. Isolated (tmp db) — never touches a live brain.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mcp_server_nucleus.memory.sor import CURATION_ACTIONS, SorStore


@pytest.fixture
def store(tmp_path: Path) -> SorStore:
    return SorStore(tmp_path / ".brain" / "engrams.db")


def test_schema_builds_wal_fts_and_overlay(tmp_path: Path) -> None:
    db = tmp_path / "sor" / "engrams.db"
    SorStore(db)
    assert db.exists(), "SoR db file must be created on construction"
    conn = sqlite3.connect(str(db))
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal", f"expected WAL journal, got {mode!r}"
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
        }
        assert "engrams" in tables
        assert "engrams_fts" in tables
        assert "curation_overlay" in tables
    finally:
        conn.close()


def test_insert_returns_id_key_ts_and_persists(store: SorStore) -> None:
    res = store.insert("claude_code", "the quick brown fox jumps")
    assert isinstance(res["id"], int) and res["id"] > 0
    assert res["key"] and isinstance(res["key"], str)
    assert res["ts"]  # ISO timestamp assigned
    assert store.count() == 1


def test_capture_recall_roundtrip(store: SorStore) -> None:
    store.insert("claude_code", "postgres tuning trick with shared buffers", kind="note")
    hits = store.search("postgres tuning")
    assert len(hits) == 1
    hit = hits[0]
    assert "postgres tuning" in hit["text"]
    assert hit["surface"] == "claude_code"
    assert hit["kind"] == "note"
    assert hit["score"] is not None
    assert hit["curation"] is None


def test_fts5_literal_token_retry(store: SorStore) -> None:
    """A query like ``tb.py`` raises ``fts5: syntax error`` unquoted; the store
    must retry with phrase-quoting and still return the row (no exception)."""
    store.insert("claude_code", "deploy feat/foo-bar via tb.py runner script")
    # Sanity: bare MATCH of this token raises unquoted (documents the hazard).
    with pytest.raises(sqlite3.OperationalError):
        conn = store._connect()
        try:
            conn.execute("SELECT 1 FROM engrams_fts WHERE engrams_fts MATCH ?", ("tb.py",)).fetchall()
        finally:
            conn.close()
    # The store's search path applies the retry and returns the row.
    hits = store.search("tb.py")
    assert len(hits) == 1
    assert "tb.py" in hits[0]["text"]


def test_curate_archive_hides_row_non_destructively(store: SorStore) -> None:
    res = store.insert("claude_code", "ephemeral scratch note to archive")
    rid = res["id"]
    assert len(store.search("ephemeral scratch")) == 1

    out = store.curate(rid, "archive")
    assert out == {"ok": True, "id": rid, "key": res["key"], "action": "archive"}

    # Hidden from default recall, visible with include_archived.
    assert store.search("ephemeral scratch") == []
    shown = store.search("ephemeral scratch", include_archived=True)
    assert len(shown) == 1
    assert shown[0]["curation"] == "archive"

    # Original engrams row is untouched (non-destructive): content + row still there.
    conn = store._connect()
    try:
        row = conn.execute("SELECT text FROM engrams WHERE id=?", (rid,)).fetchone()
        assert row is not None and row["text"] == "ephemeral scratch note to archive"
        overlay_count = conn.execute(
            "SELECT COUNT(*) FROM curation_overlay WHERE target_id=?", (rid,)
        ).fetchone()[0]
        assert overlay_count == 1
    finally:
        conn.close()


def test_curate_canonical_boosts_ranking(store: SorStore) -> None:
    a = store.insert("claude_code", "auth middleware decision alpha")
    b = store.insert("claude_code", "auth middleware decision beta")
    # Before curation, newest (b) ranks first on the id-desc tiebreak.
    store.curate(a["id"], "canonical")
    hits = store.search("auth middleware")
    assert [h["id"] for h in hits][0] == a["id"], "canonical row must rank first"
    assert hits[0]["curation"] == "canonical"


def test_curate_by_key_and_delete_action(store: SorStore) -> None:
    res = store.insert("claude_code", "note addressed by key", key="my-stable-key")
    out = store.curate("my-stable-key", "delete")
    assert out["ok"] is True and out["action"] == "delete"
    # Soft delete: hidden from default recall, row still present.
    assert store.search("addressed by key") == []
    assert store.count() == 1


def test_curate_invalid_action_raises(store: SorStore) -> None:
    res = store.insert("claude_code", "x")
    with pytest.raises(ValueError):
        store.curate(res["id"], "bogus")


def test_curate_missing_target_returns_not_ok(store: SorStore) -> None:
    out = store.curate(99999, "archive")
    assert out["ok"] is False and "not found" in out["reason"]


def test_structured_filters(store: SorStore) -> None:
    store.insert("claude_code", "alpha content", kind="decision", tags="role:main,domain:x")
    store.insert("cursor", "beta content", kind="note", tags="role:peer")
    # kind filter
    assert {h["id"] for h in store.search(kind="decision")} == {1}
    # surface filter
    assert {h["surface"] for h in store.search(surface="cursor")} == {"cursor"}
    # tags substring filter
    assert len(store.search(tags="domain:x")) == 1
    # empty-query structured scan returns both, newest first
    allrows = store.search()
    assert [h["id"] for h in allrows] == [2, 1]


def test_since_relative_and_iso_filter(store: SorStore) -> None:
    store.insert("claude_code", "old row", ts="2000-01-01T00:00:00+00:00")
    store.insert("claude_code", "new row")  # ts = now
    # ISO lower bound excludes the year-2000 row.
    recent = store.search(since="2020-01-01T00:00:00+00:00")
    assert [h["text"] for h in recent] == ["new row"]
    # Relative window (last day) also excludes the old row.
    recent2 = store.search(since="1d")
    assert [h["text"] for h in recent2] == ["new row"]


def test_curation_actions_constant() -> None:
    assert set(CURATION_ACTIONS) == {"canonical", "demote", "archive", "delete"}
