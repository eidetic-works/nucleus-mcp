"""Opposed security contract tests for the Nucleus Renaissance artifact/worker slice."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FIXED_CLOCK = datetime.now(timezone.utc).replace(microsecond=0)
FIXED_TTL = 30


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


def test_artifact_write_escape_raises_and_leaves_no_outside_payload(tmp_path):
    """Subclassing _content_path to point outside the root triggers ArtifactIntegrityError."""
    from mcp_server_nucleus.runs.artifacts import ArtifactStore
    from mcp_server_nucleus.runs.store import RunStore

    root = tmp_path / "artifacts"
    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        escape = tmp_path / "escape.bin"

        class EscapeStore(ArtifactStore):
            def _content_path(self, sha256: str) -> Path:
                return escape

        store = EscapeStore(str(root), run_store)

        with pytest.raises(Exception) as exc_info:
            store.write_bytes(run.id, "log", b"escape-attempt", "text/plain")

        assert type(exc_info.value).__name__ == "ArtifactIntegrityError", exc_info.value
        assert not escape.exists()
        assert run_store.list_artifacts(run.id) == []
    finally:
        _close(run_store)


def test_artifact_metadata_immutability_raises_on_conflict(tmp_path):
    """Rewriting the same run/kind/content with changed mime or metadata is rejected."""
    from mcp_server_nucleus.runs.artifacts import ArtifactStore
    from mcp_server_nucleus.runs.store import RunStore

    root = tmp_path / "artifacts"
    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        store = ArtifactStore(str(root), run_store)
        content = b"immutable-content"
        first = store.write_bytes(
            run.id, "log", content, "text/plain", metadata={"tag": "x"}
        )

        for mime_type, metadata in (
            ("text/html", {"tag": "x"}),
            ("text/plain", {"tag": "y"}),
        ):
            with pytest.raises(Exception) as exc_info:
                store.write_bytes(run.id, "log", content, mime_type, metadata=metadata)
            assert type(exc_info.value).__name__ == "ArtifactConflict", exc_info.value

            listed = run_store.list_artifacts(run.id)
            assert len(listed) == 1
            assert listed[0].id == _artifact_id(first)
            assert listed[0].mime_type == first.mime_type
            assert listed[0].metadata == first.metadata
            assert store.read_bytes(_artifact_id(first)) == content
    finally:
        _close(run_store)


def test_artifact_read_bytes_raises_integrity_on_missing_file(tmp_path):
    """After the content file is unlinked, read_bytes raises ArtifactIntegrityError."""
    from mcp_server_nucleus.runs.artifacts import ArtifactStore
    from mcp_server_nucleus.runs.store import RunStore

    root = tmp_path / "artifacts"
    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        store = ArtifactStore(str(root), run_store)
        content = b"present-then-gone"
        artifact = store.write_bytes(run.id, "log", content, "text/plain")

        data_path = root / artifact.path
        assert data_path.read_bytes() == content
        data_path.unlink()

        with pytest.raises(Exception) as exc_info:
            store.read_bytes(_artifact_id(artifact))
        assert type(exc_info.value).__name__ == "ArtifactIntegrityError", exc_info.value
    finally:
        _close(run_store)


def test_run_worker_failed_event_redacts_and_bounds_secret(tmp_path):
    """A handler error containing an api key is redacted and capped in run.failed."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        RunService(run_store).queue_run(run.id)

        secret = "sk-" + "x" * 35
        filler = "normal-text " * 60
        message = f"api_key={secret} {filler} tail"
        assert len(message) > 512

        def handler(ctx):
            raise RuntimeError(message)

        worker = RunWorker(run_store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        with pytest.raises(RuntimeError, match="api_key="):
            worker.execute(handler)

        final = run_store.get_run(run.id)
        assert final.state is RunState.FAILED

        events = run_store.list_events(run.id)
        failed = events[-1]
        assert failed.type == "run.failed"
        assert failed.payload.get("error_type") == "RuntimeError"

        persisted = failed.payload["message"]
        assert secret not in persisted
        assert "<REDACTED" in persisted
        assert len(persisted) <= 512
    finally:
        _close(run_store)


def test_run_worker_mid_run_cancellation_stops_handler(tmp_path):
    """A handler can request and check cancel; the worker ends in CANCELLED."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        service = RunService(run_store)
        service.queue_run(run.id)

        after_check = []

        def handler(ctx):
            assert hasattr(ctx, "check_cancelled"), "ctx.check_cancelled missing"
            service.request_cancel(run.id, "user")
            ctx.check_cancelled()
            after_check.append(True)
            ctx.emit("after_cancel", {})

        worker = RunWorker(run_store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        try:
            worker.execute(handler)
        except Exception as exc:
            assert False, f"execute raised unexpectedly: {exc!r}"

        final = run_store.get_run(run.id)
        assert final.state is RunState.CANCELLED

        event_types = [e.type for e in run_store.list_events(run.id)]
        assert "run.cancelled" in event_types
        assert "run.completed" not in event_types
        assert "after_cancel" not in event_types
        assert run_store.get_lease(f"run:{run.id}") is None
        assert not after_check
    finally:
        _close(run_store)


def test_run_worker_cleanup_failure_is_visible(tmp_path, monkeypatch):
    """A failing release_lease after a normal handler raises WorkerCleanupError."""
    from mcp_server_nucleus.runs.models import RunState
    from mcp_server_nucleus.runs.service import RunService
    from mcp_server_nucleus.runs.store import RunStore
    from mcp_server_nucleus.runs.worker import RunWorker

    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        RunService(run_store).queue_run(run.id)

        def bad_release(resource, owner_id, fencing_token, now=None):
            raise RuntimeError("release failed")

        monkeypatch.setattr(run_store, "release_lease", bad_release)

        def handler(ctx):
            ctx.emit("ok", {})

        worker = RunWorker(run_store, run.id, "worker-A", lease_ttl_seconds=FIXED_TTL)
        with pytest.raises(Exception) as exc_info:
            worker.execute(handler)

        assert type(exc_info.value).__name__ == "WorkerCleanupError", exc_info.value
        assert exc_info.value.__cause__ is not None
        assert "release failed" in str(exc_info.value.__cause__)

        final = run_store.get_run(run.id)
        assert final.state is RunState.COMPLETED
    finally:
        _close(run_store)


def test_lease_acquire_and_renew_reject_non_positive_ttl(tmp_path):
    """ttl_seconds <= 0 for acquire or renew raises ValueError without mutating the lease."""
    from mcp_server_nucleus.runs.store import RunStore

    db = tmp_path / "runs.db"
    run_store = RunStore(str(db))
    try:
        run = _seed_run(run_store)
        resource = f"run:{run.id}"

        with pytest.raises(ValueError):
            run_store.acquire_lease(resource, "worker-A", 0)
        assert run_store.get_lease(resource) is None

        lease = run_store.acquire_lease(resource, "worker-A", FIXED_TTL)
        before = run_store.get_lease(resource)
        assert before is not None
        assert before.fencing_token == lease.fencing_token

        with pytest.raises(ValueError):
            run_store.renew_lease(resource, "worker-A", lease.fencing_token, -1)

        after = run_store.get_lease(resource)
        assert after is not None
        assert after.expires_at == before.expires_at
    finally:
        _close(run_store)
