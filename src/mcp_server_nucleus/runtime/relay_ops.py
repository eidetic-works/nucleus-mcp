"""Cross-session relay for Cowork ↔ Claude Code communication.

Provides a file-based mailbox system where different Claude surfaces
(Cowork, Claude Code, Windsurf, Cursor, etc.) can exchange messages
through the shared .brain/ directory.

Storage: .brain/relay/{recipient}/{timestamp}_{id}.json
Each message is one file, organized by recipient session type.
"""
from __future__ import annotations

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
from typing import Any, Dict, List, Optional

from .common import get_brain_path
from .providers import coerce_to_tuple

logger = logging.getLogger("nucleus.relay")

_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")


def _is_shipped_artifact(ref: str) -> bool:
    """True if ref is a shipped object (commit, PR, path, etc.) — anything except a relay_id.

    Relay-of-relay is the theater loop the gate blocks: a message whose only
    artifact_refs are other relay_ids is convergence chatter, not work.
    """
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
    "unknown",
}


def _maybe_split_cc_role(detected: str) -> str:
    """Upgrade bare `claude_code` to `claude_code_main`/`claude_code_peer` per ADR-0010.

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
    """Detect what kind of Claude surface is running this process.

    Uses environment variables and heuristics to determine whether
    we're in Cowork, Claude Code, Windsurf, Cursor, etc. When CC_SESSION_ROLE
    is set to `main` or `peer`, a bare `claude_code` detection is upgraded
    to `claude_code_main` or `claude_code_peer` (Phase A three-surface routing).

    Detection priority:
    1. Explicit override via NUCLEUS_SESSION_TYPE env var
    2. Cowork sandbox path detection (/sessions/ with mnt)
    3. IDE-specific env vars (Windsurf, Cursor, VS Code, Claude Desktop)
    4. Claude Code heuristics (MCP_* env vars, CLAUDE_* vars, process tree)
    5. Fallback to "unknown"
    """
    return _maybe_split_cc_role(_detect_session_type_raw())


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
        from ..sessions.registry import find_session_in_ancestry
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


# ── Legacy bucket intercept (ADR-0010 / feedback_relay_post_to_field_uses_role_bucket) ──
#
# HARD RULE: relay_post `to:` must always use role-aware buckets
# (claude_code_main / claude_code_peer), never the bare legacy `claude_code`
# bucket. When a misconfigured caller (e.g., cc-tb) writes to "claude_code",
# this intercept coerces the target to "claude_code_main" and emits a low-sev
# WARNING so the coercion is observable — mirrors the R6.1-v2 sender-coercion
# pattern (lines ~374–383) for the same reason: substrate tolerance without
# silent drift.

_LEGACY_CC_BUCKET = "claude_code"
_CANONICAL_CC_BUCKET = "claude_code_main"


def _coerce_legacy_bucket_target(to: str, from_session_id: Optional[str] = None) -> str:
    """Coerce legacy `claude_code` bucket writes to `claude_code_main`.

    Inputs:
        to: sanitized (lowercased, underscored) recipient bucket name
        from_session_id: originating session ID for log context (optional)

    Logic:
        If `to == "claude_code"` (the legacy bucket), coerce to
        `claude_code_main`. This is the safe default per ADR-0010 § Decision:
        unset CC_SESSION_ROLE → main. Emits a WARNING so the coercion is
        observable in substrate logs.

    Returns:
        Coerced bucket name (or original if no coercion needed).
    """
    if to != _LEGACY_CC_BUCKET:
        return to

    coerced = _CANONICAL_CC_BUCKET
    logger.warning(
        "relay_post: legacy bucket %r coerced to %r. "
        "Callers must use role-aware bucket (claude_code_main / claude_code_peer) "
        "per ADR-0010. from_session_id=%r. "
        "Update sender config to pass to='claude_code_main' explicitly.",
        _LEGACY_CC_BUCKET,
        coerced,
        from_session_id or "<unknown>",
    )
    return coerced


def _parse_relay_message(path: Path) -> Dict[str, Any]:
    """Parse a relay message file and lazily coerce legacy identity."""
    msg = json.loads(path.read_text(encoding="utf-8"))
    
    # ADR-0005 §D5: Lazy coercion for legacy envelopes missing 'from_provider'
    if "from_provider" not in msg:
        sender = msg.get("from", "")
        role = msg.get("from_role", "")
        tup = coerce_to_tuple(sender, role)
        
        msg["from_role"] = tup["role"]
        msg["from_provider"] = tup["provider"]
        if not msg.get("from_session_id"):
            msg["from_session_id"] = tup["session_id"]
            
    return msg


def _iter_inbox_dirs(me: str) -> List[Path]:
    """Dirs to iterate when reading/acking for `me`.

    Dual-read rule (Phase A): `claude_code_main` dual-reads legacy `claude_code/`
    during the 2-week grace period. `claude_code_peer` does NOT dual-read legacy
    (prevents duplicate processing of omit-routed relays). All other recipients
    read only their own bucket.

    Note: under ADR-0010 fix-(a) semantics, `me == "claude_code"` is defensively
    unreachable — `_maybe_split_cc_role` upgrades bare → claude_code_main at
    detect time. This branch is retained only for callers that bypass detection.
    """
    own = _get_relay_dir(me)
    dirs = [own]
    if me == "claude_code_main":
        legacy = _get_relay_dir("claude_code")
        if legacy.exists() and legacy.resolve() != own.resolve():
            dirs.append(legacy)
    return dirs


# ── Core relay operations ─────────────────────────────────────────

def relay_post(
    to: str,
    subject: str,
    body: str,
    priority: str = "normal",
    context: Optional[Dict[str, Any]] = None,
    sender: Optional[str] = None,
    to_session_id: Optional[str] = None,
    from_session_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
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
                R6.1: when sender is None, raises ValueError by default.
                Set NUCLEUS_RELAY_INFER_SENDER=1 to restore the legacy
                detect_session_type() fallback (unreliable when multiple
                clients share one MCP server process — opt-in only).
        to_session_id: Optional session-ID filter. When set, only the matching
                client session will surface the message (others skip it).
                None = broadcast to all sessions of the recipient type.
        from_session_id: Optional originating session ID. Lets receivers tell
                live continuity from a stale queue.
        in_reply_to: Optional parent relay_id this message threads to.
                First-class envelope field — receivers read it off the envelope
                without parsing body JSON. Normalized on post; stored alongside
                from_session_id / to_session_id.

    Returns:
        Dict with message_id, status, and delivery path.
    """
    start_time = time.perf_counter()
    to = _sanitize_recipient(to)
    # Legacy-bucket intercept: coerce "claude_code" → "claude_code_main" before
    # any further processing. from_session_id may not be known yet (caller
    # passes it as a kwarg); we use what's available for log context only.
    to = _coerce_legacy_bucket_target(to, from_session_id=from_session_id)
    # R6.1 — provider-neutrality substrate: explicit sender is the default
    # contract. Legacy silent coercion is opt-in via env var so Gemini CLI,
    # Windsurf, Cursor, and other future clients must declare role explicitly
    # or consciously opt into inference.
    if sender is None:
        if os.environ.get("NUCLEUS_RELAY_INFER_SENDER") == "1":
            # R6.1-v2 (2026-04-24): the legacy fallback is known-unreliable
            # when multiple clients share one stdio pipe (antigravity
            # relay_20260424_053832_0fd9d451 was mis-attributed via this
            # exact path). Emit a WARNING so substrate-level mis-attribution
            # is audible in logs even on opt-in.
            caller = _caller_hint()
            sender = detect_session_type()
            logger.warning(
                "relay_post: sender coerced via detect_session_type() -> %r. "
                "NUCLEUS_RELAY_INFER_SENDER=1 is opt-in compat only; callers "
                "should pass sender= explicitly. Caller: %s",
                sender,
                caller,
            )
        else:
            raise ValueError(
                "relay_post: sender is required. Pass sender= explicitly "
                "(e.g. 'claude_code_main', 'claude_code_peer', 'cowork', "
                "'gemini_cli', 'windsurf'). Set NUCLEUS_RELAY_INFER_SENDER=1 "
                "to restore legacy detect_session_type() fallback."
            )
    now = datetime.now(timezone.utc)
    msg_id = f"relay_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    if os.environ.get("NUCLEUS_RELAY_STRICT") == "1":
        try:
            parsed_body = json.loads(body) if isinstance(body, str) else body
            refs = parsed_body.get("artifact_refs") if isinstance(parsed_body, dict) else None
        except (json.JSONDecodeError, TypeError):
            refs = None
        if not refs or not any(_is_shipped_artifact(r) for r in refs):
            return {
                "sent": False,
                "error": "gate_rejected",
                "reason": (
                    "NUCLEUS_RELAY_STRICT=1 requires body.artifact_refs to contain at least one "
                    "non-relay-id reference (commit SHA, PR #, or file path). "
                    "Unset the env var to restore default permissive behavior."
                ),
                "to": to,
                "subject": subject,
            }

    sender_tuple = coerce_to_tuple(sender)

    message = {
        "id": msg_id,
        "from": sender,
        "from_role": sender_tuple["role"],
        "from_provider": sender_tuple["provider"],
        "from_session_id": from_session_id or sender_tuple["session_id"],
        "to": to,
        "to_session_id": to_session_id,
        "in_reply_to": in_reply_to,
        "subject": subject,
        "body": body,
        "priority": priority,
        "context": context or {},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "read": False,
        "read_at": None,
        "read_by": None,
        # Phase A3: per-session ack tracker. Maps session_id → iso_ts of ack.
        # Shared buckets (multiple Cowork sessions, multiple CC-peer sessions)
        # need per-session unread to avoid one session hiding a relay from peers.
        # Legacy `read`/`read_at`/`read_by` remain for coarse-grained consumers
        # (relay_status, pending.json, morning brief) — they mean "any session
        # has acked this."
        "read_by_sessions": {},
    }

    # Metrics: count queued messages
    try:
        from .prometheus import inc_relay_message
        inc_relay_message("queued")
    except Exception:
        pass

    # Write to recipient's mailbox
    relay_dir = _get_relay_dir(to)
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{msg_id}.json"
    path = relay_dir / filename
    path.write_text(json.dumps(message, indent=2, default=str), encoding="utf-8")

    # Implicit ACK on Reply: mark parent message as read by the sender
    if in_reply_to:
        try:
            relay_ack(in_reply_to, recipient=sender, session_id=from_session_id)
        except Exception: pass

    # Coord-event capture (Phase B). Best-effort; never breaks relay flow.
    try:
        from . import coord_events as _ce
        _ce.emit(
            event_type="relay_fired",
            agent=sender or "unknown",
            session_id=from_session_id or "unknown",
            context_summary=f"relay to {to}: {subject[:80]}",
            chosen_option=msg_id,
            tags=[priority] if priority else [],
        )
    except Exception:
        pass

    # Marketplace reputation capture (Atom 1). Best-effort — never blocks relay.
    try:
        if sender:
            from .marketplace import ReputationSignals
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            ReputationSignals.record_interaction(
                to_address=f"{sender}@nucleus",
                from_address="relay_bus",
                latency_ms=elapsed_ms,
                success=True,
            )
    except Exception as _rep_exc:
        logger.warning("relay_post: reputation record skipped for %s: %s", sender, _rep_exc)

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
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read messages addressed to the current session type.

    Args:
        unread_only: If True, only return unread messages.
        limit: Max messages to return (newest first).
        recipient: Override auto-detected session type.
        session_id: Per-session unread filter (Phase A3). When provided AND
            `unread_only=True`, a message is considered unread if THIS session
            hasn't acked it — read_by_sessions[session_id] is absent. This
            prevents one session from hiding a relay from its peers in a
            shared bucket (e.g., two Cowork sessions). When omitted, legacy
            coarse-grained `read` flag is used (back-compat).

    Returns:
        Dict with messages list and metadata.
    """
    me = recipient or detect_session_type()
    dirs = _iter_inbox_dirs(me)

    # Collect candidate files across all dirs (main dual-reads legacy bucket)
    candidates: List[Path] = []
    for d in dirs:
        candidates.extend(d.glob("*.json"))
    candidates.sort(key=lambda p: p.name, reverse=True)

    messages = []
    for f in candidates:
        if len(messages) >= limit:
            break
        try:
            msg = _parse_relay_message(f)
            if unread_only:
                if session_id:
                    # Per-session filter: unread iff THIS session hasn't acked.
                    read_by_sessions = msg.get("read_by_sessions") or {}
                    if session_id in read_by_sessions:
                        continue
                else:
                    # Legacy coarse-grained filter.
                    if msg.get("read", False):
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
        "session_id": session_id,
    }


def relay_context_sync(
    recipient: Optional[str] = None,
    max_cycles: int = 3,
) -> Dict[str, Any]:
    """Checkpoint-optimized relay loader for session-start sync.
    
    Mitigates context window fragmentation as the org scales to 7+ agents by
    slicing full relay history down to a bounded context window.
    
    A 'cycle' is approximated by a calendar day of activity (YYYYMMDD) parsed
    from the relay message filename (e.g., 20260427_170505...).
    
    Args:
        recipient: Override auto-detected session type.
        max_cycles: Number of distinct activity cycles (days) to load history for.
        
    Returns:
        Dict with 'active_decisions' and 'recent_history' messages.
    """
    me = recipient or detect_session_type()
    dirs = _iter_inbox_dirs(me)

    # Collect candidate files across all dirs
    candidates: List[Path] = []
    for d in dirs:
        candidates.extend(d.glob("*.json"))
    candidates.sort(key=lambda p: p.name, reverse=True)

    active_decisions = []
    recent_history = []
    
    seen_cycles = set()

    for f in candidates:
        try:
            msg = _parse_relay_message(f)
            msg["_file"] = f.name
            
            # Identify active decisions (high signal, always load)
            subject = str(msg.get("subject", "")).lower()
            tags = msg.get("tags", [])
            body = msg.get("body", {})
            if isinstance(body, dict):
                tags.extend(body.get("tags", []))
            tags_lower = [str(t).lower() for t in tags]
            
            # Active decisions are typically unread directives or explicit decisions
            is_active_decision = (
                "decision" in subject or 
                "directive" in subject or 
                "decision" in tags_lower or 
                "directive" in tags_lower
            ) and not msg.get("read", False)
            
            # Determine cycle (date-based: YYYYMMDD from filename)
            # Standard relay filename: relay_YYYYMMDD_HHMMSS_id.json or YYYYMMDD_HHMMSS_...json
            parts = f.name.split("_")
            cycle_id = "unknown"
            for part in parts:
                if part.isdigit() and len(part) == 8:
                    cycle_id = part
                    break
            
            # Add to active decisions if flagged
            if is_active_decision:
                active_decisions.append(msg)
            
            # Add to recent history if within cycle limit
            if cycle_id not in seen_cycles:
                if len(seen_cycles) >= max_cycles and cycle_id != "unknown":
                    continue  # We hit the limit for known cycles
                if cycle_id != "unknown":
                    seen_cycles.add(cycle_id)
            
            if len(seen_cycles) <= max_cycles or cycle_id == "unknown":
                recent_history.append(msg)
            
        except Exception:
            continue

    return {
        "status": "success",
        "active_decisions": active_decisions,
        "recent_history": recent_history,
        "cycles_loaded": len(seen_cycles),
        "total_messages": len(active_decisions) + len(recent_history),
        "recipient": me,
    }


def relay_read(
    message_id: str,
    recipient: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a specific message and mark it as read.

    Args:
        message_id: The ID of the relay message to read.
        recipient: Override auto-detected session type.
        session_id: Per-session ack (Phase A3).
    """
    me = recipient or detect_session_type()

    for d in _iter_inbox_dirs(me):
        for f in d.glob("*.json"):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
                if msg.get("id") == message_id:
                    # Mark as read
                    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    msg["read"] = True
                    msg["read_at"] = now_iso
                    msg["read_by"] = me
                    if session_id:
                        read_by_sessions = msg.get("read_by_sessions") or {}
                        read_by_sessions[session_id] = now_iso
                        msg["read_by_sessions"] = read_by_sessions
                    
                    f.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")

                    # Project to engram
                    try:
                        from .relay_engram_projection import project_relay_to_engram
                        project_relay_to_engram(msg)
                    except Exception: pass

                    # Coord-event capture (Phase B receive-side). Closes ack-latency loop
                    # for cross-trio observability dashboard. Best-effort.
                    try:
                        from . import coord_events as _ce
                        _ce.emit(
                            event_type="relay_processed",
                            agent=me or "unknown",
                            session_id=session_id or "unknown",
                            context_summary=f"relay processed: {str(msg.get('subject',''))[:80]}",
                            chosen_option=message_id,
                            tags=["read_message"],
                        )
                    except Exception: pass

                    return {
                        "success": True,
                        "message": msg,
                        "acknowledged": True
                    }
            except Exception:
                continue

    return {"success": False, "error": f"Message {message_id} not found in {me} inbox"}


