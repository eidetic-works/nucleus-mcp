"""Comprehensive coverage tests for driver_job.py."""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.jobs import driver_job


# ── _load_driver ──────────────────────────────────────────────

def test_load_driver_not_found(monkeypatch, tmp_path):
    """Driver script missing → FileNotFoundError."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    with pytest.raises(FileNotFoundError, match="Driver not found"):
        driver_job._load_driver()


def test_load_driver_success(monkeypatch, tmp_path):
    """Driver script exists → module loaded and returned."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "def run_compound_mode(branch, rounds):\n    return 'compound'\n"
        "def run_driver(prompt, mode='autonomous', branch='tb/nucleus-work', max_tasks=0):\n    return 'driver'\n"
    )
    mod = driver_job._load_driver()
    assert mod is not None
    assert hasattr(mod, "run_compound_mode")
    assert hasattr(mod, "run_driver")


# ── check_requirements ────────────────────────────────────────

def test_check_requirements_stop_file_present(monkeypatch, tmp_path):
    """Stop file exists → (False, 'stop file present')."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "stop").write_text("")
    ok, msg = driver_job.check_requirements()
    assert ok is False
    assert msg == "stop file present"


def test_check_requirements_ollama_ok(monkeypatch, tmp_path):
    """Ollama available → (True, 'ok')."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        ok, msg = driver_job.check_requirements()
    assert ok is True
    assert msg == "ok"


def test_check_requirements_ollama_unavailable(monkeypatch, tmp_path):
    """Ollama unavailable → (True, 'degraded: ...')."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    with patch("subprocess.run", side_effect=FileNotFoundError("no ollama")):
        ok, msg = driver_job.check_requirements()
    assert ok is True
    assert "degraded" in msg


def test_check_requirements_ollama_timeout(monkeypatch, tmp_path):
    """Ollama times out → (True, 'degraded: ...')."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
        ok, msg = driver_job.check_requirements()
    assert ok is True
    assert "degraded" in msg


# ── run_compound ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_compound_stop_file(monkeypatch, tmp_path):
    """Stop file present → returns error immediately."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "stop").write_text("")
    result = await driver_job.run_compound()
    assert result["ok"] is False
    assert result["error"] == "stop file present"


@pytest.mark.asyncio
async def test_run_compound_success(monkeypatch, tmp_path):
    """Compound mode runs successfully → ok True."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "def run_compound_mode(branch, rounds):\n    return {'tasks': rounds}\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_compound(branch="tb/test", rounds=3)
    assert result["ok"] is True
    assert result["result"] == "compound_complete"


@pytest.mark.asyncio
async def test_run_compound_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "import sys\ndef run_compound_mode(branch, rounds):\n    sys.exit(2)\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_compound()
    assert result["ok"] is False
    assert "sys.exit(2)" in result["error"]


@pytest.mark.asyncio
async def test_run_compound_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "def run_compound_mode(branch, rounds):\n    raise RuntimeError('crash')\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_compound()
    assert result["ok"] is False
    assert "crash" in result["error"]


@pytest.mark.asyncio
async def test_run_compound_driver_not_found(monkeypatch, tmp_path):
    """Driver script missing → FileNotFoundError caught."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_compound()
    assert result["ok"] is False
    assert "Driver not found" in result["error"]


# ── run_driver_session ────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_driver_session_stop_file(monkeypatch, tmp_path):
    """Stop file present → returns error immediately."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "stop").write_text("")
    result = await driver_job.run_driver_session()
    assert result["ok"] is False
    assert result["error"] == "stop file present"


@pytest.mark.asyncio
async def test_run_driver_session_success(monkeypatch, tmp_path):
    """Driver session runs successfully → ok True."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "def run_driver(prompt, mode='autonomous', branch='tb/nucleus-work', max_tasks=0):\n    return 'ok'\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_driver_session(mode="autonomous", branch="tb/test", max_tasks=10)
    assert result["ok"] is True
    assert result["result"] == "driver_complete"


@pytest.mark.asyncio
async def test_run_driver_session_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "import sys\ndef run_driver(prompt, mode='autonomous', branch='tb/nucleus-work', max_tasks=0):\n    sys.exit(3)\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_driver_session()
    assert result["ok"] is False
    assert "sys.exit(3)" in result["error"]


@pytest.mark.asyncio
async def test_run_driver_session_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(driver_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "third_brother_driver.py").write_text(
        "def run_driver(prompt, mode='autonomous', branch='tb/nucleus-work', max_tasks=0):\n    raise ValueError('bad')\n"
    )
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await driver_job.run_driver_session()
    assert result["ok"] is False
    assert "bad" in result["error"]
