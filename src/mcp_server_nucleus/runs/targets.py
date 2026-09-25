"""Execution targets for Renaissance workers.

R6: bake-off between in-process, subprocess, and macOS sandbox isolation.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import RunState
from .policy import ExecutionPolicy
from .runners import RunnerResult, VendorCliRunner
from .store import RunStore
from .worker import RunWorker
from .workspace import Workspace, WorkspaceResolver, _workspace_root


class TargetError(Exception):
    """Base for target execution failures."""


class TargetResult:
    """Outcome of a target execution."""

    def __init__(self, success: bool, state: RunState | None = None, error: str | None = None) -> None:
        self.success = success
        self.state = state
        self.error = error


class ExecutionTarget(Protocol):
    """Pluggable runner execution target."""

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory: Callable[[], Callable],
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        ...


class InProcessExecutionTarget:
    """Runs the worker in the same process. Default for trusted hosts."""

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory: Callable[[], Callable],
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        resolver = WorkspaceResolver()
        worker = RunWorker(store, run_id, owner_id, workspace_resolver=resolver)
        try:
            worker.execute(handler_factory(), verifiers=verifiers)
        except Exception as exc:  # noqa: BLE001
            return TargetResult(False, error=str(exc))
        run = store.get_run(run_id)
        return TargetResult(
            success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
            state=run.state,
        )


class SubprocessExecutionTarget:
    """Runs the worker in a detached subprocess so the ACP server can die and resume."""

    def _find_worker_pid(self, store: RunStore, run_id: str) -> int | None:
        for event in reversed(store.list_events(run_id)):
            if event.type == "subprocess_worker" and event.payload.get("pid"):
                return int(event.payload["pid"])
        return None

    def _is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, OSError):
            return False
        return True

    def _wait_for_terminal(
        self,
        store: RunStore,
        run_id: str,
        timeout: float = 300.0,
        poll_interval: float = 0.25,
    ) -> TargetResult:
        deadline = time.monotonic() + timeout
        terminal = {
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.APPLIED,
            RunState.DISMISSED,
            RunState.FAILED,
            RunState.CANCELLED,
        }
        while time.monotonic() < deadline:
            run = store.get_run(run_id)
            if run.state in terminal:
                return TargetResult(
                    success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
                    state=run.state,
                )
            time.sleep(poll_interval)
        run = store.get_run(run_id)
        return TargetResult(
            success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
            state=run.state,
            error=f"timed out after {timeout}s waiting for terminal state",
        )

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory: Callable[[], Callable],
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        # The worker module itself cannot take a serialized handler, so the
        # subprocess is used only to exercise the process boundary. For a
        # vendor CLI runner, the vendor and model are passed on argv and the
        # standard VendorCliRunner handler is used. Verifiers are not yet
        # serialized across the subprocess boundary; worker_main uses the
        # default NoopVerifier.
        run = store.get_run(run_id)

        # If a previous detached worker is still alive, just re-attach.
        existing_pid = self._find_worker_pid(store, run_id)
        if existing_pid is not None and self._is_alive(existing_pid):
            if wait:
                return self._wait_for_terminal(store, run_id)
            return TargetResult(
                success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
                state=run.state,
            )

        db_path = store._db_path
        runner = run.runner_id or os.environ.get("NUCLEUS_DEFAULT_RUNNER", "agy")
        model = run.model_id or ""
        if model:
            try:
                from mcp_server_nucleus.runtime.vendor_dispatch import resolve_model
                model = resolve_model(runner, model)
            except Exception:
                model = ""
        # Run the worker module directly with this process's interpreter so the
        # child has the same package path and environment. Relying on the
        # ``nucleus-run-worker`` wrapper on PATH can resolve to a stale or
        # unrelated installation, which breaks the subprocess target test and can
        # run the wrong code in production.
        cmd = [
            sys.executable,
            "-m",
            "mcp_server_nucleus.runs.worker_main",
            "--db",
            str(db_path),
            "--run",
            run_id,
            "--owner",
            owner_id,
            "--runner",
            runner,
        ]
        if model:
            cmd.extend(["--model", model])

        env = dict(os.environ)
        env["NUCLEUS_EXECUTION_TARGET"] = "subprocess"

        log_dir = db_path.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{run_id}.log"

        with open(log_path, "ab") as log_f:
            proc = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )

        # Record the worker launch so resume can re-attach instead of spawning twice.
        store.append_event(
            run_id,
            "subprocess_worker",
            payload={"pid": proc.pid, "command": " ".join(str(c) for c in cmd)},
            owner_id=owner_id,
        )
        if wait:
            return self._wait_for_terminal(store, run_id)
        run = store.get_run(run_id)
        return TargetResult(
            success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
            state=run.state,
        )


@dataclass
class MacSandboxExecutionTarget:
    """Runs the worker under macOS sandbox-exec with a deny-by-default profile.

    Generated profile denies all operations by default, denies network, allows
    reads from a small set of system paths plus the workspace base, and only
    allows writes to the workspace target and a per-run temp directory.
    """

    profile: str | None = None

    def build_profile(
        self,
        workspace: Workspace,
        temp_dir: Path | None = None,
    ) -> str:
        """Return a Seatbelt profile string for this workspace."""
        import importlib.util
        import sysconfig
        from urllib.parse import urlparse

        base = Path(urlparse(str(workspace.base_path)).path).resolve()
        target = Path(urlparse(str(workspace.target_path)).path).resolve()
        home = Path.home()

        python_raw = shutil.which("python3") or sys.executable
        python = Path(python_raw).expanduser().resolve()
        git_raw = shutil.which("git") or "/usr/bin/git"
        git = Path(git_raw).expanduser().resolve()

        def _subpath(path: Path) -> str:
            return f'(subpath "{path}")'

        def _literal(path: Path) -> str:
            return f'(literal "{path}")'

        # Required read paths plus paths needed to actually run Python.
        read_paths: list[Path] = [
            base,
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/opt"),
            Path("/System"),
            Path("/dev/null"),
        ]

        python_unresolved = Path(python_raw).expanduser()
        git_unresolved = Path(git_raw).expanduser()
        for extra in (
            python,
            python.parent,
            python.parent.parent,
            python_unresolved,
            python_unresolved.parent,
            python_unresolved.parent.parent,
            git,
            git.parent,
            git.parent.parent,
            git_unresolved,
            git_unresolved.parent,
            git_unresolved.parent.parent,
        ):
            if extra not in read_paths:
                read_paths.append(extra)

        for key in ("stdlib", "purelib", "platlib"):
            try:
                p = Path(sysconfig.get_path(key)).expanduser().resolve()
                if p not in read_paths and p.exists():
                    read_paths.append(p)
            except Exception:
                pass

        spec = importlib.util.find_spec("mcp_server_nucleus")
        if spec is not None and spec.origin:
            pkg = Path(spec.origin).expanduser().resolve()
            if pkg not in read_paths:
                read_paths.append(pkg)
            if pkg.parent not in read_paths:
                read_paths.append(pkg.parent)
        elif spec is not None and spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                p = Path(loc).expanduser().resolve()
                if p not in read_paths:
                    read_paths.append(p)
                if p.parent not in read_paths:
                    read_paths.append(p.parent)

        read_filters = [_subpath(p) if p.name != "null" else _literal(p) for p in read_paths]

        process_filters = [
            _subpath(Path("/usr/bin")),
            _subpath(Path("/bin")),
            _subpath(Path("/sbin")),
            _subpath(Path("/opt/homebrew/bin")),
            _literal(Path(python_raw).expanduser()),
            _literal(python),
            _subpath(python.parent),
            _subpath(python_unresolved.parent),
            _subpath(git_unresolved.parent),
            _literal(Path(git_raw).expanduser()),
            _literal(git),
        ]

        write_filters = [_subpath(target)]
        if temp_dir is not None:
            resolved_temp = Path(urlparse(str(temp_dir)).path).resolve()
            write_filters.append(_subpath(resolved_temp))
        all_write_filters = write_filters
        all_write_filters.append(_literal(Path("/dev/tty")))

        lines = [
            "(version 1)",
            "(deny default)",
            "(deny network*)",
            f'(allow process-exec {" ".join(process_filters)})',
            f'(allow file-read* {" ".join(read_filters)})',
            f'(allow file-write* {" ".join(all_write_filters)})',
            f'(deny file-write* {_subpath(base)} {_subpath(home / ".ssh")} {_subpath(home / ".aws")} {_subpath(home / ".gnupg")} {_subpath(base / ".git")} {_subpath(target / ".git")})',
        ]
        return "\n".join(lines) + "\n"

    def _transition_to_waiting(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
    ) -> None:
        run = store.get_run(run_id)
        path = [
            RunState.CREATED,
            RunState.QUEUED,
            RunState.PREPARING,
            RunState.RUNNING,
            RunState.WAITING_APPROVAL,
        ]
        if run.state not in path:
            return
        idx = path.index(run.state)
        for state in path[idx + 1 :]:
            payload = {}
            if state is RunState.WAITING_APPROVAL:
                payload = {"reason": "sandbox_exec_unavailable"}
            store.transition_run(
                run_id,
                state,
                f"run.{state.value}",
                payload=payload,
                owner_id=owner_id,
            )

    def run(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        handler_factory: Callable[[], Callable],
        verifiers: list | None = None,
        wait: bool = True,
    ) -> TargetResult:
        if shutil.which("sandbox-exec") is None:
            self._transition_to_waiting(store, run_id, owner_id)
            return TargetResult(False, error="sandbox-exec unavailable")

        from urllib.parse import urlparse

        db_path = store._db_path
        project = store.get_project_for_run(run_id)
        project_root = Path(urlparse(project.root_uri).path).resolve()

        # Per-run temp directory under the brain's runs directory.
        runs_dir = db_path.parent
        run_temp = runs_dir / "tmp" / run_id
        run_temp.mkdir(parents=True, exist_ok=True)

        resolver = WorkspaceResolver()
        backend = resolver.resolve_backend(project_root)
        target_path = _workspace_root() / backend._target_name(run_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        workspace = Workspace(
            run_id=run_id,
            base_path=project_root,
            target_path=target_path,
            base_revision="",
            backend_name=backend.name,
        )

        profile = (
            self.profile
            if self.profile is not None
            else self.build_profile(workspace, temp_dir=run_temp)
        )
        profile_path = run_temp / f"{run_id}.sb"
        profile_path.write_text(profile, encoding="utf-8")

        python = shutil.which("python3") or sys.executable
        cmd = [
            "sandbox-exec",
            "-f",
            str(profile_path),
            python,
            "-m",
            "mcp_server_nucleus.runs.worker_main",
            "--db",
            str(db_path),
            "--run",
            run_id,
            "--owner",
            owner_id,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
            profile_path.unlink(missing_ok=True)
            if proc.returncode != 0:
                return TargetResult(False, error=f"sandbox failed: {proc.stderr or proc.stdout}")
        except subprocess.TimeoutExpired as exc:
            profile_path.unlink(missing_ok=True)
            return TargetResult(False, error=f"sandbox timed out: {exc}")
        run = store.get_run(run_id)
        return TargetResult(
            success=run.state in (RunState.READY_FOR_REVIEW, RunState.COMPLETED, RunState.APPLIED, RunState.DISMISSED),
            state=run.state,
        )
