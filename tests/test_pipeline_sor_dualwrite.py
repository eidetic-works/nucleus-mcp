"""ADUN (write_engram) SoR dual-write shim — Move 2 batch 3.

Proves the flag-gated, fault-isolated, single-seam dual-write added to
``runtime/memory_pipeline.py::MemoryPipeline._append_to_history`` (the ADUN
persistence tail every ``write_engram`` funnels through). This mirrors the
batch-2 wedge shim (``tests/test_wedge_sor_dualwrite.py``) but on the *separate*
A4 lineage — a ``write_engram`` flows through ``MemoryPipeline`` and never calls
``nucleus_wedge.store.Store.append``, so the two shims are independent seams.

  (a) flag-OFF is a byte-for-byte no-op — ledger.jsonl + history.jsonl are
      written exactly as before and NO SoR db is created, no facade constructed;
  (b) flag-ON dual-writes — the EXISTING ledger + history writes still land AND
      the same record is mirrored into the SoR (facade.recall finds it), sharing
      a stable key + timestamp so a later backfill can dedup;
  (c) fault isolation — if the facade capture raises, the primary write still
      succeeds, ledger/history are intact, and exactly one warning is logged;
  (d) NO double-mirror — a single logical write yields exactly ONE SoR row (the
      seam lives only in ``_append_to_history``, not also in ``_append_to_ledger``);
  (e) DELETE maps to a non-destructive ``curate(archive)`` overlay;
  (f) maintenance/audit markers (DEDUP_MIGRATION, …) are history-only — never SoR;
  (g) the real ``write_engram`` MCP impl mirrors through the same seam.

Reads are NOT changed in this batch — only the ADUN write tail grows a mirror.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from mcp_server_nucleus.memory import MEMORY_SOR_FLAG, MemoryFacade, SorStore
from mcp_server_nucleus.runtime import memory_pipeline as pipeline_mod
from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline


@pytest.fixture(autouse=True)
def _reset_flag_and_latch(monkeypatch: pytest.MonkeyPatch):
    """Each test starts flag-OFF with a fresh log-once latch."""
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)
    monkeypatch.setattr(pipeline_mod, "_sor_mirror_warned", False)


@pytest.fixture
def brain(tmp_path: Path) -> Path:
    b = tmp_path / ".brain"
    (b / "engrams").mkdir(parents=True)
    return b


def _ledger_rows(brain: Path) -> list[dict]:
    p = brain / "engrams" / "ledger.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _history_rows(brain: Path) -> list[dict]:
    p = brain / "engrams" / "history.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ── (a) flag-OFF no-op ──────────────────────────────────────────────────────
def test_flag_off_is_byte_for_byte_noop(brain: Path) -> None:
    pipeline = MemoryPipeline(brain_path=brain)
    result = pipeline.process(
        text="PostgreSQL chosen for ACID compliance guarantees",
        context="Architecture",
        intensity=8,
        key="arch_postgres_acid",
        operation="add",
    )
    assert result.get("added") == 1

    # Existing behavior intact: the record is in BOTH ledger + history.
    ledger = _ledger_rows(brain)
    history = _history_rows(brain)
    assert len(ledger) == 1
    assert ledger[0]["value"] == "PostgreSQL chosen for ACID compliance guarantees"
    assert len(history) == 1

    # Decisive no-op evidence: no SoR db, facade never constructed.
    assert not (brain / "engrams.db").exists(), "flag-OFF must not create the SoR db"
    assert pipeline._sor_facade is None


# ── (b) flag-ON dual-write round-trip ───────────────────────────────────────
def test_flag_on_dualwrites_to_ledger_history_and_sor(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="Redis selected for session cache with sub-millisecond reads",
        context="Architecture",
        intensity=7,
        source_agent="brain_write_engram",
        key="arch_redis_cache",
        operation="add",
    )

    # (1) The EXISTING stores still get the record.
    ledger = _ledger_rows(brain)
    history = _history_rows(brain)
    assert len(ledger) == 1 and len(history) == 1
    assert ledger[0]["value"].startswith("Redis selected for session cache")

    # (2) The SoR ALSO has it — round-trip via facade.recall.
    assert (brain / "engrams.db").exists(), "flag-ON must create the SoR db"
    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("Redis session cache")
    assert len(hits) == 1
    hit = hits[0]
    assert "Redis selected for session cache" in hit["text"]
    assert hit["kind"] == "Architecture"          # ADUN context -> SoR kind
    assert hit["surface"] == "brain_write_engram"  # source_agent -> SoR surface
    # Stable key: the SoR record reuses the ledger key (backfill dedup enabler).
    assert hit["key"] == "arch_redis_cache"
    assert hit["key"] == ledger[0]["key"]
    # Shared timestamp between the ledger engram and the SoR row.
    assert hit["ts"] == ledger[0]["timestamp"]


# ── (c) fault isolation ─────────────────────────────────────────────────────
def test_mirror_failure_does_not_break_primary_write(
    brain: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    def _boom(self, *a, **k):
        raise RuntimeError("SoR exploded")

    monkeypatch.setattr(
        "mcp_server_nucleus.memory.facade.MemoryFacade.capture", _boom
    )

    pipeline = MemoryPipeline(brain_path=brain)
    with caplog.at_level(logging.WARNING, logger="nucleus.memory_pipeline"):
        r1 = pipeline.process(
            text="Primary write must survive a mirror explosion",
            context="Decision", key="k_survive_1", operation="add",
        )
        r2 = pipeline.process(
            text="Second write must also survive the mirror failure",
            context="Decision", key="k_survive_2", operation="add",
        )

    # Primary writes are completely unaffected by the mirror blowing up.
    assert r1.get("added") == 1 and r2.get("added") == 1
    ledger = _ledger_rows(brain)
    history = _history_rows(brain)
    assert len(ledger) == 2 and len(history) == 2

    # Log-once: exactly one warning across the two failing mirrors.
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "SoR mirror failed" in r.getMessage()
    ]
    assert len(warnings) == 1, f"expected exactly one log-once warning, got {len(warnings)}"


# ── (d) NO double-mirror ────────────────────────────────────────────────────
def test_single_write_yields_exactly_one_sor_row(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One logical write_engram -> exactly ONE SoR row.

    An ADD commits via ``_append_to_ledger`` AND ``_append_to_history``. The
    mirror lives ONLY in ``_append_to_history``; if it also lived in
    ``_append_to_ledger`` this count would be 2. This is the no-double-mirror
    proof for the single-seam design.
    """
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="Exactly one engram should land in the source of record",
        context="Decision", intensity=5, key="k_single", operation="add",
    )

    sor = SorStore(brain / "engrams.db")
    assert sor.count() == 1, "single logical write must yield exactly one SoR row"
    # And the ledger likewise holds exactly one (the two writes are the same engram).
    assert len(_ledger_rows(brain)) == 1


