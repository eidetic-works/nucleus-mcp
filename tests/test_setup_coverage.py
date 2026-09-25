"""Coverage tests for mcp_server_nucleus/setup.py — shell-profile detection
and Nucleus PATH injection."""
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus import setup


# ── get_shell_profile ───────────────────────────────────────────────

class TestGetShellProfile:
    def test_zsh(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        p = setup.get_shell_profile()
        assert p == tmp_path / ".zshrc"

    def test_bash_linux(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch("platform.system", return_value="Linux"):
            p = setup.get_shell_profile()
        assert p == tmp_path / ".bashrc"

    def test_bash_macos_with_profile(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".bash_profile").write_text("existing")
        with patch("platform.system", return_value="Darwin"):
            p = setup.get_shell_profile()
        assert p == tmp_path / ".bash_profile"

    def test_bash_macos_no_profile(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch("platform.system", return_value="Darwin"):
            p = setup.get_shell_profile()
        assert p == tmp_path / ".bashrc"

    def test_unknown_shell(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/fish")
        assert setup.get_shell_profile() is None

    def test_empty_shell(self, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        assert setup.get_shell_profile() is None


# ── install_nucleus_path ────────────────────────────────────────────

class TestInstallNucleusPath:
    def test_no_profile_returns_false(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/fish")
        assert setup.install_nucleus_path() is False

    def test_dry_run(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"):
            r = setup.install_nucleus_path(dry_run=True)
        assert r is True
        out = capsys.readouterr().out
        assert "DRY RUN" in out
        assert "NUCLEUS_BRAIN_PATH" in out

    def test_dry_run_with_completion(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Create the completions script so the completion branch runs
        runtime_dir = Path(setup.__file__).parent / "runtime"
        comp = runtime_dir / "completions.sh"
        created = False
        if not comp.exists():
            comp.write_text("# completions")
            created = True
        try:
            with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
                 patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"):
                r = setup.install_nucleus_path(dry_run=True)
            assert r is True
            out = capsys.readouterr().out
            assert "Autocompletion" in out
        finally:
            if created:
                comp.unlink()

    def test_write_success(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        profile = tmp_path / ".zshrc"
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"):
            r = setup.install_nucleus_path(dry_run=False)
        assert r is True
        assert profile.exists()
        content = profile.read_text()
        assert "Nucleus MCP Path Integration" in content
        out = capsys.readouterr().out
        assert "Successfully updated" in out

    def test_write_with_portable_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        brain = tmp_path / ".brain"
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=brain):
            setup.install_nucleus_path(dry_run=False)
        content = (tmp_path / ".zshrc").read_text()
        assert "$HOME" in content

    def test_write_with_non_home_brain(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        brain = Path("/opt/custom/brain")
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=brain):
            setup.install_nucleus_path(dry_run=False)
        content = (tmp_path / ".zshrc").read_text()
        assert "/opt/custom/brain" in content

    def test_already_has_integration(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        profile = tmp_path / ".zshrc"
        profile.write_text("# Nucleus MCP Path Integration\nold stuff\n")
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"):
            r = setup.install_nucleus_path(dry_run=False)
        assert r is True
        out = capsys.readouterr().out
        assert "already has Nucleus integration" in out

    def test_write_failure(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value="/fake/bin"), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"), \
             patch("builtins.open", side_effect=PermissionError("nope")):
            r = setup.install_nucleus_path(dry_run=False)
        assert r is False
        out = capsys.readouterr().out
        assert "Failed to update" in out

    def test_bin_path_in_path_env(self, monkeypatch, tmp_path):
        """When bin_path is already in PATH, the PATH export is skipped."""
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        monkeypatch.setenv("PATH", str(fake_bin))
        with patch("mcp_server_nucleus.setup.get_nucleus_bin_path", return_value=str(fake_bin)), \
             patch("mcp_server_nucleus.setup.get_brain_path", return_value=tmp_path / ".brain"):
            setup.install_nucleus_path(dry_run=True)
