"""Tool registration modules for Nucleus MCP Server.

Each submodule provides a `register(mcp, helpers)` function that registers
its tools with the MCP server and returns a list of (name, func) tuples.

The register_all() function injects these tools back into the parent
mcp_server_nucleus module as attributes for backward compatibility with
the refactor integrity test.

Module Whitelisting (Phase 1):
    Set NUCLEUS_ACTIVE_MODULES env var to a comma-separated list of module
    names to limit which modules are loaded.  e.g.:
        NUCLEUS_ACTIVE_MODULES=governance,tasks,sessions

    If unset or empty, ALL modules are loaded (default).
"""

import os
import sys

from . import (
    governance,
    features,
    sessions,
    tasks,
    sync,
    orchestration,
    observability,
    federation,
    engrams,
    align,
)

_ALL_MODULES = {
    "governance": governance,
    "features": features,
    "sessions": sessions,
    "tasks": tasks,
    "sync": sync,
    "orchestration": orchestration,
    "observability": observability,
    "federation": federation,
    "engrams": engrams,
    "align": align,
}


def _get_active_modules():
    """Return list of modules to register, respecting NUCLEUS_ACTIVE_MODULES."""
    whitelist = os.environ.get("NUCLEUS_ACTIVE_MODULES", "").strip()
    if not whitelist:
        return list(_ALL_MODULES.values())

    active = []
    for name in whitelist.split(","):
        name = name.strip().lower()
        if name in _ALL_MODULES:
            active.append(_ALL_MODULES[name])
        else:
            print(f"[NUCLEUS] Warning: unknown module '{name}' in NUCLEUS_ACTIVE_MODULES, skipping.", file=sys.stderr)
    return active


def register_all(mcp, helpers):
    """Register active tool modules and re-export tools to parent module."""
    parent = sys.modules.get("mcp_server_nucleus")
    modules = _get_active_modules()

    total_tools = 0
    failed_modules = []
    for mod in modules:
        try:
            result = mod.register(mcp, helpers)
            if result and parent:
                for name, func in result:
                    setattr(parent, name, func)
                    total_tools += 1
        except Exception as e:
            mod_name = getattr(mod, '__name__', str(mod)).rsplit('.', 1)[-1]
            failed_modules.append(mod_name)
            print(f"[Nucleus] Module '{mod_name}' failed to register: {e}", file=sys.stderr)

    # Register Phase 2 Delta event hook (auto-records Deltas from task/session events)
    try:
        from ..runtime.event_ops import register_event_hook
        from ..runtime.delta_ops import delta_event_hook
        register_event_hook(delta_event_hook)
    except Exception:
        pass  # Never let hook registration block server startup

    _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv)
    if not _is_quiet:
        msg = f"[NUCLEUS] Registered {total_tools} facade tools from {len(modules)} modules."
        if failed_modules:
            msg += f" ({len(failed_modules)} failed: {', '.join(failed_modules)})"
        print(msg, file=sys.stderr)

    # Startup diagnostic summary (non-blocking, silent on error)
    if not _is_quiet and failed_modules:
        try:
            print(f"[NUCLEUS] Startup diagnostics: {len(failed_modules)} module(s) degraded.", file=sys.stderr)
            print(f"[NUCLEUS]   Failed: {', '.join(failed_modules)}", file=sys.stderr)
            print(f"[NUCLEUS]   Run 'nucleus doctor' for detailed diagnostics.", file=sys.stderr)
        except Exception:
            pass
