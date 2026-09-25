"""Consent-for-IDE-patching regression pair.

``nucleus init --wizard`` with non-interactive stdin must NOT use the default
``yes`` as affirmative consent. It must leave pre-existing IDE config files
untouched and tell the user to run ``nucleus setup`` instead.

The explicit-affirmative half proves the instrument can still patch when consent
is real.
"""
import asyncio
import json
import platform
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus import cli
import mcp_server_nucleus.runtime.onboarding as onboarding
import mcp_server_nucleus.tools.grounding as grounding


def _claude_desktop_path(home: Path) -> Path:
    if platform.system() == "Darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Linux":
        return home / ".config" / "Claude" / "claude_desktop_config.json"
    return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"


def _seed_desktop_config(home: Path) -> Path:
    """Create an existing Claude Desktop config and return its path."""
    desktop = _claude_desktop_path(home)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        json.dumps({"mcpServers": {"unrelated": {"command": "something-else"}}}, indent=2),
        encoding="utf-8",
    )
    return desktop


def test_init_noninteractive_default_does_not_patch_ide(tmp_path, monkeypatch, capsys):
    """Non-interactive --wizard keeps pre-seeded IDE configs byte-identical.

    The output must mention ``nucleus setup`` as the manual escape hatch.
    """
    home = tmp_path / "home"
    home.mkdir()
    desktop = _seed_desktop_config(home)
    original_bytes = desktop.read_bytes()

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.argv", ["nucleus", "init", "--wizard"])

    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code in (0, None), f"init exited {exc.code}"

    assert desktop.read_bytes() == original_bytes, (
        "non-interactive default must not modify an existing IDE config"
    )

    captured = capsys.readouterr().out
    assert "nucleus setup" in captured, (
        "non-interactive run must tell the user to run `nucleus setup`"
    )


def test_init_explicit_yes_patches_ide(tmp_path, monkeypatch, capsys):
    """An explicit affirmative answer still patches the existing IDE config."""
    home = tmp_path / "home"
    home.mkdir()
    desktop = _seed_desktop_config(home)

    brain = tmp_path / ".brain"
    fake_config = {
        "brain_path": str(brain),
        "template": "default",
        "persona": "founder",
        "recipe": None,
        "project_name": "demo",
        "project_description": "",
        "languages": [],
        "auto_setup_ide": True,
        "auto_setup_ide_explicit": True,
        "git": False,
        "git_remote": None,
    }

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(onboarding, "run_onboarding_wizard", lambda path=".brain": fake_config)
    monkeypatch.setattr("sys.argv", ["nucleus", "init", "--wizard"])

    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code in (0, None), f"init exited {exc.code}"

    data = json.loads(desktop.read_text(encoding="utf-8"))
    assert "unrelated" in data["mcpServers"], "pre-existing server must survive"
    assert "nucleus" in data["mcpServers"], (
        "an explicit yes must still patch the Claude Desktop config"
    )


def test_grounding_register_returns_name_func_pairs():
    """tools/grounding.py register() must return (name, callable) tuples."""

    class FakeMCP:
        def tool(self, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    mcp = FakeMCP()
    helpers = {
        "make_response": lambda ok, **kw: (ok, kw),
        "get_brain_path": lambda: str(Path("/tmp/.brain")),
    }

    result = grounding.register(mcp, helpers)

    assert isinstance(result, list), "register() must return a list"
    assert len(result) == 1, "register() must return one tool pair"
    name, func = result[0]
    assert isinstance(name, str), "first element of each pair must be a string"
    assert callable(func), "second element of each pair must be callable"
    assert name == "nucleus_ground"

    # The function is async, which is what the MCP server expects.
    assert asyncio.iscoroutinefunction(func)
