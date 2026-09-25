"""CLI surface tests for ``nucleus_wedge.__main__``.

Covers:
- top-level ``--help`` lists ``init`` + ``mcp`` subcommands
- each subcommand surface declares ≤3 user-facing flags (per kickoff plan)

Behavioural tests for each subcommand body live in their own file
(``test_init_cmd.py``, ``test_register_cmd.py``).
"""
from __future__ import annotations

import argparse

from nucleus_wedge.__main__ import _build_parser


def _subparser(parser: argparse.ArgumentParser, *names: str) -> argparse.ArgumentParser:
    current = parser
    for name in names:
        sub_action = next(a for a in current._actions if isinstance(a, argparse._SubParsersAction))
        current = sub_action.choices[name]
    return current


def _flag_count(parser: argparse.ArgumentParser) -> int:
    return sum(
        1 for a in parser._actions
        if a.option_strings and "--help" not in a.option_strings
    )


def test_top_level_has_init_and_mcp_subcommands() -> None:
    parser = _build_parser()
    sub_action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "init" in sub_action.choices
    assert "mcp" in sub_action.choices


def test_init_has_at_most_three_flags() -> None:
    init = _subparser(_build_parser(), "init")
    assert _flag_count(init) <= 3


def test_mcp_register_has_at_most_three_flags() -> None:
    reg = _subparser(_build_parser(), "mcp", "register")
    assert _flag_count(reg) <= 3


def test_mcp_serve_has_at_most_three_flags() -> None:
    serve = _subparser(_build_parser(), "mcp", "serve")
    assert _flag_count(serve) <= 3
