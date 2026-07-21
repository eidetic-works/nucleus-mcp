"""Agent OS — ``nucleus agent-os run <prompt>``: run ONE agent INSIDE the OS.

This is a thin CLI wrapper around the existing ``boot_cell`` loop
(``runtime.agent_os.boot``). It does NOT reimplement the loop — it parses a
prompt (+ optional ``--role``) and calls ``boot_cell`` once, printing the three
proofs (mediated event / recalled memory / recorded turn) plus the model
response. If no live inference token is present, ``boot_cell`` falls back to the
deterministic stub (the mediation + recall + record stay real) — the point is
the loop runs end-to-end inside the OS.

Gated by the existing ``NUCLEUS_AGENT_OS_BOOT`` flag (default OFF). When OFF,
``boot_cell`` raises ``RuntimeError`` and this command surfaces it as a clean
exit-2 with a hint, rather than a traceback.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from . import boot as boot_mod


def run(
    prompt: str,
    *,
    role: str = "bespoq_cowork",
    brain_path: Optional[str] = None,
    recall_query: Optional[str] = None,
) -> int:
    """Run one cell inside the Agent OS and print the three proofs.

    Returns an exit code: 0 on a live cell, 2 if the boot flag is off.
    """
    if not boot_mod.boot_flag_enabled():
        print(
            f"[agent-os run] {boot_mod.BOOT_FLAG} is OFF — the cell will not boot. "
            f"Set {boot_mod.BOOT_FLAG}=1 to run inside the OS."
        )
        return 2

    brain_path = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")
    intent = prompt.strip()
    if not intent:
        print("[agent-os run] empty prompt — nothing to run.")
        return 2

    # Reuse the existing loop. The agent_id carries the role label so the
    # mediated event + flywheel turn are attributable to this run.
    agent_id = f"agent-os-run:{role}"
    try:
        result = boot_mod.boot_cell(
            intent,
            recall_query=recall_query or intent,
            brain_path=brain_path,
            tools_used=[
                "nucleus_wedge.recall",
                "NucleusGateway.generate",
                "archive_pipeline.record_turn",
                "agent_os.run_cli.run",
            ],
        )
    except RuntimeError as exc:
        # boot_cell refused (flag off / scaffold failure) — surface cleanly.
        print(f"[agent-os run] boot refused: {exc}")
        return 2

    g = result.gateway_result

    # ── PROOF 1 — cognition mediated by the Nucleus gateway ───────────────
    print("\n=== PROOF 1 — cognition MEDIATED by the Nucleus gateway ===")
    print(f"  engine        : {g.engine}   (stubbed_provider_call={g.stubbed})")
    print(f"  model         : {g.model}")
    print(f"  mediated      : {g.mediated}  (Nucleus emitted LLM_GENERATE)")
    print(f"  LLM_GENERATE  : {g.event_id}")
    print(f"  note          : {g.note}")

    # ── PROOF 2 — real recalled memory injected before thinking ───────────
    print("\n=== PROOF 2 — recalled MEMORY injected before thinking ===")
    print(f"  recalled_from_memory: {result.recalled_from_memory} "
          f"({len(result.recalled_rows)} row(s))")
    for ln in result.injected_context.splitlines():
        print(f"    {ln}")

    # ── PROOF 3 — the turn was recorded to the flywheel ───────────────────
    print("\n=== PROOF 3 — turn RECORDED to the flywheel (LoopTurn) ===")
    turn = result.turn
    turn_id = getattr(turn, "turn_id", None)
    print(f"  turn_id       : {turn_id}")
    print(f"  intent        : {result.intent}")
    meta = getattr(turn, "metadata", None) or {}
    if isinstance(meta, dict):
        print(f"  metadata      : {json.dumps(meta, ensure_ascii=False)}")

    # ── Model response (the agent's actual output, stub or real) ──────────
    print("\n=== MODEL RESPONSE (inside the membrane) ===")
    print(g.text or "<empty response>")

    alive = bool(g.event_id) and result.recalled_from_memory and bool(turn_id)
    print(f"\n[agent-os run] cell alive (3 proofs fired): {alive}")
    return 0 if alive else 1


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os run``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os run",
        description="Run ONE agent INSIDE the Agent OS (reuses boot_cell).",
    )
    parser.add_argument("prompt", help="The intent / task prompt for the agent.")
    parser.add_argument(
        "--role",
        default="bespoq_cowork",
        help="Agent role label (default: bespoq_cowork).",
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this run.",
    )
    parser.add_argument(
        "--recall-query",
        default=None,
        help="Override the recall query (default: the prompt itself).",
    )
    args = parser.parse_args(argv)
    return run(
        args.prompt,
        role=args.role,
        brain_path=args.brain_path,
        recall_query=args.recall_query,
    )


if __name__ == "__main__":
    raise SystemExit(main())
