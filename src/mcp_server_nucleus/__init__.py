

# =============================================================================
# Nucleus Sovereign Control Plane
# Version from installed package metadata (works for both editable + wheel installs).
# Editable installs read pyproject; wheel installs read packaged metadata.
# =============================================================================
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("nucleus-mcp")
except Exception:
    # Editable dev fallback when metadata is unavailable
    import re
    from pathlib import Path
    try:
        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        __version__ = re.search(r'version\s*=\s*"([^"]+)"', _pyproject.read_text(encoding="utf-8")).group(1)
    except Exception:
        __version__ = "unknown"

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys
import warnings
from importlib import import_module as _import_module

# CRITICAL: Suppress output pollution to protect JSON-RPC (Stdio)
# Verify urllib3 doesn't leak OpenSSL warnings to stderr which might break some strict MCP clients
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Record start time for uptime tracking
START_TIME = time.time()

# v0.6.0 Tool Tier System - Solves Registry Bloat
from .tool_tiers import get_active_tier, get_tier_info, is_tool_allowed, tier_manager

ACTIVE_TIER = get_active_tier()
logger_init = logging.getLogger("nucleus.init")
logger_init.info(f"Nucleus Tool Tier: {ACTIVE_TIER} ({get_tier_info()['tier_name']})")

# Configure FastMCP to disable banner and use stderr for logging to avoid breaking MCP protocol
os.environ["FASTMCP_SHOW_CLI_BANNER"] = "False"
os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"

# Epic 5B: Strict Privilege Separation Assertion (Layer 5)
# Suppressed for solo/default users to reduce noise on every CLI invocation.
# Set NUCLEUS_PRIVILEGE_WARNING=1 to re-enable, or run with --verbose.
_show_priv_warning = os.environ.get("NUCLEUS_PRIVILEGE_WARNING", "0") == "1"
try:
    if os.geteuid() != 0 and _show_priv_warning:
        _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv)
        if not _is_quiet:
            logger_init.warning("🚨 INSECURE MODE: Nucleus is running unprivileged.")
            logger_init.warning("    The Watchdog can be terminated by local agents (UID collision).")
            logger_init.warning("    For active defense, install via `sudo scripts/install_nucleus_daemon.sh`")

            sys.stderr.write("[Nucleus] 🚨 INSECURE MODE: Running unprivileged. Watchdog can be killed.\n")
            sys.stderr.flush()
except AttributeError:
    # Windows fallback (os.geteuid doesn't exist)
    if _show_priv_warning:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv)
            if not _is_quiet:
                logger_init.warning("🚨 INSECURE MODE: Nucleus is running unprivileged (Non-Admin).")
                sys.stderr.write("[Nucleus] 🚨 INSECURE MODE: Running unprivileged (Non-Admin).\n")
                sys.stderr.flush()

# =============================================================================
# PERF/ARCH (Move 1): LAZY package-init aggregator.
#
# Historically this __init__ eager-imported ~20 runtime.*_ops modules AND ran the
# full MCP tool registration (register_all + resources + prompts) at import time.
# That made `import mcp_server_nucleus` — and, transitively, importing ANY core
# submodule — drag the entire facade / agent-runtime / governance / federation /
# orchestration surface (residue) into memory.
#
# The re-exported helper symbols (e.g. `_emit_event`, `_list_tasks`, `get_mounter`)
# are now resolved lazily via PEP 562 __getattr__, so `from mcp_server_nucleus
# import X` still works but the backing submodule loads only on first access.
#
# Tool registration is deferred into _ensure_registered(), invoked explicitly by
# main() (the server entry point) and lazily on first access of a
# registration-injected symbol (the `nucleus_*` facade functions that
# register_all() setattrs onto this module, e.g. `nucleus_governance`). This
# preserves the setattr-injection contract that external callers depend on,
# while keeping a bare `import mcp_server_nucleus` residue-free.
# =============================================================================

# Setup logging
logger = logging.getLogger("nucleus")
logger.setLevel(logging.WARNING)

