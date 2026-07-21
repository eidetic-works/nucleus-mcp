"""Agent OS — ``nucleus agent-os demo [prompt]``: Show the value of Agent OS by running naked vs inside.

Runs a prompt two ways:
1. NAKED: A bare model turn with no memory recall, no mediation event, and no loop turn recorded.
2. INSIDE: Run through boot_cell, which recalls + injects memory, mediates cognition, and records a loop turn.
"""
from __future__ import annotations

import os
from typing import Optional

from . import boot as boot_mod

DEFAULT_DEMO_PROMPT = "How should this agent route its model calls — inside Nucleus or out?"

def run_demo(
    prompt: Optional[str] = None,
    *,
    brain_path: Optional[str] = None,
) -> int:
    """Run a prompt naked vs inside the Agent OS and print the differences."""
    if not boot_mod.boot_flag_enabled():
        print(
            f"[agent-os demo] {boot_mod.BOOT_FLAG} is OFF — the cell will not boot. "
            f"Set {boot_mod.BOOT_FLAG}=1 to run inside the OS."
        )
        return 2

    intent = (prompt or DEFAULT_DEMO_PROMPT).strip()
    brain_path = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")

    # 1. NAKED (no OS) path
    # Simulate a bare model turn: try real provider if stub not forced, else stub
    # Note: we do NOT call boot_cell here. We do not inject system prompts or memories.
    client = None
    naked_text = None
    if not boot_mod._stub_forced():
        try:
            from ..llm_client import get_llm_client
            client = get_llm_client()
        except Exception:
            pass

    if client is not None:
        try:
            resp = client.generate_content(intent)
            naked_text = getattr(resp, "text", "") or ""
        except Exception:
            client = None

    if client is None:
        # Deterministic offline stub response for naked (no gateway mediation note, no memory)
        # Standard offline stub response but naked. Let's make it look like a bare model response.
        naked_text = f"No prior memory was injected for this task. Plan for '{intent}': proceed. MISSION_COMPLETE"

    # 2. INSIDE NUCLEUS path
    # Resolve the recall query to a keyword to help the database substring search succeed
    # on the seeded brain memory.
    recall_q = intent
    for kw in ["gateway", "route", "model", "inside"]:
        if kw in intent.lower():
            recall_q = kw
            break

    # Calls boot_cell which handles memory injection, gateway mediation, and flywheel recording
    try:
        result = boot_mod.boot_cell(
            intent,
            recall_query=recall_q,
            brain_path=brain_path,
            tools_used=[
                "nucleus_wedge.recall",
                "NucleusGateway.generate",
                "archive_pipeline.record_turn",
                "agent_os.demo_cli.run_demo",
            ],
        )
    except RuntimeError as exc:
        print(f"[agent-os demo] boot refused: {exc}")
        return 2

    # 3. Print comparison blocks
    print("## NAKED (no OS) — recalled: none | mediated: no | recorded: no")
    print(naked_text)
    print()

    # INSIDE NUCLEUS dynamic stats
    recalled_str = "none"
    n_rows = len(result.recalled_rows)
    if result.recalled_from_memory and n_rows > 0:
        recalled_str = f"{n_rows} rows (selective)"

    mediated_str = "no"
    if result.gateway_result.mediated and result.gateway_result.event_id:
        mediated_str = "yes (LLM_GENERATE event)"

    recorded_str = "no"
    turn_id = getattr(result.turn, "turn_id", None)
    if turn_id:
        recorded_str = "yes (LoopTurn)"

    print(f"## INSIDE NUCLEUS — recalled: {recalled_str} | mediated: {mediated_str} | recorded: {recorded_str}")
    print(result.gateway_result.text)
    print()

    # THE DELTA dynamic stats
    delta_actions = []
    if result.recalled_from_memory:
        delta_actions.append("recalled the right context")
    if result.gateway_result.mediated:
        delta_actions.append("mediated the call")
    if turn_id:
        delta_actions.append("recorded the turn")

    delta_str = ", ".join(delta_actions) if delta_actions else "none"
    print(f"## THE DELTA: {delta_str}")

    return 0

def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os demo``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os demo",
        description="Run a prompt naked vs inside Agent OS to show the delta.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="The prompt/intent for comparison (optional).",
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this demo.",
    )
    args = parser.parse_args(argv)
    return run_demo(args.prompt, brain_path=args.brain_path)

if __name__ == "__main__":
    import sys
    sys.exit(main())
