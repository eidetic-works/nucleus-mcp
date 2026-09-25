"""Empty-fixture smoke detector — mechanization of feedback_smoke_tests_need_realistic_load.

Treatment sweep #008 of the operator-framed program. Static AST scan for
the patterns sweep #002b empirically identified as zero-behavioral-signal
test shapes. These tests pass trivially because the assertion can be
satisfied by an empty / mocked / stub'd input that doesn't exercise the
real code path.

The fleet has burned on this once already: an empty-bucket smoke hid a
100x perf cliff before launch. The MEMORY.md rule says:

    feedback_smoke_tests_need_realistic_load: Daemon smoke tests need
    representative-load case BEFORE ship-ready (empty-bucket pass hid 100x
    perf cliff). Gate/scrubber changes also replay against most recent
    REAL blocked batch.

This script catches the static-detectable subset pre-merge.

Patterns (subset of sweep #002b taxonomy that AST can see):

  A. Empty-fixture tautology:
       result = f([])
       assert result == []
     OR:
       items = []
       assert len(items) == 0

  B. Stub-return-string tautology (matches synthesized_batch_3/6 shape
     that sweep #005 deleted):
       assert handle_foo() == 'handle_foo executed'
       assert handle_bar() == 'handle_bar executed'

  C. Module-existence-only tests:
       assert hasattr(module, 'function_name')
     with no behavioral follow-up in the same test function.

CLI:
    python scripts/empty_fixture_smoke_detector.py [--tests-dir DIR] [--json]
    Exit 0 = no candidates detected
    Exit 1 = candidates found (CI gate fails)
    Exit 2 = scan error (e.g. unparseable test file — flag, don't fail)
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterable


def _is_empty_literal(node: ast.AST) -> bool:
    """[] or {} or () or '' or 0."""
    if isinstance(node, ast.List) and not node.elts:
        return True
    if isinstance(node, ast.Dict) and not node.keys:
        return True
    if isinstance(node, ast.Tuple) and not node.elts:
        return True
    if isinstance(node, ast.Constant) and node.value in ("", 0):
        return True
    return False


def _has_substantive_assertion(test_body: list[ast.stmt]) -> bool:
    """Heuristic: a test function body has at least one assert with a
    non-literal RHS or a comparison that isn't just identity-with-stub."""
    for stmt in test_body:
        if isinstance(stmt, ast.Assert):
            t = stmt.test
            if isinstance(t, ast.Compare) and t.comparators and not all(
                isinstance(c, (ast.Constant, ast.List, ast.Dict, ast.Tuple, ast.Name))
                for c in t.comparators
            ):
                return True
    return False


