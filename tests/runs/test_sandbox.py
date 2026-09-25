"""S4-1: real deny-by-default macOS sandbox profile tests."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.targets import MacSandboxExecutionTarget
from mcp_server_nucleus.runs.workspace import Workspace


def _store_and_run(tmp_path: Path, project_root: Path | None = None):
    store = RunStore(str(tmp_path / "runs.db"))
    if project_root is None:
        project_root = tmp_path / "project"
        project_root.mkdir()
    project = store.create_project(f"file://{project_root}", "permissive")
    conv = store.create_conversation(project.id, "test conversation")
    run = store.create_run(
        conversation_id=conv.id,
        runner_id="agy",
        model_id="gemini",
        execution_target="mac-sandbox",
        mode="write",
        idempotency_key="k1",
    )
    return store, run


def test_profile_is_deny_by_default(tmp_path: Path) -> None:
    base = tmp_path / "base"
    target = tmp_path / "target"
    base.mkdir()
    target.mkdir()

    workspace = Workspace(
        run_id="r1",
        base_path=base,
        target_path=target,
        base_revision="",
        backend_name="copy",
    )
    profile = MacSandboxExecutionTarget().build_profile(workspace)

    assert profile.startswith("(version 1)")
    assert "(deny default)" in profile
    assert "(deny network*)" in profile

    # Base path must be allowed for reading, target path for writing.
    read_lines = [line for line in profile.splitlines() if line.startswith("(allow file-read*")]
    assert len(read_lines) == 1
    assert f'(subpath "{base.resolve()}")' in read_lines[0]

    write_lines = [line for line in profile.splitlines() if line.startswith("(allow file-write*")]
    assert len(write_lines) == 1
    assert f'(subpath "{target.resolve()}")' in write_lines[0]

    # Sanity: there is no broad "allow default" or network allowance.
    assert "(allow default)" not in profile
    assert "(allow network*)" not in profile


def test_sandbox_exec_unavailable_waits_for_approval(tmp_path: Path, monkeypatch) -> None:
    store, run = _store_and_run(tmp_path)

    monkeypatch.setattr(
        "mcp_server_nucleus.runs.targets.shutil.which",
        lambda _binary: None,
    )

    target = MacSandboxExecutionTarget()
    result = target.run(store, run.id, "test", lambda: lambda ctx: None)

    assert not result.success
    assert result.error == "sandbox-exec unavailable"
    run = store.get_run(run.id)
    assert run.state is RunState.WAITING_APPROVAL


def test_sandbox_run_hits_timeout_gracefully(tmp_path: Path, monkeypatch) -> None:
    store, run = _store_and_run(tmp_path)

    real_which = shutil.which

    def _which(binary: str):
        if binary == "sandbox-exec":
            return "/usr/bin/sandbox-exec"
        return real_which(binary)

    monkeypatch.setattr(
        "mcp_server_nucleus.runs.targets.shutil.which",
        _which,
    )

    def _fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 300))

    monkeypatch.setattr(
        "mcp_server_nucleus.runs.targets.subprocess.run",
        _fake_run,
    )

    target = MacSandboxExecutionTarget()
    result = target.run(store, run.id, "test", lambda: lambda ctx: None)

    assert not result.success
    assert "timed out" in (result.error or "")
