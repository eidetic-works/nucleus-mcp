"""Agent session-registry (T3.11) — presence tracking + 3rd-writer detection.

Primitive-gate axes (any-OS / any-user / any-agent / any-LLM):
  - paths resolve through ``${NUCLEUS_AGENT_REGISTRY}`` → ``brain_path()`` →
    invoking user's home. No ``/Users/*`` hardcodes.
  - envelope is provider-neutral: ``agent`` / ``role`` / ``provider`` are free
    strings keyed off ADR-0005's generic vocab; no Claude-specific assumption.
  - one file per session (``{session_id}.json``), atomic write-then-rename,
    last-writer-wins is impossible by construction because each writer owns
    its own filename.
  - liveness is clock-relative (``now - last_heartbeat < 2 * interval``), so
    host-reboot / stale-pid cases fall off naturally without a GC pass.

The registry is namespaced under ``agent_registry/`` (NOT ``sessions/``) to
stay additive with existing ``nucleus_sessions.save/resume`` which owns
session-context snapshots under ``.brain/sessions/``.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..paths import brain_path

PRIMITIVE_VERSION = "1"
DEFAULT_HEARTBEAT_INTERVAL_S = 30
_LIVENESS_MULTIPLIER = 2


def agent_registry_root() -> Path:
    """Resolve the registry directory, honoring ``NUCLEUS_AGENT_REGISTRY``."""
    override = os.environ.get("NUCLEUS_AGENT_REGISTRY")
    if override:
        return Path(override)
    return brain_path() / "agent_registry"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _resolve_worktree(path: str | os.PathLike[str] | None) -> str | None:
    if path is None:
        return None
    return str(Path(path).resolve())


def _envelope_path(session_id: str) -> Path:
    safe = session_id.replace("/", "_").replace("..", "_")
    return agent_registry_root() / f"{safe}.json"


def _atomic_write(target: Path, payload: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".reg-", suffix=".json", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True, indent=2)
        os.replace(tmp, target)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def register_session(
    session_id: str,
    agent: str,
    role: str,
    provider: str,
    worktree_path: str | os.PathLike[str] | None = None,
    pid: int | None = None,
    heartbeat_interval_s: int = DEFAULT_HEARTBEAT_INTERVAL_S,
) -> dict[str, Any]:
    """Register a session envelope. Idempotent on ``session_id``."""
    if not session_id:
        raise ValueError("session_id is required")
    now = _utcnow_iso()
    payload = {
        "session_id": session_id,
        "agent": agent,
        "role": role,
        "worktree_path": _resolve_worktree(worktree_path),
        "pid": pid if pid is not None else os.getpid(),
        "registered_at": now,
        "last_heartbeat": now,
        "heartbeat_interval_s": int(heartbeat_interval_s),
        "provider": provider,
        "primitive_version": PRIMITIVE_VERSION,
    }
    _atomic_write(_envelope_path(session_id), payload)
    return payload


def heartbeat(session_id: str) -> dict[str, Any]:
    """Touch ``last_heartbeat`` on an existing envelope."""
    path = _envelope_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"session {session_id} not registered")
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    payload["last_heartbeat"] = _utcnow_iso()
    _atomic_write(path, payload)
    return payload


def unregister(session_id: str) -> bool:
    """Delete the envelope. Returns True if a file was removed."""
    path = _envelope_path(session_id)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def _is_alive(payload: dict[str, Any], *, now: datetime | None = None) -> bool:
    interval = int(payload.get("heartbeat_interval_s", DEFAULT_HEARTBEAT_INTERVAL_S))
    try:
        last = _parse_iso(payload["last_heartbeat"])
    except (KeyError, ValueError):
        return False
    current = now or datetime.now(timezone.utc)
    return (current - last).total_seconds() < _LIVENESS_MULTIPLIER * interval


def _iter_envelopes() -> Iterable[dict[str, Any]]:
    root = agent_registry_root()
    if not root.exists():
        return
    for entry in sorted(root.iterdir()):
        if entry.suffix != ".json" or entry.name.startswith(".reg-"):
            continue
        try:
            with entry.open("r", encoding="utf-8") as fh:
                yield json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue


def list_agents(
    worktree_path: str | os.PathLike[str] | None = None,
    role: str | None = None,
    alive_only: bool = True,
) -> list[dict[str, Any]]:
    """Return registered envelopes, optionally filtered."""
    resolved = _resolve_worktree(worktree_path)
    now = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for payload in _iter_envelopes():
        if resolved is not None and payload.get("worktree_path") != resolved:
            continue
        if role is not None and payload.get("role") != role:
            continue
        if alive_only and not _is_alive(payload, now=now):
            continue
        results.append(payload)
    return results


def detect_splits(
    worktree_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Return ``(worktree_path, role)`` buckets with more than one alive session."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for payload in list_agents(worktree_path=worktree_path, alive_only=True):
        key = (payload.get("worktree_path") or "", payload.get("role") or "")
        grouped.setdefault(key, []).append(payload)
    splits: list[dict[str, Any]] = []
    for (wt, rl), members in grouped.items():
        if len(members) <= 1:
            continue
        splits.append(
            {
                "worktree_path": wt,
                "role": rl,
                "count": len(members),
                "sessions": [m["session_id"] for m in members],
                "agents": sorted({m.get("agent", "") for m in members}),
            }
        )
    return splits


# ── Ancestry-walk primitive (T3.11 deterministic detection) ──────────────────


def _walk_ppid_ancestry(start_pid: int, max_depth: int = 32) -> list[int]:
    """Walk parent-PID chain from ``start_pid`` upward.

    Returns the list of ancestor PIDs in walk order (closest ancestor first),
    excluding ``start_pid`` itself. Bounded by ``max_depth``. Best-effort —
    on platforms without a working ``ps -p <pid> -o ppid=`` invocation
    (notably Windows) returns an empty list. Stops at PID 1 (init), at
    self-parent loops, and at ps failures.

    POSIX-portable via ``ps``; same shim used by ``runtime.relay_ops.
    _disambiguate_vscode_fork`` (PR #162). Kept in registry to avoid a
    cross-module import dependency for the consumer of
    ``find_session_in_ancestry``.
    """
    import subprocess

    ancestors: list[int] = []
    curr = start_pid
    seen = {curr}
    for _ in range(max_depth):
        try:
            out = subprocess.check_output(
                ["ps", "-p", str(curr), "-o", "ppid="],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode("utf-8", errors="replace").strip()
        except Exception:
            break
        if not out:
            break
        try:
            ppid = int(out)
        except ValueError:
            break
        if ppid <= 1 or ppid in seen:
            break
        ancestors.append(ppid)
        seen.add(ppid)
        curr = ppid
    return ancestors


def find_session_in_ancestry(
    start_pid: int | None = None,
    max_depth: int = 32,
    *,
    alive_only: bool = True,
) -> dict[str, Any] | None:
    """Return the registered session whose ``pid`` matches the closest
    ancestor of ``start_pid`` (defaults to current process).

    Walks the parent-PID chain via :func:`_walk_ppid_ancestry` and returns
    the first match in :func:`list_agents`. ``None`` if no ancestor matches
    a registered session, or if ancestry walk yields nothing (e.g. Windows
    or ``ps`` unavailable).

    Use case (T3.11 wedge): when ``runtime.relay_ops.detect_session_type``
    cannot disambiguate a VS Code fork via env vars (Windsurf vs Antigravity
    inheriting the same ``VSCODE_PID``), an ancestor process registered via
    :func:`register_session` provides deterministic identification. This is
    the **primitive** companion to PR #162's heuristic process-ancestor
    app-bundle inspection in ``_disambiguate_vscode_fork`` — both can
    coexist; registry-aware is preferred when a session is actually
    registered, heuristic is the fallback.

    Args:
        start_pid: PID to start the walk from. Defaults to ``os.getpid()``.
        max_depth: Maximum number of ancestors to inspect. Defaults to 32.
        alive_only: If True (default), filter out registered sessions whose
            heartbeat is stale. Set False for debugging / forensics.

    Returns:
        The session envelope dict (same shape as :func:`register_session`'s
        return) for the closest matching ancestor, or ``None``.
    """
    pid = start_pid if start_pid is not None else os.getpid()
    ancestors = _walk_ppid_ancestry(pid, max_depth=max_depth)
    if not ancestors:
        return None
    # Build pid -> envelope index from registered sessions.
    by_pid: dict[int, dict[str, Any]] = {}
    for envelope in list_agents(alive_only=alive_only):
        env_pid = envelope.get("pid")
        if isinstance(env_pid, int):
            by_pid[env_pid] = envelope
    if not by_pid:
        return None
    # Closest ancestor wins.
    for ancestor_pid in ancestors:
        match = by_pid.get(ancestor_pid)
        if match is not None:
            return match
    return None
