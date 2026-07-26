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
    # First line of the actual BODY, past the def/decorators and any docstring.
    # The `def` line itself executes at IMPORT time — binding the function
    # object — so a window starting at `lineno` reports every function in every
    # imported module as executed. That false negative made a planted dead
    # function in an external repo come back PROVEN; only a positive control
    # caught it. The body is the only region whose execution means the code ran.
    body_lineno: int = 0
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


def _body_start(node) -> int:
    """First executable body line: past decorators, the def line, and a docstring.

    A docstring is a real statement and coverage records it, so counting it
    would keep the import-time false positive alive in a subtler form.
    """
    body = getattr(node, "body", None) or []
    if not body:
        return node.lineno + 1
    first = body[0]
    is_docstring = (isinstance(first, ast.Expr)
                    and isinstance(getattr(first, "value", None), ast.Constant)
                    and isinstance(first.value.value, str))
    if is_docstring and len(body) > 1:
        return body[1].lineno
    if is_docstring:
        return node.lineno + 1  # docstring-only body: nothing to execute
    return first.lineno


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
                                   lineno=node.lineno, end_lineno=end,
                                   body_lineno=_body_start(node)))
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
        start = s.body_lineno or (s.lineno + 1)
        s.executed_lines = sum(1 for ln in hit if start <= ln <= s.end_lineno)

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


# ── Test oracle ──────────────────────────────────────────────────────────────
#
# A DIFFERENT question from prove_diff: not "was this code executed?" but
# "did this test execute anything?" A test that passes while touching zero
# product lines is counted in CI, reported green, and verifies nothing.
#
# Measured on this repo: 458 of 2,733 test functions executed zero product
# lines. The canonical specimen mocks out its own subject with
# patch.dict(sys.modules, {...: MagicMock()}), re-implements the production
# logic inside the test body, asserts the mock it just created was called by
# itself, and prints a green checkmark. It passes in 0.08s.
#
# This is uniquely an AI-authored failure mode — humans rarely bother mocking
# out the thing they are testing — and it is invisible to linters, type
# checkers, coverage percentage, vulture, deadcode and SAST alike. Mutation
# testing is the only existing answer, at 100-1000x the runtime.

@dataclass
class TautologyResult:
    """Tests that passed while executing no product code."""

    verdict: str                       # PROVEN | REFUTED | INSUFFICIENT
    reason: str
    total_tests: int
    zero_product_tests: List[str]
    coverage_source: str = ""


def _is_test_path(rel: str) -> bool:
    """True for test files, whose own lines never count as product code."""
    parts = Path(rel).parts
    return ("tests" in parts or "test" in parts
            or Path(rel).name.startswith("test_")
            or Path(rel).name.endswith("_test.py")
            or "conftest" in Path(rel).name)


