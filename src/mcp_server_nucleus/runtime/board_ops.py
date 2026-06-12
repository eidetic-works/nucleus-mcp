"""Common Problem Board — runtime ops.

Implements the post/claim/resolve lifecycle for `.brain/relay/board/`.

See `.brain/relay/board/README.md` for the bucket convention, schema, and
lifecycle. This module provides the load-bearing primitives the facade tool
(`tools/board.py`) routes to.

Design invariants:

- Mandatory tagging: every post must carry at least one tag starting with
  `tribal-knowledge:` OR equal to `priority:blocker`.
- Atomic claim: `_claims/<board_id>.claimed` directory is created with
  `Path.mkdir(exist_ok=False)`; first writer wins on POSIX.
- Re-activation trigger: a new post in tag `tribal-knowledge:X` surfaces the
  most recent archived posts with the same tag (see `feedback_dont_let_work_go_waste`).
- TTL is activity-gated: archival runs on the next mutating call that touches
  the bucket, not on a cron.
- Activity-memory bridge: if `nucleus_wedge.memories.nucleus_wedge__recall_activity`
  exists at call time, `claim` returns recalls; on `resolve`, an activity engram
  is auto-written. Both degrade silently when the symbol is absent.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import get_brain_path

# ── Constants ─────────────────────────────────────────────────────

BOARD_DIRNAME = "board"
ARCHIVE_DIRNAME = "_archive"
CLAIMS_DIRNAME = "_claims"

TTL_OPEN_DAYS = 7
TTL_RESOLVED_DAYS = 30

_TAG_TRIBAL_PREFIX = "tribal-knowledge:"
_TAG_PRIORITY_BLOCKER = "priority:blocker"

_SUBJECT_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")
_MAX_SUBJECT_SLUG = 40

_VALID_PRIORITIES = {"low", "normal", "high", "blocker"}
_VALID_STATUSES = {"open", "claimed", "resolved"}


# ── Path helpers ──────────────────────────────────────────────────


def _board_root(brain_path: Optional[Path] = None) -> Path:
    base = brain_path or get_brain_path()
    return base / "relay" / BOARD_DIRNAME


def _archive_root(brain_path: Optional[Path] = None) -> Path:
    return _board_root(brain_path) / ARCHIVE_DIRNAME


def _claims_root(brain_path: Optional[Path] = None) -> Path:
    return _board_root(brain_path) / CLAIMS_DIRNAME


def _ensure_dirs(brain_path: Optional[Path] = None) -> None:
    for p in (_board_root(brain_path), _archive_root(brain_path), _claims_root(brain_path)):
        p.mkdir(parents=True, exist_ok=True)


# ── Time / id helpers ─────────────────────────────────────────────


def _iso_ts_compact(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _iso_ts_full(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    s = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _new_board_id(ts_compact: str) -> str:
    rand = secrets.token_hex(4)
    return f"board_{ts_compact}_{rand}"


# ── Sanitization / validation ─────────────────────────────────────


def _sanitize_subject(subject: str) -> str:
    s = (subject or "untitled").strip().lower()
    s = _SUBJECT_SANITIZE_RE.sub("-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "untitled"
    return s[:_MAX_SUBJECT_SLUG]


def _resolve_role(arg: Optional[str], default: str = "main") -> str:
    if arg:
        return arg
    env = os.environ.get("CC_SESSION_ROLE", "").strip()
    return env or default


def _validate_tags(tags: List[str]) -> None:
    if not tags:
        raise ValueError(
            "board post requires at least one tag starting with "
            "'tribal-knowledge:' or equal to 'priority:blocker' "
            "(per .brain/relay/board/README.md mandatory tagging rule)"
        )
    if not any(t.startswith(_TAG_TRIBAL_PREFIX) or t == _TAG_PRIORITY_BLOCKER for t in tags):
        raise ValueError(
            "board post tag list must contain at least one 'tribal-knowledge:<domain>' "
            "tag OR the 'priority:blocker' tag. Got: "
            f"{tags!r}. Without this the watch-relay filter degrades to "
            "deliver-everything-to-everyone."
        )


def _extract_domain(tags: List[str]) -> Optional[str]:
    """Return the first tribal-knowledge:<domain> domain string, if any."""
    for t in tags:
        if t.startswith(_TAG_TRIBAL_PREFIX):
            return t[len(_TAG_TRIBAL_PREFIX):]
    return None


# ── File I/O ─────────────────────────────────────────────────────


def _filename(post: Dict[str, Any]) -> str:
    ts = post["created_at"].replace(":", "").replace("-", "")
    # Created_at is full ISO; convert to compact form for filename.
    dt = _parse_iso(post["created_at"])
    ts_compact = _iso_ts_compact(dt) if dt else _iso_ts_compact()
    return f"{ts_compact}_{post['from_role']}_{post['status']}_{_sanitize_subject(post['subject'])}.json"


def _write_post(post: Dict[str, Any], brain_path: Optional[Path] = None) -> Path:
    _ensure_dirs(brain_path)
    path = _board_root(brain_path) / _filename(post)
    path.write_text(json.dumps(post, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _find_post_by_id(
    board_id: str, brain_path: Optional[Path] = None, include_archive: bool = False
) -> Optional[Tuple[Path, Dict[str, Any]]]:
    """Locate a post file by board_id. Returns (path, post) or None."""
    candidates = [_board_root(brain_path)]
    if include_archive:
        candidates.append(_archive_root(brain_path))
    for root in candidates:
        if not root.exists():
            continue
        for p in root.iterdir():
            if not p.is_file() or p.suffix != ".json":
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if data.get("board_id") == board_id:
                return p, data
    return None


def _rewrite_post(
    old_path: Path, post: Dict[str, Any], brain_path: Optional[Path] = None
) -> Path:
    """Replace file with one whose filename matches the post's new status."""
    new_path = _board_root(brain_path) / _filename(post)
    if new_path != old_path:
        try:
            old_path.unlink()
        except FileNotFoundError:
            pass
    new_path.write_text(json.dumps(post, indent=2, sort_keys=True), encoding="utf-8")
    return new_path


