"""``nucleus agent-os loop`` — the "run the loop for a while" primitive.

Exercises the loop CLI end-to-end against a seeded brain with the LLM stubbed
(no network): runs ``loop --count 3``, asserts 3 turns are recorded to
``loop_turns.jsonl`` and that the corpus + canary summaries print. Mirrors the
fixture/seed/env patterns from ``test_agent_os_run_cli.py`` and
``test_agent_os_loop_e2e.py`` — no invented APIs. Deterministic + offline.

The real-Groq path (live provider, non-stub engine) is skipped when no
``GROQ_API_KEY`` is present — the stub path is the one tested here.
"""
from __future__ import annotations

import json
import os

import pytest

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os import loop_cli


def _seed_prior_memory(brain_path: str, text: str) -> None:
    """Verbatim from test_agent_os_run_cli._seed_prior_memory."""
    from nucleus_wedge.store import Store

    Store(brain_path).append(
        value=text,
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )


@pytest.fixture()
def loop_env(tmp_path, monkeypatch):
    """Same env shape the other agent-os tests use (stubbed LLM, offline)."""
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")  # deterministic offline model
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")  # referee labels ON
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    return str(brain)


def test_loop_cli_runs_n_cells_and_prints_summaries(loop_env, capsys):
    """``loop --count 3`` records 3 turns and prints corpus + canary summaries."""
    brain = loop_env
    prior = "The Nucleus gateway routes model calls through the OS; agents live INSIDE."
    _seed_prior_memory(brain, prior)

    rc = loop_cli.loop(count=3, brain_path=brain, recall_query="gateway")

    out = capsys.readouterr().out

    # Every cell booted (stubbed provider, real recall + record) → exit 0.
    assert rc == 0, f"loop must exit 0 when all cells alive; got rc={rc}\nout:\n{out}"

    # ── 3 turns recorded to loop_turns.jsonl ─────────────────────────────────
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    assert turns_path.exists(), "loop must write loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 3, (
        f"loop --count 3 must record exactly 3 turns; got {len(rows)}\nout:\n{out}"
    )
    # Each turn was mediated by the Nucleus gateway + recorded via the flywheel.
    for row in rows:
        assert row["metadata"]["mediated_by"] == "NucleusGateway"
        assert "verified_label" in row, (
            "VERIFIED_RECORD=ON must persist a referee verdict to each turn"
        )

    # ── Per-cell lines printed (engine=STUB, alive=True for each) ────────────
    assert "[agent-os loop] running 3 cell(s)" in out
    assert "cell 1/3:" in out
    assert "cell 2/3:" in out
    assert "cell 3/3:" in out
    assert "engine=STUB" in out  # stubbed provider path
    assert "[agent-os loop] 3/3 cell(s) alive" in out

    # ── Corpus tally summary printed (reuses corpus_cli) ─────────────────────
    assert "=== CORPUS TALLY ===" in out
    assert "# verified corpus (3 turns" in out, (
        f"corpus tally must show 3 turns; got:\n{out}"
    )

    # ── Canary drift check summary printed (reuses canary_cli) ───────────────
    assert "=== CANARY DRIFT CHECK ===" in out
    # Canary either re-verifies CONFIRMED turns or cleanly reports none — both
    # are valid outcomes depending on the referee's verdict distribution. The
    # contract is that it prints a header and exits cleanly (rc already 0).
    assert ("# canary drift check" in out) or ("# canary: no corpus yet" in out), (
        f"canary must print its summary header; got:\n{out}"
    )


def test_loop_cli_refuses_when_flag_off(tmp_path, monkeypatch, capsys):
    """When the boot flag is OFF, loop refuses with exit 2 and a hint."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv(boot_mod.BOOT_FLAG, raising=False)
    rc = loop_cli.loop(count=2, brain_path=str(tmp_path))
    assert rc == 2
    out = capsys.readouterr().out
    assert "OFF" in out
    # No turns written when the flag is off.
    turns_path = boot_mod.Path(tmp_path) / "training" / "loop_turns.jsonl"
    assert not turns_path.exists()


def test_loop_cli_rejects_zero_count(loop_env, capsys):
    """``--count 0`` (or negative) is rejected with exit 2 before any cell runs."""
    rc = loop_cli.loop(count=0, brain_path=loop_env)
    assert rc == 2
    out = capsys.readouterr().out
    assert "--count must be >= 1" in out


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="real-Groq path requires GROQ_API_KEY; stub path is covered above",
)
def test_loop_cli_real_groq_when_key_present(tmp_path, monkeypatch, capsys):
    """When a live Groq key is present, the loop uses the real provider lane.

    Skipped by default (no key in CI). Run locally with ``GROQ_API_KEY`` set to
    exercise the non-stub path. Marked xfail/skip per spec — this is the skip
    branch; the assertion below only fires when the key is actually present.
    """
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.delenv(boot_mod.STUB_FLAG, raising=False)  # let the real provider run
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    _seed_prior_memory(str(brain), "The Nucleus gateway routes model calls through the OS.")

    rc = loop_cli.loop(count=2, brain_path=str(brain))
    out = capsys.readouterr().out
    assert rc == 0
    # At least one cell should report a non-STUB engine when Groq is reachable.
    assert "engine=GROQ" in out or "engine=NEW" in out, (
        f"real-Groq path must report a non-STUB engine; got:\n{out}"
    )
