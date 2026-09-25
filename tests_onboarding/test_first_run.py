"""Regression tests for the first-run fixes (audit ledger FR-2, FR-3, FR-4, FR-6).

This mirror ships without the main `tests/` tree, so these live in their own
directory and are runnable on their own:

    PYTHONPATH=src python3 -m pytest tests_onboarding -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_server_nucleus import cli  # noqa: E402


NUCLEUS_CFG = {"command": "nucleus-mcp", "args": [], "env": {"NUCLEUS_BRAIN_PATH": "/tmp/x/.brain"}}


# --- FR-3: an installed editor with no MCP config yet must still be configured ---

def test_config_is_created_when_the_editor_directory_exists(tmp_path, capsys):
    """A first-time MCP user has the editor but no config file."""
    ide_dir = tmp_path / ".cursor"
    ide_dir.mkdir()
    cfg = ide_dir / "mcp.json"
    assert not cfg.exists()

    assert cli._patch_mcp_config(cfg, "Cursor", NUCLEUS_CFG) is True
    assert cfg.exists(), "the config file should have been seeded"
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["nucleus"] == NUCLEUS_CFG


def test_nothing_is_invented_for_an_editor_that_is_not_installed(tmp_path):
    """No directory means no editor. Do not scatter configs for absent tools."""
    cfg = tmp_path / ".not-installed" / "mcp.json"
    assert cli._patch_mcp_config(cfg, "Windsurf", NUCLEUS_CFG) is False
    assert not cfg.exists()
    assert not cfg.parent.exists()


def test_existing_config_is_preserved_and_backed_up(tmp_path):
    ide_dir = tmp_path / ".cursor"
    ide_dir.mkdir()
    cfg = ide_dir / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")

    assert cli._patch_mcp_config(cfg, "Cursor", NUCLEUS_CFG) is True
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["other"] == {"command": "x"}, "existing servers must survive"
    assert data["mcpServers"]["nucleus"] == NUCLEUS_CFG
    assert cfg.with_suffix(".json.bak").exists(), "the original should be backed up"


def test_claude_code_config_is_still_never_invented(tmp_path):
    """The hardened Claude Code path deliberately refuses to create the file."""
    cfg = tmp_path / ".claude.json"
    assert cli._patch_mcp_config(cfg, "Claude Code", NUCLEUS_CFG) is False
    assert not cfg.exists()


# --- FR-4: an explicit --template must win over the wizard persona --------------

def _init_template_action(monkeypatch):
    """Reach the real --template action without refactoring cli.main().

    The parser is built inline at the top of an 11,000-line main(), and
    extracting a build_parser() is the cli.py surgery the ledger defers
    (CP-1). Recording every ArgumentParser main() constructs gets us the
    same object with no source change.
    """
    import argparse

    created = {}
    real_add_parser = argparse._SubParsersAction.add_parser

    def recording_add_parser(self, name, **kwargs):
        parser = real_add_parser(self, name, **kwargs)
        created.setdefault(name, parser)
        return parser

    monkeypatch.setattr(argparse._SubParsersAction, "add_parser", recording_add_parser)
    monkeypatch.setattr(sys, "argv", ["nucleus", "init", "--help"])
    with pytest.raises(SystemExit):
        cli.main()

    init_parser = created.get("init")
    assert init_parser is not None, "cli.main() never built an 'init' subparser"
    for action in init_parser._actions:
        if "--template" in (action.option_strings or []):
            return action
    pytest.fail("the init subparser has no --template action")


def test_template_has_no_default_so_an_explicit_value_is_distinguishable(monkeypatch):
    action = _init_template_action(monkeypatch)
    assert action.default is None, (
        "template must default to None, otherwise 'the user asked for default' is "
        "indistinguishable from 'the user asked for nothing' and the onboarding "
        "wizard's persona silently overrides an explicit --template"
    )
    assert set(action.choices) == {"default", "solo", "v0"}


# --- FR-2: the configurator exists and is honest when it configures nothing ------

def test_auto_configure_helper_exists_and_is_callable():
    """The wizard's 'auto-configure my IDEs' answer needs something to call."""
    assert callable(getattr(cli, "_auto_configure_ide_clients", None)), (
        "wizard answers must drive a real configurator, not just summary text"
    )


def test_auto_configure_reports_zero_rather_than_claiming_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_get_ide_config_paths",
                        lambda: [(tmp_path / "absent" / "mcp.json", "Cursor")])
    configured = cli._auto_configure_ide_clients(str(tmp_path / ".brain"))
    assert configured == 0
    out = capsys.readouterr().out
    assert "No AI client config was written" in out, (
        "a user who configured nothing must not be told to restart their client"
    )


def test_auto_configure_counts_real_writes(tmp_path, monkeypatch):
    ide_dir = tmp_path / ".cursor"
    ide_dir.mkdir()
    monkeypatch.setattr(cli, "_get_ide_config_paths",
                        lambda: [(ide_dir / "mcp.json", "Cursor"),
                                 (tmp_path / "absent" / "mcp.json", "Windsurf")])
    assert cli._auto_configure_ide_clients(str(tmp_path / ".brain")) == 1


def test_auto_configure_survives_one_client_raising(tmp_path, monkeypatch):
    """One broken client must not abort configuration of the others."""
    ide_dir = tmp_path / ".cursor"
    ide_dir.mkdir()
    calls = {"n": 0}
    real = cli._patch_mcp_config

    def flaky(path, name, cfg, force=False):
        calls["n"] += 1
        if name == "Exploding":
            raise RuntimeError("boom")
        return real(path, name, cfg, force=force)

    monkeypatch.setattr(cli, "_patch_mcp_config", flaky)
    monkeypatch.setattr(cli, "_get_ide_config_paths",
                        lambda: [(tmp_path / "x.json", "Exploding"),
                                 (ide_dir / "mcp.json", "Cursor")])
    assert cli._auto_configure_ide_clients(str(tmp_path / ".brain")) == 1
    assert calls["n"] == 2, "the second client must still be attempted"
