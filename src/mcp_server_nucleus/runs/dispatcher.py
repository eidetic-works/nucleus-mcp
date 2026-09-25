"""Real run dispatcher for the Nucleus Renaissance run engine.

The dispatcher polls the store for QUEUED runs, enforces concurrency and
per-workspace isolation, then hands each run to an ExecutionTarget. The target
(and the RunWorker it creates) is responsible for state transitions and event
appends; the dispatcher does not transition runs manually.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .hosted import HostedWorkerExecutionTarget
from .models import RunState
from .policy import ExecutionPolicy
from .runners import VendorCliRunner
from .service import RunService
from .store import LeaseConflict, RunStore, StaleLease
from .targets import (
    InProcessExecutionTarget,
    MacSandboxExecutionTarget,
    SubprocessExecutionTarget,
)
from .verifiers import NoopVerifier, Verifier
from .worker_main import _verifiers_from_requirements


class RunDispatcher:
    """Polls the run store and dispatches queued runs to execution targets."""

    _ACTIVE_STATES = frozenset(
        {RunState.RUNNING, RunState.PREPARING, RunState.VERIFYING}
    )

    def __init__(
        self,
        db_path: str | Path,
        max_concurrent: int = 3,
        poll_interval: float = 1.0,
    ) -> None:
        self._db_path = Path(db_path)
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self._store = RunStore(str(self._db_path))
        self._service = RunService(self._store)

    def _active_runs(self) -> list:
        return [r for r in self._store.list_runs() if r.state in self._ACTIVE_STATES]

    def _can_dispatch(self, run) -> bool:
        active = self._active_runs()
        if len(active) >= self.max_concurrent:
            return False
        for active_run in active:
            if active_run.workspace == run.workspace:
                return False
        return True

    def _acquire_workspace(
        self, run, owner_id: str
    ) -> Any | None:
        if run.workspace is None:
            return None
        try:
            return self._store.acquire_lease(
                f"workspace:{run.workspace}", owner_id, ttl_seconds=3600
            )
        except LeaseConflict:
            return None

    def _release_workspace(
        self, run, owner_id: str, workspace_lease: Any | None
    ) -> None:
        if workspace_lease is None or run.workspace is None:
            return
        try:
            self._store.release_lease(
                f"workspace:{run.workspace}",
                owner_id,
                workspace_lease.fencing_token,
            )
        except (StaleLease, LeaseConflict):
            pass

    def _target_for(self, run) -> InProcessExecutionTarget | SubprocessExecutionTarget | MacSandboxExecutionTarget | HostedWorkerExecutionTarget:
        project = self._store.get_project_for_run(run.id)
        if project.trust_mode == "strict":
            return MacSandboxExecutionTarget()
        if run.execution_target == "mac-sandbox":
            return MacSandboxExecutionTarget()
        if run.execution_target == "subprocess":
            return SubprocessExecutionTarget()
        if run.execution_target == "hosted":
            return HostedWorkerExecutionTarget()
        return InProcessExecutionTarget()

    def _handler_factory(self, run) -> Callable[[], Callable]:
        """Return a handler factory that runs the requested vendor CLI."""

        def _factory(_run=run) -> Callable:
            runner = VendorCliRunner(
                _run.runner_id, _run.model_id or None, mode=_run.mode
            )

            def _handler(ctx) -> Any:
                if ctx.workspace is None or ctx.workspace_backend is None:
                    raise RuntimeError("no workspace")
                project = ctx._store.get_project_for_run(ctx._run_id)
                policy = ExecutionPolicy.from_trust_mode(project.trust_mode)

                buffer: list[str] = []
                buffer_lock = threading.Lock()
                last_emit = time.monotonic()
                max_chunk_bytes = 4096

                def _flush() -> None:
                    nonlocal last_emit
                    with buffer_lock:
                        while buffer:
                            text = "".join(buffer)
                            byte_len = len(text.encode("utf-8"))
                            if byte_len <= max_chunk_bytes:
                                ctx.emit("run.output", {"chunk": text})
                                buffer.clear()
                                last_emit = time.monotonic()
                                break
                            pos = 0
                            acc = 0
                            for ch in text:
                                char_bytes = len(ch.encode("utf-8"))
                                if acc + char_bytes > max_chunk_bytes:
                                    break
                                acc += char_bytes
                                pos += 1
                            chunk = text[:pos]
                            ctx.emit("run.output", {"chunk": chunk})
                            buffer.clear()
                            buffer.append(text[pos:])
                            last_emit = time.monotonic()

                def _stream_callback(chunk: str) -> None:
                    with buffer_lock:
                        buffer.append(chunk)
                        elapsed = time.monotonic() - last_emit
                        buffered = "".join(buffer)
                        if elapsed < 1.0 and len(buffered.encode("utf-8")) < max_chunk_bytes:
                            return
                    _flush()

                try:
                    result = runner.run(
                        _run.prompt,
                        ctx.workspace,
                        ctx.workspace_backend,
                        policy,
                        timeout_s=3600,
                        cancel_event=ctx.cancel_event,
                        stream_callback=_stream_callback,
                    )
                finally:
                    _flush()
                return result

            return _handler

        return _factory

    def tick(self, owner_id: str = "dispatcher", run_id: str | None = None) -> int:
        """Dispatch queued runs that pass concurrency checks.

        Returns the number of runs handed off to an execution target in this
        tick. The target/worker is responsible for transitions and events.

        If ``run_id`` is provided, only that run is considered for dispatch;
        other queued runs are left untouched.
        """
        queued = sorted(
            (r for r in self._store.list_runs() if r.state is RunState.QUEUED),
            key=lambda r: r.created_at,
        )
        if run_id is not None:
            queued = [r for r in queued if r.id == run_id]
        dispatched = 0
        for run in queued:
            if not self._can_dispatch(run):
                continue
            workspace_lease = self._acquire_workspace(run, owner_id)
            if workspace_lease is None and run.workspace is not None:
                # Workspace is already held by another in-flight run.
                continue
            target = self._target_for(run)
            # Load persisted requirements to construct real verifiers instead
            # of always using NoopVerifier.
            verifiers = _verifiers_from_requirements(run.requirements)
            try:
                target.run(
                    self._store,
                    run.id,
                    owner_id,
                    self._handler_factory(run),
                    verifiers=verifiers,
                    wait=False,
                )
                dispatched += 1
            finally:
                self._release_workspace(run, owner_id, workspace_lease)
        return dispatched

    def run_once(self, owner_id: str = "dispatcher", run_id: str | None = None) -> int:
        """Call ``tick`` once and return the number of runs dispatched."""
        return self.tick(owner_id=owner_id, run_id=run_id)

    def _recover_abandoned_runs(self) -> list[str]:
        """Fail runs that were left active by a previous crash."""
        try:
            return self._store.recover_abandoned_runs()
        except Exception:
            return []

    def serve(self, stop_event: threading.Event | None = None) -> None:
        """Loop calling ``run_once`` until ``stop_event`` is set."""
        self._recover_abandoned_runs()
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            self.run_once()
            if stop_event is not None:
                if stop_event.wait(self.poll_interval):
                    break
            else:
                time.sleep(self.poll_interval)
