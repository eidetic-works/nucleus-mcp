"""``nucleus prove --diff`` — which symbols you just changed were actually executed?

THE GAP THIS CLOSES. Linters prove code parses. Type checkers prove it types.
Coverage reports a file-level percentage. None of them prove a given function
*ran*. Measured on this repo: 58.7% of product functions in files the suite
touches were never executed by any of its 2,705 passing tests, and 16.8% of
tests executed zero product lines. The suite was green throughout.

WHY DIFF-SCOPED. A repo-wide list of never-executed symbols is 2,124 rows —
wallpaper. Nobody acts on it, the same way nobody has acted on coverage's
"Missing" column for thirty years. Scoped to the diff it becomes a fact with
one obvious response, delivered while the code is still cheap to change:
"the 3 functions you just added were executed by nothing, including the test
you just wrote for them."

WHY IT IS NOT A DEAD-CODE FINDER. vulture and friends are AST-only: on this
package vulture found 339 unused functions against runtime's 1,645
never-executed, overlapping on just 146 — and 57% of its function findings
named symbols that DID execute. Static analysis guesses; this reads execution
facts out of a coverage database that already exists on disk.

NO COVERAGE DATA => INSUFFICIENT, never a pass. Absence of evidence is the
third state, and reporting it as success is the exact defect this whole module
family exists to prevent.
"""

from __future__ import annotations

import ast
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("nucleus.prove")

# Symbols smaller than this are usually one-line accessors, __repr__, or
# trivial passthroughs. Flagging them creates noise that trains people to
# ignore the whole report, which costs more than the misses.
_MIN_BODY_LINES = 3


@dataclass
class Symbol:
    """A function or class in the diff, with the line span used to test it."""

    file: str
    name: str
    kind: str
    lineno: int
    end_lineno: int
    executed_lines: int = 0

    @property
    def body_lines(self) -> int:
        """Total line span INCLUDING the def/class line.

        Span, not end-minus-start: a 3-line function spans 3 lines, and the
        off-by-one made the default threshold silently exclude every small
        real function — which would have made this tool quietly report
        INSUFFICIENT on diffs it should have judged.
        """
        return max(0, self.end_lineno - self.lineno + 1)

    @property
    def executed(self) -> bool:
        return self.executed_lines > 0


@dataclass
class ProveResult:
    """Outcome of a diff-scoped execution check."""

    verdict: str                      # PROVEN | REFUTED | INSUFFICIENT
    reason: str
    changed_files: List[str]
    symbols: List[Symbol]
    never_executed: List[Symbol]
    coverage_source: str = ""
    # Symbols in files coverage never instrumented. Tracked separately and
    # NEVER merged into never_executed — "not measured" and "did not run" are
    # different facts, and conflating them is the defect this tool targets.
    unmeasured: List[Symbol] = field(default_factory=list)

    @property
    def checked(self) -> int:
        return len(self.symbols)


def _git(args: List[str], repo: Path) -> str:
    """Run a git command; empty string on any failure. Never raises."""
    try:
        out = subprocess.run(
            ["git"] + args, cwd=str(repo), capture_output=True,
            text=True, timeout=15,
        )
        return out.stdout if out.returncode == 0 else ""
    except Exception as exc:  # noqa: BLE001
        logger.debug("git %s failed: %s", " ".join(args), exc)
        return ""


def repo_root(start: Optional[Path] = None) -> Path:
    """Repo root via git — the frame git's own path output uses.

    Not ``Path.cwd()``: git reports paths relative to the repository root
    regardless of the working directory, so using cwd silently resolves every
    changed file to a path that does not exist when run from a subdirectory.
    That exact bug made all four verify tiers report SKIPPED (fixed a86adbaf).
    """
    base = start or Path.cwd()
    top = _git(["rev-parse", "--show-toplevel"], base).strip()
    return Path(top) if top else base


