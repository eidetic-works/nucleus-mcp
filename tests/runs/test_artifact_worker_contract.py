"""Opposed contract tests for the Nucleus Renaissance R1 worker/artifact slice."""
from __future__ import annotations

import dataclasses
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Fixed TTL (seconds) for all lease-expiry tests. No sleeps.
FIXED_TTL = 30


@pytest.fixture
def fixed_clock():
    """Return a timezone-aware timestamp captured at test execution time."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def _seed_run(store, idempotency_key: str = "key-1"):
    """Create a project, conversation, and run, returning the run."""
    project = store.create_project("file:///repo", "strict")
    conversation = store.create_conversation(project.id, "inspect conversation")
    return store.create_run(
        conversation.id,
        runner_id="runner-1",
        model_id="model-1",
        execution_target="local",
        mode="inspect",
        idempotency_key=idempotency_key,
    )


def _close(store) -> None:
    """Close a store if it exposes a public close method."""
    closer = getattr(store, "close", None)
    if closer is not None:
        closer()


def _artifact_id(artifact):
    """Return the public id of an artifact, or the artifact itself if it is a plain id."""
    return getattr(artifact, "id", artifact)


def test_command_kind_is_str_enum_with_required_members():
    """CommandKind is a string enum exposing the six required command types."""
    from mcp_server_nucleus.runs.models import CommandKind

    assert issubclass(CommandKind, str)
    for name in ("CANCEL", "STEER", "ANSWER", "APPROVE", "PAUSE", "RESUME"):
        assert hasattr(CommandKind, name)
        assert CommandKind[name].upper() == name


def test_run_command_lease_artifact_are_dataclasses():
    """RunCommand, Lease, and Artifact are attribute dataclasses."""
    from mcp_server_nucleus.runs.models import Artifact, Lease, RunCommand

    assert dataclasses.is_dataclass(RunCommand)
    assert dataclasses.is_dataclass(Lease)
    assert dataclasses.is_dataclass(Artifact)


def test_enqueue_command_allocates_contiguous_per_run_sequence(tmp_path):
    """enqueue_command allocates contiguous per-run command sequence numbers."""
    from mcp_server_nucleus.runs.models import CommandKind
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run1 = _seed_run(store)
        run2 = _seed_run(store, idempotency_key="key-2")

        c1 = store.enqueue_command(run1.id, CommandKind.STEER, {"turn": "left"}, "user")
        c2 = store.enqueue_command(run1.id, CommandKind.PAUSE, {}, "user")
        c3 = store.enqueue_command(run1.id, CommandKind.RESUME, {}, "user")
        d1 = store.enqueue_command(run2.id, CommandKind.CANCEL, None, "user")

        assert [c1.seq, c2.seq, c3.seq] == [1, 2, 3]
        assert d1.seq == 1
    finally:
        _close(store)


def test_list_commands_and_consume_once_with_lease_fencing(fixed_clock, tmp_path):
    """list_commands respects after_seq and consumed; consume marks once and fences."""
    from mcp_server_nucleus.runs.models import CommandKind
    from mcp_server_nucleus.runs.store import RunStore, StaleLease

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        cmd1 = store.enqueue_command(run.id, CommandKind.STEER, {"x": 1}, "user")
        cmd2 = store.enqueue_command(run.id, CommandKind.ANSWER, {"x": 2}, "user")

        assert len(store.list_commands(run.id)) == 2
        assert len(store.list_commands(run.id, after_seq=1)) == 1
        assert store.list_commands(run.id, after_seq=1)[0].seq == 2
        assert len(store.list_commands(run.id, include_consumed=False)) == 2

        lease = store.acquire_lease(
            f"run:{run.id}",
            "worker-A",
            FIXED_TTL,
            now=fixed_clock,
        )
        store.consume_command(cmd1.id, "worker-A", lease.fencing_token)

        unconsumed = store.list_commands(run.id, include_consumed=False)
        assert len(unconsumed) == 1 and unconsumed[0].seq == 2

        consumed = [c for c in store.list_commands(run.id, include_consumed=True) if c.seq == 1]
        assert len(consumed) == 1 and consumed[0].consumed is True

        with pytest.raises(StaleLease):
            store.consume_command(cmd2.id, "worker-A", lease.fencing_token + 999)
    finally:
        _close(store)


def test_lease_acquire_conflict_expiry_and_fencing_token(fixed_clock, tmp_path):
    """Unexpired other owner raises LeaseConflict; after expiry a new owner gets a higher token."""
    from mcp_server_nucleus.runs.store import LeaseConflict, RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        resource = f"run:{run.id}"

        lease1 = store.acquire_lease(resource, "worker-A", FIXED_TTL, now=fixed_clock)
        assert lease1.owner_id == "worker-A"
        assert isinstance(lease1.fencing_token, int)
        assert lease1.fencing_token > 0

        with pytest.raises(LeaseConflict):
            store.acquire_lease(resource, "worker-B", FIXED_TTL, now=fixed_clock)

        later = fixed_clock + timedelta(seconds=FIXED_TTL + 1)
        lease2 = store.acquire_lease(resource, "worker-B", FIXED_TTL, now=later)
        assert lease2.owner_id == "worker-B"
        assert lease2.fencing_token > lease1.fencing_token
    finally:
        _close(store)


def test_lease_renew_release_and_get_fenced_by_owner_token(fixed_clock, tmp_path):
    """renew_lease, release_lease, and get_lease all require owner+token fencing."""
    from mcp_server_nucleus.runs.store import RunStore, StaleLease

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        resource = f"run:{run.id}"

        lease = store.acquire_lease(resource, "worker-A", FIXED_TTL, now=fixed_clock)
        renewed = store.renew_lease(
            resource,
            "worker-A",
            lease.fencing_token,
            FIXED_TTL,
            now=fixed_clock + timedelta(seconds=1),
        )
        assert renewed.fencing_token == lease.fencing_token
        assert renewed.expires_at > lease.expires_at

        with pytest.raises(StaleLease):
            store.renew_lease(resource, "worker-A", lease.fencing_token + 1, FIXED_TTL)

        with pytest.raises(StaleLease):
            store.release_lease(resource, "worker-A", lease.fencing_token + 1)

        store.release_lease(resource, "worker-A", lease.fencing_token)
        assert store.get_lease(resource) is None

        new_lease = store.acquire_lease(
            resource,
            "worker-B",
            FIXED_TTL,
            now=fixed_clock + timedelta(seconds=2),
        )
        assert new_lease.fencing_token > lease.fencing_token
    finally:
        _close(store)


def test_consume_command_rejects_stale_lease_after_expiry(fixed_clock, tmp_path):
    """A token rendered stale by a newer owner after expiry is rejected by consume_command."""
    from mcp_server_nucleus.runs.models import CommandKind
    from mcp_server_nucleus.runs.store import RunStore, StaleLease

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        resource = f"run:{run.id}"
        cmd = store.enqueue_command(run.id, CommandKind.CANCEL, {}, "user")

        old_lease = store.acquire_lease(resource, "worker-A", FIXED_TTL, now=fixed_clock)
        later = fixed_clock + timedelta(seconds=FIXED_TTL + 1)
        store.acquire_lease(resource, "worker-B", FIXED_TTL, now=later)

        with pytest.raises(StaleLease):
            store.consume_command(cmd.id, "worker-A", old_lease.fencing_token)
    finally:
        _close(store)


def test_append_event_requires_active_run_lease_and_keeps_contiguous_seq(fixed_clock, tmp_path):
    """append_event allocates contiguous seq and rejects an invalid or missing lease token."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.store import RunStore, StaleLease

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        for state, event in (
            (RunState.QUEUED, "run.queued"),
            (RunState.PREPARING, "run.preparing"),
            (RunState.RUNNING, "run.running"),
        ):
            store.transition_run(run.id, state, event)

        lease = store.acquire_lease(f"run:{run.id}", "worker-A", FIXED_TTL, now=fixed_clock)

        ev1 = store.append_event(
            run.id,
            "handler.step",
            {"n": 1},
            owner_id="worker-A",
            fencing_token=lease.fencing_token,
        )
        ev2 = store.append_event(
            run.id,
            "handler.step",
            {"n": 2},
            owner_id="worker-A",
            fencing_token=lease.fencing_token,
        )
        assert [ev1.seq, ev2.seq] == [5, 6]

        with pytest.raises(StaleLease):
            store.append_event(
                run.id,
                "handler.step",
                {},
                owner_id="worker-A",
                fencing_token=lease.fencing_token + 1,
            )
    finally:
        _close(store)


