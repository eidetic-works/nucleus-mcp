"""Agent OS — Shell-Execution Witness (regime-2 attribution).

The first external witness for the referee. Logs shell executions to
``.brain/witness/shell_log.jsonl`` with PID + timestamp + exit code, so the
referee can verify "I ran this command" claims.

The witness is OUTSIDE agent authority: agents cannot write to
``.brain/witness/`` — only the OS (this module, called from boot.py / the
gateway) writes there. This is the binding constraint that makes the witness
trustworthy: the agent cannot fabricate its own execution log.

Usage (from the OS, not from agents):

    from mcp_server_nucleus.runtime.agent_os.witness_shell import log_shell_exec

    log_shell_exec(
        command="pytest tests/test_foo.py",
        pid=12345,
        exit_code=0,
        agent_id="cell-0",
        session_id="agent-os-cell",
    )

The referee can then query the witness:

    from mcp_server_nucleus.runtime.agent_os.witness_shell import query_shell_exec

    found = query_shell_exec(command="pytest", brain_path=brain_path)
    # → True if any logged execution matches "pytest"

ADR-0047 Workstream B3: the narrowest possible regime-2 witness. It only
verifies that a command was executed, not that it succeeded for the right
reason. But it closes the attribution gap for the most common agent claim:
"I ran the tests" / "I deployed the code."
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleus.agent_os.witness_shell")

WITNESS_DIR = "witness"
SHELL_LOG_FILE = "shell_log.jsonl"


def _witness_path(brain_path: Optional[str] = None) -> Path:
    """Resolve the shell-log witness path."""
    root = Path(brain_path) if brain_path else Path(
        os.environ.get("NUCLEUS_BRAIN_PATH", ".brain")
    )
    witness_dir = root / WITNESS_DIR
    witness_dir.mkdir(parents=True, exist_ok=True)
    return witness_dir / SHELL_LOG_FILE


def log_shell_exec(
    command: str,
    *,
    pid: Optional[int] = None,
    exit_code: Optional[int] = None,
    agent_id: str = "cell-0",
    session_id: str = "agent-os-cell",
    brain_path: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> str:
    """Log a shell execution to the witness file.

    Returns the witness entry ID (``witness-shell-<timestamp>-<pid>``).

    This function is called by the OS (boot.py / gateway), NOT by agents.
    Agents cannot write to ``.brain/witness/`` — the directory is owned by
    the OS. This is the binding constraint that makes the witness trustworthy.
    """
    path = _witness_path(brain_path)
    ts = time.time()
    entry_id = f"witness-shell-{int(ts)}-{pid or 0}"

    entry = {
        "witness_id": entry_id,
        "timestamp": ts,
        "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "command": command,
        "pid": pid,
        "exit_code": exit_code,
        "agent_id": agent_id,
        "session_id": session_id,
        "duration_ms": duration_ms,
    }

    # Append-only — never overwrite
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("witness: logged shell exec — %s (exit=%s)", command[:60], exit_code)
    return entry_id


def query_shell_exec(
    command: str,
    *,
    brain_path: Optional[str] = None,
    agent_id: Optional[str] = None,
    since_timestamp: Optional[float] = None,
) -> Optional[bool]:
    """Query the witness log for a matching shell execution.

    Returns True if any logged execution contains the query command as a
    substring. This is the referee's lookup: "did any agent run a command
    matching X?"

    The match is substring-based (not exact) so "pytest" matches
    "pytest tests/test_foo.py -v". This is intentional — the referee checks
    whether the agent ran *something like* the claimed command, not the
    exact byte-for-byte command.
    """
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

    query_lower = command.lower().strip()
    if not query_lower:
        return False

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Filter by agent_id if specified
            if agent_id and entry.get("agent_id") != agent_id:
                continue

            # Filter by timestamp if specified
            if since_timestamp and entry.get("timestamp", 0) < since_timestamp:
                continue

            logged_cmd = (entry.get("command") or "").lower()
            if query_lower in logged_cmd:
                return True

    return False


def get_witness_entries(
    *,
    brain_path: Optional[str] = None,
    limit: int = 100,
    agent_id: Optional[str] = None,
) -> list[dict]:
    """Read witness entries (for debugging / canary / inspection)."""
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
    "log_shell_exec",
    "query_shell_exec",
    "get_witness_entries",
]
