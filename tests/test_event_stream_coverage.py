"""Coverage tests for mcp_server_nucleus.runtime.event_stream."""
import json
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.runtime.event_stream import (
    EventSeverity,
    EventTypes,
    get_events_path,
    read_events,
    emit_event,
    get_unprocessed_events,
    get_critical_events,
    rotate_events,
)


def test_event_severity_values():
    assert EventSeverity.ROUTINE.value == "ROUTINE"
    assert EventSeverity.NOTABLE.value == "NOTABLE"
    assert EventSeverity.CRITICAL.value == "CRITICAL"


def test_event_types_constants():
    assert EventTypes.TASK_ASSIGNED == "task_assigned"
    assert EventTypes.TASK_COMPLETED == "task_completed"
    assert EventTypes.FEDERATION_PEER_JOINED == "federation_peer_joined"
    assert EventTypes.DECISION_MADE == "decision_made"


def test_get_events_path(tmp_path):
    path = get_events_path(tmp_path)
    assert path == tmp_path / "ledger" / "events.jsonl"


def test_read_events_empty(tmp_path):
    assert read_events(tmp_path) == []


def test_read_events_with_data(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    events = [
        {"event_id": "e1", "severity": "ROUTINE"},
        {"event_id": "e2", "severity": "CRITICAL"},
        {"event_id": "e3", "severity": "NOTABLE"},
    ]
    with open(events_path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    result = read_events(tmp_path, limit=2)
    # Returns last N reversed (newest first)
    assert len(result) == 2
    assert result[0]["event_id"] == "e3"
    assert result[1]["event_id"] == "e2"


def test_read_events_skips_malformed(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        f.write(json.dumps({"event_id": "e1"}) + "\n")
        f.write("not valid json\n")
        f.write(json.dumps({"event_id": "e2"}) + "\n")
    result = read_events(tmp_path)
    assert len(result) == 2


def test_emit_event(tmp_path):
    event = emit_event(
        tmp_path,
        "task_assigned",
        "test_emitter",
        {"task": "t1"},
        severity=EventSeverity.NOTABLE,
        metadata={"meta": "val"},
    )
    assert "event_id" in event
    assert event["event_type"] == "task_assigned"
    assert event["emitter"] == "test_emitter"
    assert event["severity"] == "NOTABLE"
    assert event["payload"] == {"task": "t1"}
    assert event["metadata"] == {"meta": "val"}

    # Verify it was written
    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0]["event_id"] == event["event_id"]


def test_emit_event_default_metadata(tmp_path):
    event = emit_event(tmp_path, "test", "em", {})
    assert event["metadata"] == {}


def test_emit_event_firestore_bridge_failure(tmp_path, monkeypatch):
    """emit_event should not fail when firestore bridge raises."""
    def fake_get_bridge():
        class BadBridge:
            def push_event(self, event):
                raise RuntimeError("network down")
        return BadBridge()

    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.firestore_bridge.get_bridge",
        fake_get_bridge,
    )
    event = emit_event(tmp_path, "test", "em", {})
    assert event is not None


def test_get_unprocessed_events_no_last_id(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        for i in range(5):
            f.write(json.dumps({"event_id": f"e{i}", "severity": "ROUTINE"}) + "\n")
    result = get_unprocessed_events(tmp_path)
    assert len(result) == 5


def test_get_unprocessed_events_with_last_id(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        for i in range(5):
            f.write(json.dumps({"event_id": f"e{i}", "severity": "ROUTINE"}) + "\n")
    result = get_unprocessed_events(tmp_path, last_processed_id="e2")
    # read_events returns newest first: [e4, e3, e2, e1, e0]
    # After finding e2, subsequent events in list are e1, e0
    ids = [e["event_id"] for e in result]
    assert "e1" in ids
    assert "e0" in ids
    assert "e2" not in ids


def test_get_unprocessed_events_last_id_not_found(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        f.write(json.dumps({"event_id": "e0", "severity": "ROUTINE"}) + "\n")
    result = get_unprocessed_events(tmp_path, last_processed_id="nonexistent")
    # If not found, returns all events
    assert len(result) == 1


def test_get_unprocessed_events_severity_filter(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        f.write(json.dumps({"event_id": "e0", "severity": "ROUTINE"}) + "\n")
        f.write(json.dumps({"event_id": "e1", "severity": "CRITICAL"}) + "\n")
        f.write(json.dumps({"event_id": "e2", "severity": "ROUTINE"}) + "\n")
    result = get_unprocessed_events(tmp_path, severity_filter=EventSeverity.CRITICAL)
    assert len(result) == 1
    assert result[0]["severity"] == "CRITICAL"


def test_get_critical_events(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        f.write(json.dumps({"event_id": "e0", "severity": "ROUTINE"}) + "\n")
        f.write(json.dumps({"event_id": "e1", "severity": "CRITICAL"}) + "\n")
        f.write(json.dumps({"event_id": "e2", "severity": "CRITICAL"}) + "\n")
    result = get_critical_events(tmp_path, limit=5)
    assert len(result) == 2
    assert all(e["severity"] == "CRITICAL" for e in result)


def test_get_critical_events_empty(tmp_path):
    result = get_critical_events(tmp_path)
    assert result == []


def test_rotate_events_no_file(tmp_path):
    assert rotate_events(tmp_path) == 0


def test_rotate_events_under_limit(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        for i in range(5):
            f.write(json.dumps({"event_id": f"e{i}"}) + "\n")
    assert rotate_events(tmp_path, keep_count=10) == 0


def test_rotate_events_archives(tmp_path):
    events_path = tmp_path / "ledger" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    with open(events_path, "w") as f:
        for i in range(15):
            f.write(json.dumps({"event_id": f"e{i}"}) + "\n")
    archived = rotate_events(tmp_path, keep_count=10)
    assert archived == 5

    # Verify archive file exists
    archive_dir = tmp_path / "ledger" / "archive"
    assert archive_dir.exists()
    archive_files = list(archive_dir.glob("*.jsonl"))
    assert len(archive_files) == 1

    # Verify main file has 10 events
    with open(events_path) as f:
        lines = [l for l in f if l.strip()]
    assert len(lines) == 10
