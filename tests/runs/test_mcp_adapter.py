"""R5 MCP/ACP adapter tests for the run engine."""
from __future__ import annotations

import subprocess
from pathlib import Path

from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.models import RunState


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def test_adapter_create_and_show(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    adapter = RunMcpAdapter(tmp_path / "runs.db")
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "write a file", idempotency_key="k1")

    shown = adapter.show_run(run_id)
    assert shown["run"]["state"] == "queued"
    assert shown["run"]["conversation_id"] == conv_id


def test_adapter_list_runs(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    adapter = RunMcpAdapter(tmp_path / "runs.db")
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    r1 = adapter.create_run(conv_id, "first", idempotency_key="k1")
    r2 = adapter.create_run(conv_id, "second", idempotency_key="k2")

    runs = adapter.list_runs(conv_id)
    assert len(runs) == 2
    assert {r["id"] for r in runs} == {r1, r2}


def test_adapter_apply_and_dismiss_response(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    adapter = RunMcpAdapter(tmp_path / "runs.db")
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "noop", idempotency_key="k1")

    store = adapter._store
    for state in (RunState.PREPARING, RunState.RUNNING, RunState.VERIFYING, RunState.READY_FOR_REVIEW):
        store.transition_run(run_id, state, f"run.{state.value}")

    resp = adapter.dismiss_run(run_id)
    assert resp.success
    assert resp.data["run"]["state"] == "dismissed"


def test_adapter_cancel_run(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _git_init(project)

    adapter = RunMcpAdapter(tmp_path / "runs.db")
    project_id = adapter.create_project(f"file://{project}", "permissive")
    conv_id = adapter.create_conversation(project_id, "c")
    run_id = adapter.create_run(conv_id, "cancel me", idempotency_key="k1")

    resp = adapter.cancel_run(run_id)
    assert resp.success
