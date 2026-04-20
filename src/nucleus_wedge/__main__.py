"""nucleus-wedge CLI: ``init``, ``mcp register``, ``mcp serve``, ``bench``.

Default with no args runs ``mcp serve`` for back-compat with existing
``python -m nucleus_wedge`` invocations and ``~/.claude.json`` MCP wiring.

``init`` body in ``init_cmd.py`` (Phase 3, spec §3a).
``mcp register`` body in ``register_cmd.py`` (Phase 4, spec §3b).
``bench`` body in ``bench_cmd.py`` (Phase 6, criterion #1).
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

    bench_p = sub.add_parser("bench", help="Segmented stopwatch (Phase 6, criterion #1).")
    bench_p.add_argument("segment", help="Segment name: clone | init | register | cc_restart | first_recall.")
    bench_p.add_argument("--manual-duration", type=float, help="Operator-supplied wall-clock seconds (no subprocess).")
    bench_p.add_argument("--brain-path", help="Explicit .brain path (overrides env + cwd resolution).")

    return parser


def _split_bench_argv(argv: list[str]) -> tuple[list[str], list[str] | None]:
    """For ``nucleus-wedge bench``, split argv at ``--`` so the command after ``--``
    is preserved verbatim instead of being consumed by argparse flag parsing.
    Returns (argv_for_argparse, command_or_None)."""
    if "--" not in argv:
        return argv, None
    idx = argv.index("--")
    return argv[:idx], argv[idx + 1:]


def _serve() -> None:
    from nucleus_wedge.server import main as serve_main
    serve_main()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    raw = list(sys.argv[1:]) if argv is None else list(argv)
    bench_command: list[str] | None = None
    if raw and raw[0] == "bench":
        raw, bench_command = _split_bench_argv(raw)
    args = parser.parse_args(raw)

    if args.cmd is None:
        _serve()
        return 0

    if args.cmd == "init":
        from nucleus_wedge.init_cmd import do_init
        return do_init(args.brain_path, args.seeds, args.force)

    if args.cmd == "mcp":
        if args.mcp_cmd in (None, "serve"):
            _serve()
            return 0
        if args.mcp_cmd == "register":
            from nucleus_wedge.register_cmd import do_register
            return do_register(args.config_path, args.dry_run)

    if args.cmd == "bench":
        from nucleus_wedge.bench_cmd import do_bench
        return do_bench(args.segment, bench_command, args.manual_duration, args.brain_path)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
