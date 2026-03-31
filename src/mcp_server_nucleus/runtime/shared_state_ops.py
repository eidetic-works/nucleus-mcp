"""Shared state operations for multi-agent brain sync.

Provides read/write/list for .brain/shared/{key}.json files.
Any connected agent can share context through these keys.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .common import get_brain_path


def _get_shared_dir() -> Path:
    """Get (and ensure) the .brain/shared/ directory."""
    shared = get_brain_path() / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    return shared


def _sanitize_key(key: str) -> str:
    """Sanitize key to prevent path traversal."""
    if not key or not key.strip():
        raise ValueError(f"Invalid key: {key!r}")
    # Strip path separators and dots that could escape the directory
    sanitized = key.replace("/", "_").replace("\\", "_").replace("..", "_")
    sanitized = sanitized.rstrip(".")
    if not sanitized or sanitized.startswith("."):
        raise ValueError(f"Invalid key: {key!r}")
    return sanitized


def brain_sync_read(key: str) -> Dict[str, Any]:
    """Read shared state by key."""
    sanitized = _sanitize_key(key)
    path = _get_shared_dir() / f"{sanitized}.json"
    if not path.exists():
        return {"found": False, "key": key}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"found": True, "key": key, **data}


def brain_sync_write(key: str, value: Any, agent_id: str = "") -> Dict[str, Any]:
    """Write shared state by key with timestamp and agent_id."""
    sanitized = _sanitize_key(key)
    path = _get_shared_dir() / f"{sanitized}.json"

    if not agent_id:
        try:
            from .sync_ops import get_current_agent
            agent_id = get_current_agent() or "unknown"
        except Exception:
            agent_id = "unknown"

    data = {
        "key": key,
        "value": value,
        "agent_id": agent_id,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return {"written": True, **data}


def brain_sync_list() -> Dict[str, Any]:
    """List all shared keys with last_updated."""
    shared = _get_shared_dir()
    keys = []
    for f in sorted(shared.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            keys.append({
                "key": data.get("key", f.stem),
                "agent_id": data.get("agent_id", "unknown"),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            keys.append({"key": f.stem, "agent_id": "unknown", "updated_at": ""})
    return {"keys": keys, "count": len(keys)}
