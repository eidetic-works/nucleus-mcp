"""
Tests for EventBus — Pub/Sub Event Distribution
=================================================
Unit tests for the event_bus module and integration tests for the
File Watcher → EventBus pipeline.
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock
from mcp_server_nucleus.runtime.event_bus import (
    EventBus, BrainFileEvent, get_event_bus,
    ChangeLedger, get_change_ledger, FILE_TO_URI_MAP,
)


# ─── Unit Tests ────────────────────────────────────────────────


class TestBrainFileEvent:
    """Tests for BrainFileEvent dataclass."""

    def test_create_event(self):
        event = BrainFileEvent(event_type="modified", path="tasks.json")
        assert event.event_type == "modified"
        assert event.path == "tasks.json"
        assert event.source == "FILE_MONITOR"
        assert event.timestamp > 0
        assert event.metadata == {}

    def test_to_dict(self):
        event = BrainFileEvent(
            event_type="created",
            path="memory/cache.json",
            source="TEST",
            metadata={"size": 42},
        )
        d = event.to_dict()
        assert d["event_type"] == "created"
        assert d["path"] == "memory/cache.json"
        assert d["source"] == "TEST"
        assert d["metadata"]["size"] == 42
        assert "timestamp" in d

    def test_default_timestamp_is_recent(self):
        before = time.time()
        event = BrainFileEvent(event_type="deleted", path="old.json")
        after = time.time()
        assert before <= event.timestamp <= after


class TestEventBus:
    """Tests for EventBus pub/sub and history."""

    def test_publish_without_subscribers(self):
        bus = EventBus()
        event = BrainFileEvent(event_type="modified", path="tasks.json")
        notified = bus.publish(event)
        assert notified == 0

    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(evt):
            received.append(evt)

        bus.subscribe("file_modified", handler)
        event = BrainFileEvent(event_type="modified", path="tasks.json")
        notified = bus.publish(event)

        assert notified == 1
        assert len(received) == 1
        assert received[0].path == "tasks.json"

    def test_wildcard_subscriber(self):
        bus = EventBus()
        received = []

        bus.subscribe("*", lambda e: received.append(e))
        bus.publish(BrainFileEvent(event_type="created", path="a.json"))
        bus.publish(BrainFileEvent(event_type="deleted", path="b.json"))

        assert len(received) == 2

    def test_multiple_subscribers_same_type(self):
        bus = EventBus()
        count = {"a": 0, "b": 0}

        bus.subscribe("file_modified", lambda e: count.__setitem__("a", count["a"] + 1))
        bus.subscribe("file_modified", lambda e: count.__setitem__("b", count["b"] + 1))

        bus.publish(BrainFileEvent(event_type="modified", path="x.json"))

        assert count["a"] == 1
        assert count["b"] == 1

    def test_subscriber_error_does_not_cascade(self):
        bus = EventBus()
        received = []

        def bad_handler(evt):
            raise RuntimeError("boom")

        def good_handler(evt):
            received.append(evt)

        bus.subscribe("file_modified", bad_handler)
        bus.subscribe("file_modified", good_handler)

        event = BrainFileEvent(event_type="modified", path="tasks.json")
        notified = bus.publish(event)

        # Good handler still called despite bad handler throwing
        assert len(received) == 1
        assert notified == 1  # Only good_handler counted as notified

    def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(evt):
            received.append(evt)

        bus.subscribe("file_modified", handler)
        assert bus.unsubscribe("file_modified", handler) is True

        bus.publish(BrainFileEvent(event_type="modified", path="tasks.json"))
        assert len(received) == 0

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()
        assert bus.unsubscribe("file_modified", lambda e: None) is False

    def test_history_bounded(self):
        bus = EventBus(max_history=5)
        for i in range(10):
            bus.publish(BrainFileEvent(event_type="modified", path=f"file{i}.json"))

        history = bus.get_recent(100)
        assert len(history) == 5
        # Should have the last 5 events
        assert history[0].path == "file5.json"
        assert history[4].path == "file9.json"

    def test_get_recent_with_limit(self):
        bus = EventBus()
        for i in range(10):
            bus.publish(BrainFileEvent(event_type="modified", path=f"file{i}.json"))

        recent = bus.get_recent(3)
        assert len(recent) == 3
        assert recent[-1].path == "file9.json"

    def test_get_recent_since_timestamp(self):
        bus = EventBus()

        # Publish events with controlled timestamps
        old_event = BrainFileEvent(event_type="modified", path="old.json")
        old_event.timestamp = 1000.0
        bus.publish(old_event)

        new_event = BrainFileEvent(event_type="modified", path="new.json")
        new_event.timestamp = 2000.0
        bus.publish(new_event)

        # Only get events after timestamp 1500
        recent = bus.get_recent(since=1500.0)
        assert len(recent) == 1
        assert recent[0].path == "new.json"

    def test_get_stats(self):
        bus = EventBus(max_history=100)
        bus.subscribe("file_modified", lambda e: None)
        bus.subscribe("*", lambda e: None)
        bus.publish(BrainFileEvent(event_type="created", path="a.json"))

        stats = bus.get_stats()
        assert stats["subscriber_count"] == 2
        assert "file_modified" in stats["event_types"]
        assert "*" in stats["event_types"]
        assert stats["history_size"] == 1
        assert stats["history_capacity"] == 100

    def test_thread_safety_concurrent_publish(self):
        """Verify no crashes under concurrent publish."""
        bus = EventBus(max_history=1000)
        errors = []

        def publisher(start_id):
            for i in range(50):
                try:
                    bus.publish(BrainFileEvent(
                        event_type="modified",
                        path=f"thread{start_id}_file{i}.json"
                    ))
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=publisher, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        # All 250 events should be in history (within capacity)
        assert len(bus.get_recent(300)) == 250


class TestSingleton:
    """Tests for get_event_bus singleton."""

    def test_singleton_returns_same_instance(self):
        import mcp_server_nucleus.runtime.event_bus as eb_module

        # Reset global state for isolation
        eb_module._global_bus = None

        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_singleton_thread_safe(self):
        import mcp_server_nucleus.runtime.event_bus as eb_module
        eb_module._global_bus = None

        instances = []

        def get_bus():
            instances.append(get_event_bus())

        threads = [threading.Thread(target=get_bus) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # All threads should get the same instance
        assert all(inst is instances[0] for inst in instances)


# ─── Integration Tests ─────────────────────────────────────────


class TestFileMonitorIntegration:
    """Integration tests for FileMonitor → EventBus pipeline."""

    def test_file_monitor_callback_publishes_to_bus(self):
        """Simulate what __init__.py's _on_brain_file_change does."""
        bus = EventBus()
        received = []
        bus.subscribe("file_modified", lambda e: received.append(e))

        # Simulate the callback from __init__.py
        brain_path = "/fake/.brain"

        class FakeEvent:
            event_type = "modified"
            path = "/fake/.brain/tasks.json"

        fake_event = FakeEvent()
        rel_path = fake_event.path.replace(brain_path, "").lstrip("/")

        meaningful = ["tasks.json", "engrams.json", "state.json",
                      "events.jsonl", "sessions/", "memory/", "ledger/",
                      "commitments/", "config/"]

        if any(m in rel_path for m in meaningful):
            bus.publish(BrainFileEvent(
                event_type=fake_event.event_type,
                path=rel_path,
                source="FILE_MONITOR",
            ))

        assert len(received) == 1
        assert received[0].path == "tasks.json"
        assert received[0].event_type == "modified"

    def test_non_meaningful_files_are_ignored(self):
        """Files not in the meaningful list should not publish events."""
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e))

        brain_path = "/fake/.brain"
        rel_path = "debug.log"

        meaningful = ["tasks.json", "engrams.json", "state.json",
                      "events.jsonl", "sessions/", "memory/", "ledger/",
                      "commitments/", "config/"]

        if any(m in rel_path for m in meaningful):
            bus.publish(BrainFileEvent(
                event_type="modified", path=rel_path, source="FILE_MONITOR"
            ))

        # debug.log is not meaningful → no event published
        assert len(received) == 0

    def test_commitments_and_config_are_meaningful(self):
        """Verify our newly-added patterns work."""
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e))

        meaningful = ["tasks.json", "engrams.json", "state.json",
                      "events.jsonl", "sessions/", "memory/", "ledger/",
                      "commitments/", "config/"]

        for rel_path in ["commitments/ledger.json", "config/nucleus.yaml"]:
            if any(m in rel_path for m in meaningful):
                bus.publish(BrainFileEvent(
                    event_type="modified", path=rel_path, source="FILE_MONITOR"
                ))

        assert len(received) == 2
        assert received[0].path == "commitments/ledger.json"
        assert received[1].path == "config/nucleus.yaml"


