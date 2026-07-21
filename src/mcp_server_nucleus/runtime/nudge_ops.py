"""Nudge operations — deliver nudges to agents and track throttle state.

Issue #37: When manual replication is detected, emit a nudge via the relay
system. Throttled to 1 nudge per hour per team to avoid spam.

Nudges are informational only (not blocking) and include a direct suggestion
to use `nucleus drive --compound` instead of manual replication.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.nudge_ops")

# Throttle: 1 nudge per hour per team
NUDGE_THROTTLE_SECONDS = 3600


def _nudge_state_path(brain_path: Path, team_id: str) -> Path:
    """Get the nudge state file path for a team."""
    return brain_path / "nudges" / f"manual_replication_{team_id}.json"


def _read_nudge_state(brain_path: Path, team_id: str) -> dict:
    """Read the last nudge state for a team."""
    path = _nudge_state_path(brain_path, team_id)
    if not path.exists():
        return {"last_nudge_ts": 0, "nudge_count": 0, "last_pattern": ""}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"last_nudge_ts": 0, "nudge_count": 0, "last_pattern": ""}


def _write_nudge_state(brain_path: Path, team_id: str, state: dict) -> None:
    """Write nudge state for a team."""
    path = _nudge_state_path(brain_path, team_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def should_nudge(brain_path: Path, team_id: str) -> bool:
    """Check if enough time has passed since the last nudge."""
    state = _read_nudge_state(brain_path, team_id)
    now = time.time()
    return (now - state.get("last_nudge_ts", 0)) >= NUDGE_THROTTLE_SECONDS


def emit_nudge(
    team_id: str,
    pattern: str,
    actor: str,
    details: str,
    brain_path: Optional[Path] = None,
) -> dict:
    """Emit a nudge to an agent about manual replication.

    Args:
        team_id: Team to nudge.
        pattern: Detection pattern name.
        actor: Agent that triggered the detection.
        details: Human-readable details.
        brain_path: Optional brain path override.

    Returns:
        dict with: {emitted: bool, reason: str, nudge: dict}
    """
    if brain_path is None:
        brain_path = Path.cwd() / ".brain"

    # Check throttle
    if not should_nudge(brain_path, team_id):
        return {
            "emitted": False,
            "reason": "throttled",
            "nudge": None,
        }

    nudge = {
        "type": "nudge",
        "category": "efficiency",
        "pattern": pattern,
        "actor": actor,
        "message": (
            f"Detected {pattern} — Nucleus can automate this via "
            f"`nucleus drive --compound`. "
            f"Enable it with `nucleus start` or run manually with "
            f"`nucleus drive --compound 5`."
        ),
        "details": details,
        "severity": "info",
        "at": datetime.now(timezone.utc).isoformat(),
    }

    # Try to post via relay system (best-effort)
    relay_posted = False
    try:
        from mcp_server_nucleus.runtime.relay.core import relay_post

        relay_post(
            to=actor or "claude_code_main",
            subject=f"[NUDGE] Manual replication detected: {pattern}",
            body=nudge["message"] + "\n\n" + details,
            sender="nucleus",
        )
        relay_posted = True
    except Exception as e:
        logger.warning(f"Failed to post nudge via relay: {e}")

    # Write to nudges log (always, even if relay fails)
    try:
        nudge_log = brain_path / "nudges" / "nudge_log.jsonl"
        nudge_log.parent.mkdir(parents=True, exist_ok=True)
        with open(nudge_log, "a") as f:
            f.write(json.dumps({**nudge, "relay_posted": relay_posted, "team_id": team_id}) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write nudge log: {e}")

    # Update throttle state
    state = _read_nudge_state(brain_path, team_id)
    state["last_nudge_ts"] = time.time()
    state["nudge_count"] = state.get("nudge_count", 0) + 1
    state["last_pattern"] = pattern
    _write_nudge_state(brain_path, team_id, state)

    return {
        "emitted": True,
        "reason": "ok",
        "nudge": nudge,
        "relay_posted": relay_posted,
    }


def detect_and_nudge(
    team_id: str,
    brain_path: Optional[Path] = None,
    window_minutes: int = 5,
) -> dict:
    """Run detection and emit nudge if manual replication is found.

    This is the main entry point — call after each audit log entry.

    Returns:
        dict with: {detected: bool, nudged: bool, pattern: str, details: str}
    """
    from mcp_server_nucleus.runtime.manual_replication_detector import (
        detect_manual_compound_replication,
    )

    if brain_path is None:
        brain_path = Path.cwd() / ".brain"

    result = detect_manual_compound_replication(
        team_id=team_id,
        window_minutes=window_minutes,
    )

    if result is None or not result.detected:
        return {"detected": False, "nudged": False, "pattern": "", "details": ""}

    nudge_result = emit_nudge(
        team_id=team_id,
        pattern=result.pattern,
        actor=result.actor,
        details=result.details,
        brain_path=brain_path,
    )

    return {
        "detected": True,
        "nudged": nudge_result["emitted"],
        "pattern": result.pattern,
        "confidence": result.confidence,
        "details": result.details,
        "nudge_reason": nudge_result["reason"],
    }
