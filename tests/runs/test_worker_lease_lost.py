import uuid

import pytest

from mcp_server_nucleus.runs.models import RunState
from mcp_server_nucleus.runs.store import RunStore
from mcp_server_nucleus.runs.worker import RunWorker, WorkerLeaseLost


def test_worker_lease_lost_transitions_to_failed(tmp_path):
    db_path = tmp_path / "runs.db"
    store = RunStore(db_path)

    project = store.create_project("file:///tmp/test", "default")
    conv = store.create_conversation(project.id, "test")
    run = store.create_run(conv.id, "agy", "gpt-4", "local", "write", str(uuid.uuid4()))

    worker = RunWorker(store, run.id, "owner-1")

    def failing_handler(ctx):
        raise WorkerLeaseLost("lease lost during execution")

    with pytest.raises(WorkerLeaseLost):
        worker.execute(failing_handler)

    updated_run = store.get_run(run.id)
    assert updated_run.state == RunState.FAILED
    events = store.list_events(run.id)
    failed_events = [e for e in events if e.type == "run.failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload == {"error_type": "WorkerLeaseLost", "phase": "lease"}
