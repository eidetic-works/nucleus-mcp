"""Tests for `nucleus prove --diff`.

The load-bearing assertions are the ones separating "did not run" from "was
never measured" and from "no evidence at all". Every one of those is a third
state that binary pass/fail would round to green.
"""

import os
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.prove import (
    ProveResult,
    Symbol,
    changed_python_files,
    extract_symbols,
    format_result,
    prove_diff,
)


@pytest.fixture
def repo(tmp_path):
    """A real git repo — no mocking of git itself."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=False)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=False)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=False)
    return tmp_path


def _write(repo, rel, body):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def _fake_coverage(monkeypatch, mapping):
    """Stub the coverage read with {relpath: {executed lines}}."""
    from mcp_server_nucleus.runtime import prove as P

    def fake(cov_file):
        return ({str(k): v for k, v in mapping.items()}, "stub")
    monkeypatch.setattr(P, "load_executed_lines", fake)
    if mapping:
        first_path = Path(next(iter(mapping.keys())))
        p = first_path.parent
        while p != p.parent:
            if (p / ".git").exists():
                cov = p / ".coverage"
                cov.write_text("")
                os.utime(cov, None)
                break
            p = p.parent


def test_untracked_new_file_is_included(repo):
    """A brand-new module is the likeliest thing to be unexecuted.

    `git diff` never lists untracked files; omitting them made prove blind to
    its own source file on the first real run.
    """
    _write(repo, "brand_new.py", "def alpha():\n    x = 1\n    return x\n")
    files = changed_python_files(repo)
    assert "brand_new.py" in files


def test_no_coverage_data_is_insufficient_not_pass(repo):
    """Absence of evidence must never render as success."""
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n")
    r = prove_diff(repo=repo, coverage_file=repo / "does-not-exist")
    assert r.verdict == "INSUFFICIENT"
    assert "no coverage data" in r.reason


def test_unmeasured_file_is_not_reported_as_never_executed(repo, monkeypatch):
    """'Never measured' and 'did not run' are different facts.

    Reporting the former as the latter is a false accusation — and is exactly
    how prove's first real run flagged 191/191, including tests that had
    demonstrably just executed.
    """
    _write(repo, "seen.py", "def alpha():\n    x = 1\n    return x\n")
    _write(repo, "unseen.py", "def beta():\n    y = 2\n    return y\n")
    _fake_coverage(monkeypatch, {str(repo / "seen.py"): {1, 2, 3}})
    r = prove_diff(repo=repo)
    unmeasured_names = {s.name for s in r.unmeasured}
    never_names = {s.name for s in r.never_executed}
    assert "beta" in unmeasured_names          # unseen.py was never instrumented
    assert "beta" not in never_names           # so it is NOT an accusation


def test_measured_but_unexecuted_is_refuted(repo, monkeypatch):
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n\n\ndef beta():\n    y = 2\n    return y\n")
    # File measured, but only alpha's lines executed.
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3}})
    r = prove_diff(repo=repo)
    assert r.verdict == "REFUTED"
    assert {s.name for s in r.never_executed} == {"beta"}


def test_all_measured_and_executed_is_proven(repo, monkeypatch):
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3}})
    r = prove_diff(repo=repo)
    assert r.verdict == "PROVEN"
    assert r.never_executed == []


def test_partial_measurement_downgrades_to_insufficient(repo, monkeypatch):
    """Everything measured ran, but coverage missed a changed file.

    That is not a clean pass and must not round up to PROVEN.
    """
    _write(repo, "seen.py", "def alpha():\n    x = 1\n    return x\n")
    _write(repo, "unseen.py", "def beta():\n    y = 2\n    return y\n")
    _fake_coverage(monkeypatch, {str(repo / "seen.py"): {1, 2, 3}})
    r = prove_diff(repo=repo)
    assert r.verdict == "INSUFFICIENT"
    assert "never measured" in r.reason


def test_tiny_symbols_are_ignored_as_noise(repo, monkeypatch):
    _write(repo, "m.py", "def tiny():\n    pass\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1}})
    r = prove_diff(repo=repo, min_body_lines=3)
    assert r.verdict == "INSUFFICIENT"
    assert "no symbols" in r.reason


def test_no_changed_files_is_insufficient_not_proven(repo):
    """Nothing to prove is not proof."""
    r = prove_diff(repo=repo)
    assert r.verdict == "INSUFFICIENT"


def test_extract_symbols_captures_functions_and_classes(repo):
    _write(repo, "m.py",
           "class Thing:\n    def method(self):\n        x = 1\n        return x\n")
    syms = extract_symbols(repo, ["m.py"])
    kinds = {(s.name, s.kind) for s in syms}
    assert ("Thing", "class") in kinds
    assert ("method", "function") in kinds


def test_format_never_renders_insufficient_as_pass():
    r = ProveResult("INSUFFICIENT", "no coverage data", ["a.py"], [], [])
    out = format_result(r)
    assert "INSUFFICIENT" in out
    assert "PROVEN" not in out


# ── Test oracle ──────────────────────────────────────────────────────────────

from mcp_server_nucleus.runtime.prove import (  # noqa: E402
    TautologyResult,
    _is_test_path,
    format_tautology,
    prove_tests,
)


class _FakeCovData:
    """Minimal CoverageData stand-in: contexts -> {file: lines}."""

    def __init__(self, per_context):
        self._per = per_context
        self._ctx = ""

    def read(self):
        return None

    def measured_contexts(self):
        return set(self._per) | {""}

    def measured_files(self):
        return {f for m in self._per.values() for f in m}

    def set_query_context(self, ctx):
        self._ctx = ctx

    def lines(self, fname):
        return self._per.get(self._ctx, {}).get(fname, [])


def _patch_cov(monkeypatch, per_context):
    import coverage
    monkeypatch.setattr(coverage, "CoverageData",
                        lambda basename=None: _FakeCovData(per_context))


def test_static_context_label_is_insufficient_not_proven(repo, monkeypatch):
    """`--context=NAME` sets ONE label for the whole run.

    Treating it as per-test data made prove_tests report
    'PROVEN — all 1 test(s) executed product code' over a 33-test run.
    A bare aggregate label must be rejected, not believed.
    """
    (repo / ".coverage").write_text("")
    _patch_cov(monkeypatch, {"test": {str(repo / "prod.py"): [1, 2]}})
    r = prove_tests(repo=repo, coverage_file=repo / ".coverage")
    assert r.verdict == "INSUFFICIENT"
    assert "PER-TEST" in r.reason


def test_missing_coverage_data_is_insufficient(repo):
    r = prove_tests(repo=repo, coverage_file=repo / "nope")
    assert r.verdict == "INSUFFICIENT"
    assert "no coverage data" in r.reason


def test_test_touching_only_itself_is_refuted(repo, monkeypatch):
    """A test executing only its own lines has verified nothing."""
    (repo / ".coverage").write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_tautology": {str(repo / "tests" / "test_thing.py"): [1, 2]},
    })
    r = prove_tests(repo=repo, coverage_file=repo / ".coverage")
    assert r.verdict == "REFUTED"
    assert r.zero_product_tests == ["tests.test_thing.test_tautology"]


def test_test_touching_product_is_proven(repo, monkeypatch):
    (repo / ".coverage").write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_real": {str(repo / "prod.py"): [1, 2]},
    })
    r = prove_tests(repo=repo, coverage_file=repo / ".coverage")
    assert r.verdict == "PROVEN"
    assert r.zero_product_tests == []


def test_is_test_path_classification():
    assert _is_test_path("tests/test_foo.py")
    assert _is_test_path("pkg/tests/helper.py")
    assert _is_test_path("conftest.py")
    assert _is_test_path("thing_test.py")
    assert not _is_test_path("src/pkg/prod.py")
    assert not _is_test_path("src/latest/module.py")   # 'test' substring, not a test


def test_tautology_format_never_renders_insufficient_as_pass():
    out = format_tautology(TautologyResult("INSUFFICIENT", "no contexts", 0, []))
    assert "INSUFFICIENT" in out
    assert "PROVEN" not in out


def test_def_line_execution_does_not_count_as_running(repo, monkeypatch):
    """A `def` line executes at IMPORT time and proves nothing.

    Positive control on an external repo caught this: a planted function that
    nothing calls came back PROVEN, because the execution window started at
    the def line, which always runs when the module is imported. Every
    function in every imported module looked executed.
    """
    _write(repo, "m.py",
           "def never_called(v):\n"        # line 1 — runs at import
           '    """doc"""\n'               # line 2 — runs at import
           "    x = v * 2\n"               # line 3 — only runs if CALLED
           "    return x\n")               # line 4 — only runs if CALLED
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2}})  # import only
    r = prove_diff(repo=repo)
    assert r.verdict == "REFUTED"
    assert {s.name for s in r.never_executed} == {"never_called"}


def test_body_execution_does_count_as_running(repo, monkeypatch):
    _write(repo, "m.py",
           "def called(v):\n"
           '    """doc"""\n'
           "    x = v * 2\n"
           "    return x\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3, 4}})  # body ran
    r = prove_diff(repo=repo)
    assert r.verdict == "PROVEN"


def test_prove_diff_stale_coverage_returns_insufficient(repo, monkeypatch):
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3}})
    cov = repo / ".coverage"
    cov.write_text("")
    os.utime(cov, (1000, 1000))
    os.utime(repo / "m.py", (2000, 2000))

    r = prove_diff(repo=repo, coverage_file=cov)
    assert r.verdict == "INSUFFICIENT"
    assert "older than changed file(s): m.py" in r.reason


def test_prove_diff_fresh_coverage_preserves_verdict(repo, monkeypatch):
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3}})
    cov = repo / ".coverage"
    cov.write_text("")
    os.utime(cov, (2000, 2000))
    os.utime(repo / "m.py", (1000, 1000))

    r = prove_diff(repo=repo, coverage_file=cov)
    assert r.verdict == "PROVEN"


def test_prove_diff_allow_stale_bypasses_insufficient(repo, monkeypatch):
    _write(repo, "m.py", "def alpha():\n    x = 1\n    return x\n")
    _fake_coverage(monkeypatch, {str(repo / "m.py"): {1, 2, 3}})
    cov = repo / ".coverage"
    cov.write_text("")
    os.utime(cov, (1000, 1000))
    os.utime(repo / "m.py", (2000, 2000))

    r = prove_diff(repo=repo, coverage_file=cov, allow_stale=True)
    assert r.verdict == "PROVEN"


def test_prove_tests_stale_coverage_returns_insufficient(repo, monkeypatch):
    cov = repo / ".coverage"
    cov.write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_real": {str(repo / "prod.py"): [1, 2]},
    })
    _write(repo, "prod.py", "x = 1\n")
    os.utime(cov, (1000, 1000))
    os.utime(repo / "prod.py", (2000, 2000))

    r = prove_tests(repo=repo, coverage_file=cov)
    assert r.verdict == "INSUFFICIENT"
    assert "older than file(s): prod.py" in r.reason


def test_prove_tests_fresh_coverage_preserves_verdict(repo, monkeypatch):
    cov = repo / ".coverage"
    cov.write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_real": {str(repo / "prod.py"): [1, 2]},
    })
    _write(repo, "prod.py", "x = 1\n")
    os.utime(cov, (2000, 2000))
    os.utime(repo / "prod.py", (1000, 1000))

    r = prove_tests(repo=repo, coverage_file=cov)
    assert r.verdict == "PROVEN"


def test_prove_tests_allow_stale_bypasses_insufficient(repo, monkeypatch):
    cov = repo / ".coverage"
    cov.write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_real": {str(repo / "prod.py"): [1, 2]},
    })
    _write(repo, "prod.py", "x = 1\n")
    os.utime(cov, (1000, 1000))
    os.utime(repo / "prod.py", (2000, 2000))

    r = prove_tests(repo=repo, coverage_file=cov, allow_stale=True)
    assert r.verdict == "PROVEN"


def test_prove_tests_external_files_ignored_for_staleness(repo, monkeypatch):
    """Verify B1 fix: site-packages or external files newer than .coverage do NOT trigger INSUFFICIENT."""
    cov = repo / ".coverage"
    cov.write_text("")
    _patch_cov(monkeypatch, {
        "tests.test_thing.test_real": {
            str(repo / "prod.py"): [1, 2],
            "/usr/lib/python3.11/os.py": [10, 20],
        },
    })
    _write(repo, "prod.py", "x = 1\n")
    os.utime(cov, (2000, 2000))
    os.utime(repo / "prod.py", (1000, 1000))

    r = prove_tests(repo=repo, coverage_file=cov)
    assert r.verdict == "PROVEN"


def test_prove_diff_none_repo_handles_staleness_safely(monkeypatch):
    """Verify C1 fix: calling prove_diff with repo=None does not raise AttributeError or TypeError."""
    r = prove_diff(repo=None, coverage_file=Path("/nonexistent/.coverage"))
    assert r.verdict == "INSUFFICIENT"


def test_prove_diff_nonexistent_coverage_file_does_not_crash(repo):
    """Verify C2 fix: passing non-existent coverage_file does not raise FileNotFoundError."""
    r = prove_diff(repo=repo, coverage_file=repo / "missing_cov")
    assert r.verdict == "INSUFFICIENT"


def test_prove_tests_none_repo_handles_staleness_safely(monkeypatch):
    """Verify prove_tests with repo=None does not raise AttributeError or TypeError."""
    r = prove_tests(repo=None, coverage_file=Path("/nonexistent/.coverage"))
    assert r.verdict == "INSUFFICIENT"


def test_prove_tests_nonexistent_coverage_file_does_not_crash(repo):
    """Verify prove_tests with non-existent coverage_file does not raise FileNotFoundError."""
    r = prove_tests(repo=repo, coverage_file=repo / "missing_cov")
    assert r.verdict == "INSUFFICIENT"