# ── Re-activation trigger ─────────────────────────────────────────


def _surface_related_archived(
    domain: str, brain_path: Optional[Path] = None, limit: int = 3
) -> List[str]:
    """Return up to `limit` most-recent archived board_ids sharing the domain tag."""
    if not domain:
        return []
    target = f"{_TAG_TRIBAL_PREFIX}{domain}"
    archive = _archive_root(brain_path)
    if not archive.exists():
        return []
    matches: List[Tuple[str, str]] = []
    for p in archive.iterdir():
        if not p.is_file() or p.suffix != ".json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if target in (data.get("tags") or []):
            matches.append((data.get("created_at", ""), data.get("board_id", "")))
    matches.sort(reverse=True)
    return [bid for _, bid in matches[:limit] if bid]


# ── TTL archival (activity-gated) ─────────────────────────────────


def _archive_stale(brain_path: Optional[Path] = None) -> List[str]:
    """Scan open posts; move stale ones to _archive/. Idempotent. Returns archived ids."""
    root = _board_root(brain_path)
    archive = _archive_root(brain_path)
    if not root.exists():
        return []
    archive.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    archived: List[str] = []
    for p in root.iterdir():
        if not p.is_file() or p.suffix != ".json":
            continue
        if p.name.startswith("."):  # skip .gitkeep etc.
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        status = data.get("status", "open")
        created = _parse_iso(data.get("created_at", ""))
        if created is None:
            continue
        age = now - created
        ttl = (
            timedelta(days=TTL_OPEN_DAYS) if status == "open"
            else timedelta(days=TTL_RESOLVED_DAYS) if status == "resolved"
            else None
        )
        if ttl is None or age <= ttl:
            continue
        dest = archive / p.name
        try:
            p.rename(dest)
            archived.append(data.get("board_id", ""))
        except OSError:
            continue
    return archived


# ── Activity-memory bridge (optional, degrades silently) ─────────


def _try_recall_activity(role: str, domain: Optional[str]) -> List[Dict[str, Any]]:
    if not domain:
        return []
    try:
        from nucleus_wedge import memories  # type: ignore
    except Exception:
        return []
    fn = getattr(memories, "nucleus_wedge__recall_activity", None)
    if not callable(fn):
        return []
    try:
        result = fn(role=role, domain=domain)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "results" in result:
            return list(result["results"])
        return []
    except Exception:
        return []


def _try_write_activity_engram(
    role: str, domain: Optional[str], resolution: str, board_id: str
) -> bool:
    try:
        from nucleus_wedge import memories  # type: ignore
    except Exception:
        return False
    fn = getattr(memories, "nucleus_wedge__write_activity", None)
    if not callable(fn):
        return False
    tags = [f"role:{role}", "source:board-resolution", f"board_id:{board_id}"]
    if domain:
        tags.append(f"domain:{domain}")
    try:
        fn(role=role, content=resolution, tags=tags)
        return True
    except Exception:
        return False


# ── Public ops ────────────────────────────────────────────────────


