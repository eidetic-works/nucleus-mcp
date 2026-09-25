"""R4 apply/dismiss service tests."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.service import ApplyNotReady, RunService
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.verification import VerificationBundle
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


def _project_and_run(store, project_root):
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="vendor",
        model_id="m",
        execution_target="local",
        mode="write",
        idempotency_key="k1",
    )
    return run


def _set_ready_for_review(store, run, patch_bytes=None, apply_eligible=True):
    """Transition a run to READY_FOR_REVIEW with a proper bundle payload.

    If ``patch_bytes`` is provided, it is persisted as an artifact and
    referenced in the bundle.  ``apply_eligible`` controls whether the
    bundle marks the run as eligible for apply (default True for
    backward-compatibility with existing apply tests).
    """
    store.transition_run(run.id, RunState.QUEUED, "run.queued")
    store.transition_run(run.id, RunState.PREPARING, "run.preparing")
    store.transition_run(run.id, RunState.RUNNING, "run.running")
    store.transition_run(run.id, RunState.VERIFYING, "run.verifying")

    import hashlib

    from mcp_server_nucleus.runs.verification import VerificationBundle

    patch_ref = None
    diff_sha = ""
    diff_size = 0
    if patch_bytes is not None:
        patch_ref = VerificationBundle.with_artifact(
            "patch", patch_bytes, mimetype="text/x-diff"
        )
        diff_sha = patch_ref.sha256
        diff_size = patch_ref.size

    bundle_payload = {
        "status": "ok",
        "output": "",
        "diff_sha256": diff_sha,
        "diff_size": diff_size,
        "is_clean": diff_size == 0,
        "apply_eligible": apply_eligible,
        "patch": {
            "sha256": patch_ref.sha256 if patch_ref else "",
            "path": patch_ref.path if patch_ref else "",
            "size": patch_ref.size if patch_ref else 0,
            "mimetype": patch_ref.mimetype if patch_ref else None,
        } if patch_ref else None,
        "verdict": "ok",
        "warning": False,
    }
    store.transition_run(
        run.id,
        RunState.READY_FOR_REVIEW,
        "run.ready_for_review",
        payload=bundle_payload,
    )


def test_apply_run_success(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    resolver = WorkspaceResolver()
    store = _store(tmp_path)
    run = _project_and_run(store, project)

    # Simulate worker end-state: workspace created and READY_FOR_REVIEW
    backend = resolver.resolve_backend(project)
    ws = backend.create(project, run.id)
    (ws.target_path / "file.txt").write_text("hello\nworld\n")
    store.set_run_workspace(
        run.id,
        workspace=str(ws.target_path),
        base_revision=ws.base_revision,
    )
    # Capture the diff and pass it as the reviewed patch.
    diff_bytes = backend.diff(ws)
    _set_ready_for_review(store, run, patch_bytes=diff_bytes)

    service = RunService(store, workspace_resolver=resolver)
    bundle = service.apply_run(run.id)

    updated = store.get_run(run.id)
    assert updated.state is RunState.APPLIED
    assert (project / "file.txt").read_text() == "hello\nworld\n"


def test_apply_no_changes_goes_applied(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    resolver = WorkspaceResolver()
    store = _store(tmp_path)
    run = _project_and_run(store, project)

    backend = resolver.resolve_backend(project)
    ws = backend.create(project, run.id)
    store.set_run_workspace(
        run.id,
        workspace=str(ws.target_path),
        base_revision=ws.base_revision,
    )
    _set_ready_for_review(store, run)

    service = RunService(store, workspace_resolver=resolver)
    bundle = service.apply_run(run.id)

    updated = store.get_run(run.id)
    assert updated.state is RunState.APPLIED


def test_dismiss_run(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    resolver = WorkspaceResolver()
    store = _store(tmp_path)
    run = _project_and_run(store, project)
    _set_ready_for_review(store, run)

    service = RunService(store, workspace_resolver=resolver)
    bundle = service.dismiss_run(run.id)

    updated = store.get_run(run.id)
    assert updated.state is RunState.DISMISSED
    assert isinstance(bundle, VerificationBundle)


def test_apply_conflict_when_base_modified(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    resolver = WorkspaceResolver()
    store = _store(tmp_path)
    run = _project_and_run(store, project)

    backend = resolver.resolve_backend(project)
    ws = backend.create(project, run.id)
    # target changes line 2 to "world"
    (ws.target_path / "file.txt").write_text("hello\nworld\n")
    store.set_run_workspace(
        run.id,
        workspace=str(ws.target_path),
        base_revision=ws.base_revision,
    )
    # Capture the diff and pass it as the reviewed patch.
    diff_bytes = backend.diff(ws)
    _set_ready_for_review(store, run, patch_bytes=diff_bytes)

    # base changes the same line before apply, and commits the drift
    (project / "file.txt").write_text("hello\ncosmos\n")
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "drift"], cwd=project, check=True)

    service = RunService(store, workspace_resolver=resolver)
    bundle = service.apply_run(run.id)

    updated = store.get_run(run.id)
    assert updated.state is RunState.FAILED
    assert bundle.status in ("apply_conflict", "apply_blocked")
    assert bundle.reason in ("apply_conflict", "APPLY_CONFLICT", "base_drift", "apply_blocked")
    # base must not have been mutated by the rejected apply
    assert (project / "file.txt").read_text() == "hello\ncosmos\n"


def test_apply_not_ready(tmp_path):
    store = _store(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    run = _project_and_run(store, project)

    service = RunService(store, workspace_resolver=WorkspaceResolver())
    with pytest.raises(ApplyNotReady):
        service.apply_run(run.id)


def test_apply_run_and_conflict(tmp_path):
    """A successful apply updates the base; a later conflicting apply is rejected and the base is untouched."""
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    resolver = WorkspaceResolver()
    store = _store(tmp_path)

    # First run: apply a simple change.
    run1 = _project_and_run(store, project)
    backend = resolver.resolve_backend(project)
    ws1 = backend.create(project, run1.id)
    (ws1.target_path / "file.txt").write_text("hello\nworld\n")
    store.set_run_workspace(
        run1.id,
        workspace=str(ws1.target_path),
        base_revision=ws1.base_revision,
    )
    diff1 = backend.diff(ws1)
    _set_ready_for_review(store, run1, patch_bytes=diff1)

    service = RunService(store, workspace_resolver=resolver)
    bundle1 = service.apply_run(run1.id)
    updated1 = store.get_run(run1.id)
    assert updated1.state is RunState.APPLIED
    assert (project / "file.txt").read_text() == "hello\nworld\n"

    # Commit the applied change so the second workspace is built from the new base.
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "applied"], cwd=project, check=True)

    # Second run: workspace change now conflicts with a new base drift.
    run2 = _project_and_run(store, project)
    ws2 = backend.create(project, run2.id)
    (ws2.target_path / "file.txt").write_text("hello\nall\n")
    store.set_run_workspace(
        run2.id,
        workspace=str(ws2.target_path),
        base_revision=ws2.base_revision,
    )
    diff2 = backend.diff(ws2)
    _set_ready_for_review(store, run2, patch_bytes=diff2)

    # Drift the base before applying.
    (project / "file.txt").write_text("hello\ncosmos\n")
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "drift"], cwd=project, check=True)

    bundle2 = service.apply_run(run2.id)
    updated2 = store.get_run(run2.id)
    assert updated2.state is RunState.FAILED
    assert bundle2.status in ("apply_conflict", "apply_blocked")
    assert bundle2.reason in ("apply_conflict", "APPLY_CONFLICT", "base_drift", "apply_blocked")
    # The conflicting apply must not mutate the base.
    assert (project / "file.txt").read_text() == "hello\ncosmos\n"