def relay_ack(
    message_id: str,
    recipient: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Acknowledge / mark a message as read.

    Args:
        message_id: The relay message ID to acknowledge.
        recipient: Override auto-detected session type.
        session_id: Per-session ack (Phase A3). When provided, records this
            session's ack in `read_by_sessions[session_id]` so peer sessions
            sharing the bucket still see the message as unread. The legacy
            coarse-grained `read`/`read_at`/`read_by` fields are always
            updated too, so `relay_status`, `pending.json`, and the morning
            brief continue to report "any-session acked" semantics.

    Returns:
        Dict with acknowledgment status.
    """
    me = recipient or detect_session_type()

    # Dual-read: main can ack messages that landed in legacy claude_code/ bucket
    for d in _iter_inbox_dirs(me):
        for f in d.glob("*.json"):
            try:
                msg = _parse_relay_message(f)
                if msg.get("id") == message_id:
                    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    msg["read"] = True
                    msg["read_at"] = now_iso
                    msg["read_by"] = me
                    if session_id:
                        read_by_sessions = msg.get("read_by_sessions") or {}
                        read_by_sessions[session_id] = now_iso
                        msg["read_by_sessions"] = read_by_sessions
                    f.write_text(json.dumps(msg, indent=2, default=str), encoding="utf-8")
                    # Metrics: count acked messages
                    try:
                        from .prometheus import inc_relay_message
                        inc_relay_message("acked")
                    except Exception:
                        pass
                    try:
                        from .relay_engram_projection import project_relay_to_engram
                        project_relay_to_engram(msg)
                    except Exception as exc:
                        logger.debug("relay engram projection skipped: %s", exc)

                    # Coord-event capture (Phase B receive-side). Best-effort.
                    try:
                        from . import coord_events as _ce
                        _ce.emit(
                            event_type="relay_processed",
                            agent=me or "unknown",
                            session_id=session_id or "unknown",
                            context_summary=f"relay processed: {str(msg.get('subject',''))[:80]}",
                            chosen_option=message_id,
                            tags=["relay_ack"],
                        )
                    except Exception: pass

                    return {
                        "acknowledged": True,
                        "message_id": message_id,
                        "read_by": me,
                        "session_id": session_id,
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
                msg = _parse_relay_message(f)
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
                msg = _parse_relay_message(f)
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


# ── Two-axis instrumentation (override rate + skip rate) ──────────
#
# Every /to-cowork or /to-cc invocation logs one line to event_log.jsonl
# regardless of whether the relay fired. Skip events are the input to the
# v2.2 auto-fire judge decision: "should the cold-start gate have let this
# through?" Override rate is read-time analytics:
#   count(fire WHERE match=cold-start AND priority=high
#                 AND not question-to-peer) / count(fire)
# Classifications are written to a sidecar so event_log.jsonl stays
# append-only and tail-friendly.

EVENT_LOG_NAME = "event_log.jsonl"
SKIP_CLASSIFICATIONS_NAME = "skip_classifications.jsonl"

VALID_LOG_EVENTS = {"fire", "skip"}
VALID_CLASSIFICATIONS = {"should_have_fired", "rightly_skipped"}


def _event_log_path() -> Path:
    return _get_relay_dir() / EVENT_LOG_NAME


def _skip_classifications_path() -> Path:
    return _get_relay_dir() / SKIP_CLASSIFICATIONS_NAME


def relay_log_event(
    event: str,
    side: str,
    subject: str,
    tags: Optional[List[str]] = None,
    match_reason: str = "",
    priority: str = "normal",
    message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one fire/skip event to .brain/relay/event_log.jsonl.

    Called by /to-cowork and /to-cc skills on both code paths:
    - Fire path (after relay_post succeeds): event=fire, message_id=<id>
    - Skip path (cold-start gate trips): event=skip, message_id=None

    Best-effort: caller should not surface failures to the user. If the
    log can't be written, the relay fire/skip itself still happened.
    """
    if event not in VALID_LOG_EVENTS:
        return {"logged": False, "error": f"event must be one of {VALID_LOG_EVENTS}"}

    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        "side": side,
        "subject": subject,
        "tags": tags or [],
        "match_reason": match_reason,
        "priority": priority,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
    }

    try:
        path = _event_log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return {"logged": True, "event": event, "path": str(path.relative_to(get_brain_path()))}
    except Exception as e:
        return {"logged": False, "error": str(e)}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of dicts, skipping malformed lines."""
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def relay_skip_review(limit: int = 20) -> Dict[str, Any]:
    """Surface the most recent unclassified skip events for human review.

    Joins event_log.jsonl (event=skip) against skip_classifications.jsonl
    (by ts+subject as composite key — skips have no message_id). Returns
    the most recent N skips lacking a classification.
    """
    skips = [e for e in _read_jsonl(_event_log_path()) if e.get("event") == "skip"]
    classifications = _read_jsonl(_skip_classifications_path())
    classified_keys = {(c.get("ts"), c.get("subject")) for c in classifications}

    unclassified = [
        s for s in skips if (s.get("ts"), s.get("subject")) not in classified_keys
    ]
    # Most recent first
    unclassified.sort(key=lambda s: s.get("ts", ""), reverse=True)
    return {
        "total_skips": len(skips),
        "total_classified": len(classified_keys),
        "unclassified_count": len(unclassified),
        "unclassified": unclassified[:limit],
    }


def relay_classify_skip(
    ts: str,
    subject: str,
    classification: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a human classification of a skip event.

    Writes to .brain/relay/skip_classifications.jsonl. Sidecar (not inline
    rewrite) keeps event_log.jsonl strictly append-only.
    """
    if classification not in VALID_CLASSIFICATIONS:
        return {
            "classified": False,
            "error": f"classification must be one of {VALID_CLASSIFICATIONS}",
        }

    entry = {
        "ts": ts,
        "subject": subject,
        "classification": classification,
        "note": note or "",
        "classified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        path = _skip_classifications_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return {"classified": True, "classification": classification}
    except Exception as e:
        return {"classified": False, "error": str(e)}


def relay_event_stats() -> Dict[str, Any]:
    """Compute fire/skip/override counts and rates from event_log.jsonl.

    Used by the v2.2 gate decision and weekly review dashboards.
    Override rate = fires that bypassed cold-start via priority=high
    without question-to-peer in tags.
    """
    events = _read_jsonl(_event_log_path())
    fires = [e for e in events if e.get("event") == "fire"]
    skips = [e for e in events if e.get("event") == "skip"]

    cold_start_fires = [
        e for e in fires
        if "cold-start default" in (e.get("match_reason") or "")
    ]
    overrides = [
        e for e in cold_start_fires
        if e.get("priority") == "high"
        and "question-to-peer" not in (e.get("tags") or [])
    ]

    total_fires = len(fires)
    total_skips = len(skips)
    total_attempts = total_fires + total_skips

    override_rate = (len(overrides) / total_fires) if total_fires else 0.0
    skip_rate = (total_skips / total_attempts) if total_attempts else 0.0

    return {
        "total_fires": total_fires,
        "total_skips": total_skips,
        "total_attempts": total_attempts,
        "override_count": len(overrides),
        "override_rate": round(override_rate, 4),
        "skip_rate": round(skip_rate, 4),
    }


# ── Pending consolidation (consumed by morning brief + session start) ─

def relay_consolidate_pending() -> Dict[str, Any]:
    """Write .brain/relay/pending.json with a summary of all unread messages.

    This file is the "you have mail" signal. It's designed to be read by:
    - Morning brief (section injection)
    - Session start hooks
    - Any polling consumer that can't receive async push

    The file is atomically written so readers never see a partial state.
    """
    base = _get_relay_dir()
    pending: Dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_unread": 0,
        "mailboxes": {},
        "urgent": [],
    }

    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        recipient = d.name
        unread_msgs = []

        for f in sorted(d.glob("*.json"), reverse=True):
            try:
                msg = _parse_relay_message(f)
                if not msg.get("read", False):
                    summary = {
                        "id": msg.get("id"),
                        "from": msg.get("from"),
                        "from_role": msg.get("from_role"),
                        "from_provider": msg.get("from_provider"),
                        "from_session_id": msg.get("from_session_id"),
                        "subject": msg.get("subject"),
                        "priority": msg.get("priority", "normal"),
                        "created_at": msg.get("created_at"),
                    }
                    unread_msgs.append(summary)
                    if msg.get("priority") in ("high", "urgent"):
                        pending["urgent"].append({
                            **summary,
                            "to": recipient,
                        })
            except Exception:
                continue

        if unread_msgs:
            pending["mailboxes"][recipient] = {
                "unread": len(unread_msgs),
                "messages": unread_msgs[:10],  # cap at 10 per mailbox
            }
            pending["total_unread"] += len(unread_msgs)

    # Atomic write
    pending_path = base / "pending.json"
    tmp_path = base / "pending.json.tmp"
    try:
        tmp_path.write_text(json.dumps(pending, indent=2, default=str), encoding="utf-8")
        os.replace(tmp_path, pending_path)
    except Exception as e:
        logger.error(f"Failed to write pending.json: {e}")

    return pending


