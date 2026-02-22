

# =============================================================================
# Nucleus Sovereign Control Plane v1.0.8
# =============================================================================
__version__ = "1.0.8"

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

# from fastmcp import FastMCP (Moved to try/except block below)

# Import commitment ledger module
from . import commitment_ledger

# Phase 1 Monolith Decomposition Imports
from .runtime.common import get_brain_path, make_response, _get_state, _update_state
from .runtime.event_ops import _emit_event, _read_events
from .runtime.task_ops import (
    _list_tasks, _add_task, 
    _claim_task, _update_task, _get_next_task, _import_tasks_from_jsonl,
    _escalate_task
)
from .runtime.session_ops import (
    _save_session, _resume_session, _list_sessions, 
    _get_session, _check_for_recent_session, _prune_old_sessions,
    _get_sessions_path, _get_active_session_path
)
from .runtime.depth_ops import (
    _get_depth_path, _get_depth_state, _save_depth_state, _depth_push, 
    _depth_pop, _depth_show, _depth_reset, _depth_set_max, _format_depth_indicator,
    _generate_depth_map
)
from .runtime.schema_gen import generate_tool_schema
from .runtime.mounter_ops import get_mounter
from .runtime.trigger_ops import _get_triggers_impl, _trigger_agent_impl
from .runtime.artifact_ops import _read_artifact
from .runtime.telemetry_ops import (
    _brain_record_interaction_impl,
    _brain_value_ratio_impl,
    _brain_check_kill_switch_impl,
    _brain_pause_notifications_impl,
    _brain_resume_notifications_impl,
    _brain_record_feedback_impl,
    _brain_mark_high_impact_impl
)
from .runtime.sync_ops import (
    get_current_agent, set_current_agent, get_agent_info,
    sync_lock, perform_sync, get_sync_status, record_sync_time,
    start_file_watcher, stop_file_watcher, is_sync_enabled,
    auto_start_sync_if_configured
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
    import sys
    
    # CRITICAL: Use direct stderr write to ensure NO stdout pollution
    sys.stderr.write("[Nucleus Init] WARNING: FastMCP not installed. Running in standalone/verification mode.\\n")
    sys.stderr.flush()
    
    # Define MockMCP before use
    class MockMCP:
        def tool(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def resource(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def prompt(self, *args, **kwargs):
            def decorator(f): return f
            return decorator
        def run(self): pass
    
    mcp = MockMCP()

# Initialize tiered tool registration (must happen after mcp is created)
from .core.tool_registration_impl import configure_tiered_tool_registration
configure_tiered_tool_registration(mcp)



# ORCHESTRATOR V3.1 INTEGRATION
# ============================================================
# Lazy-loaded singleton for orchestrator access
# All task operations route through this for CRDT + V3.1 features
# IMPORTANT: Uses the SAME singleton as orchestrator_v3.get_orchestrator()

def get_orch():
    """Get the orchestrator singleton (Unified)."""
    from .runtime.orchestrator_unified import get_orchestrator
    return get_orchestrator()

# ============================================================
# CORE LOGIC (Testable, plain functions)
# ============================================================

# make_response imported from runtime.common
# _emit_event imported from runtime.event_ops
# _read_events imported from runtime.event_ops


# brain_health() defined later in file (line ~7155) - uses _brain_health_impl()

@mcp.tool()
def brain_auto_fix_loop(file_path: str, verification_command: str) -> str:
    """
    Auto-fix loop: Verify -> Diagnose -> Fix -> Verify.
    Retries up to 3 times.
    Phase 4: Self-Healing.
    """
    from .runtime.loops.fixer import FixerLoop
    
    # We pass brain_fix_code as the fixer callback
    # brain_fix_code returns a JSON string, which FixerLoop expects
    loop = FixerLoop(
        target_file=file_path,
        verification_command=verification_command,
        fixer_func=brain_fix_code,
        max_retries=3
    )
    
    result = loop.run()
    return json.dumps(result, indent=2)

# _get_state imported from runtime.common
# _update_state imported from runtime.common

# ============================================================
# HYPERVISOR LAYER (v0.8.0) - "God Mode" Lock
# ============================================================
# Hypervisor ops extracted to runtime/hypervisor_ops.py
from .runtime.hypervisor_ops import (
    _locker, _injector, _watchdog, _workspace_root,
    lock_resource_impl, unlock_resource_impl, set_hypervisor_mode_impl,
    nucleus_list_directory_impl, nucleus_delete_file_impl,
    watch_resource_impl, hypervisor_status_impl,
)

@mcp.tool()
def lock_resource(path: str) -> str:
    """
    [HYPERVISOR] Locks a file or directory using 'chflags uchg' (Immutable).
    Prevents ANY modification, even by root/sudo, until unlocked.
    Use this to protect critical state or during Red Team audits.
    """
    return lock_resource_impl(path)

@mcp.tool()
def unlock_resource(path: str) -> str:
    """
    [HYPERVISOR] Unlocks a file or directory (removes 'uchg' flag).
    """
    return unlock_resource_impl(path)

@mcp.tool()
def set_hypervisor_mode(mode: str) -> str:
    """
    [HYPERVISOR] Switches the IDE visual context (Layer 2 Injection).
    mode: "red" (Audit/Attack) or "blue" (Build/Defend).
    """
    return set_hypervisor_mode_impl(mode)

@mcp.tool()
def nucleus_list_directory(path: str) -> str:
    """
    [GOVERNANCE] Lists files in a directory. 
    Allows the agent to safely inspect a folder before performing audit actions.
    """
    return nucleus_list_directory_impl(path)

@mcp.tool()
def nucleus_delete_file(path: str) -> str:
    """
    [GOVERNANCE] Attempts to delete a file. 
    This action is strictly governed by the Nucleus Hypervisor (Layer 4).
    """
    return nucleus_delete_file_impl(path, emit_event_fn=_emit_event)

@mcp.tool()
def watch_resource(path: str) -> str:
    """
    [HYPERVISOR] key file/folder monitoring (Layer 1).
    If a protected resource is modified while locked, it triggers an alert
    and immediately re-applies the lock.
    """
    return watch_resource_impl(path)

@mcp.tool()
def hypervisor_status() -> str:
    """
    [HYPERVISOR] Reports the current security state of the Agent OS.
    """
    return hypervisor_status_impl()

# Artifact and Trigger logic moved to runtime/artifact_ops.py and runtime/trigger_ops.py

# ============================================================
# V2 TASK MANAGEMENT CORE LOGIC
# ============================================================

# Task logic moved to runtime/task_ops.py

# Task logic moved to runtime/task_ops.py


# ============================================================
# DEPTH TRACKER - TIER 1 MVP (ADHD Accommodation)
# ============================================================
# Purpose: Real-time "you are here" indicator for conversation depth
# Philosophy: WARN but ALLOW - guardrail, not a wall

# Depth tracking logic moved to runtime/depth_ops.py




# Deployment operations extracted to runtime/deployment_ops.py
from .runtime.deployment_ops import (
    _get_render_config, _save_render_config, _run_smoke_test,
    _poll_render_once, _start_deploy_poll, _check_deploy_status,
    _complete_deploy
)

# ============================================================
# FEATURE MAP (Product feature inventory)
# ============================================================

# Feature map operations extracted to runtime/feature_ops.py
from .runtime.feature_ops import (
    _get_features_path, _load_features, _save_features,
    _add_feature, _list_features, _get_feature,
    _update_feature, _mark_validated, _search_features
)



# ============================================================
# PROOF SYSTEM (Feature validation proof)
# ============================================================



# Session management logic moved to runtime/session_ops.py
# Context and Prompt logic moved to runtime/context_ops.py
from .runtime.context_ops import (
    _resource_context_impl, _activate_synthesizer_prompt,
    _start_sprint_prompt, _cold_start_prompt
)






# ============================================================
# BRAIN CONSOLIDATION - TIER 1 (Reversibility-First)
# ============================================================
# Purpose: Automated cleanup of artifact noise without data loss
# Philosophy: MOVE, never DELETE - all actions are reversible

# Consolidation operations extracted to runtime/consolidation_ops.py
from .runtime.consolidation_ops import (
    _get_archive_path, _archive_resolved_files,
    _detect_redundant_artifacts, _generate_merge_proposals
)


# ============================================================
# FEATURE MAP TOOLS (MCP wrappers)
# ============================================================



@mcp.tool()
def brain_add_feature(product: str, name: str, description: str, source: str,
                      version: str, how_to_test: List[str], expected_result: str,
                      status: str = "development", tags: List[str] = None) -> Dict:
    """Add a new feature to the product's feature map.
    
    Args:
        product: "gentlequest" or "nucleus"
        name: Human-readable feature name
        description: What the feature does
        source: Where it lives (e.g., "gentlequest_app", "pypi_mcp")
        version: Which version it shipped in
        how_to_test: List of test steps
        expected_result: What should happen when testing
        status: development/staged/production/released
        tags: Searchable tags
    
    Returns:
        Created feature object
    """
    kwargs = {}
    if tags:
        kwargs["tags"] = tags
    return _add_feature(product, name, description, source, version, 
                        how_to_test, expected_result, status, **kwargs)

@mcp.tool()
def brain_list_features(product: str = None, status: str = None, tag: str = None) -> Dict:
    """List all features, optionally filtered.
    
    Args:
        product: Filter by product ("gentlequest" or "nucleus")
        status: Filter by status
        tag: Filter by tag
    
    Returns:
        List of matching features
    """
    return _list_features(product, status, tag)

@mcp.tool()
def brain_get_feature(feature_id: str) -> Dict:
    """Get a specific feature by ID.
    
    Args:
        feature_id: The feature ID (snake_case)
    
    Returns:
        Feature object with test instructions
    """
    return _get_feature(feature_id)

@mcp.tool()
def brain_update_feature(feature_id: str, status: str = None, 
                         description: str = None, version: str = None) -> Dict:
    """Update a feature's fields.
    
    Args:
        feature_id: Feature to update
        status: New status
        description: New description
        version: New version
    
    Returns:
        Updated feature
    """
    updates = {}
    if status:
        updates["status"] = status
    if description:
        updates["description"] = description
    if version:
        updates["version"] = version
    
    if not updates:
        return {"error": "No updates provided"}
    
    return _update_feature(feature_id, **updates)

@mcp.tool()
def brain_mark_validated(feature_id: str, result: str) -> Dict:
    """Mark a feature as validated after testing.
    
    Args:
        feature_id: Feature that was tested
        result: "passed" or "failed"
    
    Returns:
        Updated feature with validation timestamp
    """
    return _mark_validated(feature_id, result)

# ============================================================
# RECURSIVE MOUNTER (AG-021)
# ============================================================

@mcp.tool()
async def brain_mount_server(name: str, command: str, args: List[str] = []) -> str:
    """
    Mount an external MCP server to Nucleus (Recursive Aggregator).
    
    This allows Nucleus to act as a Host-Runtime for other servers,
    providing a single unified interface for the AI client.
    
    Args:
        name: Local name for the mounted server
        command: Executable command (e.g. "npx", "python")
        args: Command line arguments
    """
    try:
        from .runtime.mounter_ops import _brain_mount_server_impl
        return await _brain_mount_server_impl(name, command, args)
    except Exception as e:
        return f"Error mounting server: {e}"

@mcp.tool()
async def brain_thanos_snap() -> str:
    """
    Trigger the Phase C 'Thanos Snap' - Instance Fractal Aggregation.
    
    Instantly mounts mock Stripe, Postgres, and Brave Search servers
    to demonstrate the recursive aggregator pattern in v0.5.
    """
    try:
        from .runtime.mounter_ops import _brain_thanos_snap_impl
        return await _brain_thanos_snap_impl()
    except Exception as e:
        return f"Error during Thanos Snap: {e}"

@mcp.tool()
async def brain_unmount_server(server_id: str) -> str:
    """
    Unmount an external MCP server.
    
    Args:
        server_id: The ID of the server to unmount (e.g. mnt-123456)
    """
    try:
        from .runtime.mounter_ops import _brain_unmount_server_impl
        return await _brain_unmount_server_impl(server_id)
    except Exception as e:
        return f"Error unmounting server: {e}"

@mcp.tool()
def brain_list_mounted() -> str:
    """
    List all currently mounted external MCP servers.
    """
    try:
        from .runtime.mounter_ops import _brain_list_mounted_impl
        return _brain_list_mounted_impl()
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
async def brain_discover_mounted_tools(server_id: str = None) -> str:
    """
    Discover tools from mounted MCP servers.
    
    This is the "Southbound Query" of the Recursive Aggregator pattern.
    It asks mounted servers what tools they provide.
    
    Args:
        server_id: Optional. Specific server to query. If None, queries all.
    """
    try:
        from .runtime.mounter_ops import _brain_discover_mounted_tools_impl
        return await _brain_discover_mounted_tools_impl(server_id)
    except Exception as e:
        return make_response(False, error=str(e))

@mcp.tool()
async def brain_invoke_mounted_tool(server_id: str, tool_name: str, arguments: Dict[str, Any] = {}) -> str:
    """
    Invoke a tool on a mounted external MCP server.
    
    This is the "Southbound Execution" of the Recursive Aggregator pattern.
    It allows calling tools on any number of external servers without 
    bloating the primary Nucleus registry.
    
    Args:
        server_id: The ID of the server (e.g. mnt-123456)
        tool_name: The name of the tool to call on that server
        arguments: Arguments for the tool
    """
    try:
        from .runtime.mounter_ops import _brain_invoke_mounted_tool_impl
        return await _brain_invoke_mounted_tool_impl(server_id, tool_name, arguments)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@mcp.tool()
def brain_search_features(query: str) -> Dict:
    """Search features by name, description, or tags.
    
    Args:
        query: Search query
    
    Returns:
        Matching features
    """
    return _search_features(query)

# ============================================================
# PROOF SYSTEM TOOLS (MCP wrappers)
# ============================================================

@mcp.tool()
def brain_generate_proof(feature_id: str, thinking: str = None,
                         deployed_url: str = None, 
                         files_changed: List[str] = None,
                         risk_level: str = "low",
                         rollback_time: str = "15 minutes") -> str:
    """Generate a proof document for a feature.
    
    Creates a markdown proof file with:
    - AI thinking (options, choice, reasoning, fallback)
    - Deployed URL
    - Files changed
    - Rollback plan with risk level
    
    Args:
        feature_id: Feature to generate proof for
        thinking: AI's decision-making process (markdown)
        deployed_url: Production URL
        files_changed: List of files modified
        risk_level: low/medium/high
        rollback_time: Estimated time to rollback
    
    Returns:
        Proof generation result with path
    """
    from .runtime.proof_ops import _brain_generate_proof_impl
    return _brain_generate_proof_impl(feature_id, thinking, deployed_url, 
                           files_changed or [], risk_level, rollback_time)

@mcp.tool()
def brain_get_proof(feature_id: str) -> str:
    """Get the proof document for a feature.
    
    Args:
        feature_id: Feature ID to get proof for
    
    Returns:
        Proof content or message if not found
    """
    from .runtime.proof_ops import _brain_get_proof_impl
    return _brain_get_proof_impl(feature_id)

@mcp.tool()
def brain_list_proofs() -> List[str]:
    """List all proof documents.
    
    Returns:
        List of proofs with metadata
    """
    from .runtime.proof_ops import _brain_list_proofs_impl
    return _brain_list_proofs_impl()

# ============================================================
# SESSION MANAGEMENT TOOLS (MCP wrappers)
# ============================================================

@mcp.tool()
def brain_save_session(context: str, active_task: str = None,
                       pending_decisions: List[str] = None,
                       breadcrumbs: List[str] = None,
                       next_steps: List[str] = None) -> str:
    """Save current session for later resumption."""
    result = _save_session(context, active_task, pending_decisions, breadcrumbs, next_steps)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_resume_session(session_id: str = None) -> str:
    """Resume a saved session."""
    result = _resume_session(session_id)
    if result:
        return make_response(True, data=result)
    return make_response(False, error="Session not found")

@mcp.tool()
def brain_list_sessions() -> Dict:
    """List all saved sessions.
    
    Returns:
        List of sessions with metadata (context, task, date)
    """
    sessions = _list_sessions()
    return make_response(True, data=sessions)

@mcp.tool()
def brain_check_recent_session() -> Dict:
    """Check if there's a recent session to offer resumption.
    
    Call this at the start of a new conversation to see if
    the user should be offered to resume their previous work.
    
    Returns:
        Whether a recent session exists with prompt text
    """
    result = _check_for_recent_session()
    return make_response(True, data=result)

# ============================================================
# BRAIN CONSOLIDATION TOOLS (MCP wrappers)
# ============================================================

# DT-1 Ticket #6: Session-End Engrams
from .runtime.session_ops import _brain_session_end_impl


@mcp.tool()
def brain_session_end(summary: str = "", learnings: str = "",
                      mood: str = "neutral") -> str:
    """
    🏁 End your work session — auto-captures what happened as an engram.

    Call this before closing your IDE. It:
    1. Counts tasks completed, claimed, and created this session
    2. Writes a session summary engram (via ADUN)
    3. Feeds the Morning Brief tomorrow's "Yesterday" context

    Args:
        summary: What you accomplished (auto-generated if empty).
        learnings: Key decisions or patterns discovered.
        mood: How it went (productive/neutral/stuck/frustrated).

    The Morning Brief tomorrow will show this session's data.
    """
    result = _brain_session_end_impl(summary, learnings, mood)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error", "Unknown error"))


@mcp.tool()
def brain_archive_resolved() -> Dict:
    """Archive all .resolved.* backup files to clean up the brain folder.
    
    This moves auto-generated version backup files (created by Antigravity)
    to the archive/resolved/ folder. The files are NOT deleted - they can
    be recovered from the archive at any time.
    
    Safe to run regularly (nightly recommended). Reversible action.
    
    Returns:
        Summary of archived files including count and paths
    """
    return _archive_resolved_files()

@mcp.tool()
def brain_propose_merges() -> Dict:
    """Detect redundant artifacts and generate merge proposals.
    
    Scans the brain folder for:
    - Versioned duplicates (old.md vs NEW_V0_4_0.md)
    - Related series (SYNTHESIS_PART1, PART2, etc.)
    - Stale files (30+ days unmodified)
    - Archive candidates (temp files, drafts)
    
    Returns proposals only - no files are moved or modified.
    Human reviews proposals before any action is taken.
    
    Returns:
        Merge proposals with structured findings and readable report
    """
    return _generate_merge_proposals()

@mcp.tool()
def brain_emit_event(event_type: str, emitter: str, data: Dict[str, Any], description: str = "") -> str:
    """Emit a new event to the brain ledger."""
    result = _emit_event(event_type, emitter, data, description)
    if result.startswith("Error"):
        return make_response(False, error=result)
    return make_response(True, data={"event_id": result})

@mcp.tool()
def brain_read_events(limit: int = 10) -> List[Dict]:
    """Read recent events."""
    events = _read_events(limit)
    return make_response(True, data={"events": events})

@mcp.tool()
def brain_get_state(path: Optional[str] = None) -> Dict:
    """Get the current state of the brain."""
    return _get_state(path)

@mcp.tool()
def brain_update_state(updates: Dict[str, Any]) -> str:
    """Update the brain state with new values (shallow merge)."""
    return _update_state(updates)

# ============================================================
# MULTI-AGENT SYNC TOOLS (v0.7.0)
# ============================================================

@mcp.tool()
def brain_identify_agent(agent_id: str, environment: str, role: str = "") -> str:
    """
    Register current agent identity for multi-agent coordination.
    
    This is the first tool an agent should call when starting a session.
    It persists agent identity in .brain/.nucleus_agent for event logging
    and sync coordination.
    
    Args:
        agent_id: Unique identifier (e.g., "windsurf_main", "cursor_dev")
        environment: Tool name (e.g., "windsurf", "cursor", "claude_desktop")
        role: Optional role (e.g., "architect", "developer", "reviewer")
    
    Returns:
        JSON with registration details and storage location
    
    Example:
        brain_identify_agent("windsurf_opus", "windsurf", "architect")
    """
    # Pillar 6: ID Collision Protection (Finding 6)
    try:
        from .runtime.event_ops import _read_events
        import socket
        current_host = socket.gethostname()
        
        # Check last 50 events for this ID from a different host
        recent_events = _read_events(limit=50)
        collision_detected = False
        for event in recent_events:
            # If agent registered recently (< 5 mins) from another host
            if event.get("emitter") == agent_id and event.get("type") == "AGENT_REGISTERED":
                stored_data = event.get("data", {})
                if stored_data.get("host") and stored_data.get("host") != current_host:
                    collision_detected = True
                    break
        
        if collision_detected:
            warning = f"WARNING: Agent ID '{agent_id}' is already active on another host. Consider using a suffix (e.g. {agent_id}-{current_host[:5]})."
            logger.warning(warning)
            # We return the warning in the JSON result but don't hard-block (Non-destructive)
    except Exception:
        collision_detected = False

    result = set_current_agent(agent_id, environment, role)
    if collision_detected:
        result["collision_warning"] = warning
    
    # Emit registration event with host info
    import socket
    result["host"] = socket.gethostname()
    
    _emit_event(
        event_type="AGENT_REGISTERED",
        emitter=agent_id,
        data=result,
        description=f"Agent {agent_id} registered in {environment} (v0.7.1)"
    )
    
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_sync_status() -> str:
    """
    Check current multi-agent sync status.
    
    Returns comprehensive sync state including:
    - Whether sync is enabled and mode (auto/manual)
    - Current agent identity
    - All detected agents that have modified watched files
    - Pending conflicts
    - Auto-sync watcher status
    
    Use this to understand the current sync state before making changes
    or to debug sync issues.
    
    Returns:
        JSON with sync status details
    """
    status = get_sync_status()
    return json.dumps(status, indent=2)


@mcp.tool()
def brain_sync_now(force: bool = False) -> str:
    """
    Manually trigger multi-agent sync.
    
    Synchronizes watched files (.brain/ledger/state.json, decisions.md, task.md)
    with proper conflict detection and resolution. Use this when:
    - Taking over from another agent
    - Before making critical changes
    - After a conflict is detected
    
    Args:
        force: If True, sync even if no changes detected
    
    Returns:
        JSON with sync result including files synced and conflicts resolved
    """
    if not is_sync_enabled():
        return json.dumps({
            "error": "Sync not enabled",
            "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true",
            "example": "sync:\\n  enabled: true\\n  mode: auto"
        }, indent=2)
    
    try:
        with sync_lock(timeout=5):
            result = perform_sync(force)
            record_sync_time()
            
            # Emit sync event
            _emit_event(
                event_type="SYNC_MANUAL",
                emitter=get_current_agent(),
                data=result,
                description=f"Manual sync by {get_current_agent()}"
            )
            
            return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "hint": "Another agent may be syncing. Wait and retry."
        }, indent=2)


@mcp.tool()
def brain_sync_auto(enable: bool) -> str:
    """
    Enable or disable automatic file watching and sync.
    
    When enabled, watches configured files for changes and automatically
    syncs within 5 seconds of modification. Uses watchdog library for
    cross-platform file monitoring.
    
    Args:
        enable: True to start watching, False to stop
    
    Returns:
        JSON with auto-sync status and watched files
    
    Requires:
        - .brain/config/nucleus.yaml with sync.enabled: true
        - watchdog library installed (pip install watchdog)
    """
    if enable:
        result = start_file_watcher()
        
        # Pillar 5: Git Hygiene (Finding 5)
        try:
            from .runtime.common import get_brain_path
            root_path = get_brain_path().parent
            gitignore = root_path / ".gitignore"
            
            ignore_block = "\n# Nucleus MCP Sync Metadata\n**/*.meta\n**/*.conflict\n.nucleus_agent\n.sync_last\n"
            
            if gitignore.exists():
                content = gitignore.read_text()
                if "**/*.meta" not in content:
                    logger.info("Automatically patching .gitignore for Nucleus sync hygiene...")
                    with open(gitignore, "a") as f:
                        f.write(ignore_block)
                    result["gitignore_patched"] = True
            else:
                # Optionally create it if it doesn't exist? (Non-destructive)
                # For now, only patch if it exists to respect user sovereignty
                pass
        except Exception as e:
            logger.debug(f"Git hygiene check failed: {e}")
    else:
        result = stop_file_watcher()
        
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_sync_resolve(file_path: str, strategy: str = "last_write_wins") -> str:
    """
    Manually resolve a file conflict (v0.7.1).
    
    Args:
        file_path: Relative path to the file (e.g., "task.md")
        strategy: "last_write_wins" (accept current) or "manual" (keep marker)
        
    Returns:
        JSON with resolution result.
    """
    try:
        from .runtime.common import get_brain_path
        from .runtime.sync_ops import detect_conflict, resolve_conflict, sync_lock, get_current_agent
        
        brain_path = get_brain_path()
        abs_path = brain_path / file_path
        
        with sync_lock(brain_path):
            conflict = detect_conflict(abs_path)
            if not conflict:
                return json.dumps({"status": "error", "message": "No active conflict found for this file."}, indent=2)
            
            status = resolve_conflict(conflict, strategy, brain_path)
            
            description = f"Conflict in {file_path} resolved via {strategy} by {get_current_agent()}"
            _emit_event(
                event_type="SYNC_CONFLICT_RESOLVED",
                emitter=get_current_agent(),
                data={"file": file_path, "strategy": strategy, "status": status},
                description=description
            )
            
            return json.dumps({"status": status, "file": file_path}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
def brain_read_artifact(path: str) -> str:
    """Read contents of an artifact file (relative to .brain/artifacts)."""
    from .runtime.artifact_ops import _read_artifact
    return _read_artifact(path)

@mcp.tool()
def brain_write_artifact(path: str, content: str) -> str:
    """Write contents to an artifact file."""
    from .runtime.artifact_ops import _write_artifact
    return _write_artifact(path, content)

@mcp.tool()
def brain_list_artifacts(folder: Optional[str] = None) -> List[str]:
    """List artifacts in a folder."""
    from .runtime.artifact_ops import _list_artifacts
    return _list_artifacts(folder)

@mcp.tool()
def brain_trigger_agent(agent: str, task_description: str, context_files: List[str] = None) -> str:
    """Trigger an agent by emitting a task_assigned event."""
    from .runtime.trigger_ops import _trigger_agent_impl
    return _trigger_agent_impl(agent, task_description, context_files)

@mcp.tool()
def brain_get_triggers() -> List[Dict]:
    """Get all defined neural triggers from triggers.json."""
    from .runtime.trigger_ops import _get_triggers_impl
    return _get_triggers_impl()

@mcp.tool()
def brain_evaluate_triggers(event_type: str, emitter: str) -> List[str]:
    """Evaluate which agents should activate for a given event type and emitter."""
    from .runtime.trigger_ops import _evaluate_triggers_impl
    return _evaluate_triggers_impl(event_type, emitter)

# ============================================================
# V2 TASK MANAGEMENT TOOLS
# ============================================================

@mcp.tool()
def brain_list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    skill: Optional[str] = None,
    claimed_by: Optional[str] = None
) -> str:
    """List tasks with optional filters."""
    tasks = _list_tasks(status, priority, skill, claimed_by)
    return make_response(True, data=tasks)

@mcp.tool()
def brain_get_next_task(skills: List[str]) -> str:
    """Get the highest-priority unblocked task."""
    task = _get_next_task(skills)
    if task:
        return make_response(True, data=task)
    return make_response(True, data=None, error="No matching tasks found")

@mcp.tool()
def brain_claim_task(task_id: str, agent_id: str) -> str:
    """Atomically claim a task."""
    result = _claim_task(task_id, agent_id)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_update_task(task_id: str, updates: Dict[str, Any]) -> str:
    """Update task fields."""
    result = _update_task(task_id, updates)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_add_task(
    description: str,
    priority: int = 3,
    blocked_by: List[str] = None,
    required_skills: List[str] = None,
    source: str = "synthesizer",
    task_id: str = None,
    skip_dep_check: bool = False
) -> str:
    """Create a new task in the queue.
    
    Args:
        description: Task description
        priority: 1-5 (1=highest)
        blocked_by: Optional list of task IDs that block this task
        required_skills: Optional list of skills needed
        source: Emitter name
        task_id: Optional custom ID (semantic)
        skip_dep_check: For bulk imports to bypass referential integrity check
    """
    result = _add_task(description, priority, blocked_by, required_skills, source, task_id, skip_dep_check)
    if result.get("success"):
        return make_response(True, data=result.get("task"))
    return make_response(False, error=result.get("error"))

# Bulk task import logic moved to runtime/task_ops.py



@mcp.tool()
def brain_import_tasks_from_jsonl(jsonl_path: str, clear_existing: bool = False, merge_gtm_metadata: bool = True) -> str:
    """Import tasks from a JSONL file.
    
    Args:
        jsonl_path: Path to tasks.jsonl (relative to brain or absolute)
        clear_existing: Whether to wipe the current queue
        merge_gtm_metadata: Whether to preserve environment/model fields for GTM
    """
    result = _import_tasks_from_jsonl(jsonl_path, clear_existing, merge_gtm_metadata)
    if result.get("success"):
        return make_response(True, data=result)
    return make_response(False, error=result.get("error"))

@mcp.tool()
def brain_escalate(task_id: str, reason: str) -> Dict:
    """Escalate a task to request human help.
    
    Args:
        task_id: The task ID or description to escalate
        reason: Why the agent needs human help
    
    Returns:
        Result with success boolean and updated task or error
    """
    return _escalate_task(task_id, reason)

# ============================================================
# DEPTH TRACKER TOOLS (ADHD Accommodation)
# ============================================================

@mcp.tool()
def brain_depth_push(topic: str) -> Dict:
    """Go deeper into a subtopic."""
    result = _depth_push(topic)
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_pop() -> str:
    """Come back up one level."""
    result = _depth_pop()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_show() -> str:
    """Show current depth state."""
    result = _depth_show()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_reset() -> str:
    """Reset depth to root level."""
    result = _depth_reset()
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_set_max(max_depth: int) -> str:
    """Set the maximum safe depth."""
    result = _depth_set_max(max_depth)
    return make_response(True, data=result)

@mcp.tool()
def brain_depth_map() -> str:
    """Generate exploration map."""
    result = _generate_depth_map()
    return make_response(True, data=result)

# ============================================================
# RENDER POLLER TOOLS (Deploy monitoring)
# ============================================================



@mcp.tool()
def brain_start_deploy_poll(service_id: str, commit_sha: str = None) -> Dict:
    """Start monitoring a Render deploy. 
    
    Call this after git push to start tracking deploy status.
    The system will log events and you can check status with brain_check_deploy().
    
    Args:
        service_id: Render service ID (e.g., 'srv-abc123')
        commit_sha: Optional Git commit SHA being deployed
    
    Returns:
        Poll ID and instructions for checking status
    """
    return _start_deploy_poll(service_id, commit_sha)

@mcp.tool()
def brain_check_deploy(service_id: str) -> Dict:
    """Check status of an active deploy poll.
    
    Returns elapsed time and instructions. Use mcp_render_list_deploys()
    to get actual status from Render, then call brain_complete_deploy()
    when the deploy finishes.
    
    Args:
        service_id: Render service ID to check
    
    Returns:
        Current poll status and next action hints
    """
    return _check_deploy_status(service_id)

@mcp.tool()
def brain_complete_deploy(service_id: str, success: bool, deploy_url: str = None,
                          error: str = None, run_smoke_test: bool = True) -> Dict:
    """Mark a deploy as complete and optionally run smoke test.
    
    Call this when you see the deploy is 'live' in Render.
    If success=True and deploy_url is provided, runs a health check.
    
    Args:
        service_id: Render service ID
        success: True if deploy succeeded, False if failed
        deploy_url: URL of deployed service (for smoke test)
        error: Error message if deploy failed
        run_smoke_test: Whether to run health check (default True)
    
    Returns:
        Final status with smoke test results
    """
    return _complete_deploy(service_id, success, deploy_url, error, run_smoke_test)

@mcp.tool()
def brain_smoke_test(url: str, endpoint: str = "/api/health") -> Dict:
    """Run a smoke test on any URL.
    
    Useful for quick health checks without full deploy workflow.
    
    Args:
        url: Base URL of service (e.g., 'https://myapp.onrender.com')
        endpoint: Health endpoint to hit (default: '/api/health')
    
    Returns:
        Smoke test result with pass/fail and latency
    """
    return _run_smoke_test(url, endpoint)

# ============================================================
# MCP RESOURCES (Subscribable data)
# ============================================================

@mcp.resource("brain://state")
def resource_state() -> str:
    """Live state.json content - subscribable."""
    state = _get_state()
    return json.dumps(state, indent=2)

@mcp.resource("brain://events")
def resource_events() -> str:
    """Recent events - subscribable."""
    events = _read_events(limit=20)
    return json.dumps(events, indent=2)

@mcp.resource("brain://triggers")
def resource_triggers() -> str:
    """Trigger definitions - subscribable."""
    triggers = _get_triggers_impl()
    return json.dumps(triggers, indent=2)

@mcp.resource("brain://depth")
def resource_depth() -> str:
    """Current depth tracking state - subscribable. Shows where you are in the conversation tree."""
    depth_state = _depth_show()
    return json.dumps(depth_state, indent=2)

@mcp.resource("brain://context")
def resource_context() -> str:
    """Full context for cold start - auto-visible in sidebar. Click this first in any new session."""
    return _resource_context_impl()

# ============================================================
# MCP PROMPTS (Pre-built orchestration)
# ============================================================

@mcp.prompt()
def activate_synthesizer() -> str:
    """Activate Synthesizer agent to orchestrate the current sprint."""
    return _activate_synthesizer_prompt()

@mcp.prompt()
def start_sprint(goal: str = "MVP Launch") -> str:
    """Initialize a new sprint with the given goal."""
    return _start_sprint_prompt(goal)

@mcp.prompt()
def cold_start() -> str:
    """Get instant context when starting a new session. Call this first in any new conversation."""
    return _cold_start_prompt()

# ============================================================
# ============================================================
# SATELLITE VIEW (Unified Status Dashboard) — Extracted to runtime/satellite_ops.py
# ============================================================

from .runtime.satellite_ops import (
    _generate_sparkline,
    _get_activity_sparkline,
    _get_health_stats,
    _get_satellite_view,
    _format_satellite_cli,
)

@mcp.tool()
def brain_satellite_view(detail_level: str = "standard") -> str:
    """
    Get unified satellite view of the brain.
    
    Shows depth, activity, health, and session in one view.
    
    Args:
        detail_level: "minimal", "standard", or "full"
    
    Returns:
        Formatted satellite view
    """
    view = _get_satellite_view(detail_level)
    formatted = _format_satellite_cli(view)
    return make_response(True, data=formatted)

# ============================================================
# COMMITMENT LEDGER MCP TOOLS (PEFS Phase 2)
# ============================================================

@mcp.tool()
def brain_scan_commitments() -> str:
    """
    Scan artifacts for new commitments (checklists, TODOs).
    Updates the ledger with any new items found.
    (MDR_005 Compliant: Logic moved to shared library)
    
    Returns:
        Scan results
    """
    try:
        brain = get_brain_path()
        result = commitment_ledger.scan_for_commitments(brain)
        return f"✅ Scan complete. Found {result.get('new_found', 0)} new items."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_archive_stale() -> str:
    """
    Auto-archive commitments older than 30 days.
    
    Returns:
        Count of archived items
    """
    try:
        brain = get_brain_path()
        count = commitment_ledger.auto_archive_stale(brain)
        return f"✅ Archive complete. Archived {count} stale items."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_export() -> str:
    """
    Export the brain content to a zip file in .brain/exports/.
    Respects .brain/.brainignore patterns to protect IP.
    (MDR_008 Compliance)
    
    Returns:
        Path to the exported zip file
    """
    try:
        brain = get_brain_path()
        if hasattr(commitment_ledger, 'export_brain'):
            result = commitment_ledger.export_brain(brain)
            return f"✅ {result}"
        return "Error: export_brain validation failed (function missing)."
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_list_commitments(tier: str = None) -> str:
    """
    List all open commitments.
    
    Args:
        tier: Optional filter by tier ("green", "yellow", "red")
    
    Returns:
        List of open commitments with details
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        
        # Filter open commitments by tier if specified
        all_commitments = ledger.get('commitments', [])
        commitments = [c for c in all_commitments if c.get('status') == 'open']
        if tier:
            commitments = [c for c in commitments if c.get('tier') == tier]
        
        if not commitments:
            return "✅ No open commitments!"
        
        output = f"**Open Commitments ({len(commitments)} total)**\n\n"
        
        for comm in commitments:
            tier_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(comm["tier"], "⚪")
            output += f"{tier_emoji} **{comm['description'][:60]}**\n"
            output += f"   Age: {comm['age_days']} days | Suggested: {comm['suggested_action']}\n"
            output += f"   Reason: {comm['suggested_reason']}\n"
            output += f"   ID: `{comm['id']}`\n\n"
        
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_close_commitment(commitment_id: str, method: str) -> str:
    """
    Close a commitment with specified method.
    
    Args:
        commitment_id: The commitment ID (e.g., comm_20260106_163000_0)
        method: Closure method (do_now, scheduled, archived, killed, delegated)
    
    Returns:
        Confirmation with updated commitment
    """
    try:
        brain = get_brain_path()
        commitment = commitment_ledger.close_commitment(brain, commitment_id, method)
        
        # Emit event
        _emit_event(
            "commitment_closed",
            "user",
            {"commitment_id": commitment_id, "method": method},
            description=f"Closed: {commitment['description'][:50]}"
        )
        
        return f"""✅ Commitment closed!

**Description:** {commitment['description']}
**Method:** {method}
**Was open:** {commitment['age_days']} days
**Closed at:** {commitment['closed_at']}"""
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_commitment_health() -> str:
    """
    Get commitment health summary.
    
    Shows open loop count, tier breakdown, and mental load estimate.
    Useful for quick status check.
    
    Returns:
        Health summary with actionable insights
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        stats = ledger.get("stats", {})
        
        total = stats.get("total_open", 0)
        green = stats.get("green_tier", 0)
        yellow = stats.get("yellow_tier", 0)
        red = stats.get("red_tier", 0)
        by_type = stats.get("by_type", {})
        
        # Mental load calculation
        if red > 0:
            mental_load = "🔴 HIGH"
            advice = "Focus on red-tier items first"
        elif yellow > 2:
            mental_load = "🟡 MEDIUM"
            advice = "Clear yellow items before they go red"
        elif total == 0:
            mental_load = "✨ ZERO"
            advice = "No open loops - guilt-free operation!"
        else:
            mental_load = "🟢 LOW"
            advice = "Looking good, maintain momentum"
        
        # Format by_type
        type_str = ", ".join([f"{t}: {c}" for t, c in by_type.items()]) if by_type else "(none)"
        
        return f"""## 🎯 Commitment Health

**Open loops:** {total}
- 🟢 Green: {green}
- 🟡 Yellow: {yellow}
- 🔴 Red: {red}

**By type:** {type_str}

**Mental load:** {mental_load}
**Advice:** {advice}

**Last scan:** {ledger.get('last_scan', 'Never')[:16] if ledger.get('last_scan') else 'Never'}"""
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def brain_open_loops(
    type_filter: str = None,
    tier_filter: str = None
) -> str:
    """
    Unified view of ALL open loops (tasks, todos, drafts, decisions).
    
    This is the single source of truth for what needs attention.
    Replaces the need to check separate task/commitment systems.
    
    Args:
        type_filter: Filter by type ("task", "todo", "draft", "decision")
        tier_filter: Filter by tier ("green", "yellow", "red")
    
    Returns:
        All open loops grouped by type and priority
    """
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        
        open_comms = [c for c in ledger["commitments"] if c["status"] == "open"]
        
        # Apply filters
        if type_filter:
            open_comms = [c for c in open_comms if c.get("type") == type_filter]
        if tier_filter:
            open_comms = [c for c in open_comms if c.get("tier") == tier_filter]
        
        if not open_comms:
            return "✅ No open loops! Guilt-free operation."
        
        # Group by type
        by_type = {}
        for c in open_comms:
            t = c.get("type", "unknown")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(c)
        
        # Build output
        output = f"## 📋 Open Loops ({len(open_comms)} total)\n\n"
        
        type_emoji = {"task": "🔧", "todo": "☑️", "draft": "📝", "decision": "🤔"}
        
        for t, items in by_type.items():
            emoji = type_emoji.get(t, "📌")
            output += f"### {emoji} {t.upper()} ({len(items)})\n\n"
            
            # Sort by tier (red first) then age
            items.sort(key=lambda x: ({"red": 0, "yellow": 1, "green": 2}.get(x.get("tier"), 3), -x.get("age_days", 0)))
            
            for c in items[:5]:  # Max 5 per type
                tier_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(c.get("tier"), "⚪")
                output += f"{tier_emoji} **{c['description'][:50]}**\n"
                output += f"   {c.get('age_days', 0)}d old | Suggested: {c.get('suggested_action')}\n"
                output += f"   ID: `{c['id']}`\n\n"
            
            if len(items) > 5:
                output += f"   ...and {len(items) - 5} more\n\n"
        
        return output
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_add_loop(
    description: str,
    loop_type: str = "task",
    priority: int = 3
) -> str:
    """
    Manually add a new open loop (task, todo, draft, or decision).
    
    Use this when you want to track something that isn't in a document.
    
    Args:
        description: What needs to be done
        loop_type: Type of loop ("task", "todo", "draft", "decision")
        priority: 1-5, lower is higher priority
    
    Returns:
        Created loop details
    """
    try:
        brain = get_brain_path()
        commitment = commitment_ledger.add_commitment(
            brain,
            source_file="manual",
            source_line=0,
            description=description,
            comm_type=loop_type,
            source="manual",
            priority=priority
        )
        
        # Emit event for orchestration
        try:
            _emit_event(
                "commitment_created",
                "brain_add_loop",
                {
                    "commitment_id": commitment['id'],
                    "type": loop_type,
                    "description": description[:60],
                    "priority": priority,
                    "tier": commitment.get('tier', 'green')
                },
                description=f"New {loop_type}: {description[:40]}"
            )
        except Exception:
            pass  # Don't fail loop creation if event emission fails
        
        return f"""✅ Loop created!

**ID:** `{commitment['id']}`
**Type:** {loop_type}
**Description:** {description}
**Priority:** {priority}
**Suggested:** {commitment['suggested_action']} - {commitment['suggested_reason']}"""
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_weekly_challenge(
    action: str = "get",  # get, set, list
    challenge_id: str = None
) -> str:
    """
    Manage the weekly growth challenge.
    
    Args:
        action: "get" (current status), "set" (start new), "list" (show options)
        challenge_id: ID of challenge to set (if action="set")
    
    Returns:
        Challenge status or list of options
    """
    try:
        brain = get_brain_path()
        
        if action == "list":
            challenges = commitment_ledger.get_starter_challenges()
            output = "## 🏆 Weekly Challenges\n\n"
            for c in challenges:
                output += f"**{c['title']}** (`{c['id']}`)\n"
                output += f"{c['description']}\n"
                output += f"🏆 Reward: {c['reward']}\n\n"
            return output
            
        if action == "set":
            if not challenge_id:
                return "⚠️ Please provide `challenge_id` to set a challenge."
            
            challenges = commitment_ledger.get_starter_challenges()
            selected = next((c for c in challenges if c["id"] == challenge_id), None)
            
            if not selected:
                return f"❌ Challenge `{challenge_id}` not found."
            
            # Start fresh
            selected["started_at"] = datetime.now().isoformat()
            selected["status"] = "active"
            commitment_ledger.set_challenge(brain, selected)
            
            return f"✅ **Challenge Accepted: {selected['title']}**\n\nGoal: {selected['description']}\nGo get it!"
            
        # Default: get
        challenge = commitment_ledger.load_challenge(brain)
        if not challenge:
            return "No active challenge. Run `brain_weekly_challenge(action='list')` to pick one!"
            
        return f"""## 🏆 Current Challenge: {challenge['title']}

📝 **Goal:** {challenge['description']}
📅 **Started:** {challenge['started_at'][:10]}
🎁 **Reward:** {challenge['reward']}

Keep pushing!"""

    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_patterns(
    action: str = "list",  # list, learn
) -> str:
    """
    Manage learned patterns for commitment closure.
    
    Args:
        action: "list" (show learned patterns), "learn" (scan ledger for new patterns)
    
    Returns:
        List of patterns or learning result
    """
    try:
        brain = get_brain_path()
        
        if action == "learn":
            patterns = commitment_ledger.learn_patterns(brain)
            return f"✅ Learning complete. Total patterns: {len(patterns)}"
            
        # List
        patterns = commitment_ledger.load_patterns(brain)
        if not patterns:
            return "No patterns learned yet. Run `brain_patterns(action='learn')` after closing some items!"
            
        output = "## 🧠 Learned Patterns\n\n"
        for p in patterns:
            output += f"**{p['name']}**\n"
            output += f"• Keywords: {', '.join(p['keywords'])}\n"
            output += f"• Action: {p['action']}\n\n"
            
        return output

    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_metrics() -> str:
    """
    Get coordination metrics (velocity, closure rates, mental load).
    
    Returns:
        Formatted metrics report
    """
    try:
        brain = get_brain_path()
        metrics = commitment_ledger.calculate_metrics(brain)
        
        output = "## 📊 Coordination Metrics (Last 7 Days)\n\n"
        output += f"**🚀 Velocity:** {metrics['velocity_7d']} items closed\n"
        output += f"**⏱️ Speed:** {metrics['avg_days_to_close']} days avg to close\n\n"
        
        output += "**📈 Closure Rates by Type:**\n"
        if metrics['closure_rates']:
            for t, rate in metrics['closure_rates'].items():
                output += f"- {t}: {rate}\n"
        else:
            output += "(No closed items yet)\n"
            
        output += "\n**🧠 Current Load:**\n"
        output += f"- Total Open: {metrics['current_load']['total']}\n"
        output += f"- Red Tier: {metrics['current_load']['red']}\n"
        
        return output

    except Exception as e:
        return f"Error: {e}"

    except Exception as e:
        return f"Error: {e}"

# Internal proof functions removed (moved to runtime/proof_ops.py)


# ============================================================
# MULTI-TIER LLM MANAGEMENT TOOLS
# ============================================================

@mcp.tool()
def brain_set_llm_tier(tier: str) -> str:
    """
    Set the default LLM tier for agent spawning.
    
    Available tiers:
    - premium: gemini-2.5-pro (high quality, higher cost)
    - standard: gemini-2.5-flash (default, balanced)
    - economy: gemini-2.5-flash-lite (low cost, background tasks)
    - local_paid: API Key mode with billing
    - local_free: API Key free tier (100 req/day)
    
    Args:
        tier: One of the available tier names
    
    Returns:
        Confirmation message
    """
    import os
    valid_tiers = ["premium", "standard", "economy", "local_paid", "local_free"]
    
    if tier.lower() not in valid_tiers:
        return f"❌ Invalid tier '{tier}'. Valid tiers: {', '.join(valid_tiers)}"
    
    # Set environment variable for the session
    os.environ["NUCLEUS_LLM_TIER"] = tier.lower()
    
    return f"✅ LLM tier set to '{tier}'. All subsequent agent spawns will use this tier."


@mcp.tool()
def brain_get_llm_status() -> str:
    """
    Get current LLM tier configuration and available tiers.
    
    Returns:
        Status report with current tier, available models, and benchmark results.
    """
    import os
    import json
    from pathlib import Path
    
    brain = get_brain_path()
    tier_status_path = brain / "tier_status.json"
    
    output = "## 🧠 LLM Tier Status\n\n"
    
    # Current settings
    current_tier = os.environ.get("NUCLEUS_LLM_TIER", "auto (standard)")
    force_vertex = os.environ.get("FORCE_VERTEX", "1")
    
    output += f"**Current Tier:** {current_tier}\n"
    output += f"**Vertex Mode:** {'Enabled' if force_vertex == '1' else 'Disabled'}\n\n"
    
    # Load cached tier status if available
    if tier_status_path.exists():
        try:
            with open(tier_status_path) as f:
                status = json.load(f)
            
            output += "### Available Tiers (from last benchmark)\n"
            output += "| Tier | Model | Status | Latency |\n"
            output += "|------|-------|--------|--------|\n"
            
            for tier_name, result in status.get("tier_results", {}).items():
                status_emoji = "✅" if result.get("status") == "SUCCESS" else "❌"
                latency = f"{result.get('latency_ms', '-')}ms" if result.get('latency_ms') else "-"
                output += f"| {tier_name} | {result.get('model', 'unknown')} | {status_emoji} {result.get('status')} | {latency} |\n"
            
            output += f"\n**Recommended:** {status.get('recommended_tier', 'standard')}\n"
            output += f"**Last Benchmark:** {status.get('run_timestamp', 'unknown')}\n"
        except Exception as e:
            output += f"Could not load tier status: {e}\n"
    else:
        output += "No benchmark data available. Run `test_llm_tiers.py --save` to generate.\n"
    
    return output


@mcp.tool()
async def brain_spawn_agent(
    intent: str,
    execute_now: bool = True,
    persona: str = None
) -> str:
    """
    Spawn an Ephemeral Agent via the Nucleus Agent Runtime (NAR).
    The factory constructs a context based on intent and launches a disposable agent.
    MDR_044: Now uses Dual-Engine LLM with intelligent tier routing.
    
    Args:
        intent: The high-level goal (e.g., "Deploy production service")
        execute_now: Whether to run immediately or just return the plan.
        persona: Optional explicit persona to use (e.g., 'developer', 'devops')
        
    Returns:
        Execution log or plan details.
    """
    try:
        from uuid import uuid4
        from .runtime.llm_client import DualEngineLLM, LLMTier, TierRouter
        
        session_id = f"spawn-{str(uuid4())[:8]}"
        from .runtime.factory import ContextFactory
        from .runtime.agent import EphemeralAgent

        factory = ContextFactory()
        
        if persona:
            context = factory.create_context_for_persona(session_id, persona, intent)
        else:
            context = factory.create_context(session_id, intent)
        
        # Get job_type from context for tier routing
        job_type = context.get("job_type", "ORCHESTRATION")
        
        output = "## 🏭 NAR Factory Receipt\n"
        output += f"**Intent:** {intent}\n"
        output += f"**Persona:** {context.get('persona', 'Unknown')}\n"
        output += f"**Job Type:** {job_type}\n"
        output += f"**Capabilities:** {', '.join(context['capabilities'])}\n"
        output += f"**Tools Mapped:** {len(context['tools'])}\n"
        
        if not context['tools']:
            return output + "\n❌ No tools mapped. Agent would be powerless."
            
        if execute_now:
            output += "\n--- Executive Trace (Tier-Routed) ---\n"
            
            # Initialize with tier routing based on job_type
            llm = DualEngineLLM(job_type=job_type)
            
            output += f">> 🎯 Tier: {llm.tier.value if llm.tier else 'default'}\n"
            output += f">> 🧠 Model: {llm.model_name}\n"
            output += f">> ⚡ Engine: {llm.active_engine}\n"
            
            agent = EphemeralAgent(context, model=llm)
            log = await agent.run()
            output += log + "\n"
            output += "✅ Ephemeral Agent executed and terminated.\n"
            
        return output

    except Exception as e:
        return f"Error spawning agent: {e}"


# ============================================================
# MDR_010: USAGE TELEMETRY & FEEDBACK MCP TOOLS
# ============================================================

@mcp.tool()
def brain_record_interaction() -> str:
    """
    Record a user interaction timestamp (MDR_010).
    Call this when the user engages with any brain functionality.
    """
    return _brain_record_interaction_impl()

@mcp.tool()
def brain_value_ratio() -> str:
    """
    Get the Value Ratio metric (MDR_010).
    Value Ratio = High Impact Closures / Notifications Sent.
    """
    return _brain_value_ratio_impl()

@mcp.tool()
def brain_check_kill_switch() -> str:
    """
    Check Kill Switch status (MDR_010).
    Detects inactivity and suggests pausing notifications.
    """
    return _brain_check_kill_switch_impl()

@mcp.tool()
def brain_pause_notifications() -> str:
    """
    Pause all PEFS notifications (Kill Switch activation).
    Call this when the user requests to stop notifications.
    """
    return _brain_pause_notifications_impl()

@mcp.tool()
def brain_resume_notifications() -> str:
    """
    Resume PEFS notifications after pause.
    """
    return _brain_resume_notifications_impl()

@mcp.tool()
def brain_record_feedback(notification_type: str, score: int) -> str:
    """
    Record user feedback on a notification (MDR_010).
    
    Args:
        notification_type: Type of notification (e.g., 'daily', 'red_tier', 'challenge')
        score: Feedback score (1-5, where 5=helpful, 1=noise)
    """
    return _brain_record_feedback_impl(notification_type, score)

@mcp.tool()
def brain_mark_high_impact() -> str:
    """
    Manually mark a loop closure as high-impact (MDR_010).
    Use when a notification led to a meaningful outcome.
    """
    return _brain_mark_high_impact_impl()


# Session start impl extracted to runtime/session_ops.py
from .runtime.session_ops import _brain_session_start_impl

@mcp.tool()
def brain_session_start() -> str:
    """
    START HERE - Mandatory session start protocol.
    
    Returns current Brain state to drive your work:
    - Satellite view (depth, activity, health)
    - Top 5 pending tasks by priority
    - Active sprint (if any)
    - Recommendations
    
    CRITICAL: Call this BEFORE starting significant work.
    Read AGENT_PROTOCOL.md for full workflow.
    
    Returns:
        Formatted report with priorities and recommendations
    """
    return _brain_session_start_impl()

def _check_protocol_compliance(agent_id: str) -> Dict:
    """Check if agent is following multi-agent coordination protocol."""
    try:
        brain = get_brain_path()
        violations = []
        warnings = []
        
        # Load protocol
        protocol_path = brain / "protocols" / "multi_agent_mou.json"
        if not protocol_path.exists():
            return {
                "compliant": True,
                "message": "Protocol file not found - operating in standalone mode",
                "violations": [],
                "warnings": []
            }
        
        with open(protocol_path) as f:
            protocol = json.load(f)
        
        # Check 1: Is agent registered?
        agents = protocol.get("agents", {})
        if agent_id not in agents:
            warnings.append(f"Agent '{agent_id}' not in protocol registry")
        
        # Check 2: Any IN_PROGRESS tasks claimed by other agents?
        from .runtime.db import get_storage_backend
        tasks = get_storage_backend(brain).list_tasks()
        in_progress = [t for t in tasks if t.get("status") == "IN_PROGRESS"]
        
        other_agent_tasks = [
            t for t in in_progress 
            if t.get("claimed_by") and t.get("claimed_by") != agent_id
        ]
        
        if other_agent_tasks:
            for t in other_agent_tasks:
                warnings.append(
                    f"Task '{t.get('id')}' claimed by {t.get('claimed_by')} - do not overlap"
                )
        
        # Check 3: Environment routing
        pending_tasks = [t for t in tasks if t.get("status") == "PENDING"]
        agent_env = agents.get(agent_id, {}).get("environment")
        
        routed_to_me = [
            t for t in pending_tasks 
            if t.get("environment") == agent_env
        ]
        
        # Build compliance report
        compliant = len(violations) == 0
        
        return {
            "compliant": compliant,
            "agent_id": agent_id,
            "agent_role": agents.get(agent_id, {}).get("role", "unknown"),
            "violations": violations,
            "warnings": warnings,
            "active_agents": list(agents.keys()),
            "tasks_for_me": [t.get("id") for t in routed_to_me],
            "tasks_in_progress_by_others": [
                {"id": t.get("id"), "claimed_by": t.get("claimed_by")} 
                for t in other_agent_tasks
            ],
            "protocol_version": protocol.get("version", "unknown"),
            "message": "Protocol compliance check complete"
        }
    except Exception as e:
        return {
            "compliant": False,
            "error": str(e),
            "violations": [f"Protocol check failed: {str(e)}"],
            "warnings": []
        }


@mcp.tool()
def brain_check_protocol(agent_id: str) -> str:
    """
    Check multi-agent coordination protocol compliance.
    
    Call this at session start to verify you're following the MoU.
    Returns violations (blocking) and warnings (informational).
    
    Args:
        agent_id: Your agent ID (e.g., 'windsurf_exec_001')
    
    Returns:
        Compliance report with violations, warnings, and task routing info
    
    Example:
        brain_check_protocol("windsurf_exec_001")
    """
    from .runtime.slot_ops import _check_protocol_compliance
    result = _check_protocol_compliance(agent_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def brain_request_handoff(
    to_agent: str,
    context: str,
    request: str,
    priority: int = 3,
    artifacts: List[str] = None
) -> str:
    """
    Request a handoff to another agent via the shared brain.
    
    Creates a handoff request that the other agent (or human) can see.
    Use this when you need another agent to continue work.
    
    Args:
        to_agent: Target agent ID (e.g., 'antigravity_exec_001')
        context: Brief context about current state
        request: What you need them to do
        priority: 1-5 (1=critical)
        artifacts: List of files they should read
    
    Returns:
        Handoff request confirmation
    """
    from .runtime.slot_ops import _brain_request_handoff_impl
    return _brain_request_handoff_impl(to_agent, context, request, priority, artifacts)


@mcp.tool()
def brain_get_handoffs(agent_id: str = None) -> str:
    """
    Get pending handoff requests for an agent.
    
    Args:
        agent_id: Filter to handoffs for this agent (optional)
    
    Returns:
        List of pending handoff requests
    """
    from .runtime.slot_ops import _brain_get_handoffs_impl
    return _brain_get_handoffs_impl(agent_id)



# Orchestration helpers extracted to runtime/orch_helpers.py
from .runtime.orch_helpers import (
    _get_slot_registry, _save_slot_registry, _get_tier_definitions,
    _get_tier_for_model, _resolve_slot_id, _infer_task_tier,
    _can_slot_run_task, _compute_slot_blockers, _increment_fence_token,
    _get_model_cost, _compute_dependency_graph, _score_slot_for_task,
    _claim_with_fence, _complete_with_fence,
)

# Orchestration impl extracted to runtime/orchestrate_ops.py
from .runtime.orchestrate_ops import _brain_orchestrate_impl

@mcp.tool()
def brain_orchestrate(
    slot_id: str = None,
    model: str = None,
    alias: str = None,
    mode: str = "auto"
) -> str:
    """
    THE GOD COMMAND - Single entry point for all slot operations.
    
    Modes:
    - register: Create new slot with model/alias
    - auto: Check status + auto-claim best task + return instructions
    - guided: Check status + show options + wait for human choice
    - report: Just show status, no actions
    
    Args:
        slot_id: Your slot ID or alias (e.g., 'windsurf_001' or 'ws_opus')
        model: Model name for registration (e.g., 'claude_opus_4.5')
        alias: Human-friendly alias for slot
        mode: Operation mode - 'auto', 'guided', 'report', 'register'
    
    Returns:
        JSON with guaranteed schema - no interpretation needed.
        
    Example:
        brain_orchestrate("windsurf_001", mode="auto")
        brain_orchestrate(slot_id="new_slot", model="gemini_3_pro_high", mode="register")
    """
    return _brain_orchestrate_impl(slot_id, model, alias, mode)


@mcp.tool()
def brain_slot_complete(slot_id: str, task_id: str, outcome: str = "success", notes: str = None) -> str:
    """
    Mark a task as complete and get next task.
    
    Args:
        slot_id: Your slot ID
        task_id: Task you just completed
        outcome: 'success' or 'failed'
        notes: Optional completion notes
    
    Returns:
        Updated status and next task recommendation
    """
    from .runtime.slot_ops import _brain_slot_complete_impl
    
    # Call completion logic
    result = _brain_slot_complete_impl(slot_id, task_id, outcome, verification_notes=notes)
    
    # Get next task (Legacy behavior)
    next_task = _brain_orchestrate_impl(slot_id=slot_id, mode="auto")
    
    return f"{result}\n\nNext Task:\n{next_task}"


@mcp.tool()
def brain_slot_exhaust(slot_id: str, reset_hours: int = 5) -> str:
    """
    Mark slot as exhausted (model hit usage limit).
    
    Args:
        slot_id: Your slot ID
        reset_hours: Hours until model resets (default: 5 for Gemini)
    
    Returns:
        Confirmation with reset time
    """
    from .runtime.slot_ops import _brain_slot_exhaust_impl
    reset_at = time.time() + (reset_hours * 3600)
    reset_at_str = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(reset_at))
    return _brain_slot_exhaust_impl(slot_id, reason="Model usage limit", reset_at=reset_at_str)

# ============================================================================
# NOP V3.1: STATUS DASHBOARD - VISUAL MONITORING
# ============================================================================

@mcp.tool()
def brain_status_dashboard(detail_level: str = "standard") -> str:
    """
    Generate ASCII dashboard of slot status/health (Legacy V3.0).
    
    Args:
        detail_level: 'standard' or 'full' (full includes costs)
    
    Returns:
        ASCII table status report
    """
    from .runtime.slot_ops import _brain_status_dashboard_impl
    return _brain_status_dashboard_impl(detail_level)


# ============================================================================
# NOP V3.1: CHECKPOINT TOOLS - PAUSE/RESUME FOR LONG-RUNNING TASKS

# Checkpoint impls extracted to runtime/checkpoint_ops.py
from .runtime.checkpoint_ops import (
    _brain_checkpoint_task_impl,
    _brain_resume_from_checkpoint_impl,
    _brain_generate_handoff_summary_impl,
)
# ============================================================================

@mcp.tool()
def brain_checkpoint_task(
    task_id: str,
    step: int = None,
    progress_percent: float = None,
    context: str = None,
    artifacts: List[str] = None,
    resumable: bool = True
) -> str:
    """
    Save checkpoint for long-running task.
    
    Use this to persist progress before:
    - Agent exhaustion (rate limits, reset cycles)
    - Session end
    - Handoff to another agent
    
    Args:
        task_id: Task to checkpoint
        step: Current step number (e.g., 3 of 5)
        progress_percent: 0-100 completion percentage
        context: Textual context for resume
        artifacts: List of artifact paths created so far
        resumable: Whether task can be resumed from this point
    
    Returns:
        Checkpoint confirmation with recovery instructions
    """
    return _brain_checkpoint_task_impl(task_id, step, progress_percent, context, artifacts, resumable)


@mcp.tool()
def brain_resume_from_checkpoint(task_id: str) -> str:
    """
    Get checkpoint data for task resumption.
    
    Use this when:
    - Resuming after agent exhaustion
    - Taking over from another agent
    - Continuing after session restart
    
    Args:
        task_id: Task to resume
    
    Returns:
        Checkpoint data with context and resume instructions
    """
    return _brain_resume_from_checkpoint_impl(task_id)


@mcp.tool()
def brain_generate_handoff_summary(
    task_id: str,
    summary: str,
    key_decisions: List[str] = None,
    handoff_notes: str = ""
) -> str:
    """
    Generate context summary for task handoff.
    
    Use this before:
    - Handing off to another agent
    - Ending a session with incomplete work
    - Approaching reset cycle limit
    
    Args:
        task_id: Task to summarize
        summary: Brief summary of current state
        key_decisions: List of decisions made during work
        handoff_notes: Notes for the next agent
    
    Returns:
        Confirmation of summary generation
    """
    return _brain_generate_handoff_summary_impl(task_id, summary, key_decisions, handoff_notes)




# ============================================================================
# NOP V3.0: THE SPRINT COMMAND - MULTI-SLOT ORCHESTRATION
# ============================================================================

@mcp.tool()
def brain_autopilot_sprint(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    dry_run: bool = False
) -> str:
    """
    THE SPRINT COMMAND - Orchestrate multiple slots in parallel.
    
    This is the ENTERPRISE upgrade over brain_orchestrate().
    Coordinates a TEAM of slots working simultaneously.
    
    Args:
        slots: Slot IDs to orchestrate (None = all active slots)
        mode: 'auto' (execute), 'plan' (show what would happen), 'status' (current state)
        halt_on_blocker: Stop if circular dependency detected
        halt_on_tier_mismatch: Stop if task requires higher tier than available
        max_tasks_per_slot: Max tasks to assign per slot in one sprint
        budget_limit: Max cost ($) for entire sprint (None = unlimited)
        dry_run: If True, don't actually claim tasks, just show plan
    
    Returns:
        Sprint execution report with per-slot results.
    
    Example:
        brain_autopilot_sprint()  # All active slots
        brain_autopilot_sprint(slots=["windsurf_001", "antigravity_001"])
        brain_autopilot_sprint(mode="plan", dry_run=True)  # Preview
    """
    from .runtime.slot_ops import _brain_autopilot_sprint_impl
    return _brain_autopilot_sprint_impl(slots, mode, halt_on_blocker, halt_on_tier_mismatch, max_tasks_per_slot, budget_limit, dry_run)


@mcp.tool()
def brain_force_assign(slot_id: str, task_id: str, acknowledge_risk: bool = False) -> str:
    """
    Force assign a task to a slot, overriding tier requirements.
    
    Use this when you MUST run a task on a specific slot despite tier mismatch.
    Requires explicit risk acknowledgment.
    
    Args:
        slot_id: Target slot ID
        task_id: Task to assign
        acknowledge_risk: Must be True to proceed with tier mismatch
    
    Returns:
        Assignment result with warnings
    """
    from .runtime.slot_ops import _brain_force_assign_impl
    return _brain_force_assign_impl(slot_id, task_id, acknowledge_risk)


@mcp.tool()
def brain_file_changes() -> str:
    """
    Get pending file change events from the Brain folder.
    
    Phase 50 Native Sync: Returns a list of files that have changed
    since the last check. Use this to detect updates made by other
    Chats/IDEs/CLI tools.
    
    Returns:
        List of file change events (type, path, timestamp)
    """
    try:
        from .runtime.file_monitor import get_file_monitor
        
        monitor = get_file_monitor()
        if not monitor:
            return json.dumps({
                "status": "disabled",
                "message": "File monitor not initialized. Ensure watchdog is installed.",
                "events": []
            })
        
        if not monitor.is_running:
            return json.dumps({
                "status": "stopped",
                "message": "File monitor is not running.",
                "events": []
            })
        
        events = monitor.get_pending_events()
        return json.dumps({
            "status": "active",
            "event_count": len(events),
            "events": [e.to_dict() for e in events]
        })
        
    except ImportError:
        return json.dumps({
            "status": "unavailable",
            "message": "watchdog library not installed. Run: pip install watchdog",
            "events": []
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "events": []
        })


@mcp.tool()
def brain_gcloud_status() -> str:
    """
    Check GCloud authentication status.
    
    Phase 49 GCloud Integration: Returns the current gcloud configuration
    including active project and authenticated account.
    
    Returns:
        GCloud auth status (project, account, availability)
    """
    try:
        from .runtime.gcloud_ops import get_gcloud_ops
        
        ops = get_gcloud_ops()
        status = ops.check_auth_status()
        return json.dumps(status, indent=2)
        
    except ImportError as e:
        return json.dumps({
            "error": f"GCloudOps module not available: {e}"
        })
    except Exception as e:
        return json.dumps({
            "error": str(e)
        })


@mcp.tool()
def brain_gcloud_services(project: str = None, region: str = "us-central1") -> str:
    """
    List Cloud Run services in a project.
    
    Phase 49 GCloud Integration: Uses your local gcloud auth to query
    infrastructure status. No API keys needed.
    
    Args:
        project: GCP project ID (optional, uses default if not set)
        region: GCP region (default: us-central1)
    
    Returns:
        List of Cloud Run services with status
    """
    try:
        from .runtime.gcloud_ops import GCloudOps
        
        ops = GCloudOps(project=project, region=region)
        
        if not ops.is_available:
            return json.dumps({
                "error": "gcloud CLI not found",
                "install": "https://cloud.google.com/sdk/docs/install"
            })
        
        result = ops.list_cloud_run_services()
        return json.dumps(result.to_dict(), indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e)
        })




