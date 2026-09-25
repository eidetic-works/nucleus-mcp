"""S4-2 trust mode to execution target wiring tests."""
from __future__ import annotations

from pathlib import Path

from mcp_server_nucleus.runs.dispatcher import RunDispatcher
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.targets import (
    InProcessExecutionTarget,
    MacSandboxExecutionTarget,
    SubprocessExecutionTarget,
)


def _seed_run(
    store: RunStore,
    project_root: Path,
    trust_mode: str = "default",
    execution_target: str = "in-process",
):
    project = store.create_project(f"file://{project_root}", trust_mode)
    conversation = store.create_conversation(project.id, "test conversation")
    return store.create_run(
        conversation_id=conversation.id,
        runner_id="agy",
        model_id="",
        execution_target=execution_target,
        mode="write",
        idempotency_key="k1",
    )


def test_strict_project_uses_mac_sandbox(tmp_path):
    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    run = _seed_run(store, tmp_path, trust_mode="strict")
    store.close()

    dispatcher = RunDispatcher(str(db))
    target = dispatcher._target_for(run)

    assert isinstance(target, MacSandboxExecutionTarget)


def test_mac_sandbox_target_uses_mac_sandbox(tmp_path):
    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    run = _seed_run(
        store, tmp_path, trust_mode="permissive", execution_target="mac-sandbox"
    )
    store.close()

    dispatcher = RunDispatcher(str(db))
    target = dispatcher._target_for(run)

    assert isinstance(target, MacSandboxExecutionTarget)


def test_subprocess_target_uses_subprocess(tmp_path):
    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    run = _seed_run(store, tmp_path, execution_target="subprocess")
    store.close()

    dispatcher = RunDispatcher(str(db))
    target = dispatcher._target_for(run)

    assert isinstance(target, SubprocessExecutionTarget)