def test_cross_lineage_no_double_mirror_with_wedge(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ADUN seam does not fire the wedge (batch-2) seam and vice-versa.

    A ``MemoryPipeline`` write must never route through
    ``nucleus_wedge.store.Store.append``; if it did, one write_engram would
    mirror twice. Guard the call graph directly.
    """
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    import nucleus_wedge.store as wedge_store

    calls = {"n": 0}
    real_append = wedge_store.Store.append

    def _counting_append(self, *a, **k):
        calls["n"] += 1
        return real_append(self, *a, **k)

    monkeypatch.setattr(wedge_store.Store, "append", _counting_append)

    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="ADUN write must not pass through the wedge Store.append seam",
        context="Decision", key="k_no_wedge", operation="add",
    )

    assert calls["n"] == 0, "ADUN write_engram must not invoke wedge Store.append"
    assert SorStore(brain / "engrams.db").count() == 1


# ── (e) DELETE -> curate(archive) ───────────────────────────────────────────
def test_delete_maps_to_curate_archive(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="Ephemeral fact that will later be deleted from the store",
        context="Decision", key="k_deletable", operation="add",
    )
    reader = MemoryFacade(brain_path=brain, enabled=True)
    assert len(reader.recall("Ephemeral fact")) == 1  # present after ADD

    # DELETE (soft) -> the SoR row is archived (non-destructive overlay).
    pipeline.process(text="delete marker", key="k_deletable", operation="delete")

    # Default recall now hides it; the underlying row is NOT removed.
    assert reader.recall("Ephemeral fact") == []
    archived = reader.recall("Ephemeral fact", include_archived=True)
    assert len(archived) == 1
    assert archived[0]["curation"] == "archive"
    # Non-destructive: the engrams row still exists in the SoR.
    assert SorStore(brain / "engrams.db").count() == 1


# ── (f) maintenance markers are history-only ────────────────────────────────
def test_maintenance_marker_not_mirrored(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    pipeline = MemoryPipeline(brain_path=brain)
    # A non-ADUN op_type (e.g. DEDUP_MIGRATION) must be history-only.
    pipeline._append_to_history(
        {"key": "__ledger_dedup_migration__", "duplicates_removed": 3},
        "DEDUP_MIGRATION",
    )
    # History got the audit marker...
    assert any(
        r.get("op_type") == "DEDUP_MIGRATION" for r in _history_rows(brain)
    )
    # ...but the SoR did not (no db forced into existence with a spurious row).
    db = brain / "engrams.db"
    if db.exists():
        assert SorStore(db).count() == 0


# ── (g) the real write_engram MCP impl path dual-writes ─────────────────────
def test_write_engram_impl_dualwrites(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl

    out = _brain_write_engram_impl(
        key="feat_facade_dualwrite",
        value="write_engram now mirrors into the unified SoR facade",
        context="Feature",
        intensity=6,
    )
    payload = json.loads(out)
    assert payload.get("success") is True

    # Ledger (existing store) has it.
    assert any(r["key"] == "feat_facade_dualwrite" for r in _ledger_rows(brain))

    # SoR mirror has it too.
    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("mirrors into the unified SoR")
    assert any("unified SoR facade" in h["text"] for h in hits)
    assert any(h["key"] == "feat_facade_dualwrite" for h in hits)


# ── (h) batch 7: ADUN capture feeds the derived vector index ────────────────
def _vector_index_rows(brain: Path, needle: str) -> list[str]:
    """Read the LocalSQLiteStore vector index (``memory.db``) directly and return
    the ``content`` of rows matching ``needle`` — proving the sink populated the
    derived index independently of any VectorStore read path."""
    import sqlite3

    db = brain / "memory.db"
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT content FROM memories WHERE content LIKE ?", (f"%{needle}%",)
        ).fetchall()
    return [r[0] for r in rows]


def test_flag_on_capture_feeds_vector_index(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flag-ON ADUN write lands in the SoR AND the derived vector index (so
    hybrid recall re-rank is no longer cold). The VectorStore's local sink
    resolves via ``get_brain_path()``, so co-locate it by pointing the env at
    the test brain, then query ``memory.db`` directly."""
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_STORAGE_TYPE", "local")

    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="Vector sink wiring keeps the derived index warm on write",
        context="Architecture", intensity=7,
        source_agent="brain_write_engram", key="arch_vector_sink", operation="add",
    )

    # (1) SoR has the row (authoritative capture).
    reader = MemoryFacade(brain_path=brain, enabled=True)
    assert any(h["key"] == "arch_vector_sink" for h in reader.recall("derived index warm"))

    # (2) The derived vector index ALSO has it — queried straight from memory.db.
    indexed = _vector_index_rows(brain, "derived index warm on write")
    assert indexed, "batch 7: the ADUN capture must feed the derived vector index"
    assert any("derived index warm on write" in c for c in indexed)

    # The sink is lazily constructed and cached on the pipeline.
    assert pipeline._sor_vector_sink is not None