def test_store_artifact_metadata_methods(tmp_path):
    """RunStore exposes record_artifact, get_artifact, and list_artifacts for ArtifactStore."""
    from mcp_server_nucleus.runs.models import Artifact
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        sha = hashlib.sha256(b"hello").hexdigest()

        artifact = store.record_artifact(
            run.id,
            "output",
            sha,
            "text/plain",
            5,
            metadata={"foo": "bar"},
        )

        assert isinstance(artifact, Artifact)
        assert artifact.run_id == run.id
        assert artifact.kind == "output"
        assert artifact.sha256 == sha

        retrieved = store.get_artifact(artifact.id)
        assert retrieved.id == artifact.id

        listed = store.list_artifacts(run.id)
        assert len(listed) == 1
        assert listed[0].id == artifact.id
    finally:
        _close(store)


def test_artifact_store_write_bytes_is_content_addressed_and_idempotent(tmp_path):
    """ArtifactStore writes bytes by SHA-256 and returns the same artifact for identical input."""
    from mcp_server_nucleus.runs.artifacts import ArtifactStore
    from mcp_server_nucleus.runs.store import RunStore

    root = tmp_path / "artifacts"
    db_path = tmp_path / "runs.db"
    run_store = RunStore(str(db_path))
    try:
        run = _seed_run(run_store)
        store = ArtifactStore(str(root), run_store)
        content = b"deterministic content"

        art1 = store.write_bytes(run.id, "log", content, "text/plain", metadata={"tag": "x"})
        art2 = store.write_bytes(run.id, "log", content, "text/plain", metadata={"tag": "x"})

        assert _artifact_id(art1) == _artifact_id(art2)

        listed = run_store.list_artifacts(run.id)
        assert len(listed) == 1
        assert listed[0].id == _artifact_id(art1)

        assert store.read_bytes(_artifact_id(art1)) == content
    finally:
        _close(run_store)


