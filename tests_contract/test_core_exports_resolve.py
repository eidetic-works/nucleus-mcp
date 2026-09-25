"""Everything `core/__init__.py` exports must actually work when called (CN-4).

`core/orchestrator.py::get_orchestrator` did
`from .orchestrator_unified import get_orchestrator` — relative, so it resolved
to `mcp_server_nucleus.core.orchestrator_unified`, which does not exist. There is
only `runtime/orchestrator_unified.py`.

The import sits inside the function, so the module imported cleanly and the
package re-exported the name without complaint. It raised `ModuleNotFoundError`
the first time anybody called it. Nothing in this mirror calls it, which is why
it survived — and why a test that only imports the package would not have caught
it either.

So these tests check the import *target*, statically, rather than calling
through. Calling would need the full orchestrator dependency tree, which is not
installable in every checkout, and a test that skips on a missing dependency
would have skipped straight past this bug.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

CORE = SRC / "mcp_server_nucleus" / "core"

pytestmark = pytest.mark.skipif(not CORE.is_dir(), reason="core package not in this export")


def _relative_import_targets(path: Path):
    """Every `from ..x.y import z` in the file, resolved to a module name.

    Yields (module_name, lineno). `level` is the number of leading dots, which
    is exactly what got this wrong: one dot meant `core.`, two means the package
    above it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = "mcp_server_nucleus.core"
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        parts = package.split(".")
        # level 1 == this package; each extra dot climbs one more.
        base = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
        target = ".".join(base + ([node.module] if node.module else []))
        yield target, node.lineno


CORE_MODULES = sorted(p for p in CORE.glob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("path", CORE_MODULES, ids=lambda p: p.name)
def test_every_relative_import_in_core_resolves_to_a_real_module(path):
    unresolved = [
        (target, lineno)
        for target, lineno in _relative_import_targets(path)
        if importlib.util.find_spec(target) is None
    ]
    assert not unresolved, (
        f"{path.name} imports modules that do not exist: {unresolved}. An import "
        "inside a function body does not fail until the function is called, so "
        "this is invisible to anything that only imports the package."
    )


def test_the_orchestrator_wrapper_points_at_the_runtime_module():
    """The specific bug, pinned by name."""
    targets = [t for t, _ in _relative_import_targets(CORE / "orchestrator.py")]
    assert "mcp_server_nucleus.runtime.orchestrator_unified" in targets
    assert "mcp_server_nucleus.core.orchestrator_unified" not in targets


def test_the_wrapper_still_threads_brain_path_through():
    """Dropping it would reintroduce the process-wide singleton TN-3 removed."""
    tree = ast.parse((CORE / "orchestrator.py").read_text(encoding="utf-8"))
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "get_orchestrator"
    )
    assert [a.arg for a in fn.args.args] == ["brain_path"], (
        "the wrapper no longer accepts brain_path, so every caller through it "
        "shares one orchestrator again"
    )
    body = ast.unparse(fn)
    assert "brain_path" in body.split("return", 1)[-1], (
        "brain_path is accepted but not passed on, which is worse than not "
        "accepting it: the caller believes it selected a brain"
    )


def test_what_the_core_package_exports_is_importable():
    """Import-time breakage, as opposed to the call-time kind above."""
    tree = ast.parse((CORE / "__init__.py").read_text(encoding="utf-8"))
    for target, lineno in _relative_import_targets(CORE / "__init__.py"):
        assert importlib.util.find_spec(target) is not None, (
            f"core/__init__.py:{lineno} re-exports from {target}, which does not exist"
        )
