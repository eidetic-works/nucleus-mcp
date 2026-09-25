"""Tests for scripts/handler_completeness_gate.py (treatment sweep #010 vaccine).

Covers the four regression classes the gate must catch:
  1) A handler file with `raise NotImplementedError` is flagged.
  2) A handler file with no stubs passes clean.
  3) Comment lines containing `raise NotImplementedError` are not flagged.
  4) Test files are excluded from the scan.

Plus:
  5) NUCLEUS_HANDLER_GATE_DISABLED=1 always returns 0 (no-op).
  6) The gate passes clean against the LIVE Servers A + B source directories
     (regression: no shipped stub handlers).
  7) JSON output mode returns parseable JSON array.
  8) Multiple stubs in one file produce multiple hits.
  9) Missing src dir emits a warning but does not raise.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_gate():
    repo_root = Path(__file__).parent.parent.parent
    spec_path = repo_root / "scripts" / "handler_completeness_gate.py"
    spec = importlib.util.spec_from_file_location("handler_completeness_gate", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load_gate()


# ── unit: scan_file ──────────────────────────────────────────────────────────

def test_scan_file_finds_stub(tmp_path):
    """A file with `raise NotImplementedError` is flagged."""
    stub = tmp_path / "stub_tool.py"
    stub.write_text("def handle_foo():\n    raise NotImplementedError\n")
    hits = gate.scan_file(stub)
    assert len(hits) == 1
    assert hits[0].line_no == 2
    assert "NotImplementedError" in hits[0].text


def test_scan_file_finds_stub_with_message(tmp_path):
    """raise NotImplementedError('msg') is also flagged."""
    stub = tmp_path / "tool.py"
    stub.write_text("def handle_bar():\n    raise NotImplementedError('not done yet')\n")
    hits = gate.scan_file(stub)
    assert len(hits) == 1


def test_scan_file_comment_line_not_flagged(tmp_path):
    """Lines that are pure comments are not flagged."""
    src = tmp_path / "ok.py"
    src.write_text(
        "# raise NotImplementedError  <-- example, do not copy\n"
        "def handle_baz():\n"
        "    return 'done'\n"
    )
    hits = gate.scan_file(src)
    assert len(hits) == 0


def test_scan_file_no_stubs(tmp_path):
    """A fully implemented handler produces zero hits."""
    impl = tmp_path / "tool.py"
    impl.write_text(
        "def handle_ok(args):\n    return {'status': 'ok', 'args': args}\n"
    )
    hits = gate.scan_file(impl)
    assert hits == []


def test_scan_file_multiple_stubs(tmp_path):
    """Multiple stub lines in one file produce multiple hits."""
    stub = tmp_path / "multi_stub.py"
    stub.write_text(
        "def a():\n    raise NotImplementedError\n\n"
        "def b():\n    raise NotImplementedError('todo')\n"
    )
    hits = gate.scan_file(stub)
    assert len(hits) == 2
    assert {h.line_no for h in hits} == {2, 5}


# ── unit: scan_directory ─────────────────────────────────────────────────────

def test_scan_directory_excludes_tests(tmp_path):
    """Files inside a 'tests/' subdirectory are not scanned."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_stub.py"
    test_file.write_text("def test_it():\n    raise NotImplementedError\n")
    # The stub inside tests/ should be ignored
    hits = gate.scan_directory(tmp_path, exclude_tests=True)
    assert len(hits) == 0


def test_scan_directory_excludes_pycache(tmp_path):
    """__pycache__ directories are not scanned."""
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    pyc = cache / "stub.py"
    pyc.write_text("raise NotImplementedError\n")
    hits = gate.scan_directory(tmp_path)
    assert len(hits) == 0


def test_scan_directory_finds_nested_stub(tmp_path):
    """Stubs in nested subdirectories are found."""
    sub = tmp_path / "tools" / "sub"
    sub.mkdir(parents=True)
    (sub / "nested_stub.py").write_text("def h():\n    raise NotImplementedError\n")
    hits = gate.scan_directory(tmp_path)
    assert len(hits) == 1


# ── unit: run ────────────────────────────────────────────────────────────────

def test_run_disabled_env_var_is_noop(tmp_path, monkeypatch):
    """NUCLEUS_HANDLER_GATE_DISABLED=1 always exits 0."""
    monkeypatch.setenv("NUCLEUS_HANDLER_GATE_DISABLED", "1")
    stub = tmp_path / "stub.py"
    stub.write_text("raise NotImplementedError\n")
    rc = gate.run([tmp_path])
    assert rc == 0


def test_run_clean_exits_zero(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_HANDLER_GATE_DISABLED", raising=False)
    (tmp_path / "ok.py").write_text("def h(): return 42\n")
    rc = gate.run([tmp_path])
    assert rc == 0


def test_run_stub_exits_one(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_HANDLER_GATE_DISABLED", raising=False)
    (tmp_path / "stub.py").write_text("def h():\n    raise NotImplementedError\n")
    rc = gate.run([tmp_path])
    assert rc == 1


def test_run_json_output_is_parseable(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NUCLEUS_HANDLER_GATE_DISABLED", raising=False)
    (tmp_path / "stub.py").write_text("def h():\n    raise NotImplementedError\n")
    rc = gate.run([tmp_path], json_output=True)
    assert rc == 1
    captured = capsys.readouterr()
    findings = json.loads(captured.out)
    assert isinstance(findings, list)
    assert len(findings) == 1
    assert findings[0]["line"] == 2


def test_run_missing_src_dir_warns_not_raises(tmp_path, monkeypatch):
    """A missing src dir emits a warning but does not crash (exits 0 with no hits)."""
    monkeypatch.delenv("NUCLEUS_HANDLER_GATE_DISABLED", raising=False)
    missing = tmp_path / "does_not_exist"
    rc = gate.run([missing])
    assert rc == 0  # no hits from a missing dir


# ── integration: live Servers A + B must pass clean ──────────────────────────

def test_live_servers_a_and_b_are_clean(monkeypatch):
    """Regression: the actual Servers A + B source trees contain no stub handlers.

    This is the core gate: if someone merges a `raise NotImplementedError` into
    a shipped handler, this test turns red on the next CI run.
    """
    monkeypatch.delenv("NUCLEUS_HANDLER_GATE_DISABLED", raising=False)
    repo_root = Path(__file__).parent.parent.parent
    src_dirs = gate._default_src_dirs(repo_root)
    assert src_dirs, "No src dirs found — check repo structure"
    rc = gate.run(src_dirs)
    assert rc == 0, (
        "NotImplementedError stub(s) found in shipped handlers. "
        "Run `python scripts/handler_completeness_gate.py` for details."
    )
