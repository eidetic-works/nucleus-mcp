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
    for mod in modules:
        result = mod.register(mcp, helpers)
        if result and parent:
            for name, func in result:
                setattr(parent, name, func)
                total_tools += 1

    print(f"[NUCLEUS] Registered {total_tools} facade tools from {len(modules)} modules.", file=sys.stderr)
