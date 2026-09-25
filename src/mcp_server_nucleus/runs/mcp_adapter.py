"""MCP/ACP adapter exposing the Renaissance run engine to AionUi and clients."""
from __future__ import annotations

import dataclasses
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import RunState
from .policy import ExecutionPolicy
from .runners import VendorCliRunner
from .service import RunService
from .store import RunStore, Session
from .targets import InProcessExecutionTarget
from .verifiers import NoopVerifier
from .workspace import WorkspaceResolver


@dataclass
class RunToolResponse:
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), default=str, indent=2)


class RunMcpAdapter:
    """Headless run-engine adapter for MCP/ACP clients."""

    def __init__(self, db_path: str | Path) -> None:
        self._store = RunStore(str(db_path))
        self._service = RunService(self._store, workspace_resolver=WorkspaceResolver())

    def _run_to_dict(self, run):
        return {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "runner_id": run.runner_id,
            "model_id": run.model_id,
            "execution_target": run.execution_target,
            "mode": run.mode,
            "prompt": run.prompt,
            "state": run.state.value,
            "workspace": run.workspace,
            "base_revision": run.base_revision,
            "requirements": run.requirements,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }

    def create_project(self, root_uri: str, trust_mode: str = "default") -> str:
        project = self._store.create_project(root_uri, trust_mode)
        return project.id

    def get_project_by_root(self, root_uri: str) -> dict | None:
        project = self._store.get_project_by_root(root_uri)
        if project is None:
            return None
        return {
            "id": project.id,
            "root_uri": project.root_uri,
            "trust_mode": project.trust_mode,
            "policy_json": project.policy_json,
            "created_at": project.created_at.isoformat(),
        }

    def get_or_create_project(self, root_uri: str, trust_mode: str) -> str:
        project = self._store.get_project_by_root(root_uri)
        if project is not None:
            if project.trust_mode != trust_mode:
                project = self._store.set_project_trust_mode(project.id, trust_mode)
            return project.id
        project = self._store.create_project(root_uri, trust_mode)
        return project.id

    def create_conversation(self, project_id: str, title: str) -> str:
        conv = self._store.create_conversation(project_id, title)
        return conv.id

    def create_run(
        self,
        conversation_id: str,
        prompt: str,
        runner_id: str = "",
        model_id: str = "",
        execution_target: str = "local",
        mode: str = "write",
        idempotency_key: str = "",
        requirements: str | None = None,
    ) -> str:
        runner_id = runner_id or os.environ.get("NUCLEUS_DEFAULT_RUNNER", "agy")
        model_id = model_id or os.environ.get("NUCLEUS_DEFAULT_MODEL", "")
        run = self._store.create_run(
            conversation_id=conversation_id,
            runner_id=runner_id,
            model_id=model_id,
            execution_target=execution_target,
            mode=mode,
            idempotency_key=idempotency_key or f"{conversation_id}-{runner_id}",
            prompt=prompt,
            requirements=requirements,
        )
        self._service.queue_run(run.id)
        return run.id

    def queue_run(self, run_id: str) -> None:
        """Queue an existing run for the dispatcher."""
        self._service.queue_run(run_id)

    def list_runs(self, conversation_id: str | None = None) -> list[dict]:
        return [self._run_to_dict(r) for r in self._store.list_runs(conversation_id)]

    def show_run(self, run_id: str) -> dict:
        run = self._store.get_run(run_id)
        events = self._store.list_events(run_id)
        bundle = self._service.get_run_bundle(run_id)
        return {
            "run": self._run_to_dict(run),
            "events": [
                {"seq": e.seq, "type": e.type, "payload": e.payload, "created_at": e.created_at.isoformat()}
                for e in events
            ],
            "bundle": asdict(bundle),
            "usage": bundle.usage,
        }

    def export_run(self, run_id: str) -> dict:
        """Return a full portable snapshot of a run and its related records."""
        run = self._store.get_run(run_id)
        project = self._store.get_project_for_run(run_id)
        conversation = self._store.get_conversation(run.conversation_id)
        events = self._store.list_events(run_id)
        artifacts = self._store.list_artifacts(run_id)
        usage = self._store.get_usage(run_id)
        bundle = self._service.get_run_bundle(run_id)

        return {
            "project": asdict(project),
            "conversation": asdict(conversation),
            "run": self._run_to_dict(run),
            "events": [
                {"seq": e.seq, "type": e.type, "payload": e.payload, "created_at": e.created_at.isoformat()}
                for e in events
            ],
            "artifacts": [asdict(a) for a in artifacts],
            "usage": asdict(usage) if usage else None,
            "bundle": asdict(bundle),
        }

    def apply_run(self, run_id: str) -> RunToolResponse:
        try:
            bundle = self._service.apply_run(run_id)
            run = self._store.get_run(run_id)
            # The apply is only successful if the run reached APPLIED state.
            # A returned conflict/blocked bundle means the apply failed.
            success = run.state == RunState.APPLIED
            return RunToolResponse(
                success=success,
                data={"run": self._run_to_dict(run), "bundle": asdict(bundle)},
                error=None if success else (bundle.reason or bundle.status or "apply_failed"),
            )
        except Exception as exc:  # noqa: BLE001
            return RunToolResponse(success=False, error=str(exc))

    def dismiss_run(self, run_id: str) -> RunToolResponse:
        try:
            bundle = self._service.dismiss_run(run_id)
            run = self._store.get_run(run_id)
            return RunToolResponse(
                success=True,
                data={"run": self._run_to_dict(run), "bundle": asdict(bundle)},
            )
        except Exception as exc:  # noqa: BLE001
            return RunToolResponse(success=False, error=str(exc))

    def cancel_run(self, run_id: str, issuer: str = "user") -> RunToolResponse:
        try:
            self._service.request_cancel(run_id, issuer)
            run = self._store.get_run(run_id)
            return RunToolResponse(success=True, data={"run": self._run_to_dict(run)})
        except Exception as exc:  # noqa: BLE001
            return RunToolResponse(success=False, error=str(exc))

    def execute_run(self, run_id: str, target: str = "in-process") -> dict:
        target = os.environ.get("NUCLEUS_EXECUTION_TARGET", target)

        if target not in ("in-process", "subprocess"):
            raise ValueError(f"unsupported execution target {target!r}")

        run = self._store.get_run(run_id)
        model = run.model_id or None
        runner = VendorCliRunner(run.runner_id, model=model, mode=run.mode)

        def _handler_factory():
            def _handler(ctx):
                if ctx.workspace is None or ctx.workspace_backend is None:
                    raise RuntimeError("no workspace")
                project = self._store.get_project_for_run(run_id)
                policy = ExecutionPolicy.from_trust_mode(project.trust_mode)
                return runner.run(
                    run.prompt,
                    ctx.workspace,
                    ctx.workspace_backend,
                    policy,
                    timeout_s=3600,
                    cancel_event=ctx.cancel_event,
                )

            return _handler

        if target == "subprocess":
            from .targets import SubprocessExecutionTarget

            SubprocessExecutionTarget().run(
                self._store,
                run_id,
                owner_id="acp",
                handler_factory=_handler_factory,
                verifiers=[NoopVerifier()],
                wait=False,
            )
        else:
            InProcessExecutionTarget().run(
                self._store,
                run_id,
                owner_id="acp",
                handler_factory=_handler_factory,
                verifiers=[NoopVerifier()],
            )
        return self.show_run(run_id)

    def create_session(
        self,
        session_id: str,
        run_id: str,
        conversation_id: str,
        project_id: str,
        cwd: str | None = None,
        prompt: str = "",
    ) -> Session:
        return self._store.create_session(session_id, run_id, conversation_id, project_id, cwd, prompt)

    def get_session(self, session_id: str) -> Session | None:
        try:
            return self._store.get_session(session_id)
        except ValueError:
            return None

    def get_run_for_session(self, session_id: str) -> dict | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        try:
            run = self._store.get_run(session.run_id)
        except ValueError:
            return None
        return self._run_to_dict(run)

    def list_sessions(self) -> list[Session]:
        return self._store.list_sessions()

    def update_session(self, session_id: str, **kwargs: Any) -> Session:
        return self._store.update_session(session_id, **kwargs)
