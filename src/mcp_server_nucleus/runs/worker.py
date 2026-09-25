from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from mcp_server_nucleus.runtime.liveness import redact_secrets

from .models import CommandKind, RunState
from .runners import RunnerResult
from .store import RunStore, StaleLease
from .verification import VerificationBundle
from .verifiers import NoopVerifier, VerificationResult, Verifier
from .workspace import Workspace, WorkspaceBackend, WorkspaceError, WorkspaceResolver


class WorkerCleanupError(Exception):
    pass


class WorkerLeaseLost(Exception):
    pass


class _WorkerCancelled(Exception):
    pass


class _HandlerContext:
    def __init__(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        fencing_token: int,
        worker,
        workspace: Workspace | None = None,
        workspace_backend: WorkspaceBackend | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._owner_id = owner_id
        self._fencing_token = fencing_token
        self._worker = worker
        self.workspace = workspace
        self.workspace_backend = workspace_backend
        self.cancel_event = cancel_event

    def emit(self, event_type: str, payload: dict | None = None):
        self._worker._check_heartbeat_failure()
        result = self._store.append_event(
            self._run_id,
            event_type,
            payload,
            owner_id=self._owner_id,
            fencing_token=self._fencing_token,
        )
        self._worker._check_heartbeat_failure()
        return result

    def check_cancelled(self):
        for command in self._store.list_commands(self._run_id, include_consumed=False):
            if command.kind is CommandKind.CANCEL:
                self._store.consume_command(
                    command.id,
                    self._owner_id,
                    self._fencing_token,
                )
                self._store.transition_run(
                    self._run_id,
                    RunState.CANCELLED,
                    "run.cancelled",
                    owner_id=self._owner_id,
                    fencing_token=self._fencing_token,
                )
                self._worker._check_heartbeat_failure()
                raise _WorkerCancelled()
        self._worker._check_heartbeat_failure()


class RunWorker:
    def __init__(
        self,
        store: RunStore,
        run_id: str,
        owner_id: str,
        lease_ttl_seconds: int = 30,
        heartbeat_interval_seconds: float | None = None,
        workspace_resolver: WorkspaceResolver | None = None,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._owner_id = owner_id
        self._lease_ttl_seconds = lease_ttl_seconds
        if heartbeat_interval_seconds is None:
            self._heartbeat_interval_seconds = max(0.1, self._lease_ttl_seconds / 3)
        elif heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        else:
            self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._resource = f"run:{run_id}"
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_lock = threading.Lock()
        self._heartbeat_error: BaseException | None = None
        self._workspace_resolver = workspace_resolver
        self._workspace: Workspace | None = None
        self._workspace_backend: WorkspaceBackend | None = None

    def _root_uri_to_path(self, root_uri: str) -> Path:
        parsed = urlparse(root_uri)
        if parsed.scheme in ("", "file"):
            return Path(parsed.path)
        raise WorkspaceError(f"unsupported project root scheme: {root_uri}")

    def _prepare_workspace(self, lease) -> Workspace | None:
        if self._workspace_resolver is None:
            return None
        project = self._store.get_project_for_run(self._run_id)
        project_root = self._root_uri_to_path(project.root_uri)
        backend = self._workspace_resolver.resolve_backend(project_root)
        workspace = backend.create(project_root, self._run_id)
        self._workspace_backend = backend
        self._store.set_run_workspace(
            self._run_id,
            workspace=str(workspace.target_path),
            base_revision=workspace.base_revision,
            owner_id=self._owner_id,
            fencing_token=lease.fencing_token,
        )
        return workspace

    def _finalize_runner_result(
        self,
        result: RunnerResult,
        verifier_results: list[VerificationResult],
        fencing_token: int,
        candidate_drifted: bool = False,
    ) -> None:
        run = self._store.get_run(self._run_id)
        project = self._store.get_project_for_run(self._run_id)

        self._store.record_usage(
            self._run_id,
            tokens=None,
            cost=None,
            source="unknown",
            confidence="low",
            quota_class="free",
            model_family=result.model_family,
            model_id=result.model_id,
            vendor=result.vendor,
            duration=result.duration,
        )

        patch = None
        if result.diff_artifact:
            patch = VerificationBundle.with_artifact(
                "patch",
                result.diff_artifact,
                mimetype="text/x-diff",
            )

        stdout_log = VerificationBundle.with_artifact(
            "stdout_log",
            result.output.encode("utf-8"),
            mimetype="text/plain",
        )

        events = self._store.list_events(self._run_id)
        work_log_data = json.dumps(
            [
                {
                    "seq": e.seq,
                    "type": e.type,
                    "payload": e.payload,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            default=str,
        ).encode("utf-8")
        work_log = VerificationBundle.with_artifact(
            "work_log",
            work_log_data,
            mimetype="application/json",
        )

        route = {
            "vendor": result.vendor,
            "model": result.model_id or run.model_id,
            "execution_target": run.execution_target,
            "policy": project.trust_mode,
        }
        usage = {
            "tokens": None,
            "cost": None,
            "source": "unknown",
            "confidence": "low",
            "quota_class": "free",
            "model_family": result.model_family,
            "model_id": result.model_id,
            "vendor": result.vendor,
            "duration": round(result.duration, 3),
            "redacted": result.redacted,
            "rc": result.rc,
        }
        usage.update(result.metadata.get("usage", {}))

        test_report = None
        for vr in verifier_results:
            if vr.artifact is not None:
                test_report = vr.artifact
                break

        verifier_failed = any(not vr.success for vr in verifier_results)

        bundle = VerificationBundle(
            status=result.status,
            output=result.output,
            diff_sha256=patch.sha256 if patch else "",
            diff_size=patch.size if patch else 0,
            is_clean=result.is_clean,
            base_revision=self._workspace.base_revision if self._workspace else None,
            metadata={
                "vendor": result.vendor,
                "model_family": result.model_family,
                "model_id": result.model_id,
                "rc": result.rc,
                "redacted": result.redacted,
                "duration": round(result.duration, 3),
            },
            patch=patch,
            test_report=test_report,
            stdout_log=stdout_log,
            work_log=work_log,
            target_head_at_review=self._workspace.base_revision if self._workspace else "",
            route=route,
            usage=usage,
            unknowns=list(result.metadata.get("unknowns", [])),
            verdict="ok",
            warning=False,
        )

        # Candidate drift: the check command mutated the workspace after the
        # diff was captured.  Block apply and fail the run.
        if candidate_drifted:
            bundle.verdict = "failed"
            bundle.reason = "CANDIDATE_CHANGED_DURING_CHECK"
            bundle.apply_eligible = False
            self._store.transition_run(
                self._run_id,
                RunState.FAILED,
                "run.failed",
                payload=asdict(bundle),
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
            return

        # Determine whether a real (non-noop) check was run and passed.
        real_check_run = any(vr.status != "not_run" for vr in verifier_results)
        real_check_passed = any(
            vr.success and vr.status == "ok" for vr in verifier_results
        )
        real_check_failed = any(
            (not vr.success) and vr.status != "not_run" for vr in verifier_results
        )
        # apply_eligible: a real check passed (or no check was configured),
        # candidate didn't drift, and there is a real diff to apply.
        # A real check that failed blocks apply.
        if real_check_failed:
            bundle.apply_eligible = False
        else:
            bundle.apply_eligible = (
                (real_check_passed or not real_check_run)
                and not candidate_drifted
                and not result.is_clean
            )

        # S3-4: terminal-state honesty pre-checks before the verifier loop.
        if result.status == "timed_out":
            if result.diff_artifact or result.output.strip():
                bundle.warning = True
                bundle.reason = "timeout_with_valid_artifacts"
                self._store.transition_run(
                    self._run_id,
                    RunState.READY_FOR_REVIEW,
                    "run.ready_for_review",
                    payload=asdict(bundle),
                    owner_id=self._owner_id,
                    fencing_token=fencing_token,
                )
            else:
                bundle.verdict = "failed"
                bundle.reason = "timeout_no_output"
                self._store.transition_run(
                    self._run_id,
                    RunState.FAILED,
                    "run.failed",
                    payload=asdict(bundle),
                    owner_id=self._owner_id,
                    fencing_token=fencing_token,
                )
            return

        if (
            result.rc == 0
            and not result.output.strip()
            and not result.diff_artifact
        ):
            bundle.verdict = "failed"
            bundle.reason = "INVALID_RUNNER_RESULT"
            self._store.transition_run(
                self._run_id,
                RunState.FAILED,
                "run.failed",
                payload=asdict(bundle),
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
            return

        if (
            result.status in (
                "empty_output",
                "not_found",
                "budget_rejected",
                "prompt_too_large",
                "error",
            )
            and not result.diff_artifact
        ):
            bundle.verdict = "failed"
            bundle.reason = result.status
            self._store.transition_run(
                self._run_id,
                RunState.FAILED,
                "run.failed",
                payload=asdict(bundle),
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
            return

        if verifier_failed:
            bundle.status = "failed"
            bundle.verdict = "test_failed"
            bundle.warning = True
            bundle_payload = asdict(bundle)
            if result.status == "cancelled":
                self._store.transition_run(
                    self._run_id,
                    RunState.CANCELLED,
                    "run.cancelled",
                    payload=bundle_payload,
                    owner_id=self._owner_id,
                    fencing_token=fencing_token,
                )
            else:
                self._store.transition_run(
                    self._run_id,
                    RunState.READY_FOR_REVIEW,
                    "run.ready_for_review",
                    payload=bundle_payload,
                    owner_id=self._owner_id,
                    fencing_token=fencing_token,
                )
            return

        bundle_payload = asdict(bundle)

        if result.status in ("ok", "empty_output") and not result.is_clean:
            self._store.transition_run(
                self._run_id,
                RunState.READY_FOR_REVIEW,
                "run.ready_for_review",
                payload=bundle_payload,
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
        elif result.status in ("ok", "empty_output") and result.is_clean:
            self._store.transition_run(
                self._run_id,
                RunState.COMPLETED,
                "run.completed",
                payload=bundle_payload,
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
        elif result.status == "cancelled":
            bundle.verdict = "failed"
            bundle_payload = asdict(bundle)
            self._store.transition_run(
                self._run_id,
                RunState.CANCELLED,
                "run.cancelled",
                payload=bundle_payload,
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )
        else:
            bundle.verdict = "failed"
            bundle_payload = asdict(bundle)
            self._store.transition_run(
                self._run_id,
                RunState.FAILED,
                "run.failed",
                payload=bundle_payload,
                owner_id=self._owner_id,
                fencing_token=fencing_token,
            )

    def _check_heartbeat_failure(self):
        with self._heartbeat_lock:
            err = self._heartbeat_error
        if err is not None:
            raise WorkerLeaseLost("heartbeat lost") from err

    def _candidate_identity(self) -> str:
        """Return a SHA-256 hash of the current workspace diff.

        Used to freeze candidate identity before verification and detect
        drift if the check command mutates the workspace after the diff was
        captured.
        """
        if self._workspace is None or self._workspace_backend is None:
            return ""
        try:
            diff = self._workspace_backend.diff(self._workspace)
            return hashlib.sha256(diff).hexdigest()
        except WorkspaceError:
            return ""

    def _heartbeat_loop(self, fencing_token: int) -> None:
        while not self._heartbeat_stop.wait(self._heartbeat_interval_seconds):
            try:
                self._store.renew_lease(
                    self._resource,
                    self._owner_id,
                    fencing_token,
                    self._lease_ttl_seconds,
                )
            except (StaleLease, sqlite3.Error) as exc:
                with self._heartbeat_lock:
                    if self._heartbeat_error is None:
                        self._heartbeat_error = exc
                self._heartbeat_stop.set()
                break

    def _stop_heartbeat(self):
        if self._heartbeat_thread is not None:
            self._heartbeat_stop.set()
            self._heartbeat_thread.join()
            self._heartbeat_thread = None

    def execute(
        self,
        handler,
        verifiers: list[Verifier] | None = None,
    ):
        if verifiers is None:
            verifiers = [NoopVerifier()]
        lease = None
        cancel_event = threading.Event()
        poll_stop = threading.Event()

        def _poll_cancel():
            while not poll_stop.wait(0.2):
                try:
                    for command in self._store.list_commands(
                        self._run_id, include_consumed=False
                    ):
                        if command.kind is CommandKind.CANCEL:
                            self._store.consume_command(
                                command.id,
                                self._owner_id,
                                lease.fencing_token if lease else 0,
                            )
                            self._store.transition_run(
                                self._run_id,
                                RunState.CANCELLED,
                                "run.cancelled",
                                owner_id=self._owner_id,
                                fencing_token=lease.fencing_token if lease else 0,
                            )
                            cancel_event.set()
                            return
                except Exception:
                    pass

        try:
            lease = self._store.acquire_lease(
                self._resource,
                self._owner_id,
                self._lease_ttl_seconds,
            )

            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                args=(lease.fencing_token,),
                name=f"nucleus-run-heartbeat-{self._run_id}",
                daemon=True,
            )
            self._heartbeat_thread.start()

            run = self._store.get_run(self._run_id)
            if run.state is RunState.CREATED:
                self._store.transition_run(
                    self._run_id,
                    RunState.QUEUED,
                    "run.queued",
                    owner_id=self._owner_id,
                    fencing_token=lease.fencing_token,
                )

            for command in self._store.list_commands(self._run_id, include_consumed=False):
                if command.kind is CommandKind.CANCEL:
                    self._store.consume_command(
                        command.id,
                        self._owner_id,
                        lease.fencing_token,
                    )
                    self._store.transition_run(
                        self._run_id,
                        RunState.CANCELLED,
                        "run.cancelled",
                        owner_id=self._owner_id,
                        fencing_token=lease.fencing_token,
                    )
                    return

            self._store.transition_run(
                self._run_id,
                RunState.PREPARING,
                "run.preparing",
                owner_id=self._owner_id,
                fencing_token=lease.fencing_token,
            )
            try:
                self._workspace = self._prepare_workspace(lease)
            except Exception as exc:
                redacted, _ = redact_secrets(str(exc))
                self._store.transition_run(
                    self._run_id,
                    RunState.FAILED,
                    "run.failed",
                    payload={
                        "error_type": type(exc).__name__,
                        "message": redacted[:512],
                        "phase": "workspace_prepare",
                    },
                    owner_id=self._owner_id,
                    fencing_token=lease.fencing_token,
                )
                raise

            self._store.transition_run(
                self._run_id,
                RunState.RUNNING,
                "run.running",
                owner_id=self._owner_id,
                fencing_token=lease.fencing_token,
            )

            poll_thread = threading.Thread(target=_poll_cancel, daemon=True)
            poll_thread.start()

            ctx = _HandlerContext(
                self._store,
                self._run_id,
                self._owner_id,
                lease.fencing_token,
                self,
                workspace=self._workspace,
                workspace_backend=self._workspace_backend,
                cancel_event=cancel_event,
            )
            try:
                result = handler(ctx)
                ctx.check_cancelled()
            except _WorkerCancelled:
                return
            except WorkerLeaseLost:
                try:
                    self._store.transition_run(
                        self._run_id,
                        RunState.FAILED,
                        "run.failed",
                        payload={"error_type": "WorkerLeaseLost", "phase": "lease"},
                        owner_id=self._owner_id,
                        fencing_token=lease.fencing_token,
                    )
                except Exception:
                    pass
                raise
            except Exception as exc:
                redacted, _ = redact_secrets(str(exc))
                persisted = redacted[:512]
                self._store.transition_run(
                    self._run_id,
                    RunState.FAILED,
                    "run.failed",
                    payload={
                        "error_type": type(exc).__name__,
                        "message": persisted,
                    },
                    owner_id=self._owner_id,
                    fencing_token=lease.fencing_token,
                )
                raise

            verifier_results: list[VerificationResult] = []
            candidate_drifted = False
            if isinstance(result, RunnerResult):
                self._store.transition_run(
                    self._run_id,
                    RunState.VERIFYING,
                    "run.verifying",
                    owner_id=self._owner_id,
                    fencing_token=lease.fencing_token,
                )
                # Freeze candidate identity before verification so we can
                # detect if the check command mutates the workspace.
                identity_before = self._candidate_identity()
                try:
                    verifier_results = [v.verify(ctx) for v in verifiers]
                except Exception as exc:
                    redacted, _ = redact_secrets(str(exc))
                    self._store.transition_run(
                        self._run_id,
                        RunState.FAILED,
                        "run.failed",
                        payload={
                            "error_type": type(exc).__name__,
                            "message": redacted[:512],
                            "phase": "verification",
                        },
                        owner_id=self._owner_id,
                        fencing_token=lease.fencing_token,
                    )
                    raise
                identity_after = self._candidate_identity()
                candidate_drifted = (
                    identity_before != "" and identity_after != "" and identity_before != identity_after
                )

            self._stop_heartbeat()
            self._check_heartbeat_failure()

            if isinstance(result, RunnerResult):
                self._finalize_runner_result(
                    result, verifier_results, lease.fencing_token,
                    candidate_drifted=candidate_drifted,
                )
            else:
                self._store.transition_run(
                    self._run_id,
                    RunState.COMPLETED,
                    "run.completed",
                    owner_id=self._owner_id,
                    fencing_token=lease.fencing_token,
                )
        finally:
            poll_stop.set()
            if 'poll_thread' in locals():
                poll_thread.join(timeout=1.0)
            self._stop_heartbeat()
            if lease is not None:
                try:
                    self._store.release_lease(
                        self._resource,
                        self._owner_id,
                        lease.fencing_token,
                    )
                except Exception as exc:
                    raise WorkerCleanupError("lease cleanup failed") from exc
