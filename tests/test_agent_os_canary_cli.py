"""``nucleus agent-os canary`` — temporal-consequence drift detector v0.

Exercises the re-verify path against a seeded ``loop_turns.jsonl``: CONFIRMED
turns whose outcome re-verifies to a KNOWN result via an ``InjectedReasoner``
with ``fs/file_exists`` anchors. One turn's anchor STILL holds (stays
CONFIRMED); one turn's anchor now FAILS (its file is gone → re-verify returns
non-CONFIRMED → drift). Also covers the no-CONFIRMED / missing-file clean-empty
case. No network.
"""
from __future__ import annotations

import json

from mcp_server_nucleus.runtime.agent_os import canary_cli
from mcp_server_nucleus.runtime.verifier import (
    Anchor,
    InjectedReasoner,
    ProbeEngine,
    Verifier,
)


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


def _make_turn(
    turn_id: str,
    outcome: str,
    label: dict | None = None,
) -> dict:
    t = {"turn_id": turn_id, "intent": turn_id, "outcome": outcome}
    if label is not None:
        t["verified_label"] = label
    return t


def _confirmed_label() -> dict:
    return {"status": "CONFIRMED", "confidence": 0.9, "detail": "ok at record-time"}


def _verifier_with_fs_anchors(anchors_by_claim_id: dict) -> Verifier:
    """Build a Verifier with an InjectedReasoner mapping claim_id → [Anchor].

    Each anchor is an ``fs/file_exists`` probe on a specific path. The canary
    calls ``label_turn(outcome, claim_id=turn_id, verifier=...)``, so the
    turn_id is the claim_id key.
    """
    return Verifier(
        reasoner=InjectedReasoner(anchors_by_claim_id),
        probe_engine=ProbeEngine(),
        ledger=None,
        record=False,
    )


# ── drift detection: one stays CONFIRMED, one drifts ──────────────────────────


def test_canary_detects_drift_when_anchor_breaks(tmp_path, capsys):
    """Two CONFIRMED turns: one anchor holds (stays CONFIRMED), one anchor
    breaks (file gone → non-CONFIRMED → drift). Assert drift reflects exactly
    the broken one.
    """
    brain = tmp_path / "brain"

    # Anchor that STILL holds: a real temp file.
    live_file = tmp_path / "live.txt"
    live_file.write_text("shipped\n", encoding="utf-8")

    # Anchor that now FAILS: a path that does not exist at re-check time.
    dead_path = str(tmp_path / "gone.txt")  # never created → file_exists fails

    turns = [
        _make_turn(
            "t-stays",
            "the output file was written",
            _confirmed_label(),
        ),
        _make_turn(
            "t-drifts",
            "the output file was written",
            _confirmed_label(),
        ),
    ]
    _seed_turns(str(brain), turns)

    verifier = _verifier_with_fs_anchors({
        "t-stays": [
            Anchor(
                "a-stays",
                "fs",
                {"op": "file_exists", "path": str(live_file)},
                "file exists",
                critical=True,
            )
        ],
        "t-drifts": [
            Anchor(
                "a-drifts",
                "fs",
                {"op": "file_exists", "path": dead_path},
                "file exists",
                critical=True,
            )
        ],
    })

    rc = canary_cli.canary(brain_path=str(brain), verifier=verifier)

    assert rc == 1  # drift found -> non-zero exit (239d6acb), so CI can gate on it
    out = capsys.readouterr().out
    assert "# canary drift check (2 CONFIRMED turns re-verified)" in out
    assert "drift: 50% (1 now non-CONFIRMED)" in out
    assert "DRIFT" in out
    assert "t-drifts" not in out  # turn_id not printed; outcome preview is
    # The drifted line shows the outcome preview and a non-CONFIRMED status.
    assert "the output file was written" in out


