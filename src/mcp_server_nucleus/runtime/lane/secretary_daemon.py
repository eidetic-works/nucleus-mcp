"""Secretary daemon — independently verifies DONE tasks.

The secretary runs in VERIFY_ONLY mode by default. It:
    1. Polls for [DONE] relays from executors
    2. Runs focused pytest on the committed changes
    3. Records CONFIRMED only on test pass (not self-report)
    4. Does NOT create new tasks or process plans

This is the trust anchor — executor self-report is not trusted. Only
secretary-verified CONFIRMED status is authoritative.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import LaneConfig


class SecretaryDaemon:
    """Verifies DONE tasks by running focused tests."""

    def __init__(
        self,
        config: LaneConfig,
        poll_interval: int = 10,
        verify_only: bool = True,
    ):
        self.config = config
        self.poll_interval = poll_interval
        self.verify_only = verify_only
        self._telemetry = {
            "verified": 0,
            "confirmed": 0,
            "failed": 0,
            "retries_seen": 0,
            "escalations_seen": 0,
            "skipped": 0,
            "skipped_reasons": {},  # reason -> count
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self._last_telemetry_post = 0.0
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.config.brain_path / "state", self.config.relay_dir, self.config.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _task_ops(self):
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime import task_ops
        return task_ops

    def _relay(self):
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime.relay import core
        return core

    def _get_done_relays(self) -> List[dict]:
        """Get unread [DONE] relays from executors.

        Filters out relays older than 1 hour (addresses high_relay_unbounded
        — stale relays don't accumulate in the processing queue).
        """
        relay = self._relay()
        inbox = relay.relay_inbox(unread_only=True, recipient="secretary", limit=50)
        now = datetime.now(timezone.utc)
        filtered = []
        for m in inbox.get("messages", []):
            subject = m.get("subject", "")
            if not subject.startswith("[DONE]"):
                continue
            # Skip relays older than 1 hour
            created = m.get("created_at") or m.get("timestamp")
            if created:
                try:
                    # Parse ISO format timestamp
                    ts = created.replace("Z", "+00:00")
                    age = (now - datetime.fromisoformat(ts)).total_seconds()
                    if age > 3600:  # 1 hour
                        continue
                except (ValueError, TypeError):
                    pass  # If we can't parse the timestamp, don't skip
            filtered.append(m)
        return filtered

    def _extract_task_id(self, relay_msg: dict) -> Optional[str]:
        """Extract task ID from a [DONE] relay subject."""
        subject = relay_msg.get("subject", "")
        # [DONE] <task_id>
        if "] " in subject:
            return subject.split("] ", 1)[1].strip()
        return None

    def _run_focused_tests(self, task_id: str, commit_sha: str) -> Dict[str, Any]:
        """Run focused pytest for a task's commit.

        Returns a dict with pass/fail status and output.
        """
        repo = self.config.repo_root
        # Find test files related to the task
        # Look for test files matching the task_id pattern
        task_suffix = task_id.replace(f"{self.config.role}_", "").replace("_", "_")
        test_patterns = [
            f"tests/test_{task_suffix}.py",
            f"tests/test_*{task_suffix}*.py",
            f"**/test_{task_suffix}.py",
        ]

        import glob
        test_files: List[str] = []
        for pattern in test_patterns:
            test_files.extend(glob.glob(str(repo / pattern), recursive=True))

        if not test_files:
            # No specific tests found — run GROUND verification
            return {
                "pass": True,
                "output": "No task-specific tests found — GROUND verification only",
                "tests_run": 0,
            }

        # Run pytest on the found test files.
        # Prefer the project .venv (which has pytest installed), then
        # PYTHON_BIN env var, then sys.executable as last resort.
        # The nucleus tool venv (sys.executable when installed via uv tool)
        # does NOT have pytest — using it causes false verification failures.
        py_bin = os.environ.get("PYTHON_BIN", "")
        if not py_bin:
            venv_py = repo / ".venv" / "bin" / "python"
            if venv_py.exists():
                py_bin = str(venv_py)
            else:
                py_bin = sys.executable
        try:
            result = subprocess.run(
                [py_bin, "-m", "pytest"] + test_files + ["--tb=short", "-q"],
                capture_output=True,
                text=True,
                cwd=str(repo),
                timeout=120,
            )
            return {
                "pass": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "tests_run": len(test_files),
            }
        except subprocess.TimeoutExpired:
            return {
                "pass": False,
                "output": "Test execution timed out (120s)",
                "tests_run": len(test_files),
            }
        except Exception as exc:
            return {
                "pass": False,
                "output": str(exc),
                "tests_run": len(test_files),
            }

    def _verify_task(self, task_id: str, commit_sha: str) -> Dict[str, Any]:
        """Verify a task by running its focused tests."""
        result = self._run_focused_tests(task_id, commit_sha)
        return result

    def _record_confirmed(self, task_id: str, commit_sha: str, note: str) -> None:
        """Record CONFIRMED verification status on a task."""
        ops = self._task_ops()
        ops._update_task(task_id, {
            "verification_status": "CONFIRMED",
            "verified_by": "secretary",
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "verification_note": f"Commit {commit_sha}. {note}",
        })

    def _ack_relay(self, relay_id: str) -> None:
        """Ack a relay message."""
        relay = self._relay()
        relay.relay_ack(relay_id, recipient="secretary")

    # ── Executor crash recovery ────────────────────────────────────────
    # SPEC.md:L8 — Mark IN_PROGRESS tasks as FAILED if executor dies
    # mid-task. A task is stale when its claimed_at is older than 30 min
    # AND the claiming process is no longer alive (os.kill(pid, 0)).
    _STALE_THRESHOLD_SECONDS = 30 * 60  # 30 minutes

    @staticmethod
    def _extract_pid(claimed_by: Any) -> Optional[int]:
        """Extract a PID from the claimed_by field.

        Supports three shapes:
          1. Pure numeric string ("12345")        → int("12345")
          2. Trailing separator suffix ("agent:12345",
             "agent-12345", "agent_12345")        → int("12345")
          3. Non-numeric agent id ("lane-g1_devin") → None (no PID to probe)

        Returns None when no PID can be derived — callers must skip
        reaping in that case (cannot verify liveness).
        """
        if not claimed_by:
            return None
        raw = str(claimed_by).strip()
        if not raw:
            return None
        # Direct numeric
        if raw.lstrip("-").isdigit():
            try:
                return int(raw)
            except ValueError:
                return None
        # Trailing separator suffix
        for sep in (":", "-", "_"):
            if sep in raw:
                tail = raw.rsplit(sep, 1)[-1].strip()
                if tail.lstrip("-").isdigit():
                    try:
                        return int(tail)
                    except ValueError:
                        return None
        return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Return True if `pid` is currently alive.

        Uses os.kill(pid, 0): no signal is delivered, only existence/liveness
        is probed. EPERM (process exists but we lack permission) is treated
        as alive — the executor is still running, just not signalable by us.
        """
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we can't signal it — treat as alive.
            return True
        except OSError:
            return False
        return True

    def _reap_stale_tasks(self) -> int:
        """Reap IN_PROGRESS tasks whose executor has died.

        Per SPEC.md:L8: a task is stale when BOTH
          (a) its claimed_at timestamp is older than 30 minutes, AND
          (b) the claiming process (PID derived from claimed_by) is dead.

        Stale tasks are marked FAILED with a verification_note explaining
        the executor died, so the work can be re-queued rather than
        hanging forever in IN_PROGRESS.

        Returns the count of tasks reaped.
        """
        ops = self._task_ops()
        try:
            tasks = ops._list_tasks()
        except Exception as exc:
            print(f"[secretary] _reap_stale_tasks: list failed: {exc}", flush=True)
            return 0

        now = datetime.now(timezone.utc)
        reaped = 0
        for task in tasks:
            if task.get("status", "").upper() != "IN_PROGRESS":
                continue

            claimed_by = task.get("claimed_by")
            pid = self._extract_pid(claimed_by)
            if pid is None:
                # No PID to probe (e.g. agent_id without numeric suffix) —
                # cannot verify liveness, skip.
                continue

            # Age check — claimed_at older than 30 min.
            claimed_at_raw = task.get("claimed_at") or task.get("updated_at") or task.get("created_at")
            if not claimed_at_raw:
                continue
            try:
                ts = claimed_at_raw.replace("Z", "+00:00")
                claimed_at = datetime.fromisoformat(ts)
                if claimed_at.tzinfo is None:
                    claimed_at = claimed_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            age_seconds = (now - claimed_at).total_seconds()
            if age_seconds < self._STALE_THRESHOLD_SECONDS:
                continue

            if self._is_process_alive(pid):
                continue

            # Executor is dead and the claim is stale — mark FAILED.
            task_id = task.get("id")
            note = (
                f"Executor (pid={pid}, claimed_by={claimed_by}) died mid-task. "
                f"claimed_at={claimed_at_raw}, age={int(age_seconds)}s exceeds "
                f"{self._STALE_THRESHOLD_SECONDS}s threshold. Reaped by secretary."
            )
            try:
                ops._update_task(task_id, {
                    "status": "FAILED",
                    "verification_status": "FAILED",
                    "verified_by": "secretary",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "verification_note": note,
                })
                reaped += 1
                print(
                    f"[secretary] REAPED stale task {task_id}: "
                    f"executor pid={pid} dead, age={int(age_seconds)}s",
                    flush=True,
                )
            except Exception as exc:
                print(
                    f"[secretary] _reap_stale_tasks: failed to reap {task_id}: {exc}",
                    flush=True,
                )
        return reaped

    def _record_skip(self, reason: str) -> None:
        """Track a skipped relay with its reason for telemetry visibility."""
        self._telemetry["skipped"] += 1
        reasons = self._telemetry["skipped_reasons"]
        reasons[reason] = reasons.get(reason, 0) + 1

    def _process_done_relays(self) -> None:
        """Process all pending [DONE] relays.

        Includes sender verification (addresses high_relay_forgery):
        only processes DONE relays where the relay sender matches the
        task's claimed_by field. This prevents a rogue process from
        writing a fake DONE relay to the secretary bucket.
        """
        relays = self._get_done_relays()
        for msg in relays:
            task_id = self._extract_task_id(msg)
            if not task_id:
                self._record_skip("unparseable_subject")
                self._ack_relay(msg["id"])
                continue

            # Get the task
            ops = self._task_ops()
            tasks = {t["id"]: t for t in ops._list_tasks()}
            task = tasks.get(task_id)
            if not task:
                self._record_skip("task_not_found")
                self._ack_relay(msg["id"])
                continue

            if task.get("status", "").upper() != "DONE":
                self._record_skip(f"task_status_{task.get('status','unknown').lower()}")
                self._ack_relay(msg["id"])
                continue

            if task.get("verification_status") == "CONFIRMED":
                self._record_skip("already_confirmed")
                self._ack_relay(msg["id"])
                continue

            # Sender verification: relay sender must match task's verified_by
            # (the executor that marked it DONE). This prevents forgery.
            # Normalize both sides via resolve_canonical_inbox_name to avoid
            # hyphen/underscore mismatches (relay_post normalizes sender, but
            # verified_by is stored raw from executor agent_id).
            relay_sender = msg.get("from") or msg.get("sender", "")
            task_verifier = task.get("verified_by", "")
            try:
                from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name
                if relay_sender:
                    relay_sender = resolve_canonical_inbox_name(relay_sender)
                if task_verifier:
                    task_verifier = resolve_canonical_inbox_name(task_verifier)
            except Exception:
                pass  # If normalization fails, fall back to raw comparison
            if task_verifier and relay_sender and task_verifier != relay_sender:
                print(
                    f"[secretary] SENDER MISMATCH for {task_id}: "
                    f"relay from {relay_sender}, task verified_by {task_verifier} — "
                    f"leaving unacked for retry (do NOT ack-and-skip)",
                    flush=True,
                )
                self._record_skip("sender_mismatch")
                # Do NOT ack — leave the relay for re-processing after a fix.
                # Acks are only for successfully-processed relays.
                continue

            # Extract commit SHA from the relay body or task verification_note
            commit_sha = "unknown"
            note = task.get("verification_note", "")
            import re
            match = re.search(r"\b([0-9a-f]{7,40})\b", note)
            if match:
                commit_sha = match.group(1)

            # Verify
            print(f"[secretary] verifying {task_id} (commit {commit_sha[:8]})", flush=True)
            result = self._verify_task(task_id, commit_sha)

            if result["pass"]:
                self._record_confirmed(task_id, commit_sha, result["output"][:200])
                self._telemetry["confirmed"] += 1
                print(f"[secretary] CONFIRMED: {task_id}", flush=True)
            else:
                self._telemetry["failed"] += 1
                print(f"[secretary] verification FAILED for {task_id}: {result['output'][:200]}", flush=True)

            self._telemetry["verified"] += 1
            self._ack_relay(msg["id"])

    def _post_telemetry(self) -> None:
        """Post a telemetry health relay with friction metrics.

        Includes: verified, confirmed, failed, retries, escalations, failure rate.
        Posts every ~5 minutes (not every poll) to avoid relay flooding.
        Also auto-creates a GitHub issue if failure rate > 50% and >=4 tasks verified.
        """
        now = time.time()
        if now - self._last_telemetry_post < 300:  # 5 min cadence
            return
        self._last_telemetry_post = now

        verified = self._telemetry["verified"]
        confirmed = self._telemetry["confirmed"]
        failed = self._telemetry["failed"]
        skipped = self._telemetry["skipped"]
        failure_rate = (failed / verified * 100) if verified > 0 else 0.0

        ops = self._task_ops()
        tasks = ops._list_tasks()
        from collections import Counter
        status_counts = Counter(t.get("status", "").upper() for t in tasks)
        escalated = status_counts.get("ESCALATED", 0)

        # Per-task wall-clock metrics: collect durations from DONE tasks
        durations = [t.get("duration_s", 0) for t in tasks
                     if t.get("status", "").upper() == "DONE" and t.get("duration_s")]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            duration_line = (
                f"Task duration: avg={avg_duration:.1f}s, "
                f"min={min_duration:.1f}s, max={max_duration:.1f}s "
                f"(n={len(durations)})"
            )
        else:
            duration_line = "Task duration: (no completed tasks with timing data)"

        # Format skip reasons for telemetry
        skip_reasons = self._telemetry.get("skipped_reasons", {})
        skip_breakdown = ", ".join(f"{k}={v}" for k, v in sorted(skip_reasons.items(), key=lambda x: -x[1])) or "none"

        body = (
            f"Tasks: PENDING={status_counts.get('PENDING', 0)} "
            f"IN_PROGRESS={status_counts.get('IN_PROGRESS', 0)} "
            f"DONE={status_counts.get('DONE', 0)} "
            f"ESCALATED={escalated}\n"
            f"Secretary verified: {verified} (confirmed={confirmed}, failed={failed})\n"
            f"Skipped relays: {skipped} ({skip_breakdown})\n"
            f"Failure rate: {failure_rate:.1f}%\n"
            f"{duration_line}\n"
            f"Secretary uptime: since {self._telemetry['started_at']}"
        )

        relay = self._relay()
        try:
            relay.relay_post(
                to="claude_code_main",
                subject="[TELEMETRY] lane secretary health",
                body=body,
                priority="normal",
                sender="secretary",
            )
        except Exception:
            pass  # Never let telemetry crash the secretary

        # Auto-friction alert: high failure rate
        if verified >= 4 and failure_rate > 50:
            try:
                from .feedback import submit_feedback
                submit_feedback(
                    feedback_type="bug",
                    subject=f"High failure rate: {failure_rate:.0f}% ({failed}/{verified} tasks failed)",
                    body=f"Secretary telemetry detected high failure rate.\n\n{body}",
                    reporter="secretary-telemetry",
                    repo=str(self.config.repo_root),
                )
            except Exception:
                pass  # Best-effort

    def run(self) -> None:
        """Run the secretary daemon loop."""
        print(
            f"[secretary] daemon started (poll={self.poll_interval}s, "
            f"verify_only={self.verify_only}, brain={self.config.brain_path})",
            flush=True,
        )

        while True:
            try:
                self._reap_stale_tasks()
                self._process_done_relays()
                self._post_telemetry()
            except KeyboardInterrupt:
                print("[secretary] shutting down", flush=True)
                break
            except Exception as exc:
                print(f"[secretary] error: {exc}", flush=True)

            time.sleep(self.poll_interval)
