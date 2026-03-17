"""Tool Tier Definitions for Nucleus Security Hardening."""
from enum import IntEnum

class ToolTier(IntEnum):
    T0_READ = 0
    T1_INFO = 1
    T2_CODE = 2
    T3_SYSTEM = 3

# Mapping of facade:action to their required tiers
TOOL_TIER_MAPPING = {
    # T0: Read-only status and health
    "nucleus_governance:status": ToolTier.T0_READ,
    "nucleus_governance:handshake": ToolTier.T0_READ,
    "nucleus_engrams:health": ToolTier.T0_READ,
    "nucleus_engrams:version": ToolTier.T0_READ,
    "nucleus_engrams:morning_brief": ToolTier.T0_READ,
    "nucleus_tasks:list": ToolTier.T0_READ,
    "nucleus_tasks:get_next": ToolTier.T0_READ,
    "nucleus_sessions:list": ToolTier.T0_READ,
    "nucleus_telemetry:dispatch_metrics": ToolTier.T0_READ,
    "nucleus_pm_view:summary": ToolTier.T0_READ,
    
    # T1: Information gathering and non-destructive context
    "nucleus_engrams:audit_log": ToolTier.T1_INFO,
    "nucleus_engrams:query_engrams": ToolTier.T1_INFO,
    "nucleus_engrams:search_engrams": ToolTier.T1_INFO,
    "nucleus_engrams:context_graph": ToolTier.T1_INFO,
    "nucleus_engrams:engram_neighbors": ToolTier.T1_INFO,
    "nucleus_engrams:render_graph": ToolTier.T1_INFO,
    "nucleus_engrams:billing_summary": ToolTier.T1_INFO,
    "nucleus_tasks:depth_show": ToolTier.T1_INFO,
    "nucleus_pm_view:gantt": ToolTier.T1_INFO,
    "nucleus_self_healing:diagnose": ToolTier.T1_INFO,
    
    # T2: State modifications (Engrams, Tasks, Sessions)
    "nucleus_engrams:write_engram": ToolTier.T2_CODE,
    "nucleus_self_healing:refactor": ToolTier.T2_CODE,
    "nucleus_tasks:add": ToolTier.T2_CODE,
    "nucleus_tasks:update": ToolTier.T2_CODE,
    "nucleus_tasks:claim": ToolTier.T2_CODE,
    "nucleus_tasks:depth_push": ToolTier.T2_CODE,
    "nucleus_tasks:depth_pop": ToolTier.T2_CODE,
    "nucleus_sessions:save": ToolTier.T2_CODE,
    "nucleus_sessions:resume": ToolTier.T2_CODE,
    "nucleus_engrams:pulse_and_polish": ToolTier.T2_CODE,
    "nucleus_engrams:self_healing_sre": ToolTier.T2_CODE,
    "nucleus_engrams:fusion_reactor": ToolTier.T2_CODE,
    
    # T3: System-level control and high-risk operations
    "nucleus_governance:lock": ToolTier.T3_SYSTEM,
    "nucleus_governance:unlock": ToolTier.T3_SYSTEM,
    "nucleus_governance:set_mode": ToolTier.T3_SYSTEM,
    "nucleus_governance:list_directory": ToolTier.T3_SYSTEM,
    "nucleus_governance:delete_file": ToolTier.T3_SYSTEM,
    "nucleus_governance:pip_install": ToolTier.T3_SYSTEM,
    "nucleus_governance:curl": ToolTier.T3_SYSTEM,
    "nucleus_agents:spawn_agent": ToolTier.T3_SYSTEM,
    "nucleus_agents:chief": ToolTier.T3_SYSTEM,
    "nucleus_self_healing:fix": ToolTier.T3_SYSTEM,
}

def get_tool_tier(facade_name: str, action: str) -> ToolTier:
    """Return the tier for a given tool/action, defaulting to T2 if unknown."""
    key = f"{facade_name}:{action}"
    return TOOL_TIER_MAPPING.get(key, ToolTier.T2_CODE)

def is_authorized(agent_tier: str, facade_name: str, action: str) -> bool:
    """Check if an agent tier is authorized to run a specific tool action."""
    try:
        # Support short names like "T2" as well as full names like "T2_CODE"
        tier_str = agent_tier.upper() if agent_tier else "T1_INFO"
        if tier_str in ["T0", "T1", "T2", "T3"]:
            mapping = {"T0": "T0_READ", "T1": "T1_INFO", "T2": "T2_CODE", "T3": "T3_SYSTEM"}
            tier_str = mapping[tier_str]
        
        a_tier = ToolTier[tier_str]
    except (KeyError, ValueError):
        a_tier = ToolTier.T1_INFO
        
    required_tier = get_tool_tier(facade_name, action)
    return a_tier >= required_tier
