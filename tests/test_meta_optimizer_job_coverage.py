"""Comprehensive coverage tests for meta_optimizer_job.py."""

from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime.jobs import meta_optimizer_job


@pytest.mark.asyncio
async def test_run_optimizer_script_not_found(monkeypatch, tmp_path):
    """Script missing → error."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is False
    assert result["error"] == "meta_optimizer.py not found"


@pytest.mark.asyncio
async def test_run_optimizer_success(monkeypatch, tmp_path):
    """Script runs run_meta_optimizer successfully → ok True with result."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "meta_optimizer.py").write_text(
        "def run_meta_optimizer():\n    return {'improvements': 5}\n"
    )
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is True
    assert result["result"]["improvements"] == 5


@pytest.mark.asyncio
async def test_run_optimizer_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "meta_optimizer.py").write_text(
        "import sys\ndef run_meta_optimizer():\n    sys.exit(1)\n"
    )
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["error"]


@pytest.mark.asyncio
async def test_run_optimizer_system_exit_none_code(monkeypatch, tmp_path):
    """Script calls sys.exit() with no code → caught with None."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "meta_optimizer.py").write_text(
        "import sys\ndef run_meta_optimizer():\n    sys.exit()\n"
    )
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is False
    assert "sys.exit" in result["error"]


@pytest.mark.asyncio
async def test_run_optimizer_exception(monkeypatch, tmp_path):
    """Script raises exception → caught."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "meta_optimizer.py").write_text(
        "def run_meta_optimizer():\n    raise RuntimeError('optimization failed')\n"
    )
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is False
    assert "optimization failed" in result["error"]


@pytest.mark.asyncio
async def test_run_optimizer_returns_none(monkeypatch, tmp_path):
    """Script returns None → ok True with result None."""
    monkeypatch.setattr(meta_optimizer_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "meta_optimizer.py").write_text(
        "def run_meta_optimizer():\n    return None\n"
    )
    result = await meta_optimizer_job.run_optimizer()
    assert result["ok"] is True
    assert result["result"] is None
