"""Comprehensive coverage tests for smart_drain_job.py."""

import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.jobs import smart_drain_job


# ── check_requirements ────────────────────────────────────────

def test_check_requirements_docker_ok(monkeypatch):
    """Docker info returns 0 → (True, 'ok')."""
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        ok, msg = smart_drain_job.check_requirements()
    assert ok is True
    assert msg == "ok"


def test_check_requirements_docker_not_running(monkeypatch):
    """Docker info returns non-zero → (False, 'docker daemon not running')."""
    fake_proc = SimpleNamespace(returncode=1)
    with patch("subprocess.run", return_value=fake_proc):
        ok, msg = smart_drain_job.check_requirements()
    assert ok is False
    assert msg == "docker daemon not running"


def test_check_requirements_docker_unavailable(monkeypatch):
    """Docker command not found → (False, 'docker unavailable')."""
    with patch("subprocess.run", side_effect=FileNotFoundError("no docker")):
        ok, msg = smart_drain_job.check_requirements()
    assert ok is False
    assert msg == "docker unavailable"


def test_check_requirements_docker_timeout(monkeypatch):
    """Docker info times out → (False, 'docker unavailable')."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 3)):
        ok, msg = smart_drain_job.check_requirements()
    assert ok is False
    assert msg == "docker unavailable"


# ── run_smart_drain ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_smart_drain_docker_unavailable(monkeypatch):
    """Docker unavailable → returns error immediately."""
    with patch("subprocess.run", side_effect=FileNotFoundError("no docker")):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is False
    assert result["error"] == "docker unavailable"


@pytest.mark.asyncio
async def test_run_smart_drain_script_not_found(monkeypatch, tmp_path):
    """Docker ok but script missing → error."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    fake_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", return_value=fake_proc):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is False
    assert result["error"] == "smart-drain.sh not found"


@pytest.mark.asyncio
async def test_run_smart_drain_success(monkeypatch, tmp_path):
    """Script runs and returns 0 → ok True with output."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "smart-drain.sh").write_text("#!/bin/bash\necho drained\n")

    # First call: docker info (returncode=0). Second call: bash script (returncode=0)
    docker_proc = SimpleNamespace(returncode=0)
    script_proc = SimpleNamespace(returncode=0, stdout="drained successfully")
    with patch("subprocess.run", side_effect=[docker_proc, script_proc]):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is True
    assert result["output"] == "drained successfully"


@pytest.mark.asyncio
async def test_run_smart_drain_script_failure(monkeypatch, tmp_path):
    """Script runs but returns non-zero → ok False with output."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "smart-drain.sh").write_text("#!/bin/bash\necho fail\n")

    docker_proc = SimpleNamespace(returncode=0)
    script_proc = SimpleNamespace(returncode=1, stdout="drain failed")
    with patch("subprocess.run", side_effect=[docker_proc, script_proc]):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is False
    assert result["output"] == "drain failed"


@pytest.mark.asyncio
async def test_run_smart_drain_long_output_truncated(monkeypatch, tmp_path):
    """Output longer than 500 chars is truncated."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "smart-drain.sh").write_text("#!/bin/bash\necho drained\n")

    docker_proc = SimpleNamespace(returncode=0)
    long_output = "x" * 600
    script_proc = SimpleNamespace(returncode=0, stdout=long_output)
    with patch("subprocess.run", side_effect=[docker_proc, script_proc]):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is True
    assert len(result["output"]) == 500


@pytest.mark.asyncio
async def test_run_smart_drain_exception(monkeypatch, tmp_path):
    """Subprocess raises exception → caught."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "smart-drain.sh").write_text("#!/bin/bash\necho drained\n")

    docker_proc = SimpleNamespace(returncode=0)
    with patch("subprocess.run", side_effect=[docker_proc, subprocess.TimeoutExpired("bash", 120)]):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_run_smart_drain_no_stdout(monkeypatch, tmp_path):
    """Script returns 0 with no stdout → ok True, output empty."""
    monkeypatch.setattr(smart_drain_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "smart-drain.sh").write_text("#!/bin/bash\n")

    docker_proc = SimpleNamespace(returncode=0)
    script_proc = SimpleNamespace(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[docker_proc, script_proc]):
        result = await smart_drain_job.run_smart_drain()
    assert result["ok"] is True
    assert result["output"] == ""
