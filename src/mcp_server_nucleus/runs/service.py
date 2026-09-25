"""High-level run orchestration service."""
from __future__ import annotations

import hashlib
import re
import shlex
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import Artifact, CommandKind, RunState
from .store import RunStore
from .verification import ApplyNotReady, ArtifactRef, VerificationBundle
from .workspace import Workspace, WorkspaceError, WorkspaceResolver

_URL_RE = re.compile(r"https?://\S+")


class RunService:
    def __init__(
        self,
        store: RunStore,
        workspace_resolver: WorkspaceResolver | None = None,
    ) -> None:
        self._store = store
        self._workspace_resolver = workspace_resolver

    def queue_run(self, run_id: str):
        return self._store.transition_run(run_id, RunState.QUEUED, "run.queued")

    def preflight(
        self,
        project_root: str | Path,
        runner_id: str,
        check_argv: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Preflight checks before creating a run.

        Returns (ok, reason).  If not ok, reason explains the blocker.
        """
        root = Path(project_root)
        if not root.exists():
            return False, f"project root does not exist: {root}"
        if not (root / ".git").exists():
            return False, f"not a git repository: {root}"
        # Check for a valid HEAD.
        import subprocess
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root, capture_output=True, timeout=5, check=False,
            )
            if result.returncode != 0:
                return False, "git repository has no commits (empty HEAD)"
        except (subprocess.TimeoutExpired, OSError) as exc:
            return False, f"git rev-parse HEAD failed: {exc}"
        # Check for dirty working tree (uncommitted changes).
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root, capture_output=True, timeout=5, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return False, "working tree is dirty (uncommitted changes)"
        except (subprocess.TimeoutExpired, OSError):
            pass
        # Check runner is available (if not a known test runner).
        if runner_id and runner_id not in ("agy", "noop", "test"):
            from shutil import which
            if not which(runner_id):
                return False, f"runner '{runner_id}' not found on PATH"
        return True, ""

    def submit_run(
        self,
        project_root: str | Path,
        prompt: str,
        runner_id: str = "agy",
        model_id: str = "",
        execution_target: str = "local",
        mode: str = "write",
        trust_mode: str = "default",
        check_argv: list[str] | None = None,
        check_name: str | None = None,
        check_timeout: int = 300,
        idempotency_key: str = "",
    ) -> tuple[str | None, str]:
        """Create a project, conversation, and queued run with preflight.

        Returns (run_id, reason).  If run_id is None, reason explains the blocker.
        """
        ok, reason = self.preflight(project_root, runner_id, check_argv)
        if not ok:
            return None, reason

        project = self._store.create_project(f"file://{Path(project_root).resolve()}", trust_mode)
        conv = self._store.create_conversation(project.id, prompt or "submit")

        requirements_json = None
        if check_argv:
            import json
            req_obj = {
                "check": {
                    "name": check_name or "approved_check",
                    "argv": check_argv,
                    "timeout": check_timeout,
                }
            }
            requirements_json = json.dumps(req_obj)

        run = self._store.create_run(
            conversation_id=conv.id,
            runner_id=runner_id,
            model_id=model_id,
            execution_target=execution_target,
            mode=mode,
            idempotency_key=idempotency_key or f"{conv.id}-{runner_id}",
            prompt=prompt,
            requirements=requirements_json,
        )
        self.queue_run(run.id)
        return run.id, ""

    def request_cancel(self, run_id: str, issuer: str):
        return self._store.enqueue_command(run_id, CommandKind.CANCEL, None, issuer)

    def get_run_bundle(self, run_id: str) -> VerificationBundle:
        """Return the most recent verification bundle for a run, or an empty one.

        Recovers evidence from any terminal event that carries a bundle
        payload, not just ``run.ready_for_review``.  This ensures that
        failed, cancelled, and completed runs also expose their evidence
        for review.
        """

        def _ref_from_dict(data: dict | None) -> ArtifactRef | None:
            if data is None:
                return None
            return ArtifactRef(
                sha256=data.get("sha256", ""),
                path=data.get("path", ""),
                size=data.get("size", 0),
                mimetype=data.get("mimetype"),
            )

        def _usage_from_payload_or_store(payload: dict) -> dict:
            usage = payload.get("usage")
            if usage:
                return usage
            usage_row = self._store.get_usage(run_id)
            if usage_row is None:
                return {}
            return {
                "run_id": usage_row.run_id,
                "tokens": usage_row.tokens,
                "cost": usage_row.cost,
                "source": usage_row.source,
                "confidence": usage_row.confidence,
                "quota_class": usage_row.quota_class,
                "model_family": usage_row.model_family,
                "model_id": usage_row.model_id,
                "vendor": usage_row.vendor,
                "duration": usage_row.duration,
            }

        # Events that carry a full bundle payload.
        _BUNDLE_EVENTS = frozenset({
            "run.ready_for_review",
            "run.completed",
            "run.failed",
            "run.cancelled",
            "run.apply_failed",
        })

        events = self._store.list_events(run_id)
        for ev in reversed(events):
            if ev.type in _BUNDLE_EVENTS:
                payload = ev.payload or {}
                # Only return if the payload actually has bundle-like fields.
                if "status" in payload or "patch" in payload or "verdict" in payload:
                    return VerificationBundle(
                        status=payload.get("status", "ready_for_review"),
                        output=payload.get("output", ""),
                        diff_sha256=payload.get("diff_sha256", ""),
                        diff_size=payload.get("diff_size", 0),
                        is_clean=payload.get("is_clean", False),
                        base_revision=payload.get("base_revision"),
                        metadata=payload.get("metadata", {}),
                        patch=_ref_from_dict(payload.get("patch")),
                        test_report=_ref_from_dict(payload.get("test_report")),
                        stdout_log=_ref_from_dict(payload.get("stdout_log")),
                        stderr_log=_ref_from_dict(payload.get("stderr_log")),
                        work_log=_ref_from_dict(payload.get("work_log")),
                        target_head_at_review=payload.get("target_head_at_review", ""),
                        route=payload.get("route", {}),
                        usage=_usage_from_payload_or_store(payload),
                        unknowns=payload.get("unknowns", []),
                        verdict=payload.get("verdict", "ok"),
                        warning=payload.get("warning", False),
                        reason=payload.get("reason"),
                        apply_eligible=payload.get("apply_eligible", False),
                    )
        return VerificationBundle(status="none", output="")

    def _reconstruct_workspace(self, run_id: str) -> tuple[Workspace, Any]:
        if self._workspace_resolver is None:
            raise WorkspaceError("RunService has no WorkspaceResolver")
        run = self._store.get_run(run_id)
        if run.workspace is None:
            raise WorkspaceError(f"Run {run_id!r} has no workspace")
        project = self._store.get_project_for_run(run_id)
        project_root = Path(urlparse(project.root_uri).path)
        backend = self._workspace_resolver.resolve_backend(project_root)
        workspace = Workspace(
            run_id=run.id,
            base_path=project_root,
            target_path=Path(run.workspace),
            base_revision=run.base_revision,
            backend_name=backend.name,
        )
        return workspace, backend

    def apply_run(self, run_id: str) -> VerificationBundle:
        """Apply a run's reviewed patch to the base, if it is safe.

        Binds to the reviewed patch identity (from the verification bundle)
        rather than recomputing an unbound workspace diff.  Fails closed if:
        - ``apply_eligible`` is False (no real check passed, or candidate drifted)
        - the reviewed patch is missing or corrupt
        - the base has drifted since review
        - the apply itself conflicts
        """
        run = self._store.get_run(run_id)
        # Repeated apply of an already-APPLIED run returns the recorded result
        # without reapplying the patch.
        if run.state is RunState.APPLIED:
            bundle = self.get_run_bundle(run_id)
            return replace(bundle, status="applied", reason="already_applied")
        if run.state not in (RunState.READY_FOR_REVIEW, RunState.COMPLETED):
            raise ApplyNotReady(
                f"Run {run_id!r} is {run.state.value}, expected ready_for_review or completed"
            )

        workspace, backend = self._reconstruct_workspace(run_id)
        bundle = self.get_run_bundle(run_id)

        # Fail closed if the run is not apply-eligible.
        if not bundle.apply_eligible:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "not_apply_eligible",
                    "base_revision": workspace.base_revision,
                    "verdict": bundle.verdict,
                    "warning": bundle.warning,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="not_apply_eligible",
            )

        # Clean run (no diff): apply is a no-op.
        if bundle.is_clean or not bundle.diff_size:
            self._store.transition_run(
                run_id,
                RunState.APPLIED,
                "run.applied",
                {"reason": "no_diff", "base_revision": workspace.base_revision},
            )
            return bundle

        # Bind to the reviewed patch identity.
        if bundle.patch is None or not bundle.patch.sha256:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "no_reviewed_patch",
                    "base_revision": workspace.base_revision,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="no_reviewed_patch",
            )

        # Read the reviewed patch from the artifact store and verify integrity.
        try:
            patch_bytes = VerificationBundle.read_artifact(bundle.patch)
        except ValueError as exc:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "artifact_integrity_error",
                    "error": str(exc),
                    "base_revision": workspace.base_revision,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="ARTIFACT_INTEGRITY_ERROR",
                output=str(exc),
            )

        if patch_bytes is None:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "patch_missing",
                    "base_revision": workspace.base_revision,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="patch_missing",
            )

        # Verify the patch hash matches what was reviewed.
        actual_hash = hashlib.sha256(patch_bytes).hexdigest()
        if actual_hash != bundle.patch.sha256:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "patch_hash_mismatch",
                    "expected": bundle.patch.sha256,
                    "actual": actual_hash,
                    "base_revision": workspace.base_revision,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="ARTIFACT_INTEGRITY_ERROR",
                output=f"hash mismatch: expected {bundle.patch.sha256}, got {actual_hash}",
            )

        # Check for base drift since review.
        if bundle.base_revision and workspace.base_revision != bundle.base_revision:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.apply_failed",
                {
                    "reason": "base_drift",
                    "reviewed_base": bundle.base_revision,
                    "current_base": workspace.base_revision,
                },
            )
            return replace(
                bundle,
                status="apply_blocked",
                reason="base_drift",
            )

        if not patch_bytes:
            self._store.transition_run(
                run_id,
                RunState.APPLIED,
                "run.applied",
                {"reason": "no_diff", "base_revision": workspace.base_revision},
            )
            return bundle

        self._store.transition_run(run_id, RunState.APPLYING, "run.applying", {"diff_size": len(patch_bytes)})

        try:
            backend.apply(workspace, patch_bytes)
            self._store.transition_run(
                run_id,
                RunState.APPLIED,
                "run.applied",
                {
                    "diff_sha256": bundle.patch.sha256,
                    "diff_size": len(patch_bytes),
                    "base_revision": workspace.base_revision,
                },
            )
            return bundle
        except Exception as exc:
            conflict_bundle = replace(
                bundle,
                status="apply_conflict",
                reason="APPLY_CONFLICT",
                output=str(exc),
            )
            # A failed apply is not terminal: the run returns to
            # READY_FOR_REVIEW so the operator can clean the base and retry.
            self._store.transition_run(
                run_id,
                RunState.READY_FOR_REVIEW,
                "run.apply_failed",
                {
                    "reason": "apply_conflict",
                    "base_revision": workspace.base_revision,
                    "error": str(exc),
                },
            )
            return conflict_bundle

    def dismiss_run(self, run_id: str) -> VerificationBundle:
        """Dismiss a run; no changes are applied to the base."""
        run = self._store.get_run(run_id)
        if run.state not in (
            RunState.READY_FOR_REVIEW,
            RunState.COMPLETED,
            RunState.APPLYING,
        ):
            raise ApplyNotReady(
                f"Run {run_id!r} is {run.state.value}, cannot dismiss"
            )

        bundle = self.get_run_bundle(run_id)
        self._store.transition_run(
            run_id,
            RunState.DISMISSED,
            "run.dismissed",
            {"base_revision": run.base_revision},
        )
        return bundle

    def preview_run(
        self,
        run_id: str,
        command: str | list[str],
        timeout_s: float = 120,
    ) -> Artifact | None:
        workspace, _ = self._reconstruct_workspace(run_id)
        if isinstance(command, (list, tuple)):
            command = shlex.join(command)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(workspace.target_path),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.preview_failed",
                {"command": command, "reason": "timeout", "timeout_s": timeout_s},
            )
            return None

        if proc.returncode != 0:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.preview_failed",
                {
                    "command": command,
                    "returncode": proc.returncode,
                    "stderr": proc.stderr,
                },
            )
            return None

        url = self._extract_url(proc.stdout)
        if url is None:
            self._store.transition_run(
                run_id,
                RunState.FAILED,
                "run.preview_failed",
                {"command": command, "reason": "no_url", "stdout": proc.stdout},
            )
            return None

        url_bytes = url.encode()
        artifact = self._store.record_artifact(
            run_id,
            "preview_url",
            hashlib.sha256(url_bytes).hexdigest(),
            "text/x-preview-url",
            len(url_bytes),
            metadata={"url": url},
        )
        self._store.transition_run(
            run_id,
            RunState.PREVIEWED,
            "run.previewed",
            {"command": command, "url": url, "artifact_id": artifact.id},
        )
        return artifact

    def _extract_url(self, text: str) -> str | None:
        match = _URL_RE.search(text)
        return match.group(0) if match else None
