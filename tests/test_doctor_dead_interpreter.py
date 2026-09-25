import argparse
import os
import sys

from mcp_server_nucleus.cli import handle_doctor_command


def test_doctor_fails_on_dead_symlink(tmp_path, capsys, monkeypatch):
    """A dead venv interpreter symlink (target missing) is flagged as FAIL."""
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    dead_target = venv_bin / "nonexistent_target"
    python_link = venv_bin / "python"
    os.symlink(dead_target, python_link)

    monkeypatch.chdir(tmp_path)
    handle_doctor_command(argparse.Namespace())
    out = capsys.readouterr().out

    assert "Venv interpreter symlink is dead" in out
    assert "recreate the venv (e.g. uv venv)" in out


def test_doctor_passes_on_live_symlink(tmp_path, capsys, monkeypatch):
    """A live venv interpreter symlink (target exists) is not flagged."""
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    python_link = venv_bin / "python"
    os.symlink(sys.executable, python_link)

    monkeypatch.chdir(tmp_path)
    handle_doctor_command(argparse.Namespace())
    out = capsys.readouterr().out

    assert "Venv interpreter symlink is dead" not in out


def test_doctor_no_venv(tmp_path, capsys, monkeypatch):
    """No .venv present means no dead-symlink FAIL."""
    monkeypatch.chdir(tmp_path)
    handle_doctor_command(argparse.Namespace())
    out = capsys.readouterr().out

    assert "Venv interpreter symlink is dead" not in out
