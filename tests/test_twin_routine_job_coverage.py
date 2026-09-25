"""Comprehensive coverage tests for twin_routine_job.py."""

import pytest

from mcp_server_nucleus.runtime.jobs import twin_routine_job


# ── _load_module ──────────────────────────────────────────────

def test_load_module_not_found(monkeypatch, tmp_path):
    """Script missing → FileNotFoundError."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    with pytest.raises(FileNotFoundError, match="twin_routine.py not found"):
        twin_routine_job._load_module()


def test_load_module_success(monkeypatch, tmp_path):
    """Script exists → module loaded."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return 'morning'\n"
        "def run_evening_routine():\n    return 'evening'\n"
    )
    mod = twin_routine_job._load_module()
    assert hasattr(mod, "run_morning_routine")
    assert hasattr(mod, "run_evening_routine")


# ── run_morning ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_morning_success(monkeypatch, tmp_path):
    """Morning routine runs successfully → ok True."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return 'morning done'\n"
        "def run_evening_routine():\n    return None\n"
    )
    result = await twin_routine_job.run_morning()
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_run_morning_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "import sys\ndef run_morning_routine():\n    sys.exit(1)\n"
        "def run_evening_routine():\n    return None\n"
    )
    result = await twin_routine_job.run_morning()
    assert result["ok"] is False
    assert "sys.exit(1)" in result["error"]


@pytest.mark.asyncio
async def test_run_morning_system_exit_none(monkeypatch, tmp_path):
    """Script calls sys.exit() with no code → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "import sys\ndef run_morning_routine():\n    sys.exit()\n"
        "def run_evening_routine():\n    return None\n"
    )
    result = await twin_routine_job.run_morning()
    assert result["ok"] is False
    assert "sys.exit" in result["error"]


@pytest.mark.asyncio
async def test_run_morning_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    raise RuntimeError('morning failed')\n"
        "def run_evening_routine():\n    return None\n"
    )
    result = await twin_routine_job.run_morning()
    assert result["ok"] is False
    assert "morning failed" in result["error"]


@pytest.mark.asyncio
async def test_run_morning_module_not_found(monkeypatch, tmp_path):
    """Module missing → FileNotFoundError caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await twin_routine_job.run_morning()
    assert result["ok"] is False
    assert "twin_routine.py not found" in result["error"]


# ── run_evening ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_evening_success(monkeypatch, tmp_path):
    """Evening routine runs successfully → ok True."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return None\n"
        "def run_evening_routine():\n    return 'evening done'\n"
    )
    result = await twin_routine_job.run_evening()
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_run_evening_system_exit(monkeypatch, tmp_path):
    """Script calls sys.exit → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return None\n"
        "import sys\ndef run_evening_routine():\n    sys.exit(2)\n"
    )
    result = await twin_routine_job.run_evening()
    assert result["ok"] is False
    assert "sys.exit(2)" in result["error"]


@pytest.mark.asyncio
async def test_run_evening_system_exit_none(monkeypatch, tmp_path):
    """Script calls sys.exit() with no code → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return None\n"
        "import sys\ndef run_evening_routine():\n    sys.exit()\n"
    )
    result = await twin_routine_job.run_evening()
    assert result["ok"] is False
    assert "sys.exit" in result["error"]


@pytest.mark.asyncio
async def test_run_evening_exception(monkeypatch, tmp_path):
    """Script raises → caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "twin_routine.py").write_text(
        "def run_morning_routine():\n    return None\n"
        "def run_evening_routine():\n    raise ValueError('evening error')\n"
    )
    result = await twin_routine_job.run_evening()
    assert result["ok"] is False
    assert "evening error" in result["error"]


@pytest.mark.asyncio
async def test_run_evening_module_not_found(monkeypatch, tmp_path):
    """Module missing → FileNotFoundError caught."""
    monkeypatch.setattr(twin_routine_job, "PROJECT_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    result = await twin_routine_job.run_evening()
    assert result["ok"] is False
    assert "twin_routine.py not found" in result["error"]
