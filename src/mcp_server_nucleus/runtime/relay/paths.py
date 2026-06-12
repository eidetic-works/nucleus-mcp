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


# ── Relay directory helpers ───────────────────────────────────────

def _get_relay_dir(recipient: Optional[str] = None, force_fs: bool = False) -> Path:
    """Get (and ensure) the relay directory.

    .brain/relay/          — root
    .brain/relay/cowork/   — messages for Cowork
    .brain/relay/claude_code/ — messages for Claude Code

    PR-A v0.1 swap-point: HTTP-mode returns the Path object but does NOT
    create the directory (no local FS state needed in HTTP-only sessions).
    Callers that branch on is_http_mode() upstream are unaffected; callers
    that downstream-iterate the Path (.glob, etc.) will branch separately.

    force_fs=True (server-side self-recursion guard, see core.relay_post):
    the server IS the FS authority even when it runs with NUCLEUS_RELAY_URL
    set, so its write/iterate paths still need the directory created.
    """
    base = get_brain_path() / "relay"
    if recipient:
        d = base / recipient
    else:
        d = base
    # PR-A v0.1 swap-point: skip mkdir in HTTP-mode (no local FS dir needed).
    from ..relay_transport import is_http_mode
    if force_fs or not is_http_mode():
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


def _coerce_provider_to_role(to: str, from_session_id: Optional[str] = None) -> str:
    """Coerce legacy IDE provider targets (windsurf, antigravity) to roles if possible,
    or emit a warning."""
    known_providers = {"windsurf", "antigravity", "cursor", "vscode", "claude_desktop", "gemini_cli"}
    if to in known_providers:
        logger.warning(
            "relay_post: Targeted provider bucket %r directly. "
            "Callers must use generic roles (e.g. 'coordinator', 'worker', 'primary', 'secondary') "
            "per AGENTS.md. from_session_id=%r. "
            "Update sender config to pass role explicitly.",
            to,
            from_session_id or "<unknown>",
        )
    return to


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





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .core import *
from .instrumentation import *
from .pending import *
from .briefing import *
from .watcher import *
from .daemon import *
