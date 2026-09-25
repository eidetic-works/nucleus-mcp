"""nucleus_wedge SoR dual-write shim — Move 2 batch 2.

Proves the flag-gated, fault-isolated dual-write added to
``nucleus_wedge/store.py::Store.append`` (and therefore to
``server.py::remember``, which delegates to it):

  (a) flag-OFF is a byte-for-byte no-op — history.jsonl is written exactly as
      before and NO SoR db is created, no facade constructed;
  (b) flag-ON dual-writes — the EXISTING history.jsonl append still lands AND the
      same record is mirrored into the SoR (facade.recall finds it), sharing a
      stable key so a later backfill can dedup;
  (c) fault isolation — if the facade capture raises, the primary append still
      succeeds, history is intact, and exactly one warning is logged (log-once);
  (d) the real ``remember`` MCP tool mirrors through the same seam.

Reads are NOT changed in this batch — only the write path grows a mirror.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from mcp_server_nucleus.memory import MEMORY_SOR_FLAG, MemoryFacade
from nucleus_wedge import store as store_mod
from nucleus_wedge.store import Store


@pytest.fixture(autouse=True)
def _reset_flag_and_latch(monkeypatch: pytest.MonkeyPatch):
    """Each test starts flag-OFF with a fresh log-once latch."""
    monkeypatch.delenv(MEMORY_SOR_FLAG, raising=False)
    monkeypatch.setattr(store_mod, "_sor_mirror_warned", False)


@pytest.fixture
def brain(tmp_path: Path) -> Path:
    b = tmp_path / ".brain"
    (b / "engrams").mkdir(parents=True)
    return b


def _history_records(brain: Path) -> list[dict]:
    text = (brain / "engrams" / "history.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


# ── (a) flag-OFF no-op ──────────────────────────────────────────────────────
def test_flag_off_is_byte_for_byte_noop(brain: Path) -> None:
    store = Store(brain_path=brain)
    ret = store.append("off-path payload", kind="note")

    # Existing behavior intact: the record is in history.jsonl.
    recs = _history_records(brain)
    assert len(recs) == 1
    assert recs[0]["snapshot"]["value"] == "off-path payload"
    assert ret["key"] == recs[0]["key"]

    # Decisive no-op evidence: no SoR db, facade never constructed.
    assert not (brain / "engrams.db").exists(), "flag-OFF must not create the SoR db"
    assert store._sor_facade is None


# ── (b) flag-ON dual-write round-trip ───────────────────────────────────────
def test_flag_on_dualwrites_to_history_and_sor(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    store = Store(brain_path=brain)
    ret = store.append(
        "suspense boundary react note", kind="decision", tags=["role:main"]
    )

    # (1) The EXISTING store still gets the record, unchanged in shape.
    recs = _history_records(brain)
    assert len(recs) == 1
    assert recs[0]["snapshot"]["value"] == "suspense boundary react note"
    assert recs[0]["key"] == ret["key"]

    # (2) The SoR ALSO has it — round-trip via facade.recall.
    assert (brain / "engrams.db").exists(), "flag-ON must create the SoR db"
    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("suspense boundary")
    assert len(hits) == 1
    hit = hits[0]
    assert "suspense boundary" in hit["text"]
    assert hit["kind"] == "decision"
    assert hit["surface"] == "nucleus-wedge"  # default source_agent
    # Stable key: the SoR record reuses the history key (backfill dedup enabler).
    assert hit["key"] == ret["key"]
    # Shared timestamp between the two stores.
    assert hit["ts"] == ret["timestamp"]


def test_flag_on_via_explicit_key_propagates_stable_key(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")
    store = Store(brain_path=brain)
    store.append("keyed payload alpha", key="fixed-key-123")

    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("keyed")
    assert len(hits) == 1
    assert hits[0]["key"] == "fixed-key-123"


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

    store = Store(brain_path=brain)
    with caplog.at_level(logging.WARNING, logger="nucleus_wedge.store"):
        ret1 = store.append("primary must survive", kind="note")
        ret2 = store.append("second write too", kind="note")

    # Primary write is completely unaffected by the mirror blowing up.
    assert ret1["key"] and ret2["key"]
    recs = _history_records(brain)
    assert len(recs) == 2
    assert recs[0]["snapshot"]["value"] == "primary must survive"
    assert recs[1]["snapshot"]["value"] == "second write too"

    # Log-once: exactly one warning across the two failing mirrors.
    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "SoR mirror failed" in r.getMessage()
    ]
    assert len(warnings) == 1, f"expected exactly one log-once warning, got {len(warnings)}"


# ── (d) the real remember() MCP tool path dual-writes ───────────────────────
async def test_remember_tool_dualwrites(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    from nucleus_wedge.server import build_server

    mcp = build_server()
    # Tool lookup across FastMCP versions. The pinned build exposes
    # list_tools() -> [Tool]; older/newer ones expose get_tools() -> {name: tool}.
    # This test asserted get_tools() unconditionally and died with
    # AttributeError on the installed version — it was green only while the
    # file was missing from the worktree.
    if hasattr(mcp, "get_tools"):
        tools = await mcp.get_tools()
        remember_fn = tools.get("remember")
    else:
        listed = await mcp.list_tools()
        remember_fn = next(
            (t for t in listed if getattr(t, "name", None) == "remember"), None
        )
        # list_tools() returns metadata; the callable lives on the tool manager.
        if remember_fn is not None and not hasattr(remember_fn, "fn"):
            mgr = getattr(mcp, "_tool_manager", None)
            got = mgr.get_tool("remember") if mgr and hasattr(mgr, "get_tool") else None
            remember_fn = got or remember_fn
    assert remember_fn is not None, "remember tool not registered"
    # The tool may be a FunctionTool wrapper or the raw function
    if hasattr(remember_fn, "fn"):
        remember_fn = remember_fn.fn
    # Call the function (may be sync or async)
    import inspect
    if inspect.iscoroutinefunction(remember_fn):
        await remember_fn(content="vector index rebuild note", kind="note")
    else:
        remember_fn(content="vector index rebuild note", kind="note")

    # History (existing store) has it.
    values = [r["snapshot"]["value"] for r in _history_records(brain)]
    assert "vector index rebuild note" in values

    # SoR mirror has it too.
    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("vector index rebuild")
    assert any("vector index rebuild note" in h["text"] for h in hits)


# ── (e) Move 2 batch B2 — the SoR mirror pushes into the vector sink ─────────
def test_flag_on_capture_reaches_vector_sink(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flag-ON: the wedge mirror wires facade.capture's ``vector_sink`` so the
    captured text reaches ``VectorStore.index`` (keeps the derived index warm)."""
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    calls: list[tuple] = []

    class _SpySink:
        def index(self, doc_id, text, metadata=None):
            calls.append((doc_id, text, metadata))
            return doc_id

    # The lazy `from ...vector_store import VectorStore` binds this symbol at
    # call time, so patching it here intercepts the wedge's sink construction.
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vector_store.VectorStore", _SpySink
    )

    store = Store(brain_path=brain)
    ret = store.append("vector sink wedge payload", kind="note")

    # The primary + SoR writes still land.
    assert (brain / "engrams.db").exists()
    # The sink saw exactly the captured record: SoR row id + payload + meta.
    assert len(calls) == 1
    doc_id, text, metadata = calls[0]
    assert text == "vector sink wedge payload"
    assert doc_id, "sink must receive the SoR row id (facade result['id'])"
    assert metadata == {"op_type": "ADD"}
    # Sink cached on the Store for reuse across appends.
    assert store._sor_vector_sink is not None


