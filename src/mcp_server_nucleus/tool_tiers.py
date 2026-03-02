"""
Nucleus Tool Tier System - Facade-Aware Registry Control

Updated for v2.0 Super-Tools Facade pattern.
With ~170 individual tools consolidated into 12 facade tools, tier filtering
now operates on facade names (nucleus_*) instead of individual brain_* names.

Tiers:
- Tier 0 (LAUNCH): Essential facades for nucleusos.dev demo (engrams, governance)
- Tier 1 (CORE): Tier 0 + orchestration/task/session facades
- Tier 2 (ADVANCED): All 12 facade tools

Set NUCLEUS_BETA_TOKEN to control which tier is active:
- (unset):                    Tier 0 — Journal Mode (default)
- "sovereign-launch-alpha":   Tier 1 — Manager Suite
- "titan-sovereign-godmode":  Tier 2 — Everything

Author: Nucleus Team
Version: 2.0.0
"""

import os
from typing import Set, Dict, Any

# =============================================================================
# TIER DEFINITIONS (Facade-Aware)
# =============================================================================
# Each entry is a registered @mcp.tool() facade function name.
# Individual actions within facades are NOT filtered — the facade itself
# is the unit of access control.

TIER_0_LAUNCH: Set[str] = {
    # ═══════════════════════════════════════════════════════════════════════
    # Essential facades for demo / nucleusos.dev launch
    # ═══════════════════════════════════════════════════════════════════════
    "nucleus_engrams",           # Memory: write, query, search, health, version, morning brief
    "nucleus_governance",        # Governance: lock, unlock, watch, audit, hypervisor, mode
}

TIER_1_CORE: Set[str] = {
    # ═══════════════════════════════════════════════════════════════════════
    # Manager Suite — task management, sessions, orchestration
    # ═══════════════════════════════════════════════════════════════════════
    "nucleus_tasks",             # Task + depth management (add, list, claim, depth_push, etc.)
    "nucleus_sessions",          # Session management (save, resume, start, checkpoint, etc.)
    "nucleus_sync",              # Multi-agent sync (identify, sync_now, read/write artifacts)
    "nucleus_orchestration",     # Core orchestration (satellite, commitments, loops, metrics)
    "nucleus_slots",             # Slot management (orchestrate, missions, sprints)
    "nucleus_telemetry",         # Telemetry (LLM tiers, interactions, protocols)
}

TIER_2_ADVANCED: Set[str] = {
    # ═══════════════════════════════════════════════════════════════════════
    # Full power — federation, features, infra, agents
    # ═══════════════════════════════════════════════════════════════════════
    "nucleus_federation",        # Federation (join, leave, peers, route, health)
    "nucleus_features",          # Feature map + proofs + mounter (add, list, mount, proof)
    "nucleus_infra",             # Infrastructure (gcloud, strategy, file changes, export)
    "nucleus_agents",            # Agent management (spawn, critique, dashboard, ingest)
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
        
        @manager.register("nucleus_my_facade")
        def nucleus_my_facade():
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
