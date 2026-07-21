"""Agent OS — ``nucleus agent-os canary``: the moat's immune system v0.

CANARY.md §1b — temporal-consequence drift. The flywheel
(``boot.record_turn_to_flywheel``) appends each cell's turn to
``.brain/training/loop_turns.jsonl`` with a ``verified_label`` — the referee
verdict at *record-time*. But the world moves: a file that existed when the
label was minted can be gone now, a URL that returned 200 can be dead, a commit
can be force-pushed away. A CONFIRMED label whose anchor broke *under* it is
drift — the corpus is lying about the present.

This command RE-verifies every turn whose stored ``verified_label.status`` is
``CONFIRMED`` by re-running ``verified_record.label_turn`` on the SAME outcome
text the original label was derived from, RIGHT NOW. Same referee, re-run over
time = temporal drift detector. Any turn that comes back non-CONFIRMED is
flagged as ``DRIFT``.

It is a thin, read-only CLI wrapper. It locates ``loop_turns.jsonl`` the SAME
way ``corpus_cli`` does (brain path from ``--brain-path`` or
``NUCLEUS_BRAIN_PATH`` or ``get_brain_path()``, then the ``training`` subdir),
reads every line, filters to CONFIRMED, and re-verifies. It NEVER writes the
corpus — pure analysis.

Robust to malformed / legacy lines: a bad line is skipped, never crashes the
check. If ``loop_turns.jsonl`` is missing or has no CONFIRMED turns, prints a
clean ``no corpus yet`` and exits 0.

STRICTLY ADDITIVE. No .sh / settings.json / live-hook edits.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .verified_record import label_turn


def _resolve_turns_path(brain_path: Optional[str] = None) -> Path:
    """Locate ``loop_turns.jsonl`` the same way ``corpus_cli`` does.

    Resolution order mirrors ``corpus_cli._resolve_turns_path`` (which mirrors
    ``boot._ensure_brain_scaffold``): explicit arg → ``NUCLEUS_BRAIN_PATH`` env
    → ``get_brain_path()`` from ``..common`` → ``.brain``. Then the
    ``training`` subdir + ``loop_turns.jsonl``. Does NOT mkdir (read-only).
    """
    if brain_path:
        root = Path(brain_path)
    else:
        env_path = os.environ.get("NUCLEUS_BRAIN_PATH")
        if env_path:
            root = Path(env_path)
        else:
            try:
                from ..common import get_brain_path

                root = Path(get_brain_path())
            except Exception:  # noqa: BLE001 — cold brain, no daemon scaffold
                root = Path(".brain")
    return root / "training" / "loop_turns.jsonl"


def _read_turns(path: Path) -> list[dict]:
    """Read every jsonl line, skipping blank / malformed / legacy lines.

    Byte-identical to ``corpus_cli._read_turns`` — same robustness contract.
    """
    if not path.exists():
        return []
    turns: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:  # noqa: BLE001 — unreadable file, treat as empty
        return []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue  # malformed / legacy line — skip, don't crash
        if isinstance(obj, dict):
            turns.append(obj)
    return turns


def _status_of(turn: dict) -> str:
    """The verified_label status for a turn, or empty string if absent."""
    label = turn.get("verified_label")
    if isinstance(label, dict):
        status = label.get("status")
        if isinstance(status, str) and status:
            return status
    return ""


def _outcome_text(turn: dict) -> str:
    """The text the original label was derived from.

    Per ``boot.record_turn_to_flywheel`` + ``boot.boot_cell``: the referee labels
    the model's *outcome* text (``gateway_result.text``), persisted as the
    ``outcome`` field. If ``outcome`` is missing or empty (legacy / partial
    record), fall back to ``intent`` — the task prompt that drove the turn.
    If both are missing, return empty (caller skips).
    """
    outcome = turn.get("outcome")
    if isinstance(outcome, str) and outcome.strip():
        return outcome
    intent = turn.get("intent")
    if isinstance(intent, str) and intent.strip():
        return intent
    return ""


def canary(
    *,
    brain_path: Optional[str] = None,
    sample: Optional[int] = None,
    verifier=None,
    export: bool = False,
    json_output: bool = False,
) -> int:
    """Re-verify CONFIRMED turns and flag temporal-consequence drift.

    Reads ``loop_turns.jsonl``, selects turns whose ``verified_label.status`` is
    ``CONFIRMED``, and re-runs ``label_turn`` on each one's outcome text. Any
    turn whose new status is not ``CONFIRMED`` is drift — the world moved under
    the label.

    ``sample`` limits the re-check to the first N CONFIRMED turns (deterministic
    — order preserved from the file). ``verifier`` is an optional
    ``Verifier`` instance passed through to ``label_turn`` (defaults to the
    standard ``RuleReasoner``-backed verifier; used by tests to inject
    deterministic fs anchors).

    ``export`` writes drifted turns to
    ``.brain/training/canary_drift_<timestamp>.jsonl`` so the learner (future)
    can consume them. No drift = no file written.

    ``json_output`` prints the drift results as a single JSON object to stdout
    instead of the human-readable text report. Additive — when False (default)
    the text report is byte-identical to the pre-flag behavior.

    Returns 0 always (missing corpus / zero drift / drift found are all
    informational states, not errors). Read-only — never writes the corpus
    (only writes the drift export when ``export=True`` and drift is found).
    """
    from ..verifier import Verifier  # noqa: F401 — re-exported for type hints

    turns_path = _resolve_turns_path(brain_path)
    turns = _read_turns(turns_path)

    confirmed = [t for t in turns if _status_of(t) == "CONFIRMED"]

    if not confirmed:
        if json_output:
            print(json.dumps({
                "rechecked": 0,
                "drift_count": 0,
                "drift_pct": 0.0,
                "drifted_turns": [],
                "sampled": False,
                "message": "no corpus yet (0 CONFIRMED turns to re-check)",
            }, ensure_ascii=False))
            return 0
        print(f"# canary: no corpus yet (0 CONFIRMED turns to re-check)")
        return 0

    sampled = False
    if sample is not None and sample > 0 and sample < len(confirmed):
        confirmed = confirmed[:sample]
        sampled = True

    drift_count = 0
    drift_lines: list[str] = []
    drift_turns: list[dict] = []
    for i, turn in enumerate(confirmed):
        outcome = _outcome_text(turn)
        if not outcome:
            # No text to re-verify — can't drift-check, skip silently.
            continue
        claim_id = turn.get("turn_id") or f"canary_{i}"
        result = label_turn(outcome, claim_id=claim_id, verifier=verifier)
        new_status = result.get("status", "")
        if new_status != "CONFIRMED":
            drift_count += 1
            preview = outcome[:80].replace("\n", " ")
            drift_lines.append(f"  DRIFT [{new_status}] {preview}")
            drift_turns.append({
                "turn_id": turn.get("turn_id"),
                "old_status": "CONFIRMED",
                "new_status": new_status,
                "new_detail": result.get("detail", ""),
                "outcome_preview": preview,
                "original_turn": turn,
            })

    rechecked = len(confirmed)
    pct = (drift_count / rechecked) * 100 if rechecked else 0.0

    if json_output:
        print(json.dumps({
            "rechecked": rechecked,
            "drift_count": drift_count,
            "drift_pct": pct,
            "drifted_turns": drift_turns,
            "sampled": sampled,
            "sample": sample if sampled else None,
        }, ensure_ascii=False))
    else:
        header = f"# canary drift check ({rechecked} CONFIRMED turns re-verified)"
        if sampled:
            header += f" [sampled first {sample}]"
        print(header)

        if rechecked == 0:
            print("  clean — all re-verified CONFIRMED")
            return 0

        if drift_count == 0:
            print("  clean — all re-verified CONFIRMED")
        else:
            print(f"  drift: {pct:.0f}% ({drift_count} now non-CONFIRMED)")
            for line in drift_lines:
                print(line)

    # Export drifted turns for the learner (future, MOAT §2)
    if export and drift_turns:
        import time as _time
        ts = _time.strftime("%Y%m%dT%H%M%SZ", _time.gmtime())
        export_path = turns_path.parent / f"canary_drift_{ts}.jsonl"
        with open(export_path, "w") as f:
            for dt in drift_turns:
                f.write(json.dumps(dt, ensure_ascii=False) + "\n")
        if json_output:
            # Export is a side-channel file; in JSON mode we surface its path
            # via stderr so stdout stays a single clean JSON object.
            import sys as _sys
            _sys.stderr.write(
                f"exported {len(drift_turns)} drifted turns to {export_path}\n"
            )
        else:
            print(f"  exported {len(drift_turns)} drifted turns to {export_path}")

    return 0


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os canary``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os canary",
        description=(
            "Re-verify CONFIRMED turns in loop_turns.jsonl and flag temporal-"
            "consequence drift (the moat's immune system v0). Same referee, "
            "re-run over time = drift detector. Read-only."
        ),
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this read.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Re-check only the first N CONFIRMED turns (deterministic).",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        default=False,
        help="Export drifted turns to .brain/training/canary_drift_<ts>.jsonl "
             "for the learner (future, MOAT §2). No drift = no file written.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Print drift results as a single JSON object on stdout "
             "(rechecked, drift_count, drift_pct, drifted_turns, sampled, "
             "sample) instead of the human-readable text report. Default "
             "(flag omitted) is the text report, byte-identical to pre-flag "
             "behavior.",
    )
    args = parser.parse_args(argv)
    return canary(
        brain_path=args.brain_path,
        sample=args.sample,
        export=args.export,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
