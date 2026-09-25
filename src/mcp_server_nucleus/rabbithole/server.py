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

import logging
logger = logging.getLogger(__name__)

import sys
from importlib.metadata import version as _pkg_version

from mcp.server.fastmcp import FastMCP

from . import store


def _version() -> str:
    try:
        return _pkg_version("nucleus-mcp")
    except Exception:
        logger.debug("Swallowed exception in _version", exc_info=True)
        return "1.16.5"


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
# Focus contracts
# ---------------------------------------------------------------------------

@mcp.tool()
def focus_start(
    question: str,
    deliverable: str,
    evidence_budget: int,
    depth_budget: int,
    exit_condition: str,
    session_id: str = "",
) -> str:
    """Start an advisory focus contract for a session."""
    conn = _conn()
    try:
        r = store.focus_start(
            conn,
            question,
            deliverable,
            evidence_budget,
            depth_budget,
            exit_condition,
            session_id or None,
        )
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return (
        f"Focus contract #{r['id']} active: {r['question']}\n"
        f"Deliverable: {r['deliverable']} | evidence {r['evidence_budget']} | "
        f"depth {r['depth_budget']} | exit: {r['exit_condition']}"
    )


@mcp.tool()
def focus_status(session_id: str = "") -> str:
    """Show the active advisory focus contract for a session."""
    conn = _conn()
    try:
        r = store.focus_status(conn, session_id or None)
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    if not r["active"]:
        return f"No active focus contract for session {r['session_id']}."
    contract = r["contract"]
    return (
        f"Focus contract #{contract['id']} active: {contract['question']}\n"
        f"Deliverable: {contract['deliverable']} | evidence remaining "
        f"{contract['remaining_evidence_budget']}/{contract['evidence_budget']} | "
        f"depth budget {contract['depth_budget']} | exit: {contract['exit_condition']}"
    )


@mcp.tool()
def focus_resolve(
    outcome: str,
    evidence: str,
    trigger: str = "",
    owner: str = "",
    missing_fact: str = "",
    session_id: str = "",
) -> str:
    """Explicitly resolve the active focus contract with a valid outcome."""
    conn = _conn()
    try:
        r = store.focus_resolve(
            conn,
            outcome,
            evidence,
            trigger or None,
            owner or None,
            missing_fact or None,
            session_id or None,
        )
    finally:
        conn.close()
    if "error" in r:
        return f"Error: {r['error']}"
    return f"Focus contract #{r['id']} resolved: {r['outcome']}."


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
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(
            "rabbithole -- MCP stdio server\n"
            "\n"
            "Launched by an MCP client. Example client configuration:\n"
            "\n"
            '    {"mcpServers":{"rabbithole":{"command":"nucleus-rabbithole"}}}\n'
            "\n"
            "Options:\n"
            "  -h, --help  show this help message and exit\n"
            "  --version   print the version and exit"
        )
        sys.exit(0)
    elif args and args[0] == "--version":
        print(_version())
        sys.exit(0)
    elif args:
        bad = next(a for a in args if a not in {"--help", "-h", "--version"})
        print(f"error: unknown argument '{bad}'", file=sys.stderr)
        sys.exit(2)
    mcp.run()


if __name__ == "__main__":
    main()
