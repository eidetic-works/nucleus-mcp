"""Test executor crash recovery in the secretary daemon.

SPEC.md:L8 — Mark IN_PROGRESS tasks as FAILED if the executor dies
mid-task. A task is stale when BOTH:
  (a) its claimed_at timestamp is older than 30 minutes, AND
  (b) the claiming process (PID derived from claimed_by) is dead.

Covers the required cases:
  1. stale task (dead executor, old claim) → reaped / marked FAILED
  2. alive task (live executor, old claim)  → NOT reaped

Plus regression guards for the age threshold and PID extraction so the
reaper never fires on a fresh claim or an agent_id without a PID.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Repo root (ai-mvp-backend) — the secretary's _task_ops imports from
# <repo_root>/mcp-server-nucleus/src, so the config needs the real root.
REPO_ROOT = Path(__file__).resolve().parents[3]

SRC_ROOT = REPO_ROOT / "mcp-server-nucleus" / "src"


def _ensure_src_on_path() -> None:
    src = str(SRC_ROOT)
    if src not in os.sys.path:
        os.sys.path.insert(0, src)


_ensure_src_on_path()


from mcp_server_nucleus.runtime import task_ops  # noqa: E402
from mcp_server_nucleus.runtime.db import get_storage_backend  # noqa: E402
from mcp_server_nucleus.runtime.lane.config import LaneConfig  # noqa: E402
from mcp_server_nucleus.runtime.lane.secretary_daemon import SecretaryDaemon  # noqa: E402


def _iso(dt: datetime) -> str:
    """ISO-8601 string with timezone, the shape claim_task_atomic writes."""
    return dt.isoformat()


def _make_secretary(brain_path: Path) -> SecretaryDaemon:
    config = LaneConfig(
        repo_root=REPO_ROOT,
        brain_path=brain_path,
        spec_path=REPO_ROOT / "SPEC.md",
        role="lane-g1",
        source="lane-control",
    )
    return SecretaryDaemon(config=config, poll_interval=1, verify_only=True)


def _add_in_progress_task(
    brain_path: Path,
    task_id: str,
    claimed_by: str,
    claimed_at: datetime,
) -> dict:
    """Create a task and force it into the IN_PROGRESS / claimed state.

    Uses the storage backend directly so we can set claimed_by to a PID
    string and claimed_at to an arbitrary timestamp (the executor's
    _claim_task would set claimed_by=agent_id, not a PID).
    """
    add_result = task_ops._add_task(
        description=f"crash-recovery test task {task_id}",
        priority=2,
        task_id=task_id,
        source="test",
        skip_dep_check=True,
    )
    assert add_result.get("success"), f"failed to add task: {add_result}"

    storage = get_storage_backend(brain_path)
    storage.update_task(task_id, {
        "status": "IN_PROGRESS",
        "claimed_by": claimed_by,
        "claimed_at": _iso(claimed_at),
    })
    task = task_ops._get_task(task_id)
    assert task is not None, "task disappeared after claim setup"
    return task


@pytest.fixture
def secretary(monkeypatch, tmp_path):
    """Isolated brain + secretary for each test."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    for sub in ("state", "relay", "logs", "engrams", "ledger", "sessions", "memory"):
        (brain / sub).mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return _make_secretary(brain)


