"""Tests for `nucleus work doctor`."""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from mcp_server_nucleus.runs import cli as runs_cli


def _vendor_cli_available() -> bool:
    """Return True if a vendor CLI (agy/devin) is installed and responds to version."""
    for cmd in ("agy", "devin"):
        if not shutil.which(cmd):
            continue
        for arg in ("--version", "version"):
            try:
                proc = subprocess.run(
                    [cmd, arg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if proc.returncode == 0:
                    return True
            except Exception:
                pass
    return False


def _run_doctor_env(monkeypatch, tmp_path):
    """Prepare a writable brain directory and point NUCLEUS_BRAIN_PATH at it."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Make the dispatcher check pass; the test process itself is alive.
    (brain / "dispatcher.pid").write_text(str(os.getpid()))


def test_doctor_all_pass(monkeypatch, tmp_path, capsys):
    if not _vendor_cli_available():
        pytest.xfail("no vendor CLI installed")
    _run_doctor_env(monkeypatch, tmp_path)
    rc = runs_cli.main(["doctor"])
    captured = capsys.readouterr()
    assert rc == 0, f"stdout:\n{captured.out}\nstderr:\n{captured.err}"
    assert "PASS python" in captured.out
    assert "FAIL" not in captured.out


def test_doctor_reports_missing_sandbox(monkeypatch, tmp_path, capsys):
    _run_doctor_env(monkeypatch, tmp_path)
    original_which = runs_cli.shutil.which

    def fake_which(cmd, *args, **kwargs):
        if cmd == "sandbox-exec":
            return None
        return original_which(cmd, *args, **kwargs)

    monkeypatch.setattr(runs_cli.shutil, "which", fake_which)
    rc = runs_cli.main(["doctor"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "FAIL sandbox-exec:" in captured.out
    assert "Sandbox is unavailable; strict trust mode will require approval." in captured.out
    assert "fix:" in captured.out


def test_doctor_reports_missing_vendor(monkeypatch, tmp_path, capsys):
    _run_doctor_env(monkeypatch, tmp_path)
    original_which = runs_cli.shutil.which

    def fake_which(cmd, *args, **kwargs):
        if cmd in ("agy", "devin"):
            return None
        return original_which(cmd, *args, **kwargs)

    monkeypatch.setattr(runs_cli.shutil, "which", fake_which)
    rc = runs_cli.main(["doctor"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "FAIL vendor_cli" in captured.out
