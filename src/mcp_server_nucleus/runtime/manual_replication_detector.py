"""Manual replication detector — detects when an agent manually replicates
compound-audit functionality and nudges them to use the automated loop.

Issue #37: Agent spent ~2 hours manually diagnosing audit failures, planning
fixes, implementing them, and re-running audits — exactly what --compound-audit
was already built to do. Nucleus should detect this and nudge.

Detection signals:
1. Rapid audit queries (3+ in 5min window) — agent manually reading audit logs
2. Sequential task claim → execute → sync pattern — manual task loop
3. Manual training data exports — agent exporting instead of compound
4. High frequency of same operation — timestamp clustering

The detector is read-only (queries audit logs) and non-blocking (nudges are
informational, not blocking). Throttled to 1 nudge per hour per team.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.manual_replication_detector")


@dataclass
class DetectionResult:
    """Result of a manual replication detection scan."""

    detected: bool = False
    pattern: str = ""
    confidence: float = 0.0
    evidence_count: int = 0
    suggested_action: str = ""
    actor: str = ""
    details: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_manual_compound_replication(
    team_id: str,
    window_minutes: int = 5,
    db_path: Optional[Path] = None,
) -> Optional[DetectionResult]:
    """Scan audit logs for patterns indicating manual compound-loop replication.

    Args:
        team_id: Team to scan.
        window_minutes: Look-back window in minutes (default 5).
        db_path: Optional audit DB path override.

    Returns:
        DetectionResult if manual replication detected, None otherwise.
    """
    try:
        from mcp_server_nucleus.runtime.audit_log import query_audit
    except ImportError:
        logger.warning("audit_log module not available — detector disabled")
        return None

    since = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()

    try:
        records = query_audit(team_id=team_id, since=since, db_path=db_path)
    except Exception as e:
        logger.warning(f"Failed to query audit log: {e}")
        return None

    if not records:
        return None

    # Pattern 1: Rapid audit queries (3+ in window)
    audit_queries = [r for r in records if r.event_type == "audit_query"]
    if len(audit_queries) >= 3:
        actor = audit_queries[-1].actor if audit_queries else ""
        return DetectionResult(
            detected=True,
            pattern="rapid_audit_queries",
            confidence=0.8,
            evidence_count=len(audit_queries),
            suggested_action="use_compound_mode",
            actor=actor,
            details=f"{len(audit_queries)} audit queries in {window_minutes}min — use `nucleus drive --compound` instead",
        )

    # Pattern 2: Sequential task claim → execute → sync (manual task loop)
    task_ops = [r for r in records if r.event_type in ("task_claim", "task_execute", "sync", "artifact_push")]
    if _is_sequential_compound_pattern(task_ops):
        actor = task_ops[-1].actor if task_ops else ""
        return DetectionResult(
            detected=True,
            pattern="manual_task_loop",
            confidence=0.9,
            evidence_count=len(task_ops),
            suggested_action="use_compound_mode",
            actor=actor,
            details=f"Sequential claim→execute→sync pattern detected ({len(task_ops)} ops) — use `nucleus drive --compound` instead",
        )

    # Pattern 3: Manual training data exports
    training_exports = [r for r in records if r.event_type == "training_export" and r.actor != "nucleus"]
    if len(training_exports) >= 2:
        actor = training_exports[-1].actor if training_exports else ""
        return DetectionResult(
            detected=True,
            pattern="manual_training_export",
            confidence=0.7,
            evidence_count=len(training_exports),
            suggested_action="use_compound_mode",
            actor=actor,
            details=f"{len(training_exports)} manual training exports — compound mode captures this automatically",
        )

    return None


def _is_sequential_compound_pattern(ops: list) -> bool:
    """Check if operations follow the claim→execute→sync pattern (3+ cycles)."""
    if len(ops) < 6:  # At least 2 full cycles (3 ops each)
        return False

    # Count how many times we see claim followed by execute followed by sync
    cycles = 0
    i = 0
    while i < len(ops) - 2:
        if (
            ops[i].event_type in ("task_claim", "claim_task")
            and ops[i + 1].event_type in ("task_execute", "execute_task")
            and ops[i + 2].event_type in ("sync", "artifact_push")
        ):
            cycles += 1
            i += 3
        else:
            i += 1

    return cycles >= 2
