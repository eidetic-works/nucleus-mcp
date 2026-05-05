#!/usr/bin/env python3
"""Codemod: migrate test assertions for the envelope flip.

Context:
  v1.2.0 ships envelope wrapping OFF by default (NUCLEUS_ENVELOPE=off).
  When the default flips ON (v1.3+), every test that parses a dispatch
  result with `json.loads(result)` and compares to a raw dict will break
  because the result will be wrapped: {ok, data, brain_id, ...}.

This script:
  1. Scans `tests/` for assertion patterns that compare parsed dispatch
     output against raw dicts.
  2. Emits a candidate-migration report (dry-run, default).
  3. With --apply, rewrites those assertions to call
     `_envelope.unwrap(json.loads(result))` before comparison.

It is a best-effort AST scan. Run with --dry-run first; review the
report (tests/CODEMOD_DIFF.md) before applying.

Usage:
  python3 scripts/codemod_envelope_tests.py --dry-run
  python3 scripts/codemod_envelope_tests.py --apply
  python3 scripts/codemod_envelope_tests.py --apply --path tests/test_foo.py

Exit codes:
  0 — scan completed (dry-run or apply succeeded)
  1 — syntax error in a scanned file (halts run)
  2 — invalid CLI args
"""

from __future__ import annotations

import argparse
import ast
import difflib
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
DIFF_REPORT_PATH = TESTS_DIR / "CODEMOD_DIFF.md"


class Candidate(NamedTuple):
    file: Path
    lineno: int
    col: int
    source_line: str
    reason: str


# Heuristic targets — string patterns a human would grep for.
# We detect these in source text rather than via AST to keep the script
# maintainable. Candidates are then optionally rewritten.
_PATTERNS = [
    # json.loads(result) - suggests dispatch result parsing
    ("json.loads(result)", "parses dispatch result — candidate for unwrap()"),
    ("json.loads(response)", "parses dispatch response — candidate for unwrap()"),
    ("json.loads(output)", "parses dispatch output — candidate for unwrap()"),
    # dispatch(...) direct consumption
    ("dispatch(", "direct dispatch call — check if result is later compared raw"),
    ("async_dispatch(", "direct async_dispatch call — check consumers"),
]


def scan_file(path: Path) -> List[Candidate]:
    """Identify candidate lines in a test file."""
    candidates: List[Candidate] = []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return candidates

    # Syntax check — if a test file is broken, halt the run.
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as e:
        raise SystemExit(f"ERROR: {path}: {e}") from e

    for lineno, line in enumerate(source.splitlines(), start=1):
        for needle, reason in _PATTERNS:
            if needle in line and "unwrap" not in line:
                col = line.index(needle)
                candidates.append(
                    Candidate(
                        file=path,
                        lineno=lineno,
                        col=col,
                        source_line=line.rstrip("\n"),
                        reason=reason,
                    )
                )
    return candidates


def rewrite_line(line: str) -> Optional[str]:
    """Apply a best-effort rewrite.

    Strategy: wrap `json.loads(<x>)` with `_envelope.unwrap(...)`.
    Returns the new line, or None if no rewrite is applicable.
    """
    for needle in ("json.loads(result)", "json.loads(response)", "json.loads(output)"):
        if needle in line and "unwrap" not in line:
            return line.replace(
                needle,
                f"_envelope.unwrap({needle})",
            )
    return None


def apply_rewrites(path: Path) -> int:
    """Rewrite a file in-place. Returns number of lines changed."""
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    changed = 0

    # Ensure the import will exist at the top of the file.
    needs_import = any(
        rewrite_line(line) is not None for line in lines
    )
    if not needs_import:
        return 0

    new_lines: List[str] = []
    for line in lines:
        newline_suffix = "\n" if line.endswith("\n") else ""
        body = line.rstrip("\n")
        rewritten = rewrite_line(body)
        if rewritten is not None:
            new_lines.append(rewritten + newline_suffix)
            changed += 1
        else:
            new_lines.append(line)

    # Inject import if missing.
    joined = "".join(new_lines)
    import_stmt = "from mcp_server_nucleus.tools import _envelope\n"
    if import_stmt not in joined and "_envelope" in joined:
        # Insert after the last top-level import.
        insert_at = 0
        for i, line in enumerate(new_lines):
            s = line.lstrip()
            if s.startswith("import ") or s.startswith("from "):
                insert_at = i + 1
        new_lines.insert(insert_at, import_stmt)

    path.write_text("".join(new_lines), encoding="utf-8")
    return changed


def diff_report(candidates: List[Candidate], target: Path) -> None:
    """Write CODEMOD_DIFF.md summarizing dry-run findings."""
    lines: List[str] = []
    lines.append("# Envelope Codemod — Dry-Run Report")
    lines.append("")
    lines.append(
        "Generated by `scripts/codemod_envelope_tests.py`. Review candidates "
        "below before running with `--apply`."
    )
    lines.append("")
    lines.append(f"**Total candidates:** {len(candidates)}")
    lines.append("")
    by_file: dict[Path, List[Candidate]] = {}
    for c in candidates:
        by_file.setdefault(c.file, []).append(c)
    for file, cs in sorted(by_file.items()):
        rel = file.relative_to(REPO_ROOT)
        lines.append(f"## `{rel}`")
        lines.append("")
        for c in cs:
            lines.append(f"- **Line {c.lineno}** — {c.reason}")
            lines.append(f"  ```python")
            lines.append(f"  {c.source_line.strip()}")
            lines.append(f"  ```")
            suggested = rewrite_line(c.source_line)
            if suggested is not None:
                lines.append(f"  Suggested rewrite:")
                lines.append(f"  ```python")
                lines.append(f"  {suggested.strip()}")
                lines.append(f"  ```")
            lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", default=True, help="Scan and report (default)")
    parser.add_argument("--apply", action="store_true", help="Rewrite files in place")
    parser.add_argument("--path", type=Path, default=TESTS_DIR, help="File or directory to scan (default: tests/)")
    args = parser.parse_args()

    target_paths: List[Path] = []
    if args.path.is_dir():
        target_paths.extend(sorted(args.path.rglob("test_*.py")))
    elif args.path.is_file():
        target_paths.append(args.path)
    else:
        print(f"ERROR: path not found: {args.path}", file=sys.stderr)
        return 2

    all_candidates: List[Candidate] = []
    for p in target_paths:
        all_candidates.extend(scan_file(p))

    if args.apply:
        total_changed = 0
        changed_files = 0
        for p in target_paths:
            n = apply_rewrites(p)
            if n:
                total_changed += n
                changed_files += 1
                print(f"  rewrote {n} line(s) in {p.relative_to(REPO_ROOT)}")
        print(f"\nTotal: {total_changed} line(s) changed across {changed_files} file(s).")
        return 0

    diff_report(all_candidates, DIFF_REPORT_PATH)
    print(f"Scanned {len(target_paths)} test file(s).")
    print(f"Found {len(all_candidates)} candidate assertion(s).")
    print(f"Report written to: {DIFF_REPORT_PATH.relative_to(REPO_ROOT)}")
    print("\nRun with --apply to rewrite in place (review CODEMOD_DIFF.md first).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
