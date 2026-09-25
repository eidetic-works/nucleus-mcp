"""Agent-OS moat LOOP — end-to-end composition test.

Proves the four bricks compose into ONE loop, not just that each brick works
in isolation:

  1. RUN    — ``boot_cell`` boots one turn INSIDE the OS (pager-selected recall,
              mediated cognition, referee verdict attached).
  2. PERSIST— the referee verdict lands in ``loop_turns.jsonl`` on disk (the
              on-disk corpus is REFEREE-verified, not just the in-memory result).
  3. CORPUS — ``corpus_cli.corpus`` reads that same jsonl and its tally reflects
              the labeled turn just recorded.
  4. CANARY — ``canary_cli.canary`` re-verifies the corpus against the present
              and reports a sane drift number (clean for a just-recorded turn
              whose anchor still holds, or a clean no-CONFIRMED-to-recheck
              report when the turn is UNVERIFIABLE — canary must not crash
              either way).

Reuses the exact fixture/seed/env + invocation patterns from
``test_agent_os_run_cli.py``, ``test_agent_os_verified_record.py``,
``test_agent_os_corpus_cli.py``, and ``test_agent_os_canary_cli.py`` — no
invented APIs. Deterministic + offline (LLM stubbed).
"""
from __future__ import annotations

import json

from mcp_server_nucleus.runtime.agent_os import boot as boot_mod
from mcp_server_nucleus.runtime.agent_os import canary_cli, corpus_cli


def _seed_prior_memory(brain_path: str, text: str) -> None:
    """Verbatim from test_agent_os_run_cli._seed_prior_memory."""
    from nucleus_wedge.store import Store

    Store(brain_path).append(
        value=text,
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )


_VALID_STATUSES = {"CONFIRMED", "REFUTED", "UNVERIFIABLE", "PARTIAL"}


def test_moat_loop_end_to_end(tmp_path, monkeypatch, capsys):
    """The four bricks compose: run → persist → corpus → canary, one brain."""
    # ── fixture: same env shape the other agent-os tests use ────────────────
    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")  # deterministic offline model
    monkeypatch.setenv(boot_mod.PAGER_FLAG, "1")  # Stage-1 pager selected
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")  # referee labels ON
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")

    prior = "The Nucleus gateway routes model calls through the OS; agents live INSIDE."
    _seed_prior_memory(str(brain), prior)

    # ── 1. RUN: boot one turn inside the OS ─────────────────────────────────
    result = boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=str(brain),
    )

    # Pager selected real memory → recalled_from_memory True.
    assert result.recalled_from_memory is True, (
        "pager-ON boot must recall the seeded prior memory"
    )
    assert any(prior in (r.get("text") or "") for r in result.recalled_rows), (
        "the seeded gateway memory must be in the recalled rows"
    )
    # Referee verdict attached to the in-memory BootResult.
    assert result.verified_label is not None, (
        "VERIFIED_RECORD=ON must attach a referee verdict to BootResult"
    )
    assert result.verified_label.get("status") in _VALID_STATUSES
    assert isinstance(result.verified_label.get("confidence"), float)

    # ── 2. PERSIST: the verdict landed in loop_turns.jsonl on disk ──────────
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert rows, "boot_cell must write at least one turn to the flywheel"
    last = rows[-1]
    assert "verified_label" in last, (
        "verified_label must be persisted to disk (the on-disk corpus is verified)"
    )
    assert isinstance(last["verified_label"], dict)
    assert last["verified_label"].get("status") in _VALID_STATUSES
    recorded_status = last["verified_label"]["status"]

    # ── 3. CORPUS: the corpus reader's tally reflects the labeled turn ──────
    capsys.readouterr()  # clear boot stdout before corpus prints
    rc = corpus_cli.corpus(brain_path=str(brain))
    assert rc == 0
    out = capsys.readouterr().out
    # Exactly one turn was recorded → tally header reflects it.
    assert "# verified corpus (1 turns, 1 labeled)" in out, (
        f"corpus tally must show 1 turn / 1 labeled; got:\n{out}"
    )
    # The status the boot persisted is the status the corpus reports.
    assert f"{recorded_status}: 1" in out, (
        f"corpus must count the recorded {recorded_status} turn; got:\n{out}"
    )

    # ── 4. CANARY: re-verify the corpus against the present, no crash ───────
    capsys.readouterr()  # clear corpus stdout before canary prints
    rc = canary_cli.canary(brain_path=str(brain))
    assert rc == 0, "canary must exit 0 (drift is informational, not an error)"
    out = capsys.readouterr().out

    if recorded_status == "CONFIRMED":
        # The turn's anchor was deterministic at record-time; re-verify it now.
        # A just-recorded turn whose anchor still holds → clean, 0 drift.
        assert "# canary drift check (1 CONFIRMED turns re-verified)" in out, (
            f"canary must re-verify the 1 CONFIRMED turn; got:\n{out}"
        )
        assert "clean — all re-verified CONFIRMED" in out, (
            f"a just-recorded CONFIRMED turn must not drift; got:\n{out}"
        )
        assert "DRIFT" not in out
    else:
        # UNVERIFIABLE / REFUTED / PARTIAL turns are not in the CONFIRMED set
        # canary re-verifies → clean no-CONFIRMED-to-recheck report, no crash.
        assert "# canary: no corpus yet (0 CONFIRMED turns to re-check)" in out, (
            f"canary must cleanly skip non-CONFIRMED turns; got:\n{out}"
        )
        assert "DRIFT" not in out
