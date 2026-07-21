"""Agent OS — ``nucleus agent-os status``: one dashboard for the moat loop.

A compact, read-only summary combining the three signals that define the
Agent-OS moat loop:

  1. **corpus tally by verdict** — reuses ``corpus_cli.corpus`` (the same
     ``loop_turns.jsonl`` read path ``boot.record_turn_to_flywheel`` writes).
  2. **canary drift summary** — reuses ``canary_cli.canary`` (re-verifies
     CONFIRMED turns against the present; flags temporal-consequence drift).
  3. **provider lanes** — reads ``scheduler._priority_order`` +
     ``scheduler._provider_available`` to show which cognition lanes the
     membrane can schedule onto RIGHT NOW.

It is a thin orchestrator. It does NOT reimplement any of the three signals —
it calls their underlying functions directly and lets them print their own
canonical blocks (each already carries a ``#``-prefixed header). The only new
rendering is the top-level ``# agent-os status`` banner and the ``# providers``
block (scheduler has no CLI of its own).

Robust to empty / missing corpus (corpus_cli + canary_cli already handle that
cleanly) and to canary errors (wrapped so a verifier hiccup degrades to a
one-line error, not a traceback). Exits 0 always — status is informational.

STRICTLY ADDITIVE. No .sh / settings.json / live-hook edits.
"""
from __future__ import annotations

from typing import Optional

from . import canary_cli, corpus_cli, scheduler


def _print_providers() -> None:
    """Render the scheduler's provider-lane availability.

    Uses ``scheduler._priority_order(CAP_ANY)`` for the canonical priority list
    and ``scheduler._provider_available`` to check each lane's credentials
    without constructing it. The scheduler exposes no public "list available"
    function, so per the task contract we read its configured providers via
    these module-level helpers (the scheduler's own functions, not internals
    of some other module).
    """
    try:
        order = scheduler._priority_order(scheduler.CAP_ANY)
    except Exception:
        print("# providers")
        print("  (scheduler unavailable)")
        return

    available: list[str] = []
    unavailable: list[str] = []
    for provider in order:
        try:
            ok = scheduler._provider_available(provider)
        except Exception:
            ok = False
        (available if ok else unavailable).append(provider)

    print("# providers")
    if available:
        print(f"  available   : {', '.join(available)}")
    else:
        print("  available   : (none)")
    if unavailable:
        print(f"  unavailable : {', '.join(unavailable)}")


def status(
    *,
    brain_path: Optional[str] = None,
    sample: Optional[int] = None,
) -> int:
    """Print a compact Agent-OS moat-loop dashboard.

    Combines (1) corpus tally, (2) canary drift summary, (3) provider lanes.
    Each signal is produced by calling its underlying function directly —
    corpus_cli.corpus and canary_cli.canary print their own canonical blocks;
    the providers block is rendered here (scheduler has no CLI). Returns 0
    always (status is informational, not a pass/fail gate).
    """
    print("# agent-os status")
    print()

    # 1. corpus tally by verdict
    try:
        corpus_cli.corpus(brain_path=brain_path)
    except Exception as exc:  # noqa: BLE001 — degrade to a one-line error
        print(f"# verified corpus (error: {exc})")
    print()

    # 2. canary drift summary
    try:
        canary_cli.canary(brain_path=brain_path, sample=sample)
    except Exception as exc:  # noqa: BLE001 — degrade to a one-line error
        print(f"# canary (error: {exc})")
    print()

    # 3. provider lanes the scheduler considers available
    _print_providers()
    return 0


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os status``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os status",
        description=(
            "One dashboard summarizing the Agent-OS moat loop: corpus tally + "
            "canary drift + provider lanes. Read-only."
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
        help="Re-check only the first N CONFIRMED turns in the canary section "
             "(deterministic).",
    )
    args = parser.parse_args(argv)
    return status(
        brain_path=args.brain_path,
        sample=args.sample,
    )


if __name__ == "__main__":
    raise SystemExit(main())
