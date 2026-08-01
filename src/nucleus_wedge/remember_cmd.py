"""``nucleus-wedge remember`` — append one engram to .brain/engrams/history.jsonl.

Thin CLI wrapper over ``Store.append`` — the same write path the MCP ``remember``
tool uses (``server.py:38``). Added so shell hooks and cron can write engrams
without an MCP round-trip.

First caller: ``.claude/hooks/session_end_activity_digest.sh:129``, which has
been invoking ``nucleus-wedge remember`` since 2026-05-31. That subcommand never
existed — 664 hook fires produced 52 ``invalid choice: 'remember'`` errors and
**zero** successful writes over 62 days, while the hook logged ``[done]`` 45
times. This file closes the write half of that gap; the unconditional ``[done]``
is fixed separately in the hook itself.

TAGS ARE ONE COMMA-JOINED STRING here, deliberately unlike ``recall --tags``
(which is ``action="append"`` / repeatable). The hook passes a single joined
string, e.g. ``role:main,domain:tb-endpoint``. It MUST be split into a list
before reaching ``Store.append`` — ``_normalize_role`` (ADR-0033 v3 §B) matches
whole tag elements, so handing it the joined string makes it see one opaque tag
``role:cc_main,domain:x`` that matches no alias, silently skipping role
canonicalization. Do not "harmonize" this flag with recall's.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional


def do_remember(
    content: str,
    kind: str = "note",
    tags: Optional[str] = None,
    brain_path_arg: Optional[str] = None,
) -> int:
    """Append one engram. Returns a process exit code: 0 on write, 1 on failure.

    Prints the ``{key, timestamp}`` record as JSON on stdout so a shell caller
    can assert a real write happened rather than trusting the exit code alone.
    Errors go to stderr and return 1 — the caller MUST branch on this, because
    reporting success without checking is the exact defect this file exists to
    repair.
    """
    try:
        from nucleus_wedge.store import Store
    except ImportError as exc:  # pragma: no cover - import wiring
        print(f"nucleus-wedge remember: cannot import Store: {exc}", file=sys.stderr)
        return 1

    # Split the joined string into whole tag elements. Blank segments dropped so
    # a trailing comma cannot produce an empty tag.
    tag_list: Optional[list[str]] = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if not tag_list:
            tag_list = None

    try:
        store = Store(Path(brain_path_arg)) if brain_path_arg else Store()
        record = store.append(value=content, kind=kind, tags=tag_list)
    except Exception as exc:
        print(f"nucleus-wedge remember: write failed: {exc}", file=sys.stderr)
        return 1

    if not isinstance(record, dict) or "key" not in record:
        # A write that returns nothing usable is INSUFFICIENT, not success.
        print(
            f"nucleus-wedge remember: write returned no key: {record!r}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(record))
    return 0
