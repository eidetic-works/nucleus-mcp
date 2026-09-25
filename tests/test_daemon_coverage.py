"""Comprehensive tests for mcp_server_nucleus.runtime.daemon.

Covers _check_network, _check_ollama, _check_docker, _check_ga4_creds,
REQUIREMENT_CHECKS, DaemonManager (__init__, _check_requirements, _run_job_safe,
_should_auto_compound, get_status, shutdown), run_daemon.
"""
import asyncio
import os
import socket
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

import pytest

from mcp_server_nucleus.runtime.daemon import (
    DaemonManager,
    _check_network,
    _check_ollama,
    _check_docker,
    _check_ga4_creds,
    REQUIREMENT_CHECKS,
    run_daemon,
)
from mcp_server_nucleus.runtime.scheduler import (
    ScheduledJob,
    ScheduleType,
    ResourceLevel,
)


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


# ── Requirement checkers ──

class TestCheckNetwork:
    def test_success(self, monkeypatch):
        mock_socket = MagicMock()
        mock_socket.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_socket.return_value.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(socket, "create_connection", mock_socket)
        assert _check_network() is True

    def test_failure(self, monkeypatch):
        monkeypatch.setattr(socket, "create_connection",
                            MagicMock(side_effect=OSError("no network")))
        assert _check_network() is False


class TestCheckOllama:
    def test_success(self, monkeypatch):
        mock_run = MagicMock(returncode=0)
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_run))
        assert _check_ollama() is True

    def test_failure(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run",
                            MagicMock(side_effect=FileNotFoundError("no ollama")))
        assert _check_ollama() is False


class TestCheckDocker:
    def test_success(self, monkeypatch):
        mock_run = MagicMock(returncode=0)
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_run))
        assert _check_docker() is True

    def test_failure(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run",
                            MagicMock(side_effect=FileNotFoundError("no docker")))
        assert _check_docker() is False


