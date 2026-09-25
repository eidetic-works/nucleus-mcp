"""Test executor max-retry counter — escalate after 3 failures (#74).

SPEC.md task fix_issue_74 — Relay wishlist anti-stall.

The executor daemon must NOT retry a failing task forever. After
``max_retries`` (default 3, configurable via LaneConfig) failed attempts,
the task's status is set to ESCALATED (terminal — surfaced to the operator)
instead of being reset to PENDING for another retry loop.

This test mocks the executor's LLM dispatch to fail deterministically and
verifies:
  1. After 3 failures the task status becomes ESCALATED (not PENDING).
  2. retry_count is persisted in the task store and increments on each
     failure (durable across daemon restarts).
  3. The escalation_reason explains why the task was escalated.
  4. A configurable max_retries value is honored (e.g. max_retries=2
     escalates after 2 failures, not 3).
  5. A task that succeeds before hitting the limit is marked DONE and
     retry_count is reset to 0 (regression guard).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Repo root (ai-mvp-backend) — executor imports from
# <repo_root>/mcp-server-nucleus/src, so the config needs the real root.
REPO_ROOT = Path(__file__).resolve().parents[3]

SRC_ROOT = REPO_ROOT / "mcp-server-nucleus" / "src"


def _ensure_src_on_path() -> None:
    src = str(SRC_ROOT)
    if src not in os.sys.path:
        os.sys.path.insert(0, src)


_ensure_src_on_path()


from mcp_server_nucleus.runtime import task_ops  # noqa: E402
from mcp_server_nucleus.runtime.lane.config import LaneConfig  # noqa: E402
from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon  # noqa: E402


def _make_executor(brain_path: Path, max_retries: int = 3) -> ExecutorDaemon:
    """Build an ExecutorDaemon pointed at an isolated brain."""
    config = LaneConfig(
        repo_root=REPO_ROOT,
        brain_path=brain_path,
        spec_path=REPO_ROOT / "SPEC.md",
        role="lane-g1",
        source="test",
        max_retries=max_retries,
    )
    return ExecutorDaemon(
        config=config,
        agent_id="test-executor-1",
        lane="lane-g1",
        vendor="devin",
        poll_interval=1,
        max_retries=max_retries,
    )


def _add_pending_task(task_id: str, source: str = "test") -> dict:
    """Create a PENDING task in the store."""
    result = task_ops._add_task(
        description=f"max-retry test task {task_id}",
        priority=2,
        task_id=task_id,
        source=source,
        skip_dep_check=True,
    )
    assert result.get("success"), f"failed to add task: {result}"
    return result["task"]


@pytest.fixture
def executor(monkeypatch, tmp_path):
    """Isolated brain + executor for each test."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    for sub in ("state", "relay", "logs", "engrams", "ledger", "sessions", "memory"):
        (brain / sub).mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return _make_executor(brain)


