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
# LAZY SINGLETON INITIALIZATION (Phase 14 Resilience)
# ============================================================

_locker_inst = None
# Keyed by resolved brain_path so each tenant gets its own instance.
# Lazy init is required because multi-tenant HTTP middleware sets
# NUCLEAR_BRAIN_PATH per-request; module-level resolution would freeze
# the path to whatever was set at import time.
_injector_instances: dict[str, "Injector"] = {}
_watchdog_instances: dict[str, "Watchdog"] = {}


def _current_brain_path() -> Path:
    """Resolve brain path from the current env (set per-request by tenant middleware)."""
    return Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()


# Backward-compatible module-level names — now computed lazily so they
# reflect the per-request NUCLEAR_BRAIN_PATH, not the import-time value.
def __getattr__(name: str):
    if name == "_brain_path":
        return _current_brain_path()
    if name == "_workspace_root":
        return _current_brain_path().parent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_locker():
    global _locker_inst
    if _locker_inst is None:
        from ..hypervisor.locker import Locker
        _locker_inst = Locker()
    return _locker_inst

def get_injector():
    """Return an Injector for the current tenant's brain path."""
    brain_path = _current_brain_path()
    key = str(brain_path)
    if key not in _injector_instances:
        from ..hypervisor.injector import Injector
        _injector_instances[key] = Injector(str(brain_path))
    return _injector_instances[key]

def get_watchdog():
    """Return a Watchdog for the current tenant's workspace root.

    Each distinct brain_path gets its own Watchdog instance so that
    multi-tenant deployments watch the correct directory.
    """
    brain_path = _current_brain_path()
    key = str(brain_path)
    if key not in _watchdog_instances:
        from ..hypervisor.watchdog import Watchdog
        workspace_root = brain_path.parent
        _watchdog_instances[key] = Watchdog(str(workspace_root))
    return _watchdog_instances[key]

# For backward compatibility with existing tool implementations
@property
def _locker(): return get_locker()
@property
def _injector(): return get_injector()
@property
def _watchdog(): return get_watchdog()

# Auto-start watchdog on server boot (Shielded for security and CLI cleanliness)
def autostart_watchdog():
    # Skip in CI/test environments — Observer thread blocks pytest exit
    if os.environ.get("CI") or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if os.environ.get("NUCLEUS_SKIP_AUTOSTART", "false").lower() != "true":
        try:
            get_watchdog().start()
        except Exception as e:
            logger.warning(f"Failed to start Hypervisor Watchdog: {e}")


# ============================================================
# IMPLEMENTATION FUNCTIONS
# ============================================================

def lock_resource_impl(path: str) -> str:
    """Lock a file or directory using chflags uchg (Immutable)."""
    if get_locker().lock(path):
        return f"🔒 LOCKED: {path} (Immutable flag set)"
    else:
        return f"❌ FAILED to lock: {path}"


def unlock_resource_impl(path: str, token_id: str = None) -> str:
    """Unlock a file or directory (removes uchg flag). Requires IPC Token for T3."""
    if not token_id:
        return f"❌ UNLOCK DENIED: IPC token_id required for Tier 3 operation."
    
    from .auth.ipc_provider import get_ipc_auth_manager
    
    manager = get_ipc_auth_manager()
    # Enforce Tier 3 for unlock
    is_valid, error = manager.validate_token(token_id, scope="nucleus_governance:unlock", required_tier="T3")
    
    if not is_valid:
        return f"❌ UNLOCK DENIED: {error}"

    locker = get_locker()
    if locker.unlock(path, secret=locker._internal_secret):
        return f"🔓 UNLOCKED: {path}"
    else:
        return f"❌ FAILED to unlock: {path} (Secret mismatch)"


def set_hypervisor_mode_impl(mode: str) -> str:
    """Switch IDE visual context (Layer 2 Injection)."""
    mode = mode.lower()
    injector = get_injector()
    if mode == "red":
        injector.inject_identity("RED TEAM", "#ff0000")
        return "🔴 Hypervisor Mode: RED TEAM (Audit Active)"
    elif mode == "blue":
        injector.inject_identity("BLUE TEAM", "#007acc")
        return "🔵 Hypervisor Mode: BLUE TEAM (Build Active)"
    elif mode == "reset":
        injector.reset_identity()
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
        locker = get_locker()

        status_lines = []
        for item in items:
            p = resolved_path / item
            locked = "🔒 LOCKED" if locker.is_locked(str(p)) else "🔓 OPEN"
            status_lines.append(f"{locked} | {item}")

        return "\n".join(status_lines)
    except Exception as e:
        return f"❌ ERROR: {str(e)}"


def nucleus_delete_file_impl(path: str, emit_event_fn=None, confirm: bool = False) -> str:
    """Attempt to delete a file, governed by Hypervisor lock + HITL gate.
    
    Args:
        path: File path to delete
        emit_event_fn: Callback for emitting events (to avoid circular import)
        confirm: HITL safety gate. Must be True to actually delete. Default False.
    """
    try:
        resolved_path = Path(path).resolve()

        # HITL Gate: require explicit confirmation for destructive ops
        if not confirm:
            return (
                f"⚠️ HITL GATE: delete_file requires confirm=true.\n"
                f"Target: {resolved_path}\n"
                f"Re-call with confirm=true to proceed. This is a destructive operation."
            )

        locker = get_locker()
        if locker.is_locked(str(resolved_path)):
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
        if emit_event_fn:
            emit_event_fn("file_deleted", "hypervisor_governance", {
                "path": str(resolved_path),
                "confirmed": True,
            })
        return f"✅ SUCCESS: {path} has been removed."

    except Exception as e:
        return f"❌ ERROR: {str(e)}"


def watch_resource_impl(path: str) -> str:
    """Register a file/folder with the Hypervisor watchdog."""
    get_watchdog().protect(path)
    return f"👁️ WATCHING: {path} (Security Sentinel Active)"


def hypervisor_status_impl() -> str:
    """Report the current security state of the Agent OS."""
    status = []
    status.append("🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)")
    
    brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()
    workspace_root = brain_path.parent
    watchdog = get_watchdog()

    status.append(f"📍 Workspace: {workspace_root}")
    status.append(f"👁️  Watchdog: {'Active' if watchdog.observer.is_alive() else 'Inactive'}")
    status.append(f"🔒 Protected Paths: {len(watchdog.protected_paths)}")
    for p in watchdog.protected_paths:
        status.append(f"   - {p}")

    status.append("🎨 Injector: Ready")

    return "\n".join(status)
