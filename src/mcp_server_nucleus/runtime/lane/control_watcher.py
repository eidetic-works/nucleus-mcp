"""Control watcher — dispatches tasks from the spec to executor lanes.

This is the generalized form of principal_control.py. It:
    1. Verifies the spec hasn't moved (immutability gate)
    2. Projects spec tasks into the nucleus task store
    3. Dispatches ready tasks (deps met, capacity available) to executor lanes via relay
    4. Maintains dispatch state to track outstanding work

The watcher runs in a loop with error handling — transient failures (e.g.,
git operations during executor commits) are logged and retried. Only 10
consecutive failures cause exit.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import LaneConfig, WorkItem
from .spec_parser import SpecParser, SpecParseError


class ControlWatcher:
    """Watch loop that dispatches spec tasks to executor lanes."""

    def __init__(self, config: LaneConfig):
        self.config = config
        self.parser = SpecParser(config)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.config.brain_path / "state", self.config.relay_dir, self.config.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _git(self, *args: str) -> bytes:
        return subprocess.check_output(
            ["git", "-C", str(self.config.repo_root), *args],
            stderr=subprocess.STDOUT,
        )

    def _load_state(self) -> Dict[str, Any]:
        if self.config.state_path.exists():
            return json.loads(self.config.state_path.read_text())
        return {"dispatches": {}, "runs": []}

    def _save_state(self, state: Dict[str, Any]) -> None:
        from .atomic_write import atomic_write
        atomic_write(self.config.state_path, json.dumps(state, indent=2, default=str))

    def _task_fingerprint(self, task: dict) -> str:
        return f"{task.get('status', '').upper()}:{task.get('priority', 0)}:{task.get('claimed_by')}"

    def _dispatch_is_fresh(
        self, dispatch: dict, fingerprint: str, lanes: Tuple[str, ...]
    ) -> bool:
        if not dispatch:
            return False
        if dispatch.get("fingerprint") != fingerprint:
            return False
        if dispatch.get("lane") not in lanes:
            return False
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(dispatch["at"])).total_seconds()
        return age < 600  # redispatch after 10 min

    def _task_index(self) -> Dict[str, dict]:
        """Load all tasks from the nucleus task store.

        Filters by required_role (the lane's role) — NOT by task_id prefix,
        which doesn't match the actual task IDs (e.g., 'g3_mcp_registry_listing'
        doesn't start with 'lane-g9'). This was the root cause of the
        NOT_SEEDED state sync bug: tasks were DONE in the store but showed
        as NOT_SEEDED in lane status because the ID-prefix filter never matched.
        """
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime.task_ops import _list_tasks

        result = {}
        for t in _list_tasks():
            task_role = t.get("required_role", "")
            if task_role == self.config.role:
                result[t["id"]] = t
        return result

    def _seed_tasks(self, work_items: Tuple[WorkItem, ...]) -> Dict[str, Any]:
        """Project work items into the nucleus task store."""
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime.task_ops import _list_tasks, _add_task, _update_task

        existing = {t["id"]: t for t in _list_tasks()}
        seeded = 0
        for item in work_items:
            if item.task_id not in existing:
                _add_task(
                    description=item.description,
                    priority=item.priority,
                    blocked_by=list(item.blocked_by) if item.blocked_by else None,
                    source=self.config.source,
                    task_id=item.task_id,
                    skip_dep_check=True,  # deps may not be seeded yet
                    required_role=self.config.role,
                    task_type=item.task_type,
                    command=item.command,
                )
                seeded += 1
            else:
                # Check if blocked deps are now met — auto-unblock
                task = existing[item.task_id]
                if task.get("status", "").upper() == "BLOCKED":
                    deps_met = all(
                        existing.get(dep, {}).get("status", "").upper() == "DONE"
                        for dep in item.blocked_by
                    )
                    if deps_met:
                        _update_task(item.task_id, {"status": "PENDING"})

        # Verify spec
        principal = self.parser.verify_spec()
        return {"seeded": seeded, "principal": principal}

    def _post_relay(self, task_id: str, lane: str, description: str) -> str:
        """Post a task relay to an executor lane."""
        sys.path.insert(0, str(self.config.repo_root / "mcp-server-nucleus" / "src"))
        from mcp_server_nucleus.runtime.relay.core import relay_post

        result = relay_post(
            to=lane,
            subject=f"[TASK] {task_id}",
            body=description,
            priority="normal",
            sender="lane_control",
        )
        return str(result.get("message_id", result))

    def dispatch(self) -> Dict[str, Any]:
        """Dispatch ready tasks to executor lanes.

        Returns a dict with posted/skipped tasks and spec verification.
        """
        # 1. Verify spec immutability
        principal = self.parser.verify_spec()

        # 2. Parse and seed tasks
        work_items = self.parser.parse()
        seeded = self._seed_tasks(work_items)

        # 3. Load task state
        tasks = self._task_index()
        state = self._load_state()
        dispatches = state.setdefault("dispatches", {})
        posted: Dict[str, Dict[str, str]] = {}
        skipped: Dict[str, str] = {}

        # 4. Count active and outstanding
        active = sum(
            1
            for item in work_items
            if tasks.get(item.task_id, {}).get("status", "").upper() == "IN_PROGRESS"
        )
        outstanding = 0
        for item in work_items:
            task = tasks.get(item.task_id, {})
            task_status = task.get("status", "NOT_SEEDED").upper()
            fingerprint = self._task_fingerprint(task)
            if task_status in self.config.claimable_statuses and self._dispatch_is_fresh(
                dispatches.get(item.task_id, {}), fingerprint, self.config.lanes
            ):
                outstanding += 1
        slots = self.config.max_inflight - active - outstanding

        # 5. Dispatch ready tasks
        if slots > 0:
            for item in work_items:
                if slots <= 0:
                    break
                task = tasks.get(item.task_id, {})
                task_status = task.get("status", "NOT_SEEDED").upper()

                if task_status == "DONE":
                    skipped[item.task_id] = "DONE"
                    continue
                if task_status == "IN_PROGRESS":
                    skipped[item.task_id] = "IN_PROGRESS"
                    continue
                if task_status == "BLOCKED":
                    skipped[item.task_id] = "blocked"
                    continue
                if task_status not in self.config.claimable_statuses:
                    skipped[item.task_id] = f"status={task_status}"
                    continue

                # Check deps
                deps_met = all(
                    tasks.get(dep, {}).get("status", "").upper() == "DONE"
                    for dep in item.blocked_by
                )
                if not deps_met:
                    skipped[item.task_id] = "dependencies-unverified"
                    continue

                # Check if already dispatched (fresh)
                fingerprint = self._task_fingerprint(task)
                if self._dispatch_is_fresh(
                    dispatches.get(item.task_id, {}), fingerprint, self.config.lanes
                ):
                    skipped[item.task_id] = "already-dispatched"
                    continue

                # Dispatch to the first available lane
                lane = self.config.lanes[0]
                relay_id = self._post_relay(item.task_id, lane, item.description)
                dispatches[item.task_id] = {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "fingerprint": fingerprint,
                    "lane": lane,
                    "principal_git_object": principal["blob"],
                    "relay_id": relay_id,
                }
                posted[item.task_id] = {"lane": lane, "relay_id": relay_id}
                slots -= 1
        else:
            for item in work_items:
                task = tasks.get(item.task_id, {})
                task_status = task.get("status", "NOT_SEEDED").upper()
                if task_status == "DONE":
                    skipped[item.task_id] = "DONE"
                elif task_status == "IN_PROGRESS":
                    skipped[item.task_id] = "IN_PROGRESS"
                elif task_status == "BLOCKED":
                    skipped[item.task_id] = "blocked"
                else:
                    skipped[item.task_id] = "capacity"

        # 6. Clean up dispatch records for DONE tasks
        for item in work_items:
            task = tasks.get(item.task_id, {})
            if task.get("status", "").upper() == "DONE":
                dispatches.pop(item.task_id, None)

        # 7. Save state
        state["dispatches"] = dispatches
        self._save_state(state)

        return {
            "posted": posted,
            "skipped": skipped,
            "principal": principal,
            "role": self.config.role,
        }

    def status(self) -> Dict[str, Any]:
        """Get current lane status without dispatching."""
        principal = self.parser.verify_spec()
        tasks = self._task_index()
        work_items = self.parser.parse()

        projection = []
        counts: Dict[str, int] = {}
        for item in work_items:
            task = tasks.get(item.task_id, {})
            task_status = task.get("status", "NOT_SEEDED").upper()
            counts[task_status] = counts.get(task_status, 0) + 1
            projection.append({
                "id": item.task_id,
                "status": task_status,
                "claimed_by": task.get("claimed_by"),
                "blocked_by": list(item.blocked_by),
                "verification_status": task.get("verification_status"),
            })

        return {
            "principal": principal,
            "role": self.config.role,
            "counts": counts,
            "tasks": projection,
        }

    def watch(self, interval: Optional[int] = None) -> None:
        """Run the watch loop. Dispatches tasks at each interval.

        Handles transient failures gracefully — only exits after 10
        consecutive failures.
        """
        interval = interval or self.config.poll_interval
        if interval < 5:
            raise ValueError("watch interval must be at least 5 seconds")

        consecutive_failures = 0
        while True:
            try:
                result = self.dispatch()
                print(json.dumps({"success": True, **result}, sort_keys=True), flush=True)
                consecutive_failures = 0
            except Exception as exc:
                consecutive_failures += 1
                print(
                    json.dumps(
                        {
                            "success": False,
                            "error": str(exc),
                            "consecutive_failures": consecutive_failures,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                if consecutive_failures >= 10:
                    print(
                        json.dumps(
                            {
                                "success": False,
                                "error": f"watcher exiting after {consecutive_failures} consecutive failures",
                                "fatal": True,
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    raise
            time.sleep(interval)
