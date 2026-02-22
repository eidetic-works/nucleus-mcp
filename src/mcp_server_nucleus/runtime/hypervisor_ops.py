"""Hypervisor Operations — Singleton initialization and implementation logic.

Extracted from __init__.py (Hypervisor Layer v0.8.0).
Contains:
- Locker, Injector, Watchdog singleton initialization
- Implementation functions for hypervisor MCP tools
"""

import os
import logging
from pathlib import Path

from ..hypervisor.locker import Locker
from ..hypervisor.injector import Injector
from ..hypervisor.watchdog import Watchdog

logger = logging.getLogger("mcp_nucleus")

# ============================================================
# SINGLETON INITIALIZATION
# ============================================================

_locker = Locker()

_injector = Injector(os.environ.get("NUCLEAR_BRAIN_PATH", "."))

_brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()
_workspace_root = _brain_path.parent
_watchdog = Watchdog(str(_workspace_root))

# Auto-start watchdog on server boot (Shielded for security and CLI cleanliness)
if os.environ.get("NUCLEUS_SKIP_AUTOSTART", "false").lower() != "true":
    try:
        _watchdog.start()
    except Exception as e:
        logger.warning(f"Failed to start Hypervisor Watchdog: {e}")


# ============================================================
# IMPLEMENTATION FUNCTIONS
# ============================================================

def lock_resource_impl(path: str) -> str:
    """Lock a file or directory using chflags uchg (Immutable)."""
    if _locker.lock(path):
        return f"🔒 LOCKED: {path} (Immutable flag set)"
    else:
        return f"❌ FAILED to lock: {path}"


def unlock_resource_impl(path: str) -> str:
    """Unlock a file or directory (removes uchg flag)."""
    if _locker.unlock(path):
        return f"🔓 UNLOCKED: {path}"
    else:
        return f"❌ FAILED to unlock: {path}"


def set_hypervisor_mode_impl(mode: str) -> str:
    """Switch IDE visual context (Layer 2 Injection)."""
    mode = mode.lower()
    if mode == "red":
        _injector.inject_identity("RED TEAM", "#ff0000")
        return "🔴 Hypervisor Mode: RED TEAM (Audit Active)"
    elif mode == "blue":
        _injector.inject_identity("BLUE TEAM", "#007acc")
        return "🔵 Hypervisor Mode: BLUE TEAM (Build Active)"
    elif mode == "reset":
        _injector.reset_identity()
        return "⚪ Hypervisor Mode: RESET (Default)"
    else:
        return "❌ Invalid mode. Use 'red', 'blue', or 'reset'."


def nucleus_list_directory_impl(path: str) -> str:
    """List files in a directory with lock status."""
    try:
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            return f"❌ ERROR: Path not found: {path}"

        items = os.listdir(resolved_path)

        status_lines = []
        for item in items:
            p = resolved_path / item
            locked = "🔒 LOCKED" if _locker.is_locked(str(p)) else "🔓 OPEN"
            status_lines.append(f"{locked} | {item}")

        return "\n".join(status_lines)
    except Exception as e:
        return f"❌ ERROR: {str(e)}"


def nucleus_delete_file_impl(path: str, emit_event_fn=None) -> str:
    """Attempt to delete a file, governed by Hypervisor lock.
    
    Args:
        path: File path to delete
        emit_event_fn: Callback for emitting events (to avoid circular import)
    """
    try:
        resolved_path = Path(path).resolve()

        if _locker.is_locked(str(resolved_path)):
            if emit_event_fn:
                emit_event_fn("access_denied", "hypervisor_l4", {
                    "path": str(resolved_path),
                    "action": "delete",
                    "reason": "Resource is Immutable (Layer 4 Lock)"
                })
            return f"❌ BLOCKED: {path} is locked by Nucleus Hypervisor. Permission Denied."

        if not resolved_path.exists():
            return f"❌ ERROR: File not found: {path}"

        os.remove(resolved_path)
        return f"✅ SUCCESS: {path} has been removed."

    except Exception as e:
        return f"❌ ERROR: {str(e)}"


def watch_resource_impl(path: str) -> str:
    """Register a file/folder with the Hypervisor watchdog."""
    _watchdog.protect(path)
    return f"👁️ WATCHING: {path} (Security Sentinel Active)"


def hypervisor_status_impl() -> str:
    """Report the current security state of the Agent OS."""
    status = []
    status.append("🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)")
    status.append(f"📍 Workspace: {_workspace_root}")
    status.append(f"👁️  Watchdog: {'Active' if _watchdog.observer.is_alive() else 'Inactive'}")
    status.append(f"🔒 Protected Paths: {len(_watchdog.protected_paths)}")
    for p in _watchdog.protected_paths:
        status.append(f"   - {p}")

    status.append("🎨 Injector: Ready")

    return "\n".join(status)
