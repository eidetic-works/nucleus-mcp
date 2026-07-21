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

import hashlib
import hmac
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

_ANCHOR_ENV = "NUCLEUS_IDENTITY_ANCHOR"


def _anchor_enabled() -> bool:
    return os.environ.get(_ANCHOR_ENV, "").strip().lower() in {"1", "true", "on", "yes"}


class RoleCredentialError(PermissionError):
    """Raised by :func:`register_session` when ``NUCLEUS_ROLE_CREDENTIAL`` is
    ON and the caller did not present a credential matching the claimed
    ``role``'s minted token.

    stone-1.5 (role-credential) — AUDIT_FINDINGS.md row #8 / ADJACENCY_
    THEOREM.md regime-2: ``role`` has no kernel-observable witness, so this
    is a bar-2 possession check (HMAC-comparable digest of the per-role
    token already minted at ``~/.tb/relay_token_<role>`` by
    ``scripts/gen_relay_token.py``), NOT a fraud-proof anchor. It raises the
    cost of forging a role from "type a string" to "possess that role's
    token" — a same-uid adversary who can read another role's token file
    still forges for free (bar-2 ceiling, not bar-1).
    """


def _role_credential_enabled() -> bool:
    """``NUCLEUS_ROLE_CREDENTIAL`` flag gate. Default OFF (legacy, byte-identical)."""
    return os.environ.get("NUCLEUS_ROLE_CREDENTIAL", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _role_credential_dir() -> Path:
    """Directory holding per-role tokens. Honors ``NUCLEUS_ROLE_CREDENTIAL_DIR``
    for test isolation (never point tests at the real ``~/.tb``)."""
    override = os.environ.get("NUCLEUS_ROLE_CREDENTIAL_DIR")
    if override:
        return Path(override)
    return Path.home() / ".tb"


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _verify_role_credential(role: str, presented: str | None) -> bool:
    """True iff ``presented`` matches the token minted for ``role``.

    Reads ``<role_credential_dir>/relay_token_<role>`` and compares its
    content against ``presented`` via constant-time digest comparison
    (``hmac.compare_digest`` over SHA-256 digests) — the raw values are
    hashed in-memory for the comparison and never logged, printed, or
    included in any return value or exception message.
    """
    if not presented or not role:
        return False
    token_path = _role_credential_dir() / f"relay_token_{role}"
    try:
        expected = token_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if not expected:
        return False
    return hmac.compare_digest(_digest(expected), _digest(presented))


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
    role_credential: str | None = None,
    type: str | None = None,
) -> dict[str, Any]:
    """Register a session envelope. Idempotent on ``session_id``.

    ``role_credential`` (stone-1.5, additive): when ``NUCLEUS_ROLE_CREDENTIAL``
    is ON, the caller must present the token minted for ``role`` at
    ``~/.tb/relay_token_<role>`` (or ``NUCLEUS_ROLE_CREDENTIAL_DIR`` override)
    — see :func:`_verify_role_credential`. Raises :class:`RoleCredentialError`
    on mismatch/absence. When the flag is OFF, ``role_credential`` is ignored
    entirely and behavior is byte-identical to pre-stone-1.5 callers (the
    ``role`` string is trusted as before — this is the legacy path).

    ``type`` (role_taxonomy_refactor_agy_v3.md Phase 1): optional execution
    type axis — one of {interactive, daemon, sub-agent}. Stored in the
    envelope for downstream routing/behavior decisions. Backward compatible:
    callers that don't pass ``type`` get an envelope without the field.
    """
    if not session_id:
        raise ValueError("session_id is required")
    if _role_credential_enabled():
        if not _verify_role_credential(role, role_credential):
            raise RoleCredentialError(
                f"role_credential rejected for role={role!r}: caller does not "
                "possess a matching token"
            )
    try:
        heartbeat_interval_s = int(heartbeat_interval_s)
    except (TypeError, ValueError):
        raise ValueError(f"heartbeat_interval_s must be a number, got {type(heartbeat_interval_s).__name__}")
    now = _utcnow_iso()
    payload = {
        "session_id": session_id,
        "agent": agent,
        "role": role,
        "worktree_path": _resolve_worktree(worktree_path),
        "pid": pid if pid is not None else os.getpid(),
        "registered_at": now,
        "last_heartbeat": now,
        "heartbeat_interval_s": heartbeat_interval_s,
        "provider": provider,
        "primitive_version": PRIMITIVE_VERSION,
    }
    # Phase 1: add type field if provided (backward compatible)
    if type:
        payload["type"] = type
    if _anchor_enabled():
        # FIX (HOLE 1): guard the WRITE leg like the delete/heartbeat legs.
        # If an ANCHORED envelope (one carrying create_time) already occupies this
        # session_id, only its lineage-owner may overwrite it — otherwise an
        # attacker re-registers over a victim and the server would stamp the
        # attacker as owner. A brand-new session_id (no file on disk) and
        # grandfathered envelopes (no create_time) are unaffected.
        _existing_path = _envelope_path(session_id)
        if _existing_path.exists():
            try:
                with _existing_path.open("r", encoding="utf-8") as _fh:
                    _existing = json.load(_fh)
            except (OSError, json.JSONDecodeError):
                _existing = None
            if (
                _existing is not None
                and isinstance(_existing.get("create_time"), str)
                and _existing.get("create_time")
                and not _caller_owns_envelope(_existing)
            ):
                raise PermissionError(
                    f"identity-anchor: caller lineage does not own session {session_id}"
                )
        if pid is None:
            # stdio MCP: the server is a child of the registering agent —
            # os.getppid() is the kernel-authenticated live registrant.
            payload["pid"] = os.getppid()
        elif payload["pid"] not in _caller_lineage():
            raise ValueError(
                f"identity-anchor: pid {payload['pid']} is not in the registering process lineage"
            )
        ct = _pid_create_time(payload["pid"])
        if ct is not None:
            payload["create_time"] = ct
        # ct None (no ps / Windows): fail open to pid-only envelope, same shape as flag-OFF
    _atomic_write(_envelope_path(session_id), payload)
    return payload


