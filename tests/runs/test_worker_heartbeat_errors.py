"""Opposed heartbeat-error tests for RunWorker."""
from __future__ import annotations

import sqlite3
import threading

import pytest


def _seed_run(store, idempotency_key: str = "key-1"):
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(project.id, "heartbeat conversation")
    return store.create_run(
        conversation.id,
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key=idempotency_key,
    )


def test_worker_heartbeat_renew_lease_raises_operationalerror(tmp_path):
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker, WorkerLeaseLost

    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    try:
        run = _seed_run(store)
        worker = RunWorker(
            store,
            run.id,
            "owner-1",
            lease_ttl_seconds=1,
            heartbeat_interval_seconds=0.01,
        )
        signal = threading.Event()

        def bad_renew(resource, owner_id, fencing_token, ttl_seconds, now=None):
            signal.set()
            raise sqlite3.OperationalError("disk I/O error")

        store.renew_lease = bad_renew

        def handler(ctx):
            assert signal.wait(timeout=2.0)

        with pytest.raises(WorkerLeaseLost) as exc_info:
            worker.execute(handler)

        assert isinstance(exc_info.value.__cause__, sqlite3.OperationalError)
        assert store.get_run(run.id).state is not RunState.COMPLETED
        assert worker._heartbeat_thread is None
    finally:
        store.close()


def test_worker_heartbeat_fails_before_emit_blocks_append(tmp_path):
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore, StaleLease
    from mcp_server_nucleus.runs.worker import RunWorker, WorkerLeaseLost

    db = tmp_path / "runs.db"
    store = RunStore(str(db))
    try:
        run = _seed_run(store)
        worker = RunWorker(
            store,
            run.id,
            "owner-1",
            lease_ttl_seconds=1,
            heartbeat_interval_seconds=0.01,
        )
        signal = threading.Event()

        def bad_renew(resource, owner_id, fencing_token, ttl_seconds, now=None):
            signal.set()
            raise StaleLease

        store.renew_lease = bad_renew

        def handler(ctx):
            assert signal.wait(timeout=2.0)
            ctx.emit("late.event", {})

        with pytest.raises(WorkerLeaseLost) as exc_info:
            worker.execute(handler)

        assert isinstance(exc_info.value.__cause__, StaleLease)
        assert "late.event" not in {e.type for e in store.list_events(run.id)}
        assert store.get_run(run.id).state is not RunState.COMPLETED
    finally:
        store.close()