def test_flag_off_never_reaches_vector_sink(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flag-OFF byte-identical: the sink is never constructed nor indexed."""
    calls: list[tuple] = []

    class _SpySink:
        def index(self, *a, **k):
            calls.append((a, k))
            return "x"

    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vector_store.VectorStore", _SpySink
    )

    store = Store(brain_path=brain)
    store.append("off path no sink", kind="note")

    assert calls == [], "flag-OFF must not touch the vector sink"
    assert store._sor_vector_sink is None, "flag-OFF must not construct the sink"
    assert not (brain / "engrams.db").exists()


def test_vector_sink_build_failure_still_mirrors_sor(
    brain: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Construction-isolated: a sink build/import failure degrades to a sink-less
    mirror — the SoR row still lands and the append does not raise."""
    monkeypatch.setenv(MEMORY_SOR_FLAG, "1")

    def _boom(*a, **k):
        raise RuntimeError("vector deps unavailable in this deployment")

    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.vector_store.VectorStore", _boom
    )

    store = Store(brain_path=brain)
    ret = store.append("sink build boom payload", kind="note")

    # SoR still received the record (sink-less capture), append returned normally.
    assert ret["key"]
    reader = MemoryFacade(brain_path=brain, enabled=True)
    hits = reader.recall("sink build boom")
    assert any("sink build boom payload" in h["text"] for h in hits)
    # Build failed → sink stays None (no half-built cache).
    assert store._sor_vector_sink is None
