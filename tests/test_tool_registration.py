"""
Tests for tool registration implementation
"""

import tempfile
import os
import pytest
from unittest.mock import MagicMock

# Set up test environment
_test_dir = tempfile.mkdtemp(prefix="nucleus_reg_env_")
os.environ["NUCLEAR_BRAIN_PATH"] = _test_dir

from mcp_server_nucleus.core import tool_registration_impl
from mcp_server_nucleus.tool_tiers import tier_manager, _ACTIVE_TIER_CACHE
import mcp_server_nucleus.tool_tiers as tool_tiers_module


def test_tier_based_registration():
    """Test tools are registered or filtered based on active tier"""
    # Setup mock MCP
    mock_mcp = MagicMock()
    
    # Reset tier manager state
    tier_manager.reset()
    
    # Reset the global state in tool_registration_impl so configure works cleanly
    tool_registration_impl._original_mcp_tool = None
    tool_registration_impl._REGISTERING_TOOL = False
    
    # Force Tier 0 (LAUNCH mode) by clearing the beta token and resetting cache
    os.environ.pop("NUCLEUS_BETA_TOKEN", None)
    tool_tiers_module._ACTIVE_TIER_CACHE = None
    
    configured_mcp = tool_registration_impl.configure_tiered_tool_registration(mock_mcp)
    
    # Register a tool that IS in TIER_0_LAUNCH (should be registered)
    @configured_mcp.tool()
    def brain_health():
        return "healthy"
    
    # Register a tool that is NOT in any tier set (should be filtered at tier 0)
    @configured_mcp.tool()
    def some_unlisted_tool():
        return "filtered"
    
    # At tier 0, brain_health should be registered, some_unlisted_tool should be filtered
    assert "brain_health" in tier_manager.registered_tools
    assert "some_unlisted_tool" in tier_manager.filtered_tools
    
    # Now test Tier 2 (ADVANCED - all tools pass)
    tier_manager.reset()
    tool_registration_impl._original_mcp_tool = None
    tool_registration_impl._REGISTERING_TOOL = False
    
    # Use a FRESH mock to avoid recursion (previous mock_mcp.tool was replaced with wrapper)
    mock_mcp_t2 = MagicMock()
    
    # Force Tier 2 by setting the godmode token
    os.environ["NUCLEUS_BETA_TOKEN"] = "titan-sovereign-godmode"
    tool_tiers_module._ACTIVE_TIER_CACHE = None
    
    configured_mcp_t2 = tool_registration_impl.configure_tiered_tool_registration(mock_mcp_t2)
    
    @configured_mcp_t2.tool()
    def any_custom_tool():
        return "allowed"
    
    # At tier 2, all tools should be registered (none filtered)
    assert "any_custom_tool" in tier_manager.registered_tools
    assert len(tier_manager.filtered_tools) == 0
    
    # Cleanup
    os.environ.pop("NUCLEUS_BETA_TOKEN", None)
    tool_tiers_module._ACTIVE_TIER_CACHE = None

