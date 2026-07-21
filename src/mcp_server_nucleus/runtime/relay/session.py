from __future__ import annotations
import inspect
import json
import logging
import os
import time
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from ..common import get_brain_path
from ..providers import coerce_to_tuple

logger = logging.getLogger("nucleus.relay")

_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")

def _is_shipped_artifact(ref: str) -> bool:
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    return bool(head) and not _RELAY_ID_RE.match(head)


# ── Session type detection ────────────────────────────────────────

KNOWN_SESSION_TYPES = {
    "cowork",
    "claude_code",
    "claude_code_main",
    "claude_code_peer",
    "windsurf",
    "cursor",
    "vscode",
    "claude_desktop",
    "gemini_cli",
    # Cross-vendor surfaces (Phase 0 role taxonomy refactor)
    "antigravity",
    "devin",
    "codex",
    "unknown",
}


def _maybe_split_cc_role(detected: str) -> str:
    """Upgrade bare `claude_code` to `claude_code_main`/`claude_code_peer` per ADR-0010.

    This is a Claude Code-specific fallback. It only fires when the detected
    session type is exactly "claude_code" (bare, not yet role-split). For all
    other session types (devin, agy, codex, etc.) it passes through unchanged.

    Per role_taxonomy_refactor_agy_v3.md Phase 1: this function is now called
    only from the Claude Code detection path within _detect_session_type_raw(),
    not as a blanket post-processing step. This prevents Claude-specific
    CC_SESSION_ROLE logic from leaking into non-Claude agent routing.

    ADR-0010 § Decision: `CC_SESSION_ROLE ∈ {main, peer}` (unset → `main` for legacy
    single-CC compatibility). This function implements the "unset → main" default
    so new code always produces a role-tagged sender. Legacy `claude_code` bucket
    then only holds messages from PRE-SPLIT CCs, drained by main's dual-read during
    the 2-week grace period (see _iter_inbox_dirs).
    """
    if detected == "claude_code":
        role = os.environ.get("CC_SESSION_ROLE", "").strip().lower()
        if role == "peer":
            return "claude_code_peer"
        return "claude_code_main"
    return detected


def detect_session_type() -> str:
    """Detect what kind of agent surface is running this process.

    Uses environment variables and heuristics to determine whether
    we're in Cowork, Claude Code, Windsurf, Cursor, Devin, AGY, etc.

    Per role_taxonomy_refactor_agy_v3.md Phase 1:
    - _maybe_split_cc_role() is now called inside _detect_session_type_raw()
      at the Claude Code detection point, not as a blanket post-processing step.
    - This prevents Claude-specific CC_SESSION_ROLE logic from leaking into
      non-Claude agent routing.

    Detection priority:
    1. Explicit override via NUCLEUS_SESSION_TYPE env var
    2. Registry ancestry (find_session_in_ancestry)
    3. Cowork sandbox path detection (/sessions/ with mnt)
    4. IDE-specific env vars (Windsurf, Cursor, VS Code, Claude Desktop)
    5. Claude Code heuristics (CLAUDE_* vars, process tree) → _maybe_split_cc_role
    6. Fallback to "unknown"
    """
    return _detect_session_type_raw()


def detect_session_role() -> str:
    """Resolve the agent's role independent of its IDE/provider.
    
    Per role_taxonomy_refactor_agy_v3.md Phase 1:
    1. Explicit NUCLEUS_SESSION_ROLE env var (vendor-neutral override).
    2. Registry-aware ancestry detection (reads role from registry — source of truth).
    3. CC_SESSION_ROLE env var (legacy fallback for pre-migration Claude Code sessions).
    4. Fallback to detect_session_type() for backward compatibility.
    """
    # Priority 1: Explicit override (vendor-neutral)
    explicit = os.environ.get("NUCLEUS_SESSION_ROLE", "").lower()
    if explicit:
        return explicit

    # Priority 2: Registry-aware ancestry detection (source of truth per v3 plan)
    try:
        from ...sessions.registry import find_session_in_ancestry
        matched = find_session_in_ancestry()
        if matched:
            role = matched.get("role")
            if isinstance(role, str) and role:
                return role
    except Exception:
        pass

    # Priority 3: CC_SESSION_ROLE (legacy fallback for pre-migration Claude Code)
    # The wrapper previously set this for all CLIs; now only Claude Code sets it.
    # Retained during transition period — removable after all CC sessions migrate
    # to NUCLEUS_SESSION_ROLE.
    cc_role = os.environ.get("CC_SESSION_ROLE", "").strip().lower()
    if cc_role and cc_role != "unknown":
        return cc_role

    # Priority 4: Fallback to provider type (backward compatibility)
    return detect_session_type()