def changed_python_files(repo: Path, base: Optional[str] = None) -> List[str]:
    """Changed .py files: working tree + staged, or a diff against *base*."""
    seen: List[str] = []
    ranges = [
        ["diff", "--name-only"],
        ["diff", "--name-only", "--cached"],
        # UNTRACKED FILES MATTER MOST. A brand-new module with no caller yet is
        # the single likeliest thing to be executed by nothing — and `git diff`
        # never lists it. Omitting this made `prove` blind to prove.py itself
        # on its first run, which is precisely the class of miss it exists to
        # catch.
        ["ls-files", "--others", "--exclude-standard"],
    ]
    if base:
        ranges.append(["diff", "--name-only", f"{base}...HEAD"])
    for args in ranges:
        for line in _git(args, repo).splitlines():
            line = line.strip()
            if line.endswith(".py") and line not in seen:
                seen.append(line)
    return seen


def extract_symbols(repo: Path, relpaths: List[str]) -> List[Symbol]:
    """AST symbols (functions, methods, classes) with their line extents."""
    syms: List[Symbol] = []
    for rel in relpaths:
        p = repo / rel
        if not p.exists():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — unparseable file is not our error to raise
            logger.debug("skip unparseable %s: %s", rel, exc)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                syms.append(Symbol(file=rel, name=node.name, kind=kind,
                                   lineno=node.lineno, end_lineno=end))
    return syms


def load_executed_lines(coverage_file: Path) -> Tuple[Dict[str, Set[int]], str]:
    """Read executed lines per file from a coverage database.

    Returns ``({abs_path: {line, ...}}, source_description)``. An empty mapping
    means no usable data — the caller must render that as INSUFFICIENT, never
    as a pass.
    """
    try:
        from coverage import CoverageData
    except ImportError:
        return {}, "coverage not installed"
    if not coverage_file.exists():
        return {}, f"no coverage data at {coverage_file}"
    try:
        data = CoverageData(basename=str(coverage_file))
        data.read()
        out: Dict[str, Set[int]] = {}
        for fname in data.measured_files():
            out[fname] = set(data.lines(fname) or [])
        return out, str(coverage_file)
    except Exception as exc:  # noqa: BLE001
        logger.warning("coverage read failed: %s", exc)
        return {}, f"unreadable coverage data: {exc}"


def prove_diff(repo: Optional[Path] = None, base: Optional[str] = None,
               coverage_file: Optional[Path] = None,
               min_body_lines: int = _MIN_BODY_LINES) -> ProveResult:
    """Check which symbols in the current diff were executed by anything."""
    repo = repo or repo_root()
    # coverage.py writes .coverage to the CWD of the test run, which in a
    # monorepo is usually the package directory, not the git root. Check both
    # rather than reporting INSUFFICIENT next to a perfectly good database.
    if coverage_file is not None:
        cov_path = coverage_file
    else:
        candidates = [Path.cwd() / ".coverage", repo / ".coverage"]
        cov_path = next((c for c in candidates if c.exists()), candidates[-1])

    files = changed_python_files(repo, base)
    if not files:
        # No changed Python files is not a pass — there was nothing to prove.
        return ProveResult("INSUFFICIENT", "no changed Python files to check",
                           [], [], [])

    symbols = [s for s in extract_symbols(repo, files)
               if s.body_lines >= min_body_lines]
    if not symbols:
        return ProveResult("INSUFFICIENT",
                           f"no symbols of >={min_body_lines} lines in {len(files)} changed file(s)",
                           files, [], [])

    executed, source = load_executed_lines(cov_path)
    if not executed:
        # THE load-bearing branch. Without execution data nothing is known, and
        # "unknown" must not render as "fine".
        return ProveResult(
            "INSUFFICIENT",
            f"{source} — run your suite under coverage first "
            f"(e.g. `coverage run -m pytest`), then re-run",
            files, symbols, [], coverage_source=source,
        )

    # Coverage keys are absolute; diff paths are repo-relative.
    by_rel: Dict[str, Set[int]] = {}
    for abs_path, lines in executed.items():
        try:
            by_rel[str(Path(abs_path).resolve().relative_to(repo.resolve()))] = lines
        except Exception:  # noqa: BLE001 — file outside the repo (site-packages etc.)
            continue

    # UNMEASURED IS NOT NEVER-EXECUTED. If coverage never instrumented a file
    # at all — outside --source, a different run, a new file added after the
    # run — then nothing is known about its symbols. Reporting those as
    # "executed by nothing" would be a false accusation of exactly the kind
    # this tool exists to prevent, and it is how prove's own first real run
    # flagged 191/191 including tests that had demonstrably just run.
    measured_files = {f for f in by_rel}
    measured = [s for s in symbols if s.file in measured_files]
    unmeasured = [s for s in symbols if s.file not in measured_files]

    for s in measured:
        hit = by_rel.get(s.file, set())
        s.executed_lines = sum(1 for ln in hit if s.lineno <= ln <= s.end_lineno)

    never = [s for s in measured if not s.executed]

    if not measured:
        return ProveResult(
            "INSUFFICIENT",
            f"none of the {len(files)} changed file(s) were measured by this "
            f"coverage run — widen --source or re-run the suite over them",
            files, symbols, [], coverage_source=source, unmeasured=unmeasured)

    if never:
        note = (f"{len(never)} of {len(measured)} measured symbol(s) executed by nothing")
        if unmeasured:
            note += f"; {len(unmeasured)} more unmeasured (not counted)"
        return ProveResult("REFUTED", note, files, symbols, never,
                           coverage_source=source, unmeasured=unmeasured)

    if unmeasured:
        # Everything measured ran, but coverage did not see every changed file.
        # That is not a clean pass — say so rather than rounding up.
        return ProveResult(
            "INSUFFICIENT",
            f"all {len(measured)} measured symbol(s) ran, but {len(unmeasured)} "
            f"changed symbol(s) were never measured",
            files, symbols, [], coverage_source=source, unmeasured=unmeasured)

    return ProveResult("PROVEN",
                       f"all {len(measured)} changed symbol(s) were executed",
                       files, symbols, [], coverage_source=source)


