"""
Rabbit-Hole Depth Tracker - MCP server (stdio).

Thin presentation layer over ``store.py``. Every tool opens the local SQLite
store, runs one pure operation, and formats a short human-readable string.
There is no network, no daemon, and no shared state beyond the local DB file.

Run with:  nucleus-rabbithole
       or: python -m mcp_server_nucleus.rabbithole

Import independence guarantee
-----------------------------
This module imports ONLY stdlib + the ``mcp`` package. It does NOT import
anything from sibling ``mcp_server_nucleus`` modules and is designed to run
even if the rest of the nucleus-mcp package is broken or absent.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import store

mcp = FastMCP("nucleus-rabbithole")


def _conn():
    return store.connect()


# ---------------------------------------------------------------------------
# Depth stack
# ---------------------------------------------------------------------------

@mcp.tool()
def depth_push(topic: str) -> str:
    """Push what you're diving into now onto the stack.

    Warns when the stack gets deeper than the configurable max
    (default 4, override with RABBITHOLE_MAX_DEPTH).
    """
    conn = _conn()
    try:
        r = store.depth_push(conn, topic)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    out = f"{r['indicator']} depth {r['current_depth']}/{r['max_depth']} - {r['status']}\n"
    out += f"Path: {r['breadcrumbs']}"
    if r.get("warning"):
        out += f"\n{r['warning']}"
    return out


@mcp.tool()
def depth_pop() -> str:
    """Pop the deepest dive and return to what you were on before it."""
    conn = _conn()
    try:
        r = store.depth_pop(conn)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return f"{r['indicator']} {r['message']}"


@mcp.tool()
def depth_show() -> str:
    """Show the current dive stack, root to current."""
    conn = _conn()
    try:
        r = store.depth_show(conn)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return (
        f"{r['indicator']} depth {r['current_depth']}/{r['max_depth']} - {r['status']}\n"
        f"Path: {r['breadcrumbs']}\n\n{r['tree']}"
    )


@mcp.tool()
def depth_map() -> str:
    """Render the full tangent tree/path for the current session."""
    conn = _conn()
    try:
        r = store.depth_map(conn)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return f"{r['message']}\n\n{r['map']}"


# ---------------------------------------------------------------------------
# Context switching (thrash detector)
# ---------------------------------------------------------------------------

@mcp.tool()
def switch_context(to: str) -> str:
    """Record a subtask switch; nudge you if you've been thrashing.

    A nudge fires when switches inside the recent window exceed the
    threshold (defaults: 30 min window, 5 switches).
    """
    conn = _conn()
    try:
        r = store.switch_context(conn, to)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    out = (
        f"Now on: {r['current_context']}\n"
        f"Switches in last {r['window_minutes']} min: "
        f"{r['switches_in_window']} (threshold {r['threshold']})"
    )
    if r.get("signal"):
        out += f"\n{r['signal']}"
    return out


# ---------------------------------------------------------------------------
# Open loops
# ---------------------------------------------------------------------------

@mcp.tool()
def add_loop(desc: str) -> str:
    """Externalise an open loop (a started-but-unfinished thing)."""
    conn = _conn()
    try:
        r = store.add_loop(conn, desc)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return r["message"]


@mcp.tool()
def list_loops(include_closed: bool = False) -> str:
    """List open loops (set include_closed=true to see closed ones too)."""
    conn = _conn()
    try:
        r = store.list_loops(conn, include_closed=include_closed)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    if not r["loops"]:
        return "No loops. Guilt-free."
    lines = [f"Open loops: {r['open_count']} (showing {r['count']})"]
    for loop in r["loops"]:
        mark = "[ ]" if loop["status"] == "open" else "[x]"
        lines.append(f"{mark} #{loop['id']} {loop['description']}")
    return "\n".join(lines)


@mcp.tool()
def close_loop(id: int) -> str:
    """Close an open loop by its id."""
    conn = _conn()
    try:
        r = store.close_loop(conn, id)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return r["message"]


# ---------------------------------------------------------------------------
# Weekly review
# ---------------------------------------------------------------------------

@mcp.tool()
def weekly_review(days: int = 7) -> str:
    """Summarise what you touched, what's still open, and how much you thrashed."""
    conn = _conn()
    try:
        r = store.weekly_review(conn, days=days)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return r["narrative"]


def main() -> None:
    """Console-script / module entry point: run the stdio server."""
    mcp.run()


if __name__ == "__main__":
    main()
