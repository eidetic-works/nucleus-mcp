"""Comprehensive tests for mcp_server_nucleus.runtime.scheduler.

Covers ScheduleType, ResourceLevel, ScheduledJob (next_run for all types),
NucleusScheduler (register, tick, mark_started/completed, has_running_heavy,
catchup_jobs, persist_state, status, _is_due, _restore_state).
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.scheduler import (
    ScheduleType,
    ResourceLevel,
    ScheduledJob,
    NucleusScheduler,
)


# ── Enums ──

class TestScheduleType:
    def test_values(self):
        assert ScheduleType.DAILY.value == "daily"
        assert ScheduleType.INTERVAL.value == "interval"
        assert ScheduleType.WEEKLY.value == "weekly"
        assert ScheduleType.MONTHLY.value == "monthly"


class TestResourceLevel:
    def test_values(self):
        assert ResourceLevel.LOW.value == "low"
        assert ResourceLevel.MEDIUM.value == "medium"
        assert ResourceLevel.HIGH.value == "high"


# ── ScheduledJob.next_run ──

class TestScheduledJobNextRun:
    def test_daily_future(self):
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.DAILY, "14:00")
        nxt = job.next_run(now)
        assert nxt.hour == 14
        assert nxt.minute == 0
        assert nxt.day == 15  # same day, future

    def test_daily_past_today(self):
        now = datetime(2026, 1, 15, 15, 0, 0)
        job = ScheduledJob("test", ScheduleType.DAILY, "14:00")
        nxt = job.next_run(now)
        assert nxt.day == 16  # next day
        assert nxt.hour == 14

    def test_interval_hours(self):
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "6h")
        job.last_run = now
        nxt = job.next_run(now)
        assert nxt == now + timedelta(hours=6)

    def test_interval_no_last_run(self):
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "6h")
        nxt = job.next_run(now)
        # base = now - 6h, nxt = base + 6h = now
        assert nxt == now

    def test_interval_minutes_format(self):
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "30m")
        nxt = job.next_run(now)
        # hours = 0 for "m" suffix, base = now - 0 = now, nxt = now
        assert nxt == now

    def test_interval_bare_number(self):
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "8")
        nxt = job.next_run(now)
        # last_run=None: base = now - 8h, nxt = base + 8h = now, so returns now
        assert nxt == now

    def test_weekly_future(self):
        # Jan 15 2026 is a Thursday (weekday=3)
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        nxt = job.next_run(now)
        # Sunday is weekday 6, days_ahead = (6 - 3) % 7 = 3
        assert nxt.weekday() == 6
        assert nxt.hour == 9

    def test_weekly_past_today(self):
        # Jan 18 2026 is a Sunday (weekday=6)
        now = datetime(2026, 1, 18, 15, 0, 0)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        nxt = job.next_run(now)
        # candidate is today 09:00 but <= now, so +1 week
        assert nxt.day == 25  # Jan 25

    def test_weekly_same_day_future(self):
        # Jan 18 2026 is a Sunday at 08:00
        now = datetime(2026, 1, 18, 8, 0, 0)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        nxt = job.next_run(now)
        assert nxt.day == 18  # same day, future time
        assert nxt.hour == 9

    def test_monthly_future(self):
        # Jan 15 2026
        now = datetime(2026, 1, 15, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        nxt = job.next_run(now)
        # day 1 already passed, so next month
        assert nxt.month == 2
        assert nxt.day == 1
        assert nxt.hour == 22

    def test_monthly_today_future(self):
        # Jan 1 2026 at 10:00
        now = datetime(2026, 1, 1, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        nxt = job.next_run(now)
        assert nxt.day == 1
        assert nxt.hour == 22

    def test_monthly_today_past(self):
        # Jan 1 2026 at 23:00
        now = datetime(2026, 1, 1, 23, 0, 0)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        nxt = job.next_run(now)
        assert nxt.month == 2

    def test_monthly_december_rollover(self):
        # Dec 31 2026 at 23:00
        now = datetime(2026, 12, 31, 23, 0, 0)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        nxt = job.next_run(now)
        assert nxt.year == 2027
        assert nxt.month == 1

    def test_monthly_day_capped_at_28(self):
        now = datetime(2026, 2, 1, 10, 0, 0)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "31 22:00")
        nxt = job.next_run(now)
        # Feb doesn't have 31 days, capped to 28
        assert nxt.day == 28

    def test_unknown_type_returns_none(self):
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.schedule_type = "unknown"
        now = datetime(2026, 1, 15, 10, 0, 0)
        assert job.next_run(now) is None


# ── NucleusScheduler ──

class TestNucleusScheduler:
    def test_init_creates_empty_jobs(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        assert sched.jobs == {}
        assert sched._running_jobs == {}

    def test_register_job(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        assert "test" in sched.jobs

    def test_register_restores_from_persisted_state(self, tmp_path):
        # Create persisted state
        state_dir = tmp_path / "daemon"
        state_dir.mkdir()
        state_file = state_dir / "scheduler_state.json"
        last_run = datetime(2026, 1, 15, 10, 0, 0)
        state_file.write_text(json.dumps({
            "test": {
                "last_run": last_run.isoformat(),
                "last_result": "ok",
            }
        }))
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        assert job.last_run == last_run
        assert job.last_result == "ok"

    def test_register_invalid_last_run(self, tmp_path):
        state_dir = tmp_path / "daemon"
        state_dir.mkdir()
        state_file = state_dir / "scheduler_state.json"
        state_file.write_text(json.dumps({
            "test": {
                "last_run": "invalid_date",
                "last_result": "ok",
            }
        }))
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        assert job.last_run is None

    def test_tick_returns_due_jobs(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1h")
        sched.register(job)
        # No last_run, so interval is due immediately
        due = sched.tick(datetime.now())
        assert job in due

    def test_tick_skips_disabled(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1h", enabled=False)
        sched.register(job)
        due = sched.tick(datetime.now())
        assert job not in due

    def test_tick_skips_running(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1h")
        sched.register(job)
        sched.mark_started("test")
        due = sched.tick(datetime.now())
        assert job not in due

    def test_mark_started(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        sched.mark_started("job1")
        assert "job1" in sched._running_jobs

    def test_mark_completed(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        sched.mark_started("test")
        sched.mark_completed("test", "ok", 5.0)
        assert "test" not in sched._running_jobs
        assert job.last_result == "ok"
        assert job.last_duration == 5.0
        assert job.last_run is not None

    def test_mark_completed_not_registered(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        sched.mark_started("unknown")
        sched.mark_completed("unknown", "ok")
        assert "unknown" not in sched._running_jobs

    def test_has_running_heavy_false(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        assert sched.has_running_heavy() is False

    def test_has_running_heavy_true_medium(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00",
                           resource_level=ResourceLevel.MEDIUM)
        sched.register(job)
        sched.mark_started("test")
        assert sched.has_running_heavy() is True

    def test_has_running_heavy_true_high(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00",
                           resource_level=ResourceLevel.HIGH)
        sched.register(job)
        sched.mark_started("test")
        assert sched.has_running_heavy() is True

    def test_has_running_heavy_low_only(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00",
                           resource_level=ResourceLevel.LOW)
        sched.register(job)
        sched.mark_started("test")
        assert sched.has_running_heavy() is False

    def test_catchup_never_run(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        missed = sched.catchup_jobs(datetime.now())
        assert job in missed

    def test_catchup_already_run_recently(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.last_run = datetime.now()
        sched.register(job)
        missed = sched.catchup_jobs(datetime.now())
        # next_run is tomorrow, not missed
        assert job not in missed

    def test_catchup_disabled(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00", enabled=False)
        sched.register(job)
        missed = sched.catchup_jobs(datetime.now())
        assert job not in missed

    def test_catchup_missed_interval(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1h")
        job.last_run = datetime.now() - timedelta(hours=3)
        sched.register(job)
        missed = sched.catchup_jobs(datetime.now())
        assert job in missed

    def test_persist_state(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.last_run = datetime(2026, 1, 15, 10, 0, 0)
        job.last_result = "ok"
        sched.register(job)
        sched.persist_state()
        state_file = tmp_path / "daemon" / "scheduler_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "test" in state
        assert state["test"]["last_result"] == "ok"

    def test_persist_state_no_jobs(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        sched.persist_state()
        state_file = tmp_path / "daemon" / "scheduler_state.json"
        assert state_file.exists()
        assert json.loads(state_file.read_text()) == {}

    def test_status(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("alpha", ScheduleType.DAILY, "10:00")
        sched.register(job)
        status = sched.status()
        assert status["total_jobs"] == 1
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["name"] == "alpha"
        assert status["running"] == []

    def test_status_with_running(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        sched.mark_started("test")
        status = sched.status()
        assert "test" in status["running"]
        assert status["jobs"][0]["running"] is True

    def test_restore_state_corrupt(self, tmp_path):
        state_dir = tmp_path / "daemon"
        state_dir.mkdir()
        state_file = state_dir / "scheduler_state.json"
        state_file.write_text("invalid json")
        sched = NucleusScheduler(tmp_path)
        assert sched._persisted_state == {}


# ── _is_due ──

class TestIsDue:
    def test_daily_due(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        now = datetime(2026, 1, 15, 10, 0, 0)
        assert sched._is_due(job, now) is True

    def test_daily_not_today(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.last_run = datetime(2026, 1, 15, 10, 0, 0)
        sched.register(job)
        now = datetime(2026, 1, 15, 10, 1, 0)
        assert sched._is_due(job, now) is False

    def test_daily_outside_window(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        sched.register(job)
        now = datetime(2026, 1, 15, 12, 0, 0)
        assert sched._is_due(job, now) is False

    def test_interval_due_no_last_run(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "6h")
        sched.register(job)
        assert sched._is_due(job, datetime.now()) is True

    def test_interval_not_due(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "6h")
        job.last_run = datetime.now()
        sched.register(job)
        assert sched._is_due(job, datetime.now()) is False

    def test_interval_due_elapsed(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1h")
        job.last_run = datetime.now() - timedelta(hours=2)
        sched.register(job)
        assert sched._is_due(job, datetime.now()) is True

    def test_interval_bare_number_due(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.INTERVAL, "1")
        job.last_run = datetime.now() - timedelta(hours=2)
        sched.register(job)
        assert sched._is_due(job, datetime.now()) is True

    def test_weekly_wrong_day(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        sched.register(job)
        # Thursday
        now = datetime(2026, 1, 15, 9, 0, 0)
        assert sched._is_due(job, now) is False

    def test_weekly_right_day_in_window(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        sched.register(job)
        # Sunday
        now = datetime(2026, 1, 18, 9, 0, 0)
        assert sched._is_due(job, now) is True

    def test_weekly_already_run_this_week(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.WEEKLY, "Sun 09:00")
        job.last_run = datetime(2026, 1, 18, 9, 0, 0)
        sched.register(job)
        now = datetime(2026, 1, 18, 9, 1, 0)
        assert sched._is_due(job, now) is False

    def test_monthly_wrong_day(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        sched.register(job)
        now = datetime(2026, 1, 15, 22, 0, 0)
        assert sched._is_due(job, now) is False

    def test_monthly_right_day_in_window(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        sched.register(job)
        now = datetime(2026, 1, 1, 22, 0, 0)
        assert sched._is_due(job, now) is True

    def test_monthly_already_run_this_month(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.MONTHLY, "1 22:00")
        job.last_run = datetime(2026, 1, 1, 22, 0, 0)
        sched.register(job)
        now = datetime(2026, 1, 1, 22, 1, 0)
        assert sched._is_due(job, now) is False

    def test_unknown_type_not_due(self, tmp_path):
        sched = NucleusScheduler(tmp_path)
        job = ScheduledJob("test", ScheduleType.DAILY, "10:00")
        job.schedule_type = "unknown"
        # Don't call register (it accesses .value); test _is_due directly
        sched.jobs[job.name] = job
        assert sched._is_due(job, datetime.now()) is False