# Map of substring → canonical session type, evaluated against each ancestor's
# executable path / command name. Order matters: more-specific tokens first.
_VSCODE_FORK_MARKERS: tuple[tuple[str, str], ...] = (
    ("Antigravity.app", "antigravity"),
    ("Windsurf.app", "windsurf"),
    ("Cursor.app", "cursor"),
    ("Visual Studio Code.app", "vscode"),
    ("Code - Insiders.app", "vscode"),
    # Lowercased substrings as a safety net for non-bundle invocations
    ("antigravity", "antigravity"),
    ("windsurf", "windsurf"),
    ("cursor", "cursor"),
)


def _disambiguate_vscode_fork() -> str | None:
    """Walk process ancestors looking for an app-bundle path that uniquely
    identifies which VS Code fork is hosting this process.

    Used as a fallback when VSCODE_PID is set but no fork-specific env var
    (WINDSURF_SESSION / CURSOR_SESSION / ANTIGRAVITY_SESSION) is — VS Code
    forks all inherit VSCODE_PID, so the env var alone cannot disambiguate.

    Returns one of the canonical session types from _VSCODE_FORK_MARKERS, or
    None if no ancestor matches a known fork. Best-effort, no exceptions.
    """
    try:
        curr_pid = os.getpid()
        # Bound the walk to avoid pathological infinite loops; 32 ancestors is
        # already 4x the depth of a typical macOS launchd→user-shell→app→helper chain.
        for _ in range(32):
            if curr_pid <= 1:
                break
            try:
                # `ps -o comm=` prints the executable path on macOS, basename on Linux
                comm = subprocess.check_output(
                    ["ps", "-o", "comm=", "-p", str(curr_pid)],
                    stderr=subprocess.DEVNULL,
                    timeout=1,
                ).decode("utf-8", errors="replace").strip()
            except Exception:
                break
            for marker, host in _VSCODE_FORK_MARKERS:
                if marker in comm or marker.lower() in comm.lower():
                    return host
            try:
                ppid_raw = subprocess.check_output(
                    ["ps", "-o", "ppid=", "-p", str(curr_pid)],
                    stderr=subprocess.DEVNULL,
                    timeout=1,
                ).decode("utf-8", errors="replace").strip()
                curr_pid = int(ppid_raw)
            except Exception:
                break
    except Exception:
        pass
    return None


