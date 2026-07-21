"""Isolation — ensures each project's brain is fully isolated.

Key principle: no cross-project contamination. Each lane gets:
    - Its own .brain/ directory (NUCLEUS_BRAIN_PATH)
    - Its own nucleus.db (SQLite)
    - Its own relay/ directory
    - Its own state/ and logs/ directories

The isolation guard verifies that the brain path is NOT the nucleus team's
own brain, preventing accidental contamination of the reference implementation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from .config import LaneConfig


# The nucleus team's own brain path — must never be used by other projects.
# Resolved from env var to avoid hardcoding personal paths.
NUCLEUS_TEAM_BRAIN = Path(os.environ.get("NUCLEUS_TEAM_BRAIN_PATH", "")).resolve() if os.environ.get("NUCLEUS_TEAM_BRAIN_PATH") else None
NUCLEUS_TEAM_REPO = Path(os.environ.get("NUCLEUS_TEAM_REPO_PATH", "")).resolve() if os.environ.get("NUCLEUS_TEAM_REPO_PATH") else None


class IsolationError(Exception):
    """Raised when isolation would be violated."""


def isolate_brain(
    repo_root: Path,
    brain_path: Optional[Path] = None,
    force: bool = False,
) -> Path:
    """Set up an isolated brain directory for a project.

    Args:
        repo_root: Path to the project's git repository root.
        brain_path: Override for the brain path (default: repo_root / ".brain").
        force: Skip the nucleus-team-brain guard (for testing only).

    Returns:
        The resolved brain path.

    Raises:
        IsolationError: If the brain path would contaminate the nucleus team's brain.
    """
    repo_root = Path(repo_root).resolve()
    brain = Path(brain_path) if brain_path else repo_root / ".brain"
    brain = brain.resolve()

    # Guard: never use the nucleus team's brain
    if not force and NUCLEUS_TEAM_BRAIN and brain == NUCLEUS_TEAM_BRAIN:
        raise IsolationError(
            f"Refusing to use nucleus team's brain path: {brain}. "
            "Each project must have its own .brain/ directory."
        )

    # Guard: brain must be inside the project repo (or explicitly overridden)
    if not force and brain_path is None:
        if not str(brain).startswith(str(repo_root)):
            raise IsolationError(
                f"Brain path {brain} is outside repo root {repo_root}. "
                "Set brain_path explicitly if this is intentional."
            )

    # Create the brain directory structure
    for subdir in ["state", "logs", "relay", "plans", "engrams"]:
        (brain / subdir).mkdir(parents=True, exist_ok=True)

    # Set the env var so nucleus runtime picks it up
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)

    return brain


def validate_isolation(config: LaneConfig) -> dict:
    """Validate that a lane config is properly isolated.

    Returns a dict with validation results.
    """
    issues = []

    # Check brain path is not the nucleus team's brain
    if NUCLEUS_TEAM_BRAIN and config.brain_path.resolve() == NUCLEUS_TEAM_BRAIN:
        issues.append("brain_path is the nucleus team's brain — contamination risk")

    # Check brain path exists and has the right structure
    for subdir in ["state", "logs", "relay"]:
        p = config.brain_path / subdir
        if not p.exists():
            issues.append(f"missing brain subdirectory: {p}")

    # Check repo root is a git repo
    git_dir = config.repo_root / ".git"
    if not git_dir.exists():
        issues.append(f"repo_root is not a git repo: {config.repo_root}")

    # Check spec exists
    if not config.spec_path.exists():
        issues.append(f"spec file not found: {config.spec_path}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "brain_path": str(config.brain_path),
        "repo_root": str(config.repo_root),
    }
