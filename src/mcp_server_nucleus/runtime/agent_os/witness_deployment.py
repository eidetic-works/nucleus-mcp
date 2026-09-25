"""Agent OS — Deployment Witness (regime-2 attribution for deployments).

The second external witness for the referee. Logs CI/CD deployments to
``.brain/witness/deployment_log.jsonl`` with deployment ID + timestamp +
URL + commit SHA, so the referee can verify "I deployed X" claims.

Like the shell-execution witness (B3), this witness is OUTSIDE agent
authority: agents cannot write to ``.brain/witness/`` — only the OS writes
there. This is the binding constraint that makes the witness trustworthy.

ADR-0047 Workstream D2: extends the referee's regime-2 reach to deployment
claims. Closes the attribution gap for "I deployed to production" — the
second most common agent claim type after "I ran X."
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.agent_os.witness_deployment")

WITNESS_DIR = "witness"
DEPLOYMENT_LOG_FILE = "deployment_log.jsonl"


def _witness_path(brain_path: Optional[str] = None) -> Path:
    root = Path(brain_path) if brain_path else Path(
        os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")
    )
    witness_dir = root / WITNESS_DIR
    witness_dir.mkdir(parents=True, exist_ok=True)
    return witness_dir / DEPLOYMENT_LOG_FILE


def log_deployment(
    url: str,
    *,
    commit_sha: Optional[str] = None,
    deployment_id: Optional[str] = None,
    agent_id: str = "cell-0",
    session_id: str = "agent-os-cell",
    brain_path: Optional[str] = None,
    environment: str = "production",
) -> str:
    """Log a deployment to the witness file.

    Returns the witness entry ID (``witness-deploy-<timestamp>``).
    """
    path = _witness_path(brain_path)
    ts = time.time()
    entry_id = f"witness-deploy-{int(ts)}"

    entry = {
        "witness_id": entry_id,
        "timestamp": ts,
        "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "url": url,
        "commit_sha": commit_sha,
        "deployment_id": deployment_id,
        "environment": environment,
        "agent_id": agent_id,
        "session_id": session_id,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("witness: logged deployment — %s (sha=%s)", url[:60], commit_sha)
    return entry_id


def query_deployment(
    url: Optional[str] = None,
    *,
    commit_sha: Optional[str] = None,
    brain_path: Optional[str] = None,
    agent_id: Optional[str] = None,
    since_timestamp: Optional[float] = None,
) -> Optional[bool]:
    """Query the witness log for a matching deployment.

    Returns True if any logged deployment matches the query. Match by URL
    (substring) or commit_sha (exact). At least one of url or commit_sha
    must be provided.
    """
    if not url and not commit_sha:
        return False

    path = _witness_path(brain_path)
    if not path.exists():
        # NO LOG IS NOT "NO". Returning False here answers "that never
        # happened" when the truth is "nothing was ever recorded" -- a
        # definitive negative manufactured from absent data. The witness log is
        # written only by scripts/witness_bridge.py, which nothing currently
        # invokes, so in the live system this branch is the ONLY branch: every
        # query returned a confident False.
        #
        # None is the third state (INSUFFICIENT). Callers that do `if found:`
        # are unaffected -- None is falsy -- but a caller that cares can now
        # tell "not found" from "cannot know".
        return None

    url_lower = (url or "").lower().strip()
    sha_lower = (commit_sha or "").lower().strip()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if agent_id and entry.get("agent_id") != agent_id:
                continue
            if since_timestamp and entry.get("timestamp", 0) < since_timestamp:
                continue

            # Match by URL (substring) OR commit_sha (exact)
            if url_lower and url_lower in (entry.get("url") or "").lower():
                return True
            if sha_lower and sha_lower == (entry.get("commit_sha") or "").lower():
                return True

    return False


def get_deployment_entries(
    *,
    brain_path: Optional[str] = None,
    limit: int = 100,
    agent_id: Optional[str] = None,
) -> list[dict]:
    """Read deployment witness entries (for debugging / inspection)."""
    path = _witness_path(brain_path)
    if not path.exists():
        return []

    entries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent_id and entry.get("agent_id") != agent_id:
                continue
            entries.append(entry)

    return entries[-limit:]


__all__ = [
    "log_deployment",
    "query_deployment",
    "get_deployment_entries",
]
