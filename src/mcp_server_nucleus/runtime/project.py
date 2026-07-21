"""
Nucleus Runtime - Project Detection (ADR-0042 "Project Spine", D2)
==================================================================

Pure filesystem/git project detection. No tool-, OS-, or agent-specific
assumptions (portability gate). Detection resolves a *project slug* and the
*brain root* (the directory that owns ``.brain/``) from a working directory.

Slug precedence (D2):
    1. ``.nucleus-project`` marker file  (explicit override — wins, even
       inside a git repo)
    2. git-remote-derived slug           (URL parser + slugifier below)
    3. directory-name fallback

This module is flag-gated at the consumer (``get_brain_path`` under
``NUCLEUS_PROJECT_SPINE``); the detector itself is side-effect-free and safe
to call unconditionally. ``common.py`` imports it *lazily* (inside the
function body) to avoid an import cycle.

Public entrypoint: ``resolve_project(cwd) -> ProjectInfo | None``. Named
``resolve_project`` (not ``detect_project``) to avoid colliding with the
differently-typed ``detect_project`` in ``runtime/onboarding.py`` (``-> dict``,
for ``nucleus init`` UX) — a distinct symbol in a distinct module.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Slug helpers (moved here from runtime.manifest — ADR-0043 boundary ruling)
# ---------------------------------------------------------------------------
# ``runtime.project`` is a CORE module and must stay self-contained
# (stdlib + subprocess only, per ADR-0042 D2's pure-filesystem/git
# requirement): an eager core->periphery import is forbidden by the
# boundary checker. The git-remote -> slug derivation therefore lives
# here, and ``runtime.manifest`` (periphery) imports it from this module
# — the allowed dependency direction.


def _parse_owner_from_url(url: str) -> Optional[str]:
    """Extract 'org/repo' from common git URL shapes."""
    if not url:
        return None
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    # git@host:org/repo
    if url.startswith("git@"):
        _, _, tail = url.partition(":")
        return tail or None
    # https://host/org/repo or ssh://git@host/org/repo
    for scheme in ("https://", "http://", "ssh://"):
        if url.startswith(scheme):
            parts = url[len(scheme):].split("/", 2)
            if len(parts) == 3:
                return f"{parts[1]}/{parts[2]}"
            return None
    return None


def _slugify(text: str) -> str:
    out = []
    prev_dash = False
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


# ---------------------------------------------------------------------------
# Project identity
# ---------------------------------------------------------------------------
# Root detection is deliberately narrow: an explicit ``.nucleus-project``
# marker or the git toplevel — NOT ``pyproject.toml`` / ``package.json``. A
# per-language manifest is not a project-root signal: in a monorepo a
# ``frontend/package.json`` subdir would be picked as the root, pairing the
# OUTER repo's git-remote slug (git config climbs to the enclosing repo) with
# the SUBDIR's ``.brain`` root. The slug and the brain_root must derive from the
# SAME root, so the only roots are an explicit marker or the git toplevel.
_MARKER = ".nucleus-project"


@dataclass(frozen=True)
class ProjectInfo:
    """Result of project detection.

    Attributes:
        slug:       project slug (slugified, non-empty).
        brain_root: the ``.brain`` directory that this project owns
                    (``<project_root>/.brain``). Not guaranteed to exist —
                    callers that need a real brain check ``brain_root.exists()``.
        source:     which arm resolved the slug: ``"marker" | "git-remote" | "dirname"``.
    """

    slug: str
    brain_root: Path
    source: str


def _marker_root(start: Path) -> Optional[Path]:
    """Nearest ancestor of ``start`` (inclusive) carrying a ``.nucleus-project``.

    The marker is an explicit override and wins even inside a git repo, so it
    is searched first and independently of the git toplevel. The marker *file*
    presence is the signal; its content is a slug hint resolved later.
    """
    for d in [start, *start.parents]:
        if (d / _MARKER).exists():
            return d
    return None


def _git_toplevel(start: Path) -> Optional[Path]:
    """Git toplevel containing ``start`` via ``git rev-parse --show-toplevel``.

    Returns None when git is unavailable or ``start`` is not inside a work tree
    (git-missing / non-repo tolerated). Detection then declines and the env var
    stays authoritative — ADR-0042 D1: "env remains authoritative when no
    project is detectable".
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    top = result.stdout.strip()
    return Path(top) if top else None


def _find_project_root(start: Path) -> Optional[Path]:
    """Resolve the project root owning ``start`` (marker, else git toplevel).

    Precedence:
        1. Nearest ancestor with a ``.nucleus-project`` marker (explicit
           override — wins even inside a git repo).
        2. The git toplevel containing ``start``.
        3. Neither → None. Detection declines; the env var stays authoritative.

    ``pyproject.toml`` / ``package.json`` are intentionally *not* signals — see
    the module-level ``_MARKER`` note (monorepo slug/brain-root mismatch). This
    is what guarantees the slug and brain_root share one root.
    """
    marker_root = _marker_root(start)
    if marker_root is not None:
        return marker_root
    return _git_toplevel(start)


def _marker_slug(root: Path) -> Optional[str]:
    """Read the first non-empty line of the marker file as an explicit slug.

    Returns None when the marker is absent, unreadable, empty, or contains
    only content that slugifies away (invalid content → fall through, not
    crash).
    """
    marker = root / _MARKER
    if not marker.is_file():
        return None
    try:
        text = marker.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        slug = _slugify(line)
        return slug or None
    return None


def _git_remote_slug(root: Path) -> Optional[str]:
    """Derive a slug from ``remote.origin.url`` at ``root`` (repo-name arm).

    Uses the module-local URL parser + slugifier. Returns None when
    ``root`` is not a git repo, has no origin remote, or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    owner = _parse_owner_from_url(result.stdout.strip())
    if not owner:
        return None
    slug = _slugify(owner.split("/")[-1])
    return slug or None


def resolve_project(cwd: Optional[Path] = None) -> Optional[ProjectInfo]:
    """Detect the project owning ``cwd`` — pure filesystem/git, no side effects.

    Resolution:
        1. Find the project root: nearest ``.nucleus-project`` marker ancestor,
           else the git toplevel. None → return None (no project context;
           caller falls through).
        2. Resolve the slug in precedence order: marker → git-remote → dirname.
        3. ``brain_root = root / ".brain"``.

    Returns None when no project root is found. The returned ``brain_root``
    may or may not exist on disk; the D1 consumer only diverges from the env
    var when a real project brain is present.
    """
    start = (cwd or Path.cwd()).resolve()

    root = _find_project_root(start)
    if root is None:
        return None

    slug = _marker_slug(root)
    source = "marker"
    if slug is None:
        slug = _git_remote_slug(root)
        source = "git-remote"
    if slug is None:
        slug = _slugify(root.name)
        source = "dirname"
    if not slug:
        # Even the dirname slugified away (e.g. root is "/" with an unusual
        # name). No usable identity → decline rather than emit an empty slug.
        return None

    return ProjectInfo(slug=slug, brain_root=root / ".brain", source=source)
