
"""
Nucleus Daemon Manager — Project Purple 2.
The Kernel service that runs the persistent background agent.

`nucleus start` → flywheel spins. That's the product.

Strategic Role:
- Lifecycle Management: Startup, Shutdown, Signal Handling.
- Process Safety: Enforces BrainLock to ensure only one Daemon runs.
- Heartbeat: Updates status for the HUD.
- Scheduler: Replaces 15 cron jobs with zero cron entries.
- Job Execution: Runs scheduled jobs in a bounded thread pool.
"""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .locking import get_lock, BrainLock
from .policy import DirectivesLoader
from .orchestrator import SwarmsOrchestrator
from .hooks import IdentityKey, AmbientTelemetry, InsightExchange, RemoteExecutionProtocol
from .scheduler import NucleusScheduler, ScheduledJob, ScheduleType, ResourceLevel
from .notifier import Notifier

# Configure logging (file handler added in DaemonManager.start() once brain_path is known)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("NucleusDaemon")


# ── Requirement checkers ──

def _check_network() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


def _check_ollama() -> bool:
    try:
        subprocess.run(["ollama", "list"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _check_docker() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False


def _check_ga4_creds() -> bool:
    return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")) or \
           Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".")).parent.joinpath("key.json").exists()


REQUIREMENT_CHECKS = {
    "network": _check_network,
    "ollama": _check_ollama,
    "docker": _check_docker,
    "ga4_creds": _check_ga4_creds,
}


class DaemonManager:
    def __init__(self, brain_path: Path, no_compound: bool = False, no_cron: bool = False):
        self.brain_path = brain_path
        self.lock: Optional[BrainLock] = None
        self.running = False
        self.policy_engine = DirectivesLoader(brain_path)
        self.orchestrator = SwarmsOrchestrator(brain_path)

        # Platform Hooks (Network, Identity, Scale)
        self.identity = IdentityKey(brain_path)
        self.pulse = AmbientTelemetry(brain_path, identity=self.identity)
        self.insight_exchange = InsightExchange(brain_path)
        self.grid = RemoteExecutionProtocol(brain_path)

        # Project Purple 2: Scheduler + Notifier + Job Pool
        self.scheduler = NucleusScheduler(brain_path)
        self.notifier = Notifier(brain_path)
        self._no_compound = no_compound
        self._no_cron = no_cron
        self._compound_running = False
        self._start_time = datetime.now()
        self._last_activity = datetime.now()  # For idle detection
        self._compound_window = (1, 6)  # Hours: auto-compound between 1 AM and 6 AM
        self._idle_threshold_minutes = 10

        if not no_cron:
            self._register_all_jobs()

    def _register_all_jobs(self):
        """Register all scheduled jobs — replaces 15 cron entries."""
        from .jobs import driver_job, training_refresh_job, briefing_job, backup_job
        from .jobs import health_job, orchestrator_job, meta_optimizer_job, analytics_job
        from .jobs import sunday_bundle_job, twin_routine_job, smart_drain_job
        from .jobs import conversation_ingest_job

        jobs = [
            ScheduledJob("training_refresh", ScheduleType.DAILY, "02:00",
                         handler=training_refresh_job.run_refresh,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=2400),
            ScheduledJob("briefing", ScheduleType.DAILY, "05:08",
                         handler=briefing_job.run_briefing,
                         resource_level=ResourceLevel.LOW, timeout_seconds=120,
                         requires=["network"]),
            ScheduledJob("morning_routine", ScheduleType.DAILY, "07:00",
                         handler=twin_routine_job.run_morning,
                         resource_level=ResourceLevel.LOW, timeout_seconds=60),
            ScheduledJob("analytics", ScheduleType.DAILY, "07:30",
                         handler=analytics_job.run_analytics,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=300,
                         requires=["ga4_creds"]),
            ScheduledJob("orchestrator", ScheduleType.DAILY, "09:00",
                         handler=orchestrator_job.run_orchestrator,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=600),
            ScheduledJob("health_check", ScheduleType.INTERVAL, "6h",
                         handler=health_job.run_health_check,
                         resource_level=ResourceLevel.LOW, timeout_seconds=120),
            ScheduledJob("meta_optimizer", ScheduleType.INTERVAL, "72h",
                         handler=meta_optimizer_job.run_optimizer,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=600),
            ScheduledJob("evening_routine", ScheduleType.DAILY, "23:00",
                         handler=twin_routine_job.run_evening,
                         resource_level=ResourceLevel.LOW, timeout_seconds=120),
            ScheduledJob("backup_weekly", ScheduleType.WEEKLY, "Sun 23:30",
                         handler=lambda: backup_job.run_backup("weekly"),
                         resource_level=ResourceLevel.LOW, timeout_seconds=300),
            ScheduledJob("backup_monthly", ScheduleType.MONTHLY, "1 22:00",
                         handler=lambda: backup_job.run_backup("monthly"),
                         resource_level=ResourceLevel.LOW, timeout_seconds=300),
            ScheduledJob("sunday_bundle", ScheduleType.WEEKLY, "Sun 09:00",
                         handler=sunday_bundle_job.run_sunday_bundle,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=600,
                         requires=["network"]),
            ScheduledJob("smart_drain", ScheduleType.INTERVAL, "12h",
                         handler=smart_drain_job.run_smart_drain,
                         resource_level=ResourceLevel.LOW, timeout_seconds=120,
                         requires=["docker"]),
            ScheduledJob("conversation_ingest", ScheduleType.INTERVAL, "6h",
                         handler=conversation_ingest_job.run_conversation_ingest,
                         resource_level=ResourceLevel.MEDIUM, timeout_seconds=1800),
        ]

        for job in jobs:
            self.scheduler.register(job)

        logger.info(f"Registered {len(jobs)} scheduled jobs")

    def _check_requirements(self, job: ScheduledJob) -> bool:
        """Check if a job's requirements are met. Graceful — skip if not."""
        for req in job.requires:
            checker = REQUIREMENT_CHECKS.get(req)
            if checker and not checker():
                logger.debug(f"Skipping {job.name}: requirement '{req}' not met")
                return False
        # Resource guard: don't start medium/high if one is already running
        if job.resource_level in (ResourceLevel.MEDIUM, ResourceLevel.HIGH):
            if self.scheduler.has_running_heavy():
                logger.debug(f"Skipping {job.name}: heavy job already running")
                return False
        return True

    async def _run_job_safe(self, job: ScheduledJob):
        """Execute a job with timeout and error handling."""
        self.scheduler.mark_started(job.name)
        t0 = time.time()
        logger.info(f"[JOB] Starting: {job.name}")

        try:
            result = await asyncio.wait_for(job.handler(), timeout=job.timeout_seconds)
            duration = time.time() - t0
            ok = result.get("ok", True) if isinstance(result, dict) else True
            status = "ok" if ok else f"failed: {result.get('error', 'unknown')}"
            self.scheduler.mark_completed(job.name, status, duration)
            logger.info(f"[JOB] Completed: {job.name} ({duration:.1f}s) — {status}")

            if not ok:
                self.notifier.send(f"Job failed: {job.name}",
                                   result.get("error", "unknown"), "warning")
        except asyncio.TimeoutError:
            duration = time.time() - t0
            self.scheduler.mark_completed(job.name, "timeout", duration)
            logger.warning(f"[JOB] Timeout: {job.name} after {job.timeout_seconds}s")
            self.notifier.send(f"Job timeout: {job.name}",
                               f"Killed after {job.timeout_seconds}s", "warning")
        except Exception as e:
            duration = time.time() - t0
            self.scheduler.mark_completed(job.name, f"error: {e}", duration)
            logger.error(f"[JOB] Error: {job.name} — {e}")

    async def start(self):
        """Start the Daemon sequence"""
        # Attach file handler now that brain_path is known
        log_dir = self.brain_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "daemon.log")
        fh.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))
        logger.addHandler(fh)

        logger.info("Nucleus Daemon Starting...")

        # 1. Acquire Lock
        lock_dir = self.brain_path / ".locks"
        self.lock = get_lock("daemon_process", base_dir=lock_dir)

        if not self.lock.acquire(timeout=1.0):
            logger.error("Could not acquire daemon lock. Is another instance running?")
            sys.exit(1)

        logger.info("BrainLock Acquired. I am the Sovereign Process.")
        self.running = True

        # Write PID file for `nucleus status` / `nucleus stop`
        pid_path = self.brain_path / "daemon" / "daemon.pid"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()))

        # 2. Setup Signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        # 3. Load Policy
        policy = self.policy_engine.load_policy()
        logger.info(f"Policy Loaded: Mode={policy.get('mode')}, Safety={policy.get('safety_level')}")

        # 4. Startup banner
        sched_status = self.scheduler.status()
        logger.info(
            f"Nucleus Daemon v2.0 — Project Purple 2\n"
            f"  Brain: {self.brain_path}\n"
            f"  PID: {os.getpid()}\n"
            f"  Jobs: {sched_status['total_jobs']} registered\n"
            f"  Cron: {'disabled' if self._no_cron else 'active'}\n"
            f"  Compound: {'disabled' if self._no_compound else 'idle-triggered'}"
        )

        # 5. Catch-up: run missed jobs from downtime
        if not self._no_cron:
            catchups = self.scheduler.catchup_jobs(datetime.now())
            if catchups:
                logger.info(f"Catch-up: {len(catchups)} jobs missed during downtime")
                for job in catchups[:3]:  # Max 3 catch-ups at boot
                    if self._check_requirements(job):
                        asyncio.create_task(self._run_job_safe(job))
                        await asyncio.sleep(5)  # Stagger

        # 6. Main Event Loop
        try:
            await self.main_loop()
        except asyncio.CancelledError:
            logger.info("Daemon cancelled.")
        except Exception as e:
            logger.exception(f"Daemon crashed: {e}")
        finally:
            await self.shutdown()

    async def main_loop(self):
        """The Core Preemptive Loop — 5-second tick."""
        logger.info("Daemon is active. Entering Main Loop.")
        tick_count = 0

        while self.running:
            tick_count += 1

            # ── Heartbeat (The Ambient Pulse) ──
            status = "busy" if self.orchestrator._active_missions else "idle"
            self.pulse.beat(status, len(self.orchestrator._active_missions))

            # Monitor Swarms
            active_count = len(self.orchestrator._active_missions)
            if active_count > 0:
                logger.debug(f"Active Swarms: {active_count}")

            # ── Scheduler tick — run due jobs ──
            if not self._no_cron:
                due_jobs = self.scheduler.tick(datetime.now())
                for job in due_jobs:
                    if self._check_requirements(job):
                        asyncio.create_task(self._run_job_safe(job))

            # ── Training Conductor check every ~5 min (60 ticks * 5s) ──
            if tick_count % 60 == 0:
                try:
                    from .archive_pipeline import ArchivePipeline
                    archive = ArchivePipeline(brain_path=self.brain_path)
                    t_status = archive.training_status()
                    na = t_status.get("next_action", {})
                    if na.get("priority") in ("critical", "high"):
                        logger.info(
                            f"Training Conductor [{na['priority'].upper()}]: "
                            f"{na['action']} — {na['reason']}"
                        )
                        signal_path = self.brain_path / "training" / "conductor_signal.json"
                        signal_path.parent.mkdir(parents=True, exist_ok=True)
                        signal_path.write_text(json.dumps({
                            "timestamp": datetime.now().isoformat(),
                            "action": na["action"],
                            "priority": na["priority"],
                            "reason": na["reason"],
                            "command": na.get("command"),
                            "sft_turns": t_status["sft"]["turns"],
                            "dpo_pairs": t_status["dpo"]["total"],
                            "cot_quality": t_status["cot"]["quality"],
                        }, indent=2))
                except Exception:
                    pass

            # ── Idle-triggered compound mode (every 60 ticks = 5 min) ──
            if tick_count % 60 == 0 and not self._no_compound and not self._compound_running:
                if self._should_auto_compound():
                    asyncio.create_task(self._auto_compound())

            # ── Persist scheduler state every ~1 min (12 ticks) ──
            if tick_count % 12 == 0 and not self._no_cron:
                self.scheduler.persist_state()

            # ── Track activity: missions running = not idle ──
            if self.orchestrator._active_missions:
                self._last_activity = datetime.now()

            await asyncio.sleep(5)

    def _should_auto_compound(self) -> bool:
        """Check if conditions are right for auto-compound mode."""
        now = datetime.now()

        # 1. Within compound window?
        start_h, end_h = self._compound_window
        if not (start_h <= now.hour < end_h):
            return False

        # 2. Idle long enough? (no active missions for threshold minutes)
        idle_minutes = (now - self._last_activity).total_seconds() / 60
        if idle_minutes < self._idle_threshold_minutes:
            return False

        # 3. No heavy job already running?
        if self.scheduler.has_running_heavy():
            return False

        # 4. Ollama available?
        if not _check_ollama():
            return False

        # 5. Kill switch (stop file)?
        stop_file = Path(self.brain_path).parent / "scripts" / "stop"
        if stop_file.exists():
            return False

        return True

    async def _auto_compound(self):
        """Auto-trigger compound mode when idle conditions are met."""
        from .jobs import driver_job

        self._compound_running = True
        logger.info("[COMPOUND] Auto-triggering compound mode (idle + within window)")
        self.notifier.send("Compound mode", "Auto-starting compound loop", "info")

        try:
            result = await asyncio.wait_for(
                driver_job.run_compound(rounds=5),
                timeout=7200,  # 2 hour hard limit
            )
            ok = result.get("ok", False) if isinstance(result, dict) else False
            if ok:
                logger.info("[COMPOUND] Auto-compound completed successfully")
            else:
                logger.warning(f"[COMPOUND] Auto-compound failed: {result.get('error', 'unknown')}")
        except asyncio.TimeoutError:
            logger.warning("[COMPOUND] Auto-compound timed out after 2 hours")
        except Exception as e:
            logger.error(f"[COMPOUND] Auto-compound error: {e}")
        finally:
            self._compound_running = False

    async def shutdown(self):
        """Graceful Shutdown"""
        if not self.running:
            return

        logger.info("Shutdown initiated...")
        self.running = False

        # Persist scheduler state
        try:
            self.scheduler.persist_state()
        except Exception:
            pass

        # Write stop file for any running driver
        stop_file = Path(self.brain_path).parent / "scripts" / "stop"
        try:
            stop_file.write_text(str(os.getpid()))
        except Exception:
            pass

        # Wait for running jobs to finish (up to 30s)
        self.job_pool.shutdown(wait=True, cancel_futures=False)

        # Clean stop file
        try:
            stop_file.unlink(missing_ok=True)
        except Exception:
            pass

        # Clean PID file
        pid_path = self.brain_path / "daemon" / "daemon.pid"
        try:
            pid_path.unlink(missing_ok=True)
        except Exception:
            pass

        # Release resources
        if self.lock:
            self.lock.release()
            logger.info("BrainLock Released.")

        logger.info("Daemon Stopped.")
        sys.exit(0)

    def get_status(self) -> dict:
        """Return daemon status for `nucleus status --daemon`."""
        uptime = (datetime.now() - self._start_time).total_seconds()
        return {
            "pid": os.getpid(),
            "uptime_seconds": int(uptime),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            "brain_path": str(self.brain_path),
            "running": self.running,
            "scheduler": self.scheduler.status(),
            "compound_running": self._compound_running,
            "cron_active": not self._no_cron,
        }


def run_daemon(no_compound: bool = False, no_cron: bool = False):
    """Entry point for the daemon service."""
    brain_path_str = os.environ.get("NUCLEUS_BRAIN_PATH")
    if not brain_path_str:
        # Dev fallback
        brain_path = Path.cwd() / ".brain"
    else:
        brain_path = Path(brain_path_str)

    daemon = DaemonManager(brain_path, no_compound=no_compound, no_cron=no_cron)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        pass  # Handled in signal handler


if __name__ == "__main__":
    run_daemon()
