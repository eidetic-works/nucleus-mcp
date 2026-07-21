"""Agent OS — ``nucleus agent-os corpus``: surface the VERIFIED-labeled training corpus.

The flywheel (``boot.record_turn_to_flywheel``) appends each cell's turn to
``.brain/training/loop_turns.jsonl``. When the referee flag is ON
(``NUCLEUS_AGENT_OS_VERIFIED_RECORD``), each turn carries a
``verified_label``: ``{status, confidence, detail}`` — the MOAT: verified
trajectories, not raw vibes. This command makes that corpus visible and is
the input the learner / canary will consume.

It is a thin, read-only CLI wrapper. It does NOT reimplement brain access —
it locates ``loop_turns.jsonl`` the SAME way ``boot.record_turn_to_flywheel``
does (brain path from ``--brain-path`` or ``NUCLEUS_BRAIN_PATH`` or
``get_brain_path()``, then the ``training`` subdir), reads every line, and
prints a compact tally:

    # verified corpus (<total> turns, <labeled> labeled)
      CONFIRMED: <n>
      REFUTED: <n>
      UNVERIFIABLE: <n>
      PARTIAL: <n>
      unlabeled: <n>

With ``--export FILE`` it writes a jsonl of just the turns whose
``verified_label.status`` matches ``--status`` (default ``CONFIRMED``) — the
clean verified-positive training set.

Robust to malformed / legacy lines: a bad line is skipped, never crashes the
tally. If ``loop_turns.jsonl`` is missing entirely, prints a clean
``no corpus yet (0 turns)`` and exits 0.

STRICTLY ADDITIVE. No .sh / settings.json / live-hook edits.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from . import boot as boot_mod

# The referee verdict statuses (mirrors ``verified_record.label_turn`` output).
_KNOWN_STATUSES = ("CONFIRMED", "REFUTED", "UNVERIFIABLE", "PARTIAL")
_UNLABELED = "unlabeled"


def _resolve_turns_path(brain_path: Optional[str] = None) -> Path:
    """Locate ``loop_turns.jsonl`` the same way ``boot`` does.

    Resolution order mirrors ``boot._ensure_brain_scaffold`` /
    ``archive_pipeline.ArchivePipeline``: explicit arg → ``NUCLEUS_BRAIN_PATH``
    env → ``get_brain_path()`` from ``..common`` → ``.brain``. Then the
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
    """Read every jsonl line, skipping blank / malformed / legacy lines."""
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
    """The verified_label status for a turn, or ``unlabeled`` if absent."""
    label = turn.get("verified_label")
    if isinstance(label, dict):
        status = label.get("status")
        if isinstance(status, str) and status:
            return status
    return _UNLABELED


def corpus(
    *,
    brain_path: Optional[str] = None,
    export: Optional[str] = None,
    status: str = "CONFIRMED",
    format: str = "text",
) -> int:
    """Surface the verified-labeled training corpus and optionally export a slice.

    Prints a compact tally of total turns, labeled turns, and a per-status
    breakdown. With ``export`` set, writes a jsonl of just the turns whose
    ``verified_label.status`` matches ``status`` (default ``CONFIRMED``).

    Returns 0 always (missing corpus is a clean empty state, not an error).
    """
    turns_path = _resolve_turns_path(brain_path)
    turns = _read_turns(turns_path)

    if not turns:
        if format == "json":
            data = {
                "total": 0,
                "labeled": 0,
                "status_counts": {
                    "CONFIRMED": 0,
                    "REFUTED": 0,
                    "UNVERIFIABLE": 0,
                    "PARTIAL": 0,
                    "unlabeled": 0
                },
                "CONFIRMED": 0,
                "REFUTED": 0,
                "UNVERIFIABLE": 0,
                "PARTIAL": 0,
                "unlabeled": 0
            }
            print(json.dumps(data))
        else:
            print(f"# verified corpus (0 turns, 0 labeled)")
            print(f"  no corpus yet — {turns_path} not found or empty")
        if export:
            # Still write an empty file so downstream pipelines get a stable
            # artifact (a missing file is a different failure mode than empty).
            try:
                Path(export).write_text("", encoding="utf-8")
                if format != "json":
                    print(f"exported 0 {status} turns -> {export}")
            except OSError as exc:  # noqa: BLE001
                print(f"[agent-os corpus] export failed: {exc}")
                return 1
        return 0

    # Tally: total, labeled, per-status (known statuses in canonical order,
    # then any unknown status that shows up, then unlabeled last).
    counts: dict[str, int] = {s: 0 for s in _KNOWN_STATUSES}
    unknown: dict[str, int] = {}
    labeled = 0
    for t in turns:
        s = _status_of(t)
        if s == _UNLABELED:
            continue
        labeled += 1
        if s in counts:
            counts[s] += 1
        else:
            unknown[s] = unknown.get(s, 0) + 1
    counts[_UNLABELED] = len(turns) - labeled

    if format == "json":
        status_counts = {}
        for s in _KNOWN_STATUSES:
            status_counts[s] = counts[s]
        for s in sorted(unknown):
            status_counts[s] = unknown[s]
        status_counts[_UNLABELED] = counts[_UNLABELED]

        data = {
            "total": len(turns),
            "labeled": labeled,
            "status_counts": status_counts,
        }
        for k, v in status_counts.items():
            data[k] = v
        print(json.dumps(data))
    else:
        print(f"# verified corpus ({len(turns)} turns, {labeled} labeled)")
        for s in _KNOWN_STATUSES:
            print(f"  {s}: {counts[s]}")
        for s in sorted(unknown):
            print(f"  {s}: {unknown[s]}")
        if counts[_UNLABELED]:
            print(f"  {_UNLABELED}: {counts[_UNLABELED]}")

    if export:
        selected = [t for t in turns if _status_of(t) == status]
        try:
            with open(export, "w", encoding="utf-8") as f:
                for t in selected:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
            if format != "json":
                print(f"exported {len(selected)} {status} turns -> {export}")
        except OSError as exc:  # noqa: BLE001
            print(f"[agent-os corpus] export failed: {exc}")
            return 1

    return 0


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os corpus``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os corpus",
        description=(
            "Surface the VERIFIED-labeled training corpus in loop_turns.jsonl "
            "(the moat). Prints a per-status tally; optionally exports a slice."
        ),
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this read.",
    )
    parser.add_argument(
        "--export",
        default=None,
        help="Write a jsonl of just the turns matching --status to this file.",
    )
    parser.add_argument(
        "--status",
        default="CONFIRMED",
        help=(
            "Which verified_label.status to export (default: CONFIRMED). "
            "One of CONFIRMED / REFUTED / UNVERIFIABLE / PARTIAL."
        ),
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json"],
        help="Output format (text or json, default: text).",
    )
    args = parser.parse_args(argv)
    return corpus(
        brain_path=args.brain_path,
        export=args.export,
        status=args.status,
        format=args.format,
    )


if __name__ == "__main__":
    raise SystemExit(main())
