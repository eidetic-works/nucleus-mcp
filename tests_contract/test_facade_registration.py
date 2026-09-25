"""Every facade's register() must return (name, func) pairs.

`tools/__init__.py::register_all` does:

    result = mod.register(mcp, helpers)
    for name, func in result:
        setattr(parent, name, func)

wrapped in a bare `except Exception` that prints one stderr line and moves on
(audit ledger CP-3). So a facade returning the wrong shape does not fail the
build, fail a test, or fail the boot — it prints

    [Nucleus] Module 'grounding' failed to register: cannot unpack non-iterable
    function object

and silently drops out of the re-export surface. That line sat in CI output on
every run until someone read it.

This is a static check rather than a live registration, deliberately: calling
register() needs a real MCP object and a populated helpers dict, and a test that
needs the whole server up to check a return shape will get skipped the first time
it is inconvenient.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src" / "mcp_server_nucleus" / "tools"

# Modules in tools/ that are helpers, not facades — they have no register().
NOT_FACADES = {"__init__", "_dispatch", "_envelope", "_marketplace_core",
               "_pair_actions", "_retry", "plan_review_loop"}


def facade_modules():
    return sorted(
        p for p in TOOLS.glob("*.py")
        if p.stem not in NOT_FACADES
    )


def register_returns(path: Path):
    """Every `return <list>` inside the module's top-level register()."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "register":
            return [
                n.value for n in ast.walk(node)
                if isinstance(n, ast.Return) and isinstance(n.value, (ast.List, ast.Tuple))
            ]
    return None


@pytest.mark.parametrize("path", facade_modules(), ids=lambda p: p.stem)
def test_register_returns_name_func_pairs(path):
    returns = register_returns(path)
    if returns is None:
        pytest.skip(f"{path.stem} has no top-level register()")
    if not returns:
        pytest.skip(f"{path.stem}'s register() returns no list literal")

    for returned in returns:
        for element in returned.elts:
            assert isinstance(element, ast.Tuple), (
                f"{path.stem}.register() returns {ast.unparse(element)!r}, not a "
                f"(name, func) tuple. register_all() unpacks these as pairs; a bare "
                f"value raises 'cannot unpack non-iterable ...' which register_all "
                f"swallows, dropping the whole facade from the re-export surface "
                f"with only a stderr line to show for it."
            )
            assert len(element.elts) == 2, (
                f"{path.stem}.register() returns a {len(element.elts)}-tuple; "
                f"register_all() unpacks exactly two values"
            )
            name = element.elts[0]
            assert isinstance(name, ast.Constant) and isinstance(name.value, str), (
                f"{path.stem}.register() returns a tuple whose first element is "
                f"{ast.unparse(name)!r}; it must be a literal tool name string"
            )


def test_at_least_one_facade_was_actually_checked():
    """Guard against the discovery globs silently matching nothing."""
    checked = [p for p in facade_modules() if register_returns(p)]
    assert len(checked) >= 10, (
        f"only {len(checked)} facades had an inspectable register(); the discovery "
        f"in this test has probably drifted from the package layout"
    )
