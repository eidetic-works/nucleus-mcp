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





# Export local functions
__all__ = [k for k in list(globals().keys()) if not k.startswith('__')]

# Circular wildcard imports at the bottom to avoid deadlocks
from .session import *
from .paths import *
from .core import *
from .instrumentation import *
from .pending import *
from .watcher import *
from .daemon import *