def relay_read_pending() -> Dict[str, Any]:
    """Read the consolidated pending.json.

    Returns the pending summary if it exists, otherwise runs
    consolidation on-demand and returns fresh data.
    """
    pending_path = _get_relay_dir() / "pending.json"
    if pending_path.exists():
        try:
            data = json.loads(pending_path.read_text(encoding="utf-8"))
            # If stale (older than 60s), refresh
            updated = data.get("updated_at", "")
            if updated:
                age = (datetime.now(timezone.utc) -
                       datetime.fromisoformat(updated.replace("Z", "+00:00"))).total_seconds()
                if age < 60:
                    return data
        except Exception:
            pass
    # Stale or missing — refresh
    return relay_consolidate_pending()


# ── Morning brief integration ─────────────────────────────────────

def get_relay_brief_section() -> Dict[str, Any]:
    """Generate the relay section for the morning brief.

    Called by morning_brief_ops to inject relay status into the daily brief.
    Returns a dict suitable for inclusion in the brief sections.
    """
    pending = relay_read_pending()

    if pending["total_unread"] == 0:
        return {
            "has_messages": False,
            "summary": "No unread relay messages.",
        }

    lines = []
    for recipient, info in pending["mailboxes"].items():
        lines.append(f"  📬 {recipient}: {info['unread']} unread")
        for msg in info["messages"][:3]:
            priority_icon = "🔴" if msg["priority"] in ("high", "urgent") else "⚪"
            lines.append(f"    {priority_icon} [{msg['from']}] {msg['subject']}")

    return {
        "has_messages": True,
        "total_unread": pending["total_unread"],
        "urgent_count": len(pending.get("urgent", [])),
        "summary": "\n".join(lines),
        "urgent": pending.get("urgent", []),
    }


