"""``nucleus agent-os corpus`` — surface the VERIFIED-labeled training corpus.

Exercises the read-only tally + export path against a seeded
``loop_turns.jsonl``: a mix of CONFIRMED / UNVERIFIABLE / unlabeled turns
plus a malformed line (must be skipped, not crash). Also covers the
missing-file clean-empty case. No network.
"""
from __future__ import annotations

import json

from mcp_server_nucleus.runtime.agent_os import corpus_cli


def _seed_turns(brain_path: str, turns: list[dict]) -> None:
    """Write a loop_turns.jsonl directly under <brain>/training/."""
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


def test_corpus_tally_matches_seed(tmp_path, capsys):
    """Seeded CONFIRMED / UNVERIFIABLE / unlabeled + a bad line → right counts."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("a", {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok"}),
        _make_turn("b", {"status": "CONFIRMED", "confidence": 0.8, "detail": "ok"}),
        _make_turn("c", {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"}),
        _make_turn("d"),  # unlabeled
        _make_turn("e"),  # unlabeled
    ]
    _seed_turns(str(brain), turns)
    # Append a malformed line directly to prove robustness.
    from pathlib import Path

    with open(Path(brain) / "training" / "loop_turns.jsonl", "a", encoding="utf-8") as fh:
        fh.write("{not valid json}\n")

    rc = corpus_cli.corpus(brain_path=str(brain))

    assert rc == 0
    out = capsys.readouterr().out
    # 5 valid turns (bad line skipped), 3 labeled (2 CONFIRMED + 1 UNVERIFIABLE).
    assert "# verified corpus (5 turns, 3 labeled)" in out
    assert "CONFIRMED: 2" in out
    assert "UNVERIFIABLE: 1" in out
    assert "REFUTED: 0" in out
    assert "PARTIAL: 0" in out
    assert "unlabeled: 2" in out


def test_corpus_export_confirmed_writes_only_confirmed(tmp_path, capsys):
    """--export CONFIRMED writes a jsonl of just the CONFIRMED turns."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("a", {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok"}),
        _make_turn("b", {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"}),
        _make_turn("c", {"status": "CONFIRMED", "confidence": 0.8, "detail": "ok"}),
        _make_turn("d"),  # unlabeled
    ]
    _seed_turns(str(brain), turns)
    export_path = tmp_path / "confirmed.jsonl"

    rc = corpus_cli.corpus(
        brain_path=str(brain), export=str(export_path), status="CONFIRMED"
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "exported 2 CONFIRMED turns ->" in out

    rows = [
        json.loads(l)
        for l in export_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(rows) == 2
    assert all(r["verified_label"]["status"] == "CONFIRMED" for r in rows)
    assert {r["intent"] for r in rows} == {"a", "c"}


def test_corpus_missing_file_is_clean_empty(tmp_path, capsys):
    """No loop_turns.jsonl → clean '0 turns' message, exit 0."""
    brain = tmp_path / "brain"
    rc = corpus_cli.corpus(brain_path=str(brain))
    assert rc == 0
    out = capsys.readouterr().out
    assert "# verified corpus (0 turns, 0 labeled)" in out
    assert "no corpus yet" in out


def test_corpus_export_on_missing_file_writes_empty(tmp_path, capsys):
    """--export on a missing corpus writes an empty file (stable artifact)."""
    brain = tmp_path / "brain"
    export_path = tmp_path / "confirmed.jsonl"
    rc = corpus_cli.corpus(
        brain_path=str(brain), export=str(export_path), status="CONFIRMED"
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "exported 0 CONFIRMED turns ->" in out
    assert export_path.exists()
    assert export_path.read_text(encoding="utf-8") == ""


def test_corpus_format_json_output(tmp_path, capsys):
    """Passing format="json" outputs correct JSON representation of corpus tally."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("a", {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok"}),
        _make_turn("b", {"status": "CONFIRMED", "confidence": 0.8, "detail": "ok"}),
        _make_turn("c", {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"}),
        _make_turn("d"),  # unlabeled
        _make_turn("e"),  # unlabeled
    ]
    _seed_turns(str(brain), turns)

    # Test with seeded turns
    rc = corpus_cli.corpus(brain_path=str(brain), format="json")
    assert rc == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["total"] == 5
    assert data["labeled"] == 3
    assert data["CONFIRMED"] == 2
    assert data["UNVERIFIABLE"] == 1
    assert data["REFUTED"] == 0
    assert data["PARTIAL"] == 0
    assert data["unlabeled"] == 2
    assert data["status_counts"]["CONFIRMED"] == 2
    assert data["status_counts"]["unlabeled"] == 2

    # Test with missing file
    brain_empty = tmp_path / "brain_empty"
    rc_empty = corpus_cli.corpus(brain_path=str(brain_empty), format="json")
    assert rc_empty == 0
    out_empty = capsys.readouterr().out.strip()
    data_empty = json.loads(out_empty)
    assert data_empty["total"] == 0
    assert data_empty["labeled"] == 0
    assert data_empty["status_counts"]["CONFIRMED"] == 0