class TestReapStaleTasks:
    """SPEC.md:L8 — executor crash recovery via _reap_stale_tasks."""

    def test_stale_task_with_dead_executor_is_reaped(self, secretary, tmp_path):
        """A task claimed >30 min ago by a now-dead PID → FAILED."""
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        dead_pid = 999_999  # effectively guaranteed not to exist
        old_claim = datetime.now(timezone.utc) - timedelta(minutes=45)

        task = _add_in_progress_task(
            brain, "crash-dead-1", str(dead_pid), old_claim
        )
        assert task["status"] == "IN_PROGRESS"

        reaped = secretary._reap_stale_tasks()

        assert reaped == 1, "expected exactly one task reaped"
        after = task_ops._get_task("crash-dead-1")
        assert after["status"] == "FAILED", (
            f"stale task should be FAILED, got {after['status']}"
        )
        note = after.get("verification_note", "")
        assert "died mid-task" in note, f"note should explain executor death: {note}"
        assert str(dead_pid) in note, f"note should name the dead pid: {note}"
        assert after.get("verified_by") == "secretary"

    def test_alive_executor_task_is_not_reaped(self, secretary):
        """A task claimed >30 min ago by a LIVE pid (this process) → stays IN_PROGRESS."""
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        live_pid = os.getpid()
        old_claim = datetime.now(timezone.utc) - timedelta(minutes=45)

        task = _add_in_progress_task(
            brain, "crash-alive-1", str(live_pid), old_claim
        )
        assert task["status"] == "IN_PROGRESS"

        reaped = secretary._reap_stale_tasks()

        assert reaped == 0, "live executor must not be reaped"
        after = task_ops._get_task("crash-alive-1")
        assert after["status"] == "IN_PROGRESS", (
            f"alive-executor task should stay IN_PROGRESS, got {after['status']}"
        )

    def test_recent_claim_not_reaped_even_if_dead(self, secretary):
        """A task claimed <30 min ago is NOT stale, regardless of executor liveness."""
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        dead_pid = 999_998
        fresh_claim = datetime.now(timezone.utc) - timedelta(minutes=5)

        _add_in_progress_task(brain, "crash-fresh-1", str(dead_pid), fresh_claim)

        reaped = secretary._reap_stale_tasks()

        assert reaped == 0, "fresh claim must not be reaped (age gate)"
        after = task_ops._get_task("crash-fresh-1")
        assert after["status"] == "IN_PROGRESS"

    def test_agent_id_without_pid_is_skipped(self, secretary):
        """claimed_by with no numeric PID (e.g. 'lane-g1_devin') → cannot probe, skip."""
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        old_claim = datetime.now(timezone.utc) - timedelta(minutes=60)

        _add_in_progress_task(
            brain, "crash-nopid-1", "lane-g1_devin", old_claim
        )

        reaped = secretary._reap_stale_tasks()

        assert reaped == 0, "task without a probeable PID must be skipped"
        after = task_ops._get_task("crash-nopid-1")
        assert after["status"] == "IN_PROGRESS"

    def test_only_in_progress_tasks_considered(self, secretary):
        """A DONE task with a dead pid + old claim is left alone."""
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        dead_pid = 999_997
        old_claim = datetime.now(timezone.utc) - timedelta(minutes=60)

        _add_in_progress_task(brain, "crash-done-1", str(dead_pid), old_claim)
        # Flip it to DONE — reaper must not touch terminal states.
        task_ops._update_task("crash-done-1", {"status": "DONE"})

        reaped = secretary._reap_stale_tasks()

        assert reaped == 0
        after = task_ops._get_task("crash-done-1")
        assert after["status"] == "DONE"


class TestPidExtraction:
    """Unit tests for the _extract_pid helper."""

    @pytest.mark.parametrize("raw,expected", [
        ("12345", 12345),
        ("0", 0),
        ("agent:12345", 12345),
        ("lane-g1_devin-777", 777),
        ("executor_4242", 4242),
        ("lane-g1_devin", None),   # no numeric tail
        ("", None),
        (None, None),
        ("not-a-pid", None),
    ])
    def test_extract_pid_shapes(self, raw, expected):
        assert SecretaryDaemon._extract_pid(raw) == expected


class TestIsProcessAlive:
    """Unit tests for the _is_process_alive helper (os.kill(pid, 0))."""

    def test_current_process_is_alive(self):
        assert SecretaryDaemon._is_process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_dead(self):
        # PID 1 on most test hosts is init/launchd which we may not be
        # allowed to signal; use a very high PID that won't exist.
        assert SecretaryDaemon._is_process_alive(999_999) is False