# ── File watcher for relay push ───────────────────────────────────

def _auto_dispatch_relay(msg: Dict[str, Any], recipient: str, brain_path: Optional[Path] = None):
    """Autonomous delegation: create a task from an urgent/high relay.

    When a relay arrives with priority=high or priority=urgent, this
    function creates a Nucleus task so it enters the orchestration
    pipeline. The task can then be picked up by:
    - Claude Code via get_next / autopilot
    - The TB driver for autonomous execution
    - Any agent checking the task backlog

    This is the key bridge: Cowork posts an urgent relay → watcher
    catches it → task is auto-created → Claude Code picks it up
    without the founder routing manually.

    Safety:
    - Dedup: won't create a task if one already exists for this relay ID
    - Priority mapping: urgent→P1, high→P2
    - Source tracking: task.source = "relay_dispatch:{message_id}"

    Args:
        brain_path: Explicit brain path. Required when called from watcher
                    thread where get_brain_path() may resolve to wrong dir.
    """
    # Ensure downstream get_brain_path() resolves correctly in any thread.
    # The watcher knows the correct brain_path; propagate it via env so
    # _add_task → get_brain_path() picks it up without signature changes.
    _prev_brain = os.environ.get("NUCLEUS_BRAIN_PATH")
    if brain_path:
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_path)

    try:
        return _auto_dispatch_relay_inner(msg, recipient)
    finally:
        # Restore previous env state
        if brain_path:
            if _prev_brain is not None:
                os.environ["NUCLEUS_BRAIN_PATH"] = _prev_brain
            else:
                os.environ.pop("NUCLEUS_BRAIN_PATH", None)