# Initialize FastMCP Server
# Global flag for fallback mode
USE_STDIO_FALLBACK = False

# Initialize FastMCP Server with fallback
try:
    from fastmcp import FastMCP
    mcp = FastMCP("Nucleus Brain")
except ImportError:
    USE_STDIO_FALLBACK = True
    from .runtime.common import MockMCP
    import sys

    # CRITICAL: Use direct stderr write to ensure NO stdout pollution
    sys.stderr.write("[Nucleus Init] WARNING: FastMCP not installed. Running in standalone/verification mode.\\n")
    sys.stderr.flush()
    mcp = MockMCP()

# Log tier info to stderr only when NUCLEUS_DEBUG is set
try:
    import os as _os
    if _os.environ.get("NUCLEUS_DEBUG"):
        _tier = get_active_tier()
        _tier_info = get_tier_info()
        _tier_names = {0: "LAUNCH", 1: "CORE", 2: "ADVANCED", 3: "SYSTEM"}
        _tier_label = _tier_names.get(_tier, f"T{_tier}")
        _allowed_count = _tier_info.get("tools_allowed", 0)
        import sys as _sys
        _sys.stderr.write(f"[Nucleus] Tier {_tier} ({_tier_label}): {_allowed_count} tool facades enabled.")
        if _tier == 0:
            _sys.stderr.write(" Set NUCLEUS_BETA_TOKEN to unlock more. Run 'nucleus doctor' for details.")
        _sys.stderr.write("\n")
        _sys.stderr.flush()
except Exception:
    pass


def get_orch():
    """Get the orchestrator singleton (Unified)."""
    from .runtime.orchestrator_unified import get_orchestrator
    return get_orchestrator()


# =============================================================================
# LAZY RE-EXPORTS (PEP 562)
# submodule (relative) -> the public symbols it historically exported at package
# top level. Flattened into _LAZY_MAP: symbol -> (submodule, attr).
# =============================================================================
_LAZY_SUBMODULE_EXPORTS = {
    ".runtime.common": ["get_brain_path", "make_response", "_get_state", "_update_state"],
    ".runtime.event_ops": ["_emit_event", "_read_events"],
    ".runtime.task_ops": [
        "_list_tasks", "_add_task", "_claim_task", "_update_task",
        "_get_next_task", "_import_tasks_from_jsonl", "_escalate_task",
    ],
    ".runtime.session_ops": [
        "_save_session", "_resume_session", "_list_sessions", "_get_session",
        "_check_for_recent_session", "_prune_old_sessions", "_get_sessions_path",
        "_get_active_session_path",
    ],
    ".runtime.depth_ops": [
        "_get_depth_path", "_get_depth_state", "_save_depth_state", "_depth_push",
        "_depth_pop", "_depth_show", "_depth_reset", "_depth_set_max",
        "_format_depth_indicator", "_generate_depth_map",
    ],
    ".runtime.schema_gen": ["generate_tool_schema"],
    ".runtime.mounter_ops": ["get_mounter"],
    ".runtime.trigger_ops": ["_get_triggers_impl", "_trigger_agent_impl"],
    ".runtime.artifact_ops": ["_read_artifact"],
    ".runtime.telemetry_ops": [
        "_brain_record_interaction_impl", "_brain_value_ratio_impl",
        "_brain_check_kill_switch_impl", "_brain_pause_notifications_impl",
        "_brain_resume_notifications_impl", "_brain_record_feedback_impl",
        "_brain_mark_high_impact_impl",
    ],
    ".runtime.sync_ops": [
        "get_current_agent", "set_current_agent", "get_agent_info", "sync_lock",
        "perform_sync", "get_sync_status", "record_sync_time", "start_file_watcher",
        "stop_file_watcher", "is_sync_enabled", "auto_start_sync_if_configured",
    ],
    ".runtime.orch_helpers": [
        "_get_slot_registry", "_save_slot_registry", "_resolve_slot_id",
        "_get_tier_definitions", "_get_tier_for_model", "_infer_task_tier",
        "_can_slot_run_task", "_score_slot_for_task", "_compute_dependency_graph",
        "_compute_slot_blockers",
    ],
    ".runtime.hypervisor_ops": [
        "_locker", "_injector", "_watchdog", "_workspace_root",
        "lock_resource_impl", "unlock_resource_impl", "set_hypervisor_mode_impl",
        "nucleus_list_directory_impl", "nucleus_delete_file_impl",
        "watch_resource_impl", "hypervisor_status_impl",
    ],
    ".core.egress_proxy": ["nucleus_curl_impl", "nucleus_pip_install_impl"],
    ".runtime.deployment_ops": [
        "_get_render_config", "_save_render_config", "_run_smoke_test",
        "_poll_render_once", "_start_deploy_poll", "_check_deploy_status",
        "_complete_deploy",
    ],
    ".runtime.feature_ops": [
        "_get_features_path", "_load_features", "_save_features",
        "_add_feature", "_list_features", "_get_feature",
        "_update_feature", "_mark_validated", "_search_features",
    ],
    ".runtime.context_ops": [
        "_resource_context_impl", "_activate_synthesizer_prompt",
        "_start_sprint_prompt", "_cold_start_prompt",
    ],
    ".runtime.consolidation_ops": [
        "_archive_resolved_files", "_generate_merge_proposals", "_garbage_collect_tasks",
    ],
    ".runtime.checkpoint_ops": [
        "_brain_checkpoint_task_impl", "_brain_resume_from_checkpoint_impl",
        "_brain_generate_handoff_summary_impl",
    ],
}

