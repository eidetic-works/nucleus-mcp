"""Opposed R1 recovery contract tests for the Nucleus Renaissance run store/worker."""
from __future__ import annotations


def _id(obj):
    return obj.id


def _seed_run(store, idempotency_key: str = "key-r1"):
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(_id(project), "r1 conversation")
    return store.create_run(
        _id(conversation),
        runner_id="runner-r1",
        model_id="model-r1",
        execution_target="local",
        mode="inspect",
        idempotency_key=idempotency_key,
    )


def _close(store) -> None:
    closer = getattr(store, "close", None)
    if closer:
        closer()


def _assert_no_hb_threads(run_id: str) -> None:
    import threading

    live = [t for t in threading.enumerate() if t.is_alive() and run_id in t.name]
    assert not live, f"heartbeat thread for {run_id!r} still alive: {live}"


def test_v1_to_v2_migration_preserves_run_and_events(tmp_path):
    import sqlite3

    from mcp_server_nucleus.runs.models import CommandKind, RunState
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / "r1_v1_v2.db"
    original = RunStore._SCHEMA_VERSION
    try:
        RunStore._SCHEMA_VERSION = 1
        store = RunStore(str(db))
        run = _seed_run(store)
        original_id = _id(run)
        events_before = store.list_events(_id(run))
        _close(store)
        store = None

        RunStore._SCHEMA_VERSION = 2
        store = RunStore(str(db))

        run2 = store.get_run(original_id)
        assert _id(run2) == original_id
        assert run2.state is RunState.CREATED
        assert len(store.list_events(_id(run2))) == len(events_before)
        assert store.list_events(_id(run2))[0].type == "run.created"

        store.transition_run(_id(run2), RunState.QUEUED, "run.queued")
        store.transition_run(_id(run2), RunState.PREPARING, "run.preparing")
        store.transition_run(_id(run2), RunState.RUNNING, "run.running")
        cmd = store.enqueue_command(_id(run2), CommandKind.PAUSE, {}, "user")
        assert cmd.seq == 1
        assert store.list_commands(_id(run2)) == [cmd]

        _close(store)
        store = None
    finally:
        RunStore._SCHEMA_VERSION = original

    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT version FROM schema_version").fetchall()
    conn.close()
    assert rows == [(2,)], f"schema_version rows were {rows}"

    _assert_no_hb_threads(str(db))


def test_future_version_refusal_raises_and_does_not_mutate(tmp_path):
    import sqlite3

    import pytest

    from mcp_server_nucleus.runs import store as store_mod
    from mcp_server_nucleus.runs.store import RunStore

    UnsupportedSchemaVersion = getattr(store_mod, "UnsupportedSchemaVersion", None)
    if UnsupportedSchemaVersion is None:
        pytest.fail("RunStore module does not define UnsupportedSchemaVersion")

    db = tmp_path / "r1_future.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO schema_version(version) VALUES (99)")
    conn.commit()
    conn.close()

    with pytest.raises(UnsupportedSchemaVersion):
        RunStore(str(db))

    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT version FROM schema_version").fetchall()
    conn.close()
    assert rows == [(99,)], f"future schema version was mutated to {rows}"

    _assert_no_hb_threads(str(db))


def test_worker_automatic_heartbeat_renews_lease_and_completes(tmp_path):
    import threading

    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    db = tmp_path / "r1_hb.db"
    store = RunStore(str(db))
    try:
        run = _seed_run(store)
        store.transition_run(_id(run), RunState.QUEUED, "run.queued")

        try:
            worker = RunWorker(
                store,
                _id(run),
                "worker-A",
                lease_ttl_seconds=1,
                heartbeat_interval_seconds=0.01,
            )
        except TypeError as exc:
            raise AssertionError(
                f"RunWorker does not accept heartbeat_interval_seconds: {exc}"
            ) from exc

        resource = f"run:{_id(run)}"
        original_renew = store.renew_lease
        renewed = threading.Event()

        def spy_renew(*args, **kwargs):
            result = original_renew(*args, **kwargs)
            renewed.set()
            return result

        store.renew_lease = spy_renew

        def handler(ctx):
            assert renewed.wait(timeout=2), "heartbeat renewal was not observed"
            ctx.emit("worker.step", {})

        worker.execute(handler)

        final = store.get_run(_id(run))
        assert final.state is RunState.COMPLETED
        assert store.get_lease(resource) is None

        events = [e.type for e in store.list_events(_id(run))]
        assert "worker.step" in events
        assert "run.completed" in events
        assert renewed.is_set()

        _assert_no_hb_threads(_id(run))
    finally:
        _close(store)


def test_worker_heartbeat_failure_raises_lease_lost_and_does_not_complete(tmp_path):
    import threading

    import pytest

    from mcp_server_nucleus.runs import worker as worker_mod
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore, StaleLease
    from mcp_server_nucleus.runs.worker import RunWorker

    WorkerLeaseLost = getattr(worker_mod, "WorkerLeaseLost", None)
    if WorkerLeaseLost is None:
        pytest.fail("RunWorker module does not define WorkerLeaseLost")

    db = tmp_path / "r1_hb_fail.db"
    store = RunStore(str(db))
    try:
        run = _seed_run(store)
        store.transition_run(_id(run), RunState.QUEUED, "run.queued")

        try:
            worker = RunWorker(
                store,
                _id(run),
                "worker-A",
                lease_ttl_seconds=1,
                heartbeat_interval_seconds=0.01,
            )
        except TypeError as exc:
            raise AssertionError(
                f"RunWorker does not accept heartbeat_interval_seconds: {exc}"
            ) from exc

        stale = threading.Event()

        def failing_renew(*args, **kwargs):
            stale.set()
            raise StaleLease

        store.renew_lease = failing_renew

        def handler(ctx):
            assert stale.wait(timeout=2), "stale lease signal was not observed"

        with pytest.raises(WorkerLeaseLost) as exc_info:
            worker.execute(handler)

        assert isinstance(exc_info.value.__cause__, StaleLease)

        final = store.get_run(_id(run))
        assert final.state is not RunState.COMPLETED

        events = [e.type for e in store.list_events(_id(run))]
        assert "run.completed" not in events

        _assert_no_hb_threads(_id(run))
    finally:
        _close(store)


def test_worker_heartbeat_thread_is_named_and_joined(tmp_path):
    import threading

    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    db = tmp_path / "r1_hb_thread.db"
    store = RunStore(str(db))
    try:
        run = _seed_run(store)

        try:
            worker = RunWorker(
                store,
                _id(run),
                "worker-A",
                lease_ttl_seconds=1,
                heartbeat_interval_seconds=0.01,
            )
        except TypeError as exc:
            raise AssertionError(
                f"RunWorker does not accept heartbeat_interval_seconds: {exc}"
            ) from exc

        _assert_no_hb_threads(_id(run))

        def handler(ctx):
            ctx.emit("worker.ping", {})

        worker.execute(handler)

        _assert_no_hb_threads(_id(run))
    finally:
        _close(store)
