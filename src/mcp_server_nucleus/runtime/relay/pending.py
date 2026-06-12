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


# ── Pending consolidation (consumed by morning brief + session start) ─

def relay_consolidate_pending() -> Dict[str, Any]:
    """Write .brain/relay/pending.json with a summary of all unread messages.

    This file is the "you have mail" signal. It's designed to be read by:
    - Morning brief (section injection)
    - Session start hooks
    - Any polling consumer that can't receive async push

    The file is atomically written so readers never see a partial state.
    """
    # PR-A swap-point — DECIDED Mac-local in v0.2 (Seq-2 GAP-3 close-out):
    # pending.json stays an FS-only convenience artifact. Cloud sessions
    # poll GET /relay/{role} directly, which replaces the "you have mail"
    # role pending.json fulfilled; an HTTP fan-out here would duplicate
    # relay_status. Per spec §"Swap points": "http_mode: skip body —
    # pending.json is a Mac-local convenience artifact; cloud sessions
    # don't need it." This is the settled shape, not a v0.1 stopgap.
    from ..relay_transport import is_http_mode
    if is_http_mode():
        return {
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_unread": 0,
            "mailboxes": {},
            "urgent": [],
            "transport": "http",
            "note": "pending.json is FS-only; cloud sessions use direct HTTP polling",
        }

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





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .core import *
from .instrumentation import *
from .briefing import *
from .watcher import *
from .daemon import *
