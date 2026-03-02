"""Federation tools: status, join, leave, peers, sync, route, health.

Super-Tools Facade: All 7 federation actions exposed via a single
`nucleus_federation(action, params)` MCP tool.
"""

import json
from typing import Dict, List

from ._dispatch import async_dispatch


def register(mcp, helpers):
    """Register the nucleus_federation facade tool with the MCP server."""
    make_response = helpers["make_response"]

    from ..runtime.federation_ops import (
        _brain_federation_status_impl, _brain_federation_join_impl,
        _brain_federation_leave_impl, _brain_federation_peers_impl,
        _brain_federation_sync_impl, _brain_federation_route_impl,
        _brain_federation_health_impl,
    )

    ROUTER = {
        "status": lambda: _brain_federation_status_impl(),
        "join": lambda seed_peer: _brain_federation_join_impl(seed_peer),
        "leave": lambda: _brain_federation_leave_impl(),
        "peers": lambda: _brain_federation_peers_impl(),
        "sync": lambda: _brain_federation_sync_impl(),
        "route": lambda task_id, profile="default": _brain_federation_route_impl(task_id, profile),
        "health": lambda: _brain_federation_health_impl(),
    }

    @mcp.tool()
    async def nucleus_federation(action: str, params: dict = {}) -> str:
        """Federation management for multi-brain coordination.

Actions:
  status  - Get comprehensive federation status
  join    - Join a federation via seed peer. params: {seed_peer}
  leave   - Leave the federation gracefully
  peers   - List all federation peers with details
  sync    - Force immediate synchronization with all peers
  route   - Route a task to the optimal brain. params: {task_id, profile?}
  health  - Get federation health dashboard
"""
        return await async_dispatch(action, params, ROUTER, "nucleus_federation")

    return [("nucleus_federation", nucleus_federation)]
