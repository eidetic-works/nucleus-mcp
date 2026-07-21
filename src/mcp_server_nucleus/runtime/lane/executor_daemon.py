"""Executor daemon — claims tasks and invokes vendor CLIs to execute them.

This is the generalized form of executor_daemon.sh. It:
    1. Polls for PENDING tasks in the task store
    2. Atomically claims a task (sets status=IN_PROGRESS, claimed_by=self)
    3. Writes the task prompt to a temp file
    4. Invokes the vendor CLI (devin -p --prompt-file ... --model glm-5.2)
    5. Parses the result and marks the task DONE with commit SHA
    6. Posts a [DONE] relay to the secretary for verification

The daemon runs in a loop with retry/escalation logic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import LaneConfig


class ExecutorDaemon:
    """Polls for tasks and executes them via vendor CLIs."""

    def __init__(
        self,
        config: LaneConfig,
        agent_id: str,
        lane: str,
        vendor: str = "devin",
        poll_interval: int = 10,
        max_retries: int = 3,
    ):
        self.config = config
        self.agent_id = agent_id
        self.lane = lane
        self.vendor = vendor
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self._retry_counts: Dict[str, int] = {}
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

    def _vendor_dispatch(self):
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime import vendor_dispatch
        return vendor_dispatch

    def _claim_task(self, task_id: str) -> bool:
        """Atomically claim a task."""
        ops = self._task_ops()
        try:
            ops._claim_task(task_id, self.agent_id)
            return True
        except Exception:
            return False

    def _build_prompt(self, task: dict) -> str:
        """Build the prompt for the vendor CLI."""
        desc = task.get("description", "")
        # Extract acceptance criteria from the task description if present
        has_tests_requirement = "test" in desc.lower() and ("test_" in desc or "tests/" in desc or "test case" in desc.lower())
        test_directive = ""
        if has_tests_requirement:
            test_directive = (
                "\n\nIMPORTANT: The acceptance criteria require test files. "
                "You MUST create every test file mentioned in the acceptance criteria. "
                "A task is NOT complete until all specified test files exist on disk. "
                "List the test files you created in your final summary."
            )
        return (
            f"Task: {task['id']}\n\n"
            f"{desc}\n\n"
            f"Repo root: {self.config.repo_root}\n"
            f"Agent: {self.agent_id}\n"
            f"Vendor: {self.vendor}\n\n"
            "Claim the task atomically, execute only this scope, run focused tests, "
            "commit the result, mark the task DONE with the commit SHA, and post [DONE] to secretary."
            f"{test_directive}"
        )

    def _execute_shell(self, task: dict) -> Dict[str, Any]:
        """Execute a shell task directly — no LLM, no vendor CLI.

        For meta-tasks like running tests, building docs, or checking
        status. 30x faster than going through an LLM session.

        The task must have a 'command' field (the shell command to run).
        Optional 'timeout_s' field (default 300 = 5 min).
        """
        command = task.get("command", "")
        if not command:
            return {"status": "error", "rc": 1, "result": "No 'command' field in shell task"}

        timeout_s = task.get("timeout_s", 300)
        cwd = str(self.config.repo_root)

        print(f"[executor] shell: {command[:100]}", flush=True)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=cwd,
            )
            output = result.stdout + result.stderr
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "rc": result.returncode,
                "result": output,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "rc": -1, "result": f"Command timed out after {timeout_s}s"}

    def _execute_llm(self, task: dict) -> Dict[str, Any]:
        """Execute a task via the vendor CLI."""
        prompt = self._build_prompt(task)
        vd = self._vendor_dispatch()

        # Write prompt to a temp file (identity-safe, 0600)
        fd, prompt_path = tempfile.mkstemp(prefix="nucleus_lane_prompt_")
        try:
            os.write(fd, prompt.encode("utf-8"))
            os.close(fd)
            os.chmod(prompt_path, 0o600)

            result = vd.dispatch_and_capture(
                vendor=self.vendor,
                prompt=prompt,
                artifact_ref=task["id"],
                to_role=self.lane,
                timeout_s=3600,  # 1 hour wall-clock limit (prevents hung sessions)
            )
            return result
        finally:
            try:
                os.unlink(prompt_path)
            except OSError:
                pass

    def _mark_done(self, task_id: str, commit_sha: str, note: str = "", duration_s: float = 0.0) -> None:
        """Mark a task as DONE.

        Records wall-clock duration_s for secretary telemetry.
        """
        ops = self._task_ops()
        ops._update_task(task_id, {
            "status": "DONE",
            "claimed_by": None,
            "escalation_reason": None,
            "retry_count": 0,
            "verification_status": "verified",
            "verified_by": self.agent_id,
            "verification_note": f"commit {commit_sha}. {note}",
            "duration_s": round(duration_s, 1),
        })

    def _post_done_relay(self, task_id: str, commit_sha: str) -> None:
        """Post a [DONE] relay to the secretary."""
        relay = self._relay()
        relay.relay_post(
            to="secretary",
            subject=f"[DONE] {task_id}",
            body=f"Task {task_id} completed. Commit: {commit_sha}",
            priority="normal",
            sender=self.agent_id,
        )

    def _escalate(self, task_id: str, reason: str, retry_count: Optional[int] = None) -> None:
        """Escalate a task that exceeded max retries.

        Marks the task status as ESCALATED (terminal — not retried forever)
        and records the reason. The secretary surfaces ESCALATED tasks to
        the operator for human intervention.
        """
        ops = self._task_ops()
        updates: Dict[str, Any] = {
            "status": "ESCALATED",
            "claimed_by": None,
            "escalation_reason": reason,
        }
        if retry_count is not None:
            updates["retry_count"] = retry_count
        ops._update_task(task_id, updates)

        relay = self._relay()
        relay.relay_post(
            to="secretary",
            subject=f"[ESCALATED] {task_id}",
            body=f"Task {task_id} escalated: {reason}",
            priority="high",
            sender=self.agent_id,
        )

    def _pause_and_ask(self, task_id: str, retry: int, exc: Exception) -> None:
        """Pause a task that's one retry away from escalation and ask the principal.

        Instead of burning the last retry blindly, the task goes to PAUSED
        state. The principal receives a relay and can:
        - reset to PENDING (retry_count=0) for a fresh start
        - mark DONE if completed manually
        - leave PAUSED for investigation
        - escalate explicitly

        This is the partial-failure recovery path — a middle ground between
        retry (which might fail again) and escalate (which is terminal).
        """
        ops = self._task_ops()
        reason = f"Paused after {retry} failed attempt(s): {exc}"
        ops._update_task(task_id, {
            "status": "PAUSED",
            "claimed_by": None,
            "escalation_reason": reason,
            "retry_count": retry,
        })

        relay = self._relay()
        relay.relay_post(
            to="secretary",
            subject=f"[PAUSED] {task_id}",
            body=(
                f"Task {task_id} paused after {retry} failed attempt(s).\n"
                f"Error: {exc}\n\n"
                f"One retry remaining before escalation. Principal actions:\n"
                f"  - reset to PENDING (retry_count=0) for a fresh start\n"
                f"  - mark DONE if completed manually\n"
                f"  - leave PAUSED for investigation\n"
                f"  - escalate explicitly by setting status=ESCALATED"
            ),
            priority="high",
            sender=self.agent_id,
        )
        print(f"[executor] paused {task_id} after {retry} retries — asked principal for guidance", flush=True)

    def _process_task(self, task: dict) -> None:
        """Process a single task: claim, execute, mark done.

        Supports two task types:
        - task_type: llm (default) — executes via vendor CLI (devin/agy)
        - task_type: shell — executes a shell command directly (30x faster
          for meta-tasks like running tests, no LLM overhead)

        Records wall-clock duration in the task store for telemetry.
        """
        task_id = task["id"]
        import time as _time
        start_time = _time.time()

        # Claim
        if not self._claim_task(task_id):
            return

        print(f"[executor] claimed: {task_id}", flush=True)

        try:
            task_type = task.get("task_type", "llm").lower()

            if task_type == "shell":
                # Shell tasks: run command directly, no LLM
                result = self._execute_shell(task)
            else:
                # LLM tasks: execute via vendor CLI
                result = self._execute_llm(task)

            status = result.get("status", "error")
            rc = result.get("rc", 1)

            if status == "ok" and rc == 0:
                duration_s = _time.time() - start_time
                if task_type == "shell":
                    # Shell tasks: no commit/diff verification needed
                    commit_sha = "shell"
                    output = result.get("result", "")[:500]
                    note = f"shell task. output: {output}"
                    self._mark_done(task_id, commit_sha, note, duration_s=duration_s)
                    self._post_done_relay(task_id, commit_sha)
                    print(f"[executor] marked DONE: {task_id} (shell, rc=0, {duration_s:.1f}s)", flush=True)
                    self._retry_counts.pop(task_id, None)
                else:
                    # LLM tasks: extract commit SHA and verify diff
                    commit_sha = self._extract_commit_sha(result)

                    # Verify diff has real content (not just comments/whitespace)
                    diff_check = self._verify_diff_content(commit_sha)
                    if not diff_check.get("pass"):
                        raise RuntimeError(
                            f"Diff verification failed: {diff_check.get('real_lines', 0)} real lines "
                            f"(need >=5). {diff_check.get('error', '')}"
                        )

                    note = f"diff: {diff_check['real_lines']} real lines, {diff_check['insertions']} insertions"
                    self._mark_done(task_id, commit_sha, note, duration_s=duration_s)
                    self._post_done_relay(task_id, commit_sha)
                    print(f"[executor] marked DONE: {task_id} (commit {commit_sha[:8]}, {diff_check['real_lines']} real lines)", flush=True)
                    self._retry_counts.pop(task_id, None)
            else:
                raise RuntimeError(f"Execution failed: status={status}, rc={rc}")

        except Exception as exc:
            # Track retry_count durably in the task store (survives daemon
            # restarts — in-memory _retry_counts is only a cache). The store
            # is the source of truth for "how many times has this failed?"
            ops = self._task_ops()
            current = ops._get_task(task_id) or {}

            # Re-check: if the task was marked DONE while we were running
            # (e.g., principal manually completed it), don't retry — accept
            # the DONE and move on. Prevents the retry-loop-on-killed-session
            # bug where killing a stuck devin session + manual DONE still
            # triggered 3 retries of the same task.
            if current.get("status", "").upper() == "DONE":
                print(f"[executor] {task_id} already DONE (manual/principal completion) — skipping retry", flush=True)
                self._retry_counts.pop(task_id, None)
                return

            stored_retry = current.get("retry_count")
            try:
                retry = int(stored_retry or 0) + 1
            except (TypeError, ValueError):
                retry = self._retry_counts.get(task_id, 0) + 1
            self._retry_counts[task_id] = retry
            print(f"[executor] retry {retry}/{self.max_retries} for {task_id}: {exc}", flush=True)

            if retry >= self.max_retries:
                self._escalate(
                    task_id,
                    f"Max retries ({self.max_retries}) exceeded after {retry} failed attempt(s): {exc}",
                    retry_count=retry,
                )
                self._retry_counts.pop(task_id, None)
            elif retry >= self.max_retries - 1:
                # Partial-failure recovery: one chance left. PAUSE the task
                # and ask the principal for guidance instead of burning the
                # last retry blindly. The principal can either:
                # - reset to PENDING (retry_count=0) to give a fresh start
                # - mark DONE if they completed it manually
                # - leave it PAUSED to hold for investigation
                # This prevents the lane from escalating without human
                # input when the last retry might also fail.
                self._pause_and_ask(task_id, retry, exc)
                self._retry_counts.pop(task_id, None)
            else:
                # Reset to PENDING for retry, persisting the incremented
                # retry_count so a restart doesn't reset the counter.
                ops._update_task(task_id, {
                    "status": "PENDING",
                    "claimed_by": None,
                    "retry_count": retry,
                })

    def _extract_commit_sha(self, result: dict) -> str:
        """Extract a commit SHA from the vendor result."""
        text = result.get("result", "")
        # Look for commit SHA patterns
        import re
        match = re.search(r"\b([0-9a-f]{40})\b", text)
        if match:
            return match.group(1)
        match = re.search(r"\b([0-9a-f]{8,12})\b", text)
        if match:
            return match.group(1)
        return "unknown"

    def _verify_diff_content(self, commit_sha: str) -> dict:
        """Verify that a commit has real diff content (not just comments/whitespace).

        Addresses crit_verify_bypass: prevents an LLM from adding a trivial
        comment (# TODO) to the right file and passing verification.

        Returns dict with:
            - pass: True if diff has >=5 real (non-comment, non-whitespace) lines
            - insertions: total lines added
            - real_lines: non-comment, non-blank lines added
            - files_changed: list of files in the diff
        """
        if not commit_sha or commit_sha == "unknown":
            return {"pass": False, "error": "no commit SHA", "insertions": 0, "real_lines": 0, "files_changed": []}

        repo = self.config.repo_root
        try:
            # Get diff stat
            result = subprocess.run(
                ["git", "-C", str(repo), "diff", "--stat", f"{commit_sha}~1", commit_sha],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                # Maybe it's the first commit — try against empty tree
                result = subprocess.run(
                    ["git", "-C", str(repo), "diff", "--stat", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", commit_sha],
                    capture_output=True, text=True, timeout=30,
                )
            stat_output = result.stdout

            # Get full diff for content analysis
            result = subprocess.run(
                ["git", "-C", str(repo), "diff", f"{commit_sha}~1", commit_sha, "--no-color"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "-C", str(repo), "diff", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", commit_sha, "--no-color"],
                    capture_output=True, text=True, timeout=30,
                )
            diff_text = result.stdout

            # Count added lines (lines starting with + but not +++ which is file headers)
            added_lines = [l for l in diff_text.split("\n") if l.startswith("+") and not l.startswith("+++")]
            insertions = len(added_lines)

            # Count real lines (non-comment, non-blank)
            real_lines = 0
            for line in added_lines:
                content = line[1:].strip()  # remove leading +
                if not content:
                    continue  # blank line
                if content.startswith("#") and not content.startswith("#!"):
                    continue  # comment (Python/shell)
                if content.startswith("//"):
                    continue  # comment (JS/Go/Rust)
                if content.startswith("/*") or content.startswith("*"):
                    continue  # comment (C/Java block)
                real_lines += 1

            # Extract files changed
            files_changed = []
            for line in stat_output.split("\n"):
                if "|" in line and not line.startswith(" "):
                    files_changed.append(line.split("|")[0].strip())

            return {
                "pass": real_lines >= 5,
                "insertions": insertions,
                "real_lines": real_lines,
                "files_changed": files_changed,
            }
        except Exception as exc:
            return {"pass": False, "error": str(exc), "insertions": 0, "real_lines": 0, "files_changed": []}

    def _find_claimable_task(self) -> Optional[dict]:
        """Find a PENDING task that this executor can claim.

        Rate-limits claiming: skips if this executor already has an
        IN_PROGRESS task (addresses high_executor_starvation — prevents
        one executor from claiming all PENDING tasks).
        """
        ops = self._task_ops()
        all_tasks = ops._list_tasks()

        # Build a lookup dict by task id for dependency checks
        all_tasks_by_id = {t.get("id", ""): t for t in all_tasks} if all_tasks else {}

        # Check if we already have an IN_PROGRESS task
        in_progress_count = sum(
            1 for t in all_tasks
            if t.get("claimed_by") == self.agent_id
            and t.get("status", "").upper() == "IN_PROGRESS"
        )
        if in_progress_count > 0:
            return None  # Already busy — don't claim more

        for task in all_tasks:
            if task.get("source") != self.config.source:
                continue
            if task.get("status", "").upper() not in self.config.claimable_statuses:
                continue
            if task.get("escalation_reason"):
                continue
            # Check deps
            blocked_by = task.get("blocked_by", [])
            if blocked_by:
                deps_met = all(
                    all_tasks_by_id.get(dep, {}).get("status", "").upper() == "DONE"
                    for dep in blocked_by
                )
                if not deps_met:
                    continue
            return task
        return None

    def run(self) -> None:
        """Run the executor daemon loop."""
        print(
            f"[executor] daemon started (agent={self.agent_id}, lane={self.lane}, "
            f"vendor={self.vendor}, poll={self.poll_interval}s)",
            flush=True,
        )

        while True:
            try:
                task = self._find_claimable_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                print("[executor] shutting down", flush=True)
                break
            except Exception as exc:
                print(f"[executor] error: {exc}", flush=True)
                time.sleep(self.poll_interval)
