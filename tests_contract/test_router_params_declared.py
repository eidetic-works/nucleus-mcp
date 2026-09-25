"""Every ROUTER handler that absorbs **params must declare its contract (DS-6).

`_dispatch._allowed_param_names` reads a handler's signature to decide which
keys are legal. A handler written as `def _h_x(**params)` hides that contract, so
those must publish it as `_nucleus_params`. When one does not,
`_allowed_param_names` returns None and `_reject_unknown` **skips the check
entirely** — a caller's misspelled key is silently dropped instead of rejected,
on that action alone.

That is exactly what happened to `plan_review_chief_amend`: it was added to a
ROUTER of six, each of which had a declaration, and it did not get one. The
comment immediately above still said "All six handlers". Nothing failed; the
action simply had no parameter validation while its six siblings did.

The failure mode is why this test is structural rather than per-module: the
defect is an omission, and an omission does not announce itself.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

TOOLS = SRC / "mcp_server_nucleus" / "tools"

pytestmark = pytest.mark.skipif(not TOOLS.is_dir(), reason="tools package not in this export")


def _router_handlers(tree):
    """Handler names referenced as ROUTER values, per module."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "ROUTER" for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            action = key.value if isinstance(key, ast.Constant) else None
            name = getattr(value, "id", None)
            if action and name:
                yield action, name


def _absorbs_kwargs(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node.args.kwarg is not None
    return None  # not defined in this module


def _declares_params(tree, name):
    """True if `<name>._nucleus_params = ...` appears anywhere in the module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute)
                        and target.attr == "_nucleus_params"
                        and getattr(target.value, "id", None) == name):
                    return True
    return False


MODULES = sorted(p for p in TOOLS.glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.stem)
def test_kwargs_handlers_declare_their_parameter_contract(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    undeclared = [
        (action, name)
        for action, name in _router_handlers(tree)
        if _absorbs_kwargs(tree, name) is True and not _declares_params(tree, name)
    ]
    assert not undeclared, (
        f"{path.name}: these ROUTER handlers absorb **params but publish no "
        f"_nucleus_params: {undeclared}. _dispatch will skip the unknown-param "
        "check for them, so a caller's misspelled key is silently dropped rather "
        "than rejected — and nothing fails to tell you."
    )


def test_the_action_that_was_missed_is_declared():
    """Pinned by name, since it is the one that proved the gap is reachable."""
    path = TOOLS / "vendor_delegate.py"
    if not path.exists():
        pytest.skip("vendor_delegate not in this export")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    handlers = dict(_router_handlers(tree))
    assert "plan_review_chief_amend" in handlers
    assert _declares_params(tree, handlers["plan_review_chief_amend"])


def test_dispatch_still_skips_loudly_when_a_contract_is_missing():
    """The skip must keep logging; it is the only signal such a gap gives."""
    dispatch = TOOLS / "_dispatch.py"
    if not dispatch.exists():
        pytest.skip("_dispatch not in this export")
    source = dispatch.read_text(encoding="utf-8")
    assert "unknown-param check SKIPPED" in source, (
        "the skip path no longer logs, so an undeclared handler is now entirely "
        "silent rather than merely quiet"
    )