def prove_tests(repo: Optional[Path] = None,
                coverage_file: Optional[Path] = None) -> TautologyResult:
    """Find tests that passed while executing zero product lines.

    Requires the suite to have been run with per-test contexts::

        coverage run --context=test --source=<pkg> -m pytest
        # or set dynamic_context = test_function in .coveragerc

    Without contexts nothing can be attributed to individual tests, which is
    INSUFFICIENT — never a pass. Reporting "no tautologies found" from a
    database that cannot express the answer would be the exact false-green
    this module exists to catch.
    """
    repo = repo or repo_root()
    if coverage_file is not None:
        cov_path = coverage_file
    else:
        candidates = [Path.cwd() / ".coverage", repo / ".coverage"]
        cov_path = next((c for c in candidates if c.exists()), candidates[-1])

    try:
        from coverage import CoverageData
    except ImportError:
        return TautologyResult("INSUFFICIENT", "coverage not installed", 0, [])
    if not cov_path.exists():
        return TautologyResult("INSUFFICIENT", f"no coverage data at {cov_path}", 0, [])

    try:
        data = CoverageData(basename=str(cov_path))
        data.read()
        contexts = [c for c in (data.measured_contexts() or []) if c]
    except Exception as exc:  # noqa: BLE001
        return TautologyResult("INSUFFICIENT", f"unreadable coverage data: {exc}", 0, [])

    # A STATIC LABEL IS NOT PER-TEST ATTRIBUTION. `coverage run --context=test`
    # writes ONE context named "test" covering the whole run. Treating that as
    # per-test data made this function report "PROVEN — all 1 test(s) executed
    # product code" from a run of 33 tests: a false green produced by the tool
    # misreading its own evidence. Per-test contexts carry a separator and the
    # test's own name (e.g. tests.test_prove.test_foo); a bare label does not.
    per_test = [c for c in contexts if ("." in c or "::" in c) and "test" in c.lower()]
    if not per_test:
        return TautologyResult(
            "INSUFFICIENT",
            "coverage database has no PER-TEST contexts (found %d aggregate "
            "label(s): %s) — re-run with `dynamic_context = test_function` in "
            "a coverage rcfile; note `--context=NAME` sets one static label "
            "for the whole run and cannot attribute anything to a test"
            % (len(contexts), ", ".join(sorted(contexts)[:3]) or "none"),
            0, [], coverage_source=str(cov_path))
    contexts = per_test

    measured = list(data.measured_files())
    zero: List[str] = []
    for ctx in contexts:
        touched_product = 0
        for fname in measured:
            try:
                rel = str(Path(fname).resolve().relative_to(repo.resolve()))
            except Exception:  # noqa: BLE001 — outside the repo
                continue
            if _is_test_path(rel):
                continue  # a test executing its own lines proves nothing
            try:
                data.set_query_context(ctx)
                if data.lines(fname):
                    touched_product += 1
                    break
            except Exception:  # noqa: BLE001
                continue
        if touched_product == 0:
            zero.append(ctx)

    if zero:
        pct = round(100.0 * len(zero) / len(contexts), 1)
        return TautologyResult(
            "REFUTED",
            f"{len(zero)} of {len(contexts)} test(s) ({pct}%) executed zero product lines",
            len(contexts), zero, coverage_source=str(cov_path))
    return TautologyResult(
        "PROVEN", f"all {len(contexts)} test(s) executed product code",
        len(contexts), [], coverage_source=str(cov_path))


def format_tautology(r: TautologyResult) -> str:
    """Human-readable oracle verdict. INSUFFICIENT never renders as a pass."""
    bar = "─" * 68
    out = [bar, "  NUCLEUS PROVE — did your tests execute anything?", bar]
    out.append(f"  TESTS         : {r.total_tests} with per-test attribution")
    if r.coverage_source:
        out.append(f"  EVIDENCE      : {r.coverage_source}")
    if r.zero_product_tests:
        out.append("")
        out.append("  PASSED WHILE EXECUTING ZERO PRODUCT CODE:")
        for t in r.zero_product_tests[:25]:
            out.append(f"    {t}")
        if len(r.zero_product_tests) > 25:
            out.append(f"    … and {len(r.zero_product_tests) - 25} more")
    out.append("")
    out.append(f"  VERDICT       : {r.verdict} — {r.reason}")
    out.append(bar)
    return "\n".join(out)


def emit_tautology_receipt(r: TautologyResult) -> None:
    """Record the oracle result in the claim corpus. Never raises."""
    try:
        from .receipt import ClaimType, Receipt, Verdict, record

        record(Receipt(
            claim_type=ClaimType.TESTS_PASS,
            claim="passing tests exercise product code",
            verdict=getattr(Verdict, r.verdict),
            primitive="coverage per-test contexts ∩ non-test files",
            claimed=f"{r.total_tests} tests passed",
            observed=f"{len(r.zero_product_tests)} executed zero product lines",
            source="nucleus_prove",
            evidence=r.coverage_source,
            reason=r.reason,
            tags=["prove", "test-oracle"],
        ))
    except Exception as exc:  # noqa: BLE001
        logger.debug("tautology receipt skipped: %s", exc)
