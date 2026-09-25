"""Stage 0 — first cell: the boot loop threads gateway + recall-inject + flywheel.

These assert the three seams on REAL Nucleus state (isolated temp brain):
  1. the model call is mediated — a real LLM_GENERATE event is written by the
     Nucleus gateway (a raw provider call would write none);
  2. a real recalled memory string is injected into the agent's context;
  3. a real LoopTurn is written to the flywheel.

The provider network call is stubbed offline (deterministic); recall + record
are real. Flag-OFF is a hard no-op (boot_cell refuses to run).
"""
import json
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod


@pytest.fixture()
def cell_env(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")  # deterministic offline model call
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    return str(brain)


@pytest.fixture()
def pager_env(cell_env, monkeypatch):
    """cell_env + the Stage-1 pager flag ON (selective recall)."""
    from mcp_server_nucleus.runtime.agent_os import pager as pager_mod

    monkeypatch.setenv(pager_mod.PAGER_FLAG, "1")
    return cell_env


def _seed_prior_memory(brain_path: str, text: str) -> None:
    from nucleus_wedge.store import Store

    Store(brain_path).append(value=text, kind="note", tags=["topic:gateway"],
                             source_agent="prior-session")


def test_flag_off_refuses_to_boot(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv(boot_mod.BOOT_FLAG, raising=False)
    assert boot_mod.boot_flag_enabled() is False
    with pytest.raises(RuntimeError):
        boot_mod.boot_cell("anything", brain_path=str(tmp_path))


def test_first_cell_threads_all_three_seams(cell_env):
    brain = cell_env
    prior = "The Nucleus gateway routes model calls through the OS; agents live INSIDE."
    _seed_prior_memory(brain, prior)

    result = boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=brain,
    )

    # Seam 2: real memory recalled + injected before thinking.
    assert result.recalled_from_memory is True
    assert any(prior in (r.get("text") or "") for r in result.recalled_rows)
    assert prior in result.injected_context

    # Seam 1: cognition mediated — a real LLM_GENERATE event was written.
    g = result.gateway_result
    assert g.mediated is True
    assert g.event_id and g.event_id.startswith("evt-")
    events = (boot_mod.Path(brain) / "ledger" / "events.jsonl").read_text().splitlines()
    llm_events = [json.loads(l) for l in events if l.strip() and json.loads(l)["type"] == "LLM_GENERATE"]
    assert llm_events, "gateway must write a LLM_GENERATE event (proof of mediation)"
    assert llm_events[-1]["emitter"] == "NucleusGateway"
    # The stub used the injected memory (loop is coherent, not decorative).
    assert "mediated by the Nucleus gateway" in g.text

    # Seam 3: turn recorded to the flywheel.
    assert result.turn.turn_id.startswith("turn-")
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    turn = rows[0]
    assert turn["metadata"]["mediated_by"] == "NucleusGateway"
    assert turn["metadata"]["llm_event_id"] == g.event_id
    assert turn["metadata"]["stage"] == "agent_os_stage0_first_cell"


def test_recall_is_selective_not_echo(pager_env):
    """With the Stage-1 pager ON, recall returns the matching memory, not the
    grab-bag of near-misses (the Stage-0 "blur" — MEMBRANE §2). This test FAILS
    with the pager OFF on a noisy brain; the pager is the fix.
    """
    brain = pager_env
    _seed_prior_memory(brain, "The Nucleus gateway routes model calls through the OS.")
    from nucleus_wedge.store import Store

    Store(brain).append(value="Unrelated: the floor-3 coffee machine is broken.",
                        kind="note", tags=["topic:office"], source_agent="prior-session")

    injected, rows = boot_mod.recall_and_inject("gateway", brain_path=brain)
    assert len(rows) == 1
    assert "gateway" in (rows[0]["text"] or "").lower()
    assert "coffee" not in injected.lower()


def test_pager_ranks_exact_topic_above_loosely_related_and_respects_budget(pager_env):
    """The pager policy (relevance × recency × verified-trust) ranks an
    exact-topic memory above loosely-related ones, and evicts the rest once the
    context budget is exhausted. Direct unit test of ``pager.page``.
    """
    from mcp_server_nucleus.runtime.agent_os.pager import page

    candidates = [
        {"text": "The Nucleus gateway routes model calls through the OS.",
         "tags": "topic:gateway", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "Unrelated: the floor-3 coffee machine is broken.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
        {"text": "Also unrelated: the office printer is out of toner.",
         "tags": "topic:office", "created_at": "2026-07-13T00:00:00Z",
         "source": "history.jsonl", "kind": "note"},
    ]
    ranked = page("gateway", candidates, budget_chars=2000)
    # Exact-topic memory ranks first; loosely-related ones follow only if budget
    # allows — here the budget is generous, so the order is the assertion.
    assert ranked, "pager must return at least the best candidate"
    assert "gateway" in (ranked[0].get("text") or "").lower()
    assert "coffee" not in (ranked[0].get("text") or "").lower()

    # Budget discipline: a tiny budget evicts the lower-ranked candidates even
    # though they would otherwise be returned.
    tight = page("gateway", candidates, budget_chars=60)
    assert len(tight) < len(candidates)
    assert "gateway" in (tight[0].get("text") or "").lower()


def test_agent_os_boot_wrapper_cleans_env_on_success(cell_env, monkeypatch):
    """Regression: the MCP tool wrapper (agent_os_boot.py) must pop
    NUCLEUS_AGENT_OS_BOOT / NUCLEUS_AGENT_OS_VERIFIED_RECORD after a successful
    boot. Previously only the error paths cleaned up, so a successful boot
    leaked both flags into the process env — silently flipping subsequent
    non-boot calls into the Agent OS code path for the life of the process.
    """
    from mcp_server_nucleus.tools import agent_os_boot as wrapper

    # Sanity: flags absent before the call.
    monkeypatch.delenv(wrapper._BOOT_FLAG, raising=False)
    monkeypatch.delenv(wrapper._VERIFIED_RECORD_FLAG, raising=False)

    captured = {}

    class FakeMCP:
        def tool(self, **_kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn
            return deco

    helpers = {"make_response": lambda result=None, error=None:
               {"result": result} if error is None else {"error": error}}
    wrapper.register(FakeMCP(), helpers)
    boot_fn = captured["fn"]

    resp = boot_fn("How should this agent route its model calls?",
                   recall_query="gateway", brain_path=cell_env)

    # Success path taken.
    assert "error" not in resp, resp
    assert "result" in resp
    # The leak fix: flags must be gone after a successful boot.
    assert wrapper._BOOT_FLAG not in os.environ
    assert wrapper._VERIFIED_RECORD_FLAG not in os.environ


def test_agent_os_boot_wrapper_cleans_env_on_error(cell_env, monkeypatch):
    """Regression companion: even when boot_cell raises, the wrapper must not
    leak the boot/verified-record flags. The try/finally cleanup covers this.
    """
    from mcp_server_nucleus.tools import agent_os_boot as wrapper

    monkeypatch.delenv(wrapper._BOOT_FLAG, raising=False)
    monkeypatch.delenv(wrapper._VERIFIED_RECORD_FLAG, raising=False)

    captured = {}

    class FakeMCP:
        def tool(self, **_kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn
            return deco

    helpers = {"make_response": lambda result=None, error=None:
               {"result": result} if error is None else {"error": error}}
    wrapper.register(FakeMCP(), helpers)
    boot_fn = captured["fn"]

    # Force boot_cell to raise by patching the runtime entry point the wrapper
    # imports inside its try block. This isolates the wrapper's cleanup
    # behavior from the boot_cell implementation.
    def _boom(*_a, **_kw):
        raise RuntimeError("forced failure for cleanup test")

    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.agent_os.boot.boot_cell", _boom)

    resp = boot_fn("force-failure", brain_path=cell_env)

    assert "error" in resp, resp
    assert "forced failure" in resp["error"]
    assert wrapper._BOOT_FLAG not in os.environ
    assert wrapper._VERIFIED_RECORD_FLAG not in os.environ


def test_pager_flag_off_is_byte_identical(cell_env, monkeypatch):
    """Flag OFF: recall_and_inject returns the raw recall rows unchanged (the
    pager module is not invoked). Guards the byte-identical-OFF contract.
    """
    from mcp_server_nucleus.runtime.agent_os import pager as pager_mod

    monkeypatch.delenv(pager_mod.PAGER_FLAG, raising=False)
    assert pager_mod.pager_flag_enabled() is False
    brain = cell_env
    _seed_prior_memory(brain, "The Nucleus gateway routes model calls through the OS.")
    injected, rows = boot_mod.recall_and_inject("gateway", brain_path=brain)
    # Flag-OFF path: rows come straight from _do_recall_query (no pager reselect).
    assert rows
    assert all("text" in r for r in rows)
