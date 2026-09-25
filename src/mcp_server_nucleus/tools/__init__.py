"""Tool registration modules for Nucleus MCP Server.

Each submodule provides a `register(mcp, helpers)` function that registers
its tools with the MCP server and returns a list of (name, func) tuples.

The register_all() function injects these tools back into the parent
mcp_server_nucleus module as attributes for backward compatibility with
the refactor integrity test.

PERF/ARCH (Move 1): This package __init__ is LAZY. The 12 facade submodules are
NOT imported at package-load time — importing e.g. ``tools._dispatch`` (which the
stdio transport does) no longer drags governance/federation/orchestration and
their residue-heavy spec modules. The facades are imported on demand by
``register_all()`` at server boot (which is exactly when they are needed), and
attribute access (``tools.governance``) resolves lazily via PEP 562 __getattr__.

Module Whitelisting (Phase 1):
    Set NUCLEUS_ACTIVE_MODULES env var to a comma-separated list of module
    names to limit which modules are loaded.  e.g.:
        NUCLEUS_ACTIVE_MODULES=governance,tasks,sessions

    If unset or empty, ALL modules are loaded (default).
"""

import logging
import os
import sys
from importlib import import_module
from typing import Dict, List

logger = logging.getLogger("nucleus.tools")

# Pruned 2026-06-11 sweep #006 (treatment program): align/skills/flywheel/
# delegate/board were hard-DEAD-IN-CODE (no production callers, no hook
# nudges, not allow-listed). nucleus_delegate self-deprecated by
# nucleus_sync.identify_agent at delegate.py:561 (pre-deletion). The
# orphan tests/test_phase5_convergence.py (archive-facade-only) was also
# deleted; tests/test_align_ops.py TestAlignMCPTool class likewise.
# archive/ground/synthetic_qa were DEAD-IN-REGISTRY (never imported here).

# Registration key (the token users put in NUCLEUS_ACTIVE_MODULES) -> submodule
# filename. Kept as strings so importing this package does NOT pull the facades.
_ALL_MODULE_NAMES = {
    "governance": "governance",
    "features": "features",
    "sessions": "sessions",
    "tasks": "tasks",
    "sync": "sync",
    "orchestration": "orchestration",
    "observability": "observability",
    "federation": "federation",
    "engrams": "engrams",
    "relay": "relay",  # ADR-0036 amendment c068abc1 — v0.2 wake-primitive item #7 LEAD ENABLER
    "cost_router": "cost_router",  # W5 — tier routing with per-call cost capture
    "audit_log": "audit_log_tool",  # W8 — Team-tier tamper-evident audit log
    "vendor_delegate": "vendor_delegate",  # cross-vendor dispatch facade (agent-facing)
    "lane": "lane",  # autonomous lane management (init/start/stop/status/feedback)
    "plan": "plan",  # plan→task→mission bridge (import/execute/list)
    "agent_os_boot": "agent_os_boot",  # E1: external agent boot path (Stage 4 platform)
    "grounding": "grounding",  # Phase 7 §2: C' harness — RAG context orientation
    "runs": "runs",  # Renaissance run engine facade
}

_FACADE_SUBMODULES = frozenset(_ALL_MODULE_NAMES.values())


def __getattr__(name):
    """PEP 562 lazy attribute access.

    Preserves backward compatibility for callers that reach a facade as an
    attribute of the package (e.g. ``mcp_server_nucleus.tools.governance``)
    without an explicit submodule import, and for the legacy ``_ALL_MODULES``
    name -> module mapping (built on demand).
    """
    if name in _FACADE_SUBMODULES:
        module = import_module("." + name, __name__)
        globals()[name] = module
        return module
    if name == "_ALL_MODULES":
        mapping = {
            key: import_module("." + sub, __name__)
            for key, sub in _ALL_MODULE_NAMES.items()
        }
        globals()["_ALL_MODULES"] = mapping
        return mapping
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_FACADE_SUBMODULES) + ["_ALL_MODULES"]))


def _get_active_modules():
    """Return list of facade modules to register, respecting NUCLEUS_ACTIVE_MODULES.

    Modules are imported here (lazily), not at package load time.
    """
    whitelist = os.environ.get("NUCLEUS_ACTIVE_MODULES", "").strip()
    if not whitelist:
        submodules = list(_ALL_MODULE_NAMES.values())
    else:
        submodules = []
        for name in whitelist.split(","):
            name = name.strip().lower()
            if name in _ALL_MODULE_NAMES:
                submodules.append(_ALL_MODULE_NAMES[name])
            else:
                print(f"[NUCLEUS] Warning: unknown module '{name}' in NUCLEUS_ACTIVE_MODULES, skipping.", file=sys.stderr)
    return [import_module("." + sub, __name__) for sub in submodules]