def _name_appears_in(name: str, node: ast.AST) -> bool:
    """Conservative: any Name(id=name) anywhere in this node's subtree counts
    as a possible mutation/observation. Better to under-flag than over-flag a
    substantive test that uses the accumulator idiom (peer crack #1, 2026-06-11)."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == name:
            return True
    return False


def _scan_function_for_patterns(fn: ast.FunctionDef) -> list[dict]:
    """Return list of {pattern, lineno, snippet} for findings in this fn."""
    findings: list[dict] = []
    body = fn.body

    # Pattern A: empty-fixture tautology — name assigned to empty collection,
    # NO other reference to that name between the assignment and the assertion,
    # then asserted equal to an empty collection.
    #
    # The "no intervening reference" rule fixes peer crack #1: the accumulator
    # idiom (e.g. `corruptions = []; reader threads .append(); assert
    # corruptions == []`) is a SUBSTANTIVE race-test pattern; reader thread
    # bodies inside nested defs reference `corruptions` between the assignment
    # and the assertion. Conservative AST walk catches both .append() mutations
    # AND closures that capture the name — invalidating in both cases.
    last_assigned_empty: dict[str, int] = {}  # name -> stmt index of assignment
    for i, stmt in enumerate(body):
        # Track empty assignments.
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and _is_empty_literal(stmt.value):
                    last_assigned_empty[t.id] = i
                elif isinstance(t, ast.Name) and t.id in last_assigned_empty:
                    # Reassignment to something non-empty invalidates.
                    del last_assigned_empty[t.id]

        # Walk for assertions, invalidate any name that's been mutated/closed-over
        # in non-assert statements between its assignment and this stmt.
        if isinstance(stmt, ast.Assert):
            # Invalidate any name referenced in body[assigned_index+1 : i] (any
            # node other than Assign and Assert), including nested function defs.
            for name, assigned_idx in list(last_assigned_empty.items()):
                for j in range(assigned_idx + 1, i):
                    if _name_appears_in(name, body[j]):
                        del last_assigned_empty[name]
                        break

            test = stmt.test
            if isinstance(test, ast.Compare) and test.ops and isinstance(test.ops[0], ast.Eq):
                left = test.left
                right = test.comparators[0] if test.comparators else None
                if (
                    isinstance(left, ast.Name)
                    and left.id in last_assigned_empty
                    and right is not None
                    and _is_empty_literal(right)
                ):
                    findings.append({
                        "pattern": "A",
                        "lineno": stmt.lineno,
                        "snippet": f"assert {left.id} == <empty> (from empty fixture)",
                    })

    # Pattern B: stub-return-string tautology — assertion that a call
    # returns f"{call_name} executed".
    for stmt in body:
        if isinstance(stmt, ast.Assert):
            test = stmt.test
            if (
                isinstance(test, ast.Compare)
                and test.ops
                and isinstance(test.ops[0], ast.Eq)
                and isinstance(test.left, ast.Call)
                and isinstance(test.left.func, ast.Name)
                and test.comparators
                and isinstance(test.comparators[0], ast.Constant)
                and isinstance(test.comparators[0].value, str)
            ):
                call_name = test.left.func.id
                expected = test.comparators[0].value
                if re.fullmatch(rf"{re.escape(call_name)}[ _]executed", expected):
                    findings.append({
                        "pattern": "B",
                        "lineno": stmt.lineno,
                        "snippet": f"assert {call_name}() == '{expected}' (stub-string tautology)",
                    })

    # Pattern C: function body is ONLY hasattr checks — no behavioral assertion.
    if body and not _has_substantive_assertion(body):
        hasattr_count = 0
        for stmt in body:
            if isinstance(stmt, ast.Assert) and isinstance(stmt.test, ast.Call):
                func = stmt.test.func
                if isinstance(func, ast.Name) and func.id == "hasattr":
                    hasattr_count += 1
        if hasattr_count and hasattr_count == len(
            [s for s in body if isinstance(s, ast.Assert)]
        ):
            findings.append({
                "pattern": "C",
                "lineno": fn.lineno,
                "snippet": f"function body has only hasattr() assertions ({hasattr_count})",
            })

    return findings


def scan_file(path: Path) -> list[dict] | None:
    """Scan a single test file. Returns list of findings (may be empty) on
    success, OR None on parse failure (peer crack #2, 2026-06-11: silent
    skip is a hole a regressing file can hide in — propagate as scan error
    so main() can exit 2 per the documented contract)."""
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return None

    findings: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            for f in _scan_function_for_patterns(node):
                f["file"] = str(path)
                f["function"] = node.name
                findings.append(f)
    return findings


def scan_tree(tests_root: Path) -> tuple[list[dict], list[str]]:
    """Scan every test_*.py under tests_root recursively.

    Returns (findings, parse_failures) — parse_failures is the list of file
    paths that couldn't be parsed. main() exits 2 if any.
    """
    findings: list[dict] = []
    parse_failures: list[str] = []
    for p in tests_root.rglob("test_*.py"):
        # Skip pycache, .claude/worktrees/ scratch trees.
        s = str(p)
        if "__pycache__" in s or "/.claude/worktrees/" in s or "/scratch/" in s:
            continue
        result = scan_file(p)
        if result is None:
            parse_failures.append(str(p))
        else:
            findings.extend(result)
    return findings, parse_failures


def _default_tests_dir() -> Path:
    """Resolve mcp-server-nucleus/tests/ relative to this script."""
    return Path(__file__).parent.parent / "tests"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tests-dir",
        default=None,
        help=f"directory to scan (default: {_default_tests_dir()})",
    )
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--allow-findings",
        action="store_true",
        help="exit 0 even if candidates found; print report only (default: exit 1 on findings)",
    )
    args = ap.parse_args(argv)

    tests_dir = Path(args.tests_dir) if args.tests_dir else _default_tests_dir()
    if not tests_dir.exists():
        print(f"[empty-fixture-detector] FATAL: tests dir not found: {tests_dir}", file=sys.stderr)
        return 2

    findings, parse_failures = scan_tree(tests_dir)

    if args.json:
        print(json.dumps({
            "findings": findings,
            "count": len(findings),
            "parse_failures": parse_failures,
        }))
    else:
        if findings:
            print(f"[empty-fixture-detector] {len(findings)} candidate(s) detected:", file=sys.stderr)
            for f in findings:
                print(f"  {f['file']}:{f['lineno']} [{f['pattern']}] {f['function']} -- {f['snippet']}", file=sys.stderr)
        else:
            print("[empty-fixture-detector] no candidates detected.", file=sys.stderr)
        if parse_failures:
            print(f"[empty-fixture-detector] {len(parse_failures)} file(s) could not be parsed:", file=sys.stderr)
            for p in parse_failures:
                print(f"  {p}", file=sys.stderr)

    # Peer crack #2: parse failures exit 2 per the documented contract — a
    # silent skip is a hole a regressing file can hide in.
    if parse_failures:
        return 2

    if findings and not args.allow_findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
