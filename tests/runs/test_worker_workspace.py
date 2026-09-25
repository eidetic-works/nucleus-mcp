"""R2 workspace integration tests for the run worker."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.worker import RunWorker
from mcp_server_nucleus.runs.workspace import WorkspaceResolver


def _seed_project(store, project_root: Path, trust_mode: str = "default"):
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "src").mkdir(exist_ok=True)
    (project_root / "src" / "main.py").write_text("# code\n")
    project = store.create_project(f"file://{project_root}", trust_mode)
    conversation = store.create_conversation(project.id, "workspace test")
    run = store.create_run(
        conversation.id,
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="write",
        idempotency_key="key-1",
    )
    return run


def test_worker_creates_copy_workspace_and_exposes_to_handler(tmp_path):
    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_project(store, tmp_path / "project")
        worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())

        seen = {}

        def handler(ctx):
            seen["workspace"] = ctx.workspace
            assert ctx.workspace is not None
            (Path(ctx.workspace.target_path) / "out.txt").write_text("ran")

        worker.execute(handler)

        run = store.get_run(run.id)
        assert run.state is RunState.COMPLETED
        assert run.workspace is not None
        assert run.base_revision is not None
        assert Path(run.workspace).is_dir()
        assert (Path(run.workspace) / "src" / "main.py").read_text() == "# code\n"
        assert (Path(run.workspace) / "out.txt").read_text() == "ran"
    finally:
        store.close()


def test_worker_fails_run_on_workspace_creation_error(tmp_path):
    store = RunStore(str(tmp_path / "runs.db"))
    try:
        missing = tmp_path / "missing-project"
        project = store.create_project(f"file://{missing}", "default")
        conversation = store.create_conversation(project.id, "workspace test")
        run = store.create_run(
            conversation.id,
            runner_id="runner-1",
            model_id="model-1",
            execution_target="local",
            mode="write",
            idempotency_key="key-1",
        )
        worker = RunWorker(store, run.id, "worker-1", workspace_resolver=WorkspaceResolver())

        def handler(ctx):
            pass

        with pytest.raises(Exception):
            worker.execute(handler)

        run = store.get_run(run.id)
        assert run.state is RunState.FAILED
        events = store.list_events(run.id)
        failed = [e for e in events if e.type == "run.failed"]
        assert failed
        assert failed[0].payload.get("phase") == "workspace_prepare"
    finally:
        store.close()
