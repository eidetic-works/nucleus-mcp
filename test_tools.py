from mcp_server_nucleus import mcp
import sys

# FastMCP 2.14 internal structure check
print(f"Server class: {mcp.__class__.__name__}")
try:
    tools_dict = mcp._mcp_server.request_handlers
    tool_keys = [k for k in tools_dict.keys() if 'tools' in str(k) or callable(tools_dict[k])]
    print(f"Request handlers: {len(tools_dict)}")
except Exception as e:
    print(f"Error accessing handlers: {e}")

try:
    print(f"Registered tools (internal representation length): {len(mcp._fastmcp_ref.tool_manager.tools)}")
except Exception as e:
    pass
    
from mcp_server_nucleus import tool_tiers
print(f"Active Tier resolved as: {tool_tiers.get_active_tier()}")
print(f"Manager stats: {tool_tiers.tier_manager.get_stats()}")
