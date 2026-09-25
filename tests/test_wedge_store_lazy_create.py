"""The engram store must not be created by reading it.

``Store.__init__`` unconditionally ran ``mkdir(parents=True)`` + ``touch()``, so
merely constructing a Store to *recall* materialised an empty
``.brain/engrams/history.jsonl`` wherever the process happened to be standing.
Measured on this machine: ``nucleus-renaissance/.brain/engrams/`` held only
``hook_metrics.jsonl`` and no history at all, yet a single read reported
``exists: True, rows: 0`` — because the read had just created the file it then
found empty.

That is the failure family this repo keeps paying for: a correct check over an
empty set. ``recall`` returning nothing from a brain that has no store is
indistinguishable from a brain whose store is genuinely empty, and the caller
gets a clean zero either way. ``.brain/engrams/`` is gitignored, so the created
file never showed up in ``git status`` to give the game away.

Two fixes, tested here:
  * creation moves to the write path, so a read creates nothing;
  * ``Store.exists`` and the ``memory_store_status`` tool make ABSENT and EMPTY
    two different answers instead of one zero.

``append`` still creates the store on first write — greenfield init must keep
working, so ``test_append_creates_the_store_lazily`` is the control that stops
this fix from being over-applied into "never create anything."
"""
from __future__ import annotations

import pytest

from nucleus_wedge.store import ABSENT, Store


@pytest.fixture()
def brain(tmp_path):
    """A brain path that does NOT exist yet — the fresh-clone shape."""
    return tmp_path / ".brain"


# ── NEGATIVE CONTROL: reads must not write ─────────────────────────────────


def test_constructing_a_store_creates_nothing(brain):
    Store(brain_path=brain)
    assert not (brain / "engrams").exists(), "constructor created the engrams dir"
    assert not (brain / "engrams" / "history.jsonl").exists()


def test_reading_rows_creates_nothing(brain):
    s = Store(brain_path=brain)
    assert list(s.rows()) == []
    assert not s.history_file.exists(), "reading rows created the store"


def test_keys_present_creates_nothing(brain):
    s = Store(brain_path=brain)
    assert s.keys_present() == set()
    assert not s.history_file.exists()


def test_head_hash_creates_nothing_and_reports_absent(brain):
    s = Store(brain_path=brain)
    assert s.head_hash("anything") == ABSENT
    assert not s.history_file.exists()


# ── The third state: ABSENT is not EMPTY ───────────────────────────────────


def test_store_reports_absent_when_never_written(brain):
    assert Store(brain_path=brain).exists is False


def test_store_reports_present_but_empty_after_truncation(brain):
    """A real store that happens to hold nothing. Same zero rows, different
    answer — which is the whole point."""
    s = Store(brain_path=brain)
    s.append("seed", key="k")
    s.history_file.write_text("", encoding="utf-8")
    assert s.exists is True
    assert list(s.rows()) == []


# ── POSITIVE CONTROL: the write path must still create ─────────────────────


def test_append_creates_the_store_lazily(brain):
    """Greenfield init must keep working — this stops the fix being
    over-applied into 'never create anything'."""
    s = Store(brain_path=brain)
    assert not s.history_file.exists()
    s.append("first memory", key="k")
    assert s.history_file.exists()
    assert s.exists is True
    assert [r["snapshot"]["value"] for r in s.rows()] == ["first memory"]


def test_append_creates_intermediate_directories(brain):
    s = Store(brain_path=brain / "deeper" / "nested")
    s.append("v", key="k")
    assert s.history_file.exists()


def test_cas_round_trip_works_on_a_freshly_created_store(brain):
    s = Store(brain_path=brain)
    s.append("v1", key="k", expected_hash=ABSENT)
    h = s.head_hash("k")
    s.append("v2", key="k", op_type="UPDATE", expected_hash=h)
    assert [r["snapshot"]["value"] for r in s.rows()] == ["v1", "v2"]


# ── CONSUMER: the surface must be able to say which zero it means ──────────


async def _tool(mcp, name):
    import inspect

    fn = None
    if hasattr(mcp, "get_tools"):
        fn = (await mcp.get_tools()).get(name)
    else:
        listed = await mcp.list_tools()
        fn = next((t for t in listed if getattr(t, "name", None) == name), None)
        if fn is not None and not hasattr(fn, "fn"):
            mgr = getattr(mcp, "_tool_manager", None)
            fn = (mgr.get_tool(name) if mgr and hasattr(mgr, "get_tool") else None) or fn
    assert fn is not None, f"{name} tool not registered"
    if hasattr(fn, "fn"):
        fn = fn.fn
    is_async = inspect.iscoroutinefunction(fn)
    return fn, is_async


async def _run(fn, is_async, **kw):
    return await fn(**kw) if is_async else fn(**kw)


@pytest.fixture()
def mcp_on_empty_brain(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    from nucleus_wedge.server import build_server

    return build_server(), brain


async def test_status_tool_says_absent_not_empty(mcp_on_empty_brain):
    """The failure this whole file exists for: a clean zero that means
    'wrong brain', reported as if it meant 'nothing learned yet'."""
    mcp, brain = mcp_on_empty_brain
    fn, is_async = await _tool(mcp, "memory_store_status")
    out = await _run(fn, is_async)
    assert out["state"] == "ABSENT"
    assert out["rows"] == 0
    assert str(brain) in out["path"]
    assert "absent" in out["detail"].lower() or "no engram" in out["detail"].lower()


async def test_status_tool_says_populated_after_a_write(mcp_on_empty_brain):
    mcp, _ = mcp_on_empty_brain
    status, sa = await _tool(mcp, "memory_store_status")
    remember, ra = await _tool(mcp, "remember")
    await _run(remember, ra, content="something worth keeping")
    out = await _run(status, sa)
    assert out["state"] == "POPULATED"
    assert out["rows"] >= 1
