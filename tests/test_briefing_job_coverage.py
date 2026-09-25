"""Comprehensive coverage tests for briefing_job.py."""

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.jobs import briefing_job


# ── check_requirements ────────────────────────────────────────

def test_check_requirements_network_ok(monkeypatch):
    """Network reachable → (True, 'ok')."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    ok, msg = briefing_job.check_requirements()
    assert ok is True
    assert msg == "ok"


def test_check_requirements_network_fail(monkeypatch):
    """Network unreachable → (False, 'no network')."""
    def _fail(*a, **kw):
        raise OSError("refused")
    monkeypatch.setattr(socket, "create_connection", _fail)
    ok, msg = briefing_job.check_requirements()
    assert ok is False
    assert msg == "no network"


# ── run_briefing ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_briefing_network_fail(monkeypatch):
    """Network check fails → returns error immediately."""
    def _fail(*a, **kw):
        raise OSError("refused")
    monkeypatch.setattr(socket, "create_connection", _fail)
    result = await briefing_job.run_briefing()
    assert result["ok"] is False
    assert result["error"] == "no network"


@pytest.mark.asyncio
async def test_run_briefing_script_not_found(monkeypatch, tmp_path):
    """Network ok but script missing → error."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(briefing_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await briefing_job.run_briefing()
    assert result["ok"] is False
    assert result["error"] == "telegram_briefing.py not found"


@pytest.mark.asyncio
async def test_run_briefing_success(monkeypatch, tmp_path):
    """Script runs main() successfully → ok True."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(briefing_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "telegram_briefing.py").write_text(
        "def main():\n    return None\n"
    )
    result = await briefing_job.run_briefing()
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_run_briefing_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit() → caught, returns error."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(briefing_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "telegram_briefing.py").write_text(
        "import sys\ndef main():\n    sys.exit(1)\n"
    )
    result = await briefing_job.run_briefing()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["error"]


@pytest.mark.asyncio
async def test_run_briefing_exception(monkeypatch, tmp_path):
    """Script raises exception → caught, returns error."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(briefing_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "telegram_briefing.py").write_text(
        "def main():\n    raise ValueError('bad token')\n"
    )
    result = await briefing_job.run_briefing()
    assert result["ok"] is False
    assert "bad token" in result["error"]
