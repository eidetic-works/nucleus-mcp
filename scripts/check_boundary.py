#!/usr/bin/env python3
"""Core/periphery architectural boundary checker (ADR-0043 W1).

Stdlib ``ast`` only — no third-party dependencies, no import of the package
under test. Given the checked-in core module list (``core_modules.json``,
transcribed from the module X-ray audit), it enforces two rules over the
``mcp_server_nucleus`` source tree:

  1. HARD-FAIL on any *eager* (module-level) import from a core module to a
     periphery module. The eager import-time core has zero periphery
     dependencies; that invariant is load-bearing for a physical carve and
     must never regress. Any such edge fails the check with its file:line.

  2. Count every *lazy* (function-local) core->periphery import and compare the
     per-module-pair site totals against the checked-in ledger
     (``boundary_ledger.json``). The ledger is a ratchet: growth beyond a
     pair's allowance — or a brand-new crossing pair — fails with the offending
     file:line. Shrinkage passes and prints a suggested ledger update so the
     ratchet can be tightened.

Usage::

    python scripts/check_boundary.py             # enforce (exit 1 on violation)
    python scripts/check_boundary.py --generate   # rewrite the ledger from the tree

The checker resolves its source root relative to its own location, so it runs
from any working directory and never hard-codes a checkout path.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

PACKAGE = "mcp_server_nucleus"

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_ROOT = SCRIPT_DIR.parent / "src"
PKG_ROOT = SRC_ROOT / PACKAGE
CORE_LIST_PATH = SCRIPT_DIR / "core_modules.json"
LEDGER_PATH = SCRIPT_DIR / "boundary_ledger.json"


def module_name_for_path(path: Path) -> str:
    """Dotted module name for a .py file under SRC_ROOT (packages drop __init__)."""
    rel = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def discover_package_modules() -> set[str]:
    """Every importable dotted module/package name inside the package tree."""
    modules: set[str] = set()
    for py in PKG_ROOT.rglob("*.py"):
        name = module_name_for_path(py)
        if name:
            modules.add(name)
    return modules


def load_core_modules() -> set[str]:
    data = json.loads(CORE_LIST_PATH.read_text(encoding="utf-8"))
    return set(data["core_modules"])


def _package_of(module: str, is_pkg: bool) -> str:
    if is_pkg:
        return module
    return module.rsplit(".", 1)[0] if "." in module else ""


def _relative_anchor(module: str, is_pkg: bool, level: int) -> str:
    base = _package_of(module, is_pkg)
    for _ in range(level - 1):
        base = base.rsplit(".", 1)[0] if "." in base else ""
    return base


def _resolve_targets(
    node: ast.AST,
    current_module: str,
    is_pkg: bool,
    package_modules: set[str],
) -> set[str]:
    """In-package dotted module targets referenced by one import statement.

    Deduped per statement, so one ``from X import a, b`` is a single edge to X
    (matching the audit's file:line site granularity).
    """
    targets: set[str] = set()

    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.name
            if name in package_modules:
                targets.add(name)
        return targets

    if isinstance(node, ast.ImportFrom):
        if node.level == 0:
            base = node.module or ""
        else:
            anchor = _relative_anchor(current_module, is_pkg, node.level)
            if node.module:
                base = f"{anchor}.{node.module}" if anchor else node.module
            else:
                base = anchor
        # Each imported name may itself be a submodule (from . import submod);
        # otherwise it is a symbol and the edge lands on `base`.
        for alias in node.names:
            candidate = f"{base}.{alias.name}" if base else alias.name
            if candidate in package_modules:
                targets.add(candidate)
            elif base in package_modules:
                targets.add(base)
        return targets

    return targets


def _collect_imports(tree: ast.AST) -> list[tuple[ast.AST, bool]]:
    """(import_node, is_lazy) for every import; lazy == has a function ancestor."""
    found: list[tuple[ast.AST, bool]] = []

    def walk(node: ast.AST, in_func: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                found.append((child, in_func))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, True)
            else:
                walk(child, in_func)

    walk(tree, False)
    return found


def scan() -> tuple[list[str], dict[str, list[int]]]:
    """Scan the core modules.

    Returns (eager_violations, lazy_edges) where eager_violations is a list of
    "core -> periphery  (file:line)" strings and lazy_edges maps
    "core -> periphery" to the sorted list of "relpath:line" sites.
    """
    package_modules = discover_package_modules()
    core = load_core_modules()

    missing = sorted(core - package_modules)
    if missing:
        raise SystemExit(
            "core_modules.json lists modules not found in the tree:\n  "
            + "\n  ".join(missing)
        )

    eager_violations: list[str] = []
    lazy_edges: dict[str, list[str]] = {}

    for module in sorted(core):
        rel = module[len(PACKAGE) + 1 :].replace(".", "/") if module != PACKAGE else ""
        pkg_init = (PKG_ROOT / rel / "__init__.py") if rel else (PKG_ROOT / "__init__.py")
        mod_file = (PKG_ROOT / (rel + ".py")) if rel else None
        if pkg_init.exists():
            path, is_pkg = pkg_init, True
        elif mod_file and mod_file.exists():
            path, is_pkg = mod_file, False
        else:  # pragma: no cover - guarded by the missing-modules check above
            continue

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        relpath = path.relative_to(SRC_ROOT).as_posix()

        for node, is_lazy in _collect_imports(tree):
            targets = _resolve_targets(node, module, is_pkg, package_modules)
            for target in targets:
                if target == module or target in core:
                    continue  # core->core is fine
                # target is an in-package module outside the core set == periphery
                pair = f"{module} -> {target}"
                site = f"{relpath}:{node.lineno}"
                if is_lazy:
                    lazy_edges.setdefault(pair, []).append(site)
                else:
                    eager_violations.append(f"{pair}  ({site})")

    for pair in lazy_edges:
        lazy_edges[pair].sort()
    return eager_violations, lazy_edges


def _ledger_from_edges(lazy_edges: dict[str, list[str]]) -> dict:
    counts = {pair: len(sites) for pair, sites in sorted(lazy_edges.items())}
    return {
        "_comment": (
            "Ratchet ledger for lazy (function-local) core->periphery imports "
            "(ADR-0043 W1). Each entry is a module pair mapped to the allowed "
            "number of import sites. check_boundary.py fails if any pair grows "
            "beyond its allowance or a new pair appears. Regenerate with "
            "`python scripts/check_boundary.py --generate` only to RATCHET DOWN."
        ),
        "total_lazy_edges": sum(counts.values()),
        "edges": counts,
    }


def generate() -> int:
    eager_violations, lazy_edges = scan()
    ledger = _ledger_from_edges(lazy_edges)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {LEDGER_PATH.name}: {len(ledger['edges'])} pairs, "
        f"{ledger['total_lazy_edges']} lazy edges."
    )
    if eager_violations:
        print(
            f"WARNING: {len(eager_violations)} eager core->periphery edge(s) exist; "
            "the ledger does not sanction these — enforcement will still fail."
        )
    return 0


def enforce() -> int:
    eager_violations, lazy_edges = scan()
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    allowed: dict[str, int] = ledger.get("edges", {})

    failed = False

    if eager_violations:
        failed = True
        print("EAGER core->periphery imports are forbidden (hard fail):")
        for v in sorted(eager_violations):
            print(f"  {v}")

    growth: list[str] = []
    for pair, sites in sorted(lazy_edges.items()):
        cap = allowed.get(pair, 0)
        if len(sites) > cap:
            # Report the sites beyond the ledger allowance.
            for site in sites[cap:]:
                growth.append(f"  {pair}  ({site})  [ledger allows {cap}]")
    if growth:
        failed = True
        print("LAZY core->periphery edges exceed the ratchet ledger (grow = fail):")
        for line in growth:
            print(line)

    current = {pair: len(sites) for pair, sites in lazy_edges.items()}
    total_current = sum(current.values())
    total_allowed = sum(allowed.values())

    if failed:
        print(
            f"\nBOUNDARY CHECK FAILED. lazy edges: {total_current} "
            f"(ledger caps {total_allowed}); eager violations: {len(eager_violations)}."
        )
        return 1

    # Passing. Detect slack so the ratchet can be tightened.
    shrunk = [
        pair for pair, cap in allowed.items() if current.get(pair, 0) < cap
    ]
    if shrunk or total_current < total_allowed:
        print(
            "BOUNDARY CHECK PASSED with slack — the boundary shrank; "
            "tighten the ratchet with `python scripts/check_boundary.py --generate`."
        )
        for pair in sorted(shrunk):
            print(f"  shrank: {pair}  {allowed[pair]} -> {current.get(pair, 0)}")
    else:
        print(
            f"BOUNDARY CHECK PASSED. 0 eager core->periphery edges; "
            f"{total_current} lazy edges at the ledger cap ({total_allowed})."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Rewrite the ledger from the current tree (ratchet-down only).",
    )
    args = parser.parse_args(argv)
    if not PKG_ROOT.is_dir():
        raise SystemExit(f"package source not found at {PKG_ROOT}")
    return generate() if args.generate else enforce()


if __name__ == "__main__":
    sys.exit(main())
