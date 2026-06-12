"""v0.3.1 — Disk-persistent grace-window coalesce for autonomous-wake.

REPLACES v0.3.0 in-memory implementation. Per cc-main 2026-06-09T11:29Z
+ devin_terminal_agent T3 empirical falsification: v0.3.0 used module-level
_pending dict + time.monotonic() — fails under one-shot subprocess
lifecycle (hook.py runs fresh per SessionStart/UserPromptSubmit; dict
resets every invocation; elapsed ~= 0 < 10s grace; drain returns {}).

Per cc-peer 2026-06-09T13:15Z 5-CONCUR sketch verdict + locked contract:
- Disk-persistent state at ~/.tb/coalesce_<role>.json mode 0o600
- Atomic write via tmp+replace (matches existing ~/.tb/ convention from
  Layers 0/1)
- time.time() wall-clock (NOT time.monotonic() -- process-local fails
  across one-shot subprocesses)
- Read-merge-write pattern for concurrent same-role arrivals (preserves
  all arrivals; cc-peer Q2 option (b) recommended)
- Clock-backwards edge case: max(0, elapsed) treats negative as
  not-yet-stale + retry next hook (Q3 disclosure)
- TB_AUTONOMOUS_WAKE_COALESCE_S=0 immediate-fire bypass (Q5 sub-bug
  fix: `>= 0` instead of `> 0`)

Honest scope: this fix delivers the FLEET-COORDINATED wake case (any
fleet member's hook fire drains stale coalesce state for offline roles
-- the common production case). Does NOT cover OPERATOR-FULLY-AWAY case
where zero CC sessions exist in fleet -> no hook fires -> no drain.
That is v0.4 candidate (launchd daemon per spec Option C).

What changed vs v0.3.0:
- Module-level _pending dict REMOVED -- disk is single source of truth
- add_arrival: read existing file (create if missing), append arrival,
  atomic write
- drain_ready_roles: scan ~/.tb/coalesce_*.json, return stale, delete
- peek_pending / clear_pending: filesystem-backed
- Same public API preserved (caller-transparent fix)
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.coalesce_queue")

_DEFAULT_GRACE_S = 10.0

# Disk-persistent state root. Matches existing ~/.tb/ convention from
# Layers 0/1 (oauth_<role>.json + session.<role>.pid + autonomous_wake_config.json).
_COALESCE_DIR = Path.home() / ".tb"
_FILENAME_PREFIX = "coalesce_"
_FILENAME_SUFFIX = ".json"


def _coalesce_file(role: str) -> Path:
    """Path for a role's coalesce state file."""
    return _COALESCE_DIR / f"{_FILENAME_PREFIX}{role}{_FILENAME_SUFFIX}"


def _read_state(path: Path) -> Optional[Dict[str, Any]]:
    """Read JSON state from file. Returns None on absent / corrupt."""
    try:
        raw = path.read_text()
    except OSError:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _write_state_atomic(path: Path, state: Dict[str, Any]) -> None:
    """Atomic write via tmp+replace; preserves mode 0o600."""
    _COALESCE_DIR.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state))
    tmp.chmod(0o600)
    tmp.replace(path)


def _grace_window_s() -> float:
    """Read TB_AUTONOMOUS_WAKE_COALESCE_S env override, default 10.0s.

    Per cc-peer Q5 sketch verdict: `val >= 0` (NOT `val > 0`) so
    operator can set 0 for immediate-fire mode. Negative values still
    fall through to default 10s (typo protection).
    """
    raw = os.environ.get("TB_AUTONOMOUS_WAKE_COALESCE_S")
    if not raw:
        return _DEFAULT_GRACE_S
    try:
        val = float(raw)
        if val >= 0:  # v0.3.1 fix: was `val > 0`
            return val
    except ValueError:
        pass
    return _DEFAULT_GRACE_S


