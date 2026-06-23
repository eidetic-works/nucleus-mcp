"""
Nucleus Read-Only MCP Server — Microsoft 365 Copilot variant.

Exposes ONLY tools with readOnlyHint=True, suitable for platforms that
restrict MCP tools to search/fetch operations (Microsoft 365 Copilot
federated connectors, enterprise sandboxes).

Tools exposed (4):
  - nucleus_search      — Search engrams (memory) by substring. readOnlyHint=True.
  - nucleus_audit       — Query/verify tamper-evident audit log. readOnlyHint=True.
  - nucleus_route       — Route prompts to optimal model tier. readOnlyHint=True.
  - nucleus_relay_subscribe — Long-poll relay inbox subscription. readOnlyHint=True.

Mounted at: /mcp-readonly
Full server: /mcp (all 17 tools, including write tools)

Env vars:
  NUCLEUS_BRAIN_PATH  — Path to .brain directory (same as main server)
  PORT                — Cloud Run port (default: 8080)
"""

import os
import sys
import logging

os.environ.setdefault("FASTMCP_SHOW_CLI_BANNER", "False")
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nucleus.readonly")

from fastmcp import FastMCP

# --- Create a separate FastMCP instance for read-only tools ---
_readonly_mcp = FastMCP("Nucleus Brain (Read-Only)")

# --- Build the helpers dict (same shape as __init__.py _tool_helpers) ---
from mcp_server_nucleus.runtime.common import (
    get_brain_path,
    make_response,
    _get_state,
    _update_state,
)
from mcp_server_nucleus.runtime.event_ops import _emit_event, _read_events
from mcp_server_nucleus import get_orch

_tool_helpers = {
    "get_brain_path": get_brain_path,
    "make_response": make_response,
    "emit_event": _emit_event,
    "read_events": _read_events,
    "get_state": _get_state,
    "update_state": _update_state,
    "get_orch": get_orch,
}

# --- Register the 2 existing read-only tool modules (audit + cost router) ---
from mcp_server_nucleus.tools import audit_log_tool, cost_router

audit_log_tool.register(_readonly_mcp, _tool_helpers)
cost_router.register(_readonly_mcp, _tool_helpers)

# --- Register ONLY nucleus_relay_subscribe from sync module ---
# (sync module also registers nucleus_sync and nucleus_ccr_arm which are write tools)
from fastmcp import Context
from mcp_server_nucleus.runtime.relay_notify import relay_subscribe_notifications_impl


@_readonly_mcp.tool(
    title="Relay Subscription",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
async def nucleus_relay_subscribe(
    ctx: Context,
    timeout_seconds: int = 270,
    role: str = "",
    inbox_filter: str = "",
) -> dict:
    """Long-poll subscription that pushes ctx.info() on each new inbox file.

    Replaces bash polling daemons with server-initiated push. Call once at
    session start. Server holds the subscription, watches the calling agent's
    role-specific inbox dir, and fires info-level notifications on each new
    relay file arrival. Client re-calls this in a loop for persistent coverage.

    Args:
      timeout_seconds: max subscription duration (60..1800, default 270).
      role: override calling agent's role (default: env-detected).
      inbox_filter: explicit inbox dir NAME (e.g., "cc_tb"). Bypasses role
                    detection when provided.

    Returns:
      dict with subscribed_dir, watched_seconds, events_fired, last_seen_id,
      next_action.
    """
    return await relay_subscribe_notifications_impl(
        ctx,
        timeout_seconds=timeout_seconds,
        role=role or None,
        inbox_filter=inbox_filter or None,
    )

# --- Register a new nucleus_search tool (read-only engram search) ---
from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl


@_readonly_mcp.tool(
    title="Search Memories",
    annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
)
def nucleus_search(query: str, case_sensitive: bool = False, limit: int = 50) -> str:
    """Search the Nucleus Brain's persistent memory (engrams) by keyword.

    Finds all engrams containing the query string (substring match).
    Searches both the decision ledger and the relay projection history.

    Args:
      query: Search term (substring match, case-insensitive by default).
      case_sensitive: Set to True for case-sensitive search. Default: False.
      limit: Max results to return (default 50, max 500).

    Returns:
      JSON string with matching engrams. Each engram has:
      key, value, context, intensity, timestamp, source.
    """
    return _brain_search_engrams_impl(query, case_sensitive, limit)


def get_readonly_app(transport: str = "streamable-http"):
    """Return the ASGI app for the read-only MCP server.

    The path is set to '/' so that when mounted at /mcp-readonly in the
    parent Starlette app, the MCP endpoint is accessible at /mcp-readonly/
    (with trailing slash).
    """
    return _readonly_mcp.http_app(transport=transport, path="/")