def format_result(r: ProveResult) -> str:
    """Human-readable verdict. Never renders INSUFFICIENT as a pass."""
    out: List[str] = []
    bar = "─" * 68
    out.append(bar)
    out.append("  NUCLEUS PROVE — did the code you changed actually run?")
    out.append(bar)
    out.append(f"  CHANGED FILES : {len(r.changed_files)}")
    out.append(f"  SYMBOLS       : {r.checked} checked")
    if r.coverage_source:
        out.append(f"  EVIDENCE      : {r.coverage_source}")
    if r.unmeasured:
        out.append(f"  UNMEASURED    : {len(r.unmeasured)} symbol(s) in files coverage never saw")
    if r.never_executed:
        out.append("")
        out.append("  EXECUTED BY NOTHING:")
        for s in r.never_executed:
            out.append(f"    {s.file}:{s.lineno}  {s.kind} {s.name}  ({s.body_lines} lines)")
    out.append("")
    out.append(f"  VERDICT       : {r.verdict} — {r.reason}")
    out.append(bar)
    return "\n".join(out)


def emit_receipt(r: ProveResult) -> None:
    """Record the result in the claim corpus. Best-effort; never raises."""
    try:
        from .receipt import ClaimType, Receipt, Verdict, record

        record(Receipt(
            claim_type=ClaimType.CODE_EXECUTED,
            claim="changed symbols were executed by the test suite",
            verdict=getattr(Verdict, r.verdict),
            primitive="coverage database ∩ AST symbol extents over git diff",
            claimed="changed code is covered",
            # Report measured/executed/unmeasured SEPARATELY. The obvious
            # formulation — checked minus never_executed — silently counts
            # unmeasured symbols as executed, which is the very conflation
            # this command exists to prevent, reproduced in its own receipt.
            observed=(f"{len([x for x in r.symbols if x.executed])} executed, "
                      f"{len(r.never_executed)} never executed, "
                      f"{len(r.unmeasured)} unmeasured (of {r.checked} changed)"),
            source="nucleus_prove",
            evidence=r.coverage_source,
            reason=r.reason,
            tags=["prove", "diff"],
        ))
    except Exception as exc:  # noqa: BLE001
        logger.debug("prove receipt skipped: %s", exc)
