"""Runtime-manifest bijection gate — sweep #003 vaccine for sweep #001 inventory.

Discharge criterion 6 + the named sweep #002 vaccine (upgraded from decorator-
grep per peer verdict 2026-06-11T04:03Z). Catches three regression classes
that a decorator-grep gate leaks:

  1. Server C (eidetic daemon bridge) uses dispatch-table registration with
     ZERO @mcp.tool decorator occurrences.
  2. Dead-in-registry: a module's @mcp.tool() can exist while the module is
     absent from tools/__init__.py _ALL_MODULES (decorator present + row
     present, tool NEVER loads).
  3. NUCLEUS_ACTIVE_MODULES env whitelist disables modules post-registry.

Mechanism: import each of the three Nucleus MCP servers, enumerate the
ACTUALLY-registered tools (FastMCP exposes the list; Server C's list_tools
handler returns its array), then diff BOTH directions against docs/
PRIMITIVES.md rows. Catches additions, deletions, and dead rows in one
cheap import per server.

CI invocation:
    python scripts/primitives_bijection_gate.py
Exit code 0 = bijection holds, 1 = drift, 2 = scan failed (e.g. import error).

Server C is gated by NUCLEUS_BIJECTION_SCAN_SERVER_C=1 (default: skip) since
that repo lives outside mcp-server-nucleus; CI runners that don't have it
mounted should not block.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable


_PRIMITIVES_TABLE_ROW_RX = re.compile(
    r"^\|\s*\d+\s*\|\s*`([a-z_][a-z0-9_]*)`\s*\|",
    re.MULTILINE,
)
_SERVER_SECTION_RX = re.compile(
    r"^##\s*Server\s+([ABC])\b",
    re.MULTILINE | re.IGNORECASE,
)


def primitives_from_doc(doc_path: Path) -> set[str]:
    """Extract registered tool names from docs/PRIMITIVES.md table rows."""
    if not doc_path.exists():
        return set()
    text = doc_path.read_text()
    return set(_PRIMITIVES_TABLE_ROW_RX.findall(text))


def primitives_per_server(doc_path: Path) -> dict[str, set[str]]:
    """Return {server_letter: {tool_names}} parsed from doc sections.

    A row landed in the section it appears under; rows outside any
    ## Server X heading are assigned to 'unsectioned' (for backward-compat
    docs that don't structure by server).
    """
    if not doc_path.exists():
        return {}
    text = doc_path.read_text()
    section_marks = [(m.start(), m.group(1).upper()) for m in _SERVER_SECTION_RX.finditer(text)]
    section_marks.append((len(text), None))

    out: dict[str, set[str]] = {}
    unsectioned: set[str] = set()
    first_section_start = section_marks[0][0] if section_marks else 0
    pre = text[:first_section_start]
    unsectioned.update(_PRIMITIVES_TABLE_ROW_RX.findall(pre))

    for i in range(len(section_marks) - 1):
        start, letter = section_marks[i]
        end, _ = section_marks[i + 1]
        body = text[start:end]
        names = set(_PRIMITIVES_TABLE_ROW_RX.findall(body))
        out.setdefault(letter, set()).update(names)

    if unsectioned:
        out.setdefault("unsectioned", set()).update(unsectioned)
    return out


def server_a_tools() -> set[str] | None:
    """Enumerate the actually-registered facade tools for Server A.

    Imports mcp_server_nucleus — which runs the production register_all() at
    module-init against its own FastMCP instance — and enumerates that LIVE
    registration. Returns None if the import fails (scan failure) or if the
    FastMCP instance exposes neither get_tools nor list_tools.
    """
    try:
        import mcp_server_nucleus
    except ImportError:
        return None
    return _enumerate_fastmcp_tools(mcp_server_nucleus.mcp)


def server_b_tools() -> set[str] | None:
    """Enumerate the actually-registered facade tools for Server B (nucleus_wedge).
    Returns None if Server B can't be enumerated (import error or API mismatch)."""
    try:
        from nucleus_wedge.server import build_server
    except ImportError:
        return None
    mcp = build_server()
    return _enumerate_fastmcp_tools(mcp)