# Registration failures from the most recent register_all(), as
# [{"module": str, "error": str, "error_type": str}]. Populated fresh on each
# call so a re-registration cannot inherit a stale failure.
#
# This list exists because a stderr line is not a signal (ledger CP-3). A facade
# whose register() raised was caught, printed, and otherwise forgotten: no
# non-zero exit, nothing an MCP caller could query, nothing a test could assert.
# CP-5 lived in that gap — the grounding facade returned a bare function instead
# of the (name, func) pairs every other facade returns, the bare except below
# swallowed the TypeError, and the whole GROUND surface was missing from every
# boot while CI printed the error on every run and nobody read it.
_registration_failures: List[Dict[str, str]] = []


def get_registration_failures() -> List[Dict[str, str]]:
    """Facades that failed to register on the last register_all() call.

    Empty list means every active module registered. Returns a copy — callers
    (``nucleus doctor``, the health resource, tests) must not be able to clear
    the record by mutating it.
    """
    return [dict(entry) for entry in _registration_failures]


def _strict_registration() -> bool:
    """Whether a facade failing to register should abort startup.

    Default off: a degraded server that still answers is better than no server
    for a local user whose optional dependency is missing. Set
    NUCLEUS_STRICT_REGISTRATION=true in CI and in any deployment where a missing
    tool surface should fail loudly instead of silently.
    """
    return os.environ.get("NUCLEUS_STRICT_REGISTRATION", "false").lower() in (
        "1", "true", "yes", "on",
    )


def register_all(mcp, helpers):
    """Register active tool modules and re-export tools to parent module."""
    from ..runtime.tool_instrumentation import install_instrumentation
    install_instrumentation(mcp)

    parent = sys.modules.get("mcp_server_nucleus")
    modules = _get_active_modules()

    total_tools = 0
    registered_modules = 0
    stub_modules = []
    failed_modules = []
    _registration_failures.clear()
    for mod in modules:
        mod_name = getattr(mod, '__name__', str(mod)).rsplit('.', 1)[-1]
        try:
            result = mod.register(mcp, helpers)
            if result and parent:
                for name, func in result:
                    setattr(parent, name, func)
                    total_tools += 1
                registered_modules += 1
            elif result is not None and len(result) == 0:
                # Module registered zero tools (e.g. observability stub) —
                # don't count it toward the registered-module total (fw-qa-dogfood).
                stub_modules.append(mod_name)
        except Exception as e:
            failed_modules.append(mod_name)
            _registration_failures.append({
                "module": mod_name,
                "error": str(e),
                "error_type": type(e).__name__,
            })
            # Three channels, because the single stderr print was not enough to
            # get CP-5 noticed for as long as it existed: the log (for anything
            # aggregating logs), stderr (for a human at a terminal), and
            # get_registration_failures() (for doctor, health, and tests).
            logger.error(
                "Facade module %r failed to register (%s): %s",
                mod_name, type(e).__name__, e, exc_info=True,
            )
            print(f"[Nucleus] Module '{mod_name}' failed to register: {e}", file=sys.stderr)

    if failed_modules and _strict_registration():
        raise RuntimeError(
            "Facade registration failed for: " + ", ".join(failed_modules) +
            ". NUCLEUS_STRICT_REGISTRATION is set, so this is fatal rather than "
            "a degraded start. Unset it to boot with the remaining facades."
        )

    # Register Phase 2 Delta event hook (auto-records Deltas from task/session events)
    try:
        from ..runtime.event_ops import register_event_hook
        from ..runtime.delta_ops import delta_event_hook
        register_event_hook(delta_event_hook)
    except Exception:
        logger.debug("Swallowed exception in register_all", exc_info=True)
        pass  # Never let hook registration block server startup

    _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv) or not os.environ.get("NUCLEUS_DEBUG")
    if not _is_quiet:
        msg = f"[NUCLEUS] Registered {total_tools} facade tools from {registered_modules} modules."
        if stub_modules:
            msg += f" ({len(stub_modules)} stub: {', '.join(stub_modules)})"
        if failed_modules:
            msg += f" ({len(failed_modules)} failed: {', '.join(failed_modules)})"
        print(msg, file=sys.stderr)

    # Startup diagnostic summary (non-blocking, silent on error).
    #
    # Deliberately NOT gated on _is_quiet. A degraded server is not routine
    # output that a --quiet flag is asking to suppress; it is the one thing the
    # operator needs to know at startup. _is_quiet is true unless NUCLEUS_DEBUG
    # is set, so this summary was hidden on essentially every real boot, which
    # is how a whole missing facade surface stayed unnoticed (CP-3, CP-5). The
    # success line above stays quiet-gated — that one really is routine.
    if failed_modules:
        try:
            print(f"[NUCLEUS] Startup diagnostics: {len(failed_modules)} module(s) degraded.", file=sys.stderr)
            print(f"[NUCLEUS]   Failed: {', '.join(failed_modules)}", file=sys.stderr)
            print(f"[NUCLEUS]   Run 'nucleus doctor' for detailed diagnostics.", file=sys.stderr)
        except Exception:
            logger.debug("Swallowed exception in register_all", exc_info=True)
            pass
