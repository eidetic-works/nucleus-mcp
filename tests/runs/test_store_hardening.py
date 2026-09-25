"""Hardened opposed contract tests for the Nucleus Renaissance run store."""
import sqlite3
import threading
from typing import Any

import pytest


def _make_run(store, idempotency_key: str = "key-1", **overrides: Any):
    """Create a project, conversation, and run, returning the run."""
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(project.id, "inspect conversation")
    run = store.create_run(
        conversation.id,
        runner_id=overrides.get("runner_id", "runner-1"),
        model_id=overrides.get("model_id", "model-1"),
        execution_target=overrides.get("execution_target", "local"),
        mode=overrides.get("mode", "inspect"),
        idempotency_key=idempotency_key,
    )
    return run


def _close(store) -> None:
    """Close a store if it exposes a public close method."""
    closer = getattr(store, "close", None)
    if closer is not None:
        closer()


def _idempotency_conflict_cls():
    """Return the production IdempotencyConflict exception, or fail if missing."""
    import mcp_server_nucleus.runs.store as store_mod

    cls = getattr(store_mod, "IdempotencyConflict", None)
    if cls is None:
        pytest.fail("mcp_server_nucleus.runs.store must define IdempotencyConflict")
    return cls


def test_run_store_supports_close_and_context_manager(tmp_path):
    """RunStore.close() and context-manager use close the underlying SQLite DB."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / "runs.db"
    run_id = None
    store = None
    try:
        store = RunStore(str(db))
        run = _make_run(store)
        run_id = run.id

        assert hasattr(store, "close"), "RunStore must expose a public close() method"
        assert store.close() is None, "close() should return None"

        with pytest.raises(sqlite3.ProgrammingError):
            store.list_events(run_id)
    finally:
        _close(store)

    store2 = None
    try:
        assert hasattr(RunStore, "__enter__"), "RunStore must support context-manager __enter__"
        assert hasattr(RunStore, "__exit__"), "RunStore must support context-manager __exit__"

        with RunStore(str(db)) as store2:
            run = _make_run(store2)
            run_id = run.id

        with pytest.raises(sqlite3.ProgrammingError):
            store2.list_events(run_id)
    finally:
        _close(store2)


def test_run_store_is_idempotent_for_identical_request(tmp_path):
    """Same conversation + key + identical fields returns the same run with one event."""
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    try:
        run1 = _make_run(store)
        run2 = store.create_run(
            run1.conversation_id,
            runner_id=run1.runner_id,
            model_id=run1.model_id,
            execution_target=run1.execution_target,
            mode=run1.mode,
            idempotency_key=run1.idempotency_key,
        )

        assert run1.id == run2.id
        assert run1.state == run2.state
        assert run1.runner_id == run2.runner_id
        assert run1.model_id == run2.model_id
        assert run1.execution_target == run2.execution_target
        assert run1.mode == run2.mode

        events = store.list_events(run1.id)
        assert len(events) == 1
        assert events[0].seq == 1
        assert events[0].type == "run.created"
    finally:
        _close(store)


def test_run_store_raises_idempotency_conflict_on_changed_request_fields(tmp_path):
    """Same conversation + key with changed request fields raises IdempotencyConflict."""
    from mcp_server_nucleus.runs.store import RunStore

    IdempotencyConflict = _idempotency_conflict_cls()

    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store, runner_id="runner-1", model_id="model-1")

        with pytest.raises(IdempotencyConflict):
            store.create_run(
                run.conversation_id,
                runner_id="runner-2",
                model_id="model-2",
                execution_target="remote",
                mode="edit",
                idempotency_key=run.idempotency_key,
            )

        events = store.list_events(run.id)
        assert len(events) == 1
    finally:
        _close(store)


def _path_to_running(store, run_id: str) -> None:
    from mcp_server_nucleus.runs.models import RunState

    store.transition_run(run_id, RunState.QUEUED, "run.queued")
    store.transition_run(run_id, RunState.PREPARING, "run.preparing")
    store.transition_run(run_id, RunState.RUNNING, "run.running")


def _path_to_applied(store, run_id: str) -> None:
    from mcp_server_nucleus.runs.models import RunState

    _path_to_running(store, run_id)
    store.transition_run(run_id, RunState.VERIFYING, "run.verifying")
    store.transition_run(run_id, RunState.READY_FOR_REVIEW, "run.ready_for_review")
    store.transition_run(run_id, RunState.APPLYING, "run.applying")
    store.transition_run(run_id, RunState.APPLIED, "run.applied")


def _path_to_dismissed(store, run_id: str) -> None:
    from mcp_server_nucleus.runs.models import RunState

    _path_to_running(store, run_id)
    store.transition_run(run_id, RunState.VERIFYING, "run.verifying")
    store.transition_run(run_id, RunState.READY_FOR_REVIEW, "run.ready_for_review")
    store.transition_run(run_id, RunState.DISMISSED, "run.dismissed")


@pytest.mark.parametrize(
    "path_builder,terminal",
    [
        (_path_to_applied, "applied"),
        (_path_to_dismissed, "dismissed"),
    ],
    ids=["applied", "dismissed"],
)
def test_terminal_states_reject_further_transitions(tmp_path, path_builder, terminal):
    """APPLIED and DISMISSED are terminal; any further transition is rejected."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import InvalidRunTransition, RunStore

    db = tmp_path / f"terminal-{terminal}.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store)
        path_builder(store, run.id)

        events_before = store.list_events(run.id)
        count_before = len(events_before)

        with pytest.raises(InvalidRunTransition):
            store.transition_run(run.id, RunState.RUNNING, "run.running")

        run_after = store.get_run(run.id)
        assert run_after.state == RunState(terminal)

        events_after = store.list_events(run.id)
        assert len(events_after) == count_before
    finally:
        _close(store)


