"""The secretary's stale-task reaper must actually be able to fire.

THE INCIDENT (2026-08-19): a lane restart left 2 tasks IN_PROGRESS claimed by
dead PIDs. The lane wedged for 40 minutes — 2 IN_PROGRESS / 31 PENDING, never
moving — while the secretary ran `_reap_stale_tasks()` every cycle and skipped
both tasks on every pass.

Cause: the reaper derives a PID from `claimed_by` to probe liveness, and
returns None for a bare name. Its own docstring names the production format
("lane-g1_devin") as the None case. Executors passed exactly that, so the
reaper could never reap anything. A safety net dead by construction, for its
only real input.

Compounding it: the July ticket `bug_stale_claim_cleanup` was CLOSED with the
note "stale claims reset on restart naturally since claimed_by is in-memory
state that dies with the process." That is false — `claimed_by` and
`claimed_at` are persisted to the task store, as `nucleus task list` shows.
The primary mechanism and its documented fallback were both broken at once.

Each test states its failure direction.
"""

import os
from pathlib import Path

from mcp_server_nucleus.runtime.lane.secretary_daemon import SecretaryDaemon


class TestExtractPid:
    """The parser that decides whether the reaper can act at all."""

    def test_bare_lane_name_yields_no_pid(self):
        """The ORIGINAL BUG, pinned so it cannot silently return. A bare lane
        name is unprobeable — this is correct parser behaviour, and it is
        exactly why executors must no longer pass one."""
        assert SecretaryDaemon._extract_pid("lane_devin") is None
        assert SecretaryDaemon._extract_pid("lane-g1_devin") is None

    def test_pid_suffixed_agent_id_parses(self):
        """THE FIX: the format executors now emit must yield the real PID."""
        assert SecretaryDaemon._extract_pid("lane_devin:14332") == 14332
        assert SecretaryDaemon._extract_pid("lane_agy:99") == 99

    def test_empty_and_none_are_safe(self):
        """OPPOSED: malformed input must not raise inside a reaper loop that
        runs every cycle — a crash there silently stops all reaping."""
        assert SecretaryDaemon._extract_pid(None) is None
        assert SecretaryDaemon._extract_pid("") is None
        assert SecretaryDaemon._extract_pid("   ") is None


class TestProcessLiveness:
    """The probe the reaper uses to decide dead vs alive."""

    def test_own_pid_reads_alive(self):
        """POSITIVE: a real, running process must read alive — otherwise the
        reaper would reap tasks from HEALTHY executors mid-work, which is
        worse than not reaping at all."""
        assert SecretaryDaemon._is_process_alive(os.getpid()) is True

    def test_implausible_pid_reads_dead(self):
        """OPPOSED: a probe that always says 'alive' can never reap. Use a PID
        far above any plausible live one."""
        assert SecretaryDaemon._is_process_alive(4_194_303) is False


class TestExecutorAgentIdCarriesPid:
    """The end-to-end property that makes the reaper reachable at all."""

    def test_executor_agent_id_is_probeable(self):
        """THE LOAD-BEARING ONE. If an executor's agent_id ever stops carrying
        a parseable PID, the reaper silently reverts to skipping every task and
        the lane can wedge forever on any restart — with no error anywhere."""
        import tempfile
        from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
        from mcp_server_nucleus.runtime.lane.config import LaneConfig

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = LaneConfig(repo_root=root, brain_path=root / ".brain",
                             spec_path=root / "SPEC.md")
            d = ExecutorDaemon(config=cfg, agent_id="lane_devin",
                               lane="lane_devin", vendor="devin")
            pid = SecretaryDaemon._extract_pid(d.agent_id)
            assert pid is not None, (
                f"agent_id {d.agent_id!r} yields no PID — the reaper is dead "
                f"by construction again"
            )
            assert pid == os.getpid()
            assert d.lane_name == "lane_devin", "stable lane identity must survive"
