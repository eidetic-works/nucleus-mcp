"""Cross-session relay for Cowork ↔ Claude Code communication.

Provides a file-based mailbox system where different Claude surfaces
(Cowork, Claude Code, Windsurf, Cursor, etc.) can exchange messages
through the shared .brain/ directory.

Storage: .brain/relay/{recipient}/{timestamp}_{id}.json
Each message is one file, organized by recipient session type.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import get_brain_path

# ── Session type detection ────────────────────────────────────────

KNOWN_SESSION_TYPES = {
    "cowork",
    "claude_code",
    "windsurf",
    "cursor",
    "vscode",
    "claude_desktop",
    "unknown",
}


def detect_session_type() -> str:
    """Detect what kind of Claude surface is running this process.

    Uses environment variables and heuristics to determine whether
    we're in Cowork, Claude Code, Windsurf, Cursor, etc.

    Detection priority:
    1. Explicit override via NUCLEUS_SESSION_TYPE env var
    2. Cowork sandbox path detection (/sessions/ with mnt)
    3. IDE-specific env vars (Windsurf, Cursor, VS Code, Claude Desktop)
    4. Claude Code heuristics (MCP_* env vars, CLAUDE_* vars, process tree)
    5. Fallback to "unknown"
    """
    # Priority 1: Explicit override always wins
    explicit = os.environ.get("NUCLEUS_SESSION_TYPE", "").lower()
    if explicit in KNOWN_SESSION_TYPES:
        return explicit

    # Priority 2: Cowork sessions run in /sessions/ sandbox paths
    cwd = os.getcwd()
    if "/sessions/" in cwd and "mnt" in cwd:
        return "cowork"

    # Priority 3: IDE-specific detection (reuses existing Nucleus patterns)
    if os.environ.get("WINDSURF_SESSION"):
        return "windsurf"
    if os.environ.get("CURSOR_SESSION"):
        return "cursor"
    if os.environ.get("CLAUDE_DESKTOP"):
        return "claude_desktop"
    if os.environ.get("VSCODE_PID"):
        return "vscode"

    # Priority 4: Claude Code detection (multiple heuristics)
    # Direct env vars that Claude Code may set
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_CODE_SESSION"):
        return "claude_code"

    # Claude Code runs as an MCP client — check for MCP transport indicators
    # When Nucleus is launched as an MCP server by Claude Code, it's via stdio
    if os.environ.get("MCP_TRANSPORT") == "stdio":
        # If we're in stdio MCP mode and no IDE was detected, it's likely Claude Code
        return "claude_code"

    # Check if parent process looks like Claude Code (node-based CLI)
    try:
        ppid = os.getppid()
        cmdline_path = f"/proc/{ppid}/cmdline"
        if os.path.exists(cmdline_path):
            with open(cmdline_path, "r") as f:
                parent_cmd = f.read()
            if "claude" in parent_cmd.lower():
                return "claude_code"
    except Exception:
        pass

    # Check for Claude Code's config directory presence as a strong hint
    home = os.environ.get("HOME", "")
    if home:
        claude_config = os.path.join(home, ".claude")
        # If .claude dir exists AND we're not in any other detected IDE,
        # and we're running as a stdio MCP server, likely Claude Code
        if os.path.isdir(claude_config):
            # Additional check: are we running as an MCP server (not interactive)?
            import sys
            if not sys.stdin.isatty():
                return "claude_code"

    # Priority 5: Fallback
    return "unknown"


# ── Relay directory helpers ───────────────────────────────────────

def _get_relay_dir(recipient: Optional[str] = None) -> Path:
    """Get (and ensure) the relay directory.

    .brain/relay/          — root
    .brain/relay/cowork/   — messages for Cowork
    .brain/relay/claude_code/ — messages for Claude Code
    """
    base = get_brain_path() / "relay"
    if recipient:
        d = base / recipient
    else:
        d = base
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize_recipient(to: str) -> str:
    """Validate and normalize recipient name."""
    to = to.strip().lower().replace("-", "_").replace(" ", "_")
    if not to:
        raise ValueError("Recipient cannot be empty")
    # Allow any string but warn on unknown types
    return to


# ── Core relay operations ─────────────────────────────────────────

def relay_post(
    to: str,
    subject: str,
    body: str,
    priority: str = "normal",
    context: Optional[Dict[str, Any]] = None,
    sender: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a message to a target session type.

    Args:
        to: Recipient session type (e.g., "claude_code", "cowork")
        subject: Short subject line
        body: Full message body
        priority: "low", "normal", "high", "urgent"
        context: Optional structured context (file paths, task IDs, etc.)
        sender: Explicit sender identity. Required because the MCP server
                process can't distinguish which client is calling it.
                If omitted, falls back to detect_session_type() (unreliable
                when multiple clients share the same MCP server process).

    Returns:
        Dict with message_id, status, and delivery path.
    """
    to = _sanitize_recipient(to)
    sender = sender or detect_session_type()
    now = datetime.now(timezone.utc)
    msg_id = f"relay_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    message = {
        "id": msg_id,
        "from": sender,
        "to": to,
        "subject": subject,
        "body": body,
        "priority": priority,
        "context": context or {},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "read": False,
        "read_at": None,
        "read_by": None,
    }

    # Write to recipient's mailbox
    relay_dir = _get_relay_dir(to)
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{msg_id}.json"
    path = relay_dir / filename
    path.write_text(json.dumps(message, indent=2, default=str), encoding="utf-8")

    return {
        "sent": True,
        "message_id": msg_id,
        "from": sender,
        "to": to,
        "subject": subject,
        "priority": priority,
        "path": str(path.relative_to(get_brain_path())),
    }