def test_canary_clean_when_all_anchors_hold(tmp_path, capsys):
    """All CONFIRMED turns re-verify to CONFIRMED → clean, 0 drift."""
    brain = tmp_path / "brain"

    live_a = tmp_path / "a.txt"
    live_a.write_text("ok\n", encoding="utf-8")
    live_b = tmp_path / "b.txt"
    live_b.write_text("ok\n", encoding="utf-8")

    turns = [
        _make_turn("t-a", "file a was written", _confirmed_label()),
        _make_turn("t-b", "file b was written", _confirmed_label()),
    ]
    _seed_turns(str(brain), turns)

    verifier = _verifier_with_fs_anchors({
        "t-a": [
            Anchor("a-a", "fs", {"op": "file_exists", "path": str(live_a)},
                   "file exists", critical=True)
        ],
        "t-b": [
            Anchor("a-b", "fs", {"op": "file_exists", "path": str(live_b)},
                   "file exists", critical=True)
        ],
    })

    rc = canary_cli.canary(brain_path=str(brain), verifier=verifier)

    assert rc == 0
    out = capsys.readouterr().out
    assert "# canary drift check (2 CONFIRMED turns re-verified)" in out
    assert "clean — all re-verified CONFIRMED" in out
    assert "drift:" not in out
    assert "DRIFT" not in out


# ── sample / robustness / clean-empty ─────────────────────────────────────────


def test_canary_sample_limits_recheck(tmp_path, capsys):
    """--sample N re-checks only the first N CONFIRMED turns."""
    brain = tmp_path / "brain"

    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")
    dead = str(tmp_path / "dead.txt")

    turns = [
        _make_turn("t-1", "first turn", _confirmed_label()),
        _make_turn("t-2", "second turn", _confirmed_label()),
        _make_turn("t-3", "third turn", _confirmed_label()),
    ]
    _seed_turns(str(brain), turns)

    verifier = _verifier_with_fs_anchors({
        "t-1": [Anchor("a1", "fs", {"op": "file_exists", "path": str(live)},
                        "exists", critical=True)],
        "t-2": [Anchor("a2", "fs", {"op": "file_exists", "path": dead},
                        "exists", critical=True)],
        "t-3": [Anchor("a3", "fs", {"op": "file_exists", "path": dead},
                        "exists", critical=True)],
    })

    rc = canary_cli.canary(brain_path=str(brain), sample=1, verifier=verifier)

    assert rc == 0
    out = capsys.readouterr().out
    assert "(1 CONFIRMED turns re-verified)" in out
    assert "[sampled first 1]" in out
    # Only t-1 was re-checked (its anchor holds) → clean.
    assert "clean — all re-verified CONFIRMED" in out