def _detect_session_type_raw() -> str:
    # Priority 1: Explicit override always wins
    explicit = os.environ.get("NUCLEUS_SESSION_TYPE", "").lower()
    if explicit in KNOWN_SESSION_TYPES:
        return explicit

    # Priority 2: Registry-aware ancestry detection (deterministic).
    # When a parent process registered itself via
    # ``mcp_server_nucleus.sessions.registry.register_session``, walk up
    # the PID chain and return the registered ``agent`` field for the
    # closest matching ancestor. This is the deterministic counterpart to
    # the heuristic ``_disambiguate_vscode_fork`` below — needed when env
    # vars are inherited across forks (Windsurf vs Antigravity sharing
    # ``VSCODE_PID``, the original T3.11 wedge bug). Falls through silently
    # on any error so existing fallback heuristics retain their roles.
    try:
        from ...sessions.registry import find_session_in_ancestry
        matched = find_session_in_ancestry()
        if matched:
            agent = matched.get("agent")
            if isinstance(agent, str) and agent in KNOWN_SESSION_TYPES:
                return agent
    except Exception:
        pass

    # Priority 3: Cowork sessions run in /sessions/ sandbox paths
    cwd = os.getcwd()
    if "/sessions/" in cwd and "mnt" in cwd:
        return "cowork"

    # Priority 4: IDE-specific detection (reuses existing Nucleus patterns)
    if os.environ.get("WINDSURF_SESSION"):
        return "windsurf"
    if os.environ.get("CURSOR_SESSION"):
        return "cursor"
    if os.environ.get("ANTIGRAVITY_SESSION"):
        return "antigravity"
    if os.environ.get("GEMINI_CLI"):
        return "gemini_cli"
    if os.environ.get("CLAUDE_DESKTOP"):
        return "claude_desktop"
    if os.environ.get("VSCODE_PID"):
        # VSCODE_PID is shared across every VS Code fork (Antigravity, Windsurf,
        # Cursor, vanilla VS Code) — T3.11 wedge-identity bug. Disambiguate by
        # walking process ancestors and looking for the app-bundle path that
        # uniquely identifies the host. If no host can be identified we return
        # "vscode" (generic) so callers / registry can decide, rather than
        # falsely blanket-claiming any one fork.
        host = _disambiguate_vscode_fork()
        if host:
            return host
        return "vscode"

    # Priority 5: Claude Code detection (multiple heuristics)
    # Direct env vars that Claude Code may set
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_CODE_SESSION"):
        return _maybe_split_cc_role("claude_code")

    # MCP-over-stdio is used by Claude Code AND every other CLI (devin, agy, codex).
    # Per role_taxonomy_refactor_agy_v3.md Phase 0: do NOT default to "claude_code"
    # here — that swallowed non-Claude agents into Claude's routing. The registry
    # ancestry walk (priority 2) or NUCLEUS_SESSION_TYPE env var (priority 1) should
    # have already identified the vendor. If we reach this point, we genuinely don't
    # know who launched us.
    if os.environ.get("MCP_TRANSPORT") == "stdio":
        return "unknown"

    # Check if parent process looks like Claude Code (node-based CLI)
    try:
        ppid = os.getppid()
        cmdline_path = f"/proc/{ppid}/cmdline"
        if os.path.exists(cmdline_path):
            with open(cmdline_path, "r") as f:
                parent_cmd = f.read()
            if "claude" in parent_cmd.lower():
                return _maybe_split_cc_role("claude_code")
    except Exception:
        pass

    # Per role_taxonomy_refactor_agy_v3.md Phase 0: the ~/.claude dir + non-tty
    # heuristic (formerly lines 257-267) was removed because it classified ANY
    # non-tty process on a machine with Claude Code installed as Claude Code.
    # This was the cold-start false positive source — devin/agy/codex MCP
    # servers all run without a tty and all have ~/.claude present.
    # Cold start with no env vars, no registry entry, and no process match → unknown.

    # Priority 6: Fallback
    return "unknown"


def _caller_hint() -> str:
    """Return "file:lineno:funcname" for the caller of relay_post.

    Used by the R6.1-v2 coercion warning so the log points at the site that
    omitted ``sender=``, not at the inference branch itself. Best-effort:
    returns ``<unknown>`` if stack introspection fails.
    """
    try:
        stack = inspect.stack()
        # stack[0] = this helper, [1] = relay_post, [2] = caller of relay_post
        if len(stack) <= 2:
            return "<unknown>"
        frame = stack[2]
        return f"{Path(frame.filename).name}:{frame.lineno}:{frame.function}"
    except (IndexError, AttributeError, OSError):
        return "<unknown>"





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .paths import *
from .core import *
from .instrumentation import *
from .pending import *
from .briefing import *
from .watcher import *
from .daemon import *
