"""Opposed contract tests for the Nucleus Renaissance inspect slice run store."""
import sqlite3

import pytest


def _id(obj):
    return obj.id


def test_sqlite_control_sanity(tmp_path):
    """Independent control test proving the test instrument emits a passing verdict."""
    db = tmp_path / "control.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    rows = conn.execute("SELECT x FROM t").fetchall()
    conn.close()
    assert rows == [(1,)]


def test_store_creates_objects_and_emits_created_event(tmp_path):
    """RunStore creates project, conversation, and run; a new run emits seq=1 run.created."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(_id(project), "inspect conversation")
    run = store.create_run(
        _id(conversation),
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )

    assert not isinstance(project, dict)
    assert not isinstance(conversation, dict)
    assert not isinstance(run, dict)
    assert run.state is RunState.CREATED

    retrieved = store.get_run(_id(run))
    assert _id(retrieved) == _id(run)

    events = store.list_events(_id(run))
    assert len(events) == 1
    assert not isinstance(events[0], dict)
    assert events[0].seq == 1
    assert events[0].type == "run.created"


def test_create_run_is_idempotent_for_same_conversation_and_key(tmp_path):
    """Repeating create_run with the same conversation and idempotency key returns the same run."""
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(_id(project), "inspect conversation")
    run1 = store.create_run(
        _id(conversation),
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )
    run2 = store.create_run(
        _id(conversation),
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )
    assert _id(run1) == _id(run2)
    assert len(store.list_events(_id(run1))) == 1


def test_created_to_applied_raises_InvalidRunTransition(tmp_path):
    """CREATED -> APPLIED is illegal and appends no event."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import InvalidRunTransition, RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(_id(project), "inspect conversation")
    run = store.create_run(
        _id(conversation),
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )
    with pytest.raises(InvalidRunTransition):
        store.transition_run(_id(run), RunState.APPLIED, "run.applied")
    assert len(store.list_events(_id(run))) == 1


def test_inspect_run_lifecycle_without_workspace(tmp_path):
    """An inspect run completes CREATED -> QUEUED -> PREPARING -> RUNNING -> COMPLETED.

    Events have contiguous sequence numbers and no workspace field is required.
    """
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(_id(project), "inspect conversation")
    run = store.create_run(
        _id(conversation),
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )

    transitions = [
        (RunState.QUEUED, "run.queued"),
        (RunState.PREPARING, "run.preparing"),
        (RunState.RUNNING, "run.running"),
        (RunState.COMPLETED, "run.completed"),
    ]
    for new_state, event_type in transitions:
        store.transition_run(_id(run), new_state, event_type)
        run = store.get_run(_id(run))
        assert run.state is new_state

    events = store.list_events(_id(run))
    assert len(events) == 5
    assert [e.seq for e in events] == [1, 2, 3, 4, 5]
    assert [e.type for e in events] == [
        "run.created",
        "run.queued",
        "run.preparing",
        "run.running",
        "run.completed",
    ]
    assert getattr(run, "workspace", None) is None
