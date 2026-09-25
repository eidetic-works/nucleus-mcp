"""The proposal gate, reachable — MCP surface tests for flywheel/proposals.py.

``mcp_server_nucleus.flywheel.proposals`` implements the last third of
dreaming: a batch pass proposes a memory change, attaches its evidence, and a
decision accepts or rejects it. The module is complete and tested
(test_flywheel_proposals.py) — but nothing could reach it. Zero importers in
``src/``, no export from ``flywheel/__init__.py``, no CLI verb, no MCP tool. A
gate no caller can invoke is a gate that does not exist, so these tests
exercise the three wedge-server tools that give it a door:

  * ``memory_proposals_list``    — what is waiting for a decision
  * ``memory_proposal_accept``   — the ONLY path to memory
  * ``memory_proposal_reject``   — recorded, never deleted

THE control mirrors the module's central refusal at the surface: accepting a
proposal whose evidence is INSUFFICIENT must come back as structured data
(``refused: True``) the calling agent can branch on — not a stack trace — and
must write nothing.
"""
from __future__ import annotations

import pytest

from nucleus_wedge.store import Store


# ── tool resolution (copied from test_wedge_memory_cas.py — works across
#    FastMCP versions) ──────────────────────────────────────────────────────


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


def _propose(brain, text="stop using em dashes", complete=True):
    """Record a proposal directly against the test brain (the batch-pass side
    of the gate — the tools under test are the decision side)."""
    from mcp_server_nucleus.flywheel import proposals as PR

    evidence = {
        "complete": complete,
        "summary": "em dash everywhere in 2 of 3 sessions",
        "sessions_matched": 2,
        "sessions_scanned": 3,
        "examples": ["aaaaaaaa-0000-0000-0000-000000000001"],
    }
    if not complete:
        evidence["insufficient_reason"] = "scan capped at 1 session"
    return PR.propose(brain, text, evidence, pattern="em dash everywhere")


def _memory_values(brain):
    return [r["snapshot"]["value"] for r in Store(brain_path=brain).rows()]


# ── registration: the whole point — the gate was unreachable ───────────────


async def test_all_three_proposal_tools_are_registered(mcp_brain):
    mcp, _ = mcp_brain
    for name in (
        "memory_proposals_list",
        "memory_proposal_accept",
        "memory_proposal_reject",
    ):
        await _tool(mcp, name)  # asserts fn is not None


# ── listing ────────────────────────────────────────────────────────────────


async def test_list_returns_a_pending_proposal(mcp_brain):
    mcp, brain = mcp_brain
    p = _propose(brain)
    list_tool, la = await _tool(mcp, "memory_proposals_list")

    out = await _run(list_tool, la)

    assert out["count"] >= 1
    row = next(r for r in out["pending"] if r["proposal_id"] == p["proposal_id"])
    assert row["proposed_memory"] == "stop using em dashes"
    assert "2 of 3" in row["evidence_summary"]


# ── accepting: the only path to memory ─────────────────────────────────────


async def test_accept_with_complete_evidence_writes_to_memory(mcp_brain):
    mcp, brain = mcp_brain
    p = _propose(brain, complete=True)
    accept, aa = await _tool(mcp, "memory_proposal_accept")

    out = await _run(accept, aa, proposal_id=p["proposal_id"])

    assert out.get("refused") is not True
    assert any("em dash" in v for v in _memory_values(brain))


async def test_accept_with_insufficient_evidence_is_refused_not_raised(mcp_brain):
    """THE control at the surface. A capped scan must not become a permanent
    memory, and the refusal must reach the agent as data it can branch on."""
    mcp, brain = mcp_brain
    p = _propose(brain, complete=False)
    accept, aa = await _tool(mcp, "memory_proposal_accept")

    out = await _run(accept, aa, proposal_id=p["proposal_id"])

    assert out["refused"] is True
    assert out["reason"]
    assert not any("em dash" in v for v in _memory_values(brain)), (
        "a refused accept must write nothing"
    )


# ── rejecting: recorded, never deleted ──────────────────────────────────────


async def test_reject_with_empty_reason_returns_structured_refusal(mcp_brain):
    mcp, brain = mcp_brain
    p = _propose(brain)
    reject, ra = await _tool(mcp, "memory_proposal_reject")

    out = await _run(reject, ra, proposal_id=p["proposal_id"], reason="")

    assert out["refused"] is True
    assert out["reason"]


async def test_a_rejected_proposal_leaves_the_pending_list(mcp_brain):
    mcp, brain = mcp_brain
    p = _propose(brain)
    reject, ra = await _tool(mcp, "memory_proposal_reject")
    list_tool, la = await _tool(mcp, "memory_proposals_list")

    out = await _run(reject, ra, proposal_id=p["proposal_id"], reason="not a real pattern")
    assert out.get("refused") is not True

    pending = await _run(list_tool, la)
    assert p["proposal_id"] not in [r["proposal_id"] for r in pending["pending"]]

    from mcp_server_nucleus.flywheel import proposals as PR
    assert PR.all_proposals(brain)[0]["status"] == "rejected"
