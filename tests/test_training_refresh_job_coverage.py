"""Comprehensive coverage tests for training_refresh_job.py."""

import pytest

from mcp_server_nucleus.runtime.jobs import training_refresh_job


# ── _load_module ──────────────────────────────────────────────

def test_load_module_not_found(monkeypatch, tmp_path):
    """Script missing → FileNotFoundError."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    with pytest.raises(FileNotFoundError, match="daily_data_refresh not found"):
        training_refresh_job._load_module()


def test_load_module_success(monkeypatch, tmp_path):
    """Script exists → module loaded."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {'rows': 10}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {'ready': True}\n"
    )
    mod = training_refresh_job._load_module()
    assert hasattr(mod, "refresh_rag_index")
    assert hasattr(mod, "run_pipeline")
    assert hasattr(mod, "run_export_combined")
    assert hasattr(mod, "check_retrain_readiness")


# ── run_refresh ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_refresh_success_with_index(monkeypatch, tmp_path):
    """Full refresh with index=True → ok True with all fields."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {'rows': 10}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {'ready': True}\n"
    )
    result = await training_refresh_job.run_refresh(index=True)
    assert result["ok"] is True
    assert result["stats"]["rows"] == 10
    assert result["indexed"] is True
    assert result["readiness"]["ready"] is True


@pytest.mark.asyncio
async def test_run_refresh_success_without_index(monkeypatch, tmp_path):
    """Full refresh with index=False → indexed stays False."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {'rows': 5}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {'ready': False}\n"
    )
    result = await training_refresh_job.run_refresh(index=False)
    assert result["ok"] is True
    assert result["stats"]["rows"] == 5
    assert result["indexed"] is False
    assert result["readiness"]["ready"] is False


@pytest.mark.asyncio
async def test_run_refresh_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "import sys\ndef refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    sys.exit(1)\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {}\n"
    )
    result = await training_refresh_job.run_refresh()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["error"]


@pytest.mark.asyncio
async def test_run_refresh_system_exit_none(monkeypatch, tmp_path):
    """Script calls sys.exit() with no code → caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "import sys\ndef refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    sys.exit()\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {}\n"
    )
    result = await training_refresh_job.run_refresh()
    assert result["ok"] is False
    assert "sys.exit" in result["error"]


@pytest.mark.asyncio
async def test_run_refresh_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    raise RuntimeError('pipeline crashed')\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {}\n"
    )
    result = await training_refresh_job.run_refresh()
    assert result["ok"] is False
    assert "pipeline crashed" in result["error"]


@pytest.mark.asyncio
async def test_run_refresh_module_not_found(monkeypatch, tmp_path):
    """Module missing → FileNotFoundError caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await training_refresh_job.run_refresh()
    assert result["ok"] is False
    assert "daily_data_refresh not found" in result["error"]


# ── check_readiness ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_readiness_success(monkeypatch, tmp_path):
    """Readiness check succeeds → ok True with readiness."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    return {'ready': True, 'samples': 100}\n"
    )
    result = await training_refresh_job.check_readiness()
    assert result["ok"] is True
    assert result["readiness"]["ready"] is True
    assert result["readiness"]["samples"] == 100


@pytest.mark.asyncio
async def test_check_readiness_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "import sys\ndef refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    sys.exit(2)\n"
    )
    result = await training_refresh_job.check_readiness()
    assert result["ok"] is False
    assert "sys.exit(2)" in result["error"]


@pytest.mark.asyncio
async def test_check_readiness_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "daily_data_refresh.py").write_text(
        "def refresh_rag_index():\n    return True\n"
        "def run_pipeline():\n    return {}\n"
        "def run_export_combined():\n    return None\n"
        "def check_retrain_readiness():\n    raise ValueError('not ready')\n"
    )
    result = await training_refresh_job.check_readiness()
    assert result["ok"] is False
    assert "not ready" in result["error"]


@pytest.mark.asyncio
async def test_check_readiness_module_not_found(monkeypatch, tmp_path):
    """Module missing → FileNotFoundError caught."""
    monkeypatch.setattr(training_refresh_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await training_refresh_job.check_readiness()
    assert result["ok"] is False
    assert "daily_data_refresh not found" in result["error"]
