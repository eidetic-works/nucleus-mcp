"""Comprehensive coverage tests for analytics_job.py."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.jobs import analytics_job


# ── check_requirements ────────────────────────────────────────

def test_check_requirements_no_creds_no_key(monkeypatch, tmp_path):
    """No env var and no key.json → (False, 'no GA4 credentials')."""
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)
    ok, msg = analytics_job.check_requirements()
    assert ok is False
    assert msg == "no GA4 credentials"


def test_check_requirements_no_env_key_exists(monkeypatch, tmp_path):
    """No env var but key.json exists → sets env var, returns (True, 'ok')."""
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    key_file = tmp_path / "key.json"
    key_file.write_text("{}")
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)
    ok, msg = analytics_job.check_requirements()
    assert ok is True
    assert msg == "ok"
    import os
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == str(key_file)


def test_check_requirements_env_already_set(monkeypatch, tmp_path):
    """Env var already set → (True, 'ok') without touching filesystem."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/some/path.json")
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)
    ok, msg = analytics_job.check_requirements()
    assert ok is True
    assert msg == "ok"


# ── run_analytics ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_analytics_creds_fail(monkeypatch, tmp_path):
    """Requirements fail → returns error dict immediately."""
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)
    result = await analytics_job.run_analytics()
    assert result["ok"] is False
    assert result["error"] == "no GA4 credentials"


@pytest.mark.asyncio
async def test_run_analytics_script_not_found(monkeypatch, tmp_path):
    """Creds ok but script missing → error."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/some/path.json")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)
    result = await analytics_job.run_analytics()
    assert result["ok"] is False
    assert result["error"] == "analytics_dashboard.py not found"


@pytest.mark.asyncio
async def test_run_analytics_subprocess_success(monkeypatch, tmp_path):
    """Subprocess returns 0 → ok True."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/some/path.json")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "analytics_dashboard.py").write_text("# stub")
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)

    fake_proc = SimpleNamespace(returncode=0, stderr="", stdout="")
    with patch("subprocess.run", return_value=fake_proc) as mock_run:
        result = await analytics_job.run_analytics()
    assert result["ok"] is True
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "python3" in args[0]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 300


@pytest.mark.asyncio
async def test_run_analytics_subprocess_failure(monkeypatch, tmp_path):
    """Subprocess returns non-zero → ok False with stderr."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/some/path.json")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "analytics_dashboard.py").write_text("# stub")
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)

    long_stderr = "x" * 600
    fake_proc = SimpleNamespace(returncode=1, stderr=long_stderr, stdout="")
    with patch("subprocess.run", return_value=fake_proc):
        result = await analytics_job.run_analytics()
    assert result["ok"] is False
    assert len(result["error"]) == 500  # truncated to 500


@pytest.mark.asyncio
async def test_run_analytics_exception(monkeypatch, tmp_path):
    """Subprocess raises → caught, returns error."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/some/path.json")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "analytics_dashboard.py").write_text("# stub")
    monkeypatch.setattr(analytics_job, "PROJECT_ROOT", tmp_path)

    with patch("subprocess.run", side_effect=OSError("boom")):
        result = await analytics_job.run_analytics()
    assert result["ok"] is False
    assert "boom" in result["error"]