def server_c_tools() -> set[str] | None:
    """Enumerate the dispatch-table tools for Server C (eidetic daemon bridge).

    Gated by NUCLEUS_BIJECTION_SCAN_SERVER_C=1 since this repo lives outside
    mcp-server-nucleus. Returns set() (NOT None) when scan disabled — that's
    a valid 'opt-out' signal distinct from None ('scan attempted but failed').
    Returns None when scan enabled but bridge import fails — so main() can
    exit 2 (scan failed) instead of 0 (false green via empty set).
    """
    if os.environ.get("NUCLEUS_BIJECTION_SCAN_SERVER_C") != "1":
        return set()

    # Path is fleet-typical; override via NUCLEUS_EIDETIC_BRIDGE_PATH if needed.
    bridge_root = os.environ.get(
        "NUCLEUS_EIDETIC_BRIDGE_PATH",
        str(Path.home() / "eidetic-daemon" / "bridge" / "python"),
    )
    if bridge_root not in sys.path:
        sys.path.insert(0, bridge_root)

    try:
        from eidetic_mcp import server as _ec_server  # type: ignore
    except ImportError:
        return None  # cc-main crack #4: scan-enabled-but-failed -> exit 2

    # Server C registers via @server.list_tools() handler that returns
    # a list of Tool objects with .name. We invoke the handler.
    tools_fn = getattr(_ec_server, "list_tools_handler", None)
    fallback = lambda: _scan_server_c_dispatch_table(_ec_server)
    if tools_fn is None:
        result = fallback()
    else:
        try:
            tools = tools_fn()
            result = {t.name for t in tools if hasattr(t, "name")}
        except Exception:
            result = fallback()

    # Peer residual nit (2026-06-11T10:31Z): when scan is ENABLED (knob=1) and
    # the bridge is importable but yields zero tools, that's almost certainly a
    # handler/parser failure (a live bridge should have >=1 tool). Returning
    # set() would conflate this with the scan-disabled opt-out path. Returning
    # None routes it to main()'s exit-2 'scan failed' arm — the same shape
    # crack-4 closed for the other server enumerators.
    if not result:
        return None
    return result


def _scan_server_c_dispatch_table(module) -> set[str]:
    """Fallback: grep module source for Tool(name="...") instances."""
    src = Path(getattr(module, "__file__", "")).read_text() if getattr(module, "__file__", None) else ""
    return set(re.findall(r'Tool\(\s*name\s*=\s*[\'"]([a-z_][a-z0-9_]*)[\'"]', src))


def _is_coro(fn) -> bool:
    """Peer residual nit (2026-06-11T10:31Z): asyncio.iscoroutinefunction emits a
    DeprecationWarning on Python 3.14 and is slated for removal in 3.16.
    inspect.iscoroutinefunction is the documented-stable replacement.
    """
    import inspect
    return inspect.iscoroutinefunction(fn)


def _enumerate_fastmcp_tools(mcp) -> set[str] | None:
    """Pull registered tool names from a FastMCP instance.

    Two API variants exist depending on which FastMCP a deployment is using:
    - Standalone `fastmcp` package (2.14+): `await mcp.get_tools()` returns
      `dict[str, Tool]`.
    - Official mcp SDK `mcp.server.fastmcp.FastMCP`: `await mcp.list_tools()`
      returns `Sequence[Tool]` with `.name` per item.

    cc-main empirical finding 2026-06-11T08:09Z: my prior single-API code
    silently returned set() against fastmcp 2.14.3 (no list_tools attribute)
    while the same process logged 'Registered 20 facade tools' — gate had
    never empirically passed against real servers. Returns None to signal
    'enumeration failed' (gate distinguishes from set() = scan-succeeded-empty),
    so main() can exit 2 (scan failed) instead of 1 (drift detected).
    """
    import asyncio

    get_tools = getattr(mcp, "get_tools", None)
    list_tools = getattr(mcp, "list_tools", None)
    if get_tools is None and list_tools is None:
        return None  # signal: enumeration impossible

    try:
        if get_tools is not None:
            tools = asyncio.run(get_tools()) if _is_coro(get_tools) else get_tools()
            if hasattr(tools, "keys"):
                return set(tools.keys())
            return {t.name for t in tools if hasattr(t, "name")}
        tools = asyncio.run(list_tools()) if _is_coro(list_tools) else list_tools()
        return {t.name for t in tools if hasattr(t, "name")}
    except RuntimeError:
        # Already in an event loop (unlikely in CI; defensive).
        return None
    except Exception:
        # Anything else from the enumerator path: signal failure, not empty.
        return None


