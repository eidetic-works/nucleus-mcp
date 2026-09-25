#!/usr/bin/env python3
"""Count the MCP surface: facades, tools, actions, resources, prompts.

Why this exists
---------------
Three places stated the tool count and all three disagreed (audit ledger CL-1):
README said "114 MCP tools across 13 facades" in one paragraph and "13 tools, 10
resources, 3 prompts" in a table forty lines later, while tools/_dispatch.py's
docstring said "12 facades / 171 actions". None matched the code.

Hand-maintained counts drift the moment anyone adds a tool. Run this instead and
paste what it prints.

    python3 tools_audit/count_surface.py

Counts statically, by parsing the source — no import, so it works without fastmcp
or any runtime dependency installed. It counts what is DEFINED. What a given
client actually sees also depends on NUCLEUS_TOOL_TIER (default 2 = everything)
and NUCLEUS_ACTIVE_MODULES, so treat these as the ceiling.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, *here.parents):
        if (candidate / "src" / "mcp_server_nucleus").is_dir():
            return candidate
    sys.exit("could not locate src/mcp_server_nucleus/")


def mcp_decorated(tree: ast.AST, attr: str) -> list[str]:
    """Function names carrying @mcp.<attr> or @mcp.<attr>(...)."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == attr:
                found.append(node.name)
    return found


def router_size(tree: ast.AST) -> int:
    total = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Name) and tgt.id == "ROUTER"
                        and isinstance(node.value, ast.Dict)):
                    total += len(node.value.keys)
    return total


def main() -> int:
    pkg = repo_root() / "src" / "mcp_server_nucleus"

    facades, actions = [], 0
    for path in sorted((pkg / "tools").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = mcp_decorated(tree, "tool")
        if names:
            facades.append((path.stem, names))
        actions += router_size(tree)

    server = ast.parse((pkg / "server.py").read_text(encoding="utf-8"))
    resources = mcp_decorated(server, "resource")
    prompts = mcp_decorated(server, "prompt")
    tools = sum(len(n) for _, n in facades)

    print("Nucleus MCP surface, counted from source\n")
    print(f"  facade modules exposing tools : {len(facades)}")
    print(f"  MCP tools                     : {tools}")
    print(f"  actions across their ROUTERs  : {actions}")
    print(f"  brain:// resources            : {len(resources)}")
    print(f"  prompts                       : {len(prompts)}")
    print("\n  Ceiling, not a guarantee: NUCLEUS_TOOL_TIER and")
    print("  NUCLEUS_ACTIVE_MODULES can register fewer.\n")

    for stem, names in facades:
        print(f"  {stem:<20} {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
