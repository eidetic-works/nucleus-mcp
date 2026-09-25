"""Comprehensive coverage tests for sunday_bundle_job.py."""

import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime.jobs import sunday_bundle_job


# ── check_requirements ────────────────────────────────────────

def test_check_requirements_network_ok(monkeypatch):
    """Network reachable → (True, 'ok')."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    ok, msg = sunday_bundle_job.check_requirements()
    assert ok is True
    assert msg == "ok"


def test_check_requirements_network_fail(monkeypatch):
    """Network unreachable → (False, 'no network')."""
    def _fail(*a, **kw):
        raise OSError("refused")
    monkeypatch.setattr(socket, "create_connection", _fail)
    ok, msg = sunday_bundle_job.check_requirements()
    assert ok is False
    assert msg == "no network"


# ── run_sunday_bundle ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_sunday_bundle_network_fail(monkeypatch):
    """Network check fails → returns error immediately."""
    def _fail(*a, **kw):
        raise OSError("refused")
    monkeypatch.setattr(socket, "create_connection", _fail)
    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is False
    assert result["error"] == "no network"


@pytest.mark.asyncio
async def test_run_sunday_bundle_both_scripts_not_found(monkeypatch, tmp_path):
    """Both scripts missing → results with 'not found', ok False."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(sunday_bundle_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()

    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is False
    assert result["results"]["auto_strategy_sync"] == "not found"
    assert result["results"]["weekly_summary"] == "not found"


@pytest.mark.asyncio
async def test_run_sunday_bundle_both_success(monkeypatch, tmp_path):
    """Both scripts run successfully → ok True."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(sunday_bundle_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "auto_strategy_sync.py").write_text("def main():\n    return None\n")
    (scripts / "weekly_summary.py").write_text("def main():\n    return None\n")

    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is True
    assert result["results"]["auto_strategy_sync"] == "ok"
    assert result["results"]["weekly_summary"] == "ok"


@pytest.mark.asyncio
async def test_run_sunday_bundle_one_not_found(monkeypatch, tmp_path):
    """One script missing, one ok → ok False."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(sunday_bundle_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "auto_strategy_sync.py").write_text("def main():\n    return None\n")
    # weekly_summary.py missing

    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is False
    assert result["results"]["auto_strategy_sync"] == "ok"
    assert result["results"]["weekly_summary"] == "not found"


@pytest.mark.asyncio
async def test_run_sunday_bundle_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught per-script."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(sunday_bundle_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "auto_strategy_sync.py").write_text(
        "import sys\ndef main():\n    sys.exit(1)\n"
    )
    (scripts / "weekly_summary.py").write_text("def main():\n    return None\n")

    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["results"]["auto_strategy_sync"]
    assert result["results"]["weekly_summary"] == "ok"


@pytest.mark.asyncio
async def test_run_sunday_bundle_exception(monkeypatch, tmp_path):
    """Script raises exception → caught per-script."""
    fake_sock = MagicMock()
    fake_sock.__enter__ = MagicMock(return_value=fake_sock)
    fake_sock.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: fake_sock)
    monkeypatch.setattr(sunday_bundle_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "auto_strategy_sync.py").write_text(
        "def main():\n    return None\n"
    )
    (scripts / "weekly_summary.py").write_text(
        "def main():\n    raise RuntimeError('summary failed')\n"
    )

    result = await sunday_bundle_job.run_sunday_bundle()
    assert result["ok"] is False
    assert result["results"]["auto_strategy_sync"] == "ok"
    assert "summary failed" in result["results"]["weekly_summary"]
