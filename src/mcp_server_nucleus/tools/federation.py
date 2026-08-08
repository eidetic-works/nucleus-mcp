"""Federation tools: status, join, leave, peers, sync, route, health.

Super-Tools Facade: All 7 federation actions exposed via a single
`nucleus_federation(action, params)` MCP tool.
"""

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

    async def _h_join(seed_peer: str):
        return await _brain_federation_join_impl(seed_peer)

    async def _h_leave():
        return await _brain_federation_leave_impl()

    async def _h_sync():
        return await _brain_federation_sync_impl()

    async def _h_route(task_id: str, profile: str = "default"):
        return await _brain_federation_route_impl(task_id, profile)

    ROUTER = {
        "status": lambda: _brain_federation_status_impl(),
        "join": _h_join,
        "leave": _h_leave,
        "peers": lambda: _brain_federation_peers_impl(),
        "sync": _h_sync,
        "route": _h_route,
        "health": lambda: _brain_federation_health_impl(),
    }

    @mcp.tool(title="Federation", annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})
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
