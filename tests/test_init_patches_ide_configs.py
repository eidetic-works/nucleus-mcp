"""Opposed pair for the `nucleus init` IDE-configuration promise.

The wizard asks "Auto-configure your AI IDEs (Claude Desktop, Cursor,
Windsurf)?" and offers "detect and patch IDE configs". On yes, the post-init
summary prints "Restart your AI client to pick up the new config".

`init` genuinely writes a project-local `.mcp.json` (covered by
tests/test_onboarding_registration.py, which passes and is correct). What it
does NOT do is touch the three IDEs the prompt names -- the patching code
(`_get_ide_config_paths` / `_patch_mcp_config`) is only reachable from the
separate `nucleus setup` verb.

These two tests are an opposed pair over the set that test file never looks at:

  * yes -> an EXISTING Claude Desktop config must gain a nucleus entry
  * no  -> that same file must be byte-identical

The first must FAIL against the code as it stands. That failure is the point:
it is the positive control proving the instrument can emit non-zero.
"""
import json
import platform
import sys
from pathlib import Path

import pytest


def _claude_desktop_path(home: Path) -> Path:
    if platform.system() == "Darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Linux":
        return home / ".config" / "Claude" / "claude_desktop_config.json"
    return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"


def _run_init(tmp_path, monkeypatch, *, auto_setup_ide: bool) -> Path:
    """Run `nucleus init --wizard` with the wizard stubbed, in an isolated home.

    Returns the Claude Desktop config path, pre-seeded with an unrelated server
    so the no-invent-on-missing guard cannot be what makes the test pass.
    """
    from mcp_server_nucleus import cli

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    desktop = _claude_desktop_path(home)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(
        json.dumps({"mcpServers": {"unrelated": {"command": "something-else"}}}, indent=2),
        encoding="utf-8",
    )

    brain = tmp_path / ".brain"
    fake_config = {
        "brain_path": str(brain),
        "template": "default",
        "persona": "founder",
        "recipe": None,
        "project_name": "demo",
        "project_description": "",
        "languages": [],
        "auto_setup_ide": auto_setup_ide,
        # This fixture stands in for a user who was ASKED and answered at a real
        # prompt. Without this key the caller cannot tell an answer from a
        # non-interactive default, and init must refuse to patch -- so omitting
        # it here would quietly test the wrong thing.
        "auto_setup_ide_explicit": auto_setup_ide,
        "git": False,
        "git_remote": None,
    }

    import mcp_server_nucleus.runtime.onboarding as onboarding
    monkeypatch.setattr(onboarding, "run_onboarding_wizard", lambda path=".brain": fake_config)

    monkeypatch.setattr("sys.argv", ["nucleus", "init", "--wizard"])
    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code in (0, None), f"init exited {exc.code}"

    return desktop


def test_init_yes_patches_claude_desktop(tmp_path, monkeypatch):
    """Answering YES must add a nucleus entry to an existing Claude Desktop config.

    The wizard promised to "detect and patch IDE configs" and the summary told
    the user to restart their client to pick up "the new config".
    """
    desktop = _run_init(tmp_path, monkeypatch, auto_setup_ide=True)

    data = json.loads(desktop.read_text(encoding="utf-8"))
    assert "unrelated" in data["mcpServers"], "pre-existing server must survive"
    assert "nucleus" in data["mcpServers"], (
        "init answered YES to 'Auto-configure your AI IDEs (Claude Desktop, ...)' "
        "and printed 'Restart your AI client to pick up the new config', but the "
        "Claude Desktop config was never touched."
    )


def test_init_no_leaves_claude_desktop_byte_identical(tmp_path, monkeypatch):
    """Answering NO must leave the file exactly as it was. The opposed half."""
    home_probe = tmp_path / "home"
    desktop = _run_init(tmp_path, monkeypatch, auto_setup_ide=False)

    data = json.loads(desktop.read_text(encoding="utf-8"))
    assert data == {"mcpServers": {"unrelated": {"command": "something-else"}}}, (
        "answering NO must not modify any IDE config"
    )