def relay_inbox(
    unread_only: bool = True,
    limit: int = 20,
    recipient: Optional[str] = None,
) -> Dict[str, Any]:
    """Read messages addressed to the current session type.

    Args:
        unread_only: If True, only return unread messages.
        limit: Max messages to return (newest first).
        recipient: Override auto-detected session type.

    Returns:
        Dict with messages list and metadata.
    """
    me = recipient or detect_session_type()
    relay_dir = _get_relay_dir(me)

    messages = []
    for f in sorted(relay_dir.glob("*.json"), reverse=True):
        if len(messages) >= limit:
            break
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if unread_only and msg.get("read", False):
                continue
            msg["_file"] = f.name
            messages.append(msg)
        except Exception:
            continue

    return {
        "recipient": me,
        "messages": messages,
        "count": len(messages),
        "unread_only": unread_only,
    }


def relay_ack(message_id: str, recipient: Optional[str] = None) -> Dict[str, Any]:
    """Acknowledge / mark a message as read.

    Args:
        message_id: The relay message ID to acknowledge.
        recipient: Override auto-detected session type.

    Returns:
        Dict with acknowledgment status.
    """
    me = recipient or detect_session_type()
    relay_dir = _get_relay_dir(me)

    for f in relay_dir.glob("*.json"):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if msg.get("id") == message_id:
                msg["read"] = True
                msg["read_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                msg["read_by"] = me
                f.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")
                return {
                    "acknowledged": True,
                    "message_id": message_id,
                    "read_by": me,
                }
        except Exception:
            continue

    return {
        "acknowledged": False,
        "message_id": message_id,
        "error": f"Message not found in {me} inbox",
    }


def relay_status() -> Dict[str, Any]:
    """Get relay status across all session types.

    Shows pending/unread counts per recipient, recent activity,
    and detected session types with messages.
    """
    base = _get_relay_dir()
    status: Dict[str, Any] = {
        "current_session_type": detect_session_type(),
        "mailboxes": {},
        "total_messages": 0,
        "total_unread": 0,
    }

    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        recipient = d.name
        total = 0
        unread = 0
        latest = None

        for f in d.glob("*.json"):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
                total += 1
                if not msg.get("read", False):
                    unread += 1
                created = msg.get("created_at", "")
                if latest is None or created > latest:
                    latest = created
            except Exception:
                total += 1  # count but can't parse

        status["mailboxes"][recipient] = {
            "total": total,
            "unread": unread,
            "latest_message_at": latest,
        }
        status["total_messages"] += total
        status["total_unread"] += unread

    return status


def relay_clear(
    recipient: Optional[str] = None,
    older_than_hours: int = 168,  # 7 days default
) -> Dict[str, Any]:
    """Clean up old relay messages.

    Args:
        recipient: Target mailbox to clean (None = all).
        older_than_hours: Delete messages older than this (default 7 days).

    Returns:
        Dict with cleanup results.
    """
    base = _get_relay_dir()
    cutoff = datetime.now(timezone.utc).timestamp() - (older_than_hours * 3600)
    deleted = 0
    errors = 0

    dirs = [base / recipient] if recipient else [d for d in base.iterdir() if d.is_dir()]

    for d in dirs:
        for f in d.glob("*.json"):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
                created = msg.get("created_at", "")
                if created:
                    msg_time = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                    if msg_time < cutoff:
                        f.unlink()
                        deleted += 1
            except Exception:
                errors += 1

    return {
        "deleted": deleted,
        "errors": errors,
        "older_than_hours": older_than_hours,
    }
