"""Agent OS — ``nucleus agent-os recall <query>``: selective memory-continuity.

The primitive a SessionStart hook will call to auto-load the RIGHT prior context
for a new session. It recalls candidate rows from the SAME real-brain recall
path ``boot_cell`` / ``recall_and_inject`` uses (``nucleus_wedge.recall_cmd.
_do_recall_query`` over ``memories.db``), then — when ``NUCLEUS_AGENT_OS_PAGER``
is ON — runs the working-set pager (``runtime.agent_os.pager.page``) to select
the slice that fits a context budget, scored relevance × recency ×
verified-trust. When the flag is OFF, the raw recalled rows are returned
unchanged (plain unselective fallback — byte-identical to today's recall).

This is a thin CLI wrapper. It does NOT reimplement brain access — it reuses
``_do_recall_query`` (the helper ``recall_and_inject`` calls) and ``page``
(the Stage-1 pager) directly. ``boot.py`` is not modified; its runtime behavior
is byte-identical.

The printed stdout block is exactly what a SessionStart hook would inject:

    # selective recall (<n> rows, <budget> chars)
    - [0] <first 120 chars of row 0 text>
    - [1] <first 120 chars of row 1 text>
    ...

STRICTLY ADDITIVE, flag-gated, default-OFF selection. No .sh / settings.json /
live-hook edits.
"""
from __future__ import annotations

import os
from typing import Optional

from . import boot as boot_mod


def recall(
    query: str,
    *,
    budget: int = 2000,
    limit: Optional[int] = None,
    brain_path: Optional[str] = None,
    kind: Optional[str] = None,
    tags: Optional[list] = None,
    recall_limit: int = 5,
    list_rows: bool = False,
) -> int:
    """Recall prior context for a query and print a clean injectable block.

    Reuses the same real-brain recall path as ``boot.recall_and_inject``
    (``_do_recall_query``). When ``NUCLEUS_AGENT_OS_PAGER`` is truthy, the
    recalled candidates are run through ``pager.page`` (scored relevance ×
    recency × verified-trust, packed best-first into ``budget`` chars); else
    the raw recalled rows are emitted unchanged (plain unselective fallback).

    When ``list_rows`` is True, the same data path runs but the output is a
    clean listing of the rows the pager WOULD select — no inference, no
    injectable-block header. Useful for inspecting what recall would surface
    for a query without injecting it.

    Returns 0 on success, 2 on empty query.
    """
    q = (query or "").strip()
    if not q:
        print("[agent-os recall] empty query — nothing to recall.")
        return 2

    brain_path = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")

    # Same real-brain recall path boot.recall_and_inject uses — reuse the helper,
    # do NOT reimplement brain access.
    from nucleus_wedge.recall_cmd import _do_recall_query

    rows = _do_recall_query(
        query=q,
        limit=recall_limit,
        kind=kind,
        tags=tags,
        since=None,
        source_filter=None,
        brain_path_arg=str(brain_path) if brain_path else None,
    )

    # Stage-1 pager: reselect the working set from the raw recall candidates.
    # Flag-OFF = plain unselective fallback: the pager module is NOT imported
    # and the raw recall rows are emitted unchanged (byte-identical to today's
    # recall). Only the flag-ON branch imports ``page`` lazily and reselects.
    if os.environ.get(boot_mod.PAGER_FLAG, "").strip().lower() in boot_mod._TRUTHY:
        from .pager import page

        rows = page(q, rows, budget_chars=budget, limit=limit)

    # Render the output. ``--list`` emits a clean listing of the rows the
    # pager WOULD select (same data path, no inference, no injectable header);
    # the default emits the injectable block a SessionStart hook can inject.
    n = len(rows)
    if list_rows:
        print(f"# recall list ({n} rows)")
        for idx, r in enumerate(rows):
            text = str(r.get("text") or "")
            print(f"- [{idx}] {text[:120]}")
        return 0
    print(f"# selective recall ({n} rows, {budget} chars)")
    for idx, r in enumerate(rows):
        text = str(r.get("text") or "")
        print(f"- [{idx}] {text[:120]}")
    return 0


def main(argv: Optional[list] = None) -> int:
    """Argparse entrypoint for ``nucleus agent-os recall``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nucleus agent-os recall",
        description=(
            "Recall prior context for a query (selective memory-continuity). "
            "Prints a block a SessionStart hook can inject."
        ),
    )
    parser.add_argument("query", help="The recall query (what context to load).")
    parser.add_argument(
        "--budget",
        type=int,
        default=2000,
        help="Context budget in chars for the pager selection (default: 2000).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Hard cap on the number of returned rows (default: none).",
    )
    parser.add_argument(
        "--brain-path",
        default=None,
        help="Override NUCLEUS_BRAIN_PATH for this recall.",
    )
    parser.add_argument(
        "--recall-limit",
        type=int,
        default=5,
        help="How many candidate rows to pull from the brain (default: 5).",
    )
    parser.add_argument(
        "--list",
        dest="list_rows",
        action="store_true",
        default=False,
        help=(
            "List the rows the pager WOULD select for the query (same data "
            "path, no inference, no injectable-block header) instead of "
            "emitting the injectable block."
        ),
    )
    args = parser.parse_args(argv)
    return recall(
        args.query,
        budget=args.budget,
        limit=args.limit,
        brain_path=args.brain_path,
        recall_limit=args.recall_limit,
        list_rows=args.list_rows,
    )


if __name__ == "__main__":
    raise SystemExit(main())
