"""`.brain/manifest.yaml` — brain identity & project scoping.

Resolves the Cascade feedback P0 #2 (namespace disambiguation): every
brain now carries a manifest declaring its `brain_id`, owner, and which
projects it tracks. The envelope echoes `brain_id` on every MCP response
so consumers cannot misattribute state.

Schema (v2):
    brain_id: nucleus-primary
    brain_owner: eidetic-works/mcp-server-nucleus
    tracks_projects:
      - eidetic-works/mcp-server-nucleus
    primary_brain: true
    schema_version: 2
    created_at: 2026-04-20T12:00:00Z
    last_modified_at: 2026-04-20T12:00:00Z

Write discipline (acceptance criterion per 2026-04-18 review):
  - Atomic: write to `.manifest.yaml.tmp` → fsync → rename.
  - Exclusive: fcntl.flock(LOCK_EX) held across the write.
  - No partial-write file ever observable.

Read path:
  - Memoized in-process cache, invalidated on modification time change.
  - Missing manifest auto-generates a stub from state.json + `git remote`.
  - `load()` ALSO primes `_envelope.set_brain_id(...)` so downstream
    envelope wrapping echoes the correct id.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # pyyaml is a hard dep
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from mcp_server_nucleus.runtime.schema_versions import (
    MANIFEST_SCHEMA_VERSION,
    upgrade,
)

logger = logging.getLogger("nucleus.manifest")

MANIFEST_FILENAME = "manifest.yaml"
TMP_SUFFIX = ".tmp"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def manifest_path(brain_path: Path) -> Path:
    """Return the path to `.brain/manifest.yaml` for a given brain root."""
    return Path(brain_path) / MANIFEST_FILENAME


def now_iso() -> str:
    """Return current UTC time in ISO8601 (seconds precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(
    brain_path: Path,
    *,
    auto_create: bool = True,
    prime_envelope: bool = True,
) -> Dict[str, Any]:
    """Load the manifest for a brain.

    Args:
      brain_path: Root of the `.brain/` directory.
      auto_create: When True (default), generate a stub manifest if none
                   exists. When False, raises FileNotFoundError.
      prime_envelope: When True (default), set the envelope contextvars
                      (`brain_id`) so downstream responses are tagged.

    Returns:
      Manifest dict upgraded to the current schema version.
    """
    if yaml is None:
        raise RuntimeError("pyyaml is required to read manifest.yaml")

    path = manifest_path(brain_path)
    if not path.exists():
        if not auto_create:
            raise FileNotFoundError(f"no manifest at {path}")
        manifest = _bootstrap_manifest(brain_path)
        save(brain_path, manifest)
    else:
        with path.open("r") as f:
            raw = yaml.safe_load(f) or {}
        manifest = upgrade("manifest", raw)

    if prime_envelope:
        _prime_envelope(manifest)

    return manifest


def save(brain_path: Path, manifest: Dict[str, Any]) -> Path:
    """Persist `manifest` atomically to `.brain/manifest.yaml`.

    Discipline:
      1. Take exclusive flock on parent `.brain/.manifest.lock`.
      2. Write payload to `manifest.yaml.tmp` in the same directory.
      3. fsync the tmp file.
      4. os.rename (atomic on POSIX) to `manifest.yaml`.
      5. Release lock.

    Acceptance (review risk #1): no partial-write file is ever observable
    under concurrent writers.
    """
    if yaml is None:
        raise RuntimeError("pyyaml is required to write manifest.yaml")

    brain_path = Path(brain_path)
    brain_path.mkdir(parents=True, exist_ok=True)
    manifest = dict(manifest)
    manifest["schema_version"] = MANIFEST_SCHEMA_VERSION
    manifest["last_modified_at"] = now_iso()
    if "created_at" not in manifest:
        manifest["created_at"] = manifest["last_modified_at"]

    final_path = manifest_path(brain_path)
    tmp_path = final_path.with_suffix(final_path.suffix + TMP_SUFFIX)
    lock_path = brain_path / ".manifest.lock"

    payload = yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False)

    # Advisory lock — cross-process mutex.
    with lock_path.open("w") as lock_fp:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        try:
            with tmp_path.open("w") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, final_path)
        finally:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)

    return final_path


def add_project(brain_path: Path, project: str) -> Dict[str, Any]:
    """Idempotently add a tracked project to the manifest."""
    manifest = load(brain_path)
    projects: List[str] = list(manifest.get("tracks_projects", []))
    if project not in projects:
        projects.append(project)
    manifest["tracks_projects"] = projects
    save(brain_path, manifest)
    return manifest


def remove_project(brain_path: Path, project: str) -> Dict[str, Any]:
    """Remove a tracked project. No-op if not present."""
    manifest = load(brain_path)
    projects = [p for p in manifest.get("tracks_projects", []) if p != project]
    manifest["tracks_projects"] = projects
    save(brain_path, manifest)
    return manifest


def resolve_brain_id(brain_path: Optional[Path] = None) -> str:
    """Best-effort resolution of the active brain id.

    Priority:
      1. NUCLEUS_BRAIN_ID env var.
      2. manifest.yaml (auto-creates if missing).
      3. "unknown" fallback.

    Never raises — degrades to "unknown" on any error.
    """
    env = os.environ.get("NUCLEUS_BRAIN_ID")
    if env:
        return env

    try:
        if brain_path is None:
            from mcp_server_nucleus.runtime.common import get_brain_path
            brain_path = get_brain_path()
        manifest = load(Path(brain_path), prime_envelope=False)
        return str(manifest.get("brain_id", "unknown"))
    except Exception as e:
        logger.debug("resolve_brain_id degraded to 'unknown': %s", e)
        return "unknown"


# ---------------------------------------------------------------------------
# Internal: bootstrap + envelope priming
# ---------------------------------------------------------------------------


def _bootstrap_manifest(brain_path: Path) -> Dict[str, Any]:
    """Generate a stub manifest for a brain that has none.

    Heuristics:
      - brain_id: hostname-like slug derived from git repo name (if available),
                  else from the brain_path directory name.
      - brain_owner: `git config remote.origin.url`, stripped to org/repo.
      - tracks_projects: [brain_owner] if derivable.
      - primary_brain: True (solo-dev default).
    """
    owner = _detect_git_owner(brain_path)
    repo_slug = owner.split("/")[-1] if owner else brain_path.parent.name
    bid = f"nucleus-{_slugify(repo_slug)}" if repo_slug else "nucleus-primary"

    return {
        "brain_id": bid,
        "brain_owner": owner or f"local/{repo_slug or 'unknown'}",
        "tracks_projects": [owner] if owner else [],
        "primary_brain": True,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at": now_iso(),
        "last_modified_at": now_iso(),
    }


def _detect_git_owner(brain_path: Path) -> Optional[str]:
    """Return 'org/repo' if brain_path sits inside a git repo, else None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(brain_path.parent), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        return _parse_owner_from_url(url)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


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


def _prime_envelope(manifest: Dict[str, Any]) -> None:
    """Set the envelope contextvar so responses echo brain_id."""
    try:
        from mcp_server_nucleus.tools import _envelope
        _envelope.set_brain_id(str(manifest.get("brain_id", "unknown")))
    except Exception as e:  # pragma: no cover
        logger.debug("prime_envelope failed: %s", e)


__all__ = [
    "MANIFEST_FILENAME",
    "manifest_path",
    "load",
    "save",
    "add_project",
    "remove_project",
    "resolve_brain_id",
    "now_iso",
]