def add_arrival(role: str, arrival_info: Any) -> None:
    """Persist a new arrival for role to ~/.tb/coalesce_<role>.json.

    Read-merge-write pattern per cc-peer Q2 option (b): reads existing
    state (if any), appends new arrival, atomic-writes. Preserves all
    arrivals across concurrent same-role fires (last-writer-wins would
    drop arrivals).

    `first_ts` is set on FIRST arrival only; subsequent arrivals do NOT
    update it. Grace window measured against first_ts.
    """
    if not role:
        raise ValueError("role required")
    path = _coalesce_file(role)
    now = time.time()  # wall-clock per Q3 verdict

    state = _read_state(path)
    if state is None:
        state = {"first_ts": now, "arrivals": [arrival_info]}
    else:
        existing = state.get("arrivals", [])
        if not isinstance(existing, list):
            existing = []
        existing.append(arrival_info)
        state["arrivals"] = existing
        if "first_ts" not in state:
            state["first_ts"] = now

    _write_state_atomic(path, state)
    logger.info(
        "coalesce_queue: arrival persisted role=%s pending=%d",
        role, len(state["arrivals"]),
    )


def drain_ready_roles() -> Dict[str, List[Any]]:
    """Return + DELETE roles whose first_ts is grace-stale.

    Result: {role: [arrival_info, ...]} for roles whose first-arrival
    is older than the grace window (wall-clock). Roles still within
    grace stay on disk for the next drain attempt.

    Per Q3 edge case: clock-backwards (NTP correction / manual time
    adjustment) -> negative elapsed -> treated via max(0, elapsed) ->
    role appears not-yet-stale -> retried on next hook fire. Conservative.
    """
    if not _COALESCE_DIR.exists():
        return {}
    grace = _grace_window_s()
    now = time.time()
    ready: Dict[str, List[Any]] = {}

    for path in sorted(_COALESCE_DIR.glob(f"{_FILENAME_PREFIX}*{_FILENAME_SUFFIX}")):
        state = _read_state(path)
        if state is None:
            continue
        first_ts = state.get("first_ts")
        if not isinstance(first_ts, (int, float)):
            continue
        elapsed = max(0.0, now - float(first_ts))  # Q3: clock-backwards safe
        if elapsed >= grace:
            role = path.name[len(_FILENAME_PREFIX):-len(_FILENAME_SUFFIX)]
            arrivals = state.get("arrivals", [])
            ready[role] = list(arrivals) if isinstance(arrivals, list) else []
            try:
                path.unlink()
            except OSError:
                pass

    if ready:
        logger.info(
            "coalesce_queue: drained roles=%s",
            sorted(ready.keys()),
        )
    return ready


def peek_pending() -> Dict[str, int]:
    """Return {role: arrival_count} from all coalesce files. No side effects."""
    out: Dict[str, int] = {}
    if not _COALESCE_DIR.exists():
        return out
    for path in sorted(_COALESCE_DIR.glob(f"{_FILENAME_PREFIX}*{_FILENAME_SUFFIX}")):
        state = _read_state(path)
        if state is None:
            continue
        role = path.name[len(_FILENAME_PREFIX):-len(_FILENAME_SUFFIX)]
        arrivals = state.get("arrivals", [])
        out[role] = len(arrivals) if isinstance(arrivals, list) else 0
    return out


def clear_pending(role: str = "") -> None:
    """Delete coalesce files. If role specified, that role only.
    No-role = clear all. For tests + operator-side reset."""
    if not _COALESCE_DIR.exists():
        return
    if role:
        path = _coalesce_file(role)
        try:
            path.unlink()
        except OSError:
            pass
    else:
        for path in _COALESCE_DIR.glob(f"{_FILENAME_PREFIX}*{_FILENAME_SUFFIX}"):
            try:
                path.unlink()
            except OSError:
                pass


__all__ = [
    "add_arrival",
    "drain_ready_roles",
    "peek_pending",
    "clear_pending",
]
