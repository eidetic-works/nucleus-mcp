"""R6 execution target bake-off tests."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.targets import (
    InProcessExecutionTarget,
    MacSandboxExecutionTarget,
    SubprocessExecutionTarget,
)
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


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


def test_in_process_target(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = InProcessExecutionTarget()
    result = target.run(store, run.id, "worker-1", _handler_factory("write"))

    assert result.success
    assert result.state is RunState.READY_FOR_REVIEW


def test_subprocess_target(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    target = SubprocessExecutionTarget()
    result = target.run(store, run.id, "worker-sub", _handler_factory("write"))

    assert result.success, result.error
    terminal_success = {
        RunState.READY_FOR_REVIEW,
        RunState.COMPLETED,
        RunState.APPLIED,
        RunState.DISMISSED,
    }
    assert result.state in terminal_success, (
        f"expected a successful terminal state, got {result.state}"
    )
    final_run = store.get_run(run.id)
    assert final_run.state == result.state

    # Prove a separate worker process was actually spawned and recorded.
    worker_events = [
        e for e in store.list_events(run.id) if e.type == "subprocess_worker"
    ]
    assert worker_events, "expected a subprocess_worker launch event"
    assert all(
        isinstance(e.payload.get("pid"), int)
        and e.payload["pid"] > 0
        and e.payload["pid"] != os.getpid()
        for e in worker_events
    )


def test_mac_sandbox_target(tmp_path, monkeypatch):
    if shutil.which("sandbox-exec") is None:
        pytest.skip("sandbox-exec not available")

    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_vendor(tmp_path)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("NUCLEUS_CROSS_VENDOR", "1")

    store = RunStore(str(tmp_path / "runs.db"))
    run = _project_and_run(store, project)

    # Permissive profile for tests: allow full /private/tmp and /usr/local/bin
    profile = f"""(version 1)
(allow default)
(allow network*)
(allow process-exec (subpath "/"))
(allow file-read* (subpath "/"))
(allow file-write* (subpath "/"))
"""
    target = MacSandboxExecutionTarget(profile=profile)
    result = target.run(store, run.id, "worker-sbx", _handler_factory("write"))

    assert result.success, result.error
    assert result.state is RunState.READY_FOR_REVIEW