_LAZY_MAP = {}
for _sub, _names in _LAZY_SUBMODULE_EXPORTS.items():
    for _n in _names:
        _LAZY_MAP[_n] = (_sub, _n)

# Submodules historically bound as attributes of this package.
_LAZY_SUBMODULES = {
    "commitment_ledger": ".commitment_ledger",
    "tools": ".tools",
    "server": ".server",
    "runtime": ".runtime",
}

# Unified startup-init side-effect state.
_INITIALIZED = False


def _ensure_initialized():
    """Fire ALL load-bearing startup side effects exactly once (idempotent).

    THE unified startup-init for Move 1's de-eager contract. Every server
    entry point (stdio server.main() / __init__.main(), the HTTP/SSE/cloud
    transports, the `nucleus schema` CLI) must call this before enumerating or
    serving tools — never a bare ``import mcp_server_nucleus`` (that stays
    residue-free; init fires at ENTRYPOINT/server-start).

    Move-1 side-effect audit (bare-import ``sys.modules`` diff main-vs-branch +
    AST scan of all 132 deferred submodules): tool/resource/prompt registration
    is the COMPLETE set of load-bearing import side effects deferred by Move 1.
    There is NO separate firewall / egress / RPC-interception / monkeypatch /
    ``sys.settrace`` / ``atexit`` / ``signal`` / socket-intercept install that
    was deferred — the "egress firewall" (allowlist in ``core.egress_proxy.
    nucleus_curl_impl``) and "RPC firewall interception" (hypervisor/dispatch
    behavior surfaced via ``nucleus_governance``) are TOOL behaviors that only
    require the tool to be REGISTERED, not a separate global install. The other
    module-level statements in deferred modules are pure/idempotent (env-var
    config reads, logger creation, in-memory singletons, ``re.compile`` /
    ``ContextVar`` / ``threading.Lock`` constants) and re-run harmlessly when
    their module loads. If a genuine new load-bearing startup side effect is
    ever added, it belongs INSIDE this function.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True  # set before running to prevent re-entrant recursion

    # ADR-0042 D6 (flag NUCLEUS_PROJECT_SPINE, default OFF): establish the
    # per-process project ContextVar from cwd detection at entrypoint init.
    # Single seam — every entrypoint (stdio main, http build_app/main, the
    # cli-schema export) routes through _ensure_initialized(), so wiring it here
    # sets the var for all of them per D6. Flag OFF ⇒ no-op (no detection, the
    # var stays at its None default, runtime.project is never imported):
    # byte-identical startup. Runs first so downstream init sees the context.
    from .runtime.common import init_project_context
    init_project_context()

    # Tiered tool registration must configure mcp before any tool registers.
    # Deferred here (was an import-time side effect) so a bare package import
    # does not pull core.tool_registration_impl -> core.__init__ -> orchestrator.
    from .core.tool_registration_impl import configure_tiered_tool_registration
    configure_tiered_tool_registration(mcp)

    # Relay notification middleware — auto-surfaces unread relays on every
    # tool call via ctx.info(). This is the client-agnostic replacement for
    # Claude Code's SessionStart hook. Every agent (CC, agy, Devin) gets
    # relay notifications without needing client-side hooks or .md instructions.
    try:
        from .runtime.relay_notification_middleware import RelayNotificationMiddleware
        mcp.add_middleware(RelayNotificationMiddleware())
    except Exception as exc:
        import sys as _sys
        _sys.stderr.write(f"[Nucleus] WARNING: relay notification middleware not loaded: {exc}\n")

    from . import tools as _tools_pkg
    from . import server as _server_pkg
    from .runtime.common import get_brain_path, make_response, _get_state, _update_state
    from .runtime.event_ops import _emit_event, _read_events
    from .runtime.trigger_ops import _get_triggers_impl
    from .runtime.depth_ops import _depth_show
    from .runtime.context_ops import (
        _resource_context_impl, _activate_synthesizer_prompt,
        _start_sprint_prompt, _cold_start_prompt,
    )

    _tool_helpers = {
        "get_brain_path": get_brain_path,
        "make_response": make_response,
        "emit_event": _emit_event,
        "read_events": _read_events,
        "get_state": _get_state,
        "update_state": _update_state,
        "get_orch": get_orch,
        "get_triggers_impl": _get_triggers_impl,
        "depth_show": _depth_show,
        "resource_context_impl": _resource_context_impl,
        "activate_synthesizer_prompt": _activate_synthesizer_prompt,
        "start_sprint_prompt": _start_sprint_prompt,
        "cold_start_prompt": _cold_start_prompt,
    }

    _tools_pkg.register_all(mcp, _tool_helpers)
    _server_pkg.register_resources(mcp, _tool_helpers)
    _server_pkg.register_prompts(mcp, _tool_helpers)


# Backward-compat alias: the HTTP/SSE/cloud transports and external callers
# import `_ensure_registered`. It IS the unified init (registration was the
# complete deferred load-bearing set per the audit above), so the historical
# name aliases the canonical `_ensure_initialized`.
_ensure_registered = _ensure_initialized


def __getattr__(name):
    """PEP 562 lazy attribute resolution for the package.

    Order: (1) lazily re-exported runtime helper symbols, (2) lazily bound
    submodules, (3) registration-injected tool symbols — trigger registration
    once, then retry.
    """
    if name.startswith("__") and name.endswith("__"):
        # Never trigger registration for dunder/introspection probes.
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    entry = _LAZY_MAP.get(name)
    if entry is not None:
        submod, attr = entry
        module = _import_module(submod, __name__)
        value = getattr(module, attr)
        globals()[name] = value
        return value

    sub = _LAZY_SUBMODULES.get(name)
    if sub is not None:
        module = _import_module(sub, __name__)
        globals()[name] = module
        return module

    # Fall back: possibly a registration-injected facade symbol (e.g.
    # nucleus_governance) that register_all() setattrs onto this module at boot.
    if not _INITIALIZED:
        _ensure_initialized()
        if name in globals():
            return globals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_MAP) + list(_LAZY_SUBMODULES)))


def main():
    """Main entry point - delegates to server module."""
    _ensure_initialized()
    from .server import main as server_main
    server_main()


if __name__ == "__main__":
    main()