def test_canary_skips_malformed_lines(tmp_path, capsys):
    """Malformed / legacy lines are skipped, not crashed."""
    brain = tmp_path / "brain"
    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")

    turns = [
        _make_turn("t-ok", "the file was written", _confirmed_label()),
    ]
    _seed_turns(str(brain), turns)

    # Append a malformed line + a non-CONFIRMED labeled line.
    from pathlib import Path

    with open(Path(brain) / "training" / "loop_turns.jsonl", "a",
              encoding="utf-8") as fh:
        fh.write("{not valid json}\n")
        fh.write(json.dumps(
            _make_turn("t-unverifiable", "vibe",
                       {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"})
        ) + "\n")

    verifier = _verifier_with_fs_anchors({
        "t-ok": [Anchor("a1", "fs", {"op": "file_exists", "path": str(live)},
                        "exists", critical=True)],
    })

    rc = canary_cli.canary(brain_path=str(brain), verifier=verifier)

    assert rc == 0
    out = capsys.readouterr().out
    # Only 1 CONFIRMED turn (the UNVERIFIABLE one is not CONFIRMED).
    assert "(1 CONFIRMED turns re-verified)" in out
    assert "clean — all re-verified CONFIRMED" in out


def test_canary_no_confirmed_turns_is_clean_empty(tmp_path, capsys):
    """Corpus has turns but none are CONFIRMED → clean 0 message, exit 0."""
    brain = tmp_path / "brain"
    turns = [
        _make_turn("t-1", "vibe", {"status": "UNVERIFIABLE", "confidence": 0.3, "detail": "vibe"}),
        _make_turn("t-2", "vibe", {"status": "REFUTED", "confidence": 0.9, "detail": "no"}),
    ]
    _seed_turns(str(brain), turns)

    rc = canary_cli.canary(brain_path=str(brain))

    assert rc == 0
    out = capsys.readouterr().out
    assert "# canary: no corpus yet (0 CONFIRMED turns to re-check)" in out


def test_canary_missing_file_is_clean_empty(tmp_path, capsys):
    """No loop_turns.jsonl → clean 0 message, exit 0."""
    brain = tmp_path / "brain"
    rc = canary_cli.canary(brain_path=str(brain))
    assert rc == 0
    out = capsys.readouterr().out
    assert "# canary: no corpus yet (0 CONFIRMED turns to re-check)" in out


def test_canary_falls_back_to_intent_when_outcome_missing(tmp_path, capsys):
    """A turn with no ``outcome`` field falls back to ``intent`` for re-verify."""
    brain = tmp_path / "brain"
    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")

    # Turn with outcome stripped (legacy shape) — only intent present.
    turn = {"turn_id": "t-legacy", "intent": "the file was written",
            "verified_label": _confirmed_label()}
    _seed_turns(str(brain), [turn])

    verifier = _verifier_with_fs_anchors({
        "t-legacy": [Anchor("a1", "fs", {"op": "file_exists", "path": str(live)},
                             "exists", critical=True)],
    })

    rc = canary_cli.canary(brain_path=str(brain), verifier=verifier)

    assert rc == 0
    out = capsys.readouterr().out
    assert "(1 CONFIRMED turns re-verified)" in out
    assert "clean — all re-verified CONFIRMED" in out


# ── read-only contract ────────────────────────────────────────────────────────


def test_canary_does_not_modify_corpus(tmp_path, capsys):
    """Canary is read-only — the jsonl is byte-identical before and after."""
    from pathlib import Path

    brain = tmp_path / "brain"
    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")

    turns = [_make_turn("t-1", "the file was written", _confirmed_label())]
    _seed_turns(str(brain), turns)

    corpus_path = Path(brain) / "training" / "loop_turns.jsonl"
    before = corpus_path.read_text(encoding="utf-8")

    verifier = _verifier_with_fs_anchors({
        "t-1": [Anchor("a1", "fs", {"op": "file_exists", "path": str(live)},
                        "exists", critical=True)],
    })
    canary_cli.canary(brain_path=str(brain), verifier=verifier)

    after = corpus_path.read_text(encoding="utf-8")
    assert before == after, "canary must not modify the corpus"


# ── --json output mode ────────────────────────────────────────────────────────


def test_canary_json_flag_emits_valid_json_with_drift(tmp_path, capsys):
    """``--json`` prints a single JSON object with expected keys when drift
    is found. Stdout is exactly one JSON line (parseable, no text header).
    """
    brain = tmp_path / "brain"

    live_file = tmp_path / "live.txt"
    live_file.write_text("shipped\n", encoding="utf-8")
    dead_path = str(tmp_path / "gone.txt")

    turns = [
        _make_turn("t-stays", "the output file was written", _confirmed_label()),
        _make_turn("t-drifts", "the output file was written", _confirmed_label()),
    ]
    _seed_turns(str(brain), turns)

    verifier = _verifier_with_fs_anchors({
        "t-stays": [Anchor("a-stays", "fs",
                           {"op": "file_exists", "path": str(live_file)},
                           "file exists", critical=True)],
        "t-drifts": [Anchor("a-drifts", "fs",
                            {"op": "file_exists", "path": dead_path},
                            "file exists", critical=True)],
    })

    rc = canary_cli.canary(
        brain_path=str(brain), verifier=verifier, json_output=True
    )

    assert rc == 1  # drift found -> non-zero exit (239d6acb), so CI can gate on it
    out = capsys.readouterr().out
    # Exactly one JSON object on stdout (single line).
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 JSON line, got {lines!r}"
    obj = json.loads(lines[0])

    assert obj["rechecked"] == 2
    assert obj["drift_count"] == 1
    assert obj["drift_pct"] == 50.0
    assert obj["sampled"] is False
    assert obj["sample"] is None
    drifted = obj["drifted_turns"]
    assert isinstance(drifted, list)
    assert len(drifted) == 1
    assert drifted[0]["turn_id"] == "t-drifts"
    assert drifted[0]["old_status"] == "CONFIRMED"
    assert drifted[0]["new_status"] != "CONFIRMED"
    # No text-report artifacts leak into JSON mode.
    assert "# canary" not in out
    assert "DRIFT" not in out


def test_canary_json_flag_clean_when_no_drift(tmp_path, capsys):
    """``--json`` with zero drift emits rechecked + empty drifted_turns."""
    brain = tmp_path / "brain"
    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")

    turns = [_make_turn("t-a", "file a was written", _confirmed_label())]
    _seed_turns(str(brain), turns)

    verifier = _verifier_with_fs_anchors({
        "t-a": [Anchor("a-a", "fs", {"op": "file_exists", "path": str(live)},
                       "file exists", critical=True)],
    })

    rc = canary_cli.canary(
        brain_path=str(brain), verifier=verifier, json_output=True
    )

    assert rc == 0
    out = capsys.readouterr().out
    obj = json.loads(out.strip())
    assert obj["rechecked"] == 1
    assert obj["drift_count"] == 0
    assert obj["drift_pct"] == 0.0
    assert obj["drifted_turns"] == []


def test_canary_json_flag_no_corpus(tmp_path, capsys):
    """``--json`` with no CONFIRMED turns emits the empty-corpus shape."""
    brain = tmp_path / "brain"
    rc = canary_cli.canary(brain_path=str(brain), json_output=True)

    assert rc == 0
    out = capsys.readouterr().out
    obj = json.loads(out.strip())
    assert obj["rechecked"] == 0
    assert obj["drift_count"] == 0
    assert obj["drifted_turns"] == []
    assert "no corpus yet" in obj["message"]


def test_canary_json_flag_via_main_argv(tmp_path, capsys, monkeypatch):
    """``main(['--json', '--brain-path', ...])`` wires the flag through argparse
    and produces the same JSON shape as the direct ``canary()`` call.
    """
    brain = tmp_path / "brain"
    live = tmp_path / "live.txt"
    live.write_text("ok\n", encoding="utf-8")
    dead = str(tmp_path / "dead.txt")

    turns = [
        _make_turn("t-ok", "the file was written", _confirmed_label()),
        _make_turn("t-bad", "the file was written", _confirmed_label()),
    ]
    _seed_turns(str(brain), turns)

    # Inject the verifier via env so main() (which builds its own verifier as
    # None) still re-verifies deterministically. We do this by monkeypatching
    # label_turn to route through our verifier.
    real_label_turn = canary_cli.label_turn
    verifier = _verifier_with_fs_anchors({
        "t-ok": [Anchor("a1", "fs", {"op": "file_exists", "path": str(live)},
                        "exists", critical=True)],
        "t-bad": [Anchor("a2", "fs", {"op": "file_exists", "path": dead},
                         "exists", critical=True)],
    })

    def _patched_label_turn(outcome, *, claim_id=None, verifier=None, **kw):
        return real_label_turn(
            outcome, claim_id=claim_id, verifier=verifier, **kw
        )

    # canary() uses the module-level label_turn import; patch it so the
    # verifier is injected regardless of what main() passes (None).
    monkeypatch.setattr(
        canary_cli, "label_turn",
        lambda outcome, **kw: real_label_turn(
            outcome, **{**kw, "verifier": verifier}
        ),
    )

    rc = canary_cli.main(
        ["--json", "--brain-path", str(brain)]
    )

    assert rc == 1  # drift found -> non-zero exit (239d6acb), so CI can gate on it
    out = capsys.readouterr().out
    obj = json.loads(out.strip())
    assert obj["rechecked"] == 2
    assert obj["drift_count"] == 1
    assert obj["drift_pct"] == 50.0
    assert len(obj["drifted_turns"]) == 1
