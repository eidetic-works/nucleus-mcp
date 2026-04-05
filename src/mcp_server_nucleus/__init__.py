

# =============================================================================
# Nucleus Sovereign Control Plane
# Version sourced from pyproject.toml (single source of truth)
# =============================================================================
import re
from pathlib import Path

try:
    _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    __version__ = re.search(r'version\s*=\s*"([^"]+)"', _pyproject.read_text(encoding="utf-8")).group(1)
except Exception:
    __version__ = "1.2.0"  # fallback

import os
import re
import json
import time
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys
import warnings

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
try:
    if os.geteuid() != 0:
        _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv)
        if not _is_quiet:
            logger_init.warning("🚨 INSECURE MODE: Nucleus is running unprivileged.")
            logger_init.warning("    The Watchdog can be terminated by local agents (UID collision).")
            logger_init.warning("    For active defense, install via `sudo scripts/install_nucleus_daemon.sh`")
            
            # Suppress stderr printing if JSON or quiet output is requested to keep stdout clean for agents
            sys.stderr.write("[Nucleus] 🚨 INSECURE MODE: Running unprivileged. Watchdog can be killed.\n")
            sys.stderr.flush()
except AttributeError:
    # Windows fallback (os.geteuid doesn't exist)
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        _is_quiet = any(arg in sys.argv for arg in ['-q', '--quiet', '--json', 'json']) or any('--format' in arg for arg in sys.argv)
        if not _is_quiet:
            logger_init.warning("🚨 INSECURE MODE: Nucleus is running unprivileged (Non-Admin).")
            sys.stderr.write("[Nucleus] 🚨 INSECURE MODE: Running unprivileged (Non-Admin).\n")
            sys.stderr.flush()

# from fastmcp import FastMCP (Moved to try/except block below)

# Import commitment ledger module
from . import commitment_ledger

# Phase 1 Monolith Decomposition Imports
from .runtime.common import get_brain_path, make_response, _get_state, _update_state
from .runtime.event_ops import _emit_event, _read_events
from .runtime.task_ops import (
    _list_tasks, _add_task, _claim_task, _update_task, 
    _get_next_task, _import_tasks_from_jsonl, _escalate_task
)
from .runtime.session_ops import (
    _save_session, _resume_session, _list_sessions, _get_session, 
    _check_for_recent_session, _prune_old_sessions, _get_sessions_path, _get_active_session_path
)
from .runtime.depth_ops import (
    _get_depth_path, _get_depth_state, _save_depth_state, _depth_push, 
    _depth_pop, _depth_show, _depth_reset, _depth_set_max, _format_depth_indicator, _generate_depth_map
)
from .runtime.schema_gen import generate_tool_schema
from .runtime.mounter_ops import get_mounter
from .runtime.trigger_ops import _get_triggers_impl, _trigger_agent_impl
from .runtime.artifact_ops import _read_artifact
from .runtime.telemetry_ops import (
    _brain_record_interaction_impl, _brain_value_ratio_impl, _brain_check_kill_switch_impl,
    _brain_pause_notifications_impl, _brain_resume_notifications_impl,
    _brain_record_feedback_impl, _brain_mark_high_impact_impl
)
from .runtime.sync_ops import (
    get_current_agent, set_current_agent, get_agent_info, sync_lock, perform_sync, 
    get_sync_status, record_sync_time, start_file_watcher, stop_file_watcher, 
    is_sync_enabled, auto_start_sync_if_configured
)

# Setup logging
# logging.basicConfig(level=logging.INFO) # Removing to prevent overriding FastMCP settings
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

# Initialize tiered tool registration (must happen after mcp is created)
from .core.tool_registration_impl import configure_tiered_tool_registration

configure_tiered_tool_registration(mcp)

# Log tier info to stderr so users know what's active
try:
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

# Hypervisor ops still needed
from .runtime.hypervisor_ops import (
    _locker, _injector, _watchdog, _workspace_root,
    lock_resource_impl, unlock_resource_impl, set_hypervisor_mode_impl,
    nucleus_list_directory_impl, nucleus_delete_file_impl,
    watch_resource_impl, hypervisor_status_impl,
)
from .core.egress_proxy import nucleus_curl_impl, nucleus_pip_install_impl

from .runtime.deployment_ops import (
    _get_render_config, _save_render_config, _run_smoke_test,
    _poll_render_once, _start_deploy_poll, _check_deploy_status,
    _complete_deploy
)

from .runtime.feature_ops import (
    _get_features_path, _load_features, _save_features,
    _add_feature, _list_features, _get_feature,
    _update_feature, _mark_validated, _search_features
)

from .runtime.context_ops import (
    _resource_context_impl, _activate_synthesizer_prompt,
    _start_sprint_prompt, _cold_start_prompt
)

from .runtime.consolidation_ops import (
    _archive_resolved_files, _generate_merge_proposals, _garbage_collect_tasks
)

from .runtime.checkpoint_ops import (
    _brain_checkpoint_task_impl, _brain_resume_from_checkpoint_impl,
    _brain_generate_handoff_summary_impl
)


# ============================================================================
# TOOLS MODULE REGISTRATION 
# ============================================================================
from . import tools as _tools_pkg
from . import server as _server_pkg

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

def main():
    """Main entry point - delegates to server module."""
    from .server import main as server_main
    server_main()

if __name__ == "__main__":
    main()
