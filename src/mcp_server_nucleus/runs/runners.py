"""High-level runner bridge: workspace + policy + vendor CLI."""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..runtime.vendor_dispatch import (
    DEFAULT_MODE,
    VendorCLIExecutor,
    normalize_mode,
)
from .policy import Decision, Effect, EffectKind, ExecutionPolicy
from .workspace import Workspace, WorkspaceBackend, WorkspaceError


@dataclass
class RunnerResult:
    """Outcome of a single run inside a workspace."""

    vendor: str
    model_family: str
    model_id: str
    rc: int | None
    status: str
    output: str
    duration: float
    redacted: int = 0
    diff_artifact: bytes = b""
    is_clean: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class Runner(Protocol):
    """Pluggable runner for the Renaissance run engine."""

    def run(
        self,
        prompt: str,
        workspace: Workspace,
        workspace_backend: WorkspaceBackend,
        policy: ExecutionPolicy,
        *,
        timeout_s: int = 3600,
        cancel_event: threading.Event | None = None,
        stream_callback: Callable[[str], None] | None = None,
    ) -> RunnerResult:
        ...


class VendorCliRunner:
    """Runs a vendor CLI inside a workspace, with policy, streaming, and cancellation."""

    def __init__(self, vendor: str, model: str | None = None, mode: str = DEFAULT_MODE) -> None:
        self.vendor = vendor
        self.model = model
        self.mode = normalize_mode(mode)

    def _check_policy(
        self, policy: ExecutionPolicy, workspace: Workspace
    ) -> RunnerResult | None:
        effect = Effect(
            kind=EffectKind.FILESYSTEM,
            action="write" if self.mode == "write" else "read",
            path=str(workspace.target_path),
        )
        decision = policy.evaluate(effect)
        if decision is Decision.DENY:
            return RunnerResult(
                vendor=self.vendor,
                model_family="",
                model_id=self.model or "",
                rc=None,
                status="policy_denied",
                output=f"policy denies {effect.action} to {workspace.target_path}",
                duration=0.0,
            )
        return None

    def run(
        self,
        prompt: str,
        workspace: Workspace,
        workspace_backend: WorkspaceBackend,
        policy: ExecutionPolicy,
        *,
        timeout_s: int = 3600,
        cancel_event: threading.Event | None = None,
        stream_callback: Callable[[str], None] | None = None,
    ) -> RunnerResult:
        denied = self._check_policy(policy, workspace)
        if denied is not None:
            return denied

        executor = VendorCLIExecutor(
            self.vendor,
            prompt,
            timeout_s=timeout_s,
            model=self.model,
            mode=self.mode,
            cwd=str(workspace.target_path),
            cancel_event=cancel_event,
            stream_callback=stream_callback,
        )
        result = executor.run()

        diff = b""
        is_clean = False
        try:
            diff = workspace_backend.diff(workspace)
            is_clean = not diff
        except WorkspaceError:
            pass

        return RunnerResult(
            vendor=result.vendor,
            model_family=result.model,
            model_id=result.model_id,
            rc=result.rc,
            status=result.status,
            output=result.result,
            duration=result.duration,
            redacted=result.redacted,
            diff_artifact=diff,
            is_clean=is_clean,
        )
