"""S6-1 fake hosted execution target tests."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.hosted import FakeHostedExecutionTarget, HostedWorkerExecutionTarget
from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _make_vendor(tmp_path: Path) -> Path:
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script = bindir / "agy"
    script.write_text("#!/bin/sh\ncat > /dev/null\necho changed > out.txt\necho done\nexit 0\n")
    script.chmod(0o755)
    return bindir


def _project_and_run(store, project_root, execution_target: str = "hosted"):
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="agy",
        model_id="gemini",
        execution_target=execution_target,
        mode="write",
        idempotency_key="k1",
    )
    return run


def _handler_factory(prompt: str):
    def _factory():
        from mcp_server_nucleus.runs.policy import ExecutionPolicy
        from mcp_server_nucleus.runs.runners import VendorCliRunner

        def _h(ctx):
            if ctx.workspace is None or ctx.workspace_backend is None:
                raise RuntimeError("no workspace")
            project = ctx._store.get_project_for_run(ctx._run_id)
            policy = ExecutionPolicy.from_trust_mode(project.trust_mode)
            runner = VendorCliRunner("agy", mode="write")
            return runner.run(prompt, ctx.workspace, ctx.workspace_backend, policy, timeout_s=30)

        return _h

    return _factory


def test_fake_hosted_runs_to_completion(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = FakeHostedExecutionTarget(reconcile_timeout_s=10)
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert result.success, result.error
    assert result.state is RunState.READY_FOR_REVIEW


def test_fake_hosted_duplicate_frame(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = FakeHostedExecutionTarget(
        reconcile_timeout_s=10,
        faults={"duplicate_next_frame": True},
    )
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert result.success, result.error
    assert result.state is RunState.READY_FOR_REVIEW


def test_fake_hosted_out_of_order_frames(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = FakeHostedExecutionTarget(
        reconcile_timeout_s=10,
        faults={"reorder_frames": 3},
    )
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert result.success, result.error
    assert result.state is RunState.READY_FOR_REVIEW


def test_fake_hosted_sequence_gap_fails(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = FakeHostedExecutionTarget(
        reconcile_timeout_s=2,
        faults={"drop_next_frame": True},
    )
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert not result.success
    assert result.state is RunState.FAILED

    run = store.get_run(run.id)
    assert run.state is RunState.FAILED

    events = store.list_events(run.id)
    gap_events = [e for e in events if e.payload.get("reason") == "sequence_gap"]
    assert gap_events, "expected a sequence_gap failure event"


def test_hosted_worker_unconfigured_returns_workspace_unavailable(tmp_path, monkeypatch):
    monkeypatch.delenv("NUCLEUS_HOSTED_PROVIDER", raising=False)
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project, execution_target="hosted")

    target = HostedWorkerExecutionTarget()
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert not result.success
    assert result.state is RunState.FAILED
    assert "WORKSPACE_UNAVAILABLE" in (result.error or "")

    run = store.get_run(run.id)
    assert run.state is RunState.FAILED
    events = store.list_events(run.id)
    assert any(
        e.payload.get("error_type") == "WorkspaceUnavailable" for e in events
    )


def test_hosted_worker_fake_provider_delegates(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")
    monkeypatch.setenv("NUCLEUS_HOSTED_PROVIDER", "fake")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project, execution_target="hosted")

    target = HostedWorkerExecutionTarget()
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert result.success, result.error
    assert result.state is RunState.READY_FOR_REVIEW
