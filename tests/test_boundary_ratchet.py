"""Enforce the core/periphery architectural boundary in the full suite.

`scripts/check_boundary.py` is the ratchet (ADR-0043 W1): it hard-fails any
eager core->periphery import and fails when lazy edges grow past the checked-in
ledger. This test runs the checker as a subprocess against the live tree so the
boundary is enforced on every CI run, and exercises the checker's own failure
paths against hermetic synthetic packages so a checker that silently always
passes cannot slip through.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / "scripts" / "check_boundary.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )


def test_checker_exists():
    assert CHECKER.is_file(), f"boundary checker missing at {CHECKER}"


def test_boundary_is_green_on_current_tree():
    """The live tree must satisfy the ratchet. If this fails, a core module
    grew an eager periphery import or lazy edges exceeded the ledger."""
    result = _run(CHECKER)
    assert result.returncode == 0, (
        "boundary check failed on the current tree:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "BOUNDARY CHECK PASSED" in result.stdout


def _synthetic_tree(root: Path, init_body: str, ledger_edges: dict) -> Path:
    """Build tmp/scripts/check_boundary.py + tmp/src/<pkg> so the real checker
    (which resolves src relative to its own location) scans our fake package."""
    pkg = "mcp_server_nucleus"
    scripts = root / "scripts"
    src_pkg = root / "src" / pkg
    scripts.mkdir(parents=True)
    src_pkg.mkdir(parents=True)

    (scripts / "check_boundary.py").write_text(
        CHECKER.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (src_pkg / "__init__.py").write_text(textwrap.dedent(init_body), encoding="utf-8")
    (src_pkg / "periph.py").write_text("VALUE = 1\n", encoding="utf-8")

    (scripts / "core_modules.json").write_text(
        json.dumps({"core_modules": [pkg]}), encoding="utf-8"
    )
    (scripts / "boundary_ledger.json").write_text(
        json.dumps({"total_lazy_edges": sum(ledger_edges.values()), "edges": ledger_edges}),
        encoding="utf-8",
    )
    return scripts / "check_boundary.py"


def test_checker_hard_fails_on_eager_violation(tmp_path):
    """A module-level core->periphery import must hard-fail with file:line."""
    checker = _synthetic_tree(
        tmp_path,
        init_body="from .periph import VALUE\n",  # eager (module level)
        ledger_edges={},
    )
    result = _run(checker)
    assert result.returncode == 1, result.stdout
    assert "EAGER core->periphery" in result.stdout
    assert "periph" in result.stdout
    assert ":1" in result.stdout  # reports the offending line


def test_checker_fails_when_lazy_edges_exceed_ledger(tmp_path):
    """A function-local core->periphery import beyond the ledger cap fails."""
    checker = _synthetic_tree(
        tmp_path,
        init_body="""
        def loader():
            from .periph import VALUE
            return VALUE
        """,
        ledger_edges={},  # cap 0, one lazy edge present -> growth -> fail
    )
    result = _run(checker)
    assert result.returncode == 1, result.stdout
    assert "exceed the ratchet ledger" in result.stdout


def test_checker_passes_lazy_edge_within_ledger(tmp_path):
    """The same lazy edge is allowed when the ledger sanctions it."""
    checker = _synthetic_tree(
        tmp_path,
        init_body="""
        def loader():
            from .periph import VALUE
            return VALUE
        """,
        ledger_edges={"mcp_server_nucleus -> mcp_server_nucleus.periph": 1},
    )
    result = _run(checker)
    assert result.returncode == 0, result.stdout
    assert "BOUNDARY CHECK PASSED" in result.stdout
