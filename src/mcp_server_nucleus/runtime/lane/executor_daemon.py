"""Executor daemon — claims tasks and invokes vendor CLIs to execute them.

This is the generalized form of executor_daemon.sh. It:
    1. Polls for PENDING tasks in the task store
    2. Atomically claims a task (sets status=IN_PROGRESS, claimed_by=self)
    3. Writes the task prompt to a temp file
    4. Invokes the vendor CLI (devin -p --prompt-file ... --model swe-2-max)
    5. Parses the result and marks the task DONE with commit SHA
    6. Posts a [DONE] relay to the secretary for verification

The daemon runs in a loop with retry/escalation logic.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import LaneConfig
from .verdict import parse_verdict, judge_clean


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
        # Append this process's PID so the secretary's stale-task reaper can
        # actually probe liveness. _extract_pid() supports "<name>:<pid>" and
        # returns None for a bare name — and its own docstring names the
        # production format ("lane-g1_devin") as the None case. Executors were
        # passing exactly that, so _reap_stale_tasks() skipped EVERY task and
        # could never fire: a safety net dead by construction for its only real
        # input. Observed 2026-08-19 — a restart left 2 tasks IN_PROGRESS,
        # claimed by dead PIDs, and the lane wedged for 40 minutes with the
        # reaper running every cycle and skipping them both.
        #
        # The July ticket bug_stale_claim_cleanup was closed as "stale claims
        # reset on restart naturally since claimed_by is in-memory state that
        # dies with the process". That is false: claimed_by and claimed_at are
        # PERSISTED to the task store. Both the reaper and its supposed
        # fallback were broken at once.
        self.agent_id = f"{agent_id}:{os.getpid()}"
        self.lane_name = agent_id  # stable identity, without the PID
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
        result = ops._claim_task(task_id, self.agent_id)
        return bool(result.get("success"))

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
            "Execute only this scope.\n\n"
            "NEVER write an absolute home path into a file. Your prompt contains the "
            "repo root as an absolute path; pasting it back into prose leaks the "
            "operator's identity, and a commit hook will block the whole task. Write "
            "~/ or a repo-relative path instead. This is the single most common way a "
            "sweep task gets rejected.\n\n"
            "DO NOT run git commit, git add, git reset, git stash, or git checkout. "
            "This working tree is shared with other agents whose uncommitted work is "
            "in it right now. Edit files and stop; the executor commits your edits "
            "for you, scoped to this task alone.\n\n"
            "THREE OUTCOMES ARE VALID. Finding nothing wrong is a real result, not a "
            "failure -- do NOT invent an edit to look productive.\n\n"
            "  1. You changed the file: just leave the edit in place.\n\n"
            "  2. You checked it and it is ACCURATE. Emit exactly this block, and "
            "note it is checked against the filesystem, so every path must be a real "
            "repo-relative path you actually opened:\n\n"
            "        VERDICT: CLEAN\n"
            f"        TASK_ID: {task['id']}\n"
            "        CLAIMS_CHECKED: <how many claims you verified>\n"
            "        EVIDENCE:\n"
            "        - <the claim> | TRUE | <real/repo/path.py>[:line] | <SYMBOL>\n"
            "        - <the claim> | TRUE | <real/repo/path.py> | <SYMBOL>\n"
            "        - <the claim> | TRUE | <real/repo/path.py> | <SYMBOL>\n\n"
            "     <SYMBOL> is a verbatim token -- a function name, constant, class, "
            "path or number -- that appears in BOTH the doc you are auditing AND "
            "the file you cite. It is how the executor re-checks your work without "
            "taking your word for it, so copy it exactly; do not paraphrase.\n\n"
            "     At least 3 claims, from at least 3 DIFFERENT files that git "
            "TRACKS. Files you create yourself do not count. Emit exactly ONE "
            "VERDICT line. If any claim came back FALSE or STALE, the doc is not "
            "clean -- fix it instead (outcome 1).\n\n"
            "  3. You could not establish either. Say so plainly:\n\n"
            "        VERDICT: INSUFFICIENT\n\n"
            "     with one line on what blocked you. This is recorded as a real "
            "outcome. An honest INSUFFICIENT is worth more than a guess."
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

    def _mark_done(self, task_id: str, commit_sha: str, note: str = "",
                   duration_s: float = 0.0, verification_status: str = "verified") -> None:
        """Mark a task as DONE.

        Records wall-clock duration_s for secretary telemetry.
        """
        ops = self._task_ops()
        ops._update_task(task_id, {
            "status": "DONE",
            "claimed_by": None,
            "escalation_reason": None,
            "retry_count": 0,
            "verification_status": verification_status,
            "verified_by": self.agent_id,
            "verification_note": f"commit {commit_sha}. {note}",
            "duration_s": round(duration_s, 1),
        })

        # Make the verdict COMPOUND. Without this a completed pass evaporates:
        # the doc gets fixed, the task flips to DONE, and nothing outside the
        # task ledger records that a claim about this corpus was established.
        # CSR is the repo's standing measure of "claims that survived", and the
        # sweep -- the largest claim-checking activity this repo runs -- was
        # feeding it exactly zero. Best-effort by design: a flywheel write must
        # never cost the task result, which is the load-bearing half.
        try:
            from ...flywheel.core import Flywheel
            Flywheel(self.config.brain_path).record_survived(
                phase="doc_sweep", step=f"{task_id}:{verification_status}",
            )
        except Exception as exc:  # noqa: BLE001 - bookkeeping must not break work
            print(f"[executor] {task_id}: flywheel bump failed ({exc}) -- "
                  f"task result stands", flush=True)

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
            # Both fields, deliberately: readers disagree about which one carries
            # a pause. Writing only escalation_reason left `pause_reason: None`
            # on every paused task, so the ledger recorded that a task stopped
            # but never why -- an unreadable failure.
            "escalation_reason": reason,
            "pause_reason": reason,
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

        # Snapshot the worktree before dispatch so the no-commit path can tell
        # THIS vendor's edits from another lane's uncommitted work.
        pre_state = self._worktree_state()

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

                    # NO-COMMIT PATH (2026-08-19). The dispatch preamble's
                    # non-negotiable #2 forbids vendors from running git commit,
                    # for a correct reason: "This working tree is shared with
                    # other agents running concurrently; their uncommitted work
                    # is in it right now." But _verify_diff_content() requires a
                    # commit SHA and diffs {sha}~1..{sha}, so an obedient vendor
                    # ALWAYS failed with "no commit SHA", retried, and paused.
                    # Two subsystems built on opposite assumptions: every LLM
                    # task in a shared tree failed structurally, regardless of
                    # how good the work was. Observed on the first real sweep --
                    # two tasks produced correct, careful doc corrections and
                    # both were rejected.
                    #
                    # Resolution: the vendor edits, the EXECUTOR commits. Single
                    # writer per task, serialized across executors by a repo
                    # lock, so the shared-tree hazard the preamble names is
                    # actually handled rather than pushed onto the vendor.
                    if not commit_sha or commit_sha == "unknown":
                        commit_sha = self._verify_and_commit_worktree(task_id, pre_state)

                    # Verify diff has real content (not just comments/whitespace)
                    diff_check = self._verify_diff_content(commit_sha)
                    if not diff_check.get("pass"):
                        # THIRD STATE. A binary verdict cannot tell "the doc was
                        # already accurate" from "the vendor did nothing" -- both
                        # arrive here with zero changed lines. Before calling this
                        # a failure, look for an explicitly declared CLEAN verdict
                        # backed by evidence the executor can check itself.
                        #
                        # judge_clean() is deliberately hostile: fabricated paths,
                        # a bare claim count, one file cited three times, or a
                        # CLEAN that also edited the file are all refused. A
                        # CLEAN accepted on the vendor's word would be worse than
                        # the binary bar it replaces -- it would turn "no work
                        # done" from a visible failure into a silent pass.
                        _parsed = parse_verdict(result.get("result", "") or "")
                        _declared = self._declared_paths(task_id)
                        # "Did the vendor CHANGE the doc?" -- asked of the
                        # worktree, not of whether a commit happened.
                        #
                        # This previously read bool(commit_sha != "unknown"),
                        # which is a different question. A vendor that edited
                        # the file but whose commit returned "unknown" (no
                        # declared-scope match, a failed commit, or the executor
                        # killed mid-dispatch) presented as "no diff", so a
                        # CLEAN was accepted alongside an actual edit. Measured:
                        # 9 docs marked verification_status=clean while carrying
                        # staged, uncommitted edits to those same docs. A vendor
                        # cannot both find a doc accurate and be fixing it, and
                        # that contradiction is precisely what judge_clean
                        # exists to refuse.
                        _post_state = self._worktree_state()
                        _touched = [d for d in _declared
                                    if pre_state.get(d) != _post_state.get(d)]
                        _edited = bool(_touched) or bool(
                            commit_sha and commit_sha != "unknown")
                        _j = judge_clean(
                            _parsed,
                            self.config.repo_root,
                            has_in_scope_diff=_edited,
                            doc_path=_declared[0] if _declared else None,
                            task_id=task_id,
                        )
                        # Persist every REFUSED verdict with the evidence that
                        # was refused. Without this the judge is unauditable: a
                        # correct refusal and an over-strict one look identical
                        # from outside, and the only thing that survives is a
                        # one-line reason. Calibrating a gate you cannot inspect
                        # is guessing, and this repo's design law is that trust
                        # requires a SECOND PARTY able to evaluate the meaning.
                        if not _j.accepted and _parsed.verdict:
                            try:
                                import json as _json
                                _ref = self.config.brain_path / "reports" / "clean_refusals.jsonl"
                                _ref.parent.mkdir(parents=True, exist_ok=True)
                                with open(_ref, "a") as _fh:
                                    _fh.write(_json.dumps({
                                        "task_id": task_id,
                                        "doc": _declared[0] if _declared else None,
                                        "vendor": self.vendor,
                                        "reason": _j.reason,
                                        "declared_verdict": _parsed.verdict,
                                        "claims_checked": _parsed.claims_checked,
                                        "evidence": [
                                            {"claim": r.claim[:200], "status": r.status,
                                             "path": r.path, "symbol": r.symbol[:120]}
                                            for r in _parsed.evidence
                                        ],
                                    }) + "\n")
                            except Exception as _exc:  # noqa: BLE001
                                print(f"[executor] {task_id}: could not log refusal ({_exc})",
                                      flush=True)

                        if _j.accepted:
                            note = (f"verified clean: {_j.reason}. "
                                    f"no change needed")
                            self._mark_done(task_id, "clean", note,
                                            duration_s=duration_s,
                                            verification_status="clean")
                            self._post_done_relay(task_id, "clean")
                            print(f"[executor] marked DONE (CLEAN): {task_id} -- {_j.reason}",
                                  flush=True)
                            self._retry_counts.pop(task_id, None)
                            return
                        raise RuntimeError(
                            f"Diff verification failed: {diff_check.get('real_lines', 0)} real lines "
                            f"(need >=5). {diff_check.get('error', '')} "
                            f"[third-state: {_j.verdict} -- {_j.reason}]"
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
                # Do NOT trust the status field. _update_task authenticates
                # nothing -- "status" and every verification_* field are
                # writable by any caller, including the vendor we just
                # dispatched. A vendor that ran one `nucleus_tasks update
                # status=DONE` and exited would land here, and this branch used
                # to launder that self-declaration into an accepted completion:
                # zero doc reads, zero evidence, no retry. That bypasses the
                # CLEAN evidence rules entirely by making them unnecessary.
                #
                # A DONE is only honoured if the executor can corroborate it
                # from artifacts it checks itself: a real in-scope commit made
                # during this dispatch. Anything else is recorded as an
                # unverified self-declaration and NOT accepted.
                corroborating_sha = self._verify_and_commit_worktree(task_id, pre_state)
                if corroborating_sha and corroborating_sha != "unknown":
                    print(f"[executor] {task_id} DONE corroborated by in-scope commit "
                          f"{corroborating_sha[:8]}", flush=True)
                    self._retry_counts.pop(task_id, None)
                    return
                print(f"[executor] {task_id}: DONE found in the store with no in-scope "
                      f"commit to corroborate it — treating as UNVERIFIED, not complete",
                      flush=True)
                ops._update_task(task_id, {
                    "status": "PAUSED",
                    "claimed_by": None,
                    "verification_status": "insufficient",
                    "pause_reason": (
                        "Task was marked DONE without any verifiable work: no in-scope "
                        "commit and no accepted CLEAN verdict. A DONE written directly "
                        "into the task store is a self-declaration, not evidence."
                    ),
                })
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
        """Always "unknown". The vendor's stdout is not evidence of a commit.

        This used to regex the first 40-hex token out of vendor stdout, and
        failing that ANY 8-12 hex token, then hand it to _verify_diff_content()
        which diffs {sha}~1..{sha} with no check that the commit is new, is on
        this run's ancestry, or touches the task's scope. So:

            git log -20 --format=%H | tail -1

        printed by a vendor that did nothing produced a large historical commit
        that sailed through the real-content bar. The 8-12 fallback was worse
        still -- it matches "deadbeef", a UUID fragment, a truncated hash in a
        log line.

        There is no longer any legitimate use for a vendor-supplied SHA: the
        dispatch preamble forbids vendors from committing, and the executor does
        the commit itself, scoped to the task's declared paths. Reading a SHA
        from vendor output cannot distinguish work from a copied string, so it
        is not read at all. Kept as a method so the call site stays explicit
        about what it refuses to trust.
        """
        return "unknown"

    def _worktree_state(self) -> dict:
        """Map path -> porcelain status for the whole worktree, or {} if git
        is unreadable. Used to attribute edits to THIS dispatch rather than to
        a concurrent lane's uncommitted work."""
        try:
            r = subprocess.run(
                ["git", "-C", str(self.config.repo_root), "status", "--porcelain"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                return {}
            out = {}
            for line in r.stdout.splitlines():
                if len(line) > 3:
                    out[line[3:].strip()] = line[:2]
            return out
        except Exception:
            logger.debug("Swallowed exception in _worktree_state", exc_info=True)
            return {}

    def _declared_paths(self, task_id: str) -> list:
        """Repo-relative paths this task declared it would touch.

        A dispatch may only commit inside its own declared scope. Without this,
        attribution is "every path whose porcelain status changed during the
        dispatch window", which claims any concurrent writer's work: a sweep
        task once committed a hand-written test file under its own name while
        leaving the doc it actually edited uncommitted.

        Returns [] when the task declares nothing -- the caller treats that as
        unattributable and commits nothing, rather than falling back to the
        wide set that caused the bug.
        """
        try:
            tasks = self._task_ops()._list_tasks()
        except Exception:
            logger.debug("Swallowed exception in _declared_paths", exc_info=True)
            return []
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            return []
        text = " ".join(str(task.get(k) or "") for k in ("description", "id"))
        found, root = [], self.config.repo_root
        for m in re.finditer(r"`([^`\n]+?)`", text):
            cand = m.group(1).strip()
            if not cand or cand.startswith("-"):
                continue
            # An existing file is in scope. So is a path the task DECLARES it
            # will create, provided its parent directory already exists -- an
            # audit that must write a report cannot have its output path in
            # scope otherwise, and the commit would be refused as foreign. The
            # parent-must-exist rule keeps this from becoming "declare any path
            # you like": the task can only write where the repo already has a
            # home for it.
            if (root / cand).is_file():
                found.append(cand)
                continue
            # A path the task DECLARES it will create counts as in scope -- an
            # audit that must write a report cannot otherwise have its own
            # output in scope, and the commit would be refused as foreign.
            #
            # Three conditions, and the last two are why: a bare backticked word
            # like `grep` has a parent of "." which IS a directory, so
            # parent-exists ALONE lets any prose token become a declared path.
            # Caught by test_declared_paths_ignores_backticked_nonfiles.
            if ("/" in cand and Path(cand).suffix
                    and (root / cand).parent.is_dir()):
                found.append(cand)
        return sorted(set(found))

    def _verify_and_commit_worktree(self, task_id: str, pre_state: dict) -> str:
        """Commit exactly the files THIS dispatch changed, under a repo lock.

        Returns the new commit SHA, or "unknown" when there is nothing
        attributable to commit — which correctly fails verification downstream
        rather than inventing a pass.

        The lock is the point: two executors run concurrently and the lane
        package had NO git serialization anywhere, so `git add`/`git commit`
        from two vendors could interleave and one lane's commit could swallow
        another's staged work.
        """
        repo = str(self.config.repo_root)
        post_state = self._worktree_state()
        changed = [p for p, st in post_state.items() if pre_state.get(p) != st]
        if not changed:
            print(f"[executor] {task_id}: vendor changed no files", flush=True)
            return "unknown"

        # Scope gate. Changing during the dispatch window is necessary but not
        # sufficient -- a concurrent writer's file also changes during it. Only
        # paths this task DECLARED may be committed under this task's name.
        declared = self._declared_paths(task_id)
        if not declared:
            print(f"[executor] {task_id}: no declared scope; refusing to attribute "
                  f"{len(changed)} changed file(s)", flush=True)
            return "unknown"
        foreign = [p for p in changed if p not in declared]
        changed = [p for p in changed if p in declared]
        if foreign:
            print(f"[executor] {task_id}: left {len(foreign)} out-of-scope file(s) "
                  f"uncommitted: {', '.join(sorted(foreign)[:5])}", flush=True)
        if not changed:
            print(f"[executor] {task_id}: vendor changed no in-scope files", flush=True)
            return "unknown"

        lock_path = self.config.brain_path / "state" / "lane_git.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        import fcntl
        with open(lock_path, "w") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass  # best-effort; a missing lock must not block real work
            try:
                # Re-derive under the lock: another executor may have committed
                # some of these paths while we waited.
                still = [p for p, st in self._worktree_state().items()
                         if pre_state.get(p) != st and p in changed and p in declared]
                if not still:
                    return "unknown"
                subprocess.run(["git", "-C", repo, "add", "--"] + still,
                               capture_output=True, text=True, timeout=60, check=True)
                msg = (f"docs(sweep): {task_id}\n\n"
                       f"Committed by lane executor {self.agent_id} on behalf of vendor "
                       f"{self.vendor}, which is forbidden from git state changes by the "
                       f"dispatch preamble (shared working tree).\n\n"
                       f"Files: {', '.join(still[:10])}")
                r = subprocess.run(["git", "-C", repo, "commit", "-m", msg],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    print(f"[executor] {task_id}: commit failed: "
                          f"{(r.stderr or r.stdout)[:200]}", flush=True)
                    return "unknown"
                sha = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                                     capture_output=True, text=True, timeout=30).stdout.strip()
                print(f"[executor] {task_id}: committed {len(still)} file(s) as {sha[:8]}", flush=True)
                return sha or "unknown"
            finally:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass

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
            # DOC-ONLY DETECTION (2026-08-19). The rules below encode two
            # code-shaped assumptions that make prose changes unverifiable:
            #   1. a line starting with "#" is skipped as a Python/shell
            #      comment -- but in markdown that is a HEADER, i.e. real
            #      content, and doc edits are dense with them;
            #   2. passing requires a def/class/fn, or 20+ real lines.
            # A correct 12-line doc correction therefore scored real_lines=12
            # with has_function_or_class=False and FAILED. Observed on the
            # first real sweep: two accurate doc fixes rejected on these
            # grounds alone.
            # The code path below is deliberately UNCHANGED -- crit_verify_bypass
            # raised that bar on purpose and this must not lower it. Only a diff
            # touching exclusively prose files takes the relaxed rules.
            _DOC_EXT = (".md", ".markdown", ".rst", ".txt", ".adoc")
            # NOTE: `git diff --stat` rows are " path | 12 ++++" WITH a leading
            # space. The original parser filtered on `not line.startswith(" ")`,
            # so files_changed was ALWAYS EMPTY -- a silently dead field. Parse
            # on the stripped line instead, and exclude the trailing
            # "N files changed, ..." summary row.
            _changed_now = [ln.strip().split("|")[0].strip()
                            for ln in stat_output.split("\n")
                            if "|" in ln and "changed," not in ln]
            doc_only = bool(_changed_now) and all(
                f.lower().endswith(_DOC_EXT) for f in _changed_now
            )

            has_function_or_class = False
            for line in added_lines:
                content = line[1:].strip()  # remove leading +
                if not content:
                    continue  # blank line
                if content.startswith("#") and not content.startswith("#!") and not doc_only:
                    continue  # comment (Python/shell) -- but a markdown header in a doc
                if content.startswith("//"):
                    continue  # comment (JS/Go/Rust)
                if content.startswith("/*") or content.startswith("*"):
                    continue  # comment (C/Java block)
                real_lines += 1
                # Check for function/class definitions (indicates real code, not just config tweaks)
                if (content.startswith("def ") or content.startswith("class ")
                        or content.startswith("function ") or content.startswith("pub fn ")
                        or content.startswith("fn ") or content.startswith("func ")):
                    has_function_or_class = True

            # Extract files changed
            files_changed = list(_changed_now)

            # crit_verify_bypass fix: threshold raised from 5 to 10 real lines,
            # AND require at least one function/class definition OR >=20 real lines
            # (config-only changes with 10+ real lines are legitimate if substantial)
            if doc_only:
                # Prose: no def/class will ever appear, so requiring one is an
                # unsatisfiable condition. 5 real lines still rules out the
                # one-line-comment bypass crit_verify_bypass was written for,
                # which is what that guard actually protects against.
                passed = real_lines >= 5
            else:
                passed = real_lines >= 10 and (has_function_or_class or real_lines >= 20)
            return {
                "pass": passed,
                "insertions": insertions,
                "real_lines": real_lines,
                "has_function_or_class": has_function_or_class,
                "doc_only": doc_only,
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

        consecutive_failures = 0
        while True:
            try:
                task = self._find_claimable_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(self.poll_interval)
                consecutive_failures = 0
            except KeyboardInterrupt:
                print("[executor] shutting down", flush=True)
                break
            except Exception as exc:
                consecutive_failures += 1
                print(f"[executor] error ({consecutive_failures}): {exc}", flush=True)
                if consecutive_failures >= 10:
                    self._escalate(
                        "__executor__",
                        f"executor exiting after {consecutive_failures} consecutive failures: {exc}",
                    )
                    raise
                time.sleep(self.poll_interval)
