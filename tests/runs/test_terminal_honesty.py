"""S3-4 terminal-state honesty tests for the run worker."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.runners import RunnerResult
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.verifiers import CommandVerifier
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
    return store.create_run(
        conversation_id=conv.id,
        runner_id="fake",
        model_id="fake",
        execution_target="local",
        mode="write",
        idempotency_key="k1",
    )


def _handler_for(result: RunnerResult):
    def _handler(_ctx):
        return result

    return _handler


def _failed_event_payload(store: RunStore, run_id: str) -> dict:
    for ev in store.list_events(run_id):
        if ev.type == "run.failed":
            return ev.payload
    raise AssertionError("no run.failed event found")


def _ready_event_payload(store: RunStore, run_id: str) -> dict:
    for ev in store.list_events(run_id):
        if ev.type == "run.ready_for_review":
            return ev.payload
    raise AssertionError("no run.ready_for_review event found")


def test_timeout_with_valid_patch_is_ready_for_review(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    result = RunnerResult(
        vendor="test",
        model_family="test",
        model_id="test",
        rc=None,
        status="timed_out",
        output="some output",
        duration=1.0,
        diff_artifact=b"patch bytes",
        is_clean=False,
    )
    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_handler_for(result))

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW

    bundle = RunService(store).get_run_bundle(run.id)
    assert bundle.verdict == "ok"
    assert bundle.warning is True
    payload = _ready_event_payload(store, run.id)
    assert payload["reason"] == "timeout_with_valid_artifacts"


def test_exit_zero_empty_output_is_failed(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    result = RunnerResult(
        vendor="test",
        model_family="test",
        model_id="test",
        rc=0,
        status="ok",
        output="",
        duration=1.0,
        diff_artifact=b"",
        is_clean=True,
    )
    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_handler_for(result))

    updated = store.get_run(run.id)
    assert updated.state is RunState.FAILED

    payload = _failed_event_payload(store, run.id)
    assert payload["reason"] == "INVALID_RUNNER_RESULT"


def test_timeout_with_no_output_is_failed(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    result = RunnerResult(
        vendor="test",
        model_family="test",
        model_id="test",
        rc=None,
        status="timed_out",
        output="",
        duration=1.0,
        diff_artifact=b"",
        is_clean=True,
    )
    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_handler_for(result))

    updated = store.get_run(run.id)
    assert updated.state is RunState.FAILED

    payload = _failed_event_payload(store, run.id)
    assert payload["reason"] == "timeout_no_output"


def test_verifier_always_fails_marks_bundle_non_green(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    result = RunnerResult(
        vendor="test",
        model_family="test",
        model_id="test",
        rc=0,
        status="ok",
        output="some output",
        duration=1.0,
        diff_artifact=b"patch bytes",
        is_clean=False,
    )
    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(
        _handler_for(result),
        verifiers=[CommandVerifier("fail", [sys.executable, "-c", "import sys; sys.exit(1)"])],
    )

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW

    bundle = RunService(store).get_run_bundle(run.id)
    assert bundle.verdict == "test_failed"
    assert bundle.warning is True
    assert bundle.status == "failed"