def test_artifact_store_read_bytes_raises_after_tampering(tmp_path):
    """read_bytes verifies SHA-256 and raises ArtifactIntegrityError after file tampering."""
    from mcp_server_nucleus.runs.artifacts import ArtifactIntegrityError, ArtifactStore
    from mcp_server_nucleus.runs.store import RunStore

    root = tmp_path / "artifacts"
    db_path = tmp_path / "runs.db"
    run_store = RunStore(str(db_path))
    try:
        run = _seed_run(run_store)
        store = ArtifactStore(str(root), run_store)
        content = b"tamper me"

        artifact = store.write_bytes(run.id, "log", content, "text/plain")
        artifact_id = _artifact_id(artifact)
        assert store.read_bytes(artifact_id) == content

        data_file = next(
            p
            for p in Path(root).rglob("*")
            if p.is_file() and p.read_bytes() == content
        )
        data_file.write_bytes(b"corrupt")

        with pytest.raises(ArtifactIntegrityError):
            store.read_bytes(artifact_id)
    finally:
        _close(run_store)


def test_run_service_queue_run_and_request_cancel(tmp_path):
    """queue_run transitions CREATED->QUEUED; request_cancel enqueues CANCEL without state change."""
    from mcp_server_nucleus.runs.models import CommandKind, RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        service = RunService(store)

        queued = service.queue_run(run.id)
        assert queued.state is RunState.QUEUED

        events = store.list_events(run.id)
        assert [e.type for e in events] == ["run.created", "run.queued"]

        before = store.get_run(run.id)
        service.request_cancel(run.id, "user")
        after = store.get_run(run.id)

        assert before.state is RunState.QUEUED
        assert after.state is RunState.QUEUED

        commands = store.list_commands(run.id)
        assert len(commands) == 1
        assert commands[0].kind is CommandKind.CANCEL
        assert commands[0].issuer == "user"
    finally:
        _close(store)


def test_run_worker_execute_lifecycle_and_emits_events(tmp_path):
    """RunWorker executes QUEUED->PREPARING->RUNNING, runs handler, emits events, completes."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        RunService(store).queue_run(run.id)

        def handler(ctx):
            ctx.emit("handler.progress", {"pct": 50})
            ctx.emit("handler.done", {"ok": True})

        worker = RunWorker(store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        worker.execute(handler)

        final = store.get_run(run.id)
        assert final.state is RunState.COMPLETED

        events = store.list_events(run.id)
        assert [e.type for e in events] == [
            "run.created",
            "run.queued",
            "run.preparing",
            "run.running",
            "handler.progress",
            "handler.done",
            "run.completed",
        ]

        assert store.get_lease(f"run:{run.id}") is None
    finally:
        _close(store)


def test_run_worker_consumes_cancel_command_and_skips_handler(tmp_path):
    """A CANCEL queued before execute is consumed, the handler is not called, state is CANCELLED."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        service = RunService(store)
        service.queue_run(run.id)
        service.request_cancel(run.id, "user")

        handler_called = False

        def handler(ctx):
            nonlocal handler_called
            handler_called = True
            ctx.emit("x", {})

        worker = RunWorker(store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        worker.execute(handler)

        assert handler_called is False
        final = store.get_run(run.id)
        assert final.state is RunState.CANCELLED

        events = store.list_events(run.id)
        assert [e.type for e in events] == [
            "run.created",
            "run.queued",
            "run.cancelled",
        ]

        assert store.get_lease(f"run:{run.id}") is None
    finally:
        _close(store)


def test_run_worker_handler_exception_transitions_failed_and_releases_lease(tmp_path):
    """A handler exception sets FAILED with a safe error payload, releases lease, and re-raises."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    store = RunStore(str(tmp_path / "runs.db"))
    try:
        run = _seed_run(store)
        RunService(store).queue_run(run.id)

        def handler(ctx):
            ctx.emit("handler.before", {})
            raise RuntimeError("boom")

        worker = RunWorker(store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        with pytest.raises(RuntimeError, match="boom"):
            worker.execute(handler)

        final = store.get_run(run.id)
        assert final.state is RunState.FAILED

        events = store.list_events(run.id)
        assert [e.type for e in events] == [
            "run.created",
            "run.queued",
            "run.preparing",
            "run.running",
            "handler.before",
            "run.failed",
        ]

        failed = events[-1]
        assert "error_type" in failed.payload
        assert "message" in failed.payload
        assert failed.payload["error_type"] == "RuntimeError"
        assert isinstance(failed.payload["message"], str)
        assert failed.payload["message"]
        assert "Traceback" not in failed.payload["message"]

        assert store.get_lease(f"run:{run.id}") is None
    finally:
        _close(store)
