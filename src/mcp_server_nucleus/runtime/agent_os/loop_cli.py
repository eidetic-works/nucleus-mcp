"""Agent OS — ``nucleus agent-os loop``: run the loop for a while.

The "run the loop for a while" primitive. Runs N cells through ``boot_cell``
(``runtime.agent_os.boot``) — real inference when available (Groq via the
cognition scheduler; falls back to the deterministic stub when no provider is
reachable, so the command still runs and tests pass offline) — recording every
turn to the flywheel (``.brain/training/loop_turns.jsonl``). At the end it runs
the corpus tally (``corpus_cli.corpus``) and the canary drift check
(``canary_cli.canary``) and prints their summaries.

This is a thin CLI wrapper. It does NOT reimplement the loop, the corpus tally,
or the canary — it reuses ``boot_cell`` + ``corpus_cli.corpus`` +
``canary_cli.canary`` directly. The boot flags
(``NUCLEUS_AGENT_OS_BOOT`` / ``NUCLEUS_AGENT_OS_PAGER`` /
``NUCLEUS_AGENT_OS_VERIFIED_RECORD``) are honored exactly as ``run_cli``
honors them: ``boot_cell`` raises ``RuntimeError`` when the boot flag is OFF,
and this command surfaces that as a clean exit-2 with a hint.

STRICTLY ADDITIVE. No .sh / settings.json / live-hook edits.
"""
from __future__ import annotations

import os
from typing import Optional

from . import boot as boot_mod
from . import canary_cli
from . import corpus_cli


def loop(
    count: int = 5,
    *,
    brain_path: Optional[str] = None,
    role: str = "bespoq_cowork",
    base_intent: str = "Run the loop: observe, recall, think, record.",
    recall_query: Optional[str] = None,
) -> int:
    """Run ``count`` cells through ``boot_cell``, then tally corpus + canary.

    Each cell gets a distinct intent (``base_intent`` suffixed with the turn
    index) so the recorded turns are distinguishable in the flywheel. After the
    last cell, the corpus tally (``corpus_cli.corpus``) and the canary drift
    check (``canary_cli.canary``) run and print their summaries against the
    SAME brain path the cells wrote to.

    ``recall_query`` overrides the per-cell recall query (default: the cell's
    intent). Pass a keyword like ``"gateway"`` to match tagged memories, mirroring
    ``run_cli``'s ``--recall-query``.

    A cell is "alive" when its cognition was mediated by the gateway AND its
    turn was recorded to the flywheel (the loop's core contract). Recall is
    best-effort — a cell with no matching memory is still alive if it thought
    through the gateway and recorded its turn.

    Returns 0 if every cell booted and the summaries printed; 2 if the boot
    flag is off (the cells refuse to boot); 1 if any cell failed mid-loop.
    """
    if not boot_mod.boot_flag_enabled():
        print(
            f"[agent-os loop] {boot_mod.BOOT_FLAG} is OFF — cells will not boot. "
            f"Set {boot_mod.BOOT_FLAG}=1 to run inside the OS."
        )
        return 2

    if count < 1:
        print("[agent-os loop] --count must be >= 1")
        return 2

    brain_path = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")

    print(f"[agent-os loop] running {count} cell(s) against brain={brain_path}")
    alive_count = 0
    failures: list[int] = []
    for i in range(count):
        intent = f"{base_intent} (turn {i + 1}/{count})"
        cell_recall = recall_query or intent
        try:
            result = boot_mod.boot_cell(
                intent,
                recall_query=cell_recall,
                brain_path=brain_path,
                tools_used=[
                    "nucleus_wedge.recall",
                    "NucleusGateway.generate",
                    "archive_pipeline.record_turn",
                    "agent_os.loop_cli.loop",
                ],
            )
        except RuntimeError as exc:
            # boot_cell refused (flag off / scaffold failure) — surface cleanly.
            print(f"[agent-os loop] cell {i + 1} boot refused: {exc}")
            failures.append(i + 1)
            continue
        except Exception as exc:  # noqa: BLE001 — provider/record failure mid-loop
            print(f"[agent-os loop] cell {i + 1} failed: {type(exc).__name__}: {exc}")
            failures.append(i + 1)
            continue

        g = result.gateway_result
        turn_id = getattr(result.turn, "turn_id", None)
        # Alive = mediated cognition + turn recorded (the loop's core contract).
        # Recall is best-effort — a cell with no matching memory still lived
        # inside the OS if it thought through the gateway and recorded its turn.
        alive = bool(g.event_id) and bool(turn_id)
        print(
            f"  cell {i + 1}/{count}: engine={g.engine} "
            f"stubbed={g.stubbed} mediated={g.mediated} "
            f"recalled={len(result.recalled_rows)} turn_id={turn_id} alive={alive}"
        )
        if alive:
            alive_count += 1
        else:
            failures.append(i + 1)

    print(
        f"[agent-os loop] {alive_count}/{count} cell(s) alive"
        + (f"  failures={failures}" if failures else "")
    )

    # ── Corpus tally (reuses corpus_cli — no reimplementation). ──────────────
    print("\n=== CORPUS TALLY ===")
    corpus_cli.corpus(brain_path=brain_path)

    # ── Canary drift check (reuses canary_cli — no reimplementation). ────────
    print("\n=== CANARY DRIFT CHECK ===")
    canary_cli.canary(brain_path=brain_path)

    # Exit 0 if every cell was alive; 1 if any failed; 2 reserved for flag-off.
    return 0 if not failures else 1


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os loop``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os loop",
        description=(
            "Run the loop for a while: N cells through boot_cell (real inference "
            "when available, stub otherwise), then the corpus tally + canary "
            "drift check. Reuses boot_cell + corpus_cli + canary_cli."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of cells to run through boot_cell (default: 5).",
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this run.",
    )
    parser.add_argument(
        "--role",
        default="bespoq_cowork",
        help="Agent role label (default: bespoq_cowork).",
    )
    parser.add_argument(
        "--base-intent",
        default="Run the loop: observe, recall, think, record.",
        help="Base intent string (suffixed with the turn index per cell).",
    )
    parser.add_argument(
        "--recall-query",
        default=None,
        help="Override the per-cell recall query (default: the cell's intent).",
    )
    args = parser.parse_args(argv)
    return loop(
        count=args.count,
        brain_path=args.brain_path,
        role=args.role,
        base_intent=args.base_intent,
        recall_query=args.recall_query,
    )


if __name__ == "__main__":
    raise SystemExit(main())
