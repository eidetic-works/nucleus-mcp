"""Argv-level smoke tests for ``python -m mcp_server_nucleus.rabbithole``.

Each test spawns the module as a fresh subprocess (mirroring how an MCP client
launches it) and asserts on exit code / stdout / stderr. A 10s timeout guards
against accidental server start on the flag tests and against a hung stdio loop
on the initialize test.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

# Point subprocess at the source tree, not the installed copy (same pattern as
# test_hook.py).
_SRC = str(pathlib.Path(__file__).parents[1] / "src")
_MODULE = "mcp_server_nucleus.rabbithole"

_TIMEOUT = 10


def _env() -> dict:
    return {**os.environ, "PYTHONPATH": _SRC}


def _run(args: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", _MODULE, *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=_env(),
        timeout=_TIMEOUT,
    )


def test_help_exits_zero_with_usage() -> None:
    proc = _run(["--help"])
    assert proc.returncode == 0, proc.stderr
    assert "nucleus-rabbithole" in proc.stdout, proc.stdout
    assert "mcp" in proc.stdout.lower(), proc.stdout
    # The example client config JSON must appear verbatim.
    assert "mcpServers" in proc.stdout, proc.stdout
    assert "rabbithole" in proc.stdout, proc.stdout
    assert "command" in proc.stdout, proc.stdout


def test_version_exits_zero() -> None:
    proc = _run(["--version"])
    assert proc.returncode == 0, proc.stderr
    assert re.match(r"^\d+\.\d+\.\d+", proc.stdout.strip()), proc.stdout


def test_unknown_flag_exits_two() -> None:
    proc = _run(["--bogus"])
    assert proc.returncode == 2, proc.stdout
    assert "--bogus" in proc.stderr, proc.stderr


def test_no_args_responds_to_mcp_initialize() -> None:
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.0.0"},
        },
    }
    proc = _run([], stdin=json.dumps(init_msg) + "\n")
    assert proc.stdout, f"no stdout: rc={proc.returncode} stderr={proc.stderr!r}"
    assert "serverInfo" in proc.stdout, proc.stdout
    assert "nucleus-rabbithole" in proc.stdout, proc.stdout