def test_completed_failed_cancelled_are_terminal(tmp_path):
    """COMPLETED, FAILED, and CANCELLED reject any further transitions."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import InvalidRunTransition, RunStore

    db = tmp_path / "terminal-others.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store)

        # Build a run to RUNNING so COMPLETED/FAILED are reachable.
        _path_to_running(store, run.id)

        for terminal in (RunState.COMPLETED, RunState.FAILED):
            store.transition_run(run.id, terminal, f"run.{terminal.value}")
            events_before = store.list_events(run.id)
            with pytest.raises(InvalidRunTransition):
                store.transition_run(run.id, RunState.QUEUED, "run.queued")
            assert len(store.list_events(run.id)) == len(events_before)
            # Reset not possible; create a fresh run for the next terminal.
            run = _make_run(store, idempotency_key=f"key-{terminal.value}")
            _path_to_running(store, run.id)

        # CANCELLED is reachable directly from CREATED.
        run = _make_run(store, idempotency_key="key-cancelled")
        store.transition_run(run.id, RunState.CANCELLED, "run.cancelled")
        events_before = store.list_events(run.id)
        with pytest.raises(InvalidRunTransition):
            store.transition_run(run.id, RunState.QUEUED, "run.queued")
        assert len(store.list_events(run.id)) == len(events_before)
    finally:
        _close(store)


def test_verifying_cannot_jump_to_applying(tmp_path):
    """VERIFYING cannot transition directly to APPLYING; it must pass through READY_FOR_REVIEW."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import InvalidRunTransition, RunStore

    db = tmp_path / "verifying.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store)
        _path_to_running(store, run.id)
        store.transition_run(run.id, RunState.VERIFYING, "run.verifying")

        events_before = store.list_events(run.id)
        with pytest.raises(InvalidRunTransition):
            store.transition_run(run.id, RunState.APPLYING, "run.applying")

        assert len(store.list_events(run.id)) == len(events_before)
    finally:
        _close(store)


@pytest.mark.parametrize(
    "wait_state",
    [
        "waiting_approval",
        "waiting_input",
        "paused_budget",
        "takeover",
    ],
)
def test_wait_states_return_to_running(tmp_path, wait_state):
    """WAITING_APPROVAL, WAITING_INPUT, PAUSED_BUDGET, and TAKEOVER may resume to RUNNING."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / f"wait-{wait_state}.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store, idempotency_key=f"key-{wait_state}")
        _path_to_running(store, run.id)

        wait = RunState(wait_state)
        store.transition_run(run.id, wait, f"run.{wait_state}")

        run = store.transition_run(run.id, RunState.RUNNING, "run.running")
        assert run.state == RunState.RUNNING

        events = store.list_events(run.id)
        seqs = [e.seq for e in events]
        assert seqs == list(range(1, len(events) + 1))
    finally:
        _close(store)


def test_concurrent_created_to_queued_one_winner(tmp_path):
    """Two simultaneous CREATED->QUEUED attempts on one run have exactly one winner."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import InvalidRunTransition, RunStore

    db = tmp_path / "concurrent.db"

    # Seed the run with one store and close it so both contenders open fresh.
    seed = RunStore(str(db))
    try:
        run = _make_run(seed, idempotency_key="concurrent-key")
        run_id = run.id
    finally:
        _close(seed)

    results = {"success": 0, "invalid": 0, "other": []}
    barrier = threading.Barrier(2)

    def contender():
        store = RunStore(str(db))
        try:
            barrier.wait(timeout=5)
            try:
                store.transition_run(run_id, RunState.QUEUED, "run.queued")
            except InvalidRunTransition:
                results["invalid"] += 1
            except Exception as exc:  # pragma: no cover - opposed tests surface real errors
                results["other"].append((type(exc).__name__, str(exc)))
            else:
                results["success"] += 1
        finally:
            _close(store)

    t1 = threading.Thread(target=contender)
    t2 = threading.Thread(target=contender)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not t1.is_alive()
    assert not t2.is_alive()
    assert results["other"] == [], f"unexpected exceptions: {results['other']}"
    assert results["success"] == 1, f"expected exactly one success, got {results['success']}"
    assert results["invalid"] == 1, f"expected exactly one InvalidRunTransition, got {results['invalid']}"

    # Verify final state and events from a fresh store.
    verify = RunStore(str(db))
    try:
        run = verify.get_run(run_id)
        assert run.state == RunState.QUEUED

        events = verify.list_events(run_id)
        assert len(events) == 2
        assert [e.seq for e in events] == [1, 2]
        queued_events = [e for e in events if e.type == "run.queued"]
        assert len(queued_events) == 1
    finally:
        _close(verify)


def test_list_events_cursor_returns_payload_copy(tmp_path):
    """list_events(after_seq=1) returns only seq 2 with an equal, independent payload copy."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / "payload.db"
    store = RunStore(str(db))
    try:
        run = _make_run(store)
        payload = {"nested": {"value": 42, "list": [1, 2, 3]}, "ok": True}
        store.transition_run(run.id, RunState.QUEUED, "run.queued", payload)

        events = store.list_events(run.id, after_seq=1)
        assert len(events) == 1
        event = events[0]
        assert event.seq == 2
        assert event.type == "run.queued"
        assert event.payload == payload
        assert event.payload is not payload
        assert event.payload["nested"] is not payload["nested"]
    finally:
        _close(store)