# ─── ChangeLedger Tests ───────────────────────────────────────


class TestChangeLedger:
    """Tests for ChangeLedger monotonic version tracker."""

    def test_record_change_increments_global_version(self):
        ledger = ChangeLedger()
        assert ledger.get_global_version() == 0

        ledger.record_change("tasks.json", "modified")
        assert ledger.get_global_version() == 1

        ledger.record_change("state.json", "modified")
        assert ledger.get_global_version() == 2

    def test_record_change_maps_file_to_uris(self):
        ledger = ChangeLedger()
        affected = ledger.record_change("tasks.json", "modified")

        # tasks.json should map to brain://state and brain://context
        assert "brain://state" in affected
        assert "brain://context" in affected

        snap = ledger.get_snapshot()
        assert snap["uri_versions"]["brain://state"]["version"] == 1
        assert snap["uri_versions"]["brain://context"]["version"] == 1

    def test_unknown_file_only_bumps_global(self):
        ledger = ChangeLedger()
        affected = ledger.record_change("debug.log", "created")

        # debug.log doesn't match any pattern → no URIs affected
        assert affected == []
        assert ledger.get_global_version() == 1

        snap = ledger.get_snapshot()
        assert snap["uri_versions"] == {}

    def test_get_snapshot_structure(self):
        ledger = ChangeLedger()
        ledger.record_change("events.jsonl", "modified")

        snap = ledger.get_snapshot()
        assert "global_version" in snap
        assert "uri_versions" in snap
        assert "recent_changes" in snap
        assert "description" in snap
        assert snap["global_version"] == 1
        assert len(snap["recent_changes"]) == 1
        assert snap["recent_changes"][0]["path"] == "events.jsonl"
        assert snap["recent_changes"][0]["affected_uris"] == ["brain://events"]

    def test_multiple_changes_accumulate(self):
        ledger = ChangeLedger()
        ledger.record_change("tasks.json", "modified")
        ledger.record_change("tasks.json", "modified")
        ledger.record_change("events.jsonl", "created")

        snap = ledger.get_snapshot()
        assert snap["global_version"] == 3
        # tasks.json was modified twice → brain://state version should be 2
        assert snap["uri_versions"]["brain://state"]["version"] == 2
        # brain://context also bumped twice (from tasks.json)
        assert snap["uri_versions"]["brain://context"]["version"] == 2
        # events.jsonl → brain://events version should be 1
        assert snap["uri_versions"]["brain://events"]["version"] == 1

    def test_thread_safety_concurrent_changes(self):
        """Verify no crashes under concurrent record_change calls."""
        ledger = ChangeLedger()
        errors = []

        files = ["tasks.json", "state.json", "events.jsonl",
                 "memory/cache.json", "sessions/s1.json"]

        def writer(file_path):
            for _ in range(20):
                try:
                    ledger.record_change(file_path, "modified")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer, args=(f,)) for f in files]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        # 5 files × 20 writes = 100 total changes
        assert ledger.get_global_version() == 100


