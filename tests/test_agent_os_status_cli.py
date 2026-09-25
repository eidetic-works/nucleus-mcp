"""``nucleus agent-os status`` — one dashboard for the moat loop.

Exercises the combined read-only report against a seeded ``loop_turns.jsonl``:
asserts the status output shows (1) the corpus tally by verdict, (2) a canary
line, and (3) a providers line. Also covers the empty-brain clean-report case.
No network.
"""
from __future__ import annotations

import json

from mcp_server_nucleus.runtime.agent_os import status_cli


def _seed_turns(brain_path: str, turns: list[dict]) -> None:
    """Write a loop_turns.jsonl directly under <brain>/training/.

    Same pattern as ``test_agent_os_corpus_cli._seed_turns``.
    """
    from pathlib import Path

    training = Path(brain_path) / "training"
    training.mkdir(parents=True, exist_ok=True)
    f = training / "loop_turns.jsonl"
    with open(f, "w", encoding="utf-8") as fh:
        for t in turns:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")


def _make_turn(intent: str, label: dict | None = None) -> dict:
    t = {"turn_id": f"t-{intent}", "intent": intent, "outcome": intent}
    if label is not None:
        t["verified_label"] = label
    return t


def test_status_combines_corpus_canary_providers(tmp_path, capsys):
    """Seeded turns → status report shows corpus tally + canary line + providers line."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("shipped feature a", {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok"}),
        _make_turn("shipped feature b", {"status": "CONFIRMED", "confidence": 0.8, "detail": "ok"}),
        _make_turn("vibe turn c", {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"}),
        _make_turn("unlabeled turn d"),  # unlabeled
    ]
    _seed_turns(str(brain), turns)

    rc = status_cli.status(brain_path=str(brain))

    assert rc == 0
    out = capsys.readouterr().out
    # Top-level banner
    assert "# agent-os status" in out
    # (1) corpus tally — 4 valid turns, 3 labeled (2 CONFIRMED + 1 UNVERIFIABLE)
    assert "# verified corpus (4 turns, 3 labeled)" in out
    assert "CONFIRMED: 2" in out
    assert "UNVERIFIABLE: 1" in out
    assert "unlabeled: 1" in out
    # (2) canary line — 2 CONFIRMED turns re-verified (drift expected: benign
    # outcome text has no SHA/URL anchors → re-verify returns UNVERIFIABLE).
    assert "canary" in out
    assert "CONFIRMED turns re-verified" in out
    # (3) providers line
    assert "# providers" in out
    assert "available" in out


def test_status_empty_brain_is_clean(tmp_path, capsys):
    """No loop_turns.jsonl → clean report with all three sections, exit 0."""
    brain = tmp_path / "brain"
    rc = status_cli.status(brain_path=str(brain))

    assert rc == 0
    out = capsys.readouterr().out
    assert "# agent-os status" in out
    # corpus: clean empty
    assert "# verified corpus (0 turns, 0 labeled)" in out
    assert "no corpus yet" in out
    # canary: clean empty (no CONFIRMED turns to re-check)
    assert "canary" in out
    assert "no corpus yet" in out
    # providers: still rendered (scheduler reads env / file creds, not the brain)
    assert "# providers" in out


def test_status_sample_passes_through_to_canary(tmp_path, capsys):
    """--sample N limits the canary re-check to the first N CONFIRMED turns."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("shipped a", {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok"}),
        _make_turn("shipped b", {"status": "CONFIRMED", "confidence": 0.8, "detail": "ok"}),
        _make_turn("shipped c", {"status": "CONFIRMED", "confidence": 0.7, "detail": "ok"}),
    ]
    _seed_turns(str(brain), turns)

    rc = status_cli.status(brain_path=str(brain), sample=1)

    assert rc == 0
    out = capsys.readouterr().out
    # canary re-checked only 1 turn (sampled)
    assert "(1 CONFIRMED turns re-verified)" in out
    assert "[sampled first 1]" in out
