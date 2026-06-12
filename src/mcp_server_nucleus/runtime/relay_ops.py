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


from .relay import session, paths, core, instrumentation, pending, briefing, watcher, daemon

# Update globals with all items including protected (_) attributes
globals().update({k: v for k, v in session.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in paths.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in core.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in instrumentation.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in pending.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in briefing.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in watcher.__dict__.items() if not k.startswith("__")})
globals().update({k: v for k, v in daemon.__dict__.items() if not k.startswith("__")})