def heartbeat(session_id: str) -> dict[str, Any]:
    """Touch ``last_heartbeat`` on an existing envelope."""
    path = _envelope_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"session {session_id} not registered")
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if _anchor_enabled() and not _caller_owns_envelope(payload):
        raise PermissionError(f"identity-anchor: caller lineage does not own session {session_id}")
    payload["last_heartbeat"] = _utcnow_iso()
    _atomic_write(path, payload)
    return payload


def unregister(session_id: str) -> bool:
    """Delete the envelope. Returns True if a file was removed."""
    path = _envelope_path(session_id)
    if _anchor_enabled():
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            payload = None
        if payload is not None and not _caller_owns_envelope(payload):
            raise PermissionError(f"identity-anchor: caller lineage does not own session {session_id}")
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
    if (current - last).total_seconds() >= _LIVENESS_MULTIPLIER * interval:
        return False
    if _anchor_enabled():
        stored_ct = payload.get("create_time")
        pid_v = payload.get("pid")
        if isinstance(stored_ct, str) and stored_ct and isinstance(pid_v, int):
            live_ct = _pid_create_time(pid_v)
            if live_ct is not None and live_ct != stored_ct:
                return False  # process dead or PID recycled
    return True


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


def _ps_binary() -> str:
    """The ``ps`` executable to invoke for the kernel oracle.

    FIX (HOLE 2a): when anchoring is ON, resolve by ABSOLUTE path so a
    ``$PATH``-shimmed ``ps`` cannot redirect — or silently disable — the oracle
    the ownership check depends on. ``/bin/ps`` is preferred; only if it is
    absent do we fall back to ``shutil.which`` (POSIX-portable). Flag-OFF keeps
    the historical bare-``ps`` PATH lookup, so the flag-OFF path stays
    byte-identical.
    """
    if not _anchor_enabled():
        return "ps"
    if os.path.exists("/bin/ps"):
        return "/bin/ps"
    import shutil

    return shutil.which("ps") or "/bin/ps"


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
                [_ps_binary(), "-p", str(curr), "-o", "ppid="],
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


def _pid_create_time(pid: int) -> str | None:
    """Kernel process-start timestamp via ``ps -p <pid> -o lstart=``. None on any failure (fail-open)."""
    import subprocess

    try:
        out = subprocess.check_output(
            [_ps_binary(), "-p", str(pid), "-o", "lstart="],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        val = out.decode("utf-8", errors="replace").strip()
        return val or None
    except Exception:
        return None


def _caller_lineage() -> set[int]:
    """The querying process + its kernel ancestors. Empty ancestry ⇒ ``{os.getpid()}`` only."""
    return {os.getpid(), *_walk_ppid_ancestry(os.getpid())}


def _caller_owns_envelope(payload: dict[str, Any]) -> bool:
    """True iff the stored ``(pid, create_time)`` is a live, create_time-matching member of the caller's lineage.

    Grandfather: envelopes without a ``create_time`` key (registered flag-OFF) are
    not guarded — they degrade to the flag-OFF pid-only path (fail-open). That is
    the ONLY safe fail-open.

    FIX (HOLE 2b): for an ANCHORED envelope (one carrying ``create_time``) the
    kernel oracle MUST be reachable. If a claimant can suppress it — a
    ``$PATH``-shimmed ``ps`` collapsing lineage to ``{self}``, or an unreadable
    live create_time — we DENY (fail CLOSED), because that oracle sits inside the
    claimant's own authority. Never grant ownership of an anchored envelope on an
    oracle the caller could have silenced.
    """
    stored_ct = payload.get("create_time")
    if not (isinstance(stored_ct, str) and stored_ct):
        return True  # pre-anchor envelope — grandfathered (fail-open, flag-OFF parity)
    owner_pid = payload.get("pid")
    if not isinstance(owner_pid, int):
        return False
    lineage = _caller_lineage()
    if len(lineage) <= 1:
        return False  # oracle suppressed (lineage collapsed to self) — fail CLOSED
    if owner_pid not in lineage:
        return False
    live_ct = _pid_create_time(owner_pid)
    if live_ct is None:
        return False  # oracle unreadable for an anchored envelope — fail CLOSED
    return live_ct == stored_ct


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
        if match is None:
            continue
        if _anchor_enabled():
            stored_ct = match.get("create_time")
            if isinstance(stored_ct, str) and stored_ct:
                live_ct = _pid_create_time(ancestor_pid)
                if live_ct is not None and live_ct != stored_ct:
                    continue  # recycled PID / stale or forged envelope — skip, try next ancestor
        return match
    return None
