"""Crash recovery tests for abandoned runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore


def _seed(store):
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(project.id, "recovery")
    run = store.create_run(
        conversation.id,
        runner_id="runner-r1",
        model_id="model-r1",
        execution_target="local",
        mode="inspect",
        idempotency_key="key-1",
    )
    return run


def test_recover_abandoned_run_fails_and_emits_event(tmp_path):
    db = tmp_path / "recovery.db"
    store = RunStore(str(db))
    run = _seed(store)

    store.transition_run(run.id, RunState.QUEUED, "run.queued")
    store.transition_run(run.id, RunState.PREPARING, "run.preparing")
    store.transition_run(run.id, RunState.RUNNING, "run.running")
    # Pretend the run has not been updated in 10 minutes.
    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(seconds=600)
    store._conn.execute(
        "UPDATE runs SET updated_at = ? WHERE id = ?",
        (ten_minutes_ago.isoformat(), run.id),
    )
    store._conn.commit()

    recovered = store.recover_abandoned_runs(threshold_seconds=300)
    assert recovered == [run.id]

    run2 = store.get_run(run.id)
    assert run2.state is RunState.FAILED

    events = store.list_events(run.id)
    assert any(e.type == "recovery.crash" for e in events)


def test_recover_does_not_touch_recent_runs(tmp_path):
    db = tmp_path / "recovery.db"
    store = RunStore(str(db))
    run = _seed(store)

    store.transition_run(run.id, RunState.QUEUED, "run.queued")
    store.transition_run(run.id, RunState.PREPARING, "run.preparing")
    store.transition_run(run.id, RunState.RUNNING, "run.running")
    recovered = store.recover_abandoned_runs(threshold_seconds=300)
    assert recovered == []

    run2 = store.get_run(run.id)
    assert run2.state is RunState.RUNNING


def test_recover_releases_stale_workspace_lease(tmp_path):
    db = tmp_path / "recovery.db"
    store = RunStore(str(db))
    run = _seed(store)

    store.transition_run(run.id, RunState.QUEUED, "run.queued")
    store.transition_run(run.id, RunState.PREPARING, "run.preparing")
    store.transition_run(run.id, RunState.RUNNING, "run.running")
    store.set_run_workspace(run.id, workspace="ws-1", base_revision="abc123")
    store.acquire_lease(f"workspace:ws-1", "old-dispatcher", ttl_seconds=3600)

    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(seconds=600)
    store._conn.execute(
        "UPDATE runs SET updated_at = ? WHERE id = ?",
        (ten_minutes_ago.isoformat(), run.id),
    )
    store._conn.commit()

    store.recover_abandoned_runs(threshold_seconds=300)

    # After recovery, a new dispatcher should be able to acquire the workspace.
    lease = store.acquire_lease(f"workspace:ws-1", "new-dispatcher", ttl_seconds=3600)
    assert lease is not None


def test_recover_skips_run_with_live_lease(tmp_path):
    """A stale-updated run whose run:<id> lease is still live is a healthy
    worker mid-execution, not an abandoned run — recovery must skip it.
    Vendor lanes run 5-15min without bumping runs.updated_at; without the
    lease check the sweeper murdered live lanes at the 300s mark."""
    db = tmp_path / "recovery.db"
    store = RunStore(str(db))
    run = _seed(store)

    store.transition_run(run.id, RunState.QUEUED, "run.queued")
    store.transition_run(run.id, RunState.PREPARING, "run.preparing")
    store.transition_run(run.id, RunState.RUNNING, "run.running")

    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(seconds=600)
    store._conn.execute(
        "UPDATE runs SET updated_at = ? WHERE id = ?",
        (ten_minutes_ago.isoformat(), run.id),
    )
    store._conn.commit()

    # Live execution lease — worker is heartbeating.
    lease = store.acquire_lease(f"run:{run.id}", "worker-1", ttl_seconds=600)
    assert lease is not None

    recovered = store.recover_abandoned_runs(threshold_seconds=300)
    assert recovered == []
    assert store.get_run(run.id).state is RunState.RUNNING

    # Once the lease lapses the same stale run is recoverable.
    store.release_lease(f"run:{run.id}", "worker-1", lease.fencing_token)
    recovered = store.recover_abandoned_runs(threshold_seconds=300)
    assert recovered == [run.id]
    assert store.get_run(run.id).state is RunState.FAILED
