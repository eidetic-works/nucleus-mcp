"""
Nucleus Tool Tier System - Registry Bloat Solution

Solves the "137 tools crash LLM client" problem by organizing tools into tiers:
- Tier 0 (LAUNCH): 5 essential tools for nucleusos.dev demo
- Tier 1 (CORE): 20 standard operation tools
- Tier 2 (ADVANCED): All 137 tools

Set NUCLEUS_TOOL_TIER environment variable to control which tier is active:
- "0" or "launch": Only Tier 0 tools (default for website)
- "1" or "core": Tier 0 + Tier 1 tools
- "2" or "advanced" or "all": All tools

Author: Nucleus Team
Version: 0.6.0
"""

import os
from typing import Set, Dict, Any

# =============================================================================
# TIER DEFINITIONS
# =============================================================================

TIER_0_LAUNCH: Set[str] = {
    # The "Govern Your Agents in 60 Seconds" story
    "brain_write_engram",        # Persist a memory
    "brain_query_engrams",       # Retrieve memories
    "brain_search_engrams",      # Substring search (v0.6.0)
    "brain_audit_log",           # Trust verification (SHA-256 ledger)
    "brain_mount_server",        # Recursive aggregation demo (TEASER ONLY - Limited)
    # Meta tools
    "brain_version",             # Version check
    "brain_health",              # Health check
    "brain_list_tools",          # Discover available tools
    # Governance Demo Tools
    "nucleus_list_directory",    # Demo A: Inspect environment
    "nucleus_delete_file",       # Demo A: Test protection
    "lock_resource",             # Demo A: Block modification
    "unlock_resource",           # Demo A: Allow modification
    "hypervisor_status",         # Demo A: Status check
    "watch_resource",            # Demo A: Monitor changes
    # Egress Proxies (v1.0.9)
    "nucleus_curl",
    "nucleus_pip_install",
}

TIER_1_CORE: Set[str] = {
    # Task Management
    "brain_list_tasks",
    "brain_get_next_task",
    "brain_add_task",
    "brain_update_task",
    "brain_claim_task",
    # Orchestration
    "brain_orchestrate",
    "brain_spawn_agent",
    "brain_slot_complete",
    # State & Status
    "brain_get_state",
    "brain_update_state",
    "brain_dashboard",
    "brain_status_dashboard",
    # DSoR
    "brain_dsor_status",
    "brain_list_decisions",
    "brain_metering_summary",
    "brain_ipc_tokens",
    # Sessions
    "brain_session_start",
    "brain_save_session",
    "brain_list_sessions",
    # Memory
    "brain_read_memory",
    "brain_search_memory",
    # Multi-Agent Sync (v0.7.0)
    "brain_sync_status",
    "brain_sync_now",
    "brain_sync_auto",
    "brain_sync_auto",
    "brain_identify_agent",
    # Hypervisor (v0.8.0)
    "lock_resource",
    "unlock_resource",
    "watch_resource",
    "hypervisor_status",
    "set_hypervisor_mode",
}

TIER_2_ADVANCED: Set[str] = {
    # Federation
    "brain_federation_status",
    "brain_federation_join",
    "brain_federation_leave",
    "brain_federation_peers",
    "brain_federation_sync",
    "brain_federation_route",
    "brain_federation_health",
    "brain_federation_dsor_status",
    "brain_routing_decisions",
    # Depth Management
    "brain_depth_map",
    "brain_depth_push",
    "brain_depth_pop",
    "brain_depth_show",
    "brain_depth_reset",
    "brain_depth_set_max",
    # Autopilot
    "brain_autopilot_sprint",
    "brain_autopilot_sprint_v2",
    "brain_halt_sprint",
    "brain_resume_sprint",
    # Ingestion
    "brain_ingest_tasks",
    "brain_ingestion_stats",
    "brain_rollback_ingestion",
    "brain_import_tasks_from_jsonl",
    # Features
    "brain_add_feature",
    "brain_get_feature",
    "brain_list_features",
    "brain_update_feature",
    "brain_search_features",
    # Artifacts
    "brain_write_artifact",
    "brain_read_artifact",
    "brain_list_artifacts",
    # Proofs
    "brain_generate_proof",
    "brain_get_proof",
    "brain_list_proofs",
    # Everything else is implicitly Tier 2
}

