"""nucleus-wedge CLI: ``init``, ``mcp register``, ``mcp serve``.

Default with no args runs ``mcp serve`` for back-compat with existing
``python -m nucleus_wedge`` invocations and ``~/.claude.json`` MCP wiring.

Subcommand bodies for ``init`` and ``mcp register`` land in Phases 3 and 4
(spec ``.brain/plans/week2_init_flow_spec.md`` §3a / §3b). Phase 2 ships
scaffolding only — argparse surface + stubs that exit non-zero.
"""
from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nucleus-wedge",
        description="Nucleus wedge — remember/recall MCP server + init/register CLI.",
    )
    sub = parser.add_subparsers(dest="cmd")

    init_p = sub.add_parser("init", help="Initialize .brain/ substrate (Phase 3).")
    init_p.add_argument("--brain-path", help="Explicit .brain path (overrides env + cwd resolution).")
    init_p.add_argument("--seeds", choices=["default", "none"], default="default", help="Seed set to install.")
    init_p.add_argument("--force", action="store_true", help="Overwrite AGENTS.md stub if present.")

    mcp_p = sub.add_parser("mcp", help="MCP server management.")
    mcp_sub = mcp_p.add_subparsers(dest="mcp_cmd")

    reg_p = mcp_sub.add_parser("register", help="Register nucleus_wedge in ~/.claude.json (Phase 4).")
    reg_p.add_argument("--config-path", help="Explicit config path (overrides ~/.claude.json default).")
    reg_p.add_argument("--dry-run", action="store_true", help="Print diff; do not write.")

    serve_p = mcp_sub.add_parser("serve", help="Run the wedge MCP server (default if no subcommand).")
    serve_p.add_argument("--brain-path", help="Explicit .brain path (overrides env + cwd resolution).")

    return parser


def _serve() -> None:
    from nucleus_wedge.server import main as serve_main
    serve_main()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        _serve()
        return 0

    if args.cmd == "init":
        print("nucleus-wedge init: not implemented (Phase 3)", file=sys.stderr)
        return 1

    if args.cmd == "mcp":
        if args.mcp_cmd in (None, "serve"):
            _serve()
            return 0
        if args.mcp_cmd == "register":
            print("nucleus-wedge mcp register: not implemented (Phase 4)", file=sys.stderr)
            return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