def _auto_dispatch_relay_inner(msg: Dict[str, Any], recipient: str):
    """Inner implementation of auto-dispatch (runs with correct brain_path)."""
    message_id = msg.get("id", "unknown")
    sender = msg.get("from", "unknown")
    subject = msg.get("subject", "(no subject)")
    body = msg.get("body", "")
    priority = msg.get("priority", "normal")

    # Map relay priority to task priority
    task_priority = 1 if priority == "urgent" else 2

    # Dedup: check if task already exists for this relay
    source_key = f"relay_dispatch:{message_id}"
    try:
        from .db import get_storage_backend
        storage = get_storage_backend(get_brain_path())
        existing = storage.list_tasks()
        for t in existing:
            if t.get("source", "").startswith(source_key):
                logger.debug(f"Relay task already exists for {message_id}, skipping")
                return
    except Exception:
        pass  # Fail open — create task even if dedup check fails

    # Build task description from relay content
    # Truncate body to keep task description manageable
    body_preview = body[:200] + "..." if len(body) > 200 else body
    task_desc = (
        f"[relay:{sender}→{recipient}] {subject}\n"
        f"{body_preview}"
    )

    try:
        from .task_ops import _add_task
        result = _add_task(
            description=task_desc,
            priority=task_priority,
            source=source_key,
        )
        if result.get("success"):
            task_id = result.get("task_id", "?")
            logger.info(
                f"📬→📋 Auto-dispatched relay as task {task_id} "
                f"(P{task_priority}, from {sender})"
            )

            # IDE-side nudge routing is the receiving session's responsibility,
            # not the dispatcher's. The nucleus-bridge VS Code extension's
            # handleRelayMessage + dispatchRelay (PR #195 W1-W5 dispatch arc)
            # handle thread-aware injection on the receiving side, including
            # to_session_id targeting + panel-open/closed detection.
            #
            # The legacy keystroke + URGENT_NUDGE.md fallback path that used to
            # live here was removed 2026-04-30 per windsurf
            # relay_20260430_012851_ab1b002f. Two reasons:
            #   1. It bypassed the bridge extension entirely, so to_session_id
            #      relays landed as stray editor tabs instead of the active
            #      chat thread.
            #   2. Hardcoded subprocess calls to ["antigravity", ...] and
            #      ["windsurf", ...] failed the 5-axis primitive-gate
            #      (any-OS / any-agent) per feedback_nucleus_primitive_gate.md.

            # Emit dispatch event for observability
            try:
                from .event_ops import _emit_event
                _emit_event(
                    event_type="relay_auto_dispatched",
                    emitter="relay_watcher",
                    data={
                        "message_id": message_id,
                        "task_id": task_id,
                        "from": sender,
                        "to": recipient,
                        "subject": subject,
                        "priority": priority,
                        "task_priority": task_priority,
                    },
                    description=f"Relay from {sender} auto-dispatched as task {task_id}",
                )
            except Exception:
                pass
        else:
            logger.warning(f"Auto-dispatch task creation failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Auto-dispatch failed for relay {message_id}: {e}")


_relay_observer = None
_relay_observer_lock = threading.Lock()

# ── Poll daemon registry (relay_poll_start / stop / status) ──────────────────
# Keyed by recipient bucket name.  Each value is a _PollDaemon instance.
_poll_daemons: Dict[str, "_PollDaemon"] = {}
_poll_daemons_lock = threading.Lock()

_POLL_SIGNAL_FILENAME = "POLL_SIGNAL.json"


