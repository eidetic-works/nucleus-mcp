"""Tests for scripts/empty_fixture_smoke_detector.py (treatment sweep #008)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_detector():
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / "scripts" / "empty_fixture_smoke_detector.py"
    spec = importlib.util.spec_from_file_location("empty_fixture_smoke_detector", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


det = _load_detector()


def test_pattern_A_empty_list_assigned_then_asserted_empty(tmp_path):
    f = tmp_path / "test_empty.py"
    f.write_text(
        "def test_empty_baseline_returns_no_signals():\n"
        "    claims = []\n"
        "    signals = []\n"
        "    assert signals == []\n"
    )
    findings = det.scan_file(f)
    assert any(x["pattern"] == "A" for x in findings)


def test_pattern_B_stub_string_tautology(tmp_path):
    f = tmp_path / "test_stub.py"
    f.write_text(
        "def test_handler_runs():\n"
        "    assert handle_foo() == 'handle_foo executed'\n"
    )
    findings = det.scan_file(f)
    assert any(x["pattern"] == "B" for x in findings)


def test_pattern_C_hasattr_only_body(tmp_path):
    f = tmp_path / "test_existence.py"
    f.write_text(
        "import mod\n"
        "def test_things_exist():\n"
        "    assert hasattr(mod, 'foo')\n"
        "    assert hasattr(mod, 'bar')\n"
    )
    findings = det.scan_file(f)
    assert any(x["pattern"] == "C" for x in findings)


def test_substantive_test_not_flagged(tmp_path):
    f = tmp_path / "test_substantive.py"
    f.write_text(
        "def add(a, b):\n"
        "    return a + b\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n"
    )
    findings = det.scan_file(f)
    assert findings == []


def test_non_test_function_ignored(tmp_path):
    f = tmp_path / "test_helpers.py"
    f.write_text(
        "def helper_returns_empty():\n"
        "    x = []\n"
        "    assert x == []\n"
        "def test_real_thing():\n"
        "    assert 1 + 1 == 2\n"
    )
    findings = det.scan_file(f)
    assert findings == []


def test_malformed_file_returns_none(tmp_path):
    """Peer crack #2 (2026-06-11): parse failure propagates as None (not [])
    so main() can exit 2 per the documented contract."""
    f = tmp_path / "test_broken.py"
    f.write_text("def test_(\n  # syntax error\n")
    assert det.scan_file(f) is None


def test_accumulator_idiom_not_flagged_pattern_A(tmp_path):
    """Peer crack #1 (2026-06-11): accumulator-race idiom is SUBSTANTIVE.
    `corruptions = []` -> reader threads `.append()` -> `assert corruptions
    == []` IS the real atomicity assertion. Detector must not false-positive
    on the shape. Conservative AST walk invalidates `last_assigned_empty`
    whenever the name is referenced ANYWHERE between assignment and assert
    (incl. nested defs that close over it)."""
    f = tmp_path / "test_race.py"
    f.write_text(
        "import threading\n"
        "def test_atomic_write_no_partial_under_race():\n"
        "    corruptions = []\n"
        "    def reader():\n"
        "        corruptions.append('partial')\n"
        "    t = threading.Thread(target=reader)\n"
        "    t.start(); t.join()\n"
        "    assert corruptions == []\n"
    )
    findings = det.scan_file(f)
    assert findings == [], f"accumulator idiom should not fire Pattern A; got {findings}"


def test_scan_tree_returns_tuple_with_parse_failures(tmp_path):
    """scan_tree returns (findings, parse_failures) per crack #2 fix."""
    (tmp_path / "test_ok.py").write_text("def test_x(): assert 1 == 1\n")
    (tmp_path / "test_bad.py").write_text("def test_(\n  # bad\n")
    findings, failures = det.scan_tree(tmp_path)
    assert len(failures) == 1
    assert "test_bad.py" in failures[0]


def test_scan_tree_excludes_pycache_and_worktrees(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "test_stub.py").write_text(
        "def test_x(): assert handle_x() == 'handle_x executed'\n"
    )
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "worktrees").mkdir()
    (tmp_path / ".claude" / "worktrees" / "test_stub.py").write_text(
        "def test_x(): assert handle_x() == 'handle_x executed'\n"
    )
    (tmp_path / "test_legit.py").write_text(
        "def test_x(): assert handle_x() == 'handle_x executed'\n"
    )

    findings, failures = det.scan_tree(tmp_path)
    assert len(findings) == 1
    assert "test_legit.py" in findings[0]["file"]
    assert failures == []


def test_main_returns_zero_when_no_findings(tmp_path):
    (tmp_path / "test_clean.py").write_text(
        "def test_real():\n"
        "    assert 1 + 1 == 2\n"
    )
    rc = det.main(["--tests-dir", str(tmp_path)])
    assert rc == 0


def test_main_returns_one_when_findings_found(tmp_path):
    (tmp_path / "test_dirty.py").write_text(
        "def test_bad():\n"
        "    x = []\n"
        "    assert x == []\n"
    )
    rc = det.main(["--tests-dir", str(tmp_path)])
    assert rc == 1


def test_main_allow_findings_returns_zero_with_findings(tmp_path):
    (tmp_path / "test_dirty.py").write_text(
        "def test_bad():\n"
        "    x = []\n"
        "    assert x == []\n"
    )
    rc = det.main(["--tests-dir", str(tmp_path), "--allow-findings"])
    assert rc == 0


def test_main_returns_two_when_tests_dir_missing(tmp_path):
    rc = det.main(["--tests-dir", str(tmp_path / "nope")])
    assert rc == 2


def test_main_returns_two_on_parse_failure(tmp_path):
    """Peer crack #2: parse failure exits 2 per the documented contract,
    taking precedence over the findings-or-clean signal."""
    (tmp_path / "test_ok.py").write_text("def test_x(): assert 1 == 1\n")
    (tmp_path / "test_bad.py").write_text("def test_(\n  # syntax error\n")

    rc = det.main(["--tests-dir", str(tmp_path)])
    assert rc == 2


def test_main_json_output(tmp_path, capsys):
    (tmp_path / "test_dirty.py").write_text(
        "def test_bad():\n"
        "    assert handle_x() == 'handle_x executed'\n"
    )
    det.main(["--tests-dir", str(tmp_path), "--json", "--allow-findings"])
    captured = capsys.readouterr().out
    import json
    data = json.loads(captured.strip())
    assert data["count"] >= 1
    assert any(f["pattern"] == "B" for f in data["findings"])
