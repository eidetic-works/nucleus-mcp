"""Coverage tests for runtime/debug_import.py.

This module is a script that executes top-level code on import (sys.path
manipulation + import attempts). To achieve high coverage we exec the
source under several controlled scenarios, compiling against the real
file path so coverage attributes lines correctly.
"""
import builtins
import subprocess
import sys
from pathlib import Path

_SOURCE = (Path(__file__).resolve().parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "debug_import.py").read_text()
_REAL_PATH = str(Path(__file__).resolve().parent.parent / "src" / "mcp_server_nucleus" / "runtime" / "debug_import.py")


def _exec(source, *, file_path=_REAL_PATH, compile_path=_REAL_PATH, overrides=None):
    """Exec the debug_import source under a controlled namespace.

    compile_path is always the real file path (so coverage attributes
    lines to the real source file); file_path is the value exposed to
    the script via __file__ (used to simulate different locations).
    """
    code = compile(source, compile_path, "exec")
    ns = {"__file__": file_path, "__name__": "__main__", "__builtins__": builtins}
    if overrides:
        ns.update(overrides)
    exec(code, ns)
    return ns


def test_scenario_normal_src_found_imports_succeed(capsys):
    """src traversal succeeds, imports succeed (lines 1-15, 18-31, 34-37)."""
    _exec(_SOURCE)
    out = capsys.readouterr().out
    assert "Found src directory" in out
    assert "Successfully imported mcp_server_nucleus" in out


def test_scenario_src_not_in_syspath(capsys, monkeypatch):
    """src_root not already in sys.path -> insert branch (lines 23-24)."""
    # Remove any src-root entries from sys.path temporarily
    saved = list(sys.path)
    sys.path = [p for p in sys.path if "mcp-server-nucleus/src" not in p and p != str(Path(_REAL_PATH).parent)]
    try:
        _exec(_SOURCE)
    finally:
        sys.path = saved
    out = capsys.readouterr().out
    assert "Injected" in out or "sys.path" in out


def test_scenario_no_src_found(capsys, tmp_path):
    """No 'src' dir in parent chain -> fallback branch (lines 16-17)."""
    fake_path = str(tmp_path / "deep" / "debug_import.py")
    _exec(_SOURCE, file_path=fake_path)
    out = capsys.readouterr().out
    assert "Could not find src directory" in out


def test_scenario_mcp_import_fails(capsys, monkeypatch):
    """import mcp_server_nucleus raises ImportError (lines 32-33)."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp_server_nucleus":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    _exec(_SOURCE)
    out = capsys.readouterr().out
    assert "Failed to import mcp_server_nucleus" in out


def test_scenario_locker_import_fails(capsys, monkeypatch):
    """from mcp_server_nucleus.hypervisor.locker import Locker fails (lines 38-39)."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp_server_nucleus.hypervisor.locker":
            raise ImportError("locker blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    _exec(_SOURCE)
    out = capsys.readouterr().out
    assert "Failed to import Locker" in out


def test_subprocess_runs_and_finds_src():
    """Run the script as a standalone subprocess; verify it locates src."""
    result = subprocess.run(
        [sys.executable, _REAL_PATH],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Calculated src_root:" in result.stdout