class _PollDaemon:
    """Background thread that polls a relay bucket and writes a signal file.

    Spawned by relay_poll_start(); stopped by relay_poll_stop().
    Writes .brain/relay/<recipient>/POLL_SIGNAL.json on every scan cycle
    so Cascade threads can call relay_poll_status() without any blocking.

    Does NOT ack or move files — relay_inbox / relay_ack own that.
    """

    def __init__(
        self,
        recipient: str,
        interval_s: int = 10,
        session_id: Optional[str] = None,
    ):
        self.recipient = recipient
        self.interval_s = interval_s
        self.session_id = session_id
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"relay-poll-{recipient}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=max(self.interval_s + 2, 5))

    def _signal_path(self) -> Path:
        return _get_relay_dir(self.recipient) / _POLL_SIGNAL_FILENAME

    def _scan(self) -> List[Dict[str, Any]]:
        """Return list of pending (unread) relay summaries for recipient."""
        relay_dir = _get_relay_dir(self.recipient)
        pending = []
        try:
            for fpath in sorted(relay_dir.glob("*.json")):
                if fpath.name == _POLL_SIGNAL_FILENAME:
                    continue
                if fpath.parent.name in ("processed", "acks"):
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if data.get("read") is True:
                    continue
                # Optional session_id filter
                if self.session_id:
                    ts = data.get("to_session_id")
                    if ts and ts != self.session_id:
                        continue
                pending.append({
                    "relay_id": data.get("id", fpath.stem),
                    "subject": data.get("subject", ""),
                    "from": data.get("from", ""),
                    "priority": data.get("priority", "normal"),
                    "in_reply_to": data.get("in_reply_to"),
                })
        except Exception as exc:
            logger.debug(f"relay_poll scan error for {self.recipient}: {exc}")
        return pending

    def _write_signal(self, pending: List[Dict[str, Any]]) -> None:
        signal = {
            "running": True,
            "recipient": self.recipient,
            "interval_s": self.interval_s,
            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pending": pending,
            "pending_count": len(pending),
        }
        try:
            path = self._signal_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(signal, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug(f"relay_poll signal write failed: {exc}")

    def _run(self) -> None:
        logger.info(f"relay_poll daemon started for bucket '{self.recipient}' (interval={self.interval_s}s)")
        while not self._stop_event.is_set():
            pending = self._scan()
            self._write_signal(pending)
            self._stop_event.wait(timeout=self.interval_s)
        # Mark signal file as stopped on clean exit
        try:
            path = self._signal_path()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                data["running"] = False
                data["stopped_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        logger.info(f"relay_poll daemon stopped for bucket '{self.recipient}'")


class RelayWatchHandler:
    """Watches .brain/relay/ for new message files.

    When a new JSON file appears in any recipient's mailbox:
    1. Consolidates pending.json (atomic)
    2. Emits a relay_message_received event (feeds engram hooks)
    3. Logs the arrival

    Since Claude Code can't receive async push mid-turn, pending.json
    is the signal — the next session start or morning brief reads it.
    """

    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.relay_dir = brain_path / "relay"
        self._seen_files: set = set()
        self._debounce_seconds = 2.0
        self._last_consolidate = 0.0

        # Snapshot existing files so we only trigger on genuinely new ones
        for d in self.relay_dir.iterdir():
            if d.is_dir():
                for f in d.glob("*.json"):
                    self._seen_files.add(str(f))

    def on_created(self, event):
        """Handle new file creation in relay directory."""
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".json") or src.endswith("pending.json") or src.endswith(".tmp"):
            return
        if src in self._seen_files:
            return
        self._seen_files.add(src)
        self._on_new_relay_message(Path(src))

    def on_modified(self, event):
        """Also catch modifications (some editors create then write)."""
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".json") or src.endswith("pending.json") or src.endswith(".tmp"):
            return
        # Only process if not yet seen (new file written in two steps)
        if src not in self._seen_files:
            self._seen_files.add(src)
            self._on_new_relay_message(Path(src))

    def _on_new_relay_message(self, path: Path):
        """Process a newly arrived relay message."""
        import time
        now = time.time()

        # Debounce consolidation
        if now - self._last_consolidate < self._debounce_seconds:
            return
        self._last_consolidate = now

        try:
            msg = _parse_relay_message(path)
            sender = msg.get("from", "unknown")
            recipient = path.parent.name
            subject = msg.get("subject", "(no subject)")
            priority = msg.get("priority", "normal")

            logger.info(
                f"📬 New relay: [{sender} → {recipient}] "
                f"{subject} (priority={priority})"
            )

            # Consolidate pending.json
            relay_consolidate_pending()

            # Emit event for the hook system
            try:
                from .event_ops import _emit_event
                _emit_event(
                    event_type="relay_message_received",
                    emitter="relay_watcher",
                    data={
                        "message_id": msg.get("id"),
                        "from": sender,
                        "to": recipient,
                        "subject": subject,
                        "priority": priority,
                    },
                    description=f"Relay message from {sender} to {recipient}: {subject}",
                )
            except Exception:
                pass  # Never let event emission break the watcher

            # Autonomous delegation: urgent/high relays auto-create tasks
            if priority in ("high", "urgent"):
                try:
                    _auto_dispatch_relay(msg, recipient, brain_path=self.brain_path)
                except Exception as e:
                    logger.warning(f"Auto-dispatch failed for relay {msg.get('id', '?')}: {e}")

        except Exception as e:
            logger.error(f"Error processing relay message {path}: {e}")


