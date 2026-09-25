"""R4 worker integration with VendorCliRunner and apply/dismiss."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.policy import ExecutionPolicy
from mcp_server_nucleus.runs.runners import VendorCliRunner
from mcp_server_nucleus.runs.service import RunService
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.worker import RunWorker
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _install_fake_agy(tmp_path: Path):
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script = bindir / "agy"
    script.write_text("#!/bin/sh\ncat > /dev/null\necho changed > out.txt\necho done\nexit 0\n")
    script.chmod(0o755)
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bindir}{os.pathsep}{current}"
    return bindir


def _install_noop_agy(tmp_path: Path):
    bindir = tmp_path / "fakebin"
    bindir.mkdir(exist_ok=True)
    script = bindir / "agy"
    script.write_text("#!/bin/sh\ncat > /dev/null\necho done\nexit 0\n")
    script.chmod(0o755)
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bindir}{os.pathsep}{current}"
    return bindir


def _vendor_handler(ctx, prompt: str = "write a file"):
    if ctx.workspace is None or ctx.workspace_backend is None:
        raise RuntimeError("no workspace")
    project = ctx._store.get_project_for_run(ctx._run_id)
    policy = ExecutionPolicy.from_trust_mode(project.trust_mode)
    runner = VendorCliRunner("agy", mode="write")
    return runner.run(
        prompt,
        ctx.workspace,
        ctx.workspace_backend,
        policy,
        timeout_s=30,
    )


def _project_and_run(store, project_root):
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="agy",
        model_id="gemini",
        execution_target="local",
        mode="write",
        idempotency_key="k1",
    )
    return run


def test_worker_runs_vendor_and_reaches_ready_for_review(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    _install_fake_agy(tmp_path)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_vendor_handler)

    updated = store.get_run(run.id)
    assert updated.state is RunState.READY_FOR_REVIEW
    events = store.list_events(run.id)
    ready = [e for e in events if e.type == "run.ready_for_review"]
    assert len(ready) == 1
    assert ready[0].payload["status"] == "ok"
    assert ready[0].payload["diff_size"] > 0


def test_worker_apply_after_review(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    _install_fake_agy(tmp_path)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_vendor_handler)

    service = RunService(store, workspace_resolver=WorkspaceResolver())
    bundle = service.apply_run(run.id)

    updated = store.get_run(run.id)
    assert updated.state is RunState.APPLIED
    assert bundle.status == "ok"


def test_worker_no_op_completes(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    _install_noop_agy(tmp_path)

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())
    worker.execute(_vendor_handler)

    updated = store.get_run(run.id)
    assert updated.state is RunState.COMPLETED