@mcp.tool()
def brain_list_services() -> str:
    """
    List Render.com services.
    
    Returns:
        JSON string of service list (Real or Mock).
    """
    try:
        from .runtime.render_ops import get_render_ops
        ops = get_render_ops()
        return json.dumps(ops.list_services(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================
# MARKETING ADAPTIVE PROTOCOLS (Self-healing)
# ============================================================

def _scan_marketing_log() -> Dict:
    """Scan marketing_log.md for failures."""
    try:
        # Try relative path first (repo root)
        log_path = Path("docs/marketing/marketing_log.md")
        if not log_path.exists():
            # Fallback to absolute path
            log_path = Path("/Users/lokeshgarg/ai-mvp-backend/docs/marketing/marketing_log.md")
            
        if not log_path.exists():
            return {"status": "error", "error": f"Marketing log not found at {log_path}"}
            
        failures = []
        with open(log_path, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "[FAILURE]" in line:
                    tag = "UNKNOWN"
                    if "[AUTH_LOCKED]" in line:
                        tag = "AUTH_LOCKED"
                    elif "[SELECTOR_MISSING]" in line:
                        tag = "SELECTOR_MISSING"
                    elif "[TIMEOUT]" in line:
                        tag = "TIMEOUT"
                    elif "[RATE_LIMIT]" in line:
                        tag = "RATE_LIMIT"
                    
                    failures.append({
                        "line_number": i + 1,
                        "tag": tag,
                        "content": line.strip()
                    })
        
        # Sort by most recent (end of file)
        failures.reverse()
        
        return {
            "status": "healthy" if not failures else "degraded",
            "failure_count": len(failures),
            "failures": failures[:5]  # Show last 5
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def brain_scan_marketing_log() -> str:
    """
    Scan the marketing log for failure tags (e.g. [FAILURE], [AUTH_LOCKED]).
    Used by the Adaptive Protocols to trigger self-correction.
    
    Returns:
        JSON string with health status and recent failures.
    """
    result = _scan_marketing_log()
    return json.dumps(result, indent=2)

@mcp.tool()
def brain_synthesize_strategy(focus_topic: Optional[str] = None) -> str:
    """
    [Marketing Engine]
    Analyze marketing logs and update the Strategy Document using GenAI.
    
    Args:
        focus_topic: Optional topic to focus the strategy analysis on.
        
    Returns:
        Review of the synthesis operation.
    """
    # Lazy import of capability
    try:
        from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_synthesize_strategy
        
        result = brain_synthesize_strategy(
            project_root=str(Path.cwd()),
            focus_topic=focus_topic
        )
        
        if result.get("status") == "success":
             return f"✅ Strategy Updated.\nPath: {result.get('path')}\nInsights: {result.get('insights')}"
        else:
             return f"❌ Synthesis Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading marketing engine: {e}"

@mcp.tool()
def brain_synthesize_status_report(focus: str = "roadmap") -> str:
    """
    [Executive Engine]
    Generate a 'State of the Union' report by analyzing tasks, logs, and vision.
    
    Args:
        focus: 'roadmap' (default), 'technical', or 'marketing'.
        
    Returns:
        The generated status report.
    """
    try:
        from mcp_server_nucleus.runtime.capabilities.synthesizer import brain_synthesize_status_report
        
        result = brain_synthesize_status_report(
            project_root=str(Path.cwd()),
            focus=focus
        )
        
        if result.get("status") == "success":
             return result.get("report")
        else:
             return f"❌ Status Generation Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading synthesizer: {e}"

@mcp.tool()
def brain_optimize_workflow() -> str:
    """
    [Marketing Engine]
    Scan marketing logs for 'META-FEEDBACK' and self-optimize the workflow cheatsheet.
    
    Returns:
        Status of the optimization attempt.
    """
    try:
        from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_optimize_workflow
        
        result = brain_optimize_workflow(project_root=str(Path.cwd()))
        
        if result.get("status") == "success":
             return f"✅ Workflow Optimized.\nMessage: {result.get('message')}\nPath: {result.get('path')}"
        elif result.get("status") == "skipped":
             return f"ℹ️  Optimization Skipped: {result.get('message')}"
        else:
             return f"❌ Optimization Failed: {result.get('message')}"
             
    except Exception as e:
        return f"❌ Error loading marketing engine: {e}"


# ============================================================
# CRITIC SYSTEM TOOLS
# ============================================================




@mcp.tool()
def brain_apply_critique(review_path: str) -> Dict:
    """Apply fixes based on a critique review.
    
    Spawns a Developer agent to fix the issues identified in the review.
    
    Args:
        review_path: Path to the critique JSON file
        
    Returns:
        Task creation result
    """
    try:
        # Resolve relative path for _read_artifact
        # _read_artifact expects path relative to artifacts/
        path_str = str(review_path)
        if "artifacts/" in path_str:
            path_str = path_str.split("artifacts/")[-1]
            
        content_str = _read_artifact(path_str)
        if content_str.startswith("Error"):
             return {"error": content_str}
             
        review = json.loads(content_str)
        
        payload = review.get("payload", {})
        target = payload.get("target")
        issues = payload.get("issues", [])
        
        if not target or not issues:
             return {"error": "Invalid critique format: missing target or issues"}

        description = f"Fix {len(issues)} issues in {target} identified by Critic.\n\nIssues:\n"
        for i in issues:
            description += f"- [{i.get('severity')}] {i.get('description')}\n"
            
        # Trigger Developer
        result = _trigger_agent_impl(
            agent="developer",
            task_description=description,
            context_files=[path_str, target]
        )
        
        return {"success": True, "message": result}
        
    except Exception as e:
        return {"error": f"Failed to apply critique: {str(e)}"}



@mcp.tool()
async def brain_orchestrate_swarm(mission: str, agents: List[str] = None) -> Dict:
    """Initialize a multi-agent swarm for a complex mission (Unified)."""
    try:
        orch = get_orch()
        return await orch.start_mission(mission, agents=agents)
    except Exception as e:
        return make_response(False, error=f"Swarm failed: {str(e)}")



@mcp.tool()
def brain_search_memory(query: str) -> Dict:
    """Search long-term memory for keywords using ripgrep.
    
    Args:
        query: Keyword or phrase to search for.
        
    Returns:
        List of matching snippets with file paths.
    """
    try:
        from .runtime.memory import _search_memory
        return _search_memory(query)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_read_memory(category: str) -> Dict:
    """Read full content of a memory category.
    
    Args:
        category: One of ['context', 'patterns', 'learnings', 'decisions']
        
    Returns:
        Full content of the requested memory file.
    """
    try:
        from .runtime.memory import _read_memory
        return _read_memory(category)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_respond_to_consent(agent_id: str, choice: str = "cold") -> Dict:
    """Respond to a respawn consent request for an agent.
    
    Args:
        agent_id: ID of the agent awaiting consent.
        choice: 'warm' (Efficiency/Context Preservation) or 'cold' (Security/Reset).
        
    Returns:
        Confirmation of the recorded choice.
    """
    try:
        # In a real system, we'd use the global AgentPool instance
        # For this prototype/MDR demo, we signal the intention.
        from .runtime.agent_pool import AgentPool
        
        return {
            "success": True,
            "agent_id": agent_id,
            "choice": choice.upper(),
            "message": f"Consent recorded. Agent will respawn in {choice.upper()} mode.",
            "policy": "MDR_013 (Just-In-Time Consent) Active"
        }
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_list_pending_consents() -> Dict:
    """List agents that are exhausted and awaiting user consent for respawn.
    
    Returns:
        List of agents awaiting consent.
    """
    try:
        # This would normally query the global AgentPool
        return {
            "pending": [],
            "message": "Use brain_respond_to_consent(agent_id, choice) to authorize respawns."
        }
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_manage_strategy(action: str, content: str = None) -> Dict:
    """Read or Update the core Strategy Document.
    
    Args:
        action: 'read', 'update', or 'append'.
        content: Text content (required for update/append).
    """
    try:
        from .runtime.strategy import _manage_strategy
        return _manage_strategy(action, content)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

@mcp.tool()
def brain_update_roadmap(action: str, item: str = None) -> Dict:
    """Read or Update the Roadmap.
    
    Args:
        action: 'read' or 'add'.
        item: Roadmap item text (required for add).
    """
    try:
        from .runtime.strategy import _update_roadmap
        return _update_roadmap(action, item)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

def main():
    # Fallback for Python 3.9 / No FastMCP
    if globals().get("USE_STDIO_FALLBACK"):
        from .runtime.stdio_server import StdioServer
        import logging
        import sys
        
        # Configure logging to stderr to not corrupt stdout
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)
        
        server = StdioServer()
        server.run()
        return

    # Helper to log to debug file
    def log_debug(msg):
        with open("/tmp/mcp_debug.log", "a") as f:
            f.write(f"{msg}\n")
    
    # Phase 50: Initialize File Monitor for Native Sync
    try:
        from .runtime.file_monitor import init_file_monitor
        brain_path = os.environ.get("NUCLEAR_BRAIN_PATH")
        if brain_path and Path(brain_path).exists():
            monitor = init_file_monitor(brain_path)
            monitor.start()
            log_debug(f"📡 File monitor initialized for: {brain_path}")
    except ImportError as e:
        log_debug(f"File monitor not available: {e}")
    except Exception as e:
        log_debug(f"File monitor init failed: {e}")
    
    try:
        log_debug("Entering mcp.run()")
        mcp.run()
        log_debug("Exited mcp.run() normally")
    except Exception as e:
        log_debug(f"Exception in mcp.run(): {e}")
        import traceback
        with open("/tmp/mcp_debug.log", "a") as f:
            traceback.print_exc(file=f)
        raise

if __name__ == "__main__":
    main()

# ============================================================
# CRITIC LOOP - PHASE 12
# ============================================================

def _critique_code(file_path: str, context: Optional[str] = None) -> Dict:
    """Core logic for critiquing code using the Critic persona."""
    try:
        from .runtime.llm_client import DualEngineLLM
        import json
        
        brain = get_brain_path()
        target_file = Path(file_path)
        
        # Security check: Ensure file is within project
        # In a real impl, we'd check against PROJECT_ROOT env var, but here allow absolute
        if not target_file.exists():
            return {"error": f"File not found: {file_path}"}
            
        code_content = target_file.read_text()
        
        # Load Critic Persona
        critic_persona_path = brain / "agents" / "critic.md"
        if critic_persona_path.exists():
            system_prompt = critic_persona_path.read_text()
        else:
            system_prompt = "You are The Critic. Find bugs, security flaws, and style issues."
            
        initial_prompt = f"""
        CRITIQUE THIS FILE: {file_path}
        CONTEXT: {context or 'General Check'}
        
        Analyze the code provided below.
        Return JSON matching schema: {{ "status": "PASS/FAIL/WARN", "score": 0-100, "issues": [ {{ "severity": "CRITICAL/WARNING", "line": 1, "message": "..." }} ] }}
        """
        
        # Pass as list to handle large code blocks safely
        prompt_parts = [initial_prompt, "\nCODE:\n```\n", code_content, "\n```\n"]
        
        # Call LLM
        client = DualEngineLLM(system_instruction=system_prompt)
        response = client.generate_content(prompt_parts)
        
        # Parse JSON
        text = response.text
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            critique = json.loads(text)
        except Exception:
            # Fallback to text wrapping
            critique = {"status": "WARN", "score": 0, "summary": text, "issues": []}
            
        # Emit event
        _emit_event("code_critiqued", "critic", {
            "file": file_path,
            "status": critique.get("status"),
            "score": critique.get("score")
        })
        
        return critique
        
    except Exception as e:
        return {"error": str(e)}

def _apply_critique(file_path: str, critique_id: str) -> str:
    """Placeholder for applying critique fixes automatically."""
    return "Feature not implemented in Phase 12 MVP. Please fix manually based on critique."

@mcp.tool()
def brain_critique_code(file_path: str, context: str = "General Review") -> str:
    """
    Run a specialized 'Critic' agent review on a file.
    Args:
        file_path: Absolute path to the file to review.
        context: Optional context (e.g. "Focus on security", "Check performance").
    Returns:
        JSON string of the critique.
    """
    result = _critique_code(file_path, context)
    return json.dumps(result, indent=2)

@mcp.tool()
def brain_fix_code(file_path: str, issues_context: str) -> str:
    """
    Auto-fix code based on provided issues context.
    Args:
        file_path: Absolute path to the file.
        issues_context: Description of issues or stringified JSON from Critic.
    """
    return _fix_code(file_path, issues_context)

def _fix_code(file_path: str, issues_context: str) -> str:
    """
    Core logic for The Fixer.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"status": "error", "message": "File not found"})

        original_content = path.read_text(encoding='utf-8')
        
        # 1. Create Backup
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        backup_path.write_text(original_content, encoding='utf-8')

        # 2. Invoke LLM (Fixer Persona)
        system_prompt = (
            "You are 'The Fixer', an autonomous code repair agent. "
            "Your goal is to fix specific issues in the provided code while maintaining strict adherence to the project's style (Nucleus/Neon/Context-Aware). "
            "Return ONLY the full corrected file content inside a code block. Do not wrap in markdown or add commentary."
        )
        
        user_prompt = f"""
        TARGET: {file_path}
        
        ISSUES TO FIX:
        {issues_context}
        
        CURRENT CONTENT:
        ```
        {original_content}
        ```
        
        INSTRUCTIONS:
        1. Fix the issues listed above.
        2. Ensure accessibility (ARIA) and style compliance (Globals/Neon) if UI.
        3. Do NOT break existing logic.
        4. Return the COMPLETE new file content.
        """

        # Use Dual Engine (using mcp_server_nucleus's internal instance if available, or creating one)
        # We assume DualEngineLLM is imported (it is at top of __init__.py usually, or we use the one instantiated in server. But this is the library).
        # We need to import it or assume it's available.
        from .runtime.llm_client import DualEngineLLM
        
        llm = DualEngineLLM() 
        fix_response = llm.generate_content(
            prompt=user_prompt,
            system_instruction=system_prompt
        )

        # 3. Extract Code
        # Simple extraction logic: find first ``` and last ```
        new_content = fix_response.text.strip()
        if "```" in new_content:
            parts = new_content.split("```")
            # Usually parts[1] is the code if format is ```lang ... ```
            # If parts[0] is empty, parts[1] is language+code or just code.
            # Let's robustly strip.
            candidate = parts[1]
            if candidate.startswith(("typescript", "tsx", "python", "css", "javascript", "json")):
                 # Remove first line (lang identifier)
                 candidate = "\n".join(candidate.split("\n")[1:])
            new_content = candidate
        
        # 4. Write Fix
        path.write_text(new_content, encoding='utf-8')
        
        return json.dumps({
            "status": "success", 
            "message": f"Applied fix to {path.name}",
            "backup": str(backup_path)
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ============================================================
# PHASE 71: CROSS-CHAT TASK VISIBILITY
# ============================================================

def _get_thread_identity(conversation_id: str) -> Optional[Dict]:
    """Look up thread identity from thread_registry.md."""
    try:
        brain = get_brain_path()
        registry_path = brain / "meta" / "thread_registry.md"
        
        if not registry_path.exists():
            return None
            
        content = registry_path.read_text()
        
        # Simple parsing: look for the conversation_id prefix in any line
        short_id = conversation_id[:8] if len(conversation_id) > 8 else conversation_id
        
        for line in content.split("\n"):
            if short_id in line and "|" in line:
                # Parse table row: | Thread ID | Label | Agent Role | Purpose |
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    return {
                        "thread_id": parts[1],
                        "label": parts[2],
                        "role": parts[3],
                        "purpose": parts[4] if len(parts) > 4 else ""
                    }
        return None
    except Exception:
        return None

def _get_active_sessions() -> Dict:
    """Get active sessions from ledger."""
    try:
        brain = get_brain_path()
        sessions_path = brain / "ledger" / "active_sessions.json"
        
        if not sessions_path.exists():
            return {"sessions": {}}
            
        with open(sessions_path, "r") as f:
            return json.load(f)
    except Exception:
        return {"sessions": {}}

def _save_active_sessions(data: Dict) -> str:
    """Save active sessions to ledger."""
    try:
        brain = get_brain_path()
        sessions_path = brain / "ledger" / "active_sessions.json"
        sessions_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sessions_path, "w") as f:
            json.dump(data, f, indent=2)
        return "Saved"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def brain_session_briefing(conversation_id: Optional[str] = None) -> str:
    """Get a briefing of pending work and session identity at session start.
    
    Call this at the start of each conversation to see:
    - Who you are (from thread_registry.md)
    - Open tasks and priorities
    - What other sessions are working on
    
    Args:
        conversation_id: Optional. Your conversation ID for identity lookup.
    
    Returns:
        Formatted briefing with tasks and identity info.
    """
    lines = ["## 📋 Session Briefing", ""]
    
    # 1. Identity from thread registry
    if conversation_id:
        identity = _get_thread_identity(conversation_id)
        if identity:
            lines.append("### 🪪 Your Identity")
            lines.append(f"- **Thread:** `{conversation_id[:12]}...`")
            lines.append(f"- **Role:** {identity.get('role', 'Unknown')}")
            lines.append(f"- **Focus:** {identity.get('label', 'Unknown')}")
            lines.append("")
    
    # 2. Active sessions
    sessions = _get_active_sessions()
    active = sessions.get("sessions", {})
    if active:
        lines.append(f"### 👥 Active Sessions ({len(active)})")
        for sid, info in list(active.items())[:5]:
            lines.append(f"- `{sid[:8]}`: {info.get('focus', 'Unknown')}")
        lines.append("")
    
    # 3. In Progress tasks
    in_progress = _list_tasks(status="IN_PROGRESS")
    if in_progress:
        lines.append(f"### 🔄 In Progress ({len(in_progress)})")
        for t in in_progress[:3]:
            claimed = t.get("claimed_by", "unknown")
            lines.append(f"- {t['description'][:50]}... (by {claimed})")
        lines.append("")
    
    # 4. Pending tasks
    pending = _list_tasks(status="PENDING")
    if pending:
        lines.append(f"### 📌 Pending ({len(pending)})")
        for t in pending[:5]:
            pri = "🔴" if t.get("priority", 3) <= 2 else "🟡" if t.get("priority") == 3 else "⚪"
            lines.append(f"- {pri} {t['description'][:60]}")
        if len(pending) > 5:
            lines.append(f"  ... and {len(pending) - 5} more")
    
    if not in_progress and not pending:
        lines.append("✨ **All clear!** No pending tasks.")
    
    return "\n".join(lines)

@mcp.tool()
def brain_register_session(conversation_id: str, focus_area: str) -> str:
    """Register this session's focus area for cross-chat visibility.
    
    Call this when starting work on a specific task or phase.
    
    Args:
        conversation_id: Your conversation ID
        focus_area: What you're working on (e.g., "Phase 71: Visibility")
    
    Returns:
        Confirmation message
    """
    try:
        sessions = _get_active_sessions()
        
        sessions["sessions"][conversation_id] = {
            "focus": focus_area,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "last_active": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }
        
        _save_active_sessions(sessions)
        
        # Emit event
        _emit_event("session_registered", "nucleus_mcp", {
            "conversation_id": conversation_id,
            "focus_area": focus_area
        })
        
        return f"Registered session {conversation_id[:8]}... focused on: {focus_area}"
    except Exception as e:
        return f"Error: {e}"


# Ingestion impls extracted to runtime/ingestion_ops.py
from .runtime.ingestion_ops import (
    _get_ingestion_engine,
    _brain_ingest_tasks_impl,
    _brain_rollback_ingestion_impl,
    _brain_ingestion_stats_impl,
)
@mcp.tool()
def brain_handoff_task(
    task_description: str,
    target_session_id: Optional[str] = None,
    priority: int = 3
) -> str:
    """Hand off a task to another session or the shared queue.
    
    Creates a task in the shared task system. If target_session_id is provided,
    the task is tagged for that specific session.
    
    Args:
        task_description: What needs to be done
        target_session_id: Optional. Target session ID (or None for shared queue)
        priority: 1-5 (1=critical, 5=low). Default 3.
    
    Returns:
        Confirmation with task ID
    """
    try:
        # Add to task system
        result = _add_task(
            description=f"{'@' + target_session_id[:8] + ': ' if target_session_id else ''}{task_description}",
            priority=priority,
            source="handoff"
        )
        
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        
        task = result.get("task", {})
        
        # Log handoff
        try:
            brain = get_brain_path()
            handoffs_path = brain / "ledger" / "handoffs.json"
            
            handoffs = []
            if handoffs_path.exists():
                with open(handoffs_path, "r") as f:
                    handoffs = json.load(f)
            
            handoffs.append({
                "task_id": task.get("id"),
                "description": task_description,
                "target": target_session_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            })
            
            with open(handoffs_path, "w") as f:
                json.dump(handoffs, f, indent=2)
        except Exception:
            pass  # Don't fail if audit log fails
        
        target_msg = f"for session {target_session_id[:8]}" if target_session_id else "to shared queue"
        return f"✅ Task handed off {target_msg}. ID: {task.get('id')}"
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: TASK INGESTION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def brain_ingest_tasks(
    source: str,
    source_type: str = "auto",
    session_id: str = None,
    auto_assign: bool = False,
    skip_dedup: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Ingest tasks from various sources into the brain.
    
    Parses and imports tasks from:
    - Planning documents (markdown with checkboxes)
    - Code TODOs (TODO/FIXME/HACK comments)
    - Handoff summaries (JSON from agent handoffs)
    - Meeting notes (action items with @mentions)
    - External APIs (Jira, Linear, GitHub)
    
    Args:
        source: File path or raw text/JSON content
        source_type: "planning", "todos", "handoffs", "meetings", "api", "auto"
        session_id: Your session ID for provenance tracking
        auto_assign: If True, immediately assign tasks to available agents
        skip_dedup: If True, skip deduplication check (faster)
        dry_run: If True, parse and validate but don't create tasks
    
    Returns:
        Formatted ingestion result with batch ID, stats, and rollback hint
    
    Examples:
        brain_ingest_tasks("/docs/sprint_42.md", source_type="planning")
        brain_ingest_tasks("/src/**/*.py", source_type="todos")
        brain_ingest_tasks('{"from_session":"ws_001","tasks":[...]}', source_type="handoffs")
    """
    return _brain_ingest_tasks_impl(
        source, source_type, session_id, auto_assign, skip_dedup, dry_run
    )


@mcp.tool()
def brain_rollback_ingestion(batch_id: str, reason: str = None) -> str:
    """
    Rollback an ingestion batch.
    
    Removes all tasks created in the specified batch.
    Use the batch_id from brain_ingest_tasks result.
    
    Args:
        batch_id: Batch ID from brain_ingest_tasks result
        reason: Optional reason for rollback (logged)
    
    Returns:
        Rollback result with tasks removed count
    """
    return _brain_rollback_ingestion_impl(batch_id, reason)


@mcp.tool()
def brain_ingestion_stats() -> str:
    """
    Get overall ingestion statistics.
    
    Returns:
        Stats including total ingested, dedup rate, source breakdown
    """
    return _brain_ingestion_stats_impl()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: DASHBOARD TOOLS (ENHANCED)

# Dashboard impls extracted to runtime/dashboard_ops.py
from .runtime.dashboard_ops import (
    _get_dashboard_engine,
    _brain_enhanced_dashboard_impl,
    _brain_snapshot_dashboard_impl,
    _brain_list_snapshots_impl,
    _brain_get_alerts_impl,
    _brain_set_alert_threshold_impl,
)
# ═══════════════════════════════════════════════════════════════════════════════



def brain_dashboard(
    detail_level: str = "standard",
    format: str = "ascii",
    include_alerts: bool = True,
    include_trends: bool = False,
    category: str = None,
) -> str:
    """
    Enhanced orchestration dashboard with multiple output formats.
    
    Provides real-time visibility into all NOP V3.1 components:
    - Agent Pool Health (active, idle, exhausted, utilization)
    - Task Queue Metrics (pending, in-progress, blocked, velocity)
    - Ingestion Statistics (sources, dedup rates, batches)
    - Cost Tracking (tokens, USD, budget, burn rate)
    - Dependency Graph (depths, blocked chains, circular)
    - System Health (uptime, errors)
    
    Args:
        detail_level: "minimal", "standard", "verbose", "full"
        format: "ascii" (terminal), "json" (API), "mermaid" (diagrams)
        include_alerts: Include alert section
        include_trends: Include trend data (velocity, etc.)
        category: Filter to specific category ("agents", "tasks", "ingestion", "cost", "deps")
    
    Returns:
        Formatted dashboard in requested format
    
    Examples:
        brain_dashboard()  # Standard ASCII dashboard
        brain_dashboard(detail_level="full", include_trends=True)
        brain_dashboard(format="json")  # For API consumption
        brain_dashboard(category="agents")  # Only agent metrics
    """
    return _brain_enhanced_dashboard_impl(
        detail_level, format, include_alerts, include_trends, category
    )


@mcp.tool()
def brain_snapshot_dashboard(name: str = None) -> str:
    """
    Create a manual dashboard snapshot for later comparison.
    
    Snapshots capture the current state of all metrics and alerts.
    Use for tracking progress over time or debugging issues.
    
    Args:
        name: Optional name for the snapshot
    
    Returns:
        Snapshot ID and confirmation
    """
    return _brain_snapshot_dashboard_impl(name)


@mcp.tool()
def brain_list_snapshots(limit: int = 10) -> str:
    """
    List available dashboard snapshots.
    
    Args:
        limit: Maximum number of snapshots to list (default: 10)
    
    Returns:
        List of snapshots with IDs, names, and timestamps
    """
    return _brain_list_snapshots_impl(limit)


@mcp.tool()
def brain_get_alerts() -> str:
    """
    Get current active alerts from the dashboard.
    
    Alerts are triggered when metrics exceed thresholds:
    - CRITICAL: Immediate action required
    - WARNING: Attention needed
    
    Returns:
        List of active alerts with levels and details
    """
    return _brain_get_alerts_impl()


@mcp.tool()
def brain_set_alert_threshold(metric: str, level: str, value: float) -> str:
    """
    Set custom alert threshold for a metric.
    
    Available metrics:
    - agents.exhausted_ratio: Ratio of exhausted agents (0-1)
    - agents.utilization: Pool utilization (0-1)
    - tasks.pending: Number of pending tasks
    - tasks.blocked_ratio: Ratio of blocked tasks (0-1)
    - cost.budget_remaining_ratio: Budget remaining (0-1)
    - deps.max_depth: Maximum dependency chain depth
    
    Args:
        metric: Metric name (e.g., "tasks.pending")
        level: "warning" or "critical"
        value: Threshold value
    
    Returns:
        Confirmation of threshold setting
    """
    return _brain_set_alert_threshold_impl(metric, level, value)


# Sprint/Mission ops extracted to runtime/sprint_ops.py
from .runtime.sprint_ops import (
    _get_autopilot_engine, _brain_autopilot_sprint_v2_impl,
    _brain_start_mission_impl, _brain_mission_status_impl,
    _brain_halt_sprint_impl, _brain_resume_sprint_impl,
)


@mcp.tool()
def brain_autopilot_sprint_v2(
    slots: List[str] = None,
    mode: str = "auto",
    halt_on_blocker: bool = True,
    halt_on_tier_mismatch: bool = False,
    max_tasks_per_slot: int = 10,
    budget_limit: float = None,
    time_limit_hours: float = None,
    dry_run: bool = False,
) -> str:
    """
    Enhanced autopilot sprint with V3.1 features.
    
    Orchestrates multiple slots in parallel to execute pending tasks.
    Features wave-based dependency analysis, tier-matched assignment,
    budget control, and comprehensive halt conditions.
    
    Args:
        slots: Slot IDs to use (None = all active)
        mode: "auto" (execute), "plan" (dry run), "guided" (step-by-step), "status"
        halt_on_blocker: Stop if circular dependency detected
        halt_on_tier_mismatch: Stop if no slot can handle required tier
        max_tasks_per_slot: Max tasks per slot in one sprint
        budget_limit: Max cost in USD (None = unlimited)
        time_limit_hours: Max duration (None = unlimited)
        dry_run: Override to plan mode
    
    Returns:
        Sprint execution report with tasks completed, budget spent, etc.
    
    Examples:
        brain_autopilot_sprint_v2()  # Full auto execution
        brain_autopilot_sprint_v2(mode="plan")  # Preview what would happen
        brain_autopilot_sprint_v2(budget_limit=5.0)  # Limit cost to $5
    """
    return _brain_autopilot_sprint_v2_impl(
        slots, mode, halt_on_blocker, halt_on_tier_mismatch,
        max_tasks_per_slot, budget_limit, time_limit_hours, dry_run
    )


@mcp.tool()
def brain_start_mission(
    name: str,
    goal: str,
    task_ids: List[str],
    slot_ids: List[str] = None,
    budget_limit: float = 10.0,
    time_limit_hours: float = 4.0,
    success_criteria: List[str] = None,
) -> str:
    """
    Start a new mission for orchestrated execution.
    
    Missions are high-level goals with associated tasks, constraints,
    and success criteria. They provide persistence and tracking.
    
    Args:
        name: Mission name (e.g., "Implement NOP V3.1")
        goal: What success looks like
        task_ids: List of task IDs to complete
        slot_ids: Slots to use (None = all active)
        budget_limit: Max cost in USD
        time_limit_hours: Max duration
        success_criteria: List of success conditions
    
    Returns:
        Mission ID and confirmation
    """
    return _brain_start_mission_impl(
        name, goal, task_ids, slot_ids, budget_limit, time_limit_hours, success_criteria
    )


@mcp.tool()
def brain_mission_status(mission_id: str = None) -> str:
    """
    Get current mission status and progress.
    
    Args:
        mission_id: Mission ID (None = current mission)
    
    Returns:
        Detailed mission progress report
    """
    return _brain_mission_status_impl(mission_id)


@mcp.tool()
def brain_halt_sprint(reason: str = "User requested halt") -> str:
    """
    Request halt of current sprint.
    
    The sprint will complete its current task then stop gracefully.
    Progress is checkpointed for potential resumption.
    
    Args:
        reason: Reason for halting
    
    Returns:
        Confirmation of halt request
    """
    return _brain_halt_sprint_impl(reason)


@mcp.tool()
def brain_resume_sprint(sprint_id: str = None) -> str:
    """
    Resume a halted sprint from checkpoint.
    
    Restores state from the last checkpoint and continues execution.
    
    Args:
        sprint_id: Sprint ID to resume (None = most recent)
    
    Returns:
        Sprint execution report
    """
    return _brain_resume_sprint_impl(sprint_id)


# Federation ops extracted to runtime/federation_ops.py
from .runtime.federation_ops import (
    _get_federation_engine, _brain_federation_status_impl,
    _brain_federation_join_impl, _brain_federation_leave_impl,
    _brain_federation_peers_impl, _brain_federation_sync_impl,
    _brain_federation_route_impl, _brain_federation_health_impl,
)


@mcp.tool()
def brain_federation_status() -> str:
    """
    Get comprehensive federation status.
    
    Shows local brain info, consensus state, peer list,
    partition status, health score, and sync state.
    
    Returns:
        Formatted federation status report
    """
    return _brain_federation_status_impl()


@mcp.tool()
def brain_federation_join(seed_peer: str) -> str:
    """
    Join a federation via seed peer.
    
    Connects to an existing federation network through
    a known peer address.
    
    Args:
        seed_peer: Address of seed peer (host:port)
    
    Returns:
        Join result
    """
    return _brain_federation_join_impl(seed_peer)


@mcp.tool()
def brain_federation_leave() -> str:
    """
    Leave the federation gracefully.
    
    Notifies peers and stops federation engine.
    Brain continues operating in standalone mode.
    
    Returns:
        Leave confirmation
    """
    return _brain_federation_leave_impl()


@mcp.tool()
def brain_federation_peers() -> str:
    """
    List all federation peers with details.
    
    Shows status, region, trust level, latency,
    load, and capabilities for each peer.
    
    Returns:
        Formatted peer list
    """
    return _brain_federation_peers_impl()


@mcp.tool()
def brain_federation_sync() -> str:
    """
    Force immediate synchronization with all peers.
    
    Performs full state sync using Merkle tree comparison
    and CRDT merge for conflict resolution.
    
    Returns:
        Sync results for each peer
    """
    return _brain_federation_sync_impl()


@mcp.tool()
def brain_federation_route(task_id: str, profile: str = "default") -> str:
    """
    Route a task to the optimal brain.
    
    Uses composite scoring with configurable profiles
    to determine the best brain for task execution.
    
    Args:
        task_id: Task to route
        profile: Routing profile (default, realtime, batch, premium, budget)
    
    Returns:
        Routing decision with target brain and alternatives
    """
    return _brain_federation_route_impl(task_id, profile)


@mcp.tool()
def brain_federation_health() -> str:
    """
    Get federation health dashboard.
    
    Shows health score, partition status, metrics,
    and any active warnings.
    
    Returns:
        Health dashboard with visual indicators
    """
    return _brain_federation_health_impl()


# ============================================================================
# SYSTEM HEALTH ENDPOINT (Phase 6B Production Hardening)

# Health/version/audit ops extracted to runtime/health_ops.py
from .runtime.health_ops import (
    _brain_health_impl, _brain_health_impl_legacy,
    _brain_version_impl, _brain_audit_log_impl,
)

# ============================================================================

@mcp.tool()
def brain_health() -> str:
    """
    Get comprehensive system health status.
    
    Checks brain path, ledger, tasks, events, state, and slots.
    Returns health score and detailed status for each component.
    
    Use this for:
    - Production monitoring
    - Debugging issues
    - Verifying installation
    
    Returns:
        Health dashboard with all component statuses
    """
    return _brain_health_impl()


@mcp.tool()
def brain_version() -> str:
    """
    Get Nucleus version and system information.
    
    Returns:
        Version info as formatted string
    """
    info = _brain_version_impl()
    return f"""🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: {info['nucleus_version']}
   Python: {info['python_version']}
   Platform: {info['platform']} {info['platform_release']}

🔧 CAPABILITIES
   MCP Tools: {info['mcp_tools_count']}+
   Architecture: {info['architecture']}
   Status: {info['status']}

   GitHub: https://github.com/eidetic-works/nucleus-mcp
   PyPI: pip install nucleus-mcp
   Docs: https://nucleusos.dev"""

@mcp.tool()
async def brain_export_schema() -> str:
    """
    Export the current MCP toolset as an OpenAPI/JSON Schema.
    
    This helps the AI or external tools understand the full 
    contract of all available Nucleus tools.
    
    Returns:
        JSON Schema string
    """
    schema = await generate_tool_schema(mcp)
    return json.dumps(schema, indent=2)


@mcp.tool()
def brain_performance_metrics(export_to_file: bool = False) -> str:
    """
    Get performance metrics for Nucleus operations (AG-014).
    
    Requires NUCLEUS_PROFILING=true environment variable to collect metrics.
    
    Args:
        export_to_file: If True, also exports metrics to .brain/metrics/
    
    Returns:
        Formatted performance summary or JSON if exported
    """
    from .runtime.profiling import get_metrics, get_metrics_summary, export_metrics_to_file
    
    metrics = get_metrics()
    if not metrics:
        return make_response(True, data={
            "message": "No metrics collected. Set NUCLEUS_PROFILING=true to enable.",
            "hint": "export NUCLEUS_PROFILING=true before starting Nucleus"
        })
    
    if export_to_file:
        try:
            filepath = export_metrics_to_file()
            return make_response(True, data={
                "metrics": metrics,
                "exported_to": filepath
            })
        except Exception as e:
            return make_response(False, error=f"Export failed: {e}")
    
    return make_response(True, data={
        "summary": get_metrics_summary(),
        "metrics": metrics
    })


@mcp.tool()
def brain_prometheus_metrics(format: str = "prometheus") -> str:
    """
    Get Prometheus-compatible metrics for monitoring (AG-015).
    
    Args:
        format: Output format - "prometheus" (text) or "json"
    
    Returns:
        Metrics in Prometheus exposition format or JSON
    
    Example scrape config:
        - job_name: 'nucleus'
          static_configs:
            - targets: ['localhost:9090']
    """
    from .runtime.prometheus import get_prometheus_metrics, get_metrics_json
    
    if format.lower() == "json":
        return make_response(True, data=get_metrics_json())
    
    # Return raw Prometheus format (not wrapped in JSON for scraping)
    return get_prometheus_metrics()


@mcp.tool()
def brain_audit_log(limit: int = 20) -> str:
    """
    View the cryptographic interaction log for trust verification.
    
    Each interaction is SHA-256 hashed for integrity verification.
    This is the "Why-Trace" that proves agent decisions.
    
    Part of the Governance Moat (N-SOS V1).
    
    Args:
        limit: Number of recent entries to return (default 20)
    
    Returns:
        Recent interaction hashes with timestamps and emitters
    """
    return _brain_audit_log_impl(limit)


@mcp.tool()
def brain_write_engram(key: str, value: str, context: str = "Decision", intensity: int = 5) -> str:
    """
    Write a new Engram to the cognitive memory ledger.
    
    Engrams are persistent memory units that survive between sessions.
    Use this to record architectural decisions, constraints, and learnings.
    
    Part of the Engram Ledger (N-SOS V1).
    
    Args:
        key: Unique identifier (e.g., "auth_architecture", "no_openai")
        value: The memory content (include reasoning - "X because Y")
        context: Category - Feature, Architecture, Brand, Strategy, Decision
        intensity: 1-10 priority (10=critical constraint, 5=normal, 1=archive)
    
    Returns:
        Confirmation with engram details
    
    Examples:
        - brain_write_engram("db_choice", "PostgreSQL for ACID compliance", "Architecture", 8)
        - brain_write_engram("no_openai", "Budget constraint - Gemini only", "Decision", 10)
    """
    return _brain_write_engram_impl(key, value, context, intensity)


# Engram ops extracted to runtime/engram_ops.py
from .runtime.engram_ops import (
    _brain_write_engram_impl, _brain_query_engrams_impl,
    _brain_search_engrams_impl, _brain_governance_status_impl,
)

# Morning Brief — The Alive Workflow (MDR_015)
from .runtime.morning_brief_ops import _morning_brief_impl


@mcp.tool()
def brain_morning_brief() -> str:
    """
    🧠 The Nucleus Morning Brief — your daily "Alive Workflow".

    One command that takes you from "I just opened my IDE" to
    "I know exactly what to do today" in under 60 seconds.

    What it does:
    1. RETRIEVE — Your top engrams (decisions, constraints, learnings)
    2. ORIENT   — Current tasks from the ledger (in-progress + pending)
    3. SCAN     — Yesterday's activity (what happened last session)
    4. RECOMMEND — "Today you should: [specific next action]"

    Use this every morning. Each day's brief gets better because
    Nucleus remembers yesterday's decisions via ADUN engrams.

    Returns:
        A structured daily brief with memory, tasks, and recommendation.
    """
    result = _morning_brief_impl()
    return make_response(True, data={
        "brief": result.get("formatted", ""),
        "recommendation": result.get("recommendation", {}),
        "meta": result.get("meta", {}),
        "sections": result.get("sections", {}),
    })

# Hook Metrics — MDR_016 Monitoring
from .runtime.engram_hooks import get_hook_metrics_summary


@mcp.tool()
def brain_hook_metrics() -> str:
    """
    📊 Monitor the auto-write engram hook system (MDR_016).

    Shows how well the automatic memory creation is working:
    - Total executions, ADD/NOOP/ERROR breakdown
    - Per-event-type latency and count
    - Error rate and efficiency score
    - Coverage report (classified vs unclassified events)

    Returns:
        Metrics summary for the engram auto-write hooks.
    """
    summary = get_hook_metrics_summary()
    return make_response(True, data=summary)


@mcp.tool()
def brain_query_engrams(context: str = None, min_intensity: int = 1) -> str:
    """
    Query Engrams from the cognitive memory ledger.
    
    Retrieve persistent memory units filtered by context and intensity.
    
    Args:
        context: Filter by category (Feature, Architecture, Brand, Strategy, Decision)
                 If None, returns all engrams
        min_intensity: Minimum intensity threshold (1-10)
    
    Returns:
        List of matching engrams sorted by intensity (highest first)
    """
    return _brain_query_engrams_impl(context, min_intensity)




@mcp.tool()
def brain_search_engrams(query: str, case_sensitive: bool = False) -> str:
    """
    Search Engrams by substring match in key or value.
    
    Simple text search across all engrams. Use this to find
    specific memories by keyword.
    
    Args:
        query: Substring to search for in engram keys and values
        case_sensitive: Whether search is case-sensitive (default: False)
    
    Returns:
        List of matching engrams with match highlights
    
    Examples:
        - brain_search_engrams("postgres") - Find database decisions
        - brain_search_engrams("auth") - Find authentication-related memories
    """
    return _brain_search_engrams_impl(query, case_sensitive)




@mcp.tool()
def brain_governance_status() -> str:
    """
    Get the current governance status of the Nucleus Control Plane.
    
    Returns a summary of:
    - Active policies (Default-Deny, Isolation, Audit)
    - Audit log statistics
    - Engram count
    - Security configuration
    
    Part of the Governance Moat (N-SOS V1).
    """
    return _brain_governance_status_impl()




# =============================================================================
# v0.6.0 DSoR (Decision System of Record) MCP Tools
# =============================================================================

@mcp.tool()
def brain_list_decisions(limit: int = 20) -> str:
    """
    List recent DecisionMade events from the decision ledger.
    
    v0.6.0 DSoR: Provides visibility into agent decision provenance.
    
    Args:
        limit: Maximum number of decisions to return (default: 20)
    """
    try:
        brain = get_brain_path()
        decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        
        if not decisions_file.exists():
            return make_response(True, data={"decisions": [], "count": 0})
        
        decisions = []
        with open(decisions_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        decisions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent first
        decisions = decisions[-limit:][::-1]
        
        return make_response(True, data={
            "decisions": decisions,
            "count": len(decisions),
            "total_in_ledger": sum(1 for _ in open(decisions_file))
        })
    except Exception as e:
        return make_response(False, error=f"Error listing decisions: {e}")


@mcp.tool()
def brain_list_ledger_snapshots(limit: int = 10) -> str:
    """
    List context snapshots from the snapshot ledger.
    
    v0.6.0 DSoR: Provides visibility into state verification history.
    
    Args:
        limit: Maximum number of snapshots to return (default: 10)
    """
    try:
        brain = get_brain_path()
        snapshots_dir = brain / "ledger" / "snapshots"
        
        if not snapshots_dir.exists():
            return make_response(True, data={"snapshots": [], "count": 0})
        
        snapshots = []
        for snap_file in sorted(snapshots_dir.glob("snap-*.json"), reverse=True)[:limit]:
            try:
                with open(snap_file) as f:
                    snapshots.append(json.load(f))
            except Exception:
                continue
        
        return make_response(True, data={
            "snapshots": snapshots,
            "count": len(snapshots)
        })
    except Exception as e:
        return make_response(False, error=f"Error listing snapshots: {e}")


@mcp.tool()
def brain_metering_summary(since_hours: int = 24) -> str:
    """
    Get token metering summary for billing and audit.
    
    v0.6.0 DSoR: Addresses V9 Pricing Rebellion vulnerability.
    
    Args:
        since_hours: Only include entries from the last N hours (default: 24)
    """
    try:
        brain = get_brain_path()
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        
        if not meter_file.exists():
            return make_response(True, data={
                "total_entries": 0,
                "total_units": 0,
                "by_scope": {},
                "by_resource_type": {},
                "decisions_linked": 0
            })
        
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
        
        entries = []
        with open(meter_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", "") >= cutoff:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        # Compute summary
        summary = {
            "total_entries": len(entries),
            "total_units": sum(e.get("units_consumed", 0) for e in entries),
            "by_scope": {},
            "by_resource_type": {},
            "decisions_linked": sum(1 for e in entries if e.get("decision_id")),
            "since_hours": since_hours
        }
        
        for entry in entries:
            scope = entry.get("scope", "unknown")
            rtype = entry.get("resource_type", "unknown")
            units = entry.get("units_consumed", 0)
            
            summary["by_scope"][scope] = summary["by_scope"].get(scope, 0) + units
            summary["by_resource_type"][rtype] = summary["by_resource_type"].get(rtype, 0) + units
        
        return make_response(True, data=summary)
    except Exception as e:
        return make_response(False, error=f"Error getting metering summary: {e}")


@mcp.tool()
def brain_ipc_tokens(active_only: bool = True) -> str:
    """
    List IPC authentication tokens.
    
    v0.6.0 DSoR: Addresses CVE-2026-001 (Sidecar Exploit).
    
    Args:
        active_only: Only show active (non-consumed, non-expired) tokens
    """
    try:
        brain = get_brain_path()
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        
        if not tokens_file.exists():
            return make_response(True, data={"tokens": [], "count": 0})
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        events = []
        with open(tokens_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Group by token_id to get current state
        token_states = {}
        for event in events:
            tid = event.get("token_id")
            if tid:
                if tid not in token_states:
                    token_states[tid] = {"token_id": tid, "events": []}
                token_states[tid]["events"].append(event)
                token_states[tid]["last_event"] = event.get("event")
                token_states[tid]["decision_id"] = event.get("decision_id")
        
        tokens = list(token_states.values())
        
        if active_only:
            tokens = [t for t in tokens if t.get("last_event") == "issued"]
        
        return make_response(True, data={
            "tokens": tokens[-20:],  # Limit to recent 20
            "count": len(tokens),
            "active_only": active_only
        })
    except Exception as e:
        return make_response(False, error=f"Error listing IPC tokens: {e}")


@mcp.tool()
def brain_dsor_status() -> str:
    """
    Get comprehensive v0.6.0 DSoR (Decision System of Record) status.
    
    Returns combined status of:
    - Decision ledger
    - Context snapshots
    - IPC token metering
    - Security compliance
    """
    try:
        brain = get_brain_path()
        
        # Decision ledger stats
        decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        decision_count = 0
        if decisions_file.exists():
            with open(decisions_file) as f:
                decision_count = sum(1 for line in f if line.strip())
        
        # Snapshot stats
        snapshots_dir = brain / "ledger" / "snapshots"
        snapshot_count = len(list(snapshots_dir.glob("snap-*.json"))) if snapshots_dir.exists() else 0
        
        # Metering stats
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        meter_count = 0
        total_units = 0
        if meter_file.exists():
            with open(meter_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            meter_count += 1
                            total_units += entry.get("units_consumed", 0)
                        except:
                            pass
        
        # IPC token stats
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        token_issued = 0
        token_consumed = 0
        if tokens_file.exists():
            with open(tokens_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("event") == "issued":
                                token_issued += 1
                            elif event.get("event") == "consumed":
                                token_consumed += 1
                        except:
                            pass
        
        status = {
            "version": "0.6.0",
            "feature": "Decision System of Record (DSoR)",
            "components": {
                "decision_ledger": {
                    "status": "ACTIVE" if decision_count > 0 else "READY",
                    "total_decisions": decision_count
                },
                "context_snapshots": {
                    "status": "ACTIVE" if snapshot_count > 0 else "READY",
                    "total_snapshots": snapshot_count
                },
                "ipc_auth": {
                    "status": "ACTIVE" if token_issued > 0 else "READY",
                    "tokens_issued": token_issued,
                    "tokens_consumed": token_consumed
                },
                "token_metering": {
                    "status": "ACTIVE" if meter_count > 0 else "READY",
                    "meter_entries": meter_count,
                    "total_units_metered": total_units
                }
            },
            "v9_vulnerabilities_addressed": [
                "CVE-2026-001: Sidecar Exploit (per-request IPC auth)",
                "Pricing Rebellion (token metering linked to decisions)"
            ],
            "overall_status": "OPERATIONAL"
        }
        
        return make_response(True, data=status)
    except Exception as e:
        return make_response(False, error=f"Error getting DSoR status: {e}")


@mcp.tool()
def brain_federation_dsor_status() -> str:
    """
    Get Federation Engine DSoR status.
    
    v0.6.0 DSoR: Shows federation events with decision provenance.
    """
    try:
        brain = get_brain_path()
        events_file = brain / "ledger" / "events.jsonl"
        
        federation_events = {
            "peer_joined": 0,
            "peer_left": 0,
            "peer_suspect": 0,
            "leader_elected": 0,
            "task_routed": 0,
            "state_synced": 0
        }
        recent_events = []
        
        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            event_type = event.get("type", "")
                            
                            if event_type == "federation_peer_joined":
                                federation_events["peer_joined"] += 1
                            elif event_type == "federation_peer_left":
                                federation_events["peer_left"] += 1
                            elif event_type == "federation_peer_suspect":
                                federation_events["peer_suspect"] += 1
                            elif event_type == "federation_leader_elected":
                                federation_events["leader_elected"] += 1
                            elif event_type == "federation_task_routed":
                                federation_events["task_routed"] += 1
                            elif event_type == "federation_state_synced":
                                federation_events["state_synced"] += 1
                            
                            if event_type.startswith("federation_"):
                                recent_events.append({
                                    "type": event_type,
                                    "timestamp": event.get("timestamp"),
                                    "decision_id": event.get("data", {}).get("decision_id")
                                })
                        except:
                            pass
        
        # Get last 10 federation events
        recent_events = recent_events[-10:]
        
        status = {
            "version": "0.6.0",
            "feature": "Federation Engine DSoR Integration",
            "event_counts": federation_events,
            "total_federation_events": sum(federation_events.values()),
            "recent_events": recent_events,
            "dsor_integration": {
                "decision_provenance": True,
                "context_hashing": True,
                "event_auditing": True
            }
        }
        
        return make_response(True, data=status)
    except Exception as e:
        return make_response(False, error=f"Error getting federation DSoR status: {e}")


@mcp.tool()
def brain_routing_decisions(limit: int = 20) -> str:
    """
    Query routing decision history from the Federation Engine.
    
    v0.6.0 DSoR: All routing decisions are now auditable.
    
    Args:
        limit: Maximum number of decisions to return (default: 20)
    """
    try:
        brain = get_brain_path()
        events_file = brain / "ledger" / "events.jsonl"
        
        routing_decisions = []
        
        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("type") == "federation_task_routed":
                                data = event.get("data", {})
                                routing_decisions.append({
                                    "timestamp": event.get("timestamp"),
                                    "target_brain": data.get("target_brain"),
                                    "score": data.get("score"),
                                    "profile": data.get("profile"),
                                    "decision_id": data.get("decision_id"),
                                    "routing_time_ms": data.get("routing_time_ms")
                                })
                        except:
                            pass
        
        # Return last N decisions
        routing_decisions = routing_decisions[-limit:]
        
        return make_response(True, data={
            "total_decisions": len(routing_decisions),
            "limit": limit,
            "decisions": routing_decisions
        })
    except Exception as e:
        return make_response(False, error=f"Error querying routing decisions: {e}")


# =============================================================================
# v0.6.0 TOOL TIER SYSTEM - Registry Bloat Solution
# =============================================================================

@mcp.tool()
def brain_list_tools(category: str = None) -> str:
    """
    List available tools at the current tier level.
    
    v0.6.0 Registry Optimization: Tools are tiered to prevent LLM context overflow.
    Set NUCLEUS_TOOL_TIER env var: 0=launch, 1=core, 2=all
    
    Args:
        category: Optional filter (e.g., "federation", "task", "memory")
    """
    try:
        tier_info = get_tier_info()
        
        # Get all brain_* functions/tools that are allowed for the current tier
        import mcp_server_nucleus as nucleus
        
        all_funcs = []
        for name in dir(nucleus):
            if name.startswith('brain_'):
                # Handle both functions and FunctionTool objects
                item = getattr(nucleus, name)
                # If it's a tool, its name is item.name. If function, item.__name__
                actual_name = name
                if is_tool_allowed(actual_name):
                    all_funcs.append(actual_name)
        
        # Sync: Only list tools allowed in the current tier
        all_tools = sorted(all_funcs)
        
        if category:
            cat_map = {
                "federation": ["brain_mount_server", "brain_list_tools"],
                "memory": ["brain_write_engram", "brain_query_engrams"],
                "governance": ["brain_audit_log", "brain_governance_status", "brain_version", "brain_health"],
                "task": [] # No task tools in launch tier
            }
            
            # If valid category in map, filter by set membership
            if category.lower() in cat_map:
                target_tools = set(cat_map[category.lower()])
                all_tools = [t for t in all_tools if t in target_tools]
            else:
                # Fallback to string matching for unknown categories
                all_tools = [t for t in all_tools if category.lower() in t.lower()]
        
        return make_response(True, data={
            "tier": tier_info["tier_name"],
            "tier_level": tier_info["active_tier"],
            "total_tools": len(all_tools),
            "tools": all_tools,
            "hint": "Set NUCLEUS_TOOL_TIER=0 for launch (8 tools), =1 for core (28), =2 for all"
        })
    except Exception as e:
        return make_response(False, error=f"Error listing tools: {e}")


@mcp.tool()
def brain_tier_status() -> str:
    """
    Get current tool tier configuration status.
    
    v0.6.0 Registry Bloat Solution: Nucleus uses tiered tool exposure to prevent
    LLM context window overflow. This tool shows the current tier and counts.
    """
    try:
        info = get_tier_info()
        stats = tier_manager.get_stats()
        
        return make_response(True, data={
            "version": "0.6.0",
            "feature": "Tool Tier System (Registry Bloat Solution)",
            "current_tier": info["tier_name"],
            "tier_level": info["active_tier"],
            "env_var": info["env_var"],
            "env_value": info["current_value"],
            "tier_breakdown": {
                "tier_0_launch": info["tier_0_count"],
                "tier_1_core": info["tier_1_count"],
                "tier_2_advanced": info["tier_2_count"],
            },
            "registration_stats": stats,
            "recommendation": "Use NUCLEUS_TOOL_TIER=0 for nucleusos.dev website launch"
        })
    except Exception as e:
        return make_response(False, error=f"Error getting tier status: {e}")

