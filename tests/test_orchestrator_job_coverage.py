"""Comprehensive coverage tests for orchestrator_job.py."""

import pytest

from mcp_server_nucleus.runtime.jobs import orchestrator_job


@pytest.mark.asyncio
async def test_run_orchestrator_script_not_found(monkeypatch, tmp_path):
    """Script missing → error."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is False
    assert result["error"] == "orchestrator.py not found"


@pytest.mark.asyncio
async def test_run_orchestrator_success(monkeypatch, tmp_path):
    """Script runs run_orchestrator successfully → ok True with result."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "orchestrator.py").write_text(
        "async def run_orchestrator():\n    return {'events': 10}\n"
    )
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is True
    assert result["result"]["events"] == 10


@pytest.mark.asyncio
async def test_run_orchestrator_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "orchestrator.py").write_text(
        "import sys\nasync def run_orchestrator():\n    sys.exit(1)\n"
    )
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["error"]


@pytest.mark.asyncio
async def test_run_orchestrator_system_exit_none(monkeypatch, tmp_path):
    """Script calls sys.exit() with no code → caught."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "orchestrator.py").write_text(
        "import sys\nasync def run_orchestrator():\n    sys.exit()\n"
    )
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is False
    assert "sys.exit" in result["error"]


@pytest.mark.asyncio
async def test_run_orchestrator_exception(monkeypatch, tmp_path):
    """Script raises exception → caught."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "orchestrator.py").write_text(
        "async def run_orchestrator():\n    raise ValueError('orchestration error')\n"
    )
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is False
    assert "orchestration error" in result["error"]


@pytest.mark.asyncio
async def test_run_orchestrator_returns_none(monkeypatch, tmp_path):
    """Script returns None → ok True with result None."""
    monkeypatch.setattr(orchestrator_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "orchestrator.py").write_text(
        "async def run_orchestrator():\n    return None\n"
    )
    result = await orchestrator_job.run_orchestrator()
    assert result["ok"] is True
    assert result["result"] is None
