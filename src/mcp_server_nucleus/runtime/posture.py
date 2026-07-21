"""Agent posture — declared, confirmed, approved, persisted.

The posture is the agent's role + approach, declared in conversation,
confirmed by the agent, approved by the operator, and persisted in
.brain/posture/current.json. Every MCP call auto-reads it.

Flow:
  1. Operator says "you are principal, work via delegates"
  2. Agent calls nucleus_declare_posture(role="principal", approach="delegate")
  3. Agent confirms: "confirmed — I'm principal, working via delegates"
  4. Operator says "approved"
  5. Posture persists — survives restarts, auto-applied to every call

The posture is the single source of truth for the agent's role. No env
vars, no config files, no role strings in every call. The agent just
calls wakeup_wait() and the system knows who it is.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .common import get_brain_path

logger = logging.getLogger("nucleus.posture")

POSTURE_FILE = "posture/current.json"

VALID_ROLES = {"principal", "peer", "observer", "secretary", "reviewer", "worker"}
VALID_APPROACHES = {"delegate", "hands-on", "review-only", "execute"}


def _posture_path() -> Path:
    return get_brain_path() / POSTURE_FILE


def declare_posture(
    role: str,
    approach: str = "execute",
    agent_id: str = "",
    delegation_targets: Optional[list] = None,
) -> Dict[str, Any]:
    """Declare a posture. Agent calls this to propose its role.

    Args:
        role: the agent's role (principal, peer, observer, etc.)
        approach: how the agent works (delegate, hands-on, review-only, execute)
        agent_id: which agent is declaring (e.g. "agy", "cc_main")
        delegation_targets: if approach=delegate, which agents to delegate to

    Returns:
        dict with the declared posture (status="pending_approval")
    """
    role = role.lower().strip()
    approach = approach.lower().strip()

    if role not in VALID_ROLES:
        return {"success": False, "error": f"Invalid role '{role}'. Valid: {VALID_ROLES}"}
    if approach not in VALID_APPROACHES:
        return {"success": False, "error": f"Invalid approach '{approach}'. Valid: {VALID_APPROACHES}"}

    posture = {
        "role": role,
        "approach": approach,
        "agent_id": agent_id,
        "delegation_targets": delegation_targets or [],
        "status": "pending_approval",  # pending_approval → approved → active
        "declared_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "approved_at": None,
        "approved_by": None,
    }

    path = _posture_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(posture, indent=2), encoding="utf-8")

    logger.info("posture declared: role=%s approach=%s agent=%s — pending approval", role, approach, agent_id)
    return {"success": True, "posture": posture}


def approve_posture(approved_by: str = "operator") -> Dict[str, Any]:
    """Approve the current posture. Operator calls this after the agent confirms.

    Args:
        approved_by: who approved (default "operator")

    Returns:
        dict with the approved posture (status="active")
    """
    path = _posture_path()
    if not path.exists():
        return {"success": False, "error": "No posture declared yet"}

    posture = json.loads(path.read_text(encoding="utf-8"))
    posture["status"] = "active"
    posture["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    posture["approved_by"] = approved_by

    path.write_text(json.dumps(posture, indent=2), encoding="utf-8")

    logger.info("posture approved: role=%s approach=%s — active", posture["role"], posture["approach"])
    return {"success": True, "posture": posture}


def get_current_posture() -> Dict[str, Any]:
    """Get the current posture. Returns empty dict if none declared."""
    path = _posture_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_current_role() -> str:
    """Get the current role, or empty string if no active posture."""
    posture = get_current_posture()
    if posture.get("status") == "active":
        return posture.get("role", "")
    return ""


def clear_posture() -> Dict[str, Any]:
    """Clear the current posture. Used when the operator wants to reset."""
    path = _posture_path()
    if path.exists():
        path.unlink()
    return {"success": True}