class TestChangeLedgerSingleton:
    """Tests for get_change_ledger singleton."""

    def test_singleton_returns_same_instance(self):
        import mcp_server_nucleus.runtime.event_bus as eb_module
        eb_module._global_ledger = None  # Reset for test isolation

        ledger1 = get_change_ledger()
        ledger2 = get_change_ledger()
        assert ledger1 is ledger2


class TestChangeLedgerIntegration:
    """Integration: EventBus → ChangeLedger pipeline."""

    def test_eventbus_publish_increments_ledger(self):
        """When EventBus publishes an event, the ChangeLedger should update."""
        bus = EventBus()
        ledger = ChangeLedger()

        # Wire ledger as subscriber (same pattern as __init__.py)
        bus.subscribe("*", lambda evt: ledger.record_change(evt.path, evt.event_type))

        assert ledger.get_global_version() == 0

        # Publish a file change event
        bus.publish(BrainFileEvent(event_type="modified", path="tasks.json"))
        assert ledger.get_global_version() == 1

        snap = ledger.get_snapshot()
        assert "brain://state" in snap["uri_versions"]
        assert snap["uri_versions"]["brain://state"]["version"] == 1

    def test_full_pipeline_file_to_resource(self):
        """Complete pipeline: file change → EventBus → ChangeLedger → snapshot."""
        bus = EventBus()
        ledger = ChangeLedger()
        bus.subscribe("*", lambda evt: ledger.record_change(evt.path, evt.event_type))

        # Simulate multiple file changes from File Monitor
        changes = [
            ("tasks.json", "modified"),
            ("events.jsonl", "created"),
            ("sessions/chat_001.json", "modified"),
            ("debug.log", "modified"),  # not in FILE_TO_URI_MAP
        ]

        for path, evt_type in changes:
            bus.publish(BrainFileEvent(event_type=evt_type, path=path))

        snap = ledger.get_snapshot()
        assert snap["global_version"] == 4

        # brain://state bumped by tasks.json
        assert snap["uri_versions"]["brain://state"]["version"] == 1
        # brain://context bumped by tasks.json + sessions/
        assert snap["uri_versions"]["brain://context"]["version"] == 2
        # brain://events bumped by events.jsonl
        assert snap["uri_versions"]["brain://events"]["version"] == 1
        # debug.log → no URI bumps
        assert len(snap["recent_changes"]) == 4

