"""Locate scripts that live in a sibling repo.

Some deployments keep companion scripts in a repo next to this one while nucleus jobs still
drive them by path. Those call sites used to do ``PROJECT_ROOT / "scripts" / name``, which now silently resolves
to a path that does not exist, so the job fails with a message pointing at the wrong repo.

``find_script`` searches this repo first, then any configured sibling repos, and
``require_script`` raises one clear error naming everywhere it looked.

Configure siblings with ``NUCLEUS_SIBLING_REPOS`` (os.pathsep-separated) or one path per line
in ``$XDG_CONFIG_HOME/nucleus/siblings``. Nothing is assumed about the machine: with no
configuration this searches only the repo it ships in.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

CONFIG_PATH = Path(
    os.environ.get("NUCLEUS_CONFIG_HOME")
    or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "nucleus"
) / "siblings"


def _configured_roots() -> list[Path]:
    """Sibling repos from the environment, else from the config file, else none.

    There are no built-in defaults on purpose: which repos sit next to this one is a
    property of an installation, not of the software. A deployment that needs them sets
    NUCLEUS_SIBLING_REPOS (os.pathsep-separated) or writes one path per line to
    ``$XDG_CONFIG_HOME/nucleus/siblings``.
    """
    env = os.environ.get("NUCLEUS_SIBLING_REPOS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    if CONFIG_PATH.exists():
        return [
            Path(line.strip()).expanduser()
            for line in CONFIG_PATH.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    return []


def search_roots() -> list[Path]:
    """Repos to look in, in order. This repo always comes first."""
    return [PROJECT_ROOT, *_configured_roots()]


def find_script(relative: str) -> Path | None:
    """Return the first existing ``<root>/<relative>``, or None."""
    for root in search_roots():
        candidate = root / relative
        if candidate.exists():
            return candidate
    return None


def require_script(relative: str) -> Path:
    """Like find_script, but raise FileNotFoundError naming every place searched."""
    found = find_script(relative)
    if found is not None:
        return found
    looked = ", ".join(str(r / relative) for r in search_roots())
    raise FileNotFoundError(
        f"{relative} not found. It moved to a sibling repo in the 2026-09-17 split. "
        f"Looked in: {looked}. Set NUCLEUS_SIBLING_REPOS to point at the repo that has it."
    )