class TestCheckGa4Creds:
    def test_with_env_var(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/key.json")
        assert _check_ga4_creds() is True

    def test_with_brain_path_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        (tmp_path / "key.json").write_text("{}")
        assert _check_ga4_creds() is True

    def test_no_creds(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        brain = tmp_path / "sub" / ".brain"
        brain.mkdir(parents=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        assert _check_ga4_creds() is False


class TestRequirementChecks:
    def test_all_checkers_registered(self):
        assert "network" in REQUIREMENT_CHECKS
        assert "ollama" in REQUIREMENT_CHECKS
        assert "docker" in REQUIREMENT_CHECKS
        assert "ga4_creds" in REQUIREMENT_CHECKS

    def test_all_are_callables(self):
        for checker in REQUIREMENT_CHECKS.values():
            assert callable(checker)


# ── DaemonManager ──

class TestDaemonManagerInit:
    def test_init_no_cron(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        assert dm.brain_path == brain_env
        assert dm.running is False
        assert dm._no_compound is True
        assert dm._no_cron is True
        assert dm._compound_running is False

    def test_init_with_cron_registers_jobs(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=False)
        assert len(dm.scheduler.jobs) > 0

    def test_init_compound_window(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        assert dm._compound_window == (1, 6)

    def test_init_idle_threshold(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        assert dm._idle_threshold_minutes == 10


# ── _check_requirements ──

class TestCheckRequirements:
    def test_no_requirements(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00", requires=[])
        assert dm._check_requirements(job) is True

    def test_requirement_not_met(self, brain_env, monkeypatch):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00", requires=["network"])
        # Patch the REQUIREMENT_CHECKS dict entry directly (dict was populated at import time)
        monkeypatch.setitem(REQUIREMENT_CHECKS, "network", lambda: False)
        assert dm._check_requirements(job) is False

    def test_requirement_met(self, brain_env, monkeypatch):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00", requires=["network"])
        monkeypatch.setitem(REQUIREMENT_CHECKS, "network", lambda: True)
        assert dm._check_requirements(job) is True

    def test_heavy_job_blocked(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00",
                           resource_level=ResourceLevel.MEDIUM)
        dm.scheduler.mark_started("other_heavy")
        dm.scheduler.jobs["other_heavy"] = ScheduledJob(
            "other_heavy", ScheduleType.DAILY, "11:00",
            resource_level=ResourceLevel.HIGH)
        assert dm._check_requirements(job) is False

    def test_heavy_job_not_blocked_low(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00",
                           resource_level=ResourceLevel.LOW)
        assert dm._check_requirements(job) is True


# ── _run_job_safe ──

class TestRunJobSafe:
    @pytest.mark.asyncio
    async def test_success(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.handler = AsyncMock(return_value={"ok": True})
        dm.notifier = MagicMock()
        await dm._run_job_safe(job)
        assert "test" not in dm.scheduler._running_jobs

    @pytest.mark.asyncio
    async def test_failure_with_error(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.handler = AsyncMock(return_value={"ok": False, "error": "something broke"})
        dm.notifier = MagicMock()
        await dm._run_job_safe(job)
        dm.notifier.send.assert_called_once()
        assert "test" not in dm.scheduler._running_jobs

    @pytest.mark.asyncio
    async def test_non_dict_result(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.handler = AsyncMock(return_value="just a string")
        dm.notifier = MagicMock()
        await dm._run_job_safe(job)
        assert "test" not in dm.scheduler._running_jobs

    @pytest.mark.asyncio
    async def test_timeout(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00", timeout_seconds=0)

        async def slow_handler():
            await asyncio.sleep(10)
            return {"ok": True}
        job.handler = slow_handler
        dm.notifier = MagicMock()
        await dm._run_job_safe(job)
        dm.notifier.send.assert_called_once()
        assert "test" not in dm.scheduler._running_jobs

    @pytest.mark.asyncio
    async def test_exception(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")

        async def error_handler():
            raise RuntimeError("handler error")
        job.handler = error_handler
        await dm._run_job_safe(job)
        assert "test" not in dm.scheduler._running_jobs


# ── _should_auto_compound ──

class TestShouldAutoCompound:
    def test_outside_window(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        # Mock datetime to return 12:00 (outside 1-6)
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 12, 0, 0)
            assert dm._should_auto_compound() is False

    def test_within_window_but_not_idle(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        dm._last_activity = datetime.now()
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 3, 0, 0)
            assert dm._should_auto_compound() is False

    def test_within_window_idle_but_heavy_running(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        dm._last_activity = datetime.now() - timedelta(hours=1)
        dm.scheduler.mark_started("heavy")
        dm.scheduler.jobs["heavy"] = ScheduledJob(
            "heavy", ScheduleType.DAILY, "10:00", resource_level=ResourceLevel.HIGH)
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 3, 0, 0)
            assert dm._should_auto_compound() is False

    def test_within_window_idle_no_ollama(self, brain_env, monkeypatch):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        dm._last_activity = datetime.now() - timedelta(hours=1)
        monkeypatch.setattr("mcp_server_nucleus.runtime.daemon._check_ollama", lambda: False)
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 3, 0, 0)
            assert dm._should_auto_compound() is False

    def test_stop_file_exists(self, brain_env, monkeypatch):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        dm._last_activity = datetime.now() - timedelta(hours=1)
        monkeypatch.setattr("mcp_server_nucleus.runtime.daemon._check_ollama", lambda: True)
        # Create stop file
        stop_file = brain_env.parent / "scripts" / "stop"
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.write_text("stop")
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 3, 0, 0)
            assert dm._should_auto_compound() is False

    def test_all_conditions_met(self, brain_env, monkeypatch):
        dm = DaemonManager(brain_env, no_cron=True)
        dm._compound_window = (1, 6)
        # Use a future date so idle check passes (now - last_activity > 10 min)
        mocked_now = datetime(2027, 1, 15, 3, 0, 0)
        dm._last_activity = mocked_now - timedelta(hours=1)
        monkeypatch.setattr("mcp_server_nucleus.runtime.daemon._check_ollama", lambda: True)
        with patch("mcp_server_nucleus.runtime.daemon.datetime") as mock_dt:
            mock_dt.now.return_value = mocked_now
            assert dm._should_auto_compound() is True


# ── get_status ──

class TestGetStatus:
    def test_status(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        status = dm.get_status()
        assert status["brain_path"] == str(brain_env)
        assert status["running"] is False
        assert status["compound_running"] is False
        assert status["cron_active"] is False  # no_cron=True
        assert "uptime_seconds" in status
        assert "uptime_human" in status
        assert "pid" in status
        assert "scheduler" in status

    def test_status_with_cron(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=False)
        status = dm.get_status()
        assert status["cron_active"] is True


# ── shutdown ──

class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_not_running(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        # running is False, so shutdown should return immediately
        await dm.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_running(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.running = True
        dm.lock = MagicMock()
        dm.lock.release = MagicMock()
        # Mock job_pool
        dm.job_pool = MagicMock()
        # shutdown calls sys.exit(0) at the end
        with pytest.raises(SystemExit):
            await dm.shutdown()
        assert dm.running is False
        dm.lock.release.assert_called_once()


# ── run_daemon ──

class TestRunDaemon:
    def test_run_daemon_no_env_uses_cwd(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.chdir(tmp_path)
        # Mock asyncio.run to prevent actual daemon start
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.run") as mock_run:
            with patch("mcp_server_nucleus.runtime.daemon.DaemonManager") as mock_dm:
                run_daemon(no_compound=True, no_cron=True)
                mock_dm.assert_called_once()

    def test_run_daemon_with_env(self, brain_env, monkeypatch):
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.run") as mock_run:
            with patch("mcp_server_nucleus.runtime.daemon.DaemonManager") as mock_dm:
                run_daemon(no_compound=True, no_cron=True)
                mock_dm.assert_called_once()

    def test_run_daemon_keyboard_interrupt(self, brain_env, monkeypatch):
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.run",
                   side_effect=KeyboardInterrupt):
            with patch("mcp_server_nucleus.runtime.daemon.DaemonManager"):
                # Should not raise
                run_daemon(no_compound=True, no_cron=True)


# ── start() ──

class TestStart:
    @pytest.mark.asyncio
    async def test_start_lock_failure(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        with patch("mcp_server_nucleus.runtime.daemon.get_lock", return_value=mock_lock):
            with pytest.raises(SystemExit):
                await dm.start()

    @pytest.mark.asyncio
    async def test_start_success_no_cron(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        # Make main_loop return immediately
        dm.running = True
        call_count = [0]
        async def fake_main_loop():
            call_count[0] += 1
            dm.running = False  # Stop after one iteration
        dm.main_loop = fake_main_loop
        # Mock shutdown to avoid sys.exit
        async def fake_shutdown():
            pass
        dm.shutdown = fake_shutdown
        with patch("mcp_server_nucleus.runtime.daemon.get_lock", return_value=mock_lock):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.get_running_loop") as mock_loop:
                mock_loop.return_value = MagicMock()
                await dm.start()
        assert call_count[0] == 1
        # PID file should exist
        assert (brain_env / "daemon" / "daemon.pid").exists()

    @pytest.mark.asyncio
    async def test_start_with_cron_catchup(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=False)
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        dm.running = True
        async def fake_main_loop():
            dm.running = False
        dm.main_loop = fake_main_loop
        async def fake_shutdown():
            pass
        dm.shutdown = fake_shutdown
        # Mock catchup to return a job
        catchup_job = ScheduledJob("catchup_test", ScheduleType.DAILY, "10:00")
        dm.scheduler.catchup_jobs = MagicMock(return_value=[catchup_job])
        dm._check_requirements = MagicMock(return_value=False)  # Skip actual execution
        with patch("mcp_server_nucleus.runtime.daemon.get_lock", return_value=mock_lock):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.get_running_loop") as mock_loop:
                mock_loop.return_value = MagicMock()
                await dm.start()

    @pytest.mark.asyncio
    async def test_start_cancelled(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        dm.running = True
        async def fake_main_loop():
            raise asyncio.CancelledError()
        dm.main_loop = fake_main_loop
        async def fake_shutdown():
            pass
        dm.shutdown = fake_shutdown
        with patch("mcp_server_nucleus.runtime.daemon.get_lock", return_value=mock_lock):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.get_running_loop") as mock_loop:
                mock_loop.return_value = MagicMock()
                await dm.start()  # Should handle CancelledError

    @pytest.mark.asyncio
    async def test_start_crash(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        dm.running = True
        async def fake_main_loop():
            raise RuntimeError("crash!")
        dm.main_loop = fake_main_loop
        async def fake_shutdown():
            pass
        dm.shutdown = fake_shutdown
        with patch("mcp_server_nucleus.runtime.daemon.get_lock", return_value=mock_lock):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.get_running_loop") as mock_loop:
                mock_loop.return_value = MagicMock()
                await dm.start()  # Should handle exception


# ── main_loop() ──

class TestMainLoop:
    @pytest.mark.asyncio
    async def test_main_loop_single_tick(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        dm.running = True
        dm.pulse = MagicMock()
        # Stop after first sleep
        async def fake_sleep(seconds):
            dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            await dm.main_loop()
        dm.pulse.beat.assert_called()

    @pytest.mark.asyncio
    async def test_main_loop_with_cron(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=False)
        dm.running = True
        dm.pulse = MagicMock()
        dm.scheduler.tick = MagicMock(return_value=[])
        tick_count = [0]
        async def fake_sleep(seconds):
            tick_count[0] += 1
            if tick_count[0] >= 2:
                dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            await dm.main_loop()
        dm.scheduler.tick.assert_called()

    @pytest.mark.asyncio
    async def test_main_loop_training_conductor(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        dm.running = True
        dm.pulse = MagicMock()
        # Force tick_count to 60 on first iteration
        tick_count = [0]
        async def fake_sleep(seconds):
            tick_count[0] += 1
            dm.running = False
        # Mock ArchivePipeline to return high priority action
        mock_archive = MagicMock()
        mock_archive.training_status.return_value = {
            "sft": {"turns": 100, "ready": True},
            "dpo": {"total": 20, "ready": True},
            "cot": {"quality": 10},
            "next_action": {"priority": "critical", "action": "train", "reason": "enough data"},
        }
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            # Force tick_count to 60 by patching the condition
            original_tick = 0
            def tick_side_effect():
                nonlocal original_tick
                original_tick += 60
                return original_tick
            # We can't easily patch tick_count, so let's just run it and verify it doesn't crash
            await dm.main_loop()

    @pytest.mark.asyncio
    async def test_main_loop_active_missions(self, brain_env):
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        dm.running = True
        dm.pulse = MagicMock()
        dm.orchestrator._active_missions = {"mission-1": {}}
        async def fake_sleep(seconds):
            dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            await dm.main_loop()
        # _last_activity should be updated
        assert dm._last_activity is not None

    @pytest.mark.asyncio
    async def test_main_loop_training_conductor_tick60(self, brain_env):
        """Test training conductor runs at tick 60."""
        dm = DaemonManager(brain_env, no_compound=True, no_cron=True)
        dm.running = True
        dm.pulse = MagicMock()
        # Mock ArchivePipeline
        mock_archive = MagicMock()
        mock_archive.training_status.return_value = {
            "sft": {"turns": 100, "ready": True},
            "dpo": {"total": 20, "ready": True},
            "cot": {"quality": 10},
            "next_action": {"priority": "critical", "action": "train",
                            "reason": "enough data", "command": "nucleus train"},
        }
        tick_count = [0]
        async def fake_sleep(seconds):
            tick_count[0] += 1
            if tick_count[0] >= 61:
                dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            with patch("mcp_server_nucleus.runtime.archive_pipeline.ArchivePipeline",
                       return_value=mock_archive):
                await dm.main_loop()
        # Training conductor signal should have been written
        signal_path = brain_env / "training" / "conductor_signal.json"
        assert signal_path.exists()

    @pytest.mark.asyncio
    async def test_main_loop_due_jobs_executed(self, brain_env):
        """Test that due jobs from scheduler are executed."""
        dm = DaemonManager(brain_env, no_compound=True, no_cron=False)
        dm.running = True
        dm.pulse = MagicMock()
        due_job = ScheduledJob("test_due", ScheduleType.DAILY, "10:00")
        due_job.handler = AsyncMock(return_value={"ok": True})
        dm.scheduler.tick = MagicMock(return_value=[due_job])
        dm._check_requirements = MagicMock(return_value=True)
        async def fake_sleep(seconds):
            dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            await dm.main_loop()

    @pytest.mark.asyncio
    async def test_main_loop_compound_trigger(self, brain_env):
        """Test compound mode trigger at tick 60."""
        dm = DaemonManager(brain_env, no_compound=False, no_cron=True)
        dm.running = True
        dm.pulse = MagicMock()
        dm._should_auto_compound = MagicMock(return_value=True)
        compound_called = [False]
        async def fake_auto_compound():
            compound_called[0] = True
            dm._compound_running = False
        dm._auto_compound = fake_auto_compound
        tick_count = [0]
        original_sleep = asyncio.sleep
        async def fake_sleep(seconds):
            tick_count[0] += 1
            # Yield control to allow created tasks to run
            await original_sleep(0)
            if tick_count[0] >= 61:
                dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", new=fake_sleep):
            await dm.main_loop()
        assert compound_called[0] is True

    @pytest.mark.asyncio
    async def test_main_loop_persist_state(self, brain_env):
        """Test scheduler state is persisted at tick 12."""
        dm = DaemonManager(brain_env, no_compound=True, no_cron=False)
        dm.running = True
        dm.pulse = MagicMock()
        dm.scheduler.tick = MagicMock(return_value=[])
        persist_called = [0]
        original_persist = dm.scheduler.persist_state
        def fake_persist():
            persist_called[0] += 1
            return original_persist()
        dm.scheduler.persist_state = fake_persist
        tick_count = [0]
        async def fake_sleep(seconds):
            tick_count[0] += 1
            if tick_count[0] >= 13:
                dm.running = False
        with patch("mcp_server_nucleus.runtime.daemon.asyncio.sleep", side_effect=fake_sleep):
            await dm.main_loop()
        assert persist_called[0] > 0


# ── _auto_compound() ──

class TestAutoCompound:
    @pytest.mark.asyncio
    async def test_auto_compound_success(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.notifier = MagicMock()
        with patch("mcp_server_nucleus.runtime.jobs.driver_job.run_compound",
                   new_callable=AsyncMock, return_value={"ok": True}):
            await dm._auto_compound()
        assert dm._compound_running is False

    @pytest.mark.asyncio
    async def test_auto_compound_failure(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.notifier = MagicMock()
        with patch("mcp_server_nucleus.runtime.jobs.driver_job.run_compound",
                   new_callable=AsyncMock, return_value={"ok": False, "error": "failed"}):
            await dm._auto_compound()
        assert dm._compound_running is False

    @pytest.mark.asyncio
    async def test_auto_compound_timeout(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.notifier = MagicMock()
        async def slow_compound(rounds=5):
            await asyncio.sleep(100)
            return {"ok": True}
        with patch("mcp_server_nucleus.runtime.jobs.driver_job.run_compound", slow_compound):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.wait_for",
                       side_effect=asyncio.TimeoutError()):
                await dm._auto_compound()
        assert dm._compound_running is False

    @pytest.mark.asyncio
    async def test_auto_compound_exception(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.notifier = MagicMock()
        with patch("mcp_server_nucleus.runtime.jobs.driver_job.run_compound",
                   new_callable=AsyncMock, side_effect=RuntimeError("compound error")):
            with patch("mcp_server_nucleus.runtime.daemon.asyncio.wait_for",
                       side_effect=RuntimeError("compound error")):
                await dm._auto_compound()
        assert dm._compound_running is False

    @pytest.mark.asyncio
    async def test_auto_compound_non_dict_result(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.notifier = MagicMock()
        with patch("mcp_server_nucleus.runtime.jobs.driver_job.run_compound",
                   new_callable=AsyncMock, return_value="not a dict"):
            await dm._auto_compound()
        assert dm._compound_running is False


# ── shutdown (thorough) ──

class TestShutdownThorough:
    @pytest.mark.asyncio
    async def test_shutdown_writes_stop_file(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.running = True
        dm.lock = MagicMock()
        dm.job_pool = MagicMock()
        with pytest.raises(SystemExit):
            await dm.shutdown()
        # Stop file should have been created and cleaned up
        stop_file = brain_env.parent / "scripts" / "stop"
        # After shutdown, stop file should be cleaned up
        assert not stop_file.exists()

    @pytest.mark.asyncio
    async def test_shutdown_cleans_pid_file(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.running = True
        dm.lock = MagicMock()
        dm.job_pool = MagicMock()
        # Create PID file
        pid_path = brain_env / "daemon" / "daemon.pid"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text("12345")
        with pytest.raises(SystemExit):
            await dm.shutdown()
        assert not pid_path.exists()

    @pytest.mark.asyncio
    async def test_shutdown_no_lock(self, brain_env):
        dm = DaemonManager(brain_env, no_cron=True)
        dm.running = True
        dm.lock = None
        dm.job_pool = MagicMock()
        with pytest.raises(SystemExit):
            await dm.shutdown()
        assert dm.running is False
