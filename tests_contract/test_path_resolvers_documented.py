"""CLAUDE.md must name every brain-path resolver that exists (CN-3).

Three functions answer "where is .brain", with different precedence and
different failure behaviour. CLAUDE.md's section was titled "Two path systems"
and named two of them, so the third — `nucleus_wedge/store.py::Store.brain_path`
— was invisible to anyone working from that document.

The divergence is deliberate, not an accident to be unified away: the wedge
resolver refuses to walk up to ancestor directories (a cwd-binding hazard its
own spec rules out) and raises instead of falling back, where the runtime
resolver walks up and creates the directory. Someone who does not know it exists
is liable to "fix" one into the other.

These tests pin that the document keeps naming all three, and that the two
behavioural differences it cites are still true of the code.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

CLAUDE_MD = ROOT / "CLAUDE.md"
WEDGE = SRC / "nucleus_wedge" / "store.py"
COMMON = SRC / "mcp_server_nucleus" / "runtime" / "common.py"

pytestmark = pytest.mark.skipif(
    not CLAUDE_MD.exists(), reason="CLAUDE.md not in this export"
)


@pytest.fixture(scope="module")
def guidance():
    return CLAUDE_MD.read_text(encoding="utf-8")


@pytest.mark.parametrize("resolver", ["paths.py", "get_brain_path", "brain_path"])
def test_the_guidance_names_every_resolver(guidance, resolver):
    assert resolver in guidance, (
        f"CLAUDE.md does not mention {resolver}, so someone working from it does "
        "not know that resolver exists"
    )


def test_the_guidance_does_not_claim_there_are_only_two(guidance):
    assert "Two path systems" not in guidance, (
        "the heading still says two; there are three"
    )


@pytest.mark.skipif(not WEDGE.exists(), reason="nucleus_wedge not in this export")
def test_the_wedge_resolver_still_refuses_to_walk_up():
    """One of the two differences CLAUDE.md cites. If it changes, the doc lies."""
    source = WEDGE.read_text(encoding="utf-8")
    fn = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == "brain_path"
    )
    body = ast.unparse(fn)
    assert ".parents" not in body and "while" not in body, (
        "Store.brain_path now walks ancestors; CLAUDE.md says it deliberately "
        "does not, and the wedge spec gives a reason. Update both together."
    )


@pytest.mark.skipif(not WEDGE.exists(), reason="nucleus_wedge not in this export")
def test_the_wedge_resolver_still_raises_rather_than_falling_back():
    """The other difference. Falling back silently is what it exists to avoid."""
    source = WEDGE.read_text(encoding="utf-8")
    fn = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == "brain_path"
    )
    assert any(isinstance(n, ast.Raise) for n in ast.walk(fn)), (
        "Store.brain_path no longer raises when it cannot resolve, so it now has "
        "a silent fallback the documentation says it does not have"
    )


@pytest.mark.skipif(not COMMON.exists(), reason="runtime/common not in this export")
def test_the_runtime_resolver_still_creates_what_is_missing():
    """Asserted in CLAUDE.md, and the reason one probe test had to be rewritten."""
    source = COMMON.read_text(encoding="utf-8")
    fn = next(
        n for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == "get_brain_path"
    )
    assert "mkdir" in ast.unparse(fn), (
        "get_brain_path no longer creates the brain directory; CLAUDE.md says it "
        "does, and at least one test depends on that being true"
    )
