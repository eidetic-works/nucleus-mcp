import pytest
"""Coverage tests for mcp_server_nucleus.hypervisor.injector.Injector."""
import json
from pathlib import Path

from mcp_server_nucleus.hypervisor.injector import Injector


def test_init_paths(tmp_path):
    inj = Injector(str(tmp_path))
    assert inj.workspace_root == tmp_path
    assert inj.vscode_settings_path == tmp_path / ".vscode" / "settings.json"


def test_ensure_vscode_dir_creates(tmp_path):
    inj = Injector(str(tmp_path))
    inj._ensure_vscode_dir()
    assert (tmp_path / ".vscode").exists()


def test_read_settings_missing_returns_empty(tmp_path):
    inj = Injector(str(tmp_path))
    assert inj._read_settings() == {}


def test_read_settings_existing(tmp_path):
    inj = Injector(str(tmp_path))
    settings_path = tmp_path / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"foo": "bar"}))
    assert inj._read_settings() == {"foo": "bar"}


def test_read_settings_malformed_raises_rather_than_returning_empty(tmp_path):
    """Corrupt settings.json must RAISE, not read as an empty dict.

    Returning {} let the caller proceed and then write a fresh settings dict
    over the user's real-but-corrupt file, destroying whatever was in it. The
    raise is the safer contract: refuse to manipulate a file we could not
    parse. Changed in 8d11e6e4; this test still encoded the old behaviour.
    """
    inj = Injector(str(tmp_path))
    settings_path = tmp_path / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ this is not json")
    with pytest.raises(RuntimeError, match="corrupted settings.json"):
        inj._read_settings()


def test_read_settings_missing_file_still_returns_empty(tmp_path):
    """OPPOSED: absent is not corrupt. A missing file is a legitimate empty
    state and must NOT raise, or first-run injection would break."""
    inj = Injector(str(tmp_path))
    assert inj._read_settings() == {}


def test_write_settings_success(tmp_path):
    inj = Injector(str(tmp_path))
    assert inj._write_settings({"a": 1}) is True
    data = json.loads(inj.vscode_settings_path.read_text())
    assert data == {"a": 1}


def test_write_settings_failure(tmp_path, monkeypatch):
    inj = Injector(str(tmp_path))
    # Force write to fail by making the path a file that can't be a dir
    monkeypatch.setattr(inj, "vscode_settings_path", Path("/proc/cannot/write/here/settings.json"))
    assert inj._write_settings({"a": 1}) is False


def test_inject_identity_creates_settings(tmp_path):
    inj = Injector(str(tmp_path))
    assert inj.inject_identity("RED TEAM", "#ff0000") is True
    data = json.loads(inj.vscode_settings_path.read_text())
    assert data["workbench.colorCustomizations"]["titleBar.activeBackground"] == "#ff0000"
    assert data["workbench.colorCustomizations"]["titleBar.activeForeground"] == "#ffffff"
    assert data["workbench.colorCustomizations"]["activityBar.background"] == "#ff0000"
    assert "[RED TEAM]" in data["window.title"]


def test_inject_identity_preserves_existing(tmp_path):
    inj = Injector(str(tmp_path))
    settings_path = tmp_path / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"existing": "val", "workbench": {"colorCustomizations": {"other": "#111"}}}))
    assert inj.inject_identity("BLUE", "#007acc") is True
    data = json.loads(settings_path.read_text())
    assert data["existing"] == "val"
    assert data["workbench"]["colorCustomizations"]["other"] == "#111"
    assert data["workbench.colorCustomizations"]["activityBar.background"] == "#007acc"


def test_reset_identity_removes_keys(tmp_path):
    inj = Injector(str(tmp_path))
    inj.inject_identity("RED", "#ff0000")
    assert inj.reset_identity() is True
    data = json.loads(inj.vscode_settings_path.read_text())
    assert "workbench.colorCustomizations" not in data
    assert "window.title" not in data


def test_reset_identity_no_keys(tmp_path):
    inj = Injector(str(tmp_path))
    settings_path = tmp_path / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"other": "val"}))
    assert inj.reset_identity() is True
    data = json.loads(settings_path.read_text())
    assert data == {"other": "val"}


def test_reset_identity_removes_empty_color_customizations(tmp_path):
    inj = Injector(str(tmp_path))
    inj.inject_identity("RED", "#ff0000")
    assert inj.reset_identity() is True
    data = json.loads(inj.vscode_settings_path.read_text())
    assert "workbench.colorCustomizations" not in data


def test_reset_identity_keeps_other_color_keys(tmp_path):
    inj = Injector(str(tmp_path))
    settings_path = tmp_path / ".vscode" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({
        "workbench": {"colorCustomizations": {"other_key": "#222"}},
        "window": {"title": "should_stay"},
    }))
    # Inject on top of existing nested colorCustomizations
    inj.inject_identity("TEST", "#abc")
    assert inj.reset_identity() is True
    data = json.loads(settings_path.read_text())
    # The nested one under "workbench" stays
    assert data["workbench"]["colorCustomizations"]["other_key"] == "#222"
    assert "window.title" not in data or data.get("window", {}).get("title") == "should_stay"
