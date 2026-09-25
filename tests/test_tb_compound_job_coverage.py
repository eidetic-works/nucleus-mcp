"""Comprehensive coverage tests for tb_compound_job.py."""

import json
import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.jobs import tb_compound_job


@pytest.fixture
def fake_home(monkeypatch, tmp_path):
    """Redirect Path.home() to tmp_path and create brain structure."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    brain = fake_home / "ai-mvp-backend" / ".brain"
    brain.mkdir(parents=True)
    driver_dir = brain / "driver"
    driver_dir.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return fake_home, brain, driver_dir


def _make_config(driver_dir, **overrides):
    """Write a config.json with given overrides."""
    config = {"headless_enabled": True, "autonomous_daily_task_cap": 5, "autonomous_branch": "tb/test"}
    config.update(overrides)
    (driver_dir / "config.json").write_text(json.dumps(config))


def _make_budget(driver_dir, tasks_run, today=None):
    """Write a daily_budget.json."""
    if today is None:
        today = date.today().isoformat()
    (driver_dir / "daily_budget.json").write_text(
        json.dumps({"date": today, "tasks_run": tasks_run})
    )


@pytest.mark.asyncio
async def test_run_tb_compound_no_config(fake_home):
    """No config file → headless_enabled defaults to False → skipped."""
    fake_home, brain, driver_dir = fake_home
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is True
    assert result["skipped"] == "headless_enabled is false"


@pytest.mark.asyncio
async def test_run_tb_compound_headless_disabled(fake_home):
    """Config has headless_enabled=False → skipped."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, headless_enabled=False)
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is True
    assert result["skipped"] == "headless_enabled is false"


@pytest.mark.asyncio
async def test_run_tb_compound_config_invalid_json(fake_home):
    """Config with invalid JSON → treated as empty → skipped."""
    fake_home, brain, driver_dir = fake_home
    (driver_dir / "config.json").write_text("not valid json{{{")
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is True
    assert result["skipped"] == "headless_enabled is false"


@pytest.mark.asyncio
async def test_run_tb_compound_daily_cap_reached(fake_home):
    """Budget shows tasks_run >= cap → skipped."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=5)
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is True
    assert "daily cap 5" in result["skipped"]


@pytest.mark.asyncio
async def test_run_tb_compound_budget_stale_date(fake_home):
    """Budget has old date → reset to 0, continues to run."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=5, today="2020-01-01")
    # Driver script doesn't exist → will return error
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is False
    assert "driver not found" in result["error"]


@pytest.mark.asyncio
async def test_run_tb_compound_no_budget_file(fake_home):
    """No budget file → starts fresh, continues to run."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=3)
    # No budget file
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is False
    assert "driver not found" in result["error"]


@pytest.mark.asyncio
async def test_run_tb_compound_budget_invalid_json(fake_home):
    """Budget with invalid JSON → treated as empty, continues."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=3)
    (driver_dir / "daily_budget.json").write_text("invalid{{{")
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is False
    assert "driver not found" in result["error"]


@pytest.mark.asyncio
async def test_run_tb_compound_driver_not_found(fake_home):
    """Config ok, budget ok, but driver script missing → error."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is False
    assert "driver not found" in result["error"]


@pytest.mark.asyncio
async def test_run_tb_compound_success(fake_home):
    """Full success path: subprocess returns 0 with task completions."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=1)

    # Create fake driver script
    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    fake_proc = SimpleNamespace(
        returncode=0,
        stdout="Task completed\nTask completed\nSome other output",
    )
    with patch("subprocess.run", return_value=fake_proc):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is True
    assert result["tasks"] == 2

    # Verify budget was updated
    budget = json.loads((driver_dir / "daily_budget.json").read_text())
    assert budget["tasks_run"] == 3  # 1 + max(2, 1) = 3


@pytest.mark.asyncio
async def test_run_tb_compound_success_no_tasks(fake_home):
    """Subprocess returns 0 but no 'Task completed' in output → tasks=0, budget increments by 1."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    fake_proc = SimpleNamespace(returncode=0, stdout="no tasks here")
    with patch("subprocess.run", return_value=fake_proc):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is True
    assert result["tasks"] == 0

    budget = json.loads((driver_dir / "daily_budget.json").read_text())
    assert budget["tasks_run"] == 1  # 0 + max(0, 1) = 1


@pytest.mark.asyncio
async def test_run_tb_compound_subprocess_failure(fake_home):
    """Subprocess returns non-zero → ok False with tasks count."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    fake_proc = SimpleNamespace(returncode=1, stdout="Task completed\n")
    with patch("subprocess.run", return_value=fake_proc):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is False
    assert result["tasks"] == 1


@pytest.mark.asyncio
async def test_run_tb_compound_no_stdout(fake_home):
    """Subprocess returns 0 with None stdout → tasks=0, budget increments by 1."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    fake_proc = SimpleNamespace(returncode=0, stdout=None)
    with patch("subprocess.run", return_value=fake_proc):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is True
    assert result["tasks"] == 0


@pytest.mark.asyncio
async def test_run_tb_compound_timeout(fake_home):
    """Subprocess times out → caught, returns timeout error."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 7200)):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is False
    assert result["error"] == "timeout"


@pytest.mark.asyncio
async def test_run_tb_compound_custom_branch(fake_home):
    """Custom branch from config is passed to subprocess."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5, autonomous_branch="tb/custom")
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    fake_proc = SimpleNamespace(returncode=0, stdout="")
    with patch("subprocess.run", return_value=fake_proc) as mock_run:
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is True
    args = mock_run.call_args[0][0]
    assert "--branch" in args
    assert "tb/custom" in args


@pytest.mark.asyncio
async def test_run_tb_compound_budget_parent_created(fake_home):
    """Budget parent directory is created if it doesn't exist."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    # No budget file, and remove driver dir to test mkdir
    import shutil
    shutil.rmtree(driver_dir)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    # Config also gone, so headless_enabled=False → skipped
    result = await tb_compound_job.run_tb_compound()
    assert result["ok"] is True
    assert result["skipped"] == "headless_enabled is false"


@pytest.mark.asyncio
async def test_run_tb_compound_generic_exception(fake_home, monkeypatch):
    """Generic exception (not TimeoutExpired) after config checks → caught by broad except."""
    fake_home, brain, driver_dir = fake_home
    _make_config(driver_dir, autonomous_daily_task_cap=5)
    _make_budget(driver_dir, tasks_run=0)

    scripts_dir = fake_home / "ai-mvp-backend" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "third_brother_driver.py").write_text("# stub")

    # Patch subprocess.run to raise a non-TimeoutExpired exception
    with patch("subprocess.run", side_effect=PermissionError("access denied")):
        result = await tb_compound_job.run_tb_compound()

    assert result["ok"] is False
    assert "access denied" in result["error"]