def post(
    subject: str,
    body: Dict[str, Any],
    tags: List[str],
    priority: str = "normal",
    from_role: Optional[str] = None,
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a new board post.

    Validates mandatory tagging, generates board_id, writes file, surfaces
    related archived items via re-activation trigger.
    """
    if not isinstance(body, dict):
        raise ValueError("body must be a dict")
    if priority not in _VALID_PRIORITIES:
        raise ValueError(
            f"priority must be one of {sorted(_VALID_PRIORITIES)}, got {priority!r}"
        )
    tags = list(tags or [])
    _validate_tags(tags)

    # TTL sweep on every mutating call.
    _archive_stale(brain_path)

    role = _resolve_role(from_role)
    now = datetime.now(timezone.utc)
    ts_compact = _iso_ts_compact(now)
    board_id = _new_board_id(ts_compact)

    # Re-activation trigger — pull most-recent archived for first domain.
    domain = _extract_domain(tags)
    related = _surface_related_archived(domain, brain_path) if domain else []
    if related:
        body = {**body, "related_archived_items": related}

    # Secret carve-out marker.
    if "secret-required" in tags:
        body = {
            **body,
            "secret_notice": "operator-keyboard only; do NOT transmit values",
        }

    post_doc: Dict[str, Any] = {
        "board_id": board_id,
        "schema_version": 1,
        "from_role": role,
        "subject": subject,
        "body": body,
        "tags": tags,
        "priority": priority,
        "status": "open",
        "created_at": _iso_ts_full(now),
        "claimed_by": None,
        "claimed_at": None,
        "resolved_by": None,
        "resolved_at": None,
        "resolution": None,
    }
    path = _write_post(post_doc, brain_path)

    return {
        "ok": True,
        "board_id": board_id,
        "file_path": str(path),
        "related_archived_count": len(related),
    }


def _read_claim_sentinel(claim_path: Path) -> Dict[str, Any]:
    body_file = claim_path / "claim.json"
    if body_file.exists():
        try:
            return json.loads(body_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def claim(
    board_id: str,
    claimer_role: Optional[str] = None,
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Atomically claim a post. First mkdir wins.

    Returns:
      {ok: True, board_id, post: <doc>, recall_results: [...]} on success
      {ok: False, error: 'already_claimed', already_claimed_by: <role>} on race loss
      {ok: False, error: 'not_found'} when no post matches.
    """
    _ensure_dirs(brain_path)
    role = _resolve_role(claimer_role)

    located = _find_post_by_id(board_id, brain_path, include_archive=False)
    if located is None:
        return {"ok": False, "error": "not_found", "board_id": board_id}
    old_path, post_doc = located

    claim_dir = _claims_root(brain_path) / f"{board_id}.claimed"
    try:
        claim_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        existing = _read_claim_sentinel(claim_dir)
        return {
            "ok": False,
            "error": "already_claimed",
            "board_id": board_id,
            "already_claimed_by": existing.get("claimer_role", "unknown"),
            "claimed_at": existing.get("claimed_at"),
        }

    now = _iso_ts_full()
    sentinel_body = {
        "board_id": board_id,
        "claimer_role": role,
        "claimed_at": now,
    }
    (claim_dir / "claim.json").write_text(
        json.dumps(sentinel_body, indent=2), encoding="utf-8"
    )

    post_doc["status"] = "claimed"
    post_doc["claimed_by"] = role
    post_doc["claimed_at"] = now
    _rewrite_post(old_path, post_doc, brain_path)

    domain = _extract_domain(post_doc.get("tags", []))
    recall_results = _try_recall_activity(role=role, domain=domain)

    return {
        "ok": True,
        "board_id": board_id,
        "post": post_doc,
        "recall_results": recall_results,
        "claimer_role": role,
    }


def resolve(
    board_id: str,
    resolution: str,
    resolver_role: Optional[str] = None,
    brain_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Mark a post resolved + (if available) write activity engram."""
    _ensure_dirs(brain_path)
    role = _resolve_role(resolver_role)

    located = _find_post_by_id(board_id, brain_path, include_archive=False)
    if located is None:
        return {"ok": False, "error": "not_found", "board_id": board_id}
    old_path, post_doc = located

    now = _iso_ts_full()
    post_doc["status"] = "resolved"
    post_doc["resolved_by"] = role
    post_doc["resolved_at"] = now
    post_doc["resolution"] = resolution
    new_path = _rewrite_post(old_path, post_doc, brain_path)

    domain = _extract_domain(post_doc.get("tags", []))
    engram_written = _try_write_activity_engram(
        role=role, domain=domain, resolution=resolution, board_id=board_id
    )

    # Opportunistic TTL sweep on mutating call.
    _archive_stale(brain_path)

    return {
        "ok": True,
        "board_id": board_id,
        "file_path": str(new_path),
        "resolver_role": role,
        "engram_written": engram_written,
    }


# ── Listing helpers (read-only, useful for tests + diagnostics) ──


def list_posts(
    status: Optional[str] = None, brain_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    root = _board_root(brain_path)
    if not root.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in sorted(root.iterdir()):
        if not p.is_file() or p.suffix != ".json":
            continue
        if p.name.startswith("."):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if status and data.get("status") != status:
            continue
        out.append(data)
    return out
