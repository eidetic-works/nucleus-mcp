"""Compare-and-swap write gate on ``nucleus_wedge/store.py::Store.append``.

The pattern is the one Anthropic's Applied AI team described at AIDevCon London
2026: an agent hashes a memory before it edits, drafts the edit, and hashes again
before it commits — "if those two things do not match then the agent cannot write
it, because it means that some update was made in the meantime."

Before this gate the store was append-only with no conflict detection at all, so
two agents that both read a memory and both wrote it produced a silent
lost-update: the second append simply became the new head and the first agent's
reasoning vanished with no error anywhere.

These tests are an OPPOSED PAIR. The negative control matters more than the
positive one: a gate whose success looks like nothing happening is the thing most
likely to be broken, so ``test_stale_hash_is_refused`` asserts both that the
write raises AND that history.jsonl is byte-identical afterwards. If the gate
were deleted, that test fails; if the gate were made unconditionally strict,
``test_absent_expected_hash_never_refuses`` fails.
"""
from __future__ import annotations

import pytest

from nucleus_wedge.store import ABSENT, MemoryConflict, Store


@pytest.fixture()
def store(tmp_path):
    return Store(brain_path=tmp_path / ".brain")


def _lines(s: Store) -> list[str]:
    return s.history_file.read_text(encoding="utf-8").splitlines()


# ── head_hash: the read half of the round trip ──────────────────────────────


def test_head_hash_is_absent_for_unknown_key(store):
    assert store.head_hash("never-written") == ABSENT


def test_head_hash_is_stable_across_repeated_reads(store):
    store.append("v1", key="k")
    assert store.head_hash("k") == store.head_hash("k")


def test_head_hash_changes_after_a_write(store):
    store.append("v1", key="k")
    before = store.head_hash("k")
    store.append("v2", key="k", op_type="UPDATE")
    assert store.head_hash("k") != before


def test_head_hash_is_per_key(store):
    store.append("v1", key="a")
    store.append("v1", key="b")
    assert store.head_hash("a") != store.head_hash("b")


# ── NEGATIVE CONTROL: the write that must be refused ────────────────────────


def test_stale_hash_is_refused_and_history_is_untouched(store):
    """The lost-update this gate exists to stop.

    Agent A reads, agent B writes, agent A writes back over B. A must be told.
    """
    store.append("original", key="shared")
    stale = store.head_hash("shared")          # agent A reads
    store.append("B wrote this", key="shared", op_type="UPDATE")  # agent B lands
    before = _lines(store)

    with pytest.raises(MemoryConflict):
        store.append("A clobbers B", key="shared", op_type="UPDATE", expected_hash=stale)

    assert _lines(store) == before, "refused write must not append anything"


def test_conflict_names_both_hashes(store):
    """A refusal a human cannot diagnose is a refusal that gets disabled."""
    store.append("original", key="shared")
    stale = store.head_hash("shared")
    store.append("moved on", key="shared", op_type="UPDATE")

    with pytest.raises(MemoryConflict) as exc:
        store.append("clobber", key="shared", op_type="UPDATE", expected_hash=stale)

    assert exc.value.key == "shared"
    assert exc.value.expected == stale
    assert exc.value.actual == store.head_hash("shared")
    assert exc.value.expected != exc.value.actual


def test_expected_absent_is_refused_when_key_already_exists(store):
    """The create race: two agents both believe they are creating the key."""
    store.append("someone got there first", key="k")
    with pytest.raises(MemoryConflict):
        store.append("mine", key="k", expected_hash=ABSENT)


# ── POSITIVE CONTROL: the write that must go through ────────────────────────


def test_fresh_hash_is_accepted(store):
    store.append("original", key="k")
    fresh = store.head_hash("k")
    out = store.append("updated", key="k", op_type="UPDATE", expected_hash=fresh)
    assert out["key"] == "k"
    assert any("updated" in ln for ln in _lines(store))


def test_expected_absent_is_accepted_when_key_is_missing(store):
    out = store.append("first", key="brand-new", expected_hash=ABSENT)
    assert out["key"] == "brand-new"
    assert store.head_hash("brand-new") != ABSENT


def test_read_modify_write_loop_survives_many_sequential_rounds(store):
    store.append("r0", key="k")
    for i in range(1, 6):
        h = store.head_hash("k")
        store.append(f"r{i}", key="k", op_type="UPDATE", expected_hash=h)
    assert any("r5" in ln for ln in _lines(store))


