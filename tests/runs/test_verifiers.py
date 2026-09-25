"""Tests for S3-2 run verifiers and the VERIFYING state."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.runners import RunnerResult
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.verifiers import CommandVerifier, NoopVerifier
from mcp_server_nucleus.runs.worker import RunWorker
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _project_and_run(store: RunStore, project_root: Path):
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="test",
        model_id="test",
        execution_target="local",
        mode="write",
        idempotency_key="k1",
    )
    return run


def _handler(ctx) -> RunnerResult:
    if ctx.workspace is None or ctx.workspace_backend is None:
        raise RuntimeError("no workspace")
    (ctx.workspace.target_path / "out.txt").write_text("changed\n")
    return RunnerResult(
        vendor="test",
        model_family="test",
        model_id="test",
        rc=0,
        status="ok",
        output="done",
        duration=0.1,
        diff_artifact=b"diff",
        is_clean=False,
    )


def test_noop_verifier(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_handler, verifiers=[NoopVerifier()])

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW

    service = RunService(store)
    bundle = service.get_run_bundle(run.id)
    assert bundle.verdict == "ok"


def test_command_verifier_fails(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(
        _handler,
        verifiers=[CommandVerifier("failing", [sys.executable, "-c", "import sys; sys.exit(1)"])],
    )

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW

    service = RunService(store)
    bundle = service.get_run_bundle(run.id)
    assert bundle.verdict == "test_failed"
    assert bundle.test_report is not None
    assert bundle.warning is True


def test_command_verifier_passes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(
        _handler,
        verifiers=[CommandVerifier("passing", [sys.executable, "-c", "print('ok')"])],
    )

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW

    service = RunService(store)
    bundle = service.get_run_bundle(run.id)
    assert bundle.verdict == "ok"
