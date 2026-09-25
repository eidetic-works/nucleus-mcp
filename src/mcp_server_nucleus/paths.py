"""Nucleus path resolution — env-driven, zero user-hardcodes.

Every substrate path in shipped code must resolve through one of these helpers.
Env wins; dev-compat fallback is the invoking user's home. Strict mode raises
rather than falling back silently — for entry points where misconfiguration
should fail loud (unit tests, install verification).

Env contract:
- ``NUCLEUS_ROOT``        — repo root (git working tree). Fallback: ~/ai-mvp-backend
- ``NUCLEUS_BRAIN``       — brain dir. Fallback: ``<NUCLEUS_ROOT>/.brain``
- ``NUCLEUS_TRANSCRIPT_ROOT`` — peer transcript source (Cowork / any adapter).
  No generic fallback — adapter-specific defaults live alongside the adapter.
"""

from __future__ import annotations

import os
from pathlib import Path


class NucleusPathError(RuntimeError):
    """Raised when a required Nucleus env var is missing in strict mode."""


def _env_path(key: str) -> Path | None:
    val = os.environ.get(key)
    return Path(val) if val else None


def _discover_root(start: Path | None = None) -> Path | None:
    """Nearest ancestor of `start` (default: cwd) that holds a .brain directory."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".brain").is_dir():
            return candidate
    return None


def nucleus_root(strict: bool = False) -> Path:
    """Repo root: NUCLEUS_ROOT, else the nearest ancestor holding .brain, else cwd.

    There is no hard-coded fallback directory — where nucleus is installed is a property of
    the installation, not of the package.
    """
    env = _env_path("NUCLEUS_ROOT")
    if env is not None:
        return env
    discovered = _discover_root()
    if discovered is not None:
        return discovered
    if strict:
        raise NucleusPathError(
            "NUCLEUS_ROOT is not set and no .brain directory was found in the current "
            "directory or its parents. Export NUCLEUS_ROOT to the repo root, or run "
            "`nucleus init` to create one here."
        )
    return Path.cwd()


def brain_path(strict: bool = False) -> Path:
    env = _env_path("NUCLEUS_BRAIN")
    if env is not None:
        return env
    if strict:
        raise NucleusPathError(
            "NUCLEUS_BRAIN is not set. Export NUCLEUS_BRAIN=<repo>/.brain "
            "or NUCLEUS_ROOT and let the default take over."
        )
    return nucleus_root(strict=False) / ".brain"


def transcript_root(strict: bool = False) -> Path | None:
    env = _env_path("NUCLEUS_TRANSCRIPT_ROOT")
    if env is not None:
        return env
    if strict:
        raise NucleusPathError(
            "NUCLEUS_TRANSCRIPT_ROOT is not set. Point it at the peer agent's "
            "transcript tree (e.g. Cowork's local-agent-mode-sessions)."
        )
    return None
