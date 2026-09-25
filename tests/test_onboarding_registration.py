"""Tests for onboarding registration via ``_finish_init_with_value`` and ``main``.

These tests exercise the two public surfaces that close out ``nucleus init``:

* ``_finish_init_with_value`` — writes a project-local ``.mcp.json`` carrying
  the nucleus server entry, runs a best-effort memory self-test, and prints a
  compact next-steps block. It must be best-effort: a failed step degrades to
  an honest line, never aborts init.
* ``main`` — the argparse CLI entry point; ``--version`` must exit cleanly and
  report the installed package version.

The old ``TestInitConfigContent`` class (which asserted on
``_build_nucleus_mcp_config`` output shape) is removed; these tests cover the
broader registration close-out instead.
"""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.cli import _finish_init_with_value, main


def test_finish_init_writes_mcp_json_with_nucleus_server(tmp_path, monkeypatch, capsys):
    """``_finish_init_with_value`` writes a ``.mcp.json`` whose ``mcpServers``
    block contains a structured ``nucleus`` entry (a dict, not a bare string)."""
    monkeypatch.chdir(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()

    _finish_init_with_value(brain, "default")

    mcp_path = tmp_path / ".mcp.json"
    assert mcp_path.exists(), "_finish_init_with_value must write .mcp.json"
    parsed = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = parsed.get("mcpServers", {})
    assert "nucleus" in servers, ".mcp.json must register a 'nucleus' server"
    nucleus_entry = servers["nucleus"]
    assert isinstance(nucleus_entry, dict), (
        "nucleus server entry must be a structured dict, not a bare string"
    )
    assert nucleus_entry.get("command"), "nucleus server entry must carry a command"
    # The close-out line is printed to stdout; just confirm it didn't crash.
    captured = capsys.readouterr()
    assert captured.out  # something was printed


def test_finish_init_merges_into_existing_mcp_json(tmp_path, monkeypatch):
    """When ``.mcp.json`` already exists with other servers, the nucleus entry
    is merged in rather than overwriting the file."""
    monkeypatch.chdir(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    pre_existing = {"mcpServers": {"other": {"command": "other-mcp"}}}
    (tmp_path / ".mcp.json").write_text(json.dumps(pre_existing), encoding="utf-8")

    # Non-tTY stdin so the overwrite prompt auto-proceeds (the function treats
    # a non-interactive stdin as "proceed" only when the file exists path is
    # taken; force isatty False to avoid blocking on input).
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    _finish_init_with_value(brain, "default")

    parsed = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    servers = parsed["mcpServers"]
    assert "other" in servers, "pre-existing servers must be preserved on merge"
    assert "nucleus" in servers, "nucleus server must be added on merge"


def test_init_merge_preserves_unrelated_servers(tmp_path, monkeypatch):
    """When ``.mcp.json`` already exists with an unrelated server, ``init`` must
    merge the nucleus entry in while leaving the unrelated server's contents
    byte-for-byte unchanged — and the nucleus command must be an absolute path.

    Isolation preamble: chdir into a tmp dir and repoint ``Path.home`` so the
    memory self-test inside ``_finish_init_with_value`` cannot touch the real
    home directory.
    """
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    pre_existing = {"mcpServers": {"other-server": {"command": "something-else"}}}
    (tmp_path / ".mcp.json").write_text(json.dumps(pre_existing), encoding="utf-8")

    # Non-TTY stdin so the existing-file merge branch does not block on input().
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    brain = tmp_path / ".brain"
    brain.mkdir()

    _finish_init_with_value(brain, "default")

    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    # The unrelated server survives unchanged.
    assert data["mcpServers"]["other-server"] == {"command": "something-else"}
    # Nucleus was added with an absolute command path.
    assert Path(data["mcpServers"]["nucleus"]["command"]).is_absolute()


def test_main_version_exits_cleanly(capsys, monkeypatch):
    """``main`` with ``--version`` prints the version and exits with code 0
    (argparse's SystemExit), without touching the brain or filesystem."""
    monkeypatch.setattr("sys.argv", ["nucleus", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "nucleus" in captured.out.lower(), "--version must print the prog name"


def test_main_is_callable_with_no_args(monkeypatch, tmp_path):
    """``main`` with no subcommand must not raise an unhandled exception; it
    parses and returns (argparse leaves cli_command=None). We run it in an
    empty tmp dir so any incidental filesystem touch is harmless."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.argv", ["nucleus"])
    # No subcommand → argparse prints help to stderr and exits 0 in this CLI's
    # wiring, OR returns None. Accept either: SystemExit(0) or clean return.
    try:
        result = main()
    except SystemExit as exc:
        assert exc.value.code in (0, None), (
            f"main() with no subcommand exited with unexpected code {exc.value.code}"
        )
        result = None
    assert result is None, "main() with no subcommand should not return a truthy value"


def test_init_writes_absolute_command_and_env(tmp_path, monkeypatch):
    """``_finish_init_with_value`` must write a ``.mcp.json`` whose nucleus
    entry carries an *absolute* command path and a populated ``env`` block
    (``NUCLEUS_BRAIN_PATH`` + ``NUCLEUS_AMBIENT_HEALTH``).

    Isolation preamble: chdir into a tmp dir and repoint ``Path.home`` so the
    memory self-test inside ``_finish_init_with_value`` cannot touch the real
    home directory.
    """
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    brain = tmp_path / ".brain"
    brain.mkdir()

    _finish_init_with_value(brain, "default")

    data = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    entry = data["mcpServers"]["nucleus"]

    assert Path(entry["command"]).is_absolute() is True
    assert entry["env"]["NUCLEUS_BRAIN_PATH"] == str(brain.absolute())
    # OLD broken code wrote {"command": "nucleus-mcp"} — a bare relative string with no env. This assertion is the real guard: it fails against that code.
    assert entry["command"] != "nucleus-mcp"
    assert "NUCLEUS_AMBIENT_HEALTH" in entry["env"]