# =============================================================================
# TIER RESOLUTION
# =============================================================================

# Global cache for the active tier to avoid repeated lookups during import
_ACTIVE_TIER_CACHE = None

def get_active_tier() -> int:
    """Determine the active tier based on environment variables."""
    global _ACTIVE_TIER_CACHE
    if _ACTIVE_TIER_CACHE is not None:
        return _ACTIVE_TIER_CACHE
        
    # Security through Obscurity (v0.6.0 Friction)
    # Prevents casual users from flipping a simple '1' switch.
    # Hackers who read source will find this. That is acceptable marketing.
    beta_token = os.environ.get("NUCLEUS_BETA_TOKEN", "").strip()
    
    if beta_token == "sovereign-launch-alpha":
        _ACTIVE_TIER_CACHE = 1  # Unlock Manager Suite
    elif beta_token == "titan-sovereign-godmode":
        _ACTIVE_TIER_CACHE = 2  # Unlock Everything
    else:
        _ACTIVE_TIER_CACHE = 0  # Default to Journal Mode
        
    return _ACTIVE_TIER_CACHE


def get_allowed_tools() -> Set[str]:
    """Get the set of tool names allowed for the current tier."""
    tier = get_active_tier()
    
    if tier == 0:
        return TIER_0_LAUNCH.copy()
    elif tier == 1:
        return TIER_0_LAUNCH | TIER_1_CORE
    else:
        # Tier 2 allows all tools
        return None  # None means no filtering


def is_tool_allowed(tool_name: str) -> bool:
    """Check if a specific tool is allowed in the current tier."""
    allowed = get_allowed_tools()
    
    if allowed is None:
        return True  # Tier 2 allows all
    
    return tool_name in allowed


def get_tier_info() -> Dict[str, Any]:
    """Get information about current tier configuration."""
    tier = get_active_tier()
    allowed = get_allowed_tools()
    
    tier_names = {0: "LAUNCH", 1: "CORE", 2: "ADVANCED"}
    
    return {
        "active_tier": tier,
        "tier_name": tier_names.get(tier, "UNKNOWN"),
        "tools_allowed": len(allowed) if allowed else "ALL",
        "tier_0_count": len(TIER_0_LAUNCH),
        "tier_1_count": len(TIER_1_CORE),
        "tier_2_count": len(TIER_2_ADVANCED),
        "env_var": "NUCLEUS_TOOL_TIER",
        "current_value": os.environ.get("NUCLEUS_TOOL_TIER", "0"),
    }


# =============================================================================
# TOOL REGISTRATION FILTER
# =============================================================================

class TierFilteredToolManager:
    """
    Manages tool registration with tier filtering.
    
    Usage:
        manager = TierFilteredToolManager()
        
        @manager.register("brain_my_tool")
        def brain_my_tool():
            pass
    """
    
    def __init__(self):
        self.registered_tools: Set[str] = set()
        self.filtered_tools: Set[str] = set()
    
    def should_register(self, tool_name: str) -> bool:
        """Check if tool should be registered based on tier."""
        allowed = is_tool_allowed(tool_name)
        
        if allowed:
            self.registered_tools.add(tool_name)
        else:
            self.filtered_tools.add(tool_name)
        
        return allowed
    
    def reset(self):
        """Reset registration state. Useful for testing and reconfiguration."""
        self.registered_tools = set()
        self.filtered_tools = set()

    def get_stats(self) -> Dict[str, Any]:
        """Get registration statistics."""
        return {
            "registered": len(self.registered_tools),
            "filtered": len(self.filtered_tools),
            "tier_info": get_tier_info(),
        }


# Global instance for use in __init__.py
tier_manager = TierFilteredToolManager()