def diff_bijection(
    *,
    doc_primitives: set[str],
    a: set[str],
    b: set[str],
    c: set[str],
) -> dict[str, list[str]]:
    """Compute both-direction diff: documented-only and registered-only."""
    registered = a | b | c
    return {
        "documented_but_not_registered": sorted(doc_primitives - registered),
        "registered_but_not_documented": sorted(registered - doc_primitives),
        "shared": sorted(doc_primitives & registered),
    }


def _default_doc_path() -> Path:
    """Resolve PRIMITIVES.md relative to this script, not cwd (cc-main minor d).
    Script lives at <repo>/mcp-server-nucleus/scripts/; doc at <repo>/docs/."""
    return Path(__file__).parent.parent.parent / "docs" / "PRIMITIVES.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--doc", default=None, help=f"path to PRIMITIVES.md (default: {_default_doc_path()})")
    ap.add_argument("--allow-drift", action="store_true",
                    help="exit 0 even if drift detected; print report only (default: exit 1 on drift)")
    args = ap.parse_args(argv)

    doc_path = Path(args.doc) if args.doc else _default_doc_path()
    doc = primitives_from_doc(doc_path)
    if not doc:
        print(f"[bijection-gate] FATAL: no primitive rows found in {doc_path}", file=sys.stderr)
        return 2

    a = server_a_tools()
    b = server_b_tools()
    c = server_c_tools()

    # cc-main crack #4: distinguish scan failure (None) from scan succeeded but
    # empty (set()). Any None -> exit 2 (scan failed) — not exit 1 (drift) and
    # not exit 0 (false green via excluded-section path).
    failures = [n for n, v in [("A", a), ("B", b), ("C", c)] if v is None]
    if failures:
        print(f"[bijection-gate] FATAL: enumeration failed for {failures}; "
              f"refusing to report drift on incomplete scan.", file=sys.stderr)
        return 2

    # If Server C scan is disabled (returned set()) and the doc has a Server
    # C section, drop those rows from the bijection check — otherwise they
    # always show as "documented_but_not_registered" drift, which is a false
    # positive in CI runners without the eidetic-daemon bridge mounted.
    if not c:
        per_server = primitives_per_server(doc_path)
        c_section = per_server.get("C", set())
        if c_section:
            doc = doc - c_section
            print(f"[bijection-gate] Server C scan disabled — {len(c_section)} doc rows excluded from bijection.", file=sys.stderr)

    diff = diff_bijection(doc_primitives=doc, a=a, b=b, c=c)
    drift = bool(diff["documented_but_not_registered"] or diff["registered_but_not_documented"])

    print(f"Server A registered: {len(a)}", file=sys.stderr)
    print(f"Server B registered: {len(b)}", file=sys.stderr)
    print(f"Server C registered: {len(c)}", file=sys.stderr)
    print(f"Documented: {len(doc)}", file=sys.stderr)
    print(f"Shared: {len(diff['shared'])}", file=sys.stderr)

    if drift:
        print(file=sys.stderr)
        print("DRIFT DETECTED", file=sys.stderr)
        if diff["documented_but_not_registered"]:
            print(f"  documented_but_not_registered ({len(diff['documented_but_not_registered'])}): {diff['documented_but_not_registered']}", file=sys.stderr)
        if diff["registered_but_not_documented"]:
            print(f"  registered_but_not_documented ({len(diff['registered_but_not_documented'])}): {diff['registered_but_not_documented']}", file=sys.stderr)
        if args.allow_drift:
            return 0
        return 1

    print("OK: PRIMITIVES.md bijects with live registrations.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
