"""
Nucleus Cron Scheduler — replaces 15 cron jobs with zero cron entries.

Plugs into the daemon's 5-second tick loop. Persists state across restarts.
No external dependencies (no croniter). Simple time matching for known schedules.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("NucleusScheduler")


class ScheduleType(str, Enum):
    DAILY = "daily"
    INTERVAL = "interval"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ResourceLevel(str, Enum):
    LOW = "low"          # Background, can overlap
    MEDIUM = "medium"    # One at a time preferred
    HIGH = "high"        # Exclusive — blocks other medium/high


@dataclass
class ScheduledJob:
    name: str
    schedule_type: ScheduleType
    schedule_value: str           # "02:00", "6h", "Sun 23:00", "1 22:00"
    handler: Optional[Callable] = None
    resource_level: ResourceLevel = ResourceLevel.LOW
    timeout_seconds: int = 300
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_result: str = "never"
    last_duration: float = 0.0
    requires: List[str] = field(default_factory=list)  # ["ollama", "network", etc.]

    def next_run(self, now: datetime) -> Optional[datetime]:
        """Compute the next fire time after `now`."""
        if self.schedule_type == ScheduleType.DAILY:
            h, m = map(int, self.schedule_value.split(":"))
            candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        elif self.schedule_type == ScheduleType.INTERVAL:
            val = self.schedule_value
            if val.endswith("h"):
                hours = int(val[:-1])
            elif val.endswith("m"):
                hours = 0
                # minutes — won't be used, but defensive
            else:
                hours = int(val)
            interval = timedelta(hours=hours)
            base = self.last_run or (now - interval)
            nxt = base + interval
            return nxt if nxt > now else now

        elif self.schedule_type == ScheduleType.WEEKLY:
            # "Sun 23:00"
            parts = self.schedule_value.split()
            day_name = parts[0][:3]
            h, m = map(int, parts[1].split(":"))
            day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
            target_dow = day_map.get(day_name, 6)
            days_ahead = (target_dow - now.weekday()) % 7
            candidate = (now + timedelta(days=days_ahead)).replace(
                hour=h, minute=m, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(weeks=1)
            return candidate

        elif self.schedule_type == ScheduleType.MONTHLY:
            # "1 22:00"
            parts = self.schedule_value.split()
            day = int(parts[0])
            h, m = map(int, parts[1].split(":"))
            candidate = now.replace(day=min(day, 28), hour=h, minute=m, second=0, microsecond=0)
            if candidate <= now:
                month = now.month + 1
                year = now.year
                if month > 12:
                    month = 1
                    year += 1
                candidate = candidate.replace(year=year, month=month)
            return candidate

        return None


class NucleusScheduler:
    """Time-based job scheduler. Called every 5s by the daemon tick loop."""

    # Window tolerance: job fires if we're within ±2 minutes of target
    FIRE_WINDOW = timedelta(minutes=2)
    # Catch-up stagger: 5 minutes between catch-up jobs on restart
    CATCHUP_STAGGER = timedelta(minutes=5)

    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.jobs: Dict[str, ScheduledJob] = {}
        self.state_path = brain_path / "daemon" / "scheduler_state.json"
        self._running_jobs: Dict[str, float] = {}  # name → start timestamp
        self._restore_state()

    def register(self, job: ScheduledJob):
        """Register a job. Restores last_run from persisted state if available."""
        if job.name in self._persisted_state:
            saved = self._persisted_state[job.name]
            if saved.get("last_run"):
                try:
                    job.last_run = datetime.fromisoformat(saved["last_run"])
                except (ValueError, TypeError):
                    pass
            job.last_result = saved.get("last_result", "never")
        self.jobs[job.name] = job
        logger.debug(f"Registered job: {job.name} ({job.schedule_type.value} {job.schedule_value})")

    def tick(self, now: datetime) -> List[ScheduledJob]:
        """Check all jobs, return list of jobs that should fire now."""
        due = []
        for job in self.jobs.values():
            if not job.enabled:
                continue
            if job.name in self._running_jobs:
                continue
            if self._is_due(job, now):
                due.append(job)
        return due

    def mark_started(self, name: str):
        """Mark a job as currently running."""
        self._running_jobs[name] = time.time()

    def mark_completed(self, name: str, result: str = "ok", duration: float = 0.0):
        """Mark a job as completed. Updates last_run and persists."""
        self._running_jobs.pop(name, None)
        if name in self.jobs:
            self.jobs[name].last_run = datetime.now()
            self.jobs[name].last_result = result
            self.jobs[name].last_duration = duration

    def has_running_heavy(self) -> bool:
        """Check if any medium/high resource job is currently running."""
        for name in self._running_jobs:
            job = self.jobs.get(name)
            if job and job.resource_level in (ResourceLevel.MEDIUM, ResourceLevel.HIGH):
                return True
        return False

    def catchup_jobs(self, now: datetime) -> List[ScheduledJob]:
        """On restart, find jobs that missed their window and should run now."""
        missed = []
        for job in self.jobs.values():
            if not job.enabled:
                continue
            if job.last_run is None:
                # Never run — fire it
                missed.append(job)
                continue
            nxt = job.next_run(job.last_run)
            if nxt and nxt < now:
                missed.append(job)
        return missed

    def persist_state(self):
        """Save last_run times to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {}
        for name, job in self.jobs.items():
            state[name] = {
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "last_result": job.last_result,
                "last_duration": job.last_duration,
                "enabled": job.enabled,
            }
        try:
            self.state_path.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.warning(f"Failed to persist scheduler state: {e}")

    def status(self) -> Dict[str, Any]:
        """Return status dict for `nucleus status`."""
        now = datetime.now()
        jobs_info = []
        for job in sorted(self.jobs.values(), key=lambda j: j.name):
            nxt = job.next_run(now)
            jobs_info.append({
                "name": job.name,
                "schedule": f"{job.schedule_type.value} {job.schedule_value}",
                "last_run": job.last_run.isoformat() if job.last_run else "never",
                "last_result": job.last_result,
                "next_run": nxt.isoformat() if nxt else "unknown",
                "running": job.name in self._running_jobs,
                "enabled": job.enabled,
            })
        return {
            "total_jobs": len(self.jobs),
            "running": list(self._running_jobs.keys()),
            "jobs": jobs_info,
        }

    # ── Internal ──

    def _is_due(self, job: ScheduledJob, now: datetime) -> bool:
        """Check if a job should fire at `now`."""
        if job.schedule_type == ScheduleType.DAILY:
            h, m = map(int, job.schedule_value.split(":"))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            in_window = abs((now - target).total_seconds()) < self.FIRE_WINDOW.total_seconds()
            not_today = (job.last_run is None or job.last_run.date() < now.date())
            return in_window and not_today

        elif job.schedule_type == ScheduleType.INTERVAL:
            val = job.schedule_value
            if val.endswith("h"):
                seconds = int(val[:-1]) * 3600
            else:
                seconds = int(val) * 3600
            if job.last_run is None:
                return True
            elapsed = (now - job.last_run).total_seconds()
            return elapsed >= seconds

        elif job.schedule_type == ScheduleType.WEEKLY:
            parts = job.schedule_value.split()
            day_name = parts[0][:3]
            h, m = map(int, parts[1].split(":"))
            day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
            target_dow = day_map.get(day_name, 6)
            if now.weekday() != target_dow:
                return False
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            in_window = abs((now - target).total_seconds()) < self.FIRE_WINDOW.total_seconds()
            not_this_week = (job.last_run is None or
                             (now - job.last_run).days >= 6)
            return in_window and not_this_week

        elif job.schedule_type == ScheduleType.MONTHLY:
            parts = job.schedule_value.split()
            day = int(parts[0])
            h, m = map(int, parts[1].split(":"))
            if now.day != day:
                return False
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            in_window = abs((now - target).total_seconds()) < self.FIRE_WINDOW.total_seconds()
            not_this_month = (job.last_run is None or
                              job.last_run.month != now.month or
                              job.last_run.year != now.year)
            return in_window and not_this_month

        return False

    def _restore_state(self):
        """Load persisted state from disk."""
        self._persisted_state: Dict[str, dict] = {}
        if self.state_path.exists():
            try:
                self._persisted_state = json.loads(self.state_path.read_text())
                logger.info(f"Restored scheduler state ({len(self._persisted_state)} jobs)")
            except Exception as e:
                logger.warning(f"Failed to restore scheduler state: {e}")