class TestMaxRetryEscalation:
    """SPEC.md fix_issue_74 — escalate after max_retries failures."""

    def test_escalates_after_three_failures(self, executor):
        """Mock executor to fail 3x → status becomes ESCALATED.

        With the PAUSE-and-ask behavior (retry == max_retries - 1 pauses),
        the task PAUSES after 2 failures. To reach ESCALATED, the principal
        must reset it to PENDING, then the 3rd failure escalates.
        """
        _add_pending_task("retry-3x-1")

        # Force _execute_llm to always fail.
        call_count = {"n": 0}

        def _fail_execute(task):
            call_count["n"] += 1
            return {"status": "error", "rc": 1, "result": "boom"}

        executor._execute_llm = _fail_execute  # type: ignore[assignment]

        # Drive 2 process cycles → PAUSED after 2nd failure.
        for i in range(2):
            task = executor._find_claimable_task()
            if task is None:
                break
            executor._process_task(task)

        after_pause = task_ops._get_task("retry-3x-1")
        assert after_pause["status"] == "PAUSED", (
            f"expected PAUSED after 2 failures, got {after_pause['status']}"
        )

        # Principal resets to PENDING for the 3rd attempt.
        task_ops._update_task("retry-3x-1", {"status": "PENDING", "pause_reason": None, "escalation_reason": None})
        task = executor._find_claimable_task()
        assert task is not None, "task should be claimable after reset"
        executor._process_task(task)

        after = task_ops._get_task("retry-3x-1")
        assert after is not None, "task vanished"
        assert after["status"] == "ESCALATED", (
            f"expected ESCALATED after 3 failures, got {after['status']}"
        )
        # retry_count must reflect the 3 attempts
        assert int(after.get("retry_count", 0)) == 3, (
            f"expected retry_count=3, got {after.get('retry_count')}"
        )
        # escalation_reason must explain why
        reason = after.get("escalation_reason") or ""
        assert "Max retries" in reason, (
            f"escalation_reason should mention max retries: {reason!r}"
        )
        assert "3" in reason, f"escalation_reason should mention the count: {reason!r}"

    def test_retry_count_increments_per_failure(self, executor):
        """Each failure increments the persisted retry_count by 1."""
        _add_pending_task("retry-increment-1")

        def _fail_execute(task):
            return {"status": "error", "rc": 1, "result": "fail"}

        executor._execute_llm = _fail_execute  # type: ignore[assignment]

        # First failure
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)
        after_1 = task_ops._get_task("retry-increment-1")
        assert after_1["status"] == "PENDING", (
            f"after 1 failure should be PENDING (retry pending), got {after_1['status']}"
        )
        assert int(after_1.get("retry_count", 0)) == 1, (
            f"after 1 failure retry_count should be 1, got {after_1.get('retry_count')}"
        )

        # Second failure → PAUSED (retry == max_retries - 1 triggers pause-and-ask)
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)
        after_2 = task_ops._get_task("retry-increment-1")
        assert after_2["status"] == "PAUSED", (
            f"after 2 failures should be PAUSED (pause-and-ask), got {after_2['status']}"
        )
        assert int(after_2.get("retry_count", 0)) == 2, (
            f"after 2 failures retry_count should be 2, got {after_2.get('retry_count')}"
        )

    def test_retry_count_survives_daemon_restart(self, executor, monkeypatch, tmp_path):
        """retry_count is persisted in the task store, so a fresh daemon
        instance picks up where the previous one left off (no reset to 0)."""
        _add_pending_task("retry-restart-1")

        def _fail_execute(task):
            return {"status": "error", "rc": 1, "result": "fail"}

        executor._execute_llm = _fail_execute  # type: ignore[assignment]

        # First daemon: fail twice → PAUSED after 2nd failure.
        for _ in range(2):
            task = executor._find_claimable_task()
            assert task is not None
            executor._process_task(task)

        mid = task_ops._get_task("retry-restart-1")
        assert int(mid.get("retry_count", 0)) == 2
        assert mid["status"] == "PAUSED", (
            f"expected PAUSED after 2 failures, got {mid['status']}"
        )

        # Principal resets to PENDING for the 3rd attempt.
        task_ops._update_task("retry-restart-1", {"status": "PENDING", "pause_reason": None, "escalation_reason": None})

        # Simulate a daemon restart — new instance, same brain.
        brain = Path(os.environ["NUCLEUS_BRAIN_PATH"])
        executor2 = _make_executor(brain)
        executor2._execute_llm = _fail_execute  # type: ignore[assignment]

        # The new daemon should see retry_count=2 already persisted, so one
        # more failure (the 3rd) trips the limit and escalates.
        task = executor2._find_claimable_task()
        assert task is not None, "task should still be claimable after reset"
        executor2._process_task(task)

        after = task_ops._get_task("retry-restart-1")
        assert after["status"] == "ESCALATED", (
            f"expected ESCALATED after 3rd failure post-restart, got {after['status']}"
        )
        assert int(after.get("retry_count", 0)) == 3, (
            f"expected retry_count=3 post-restart, got {after.get('retry_count')}"
        )

    def test_configurable_max_retries_honored(self, monkeypatch, tmp_path):
        """max_retries=2 → PAUSE after 1 failure (second-to-last), then
        ESCALATE after 2nd failure (post-reset)."""
        brain = tmp_path / ".brain"
        brain.mkdir(parents=True, exist_ok=True)
        for sub in ("state", "relay", "logs", "engrams", "ledger", "sessions", "memory"):
            (brain / sub).mkdir(exist_ok=True)
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        executor = _make_executor(brain, max_retries=2)
        _add_pending_task("retry-cfg-2-1")

        def _fail_execute(task):
            return {"status": "error", "rc": 1, "result": "fail"}

        executor._execute_llm = _fail_execute  # type: ignore[assignment]

        # 1st failure → PAUSED (retry == max_retries - 1 == 1)
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)

        after_pause = task_ops._get_task("retry-cfg-2-1")
        assert after_pause["status"] == "PAUSED", (
            f"max_retries=2 should PAUSE after 1 failure, got {after_pause['status']}"
        )
        assert int(after_pause.get("retry_count", 0)) == 1

        # Reset and 2nd failure → ESCALATED
        task_ops._update_task("retry-cfg-2-1", {"status": "PENDING", "pause_reason": None, "escalation_reason": None})
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)

        after = task_ops._get_task("retry-cfg-2-1")
        assert after["status"] == "ESCALATED", (
            f"max_retries=2 should escalate after 2 failures, got {after['status']}"
        )
        assert int(after.get("retry_count", 0)) == 2
        reason = after.get("escalation_reason") or ""
        assert "2" in reason, (
            f"escalation_reason should mention max_retries=2: {reason!r}"
        )

    def test_success_before_limit_resets_retry_count(self, executor):
        """A task that fails once then succeeds is marked DONE and
        retry_count is reset to 0 (no carryover to a future re-claim)."""
        _add_pending_task("retry-success-1")

        state = {"attempts": 0}

        def _flaky_execute(task):
            state["attempts"] += 1
            if state["attempts"] == 1:
                return {"status": "error", "rc": 1, "result": "first try fails"}
            # Second attempt: fake a successful commit.
            return {
                "status": "ok",
                "rc": 0,
                "result": "commit 0123456789abcdef0123456789abcdef01234567 done",
            }

        executor._execute_llm = _flaky_execute  # type: ignore[assignment]
        # Bypass diff verification (we're not making a real commit).
        executor._verify_diff_content = lambda sha: {  # type: ignore[assignment]
            "pass": True,
            "real_lines": 10,
            "insertions": 12,
            "files_changed": ["fake.py"],
        }
        # Bypass the [DONE] relay post (no real secretary in test brain).
        executor._post_done_relay = lambda tid, sha: None  # type: ignore[assignment]

        # First attempt: fails → PENDING, retry_count=1.
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)
        after_1 = task_ops._get_task("retry-success-1")
        assert after_1["status"] == "PENDING"
        assert int(after_1.get("retry_count", 0)) == 1

        # Second attempt: succeeds → DONE, retry_count=0.
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)
        after_2 = task_ops._get_task("retry-success-1")
        assert after_2["status"] == "DONE", (
            f"expected DONE after successful retry, got {after_2['status']}"
        )
        assert int(after_2.get("retry_count", 0)) == 0, (
            f"retry_count should reset to 0 on DONE, got {after_2.get('retry_count')}"
        )
        assert after_2.get("escalation_reason") in (None, "", "None"), (
            f"DONE task should have no escalation_reason, got {after_2.get('escalation_reason')!r}"
        )

    def test_escalated_task_not_reclaimed(self, executor):
        """Once ESCALATED, the task is terminal — _find_claimable_task
        skips it (no infinite retry loop)."""
        _add_pending_task("retry-terminal-1")

        def _fail_execute(task):
            return {"status": "error", "rc": 1, "result": "fail"}

        executor._execute_llm = _fail_execute  # type: ignore[assignment]

        # Drive to PAUSED (2 failures with max_retries=3).
        for _ in range(2):
            task = executor._find_claimable_task()
            if task is None:
                break
            executor._process_task(task)

        # Reset and drive to ESCALATED (3rd failure).
        task_ops._update_task("retry-terminal-1", {"status": "PENDING", "pause_reason": None, "escalation_reason": None})
        task = executor._find_claimable_task()
        assert task is not None
        executor._process_task(task)

        after = task_ops._get_task("retry-terminal-1")
        assert after["status"] == "ESCALATED"
        # _find_claimable_task must not return an ESCALATED task.
        assert executor._find_claimable_task() is None, (
            "ESCALATED task must not be reclaimable — that would defeat the anti-stall gate"
        )