# ── BACKWARD COMPAT: opt-in means the old path cannot have changed ──────────


def test_absent_expected_hash_never_refuses(store):
    """Every pre-existing caller passes no hash and must be unaffected —
    including in exactly the racing scenario the gate refuses above."""
    store.append("original", key="shared")
    store.append("B wrote this", key="shared", op_type="UPDATE")
    out = store.append("legacy caller clobbers freely", key="shared", op_type="UPDATE")
    assert out["key"] == "shared"


def test_keyless_append_is_unaffected(store):
    out = store.append("no key supplied")
    assert out["key"].startswith("remember_")


def test_expected_hash_without_a_key_is_rejected_loudly(store):
    """A CAS over an unnamed key refers to nothing — refuse rather than
    silently auto-generate a key and let the guard pass vacuously."""
    with pytest.raises(ValueError, match="explicit key"):
        store.append("v", expected_hash=ABSENT)


# ── CONSUMER: the gate must be reachable from the surface agents call ───────
# An opposed pair on Store.append proves nothing about the MCP tool. These
# exercise the real registered tools, because a gate no caller can invoke is a
# gate that does not exist.


async def _tool(mcp, name):
    """Resolve a registered tool to a plain callable across FastMCP versions."""
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
    if inspect.iscoroutinefunction(fn):
        raw = fn

        async def _call(**kw):
            return await raw(**kw)
    else:
        def _call(**kw):
            return fn(**kw)
    return _call, inspect.iscoroutinefunction(fn)


async def _run(call, is_async, **kw):
    return await call(**kw) if is_async else call(**kw)


@pytest.fixture()
def mcp_brain(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    from nucleus_wedge.server import build_server

    return build_server(), brain


async def test_memory_head_hash_tool_is_registered_and_reports_absent(mcp_brain):
    mcp, _ = mcp_brain
    call, is_async = await _tool(mcp, "memory_head_hash")
    out = await _run(call, is_async, key="nope")
    assert out == {"key": "nope", "head_hash": ABSENT}


async def test_remember_tool_returns_the_next_round_trip_token(mcp_brain):
    """A read-modify-write loop must not need a second call to make progress."""
    mcp, _ = mcp_brain
    remember, ra = await _tool(mcp, "remember")
    head, ha = await _tool(mcp, "memory_head_hash")

    out = await _run(remember, ra, content="v1", key="k")
    assert out["head_hash"] != ABSENT
    assert out["head_hash"] == (await _run(head, ha, key="k"))["head_hash"]


async def test_remember_tool_refuses_a_stale_write(mcp_brain):
    """NEGATIVE CONTROL at the surface: the conflict must reach the agent as
    structured data it can branch on, not as a stack trace."""
    mcp, brain = mcp_brain
    remember, ra = await _tool(mcp, "remember")
    head, ha = await _tool(mcp, "memory_head_hash")

    await _run(remember, ra, content="original", key="shared")
    stale = (await _run(head, ha, key="shared"))["head_hash"]
    await _run(remember, ra, content="B wrote this", key="shared")

    hist = (brain / "engrams" / "history.jsonl").read_text(encoding="utf-8")
    out = await _run(
        remember, ra, content="A clobbers B", key="shared", expected_hash=stale
    )

    assert out.get("conflict") is True
    assert out["expected"] == stale
    assert out["actual"] != stale
    assert "retry" in out["error"].lower()
    assert (brain / "engrams" / "history.jsonl").read_text(encoding="utf-8") == hist


async def test_remember_tool_accepts_a_fresh_write(mcp_brain):
    """POSITIVE CONTROL at the surface."""
    mcp, _ = mcp_brain
    remember, ra = await _tool(mcp, "remember")
    head, ha = await _tool(mcp, "memory_head_hash")

    await _run(remember, ra, content="original", key="k")
    fresh = (await _run(head, ha, key="k"))["head_hash"]
    out = await _run(remember, ra, content="updated", key="k", expected_hash=fresh)
    assert out.get("conflict") is not True
    assert out["key"] == "k"


async def test_remember_tool_unguarded_call_is_unchanged(mcp_brain):
    """Every existing caller passes neither key nor hash. It must still work."""
    mcp, _ = mcp_brain
    remember, ra = await _tool(mcp, "remember")
    out = await _run(remember, ra, content="legacy call", kind="note")
    assert out["key"].startswith("remember_")
    assert out.get("conflict") is not True
