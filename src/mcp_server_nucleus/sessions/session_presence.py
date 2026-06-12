"""v0.3.0 — PID-file session-presence detection.

Per cc-peer 2026-06-09T11:55Z sketch SIGNOFF (Q2 CONCUR + augmentation):
PID file at ~/.tb/session.<role>.pid + os.kill(pid, 0) liveness probe.
Augmented per cc-peer: atexit + SIGTERM signal-handler cleanup to
minimize stale-PID files even on graceful shutdown (best-effort).

Used by the hook patch to skip autonomous-wake firing when a role's
CC session is currently running (existing Monitor / CCR push covers
running sessions; autonomous wake is for the OFFLINE/stepped-away case).

Race window: SIGKILL / OOM / hard-kill skip the atexit hook. Stale
PID file possible. Liveness probe via kill(pid, 0) catches this —
stale PID → file ignored → autonomous wake fires. False-negative
(session starting but PID not yet written) is acceptable v1 since
operator sees relay surface naturally on session start anyway.
"""
from __future__ import annotations

import atexit
import logging
import os
import signal
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.session_presence")

_PID_DIR = Path.home() / ".tb"

# Tracks roles this process has registered, so cleanup-on-exit only
# touches files THIS process owns.
_registered_roles: set[str] = set()


def _pidfile_for(role: str) -> Path:
    """Path to PID file for a role. Roles use [A-Za-z0-9_-] only."""
    if not role:
        raise ValueError("role required")
    return _PID_DIR / f"session.{role}.pid"


def register_session_pid(role: str, pid: Optional[int] = None) -> Path:
    """Write PID file at ~/.tb/session.<role>.pid mode 0o600.

    Default pid = os.getpid(). Returns the written path. Caller
    typically invokes from SessionStart hook.
    """
    if not role:
        raise ValueError("role required")
    path = _pidfile_for(role)
    path.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    actual_pid = pid if pid is not None else os.getpid()
    tmp.write_text(str(actual_pid))
    tmp.chmod(0o600)
    tmp.replace(path)
    _registered_roles.add(role)
    logger.info(
        "session_presence: registered role=%s pid=%d",
        role, actual_pid,
    )
    return path


def unregister_session_pid(role: str) -> bool:
    """Remove the PID file for a role. Returns True if file existed."""
    if not role:
        raise ValueError("role required")
    path = _pidfile_for(role)
    _registered_roles.discard(role)
    try:
        path.unlink()
        logger.info("session_presence: unregistered role=%s", role)
        return True
    except OSError:
        return False


def is_session_running(role: str) -> bool:
    """True iff a PID file exists for role AND the PID is alive.

    False if file absent, PID unreadable, or process dead.
    """
    if not role:
        return False
    path = _pidfile_for(role)
    try:
        raw = path.read_text().strip()
        pid = int(raw)
    except (OSError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        # ESRCH: no such process. EPERM: process exists but not ours
        # (acceptable — still "running")
        # We treat ESRCH as not-running; EPERM as running. POSIX kill(0)
        # raises ProcessLookupError (ESRCH) when process is gone.
        import errno
        return False if _last_kill_errno() == errno.ESRCH else True


def _last_kill_errno() -> int:
    """Return errno from the most recent OSError. Fallback: ESRCH."""
    # Helper to avoid catching+re-raising in is_session_running.
    # Approximate fallback when called outside an except clause.
    import errno
    import sys
    exc = sys.exc_info()[1]
    if isinstance(exc, OSError) and exc.errno is not None:
        return exc.errno
    return errno.ESRCH


def _cleanup_on_exit() -> None:
    """Remove PID files for roles registered by THIS process."""
    for role in list(_registered_roles):
        try:
            unregister_session_pid(role)
        except Exception:
            pass


def _on_sigterm(signum, frame) -> None:  # pragma: no cover - signal handler
    _cleanup_on_exit()
    # Re-raise default behavior so process actually exits
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


atexit.register(_cleanup_on_exit)
try:  # pragma: no cover - signal install
    signal.signal(signal.SIGTERM, _on_sigterm)
except Exception:
    # Non-main-thread or restricted environment — atexit still covers
    # the graceful-exit case.
    pass


__all__ = [
    "register_session_pid",
    "unregister_session_pid",
    "is_session_running",
]
