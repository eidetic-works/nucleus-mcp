"""`nucleus init` must not pin the interpreter when the entrypoint is right there.

get_nucleus_mcp_command() prefers `shutil.which("nucleus-mcp")` and otherwise
falls back to `[sys.executable, "-m", "mcp_server_nucleus"]`. The fallback is
reached far more often than intended: an MCP client, a launchd job, or a
sandboxed first run frequently has a PATH that does not include the venv's bin/,
so `which` misses a `nucleus-mcp` sitting in the SAME directory as the running
interpreter.

Measured 2026-09-20 on a real first run in a clean venv, with
`env -i PATH=/usr/bin:/bin`:

    "command": "/private/tmp/smokevenv/bin/python",
    "args": ["-m", "mcp_server_nucleus"]

...while /private/tmp/smokevenv/bin/nucleus-mcp existed the whole time.

Why that matters to a user: the written .mcp.json names a specific interpreter
path. Rebuild the venv, move it, or upgrade Python, and the MCP server stops
launching — with no error that points at the config. The entrypoint is the
stabler thing to name, and when `which` fails we can still find it, because
sys.executable IS the venv that has nucleus installed.

Last-resort `-m` is preserved: a genuinely broken install must still produce something
runnable rather than nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import common


# ── NEGATIVE CONTROL: the case that was silently degrading ─────────────────


def test_sibling_entrypoint_is_preferred_over_the_interpreter(tmp_path, monkeypatch):
    """PATH cannot see it, but it is next to the interpreter. Use it."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    entry = fake_bin / "nucleus-mcp"
    entry.write_text("#!/bin/sh\n", encoding="utf-8")
    entry.chmod(0o755)

    monkeypatch.setattr(common.shutil, "which", lambda _n: None)
    monkeypatch.setattr(sys, "executable", str(fake_bin / "python"))

    cmd = common.get_nucleus_mcp_command()
    assert cmd == [str(entry)], f"fell back to the interpreter: {cmd}"
    assert "-m" not in cmd


def test_sibling_must_be_executable_to_count(tmp_path, monkeypatch):
    """A non-executable file of the right name is not an entrypoint."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "nucleus-mcp").write_text("not executable\n", encoding="utf-8")
    (fake_bin / "nucleus-mcp").chmod(0o644)

    monkeypatch.setattr(common.shutil, "which", lambda _n: None)
    monkeypatch.setattr(sys, "executable", str(fake_bin / "python"))

    cmd = common.get_nucleus_mcp_command()
    assert cmd[1:] == ["-m", "mcp_server_nucleus"]


# ── POSITIVE CONTROLS: the paths that already worked must not change ───────


def test_which_hit_is_still_preferred(tmp_path, monkeypatch):
    found = tmp_path / "nucleus-mcp"
    found.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(common.shutil, "which", lambda _n: str(found))
    assert common.get_nucleus_mcp_command() == [str(found.resolve())]


def test_last_resort_module_fallback_survives(tmp_path, monkeypatch):
    """CONTROL against over-applying the fix: with no entrypoint ANYWHERE, the
    module invocation must still be produced. Returning nothing, or raising,
    would turn a degraded install into a broken one."""
    monkeypatch.setattr(common.shutil, "which", lambda _n: None)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bin" / "python"))
    cmd = common.get_nucleus_mcp_command()
    assert cmd[1:] == ["-m", "mcp_server_nucleus"]
    assert cmd[0] == str(tmp_path / "bin" / "python")


def test_result_is_always_non_empty_and_absolute_first_element(monkeypatch):
    cmd = common.get_nucleus_mcp_command()
    assert cmd and Path(cmd[0]).is_absolute()
