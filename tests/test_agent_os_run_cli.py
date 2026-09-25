"""``nucleus agent-os run`` — the run CLI reuses boot_cell and fires the 3 proofs.

This exercises the run path end-to-end (stubbed provider, real recall + record)
and asserts the three proofs fire, mirroring test_agent_os_boot.py's patterns.
"""
import json
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os import run_cli


@pytest.fixture()
def run_env(tmp_path, monkeypatch):
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")  # deterministic offline model call
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    return str(brain)


def _seed_prior_memory(brain_path: str, text: str) -> None:
    from nucleus_wedge.store import Store

    Store(brain_path).append(value=text, kind="note", tags=["topic:gateway"],
                             source_agent="prior-session")


def test_run_cli_fires_three_proofs(run_env, capsys):
    brain = run_env
    prior = "The Nucleus gateway routes model calls through the OS; agents live INSIDE."
    _seed_prior_memory(brain, prior)

    rc = run_cli.run(
        "How should this agent route its model calls?",
        role="bespoq_cowork",
        brain_path=brain,
        recall_query="gateway",
    )

    out = capsys.readouterr().out
    # Exit 0 = the cell lived (all 3 proofs fired).
    assert rc == 0

    # PROOF 1 — mediated cognition (LLM_GENERATE event written).
    assert "PROOF 1" in out
    assert "mediated      : True" in out
    events = (boot_mod.Path(brain) / "ledger" / "events.jsonl").read_text().splitlines()
    llm_events = [json.loads(l) for l in events if l.strip() and json.loads(l)["type"] == "LLM_GENERATE"]
    assert llm_events, "run_cli must write a LLM_GENERATE event (proof of mediation)"

    # PROOF 2 — real recalled memory injected before thinking.
    assert "PROOF 2" in out
    assert prior in out  # the injected context block is printed

    # PROOF 3 — turn recorded to the flywheel.
    assert "PROOF 3" in out
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["metadata"]["mediated_by"] == "NucleusGateway"

    # The model response (stub) is printed and coherent with the injected memory.
    assert "MODEL RESPONSE" in out
    assert "mediated by the Nucleus gateway" in out


def test_run_cli_refuses_when_flag_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv(boot_mod.BOOT_FLAG, raising=False)
    rc = run_cli.run("anything", brain_path=str(tmp_path))
    assert rc == 2
    out = capsys.readouterr().out
    assert "OFF" in out