# ── (i) batch 7: a raising sink at THIS call site never breaks the write ─────
def test_raising_vector_sink_does_not_break_primary_or_sor(
    brain: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Force ``VectorStore.index`` to raise. Because ``facade.capture`` wraps the
    sink best-effort, the exception is swallowed BEFORE it can reach the ADUN
    mirror's fault handler: the primary write + ledger + SoR row are all intact
    and the mirror logs NO failure (the sink error never surfaces to it)."""
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("NUCLEUS_STORAGE_TYPE", "local")

    import mcp_server_nucleus.runtime.vector_store as vs_mod

    def _boom_index(self, *a, **k):
        raise RuntimeError("embed backend down")

    monkeypatch.setattr(vs_mod.VectorStore, "index", _boom_index)

    pipeline = MemoryPipeline(brain_path=brain)
    with caplog.at_level(logging.WARNING, logger="nucleus.memory_pipeline"):
        result = pipeline.process(
            text="Primary write survives a raising vector sink",
            context="Decision", key="k_sink_boom", operation="add",
        )

    # Primary write completely unaffected.
    assert result.get("added") == 1
    assert len(_ledger_rows(brain)) == 1 and len(_history_rows(brain)) == 1

    # The SoR row still landed (insert precedes the best-effort index() call).
    reader = MemoryFacade(brain_path=brain, enabled=True)
    assert any(h["key"] == "k_sink_boom" for h in reader.recall("survives a raising"))

    # The index failure is isolated inside the facade → the ADUN mirror never
    # sees it, so it logs no "SoR mirror failed" warning.
    mirror_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "SoR mirror failed" in r.getMessage()
    ]
    assert mirror_warnings == []


# ── (j) batch 7: flag-OFF never constructs the sink ─────────────────────────
def test_flag_off_never_constructs_vector_sink(brain: Path) -> None:
    """Flag-OFF (default): the vector sink is never built — no import of
    ``vector_store`` on the write path, ``_sor_vector_sink`` stays None."""
    pipeline = MemoryPipeline(brain_path=brain)
    pipeline.process(
        text="Flag-off write must not touch the derived vector index at all",
        context="Decision", key="k_flag_off_sink", operation="add",
    )
    assert pipeline._sor_vector_sink is None
    assert not (brain / "memory.db").exists()
