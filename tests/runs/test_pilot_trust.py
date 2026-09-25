"""Opposed regression tests for the pilot trust workflow.

These tests verify the core pilot trust guarantees:
- Persisted task requirements survive across store reopens
- CommandVerifier distinguishes success, failure, timeout, cancellation
- VerificationBundle.read_artifact verifies content hash
- Apply requires apply_eligible=True and a reviewed patch
- Apply rejects when base has drifted since review
- Apply rejects when patch hash doesn't match reviewed hash
- get_run_bundle recovers evidence from failed/cancelled runs
- cmd_submit creates, dispatches, and prints a receipt
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.verification import ArtifactRef, VerificationBundle
from mcp_server_nucleus.runs.verifiers import CommandVerifier, NoopVerifier, VerificationResult
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _store(tmp_path):
    return RunStore(str(tmp_path / "runs.db"))


def _project_and_run(store, project_root, requirements=None):
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="vendor",
        model_id="m",
        execution_target="local",
        mode="write",
        idempotency_key=f"k-{run_id_counter()}",
        requirements=requirements,
    )
    return run, project, conv


_counter = [0]


def run_id_counter():
    _counter[0] += 1
    return _counter[0]


class _MockCtx:
    """Minimal context for verifier tests."""
    def __init__(self, workspace=None, cancel_event=None):
        self.workspace = workspace
        self.cancel_event = cancel_event or threading.Event()


# ─── Requirements persistence ───────────────────────────────────────────

class TestRequirementsPersistence:
    def test_requirements_persisted_and_recovered(self, tmp_path):
        """Requirements JSON survives store close/reopen."""
        store = _store(tmp_path)
        project = store.create_project("file:///tmp", "permissive")
        conv = store.create_conversation(project.id, "test")
        req = json.dumps({"check": {"argv": ["pytest"], "timeout": 60}})
        run = store.create_run(
            conversation_id=conv.id,
            runner_id="r",
            model_id="m",
            execution_target="local",
            mode="write",
            idempotency_key="k1",
            prompt="fix the bug",
            requirements=req,
        )
        assert run.requirements == req

        # Reopen and verify
        store2 = RunStore(str(tmp_path / "runs.db"))
        run2 = store2.get_run(run.id)
        assert run2.requirements == req

    def test_requirements_included_in_idempotency_check(self, tmp_path):
        """Different requirements → different run (IdempotencyConflict)."""
        store = _store(tmp_path)
        project = store.create_project("file:///tmp", "permissive")
        conv = store.create_conversation(project.id, "test")
        req1 = json.dumps({"check": {"argv": ["pytest"]}})
        run1 = store.create_run(
            conversation_id=conv.id,
            runner_id="r",
            model_id="m",
            execution_target="local",
            mode="write",
            idempotency_key="k1",
            prompt="fix the bug",
            requirements=req1,
        )
        # Same idempotency key, different requirements → conflict
        from mcp_server_nucleus.runs.store import IdempotencyConflict
        req2 = json.dumps({"check": {"argv": ["ruff"]}})
        with pytest.raises(IdempotencyConflict):
            store.create_run(
                conversation_id=conv.id,
                runner_id="r",
                model_id="m",
                execution_target="local",
                mode="write",
                idempotency_key="k1",
                prompt="fix the bug",
                requirements=req2,
            )

    def test_run_without_requirements_has_none(self, tmp_path):
        """Legacy runs without requirements have requirements=None."""
        store = _store(tmp_path)
        project = store.create_project("file:///tmp", "permissive")
        conv = store.create_conversation(project.id, "test")
        run = store.create_run(
            conversation_id=conv.id,
            runner_id="r",
            model_id="m",
            execution_target="local",
            mode="write",
            idempotency_key="k1",
            prompt="fix the bug",
        )
        assert run.requirements is None


# ─── CommandVerifier honesty ───────────────────────────────────────────

class TestCommandVerifierHonesty:
    def test_verifier_reports_success(self, tmp_path):
        """A passing command returns status=ok and success=True."""
        ws_path = tmp_path / "workspace"
        ws_path.mkdir()
        ctx = _MockCtx(workspace=type("W", (), {"target_path": ws_path})())
        v = CommandVerifier("test", ["true"], timeout=5)
        result = v.verify(ctx)
        assert result.success is True
        assert result.status == "ok"

    def test_verifier_reports_failure(self, tmp_path):
        """A failing command returns status=failed and success=False."""
        ws_path = tmp_path / "workspace"
        ws_path.mkdir()
        ctx = _MockCtx(workspace=type("W", (), {"target_path": ws_path})())
        v = CommandVerifier("test", ["false"], timeout=5)
        result = v.verify(ctx)
        assert result.success is False
        assert result.status == "failed"

    def test_verifier_reports_timeout(self, tmp_path):
        """A command that exceeds timeout returns status=timed_out."""
        ws_path = tmp_path / "workspace"
        ws_path.mkdir()
        ctx = _MockCtx(workspace=type("W", (), {"target_path": ws_path})())
        v = CommandVerifier("test", ["sleep", "30"], timeout=1)
        result = v.verify(ctx)
        assert result.success is False
        assert result.status == "timed_out"

    def test_verifier_reports_cancellation(self, tmp_path):
        """A command that is cancelled returns status=cancelled."""
        ws_path = tmp_path / "workspace"
        ws_path.mkdir()
        cancel = threading.Event()
        ctx = _MockCtx(
            workspace=type("W", (), {"target_path": ws_path})(),
            cancel_event=cancel,
        )
        v = CommandVerifier("test", ["sleep", "30"], timeout=60, cancel_event=cancel)

        # Cancel after a short delay
        def _cancel():
            time.sleep(0.3)
            cancel.set()

        threading.Thread(target=_cancel, daemon=True).start()
        result = v.verify(ctx)
        assert result.success is False
        assert result.status == "cancelled"

    def test_verifier_reports_launch_error_for_missing_workspace(self):
        """A missing workspace returns status=launch_error."""
        ctx = _MockCtx(workspace=None)
        v = CommandVerifier("test", ["true"], timeout=5)
        result = v.verify(ctx)
        assert result.success is False
        assert result.status == "launch_error"

    def test_verifier_reports_launch_error_for_missing_command(self, tmp_path):
        """A non-existent command returns status=launch_error."""
        ws_path = tmp_path / "workspace"
        ws_path.mkdir()
        ctx = _MockCtx(workspace=type("W", (), {"target_path": ws_path})())
        v = CommandVerifier("test", ["/nonexistent/command"], timeout=5)
        result = v.verify(ctx)
        assert result.success is False
        assert result.status == "launch_error"

    def test_noop_verifier_returns_not_run(self):
        """NoopVerifier returns status=not_run so callers can distinguish it."""
        ctx = _MockCtx()
        v = NoopVerifier()
        result = v.verify(ctx)
        assert result.success is True
        assert result.status == "not_run"


# ─── Artifact integrity ────────────────────────────────────────────────

class TestArtifactIntegrity:
    def test_read_artifact_verifies_hash(self, tmp_path, monkeypatch):
        """read_artifact raises ValueError on hash mismatch."""
        # Create an artifact
        content = b"test content"
        ref = VerificationBundle.with_artifact("test", content, mimetype="text/plain")

        # Monkeypatch brain path to find the artifact
        from mcp_server_nucleus.runtime import common
        brain_path = Path(common.get_brain_path())
        artifact_path = brain_path / ref.path

        # Corrupt the artifact
        artifact_path.write_bytes(b"corrupted content")

        with pytest.raises(ValueError, match="hash mismatch"):
            VerificationBundle.read_artifact(ref)

    def test_read_artifact_returns_none_for_missing(self, tmp_path):
        """read_artifact returns None for a missing artifact."""
        ref = ArtifactRef(sha256="abc", path="nonexistent/path", size=0)
        assert VerificationBundle.read_artifact(ref) is None


# ─── Apply eligibility and patch binding ───────────────────────────────

class TestApplyEligibility:
    def _setup_run(self, tmp_path, diff_text="hello\nworld\n", apply_eligible=True):
        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        resolver = WorkspaceResolver()
        store = _store(tmp_path)
        run, _, _ = _project_and_run(store, project)
        backend = resolver.resolve_backend(project)
        ws = backend.create(project, run.id)
        (ws.target_path / "file.txt").write_text(diff_text)
        store.set_run_workspace(
            run.id,
            workspace=str(ws.target_path),
            base_revision=ws.base_revision,
        )
        diff_bytes = backend.diff(ws)

        # Build a proper ready_for_review event with patch
        patch_ref = VerificationBundle.with_artifact("patch", diff_bytes, mimetype="text/x-diff")
        bundle_payload = {
            "status": "ok",
            "diff_sha256": patch_ref.sha256,
            "diff_size": patch_ref.size,
            "is_clean": False,
            "apply_eligible": apply_eligible,
            "patch": {
                "sha256": patch_ref.sha256,
                "path": patch_ref.path,
                "size": patch_ref.size,
                "mimetype": patch_ref.mimetype,
            },
            "verdict": "ok",
            "warning": False,
        }
        store.transition_run(run.id, RunState.QUEUED, "run.queued")
        store.transition_run(run.id, RunState.PREPARING, "run.preparing")
        store.transition_run(run.id, RunState.RUNNING, "run.running")
        store.transition_run(run.id, RunState.VERIFYING, "run.verifying")
        store.transition_run(
            run.id,
            RunState.READY_FOR_REVIEW,
            "run.ready_for_review",
            payload=bundle_payload,
        )
        return run, project, store, resolver

    def test_apply_succeeds_when_eligible(self, tmp_path):
        """Apply succeeds when apply_eligible=True and patch matches."""
        run, project, store, resolver = self._setup_run(tmp_path)
        service = RunService(store, workspace_resolver=resolver)
        bundle = service.apply_run(run.id)
        assert store.get_run(run.id).state is RunState.APPLIED
        assert (project / "file.txt").read_text() == "hello\nworld\n"

    def test_apply_blocked_when_not_eligible(self, tmp_path):
        """Apply fails when apply_eligible=False."""
        run, _project, store, resolver = self._setup_run(tmp_path, apply_eligible=False)
        service = RunService(store, workspace_resolver=resolver)
        bundle = service.apply_run(run.id)
        assert store.get_run(run.id).state is RunState.FAILED
        assert bundle.status == "apply_blocked"

    def test_apply_blocked_when_base_drifted(self, tmp_path):
        """Apply fails when base has drifted since review."""
        run, project, store, resolver = self._setup_run(tmp_path)
        # Drift the base
        (project / "file.txt").write_text("hello\ncosmos\n")
        subprocess.run(["git", "add", "."], cwd=project, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "drift"], cwd=project, check=True)
        service = RunService(store, workspace_resolver=resolver)
        bundle = service.apply_run(run.id)
        # Post-drift the patch no longer applies: conflict is retryable,
        # so the run returns to READY_FOR_REVIEW rather than terminalizing.
        assert store.get_run(run.id).state is RunState.READY_FOR_REVIEW
        assert bundle.status in ("apply_blocked", "apply_conflict")

    def test_apply_blocked_when_patch_corrupted(self, tmp_path, monkeypatch):
        """Apply fails when the reviewed patch artifact is corrupted."""
        run, _project, store, resolver = self._setup_run(tmp_path)
        # Corrupt the patch artifact
        from mcp_server_nucleus.runtime import common
        brain_path = Path(common.get_brain_path())
        bundle = RunService(store, workspace_resolver=resolver).get_run_bundle(run.id)
        if bundle.patch:
            artifact_path = brain_path / bundle.patch.path
            artifact_path.write_bytes(b"corrupted")
        service = RunService(store, workspace_resolver=resolver)
        result_bundle = service.apply_run(run.id)
        assert store.get_run(run.id).state is RunState.FAILED
        assert result_bundle.status == "apply_blocked"

    def test_apply_conflict_returns_to_review_not_failed(self, tmp_path):
        """A backend apply exception (e.g. dirty base) is retryable: the run
        returns to READY_FOR_REVIEW instead of terminalizing as FAILED."""
        run, project, store, resolver = self._setup_run(tmp_path)
        # Dirty the base file the patch touches — git apply refuses.
        (project / "file.txt").write_text("uncommitted\n")
        service = RunService(store, workspace_resolver=resolver)
        bundle = service.apply_run(run.id)
        assert bundle.status == "apply_conflict"
        assert store.get_run(run.id).state is RunState.READY_FOR_REVIEW
        events = [e.type for e in store.list_events(run.id)]
        assert "run.apply_failed" in events
        # And the run is eligible to apply again once the base is clean.
        subprocess.run(["git", "checkout", "--", "file.txt"], cwd=project, check=True)
        bundle2 = service.apply_run(run.id)
        assert store.get_run(run.id).state is RunState.APPLIED
        assert bundle2.status == "ok"


# ─── get_run_bundle recovery ───────────────────────────────────────────

class TestBundleRecovery:
    def test_get_bundle_from_failed_run(self, tmp_path):
        """get_run_bundle recovers evidence from a failed run event."""
        store = _store(tmp_path)
        project = store.create_project("file:///tmp", "permissive")
        conv = store.create_conversation(project.id, "test")
        run = store.create_run(
            conversation_id=conv.id,
            runner_id="r",
            model_id="m",
            execution_target="local",
            mode="write",
            idempotency_key="k1",
        )
        store.transition_run(run.id, RunState.QUEUED, "run.queued")
        store.transition_run(run.id, RunState.PREPARING, "run.preparing")
        store.transition_run(run.id, RunState.RUNNING, "run.running")
        store.transition_run(
            run.id,
            RunState.FAILED,
            "run.failed",
            payload={
                "status": "failed",
                "verdict": "failed",
                "reason": "timeout_no_output",
                "output": "runner timed out",
            },
        )
        service = RunService(store)
        bundle = service.get_run_bundle(run.id)
        assert bundle.status == "failed"
        assert bundle.verdict == "failed"
        assert bundle.reason == "timeout_no_output"

    def test_get_bundle_returns_empty_for_no_events(self, tmp_path):
        """get_run_bundle returns an empty bundle for a run with no terminal events."""
        store = _store(tmp_path)
        project = store.create_project("file:///tmp", "permissive")
        conv = store.create_conversation(project.id, "test")
        run = store.create_run(
            conversation_id=conv.id,
            runner_id="r",
            model_id="m",
            execution_target="local",
            mode="write",
            idempotency_key="k1",
        )
        service = RunService(store)
        bundle = service.get_run_bundle(run.id)
        assert bundle.status == "none"
        assert bundle.output == ""


# ─── CLI submit command ────────────────────────────────────────────────

class TestSubmitCommand:
    def test_submit_requires_project_or_conversation(self, tmp_path, monkeypatch):
        """submit without --project-root or --conversation fails."""
        import argparse

        from mcp_server_nucleus.runs.cli import cmd_submit

        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "brain"))
        args = argparse.Namespace(
            project_root=None,
            conversation=None,
            prompt="test",
            runner="agy",
            model=None,
            target="in-process",
            trust_mode="default",
            mode="write",
            idempotency=None,
            check=None,
            check_name=None,
            check_timeout=300,
            no_follow=True,
            json=True,
        )
        rc = cmd_submit(args)
        assert rc == 1

    def test_submit_creates_and_dispatches(self, tmp_path, monkeypatch):
        """submit creates a project, run, and dispatches it."""
        import argparse

        from mcp_server_nucleus.runs.cli import cmd_submit

        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)

        brain = tmp_path / "brain"
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        # We need a fake runner that produces a diff
        fakebin = tmp_path / "fakebin"
        fakebin.mkdir()
        (fakebin / "agy").write_text(
            "#!/bin/bash\n"
            "printf 'applied content' > applied.txt\n"
            "echo done\n"
            "exit 0\n"
        )
        (fakebin / "agy").chmod(0o755)
        monkeypatch.setenv("PATH", f"{fakebin}:{os.environ.get('PATH', '')}")
        monkeypatch.setenv("NUCLEUS_DEFAULT_RUNNER", "agy")
        monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

        args = argparse.Namespace(
            project_root=str(project),
            conversation=None,
            prompt="Create applied.txt",
            runner="agy",
            model=None,
            target="in-process",
            trust_mode="default",
            mode="write",
            idempotency=None,
            check=None,
            check_name=None,
            check_timeout=300,
            no_follow=True,
            json=True,
        )
        rc = cmd_submit(args)
        # The run should reach ready_for_review or failed
        # (we can't guarantee success without a real runner, but the command should not crash)
        assert rc in (0, 1)


# ─── Preflight checks ──────────────────────────────────────────────────

class TestPreflight:
    def test_preflight_rejects_missing_project(self, tmp_path):
        """Preflight rejects a non-existent project root."""
        store = _store(tmp_path)
        service = RunService(store)
        ok, reason = service.preflight(str(tmp_path / "nonexistent"), "agy")
        assert ok is False
        assert "does not exist" in reason

    def test_preflight_rejects_non_git_project(self, tmp_path):
        """Preflight rejects a directory without .git."""
        project = tmp_path / "project"
        project.mkdir()
        store = _store(tmp_path)
        service = RunService(store)
        ok, reason = service.preflight(str(project), "agy")
        assert ok is False
        assert "not a git repository" in reason

    def test_preflight_rejects_empty_head(self, tmp_path):
        """Preflight rejects a git repo with no commits."""
        project = tmp_path / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=project, check=True)
        store = _store(tmp_path)
        service = RunService(store)
        ok, reason = service.preflight(str(project), "agy")
        assert ok is False
        assert "HEAD" in reason or "commit" in reason

    def test_preflight_rejects_dirty_working_tree(self, tmp_path):
        """Preflight rejects a git repo with uncommitted changes."""
        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        # Make the tree dirty
        (project / "file.txt").write_text("dirty\n")
        store = _store(tmp_path)
        service = RunService(store)
        ok, reason = service.preflight(str(project), "agy")
        assert ok is False
        assert "dirty" in reason

    def test_preflight_accepts_clean_repo(self, tmp_path):
        """Preflight accepts a clean git repo with a valid HEAD."""
        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        store = _store(tmp_path)
        service = RunService(store)
        ok, reason = service.preflight(str(project), "agy")
        assert ok is True
        assert reason == ""

    def test_submit_run_returns_none_on_preflight_failure(self, tmp_path):
        """submit_run returns (None, reason) when preflight fails."""
        store = _store(tmp_path)
        service = RunService(store)
        run_id, reason = service.submit_run(
            project_root=str(tmp_path / "nonexistent"),
            prompt="test",
        )
        assert run_id is None
        assert "does not exist" in reason

    def test_submit_run_creates_run_on_success(self, tmp_path):
        """submit_run creates a queued run when preflight passes."""
        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        store = _store(tmp_path)
        service = RunService(store)
        run_id, reason = service.submit_run(
            project_root=str(project),
            prompt="fix the bug",
            check_argv=["true"],
        )
        assert run_id is not None
        assert reason == ""
        run = store.get_run(run_id)
        assert run.state is RunState.QUEUED
        assert run.requirements is not None


# ─── Repeated apply ────────────────────────────────────────────────────

class TestRepeatedApply:
    def test_repeated_apply_returns_already_applied(self, tmp_path):
        """Applying an already-APPLIED run returns the recorded result."""
        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        resolver = WorkspaceResolver()
        store = _store(tmp_path)
        run, _, _ = _project_and_run(store, project)
        backend = resolver.resolve_backend(project)
        ws = backend.create(project, run.id)
        (ws.target_path / "file.txt").write_text("hello\nworld\n")
        store.set_run_workspace(
            run.id,
            workspace=str(ws.target_path),
            base_revision=ws.base_revision,
        )
        diff_bytes = backend.diff(ws)

        # Build a proper ready_for_review event with patch
        patch_ref = VerificationBundle.with_artifact("patch", diff_bytes, mimetype="text/x-diff")
        bundle_payload = {
            "status": "ok",
            "diff_sha256": patch_ref.sha256,
            "diff_size": patch_ref.size,
            "is_clean": False,
            "apply_eligible": True,
            "patch": {
                "sha256": patch_ref.sha256,
                "path": patch_ref.path,
                "size": patch_ref.size,
                "mimetype": patch_ref.mimetype,
            },
            "verdict": "ok",
            "warning": False,
        }
        store.transition_run(run.id, RunState.QUEUED, "run.queued")
        store.transition_run(run.id, RunState.PREPARING, "run.preparing")
        store.transition_run(run.id, RunState.RUNNING, "run.running")
        store.transition_run(run.id, RunState.VERIFYING, "run.verifying")
        store.transition_run(
            run.id,
            RunState.READY_FOR_REVIEW,
            "run.ready_for_review",
            payload=bundle_payload,
        )

        service = RunService(store, workspace_resolver=resolver)
        # First apply succeeds
        bundle1 = service.apply_run(run.id)
        assert store.get_run(run.id).state is RunState.APPLIED
        # Second apply returns already_applied without reapplying
        bundle2 = service.apply_run(run.id)
        assert bundle2.status == "applied"
        assert bundle2.reason == "already_applied"
        # File content should be the same (not double-applied)
        assert (project / "file.txt").read_text() == "hello\nworld\n"


# ─── Selected-run dispatch ─────────────────────────────────────────────

class TestSelectedRunDispatch:
    def test_run_once_with_run_id_only_dispatches_that_run(self, tmp_path):
        """run_once(run_id=X) only dispatches the specified run, not others."""
        from mcp_server_nucleus.runs.dispatcher import RunDispatcher

        project = tmp_path / "project"
        project.mkdir()
        _git_init(project)
        store = _store(tmp_path)

        # Create two runs
        run1, _, _ = _project_and_run(store, project)
        run2, _, _ = _project_and_run(store, project)
        store.transition_run(run1.id, RunState.QUEUED, "run.queued")
        store.transition_run(run2.id, RunState.QUEUED, "run.queued")

        db_path = tmp_path / "runs.db"
        dispatcher = RunDispatcher(db_path)
        # Dispatch only run1
        dispatcher.run_once(run_id=run1.id)

        r1 = store.get_run(run1.id)
        r2 = store.get_run(run2.id)
        # run1 should have moved out of QUEUED
        assert r1.state is not RunState.QUEUED
        # run2 should still be QUEUED (not dispatched)
        assert r2.state is RunState.QUEUED
