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




# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .core import *
from .instrumentation import *
from .pending import *
from .briefing import *
from .daemon import *
