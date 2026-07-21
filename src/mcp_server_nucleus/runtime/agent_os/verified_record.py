"""Agent OS — DSoR referee: label an agent-turn outcome with a verdict.

The doctrine (``AGENT_OS_MEMBRANE.md`` §3 referee): *never silently CONFIRM.* An
outcome with no deterministic anchor comes back UNVERIFIABLE — the agent
withholds, it does not guess. This module is a thin adapter over the existing
``runtime.verifier`` substrate: it builds a ``Claim`` from a turn outcome, runs
the verifier, and passes the honest verdict straight through. No status
post-processing — so an unanchorable assertion naturally returns UNVERIFIABLE.

Gated behind ``NUCLEUS_AGENT_OS_BOOT`` (default OFF) at the boot layer; this
module itself is import-safe and side-effect-free.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

from ..verifier import (
    Claim,
    InjectedReasoner,
    ProbeEngine,
    RuleReasoner,
    Verifier,
)


def _detect_repo_path() -> Optional[str]:
    """Detect the git repo root from the current working directory.

    This lets the ProbeEngine actually probe git anchors (commit_exists,
    is_ancestor, etc.) instead of returning UNVERIFIABLE with "no repo
    specified." Falls back to None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


def label_turn(
    outcome: str,
    *,
    context: str = "",
    claim_id: str = "agent_os_turn",
    verifier: Optional[Verifier] = None,
    repo_path: Optional[str] = None,
) -> dict:
    """Label an agent-turn outcome with a referee verdict.

    Returns ``{'status': str, 'confidence': float, 'detail': str}``. If no
    deterministic anchor applies, ``status`` is ``UNVERIFIABLE`` (withhold,
    never guess). The verifier's honest verdict is passed straight through —
    no status post-processing — so unanchorable outcomes naturally surface as
    UNVERIFIABLE rather than being silently CONFIRMED.

    ``verifier`` defaults to a read-only ``Verifier`` with a ``RuleReasoner``
    (rule-based anchor decomposition) and the standard ``ProbeEngine``; pass an
    ``InjectedReasoner``-backed verifier to force specific anchors for a test
    or a curated claim set.

    ``repo_path`` is passed to the ProbeEngine as ``default_repo`` so git
    anchors (commit_exists, is_ancestor) can actually probe the repo. Defaults
    to auto-detecting the git root from the current working directory.
    """
    if verifier is None:
        if repo_path is None:
            repo_path = _detect_repo_path()
        verifier = Verifier(
            reasoner=RuleReasoner(),
            probe_engine=ProbeEngine(default_repo=repo_path),
            ledger=None,
            record=False,
        )

    claim = Claim(
        claim_id=claim_id,
        source="agent_os",
        claimant="agent",
        assertion=outcome,
        raw={"context": context},
    )
    verdict = verifier.verify(claim)
    return {
        "status": verdict.status,
        "confidence": float(verdict.confidence),
        "detail": verdict.rationale,
    }


__all__: list[str] = ["label_turn"]