def start_relay_watcher(brain_path: Optional[Path] = None) -> Dict[str, Any]:
    """Start watching .brain/relay/ for new messages.

    Uses watchdog if available, otherwise returns gracefully.
    Called during MCP server initialization.
    """
    global _relay_observer

    if brain_path is None:
        brain_path = get_brain_path()

    relay_dir = brain_path / "relay"
    relay_dir.mkdir(parents=True, exist_ok=True)

    with _relay_observer_lock:
        if _relay_observer is not None:
            return {"status": "already_running"}

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            handler = RelayWatchHandler(brain_path)

            class WatchdogRelay(FileSystemEventHandler):
                def on_created(self, event):
                    handler.on_created(event)
                def on_modified(self, event):
                    handler.on_modified(event)

            _relay_observer = Observer()
            _relay_observer.schedule(WatchdogRelay(), str(relay_dir), recursive=True)
            _relay_observer.daemon = True
            _relay_observer.start()

            logger.info(f"📬 Relay watcher started for {relay_dir}")

            return {
                "status": "started",
                "watching": str(relay_dir),
                "handler": "watchdog",
            }

        except ImportError:
            logger.info("Relay watcher: watchdog not installed, skipping")
            return {
                "status": "skipped",
                "reason": "watchdog not installed",
                "hint": "pip install watchdog",
            }
        except Exception as e:
            logger.error(f"Relay watcher failed to start: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


def stop_relay_watcher() -> Dict[str, Any]:
    """Stop the relay file watcher."""
    global _relay_observer

    with _relay_observer_lock:
        if _relay_observer is not None:
            try:
                _relay_observer.stop()
                _relay_observer.join(timeout=5)
            except Exception:
                pass
            _relay_observer = None
            return {"status": "stopped"}
        return {"status": "not_running"}


def relay_archive(
    recipient: Optional[str] = None,
    max_age_days: int = 7,
    max_count: int = 100,
    brain_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Archive relay messages beyond a retention window.

    Implements the relay-inbox retention policy from the agent org expansion
    plan: "keep last ``max_count`` or last ``max_age_days``, whichever is
    smaller; old relays archived to ``.brain/relay/<agent>/archive/<date>.jsonl``."

    The archive format is newline-delimited JSON (one relay per line), grouped
    by the relay's ``created_at`` date.  Original ``.json`` files are deleted
    after successful archival (unless ``dry_run=True``).

    Args:
        recipient: Relay bucket to archive (e.g. ``claude_code_main``).
            Auto-detected if omitted.
        max_age_days: Messages older than this many days are eligible for
            archival.  Default 7.
        max_count: Maximum number of messages to retain regardless of age.
            Default 100.
        brain_path: Override brain directory.
        dry_run: If True, compute what would be archived but don't move
            anything.

    Returns:
        Dict with ``archived``, ``kept``, ``archive_paths``, ``dry_run``.
    """
    brain = brain_path or get_brain_path()
    me = recipient or detect_session_type()
    bucket = brain / "relay" / me

    if not bucket.is_dir():
        return {
            "recipient": me,
            "archived": 0,
            "kept": 0,
            "archive_paths": [],
            "dry_run": dry_run,
            "error": f"Bucket directory not found: {bucket}",
        }

    # Collect all relay JSON files in the bucket (exclude archive subdir).
    relay_files: List[Path] = sorted(
        (f for f in bucket.glob("*.json") if f.is_file()),
        key=lambda p: p.name,
    )

    if not relay_files:
        return {
            "recipient": me,
            "archived": 0,
            "kept": len(relay_files),
            "archive_paths": [],
            "dry_run": dry_run,
        }

    # Parse created_at from each file to determine age.
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - (max_age_days * 86400)

    # Build list of (file, created_at_ts, relay_data) — newest last.
    entries: List[tuple] = []
    for f in relay_files:
        try:
            data = json.loads(f.read_text())
            created_str = data.get("created_at", "")
            if created_str:
                # Parse ISO timestamp — handle both Z and +00:00 suffixes.
                ts_str = created_str.replace("Z", "+00:00")
                try:
                    ts = datetime.fromisoformat(ts_str).timestamp()
                except (ValueError, TypeError):
                    ts = f.stat().st_mtime
            else:
                ts = f.stat().st_mtime
            entries.append((f, ts, data))
        except Exception:
            # Unparseable files are kept (not archived).
            continue

    # Sort newest-first for the keep/archive split.
    entries.sort(key=lambda e: e[1], reverse=True)

    # Determine which entries to archive:
    # Keep the newest ``max_count`` entries AND anything within ``max_age_days``.
    # Archive = entries that are BOTH beyond max_count AND older than cutoff.
    to_archive: List[tuple] = []
    to_keep: List[tuple] = []

    for idx, entry in enumerate(entries):
        _f, ts, _data = entry
        within_count = idx < max_count
        within_age = ts >= cutoff
        if within_count or within_age:
            to_keep.append(entry)
        else:
            to_archive.append(entry)

    if not to_archive:
        return {
            "recipient": me,
            "archived": 0,
            "kept": len(to_keep),
            "archive_paths": [],
            "dry_run": dry_run,
        }

    if dry_run:
        return {
            "recipient": me,
            "archived": len(to_archive),
            "kept": len(to_keep),
            "archive_paths": [],
            "dry_run": True,
        }

    # Group archived entries by date for JSONL output.
    archive_dir = bucket / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    by_date: Dict[str, List[dict]] = {}
    for _f, ts, data in to_archive:
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        by_date.setdefault(date_str, []).append(data)

    archive_paths: List[str] = []
    for date_str, relays in sorted(by_date.items()):
        archive_file = archive_dir / f"{date_str}.jsonl"
        # Append to existing archive for the same date (idempotent across runs).
        with archive_file.open("a") as fh:
            for relay in relays:
                fh.write(json.dumps(relay, default=str) + "\n")
        archive_paths.append(str(archive_file))

    # Delete originals after successful archival.
    deleted = 0
    for f, _ts, _data in to_archive:
        try:
            f.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning(f"Failed to delete archived relay {f.name}: {exc}")

    return {
        "recipient": me,
        "archived": deleted,
        "kept": len(to_keep),
        "archive_paths": sorted(set(archive_paths)),
        "dry_run": False,
    }


def auto_start_relay_watcher(brain_path: Optional[Path] = None):
    """Auto-start relay watcher during MCP server init.

    Called from server.py or __init__.py during startup.
    Always-on — doesn't require sync.enabled config.
    """
    try:
        start_relay_watcher(brain_path)
    except Exception as e:
        logger.debug(f"Relay watcher auto-start failed (non-critical): {e}")


def relay_poll_start(
    recipient: str,
    interval_s: int = 10,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Start an autonomous background poll daemon for a relay bucket.

    The daemon scans `recipient`'s inbox every `interval_s` seconds and
    writes `.brain/relay/<recipient>/POLL_SIGNAL.json` with pending relay
    summaries.  Cascade threads call relay_poll_status() at turn start
    (instant, non-blocking) to check for new tasks — no paste, no VSIX
    injection needed.

    Idempotent: calling again while running returns already_running status.

    Args:
        recipient:   Relay bucket to watch (e.g. 'windsurf', 'claude_code_main').
        interval_s:  Scan frequency in seconds. Default 10.
        session_id:  If set, only surface relays addressed to this session.

    Returns:
        {status: 'started'|'already_running', recipient, interval_s}
    """
    with _poll_daemons_lock:
        existing = _poll_daemons.get(recipient)
        if existing is not None and existing._thread.is_alive():
            return {
                "status": "already_running",
                "recipient": recipient,
                "interval_s": existing.interval_s,
            }
        daemon = _PollDaemon(recipient=recipient, interval_s=interval_s, session_id=session_id)
        daemon.start()
        _poll_daemons[recipient] = daemon
        logger.info(f"relay_poll_start: daemon started for '{recipient}' interval={interval_s}s")
        return {
            "status": "started",
            "recipient": recipient,
            "interval_s": interval_s,
            "session_id": session_id,
            "signal_file": str(daemon._signal_path()),
        }


def relay_poll_stop(recipient: str) -> Dict[str, Any]:
    """Stop the poll daemon for a relay bucket.

    Args:
        recipient: Relay bucket name whose daemon to stop.

    Returns:
        {status: 'stopped'|'not_running', recipient}
    """
    with _poll_daemons_lock:
        daemon = _poll_daemons.pop(recipient, None)
    if daemon is None:
        return {"status": "not_running", "recipient": recipient}
    daemon.stop()
    return {"status": "stopped", "recipient": recipient}


def relay_poll_status(recipient: str) -> Dict[str, Any]:
    """Read the latest poll signal for a relay bucket (instant, non-blocking).

    Call this at the start of every turn to check for pending relays.
    If pending is non-empty, call relay_inbox to read the full messages.

    Args:
        recipient: Relay bucket to check (e.g. 'windsurf').

    Returns:
        {running: bool, pending: [{relay_id, subject, from, priority}], checked_at, pending_count}
        If daemon not started: {running: false, pending: [], hint: '...'}
    """
    with _poll_daemons_lock:
        daemon = _poll_daemons.get(recipient)
    running = daemon is not None and daemon._thread.is_alive()

    signal_path = _get_relay_dir(recipient) / _POLL_SIGNAL_FILENAME
    if signal_path.exists():
        try:
            data = json.loads(signal_path.read_text(encoding="utf-8"))
            data["running"] = running
            return data
        except Exception:
            pass

    return {
        "running": running,
        "recipient": recipient,
        "pending": [],
        "pending_count": 0,
        "checked_at": None,
        "hint": "Call relay_poll_start(recipient) once per session to begin autonomous polling.",
    }


def relay_wait(
    in_reply_to: str,
    recipient: str,
    timeout_s: int = 60,
    poll_interval_s: int = 5,
) -> Dict[str, Any]:
    """Poll recipient's inbox until a reply to `in_reply_to` arrives.

    Blocks synchronously for up to `timeout_s` seconds, polling every
    `poll_interval_s` seconds. Intended for cross-thread / cross-agent
    tandem coordination where one agent posts a relay and needs to wait
    for the other agent's reply before proceeding.

    Keep `timeout_s` short (30-60s) when called via MCP to avoid blocking
    the connection. Callers can retry on timed_out=True.

    Args:
        in_reply_to: The relay_id this function waits for a reply to.
        recipient:   The bucket to scan (e.g. 'windsurf', 'claude_code_main').
        timeout_s:   Max seconds to wait before returning timed_out=True.
        poll_interval_s: Seconds between inbox scans.

    Returns:
        {found: True,  relay_id: str, subject: str, waited_s: int}
        {found: False, timed_out: True, waited_s: int}
    """
    import time

    relay_dir = _get_relay_dir(recipient)
    deadline = time.monotonic() + timeout_s
    waited = 0

    while True:
        try:
            for fpath in sorted(relay_dir.glob("*.json")):
                if fpath.parent.name in ("processed", "acks"):
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if data.get("in_reply_to") == in_reply_to:
                    return {
                        "found": True,
                        "relay_id": data.get("id", fpath.stem),
                        "subject": data.get("subject", ""),
                        "from": data.get("from", ""),
                        "waited_s": waited,
                    }
        except Exception as exc:
            logger.debug(f"relay_wait: scan error: {exc}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"found": False, "timed_out": True, "waited_s": waited}

        sleep_for = min(poll_interval_s, remaining)
        time.sleep(sleep_for)
        waited += int(sleep_for)


def relay_listen(
    recipient: str,
    window_s: int = 60,
    poll_s: int = 5,
    in_reply_to: Optional[str] = None,
    known_ids: Optional[List[str]] = None,
    attempt: int = 1,
) -> Dict[str, Any]:
    """Block at the end of a turn waiting for the next inbound relay.

    Unlike relay_wait (which waits for a reply to a *specific* relay_id),
    relay_listen waits for *any* new relay that wasn't there when called.
    This is the "end-of-turn wait" primitive for the autonomous ping-pong loop:

        Agent A does work → relay_post to B → relay_listen(window_s=60)
        → when B's reply lands, A's next turn starts with the relay in hand.

    The function NEVER raises on timeout — it returns
    {found: False, call_again: True, known_ids: [...]} so the caller can
    retry in the next turn, incrementing attempt each time.
    Adaptive interval: actual poll frequency = min(poll_s * attempt, 30s)
    so long-running tasks get progressively gentler polling.

    Args:
        recipient:    Bucket to watch (e.g. 'windsurf').
        window_s:     Seconds to hold the connection open this call. Default 60.
                      Keep <=90s to avoid MCP connection timeouts.
                      Retry with call_again=True — relay_listen is stateless across calls.
        poll_s:       Base poll interval in seconds. Default 5.
        in_reply_to:  Optional relay_id to filter — only surface replies to this.
                      Omit to catch any new relay in the bucket.
        known_ids:    List of relay IDs already seen (from a prior call's response).
                      Pass this back on retry so arrivals during the gap aren't missed.
        attempt:      Retry count (1-based). Increases poll interval adaptively.
                      Pass attempt=next_attempt from the previous response on retry.

    Returns:
        Found:   {found: True,  relay: {relay_id, subject, from, priority, in_reply_to},
                  waited_s: int, recipient: str}
        Timeout: {found: False, call_again: True, waited_s: int, recipient: str,
                  known_ids: [str, ...], next_attempt: int, next_poll_s: int,
                  hint: "call relay_listen again with known_ids=... attempt=..."}
    """
    effective_poll = min(poll_s * max(attempt, 1), 30)
    relay_dir = _get_relay_dir(recipient)

    # Snapshot existing IDs so we only surface truly new arrivals
    seen: set = set(known_ids or [])
    if not seen:
        try:
            for fpath in relay_dir.glob("*.json"):
                if fpath.name == _POLL_SIGNAL_FILENAME:
                    continue
                if fpath.parent.name in ("processed", "acks"):
                    continue
                seen.add(fpath.stem)
        except Exception:
            pass

    deadline = time.monotonic() + window_s
    waited = 0

    while True:
        try:
            for fpath in sorted(relay_dir.glob("*.json")):
                if fpath.name == _POLL_SIGNAL_FILENAME:
                    continue
                if fpath.parent.name in ("processed", "acks"):
                    continue
                stem = fpath.stem
                if stem in seen:
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except Exception:
                    seen.add(stem)
                    continue
                if data.get("read") is True:
                    seen.add(stem)
                    continue
                # Filter by in_reply_to if specified
                if in_reply_to and data.get("in_reply_to") != in_reply_to:
                    seen.add(stem)
                    continue
                return {
                    "found": True,
                    "relay": {
                        "relay_id": data.get("id", stem),
                        "subject": data.get("subject", ""),
                        "from": data.get("from", ""),
                        "priority": data.get("priority", "normal"),
                        "in_reply_to": data.get("in_reply_to"),
                        "context": data.get("context", {}),
                        "is_convergence": bool(data.get("context", {}).get("convergence")),
                    },
                    "waited_s": waited,
                    "recipient": recipient,
                }
        except Exception as exc:
            logger.debug(f"relay_listen: scan error: {exc}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {
                "found": False,
                "call_again": True,
                "waited_s": waited,
                "recipient": recipient,
                "known_ids": list(seen),
                "next_attempt": attempt + 1,
                "next_poll_s": min(effective_poll * 2, 30),
                "hint": (
                    f"No new relay in {window_s}s. Call relay_listen again with "
                    f"known_ids=<this response's known_ids> attempt={attempt + 1} "
                    f"to continue waiting without missing arrivals."
                ),
            }

        sleep_for = min(effective_poll, remaining)
        time.sleep(sleep_for)
        waited += int(sleep_for)
