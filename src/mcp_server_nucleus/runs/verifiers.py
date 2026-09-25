"""Run verification protocol and built-in verifiers."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from dataclasses import dataclass
from typing import Protocol

from mcp_server_nucleus.runtime.liveness import redact_secrets

from .verification import ArtifactRef, VerificationBundle


@dataclass
class VerificationResult:
    """Outcome of a single verifier."""

    success: bool
    name: str
    output: bytes
    exit_code: int | None = None
    artifact: ArtifactRef | None = None
    status: str = "ok"  # ok | failed | timed_out | launch_error | cancelled | not_run


class Verifier(Protocol):
    """Pluggable run verifier."""

    def verify(self, ctx: "mcp_server_nucleus.runs.worker._HandlerContext") -> VerificationResult:
        ...


class NoopVerifier:
    """Verifier that always succeeds with no output.

    Labeled as ``not_run`` so callers can distinguish it from a real check.
    """

    def verify(self, ctx: "mcp_server_nucleus.runs.worker._HandlerContext") -> VerificationResult:
        return VerificationResult(success=True, name="noop", output=b"", status="not_run")


class CommandVerifier:
    """Verifier that runs an approved check command in the workspace.

    Hardened for the pilot trust path:
    - Rejects a missing workspace instead of falling back to caller cwd.
    - Uses argv execution (no ``shell=True``).
    - Runs the command in its own process group so cancellation kills the
      entire process tree, not just the top-level wrapper.
    - Classifies timeout, launch-error, and cancellation distinctly.
    - Redacts stdout/stderr before persisting.
    """

    def __init__(
        self,
        name: str,
        command: list[str],
        timeout: int = 300,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.timeout = timeout
        self.cancel_event = cancel_event

    def verify(self, ctx: "mcp_server_nucleus.runs.worker._HandlerContext") -> VerificationResult:
        if ctx.workspace is None:
            return VerificationResult(
                success=False,
                name=self.name,
                output=b"no workspace available for verification",
                status="launch_error",
            )
        target = str(ctx.workspace.target_path)
        if not os.path.isdir(target):
            return VerificationResult(
                success=False,
                name=self.name,
                output=b"workspace target does not exist",
                status="launch_error",
            )

        cancel = self.cancel_event or ctx.cancel_event or threading.Event()

        try:
            proc = subprocess.Popen(
                self.command,
                cwd=target,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # own process group
            )
        except (FileNotFoundError, OSError) as exc:
            redacted, _ = redact_secrets(str(exc))
            return VerificationResult(
                success=False,
                name=self.name,
                output=redacted.encode("utf-8"),
                status="launch_error",
            )

        # Poll for completion or cancellation, whichever comes first.
        deadline = None
        if self.timeout and self.timeout > 0:
            import time
            deadline = time.monotonic() + self.timeout

        timed_out = False
        cancelled = False

        while True:
            rc = proc.poll()
            if rc is not None:
                break
            if cancel.is_set():
                cancelled = True
                break
            if deadline is not None:
                import time
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
            # Wait briefly to avoid busy-spinning.
            try:
                proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass

        if timed_out or cancelled:
            # Kill the entire process group.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                proc.wait()

        stdout_data = b""
        stderr_data = b""
        if proc.stdout:
            stdout_data = proc.stdout.read()
            proc.stdout.close()
        if proc.stderr:
            stderr_data = proc.stderr.read()
            proc.stderr.close()

        combined = stdout_data + stderr_data
        redacted_text, _ = redact_secrets(combined.decode("utf-8", errors="replace"))
        redacted = redacted_text.encode("utf-8")

        artifact = VerificationBundle.with_artifact(
            "test_report",
            redacted,
            mimetype="text/plain",
        )

        if cancelled:
            return VerificationResult(
                success=False,
                name=self.name,
                output=redacted,
                exit_code=proc.returncode,
                artifact=artifact,
                status="cancelled",
            )
        if timed_out:
            return VerificationResult(
                success=False,
                name=self.name,
                output=redacted,
                exit_code=proc.returncode,
                artifact=artifact,
                status="timed_out",
            )

        return VerificationResult(
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            output=redacted,
            name=self.name,
            artifact=artifact,
            status="ok" if proc.returncode == 0 else "failed",
        )
