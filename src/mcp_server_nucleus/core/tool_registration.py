"""
Tool Registration Module
Handles tier-based tool registration and protocol coupling fix
"""

import sys
import os

# Import tier management functions
from ..tool_tiers import get_active_tier, get_tier_info, is_tool_allowed, tier_manager

def configure_tiered_tool_registration(mcp):
    """
    Configure tier-based tool registration system
    """
    global _REGISTERING_TOOL
    
    # Capture original method before replacing it
    _original_mcp_tool = mcp.tool
    _REGISTERING_TOOL = False

    def _tiered_tool_wrapper(*args, **kwargs):
        # [Full implementation from lines 87-171 of __init__.py]
        # ...

    # Replace mcp.tool with tiered wrapper
    mcp.tool = _tiered_tool_wrapper
    return mcp
