"""``nucleus init`` implementation per ``week2_init_flow_spec.md`` §3a.

Steps (all idempotent):
1. Resolve brain path via ``Store.brain_path()`` (flag → env → cwd .brain → cwd .git → abort).
2. Create ``engrams/``, ``plans/``, ``relay/``, ``metrics/`` under brain.
3. Touch ``engrams/history.jsonl``.
4. Seed three defaults via ``ensure_seeds`` (skipped on ``--seeds none``).
5. Append missing ``.gitignore`` lines (project root = brain.parent).
6. Write ``AGENTS.md`` stub if absent (or with ``--force``).
7. Print summary.
"""
from __future__ import annotations

import sys
from pathlib import Path

from nucleus_wedge.seed import SEED_KEYS, ensure_seeds
from nucleus_wedge.store import Store

GITIGNORE_LINES: tuple[str, ...] = (
    "HANDOFF*.md",
    ".brain/relay/",
    ".brain/metrics/",
    ".brain/issues/",
    ".brain/session_mirror/",
)

SUBDIRS: tuple[str, ...] = ("engrams", "plans", "relay", "metrics")

AGENTS_STUB = """# AGENTS.md

This project uses Nucleus wedge for persistent agent memory (`remember` / `recall` MCP tools).

- Run `nucleus mcp register --client claude-code` once to wire the MCP server.
- HANDOFF.md is sovereign per ADR-0003 — gitignored, written by your CC session, not by `nucleus init`.
- On a fresh clone, HANDOFF.md will be absent. This is expected. Run a single CC session to seed it; cross-machine HANDOFF sync is out of cycle-1 scope.

See https://nucleusos.dev for full docs.
"""


def _ensure_subdirs(brain: Path) -> None:
    for sub in SUBDIRS:
        (brain / sub).mkdir(parents=True, exist_ok=True)


def _ensure_gitignore(brain: Path) -> None:
    project_root = brain.parent
    gitignore = project_root / ".gitignore"
    existing_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    existing_lines = {line.strip() for line in existing_text.splitlines()}
    missing = [line for line in GITIGNORE_LINES if line not in existing_lines]
    if not missing:
        return
    prefix = "" if not existing_text or existing_text.endswith("\n") else "\n"
    body = prefix + "\n".join(missing) + "\n"
    with gitignore.open("a", encoding="utf-8") as fh:
        fh.write(body)


def _ensure_agents(brain: Path, force: bool) -> None:
    project_root = brain.parent
    agents = project_root / "AGENTS.md"
    if agents.exists() and not force:
        return
    agents.write_text(AGENTS_STUB, encoding="utf-8")


def do_init(brain_path_arg: str | None, seeds_mode: str, force: bool) -> int:
    """Execute ``nucleus init``. Returns process exit code (0 success, 1 abort)."""
    try:
        brain = Store.brain_path(brain_path_arg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    history = brain / "engrams" / "history.jsonl"
    history_existed = history.exists()

    _ensure_subdirs(brain)
    history.touch(exist_ok=True)

    if seeds_mode == "none":
        seeds_status = "0 (--seeds none)"
    else:
        store = Store(brain_path=brain)
        written = ensure_seeds(store)
        # An empty ``written`` has two causes and they are not the same news:
        # every seed was already in the store, or the file the seeds are copied
        # FROM does not exist so there was nothing to copy. ``ensure_seeds``
        # ``continue``s past a missing entry silently, collapsing both to [].
        # Reporting "already present" for the second is a success line printed
        # over an empty brain, on the first command a new user runs.
        seed_source = brain / "memory" / "engrams.json"
        missing = [k for k in SEED_KEYS if k not in store.keys_present()]
        if written and len(written) == len(SEED_KEYS):
            seeds_status = f"{len(SEED_KEYS)} added"
        elif written:
            seeds_status = (
                f"{len(written)} added, {len(missing)} unavailable "
                f"(not in seed source {seed_source})"
            )
        elif missing:
            seeds_status = (
                f"0 added — seed source absent ({seed_source}); "
                f"{len(missing)} seeds unavailable, brain is empty"
            )
        else:
            seeds_status = f"{len(SEED_KEYS)} skipped (already present)"

    _ensure_gitignore(brain)
    _ensure_agents(brain, force=force)

    print(f"brain_path: {brain}")
    print(f"engrams: {'existing' if history_existed else 'created'}")
    print(f"seeds: {seeds_status}")
    print("next_step: nucleus mcp register --client claude-code")
    return 0
