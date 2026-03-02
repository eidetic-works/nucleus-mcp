"""
Tests for Proactive Sync Hooks — event_ops._emit_event() and db.py backends.
Verifies that tool-level writes immediately update the ChangeLedger
without waiting for Watchdog filesystem detection.
"""

import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.runtime.event_bus import (
    ChangeLedger,
    get_change_ledger,
    FILE_TO_URI_MAP,
)


# ─── Bug Fix Test ──────────────────────────────────────────────


class TestNucleusDbMapping:
    """Verify that nucleus.db is mapped in FILE_TO_URI_MAP."""

    def test_nucleus_db_in_file_to_uri_map(self):
        assert "nucleus.db" in FILE_TO_URI_MAP
        assert "brain://state" in FILE_TO_URI_MAP["nucleus.db"]
        assert "brain://context" in FILE_TO_URI_MAP["nucleus.db"]

    def test_nucleus_db_record_change_maps_to_state(self):
        ledger = ChangeLedger()
        affected = ledger.record_change("nucleus.db", "modified")
        assert "brain://state" in affected
        assert "brain://context" in affected
        snap = ledger.get_snapshot()
        assert snap["uri_versions"]["brain://state"]["version"] == 1


# ─── Proactive Hook: _emit_event ──────────────────────────────


class TestEmitEventHook:
    """Verify _emit_event proactively updates ChangeLedger."""

    def test_emit_event_increments_events_uri(self):
        """Calling _emit_event should bump brain://events via proactive hook."""
        ledger = ChangeLedger()

        # Create minimal brain structure
        with tempfile.TemporaryDirectory() as tmpdir:
            brain = Path(tmpdir)
            (brain / "ledger").mkdir(parents=True, exist_ok=True)
            (brain / "ledger" / "events.jsonl").touch()
            (brain / "ledger" / "interaction_log.jsonl").touch()
            (brain / "ledger" / "activity_summary.json").write_text("{}")

            # Patch get_brain_path and get_change_ledger at the SOURCE
            # where _emit_event imports them from
            with patch(
                "mcp_server_nucleus.runtime.event_ops.get_brain_path",
                return_value=brain,
            ), patch(
                "mcp_server_nucleus.runtime.event_bus.get_change_ledger",
                return_value=ledger,
            ), patch(
                "mcp_server_nucleus.runtime.event_bus._global_ledger",
                ledger,
            ):
                # Import and call _emit_event (it does `from .event_bus import get_change_ledger` internally)
                from mcp_server_nucleus.runtime.event_ops import _emit_event

                # We need to ensure the lazy import inside _emit_event gets our mock.
                # Since _emit_event does `from .event_bus import get_change_ledger`,
                # we mock the module-level function in event_bus.
                result = _emit_event(
                    event_type="task_added",
                    emitter="test",
                    data={"task": "test task"},
                    description="test event",
                )

        # The hook calls get_change_ledger().record_change("events.jsonl", ...)
        assert ledger.get_global_version() >= 1
        snap = ledger.get_snapshot()
        assert "brain://events" in snap["uri_versions"]


# ─── Proactive Hook: db.py backends ───────────────────────────


class TestDbProactiveHook:
    """Verify db.py backends call _notify_tasks_changed on task writes."""

    def test_json_backend_add_task_signals_ledger(self):
        """JSONBackend.add_task should signal ChangeLedger via _notify_tasks_changed."""
        from mcp_server_nucleus.runtime.db import JSONBackend, _notify_tasks_changed

        with tempfile.TemporaryDirectory() as tmpdir:
            brain_path = Path(tmpdir)
            (brain_path / "ledger").mkdir(parents=True, exist_ok=True)
            (brain_path / "ledger" / "tasks.json").write_text("[]")

            with patch(
                "mcp_server_nucleus.runtime.db._notify_tasks_changed"
            ) as mock_notify:
                backend = JSONBackend(brain_path)
                backend.add_task({
                    "id": "tsk-001",
                    "description": "Test task",
                    "status": "pending",
                    "priority": 5,
                    "blocked_by": [],
                    "required_skills": [],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                })

                assert mock_notify.called

    def test_sqlite_backend_add_task_signals_ledger(self):
        """SQLiteBackend.add_task should signal ChangeLedger."""
        from mcp_server_nucleus.runtime.db import SQLiteBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            brain_path = Path(tmpdir)

            with patch(
                "mcp_server_nucleus.runtime.db._notify_tasks_changed"
            ) as mock_notify:
                backend = SQLiteBackend(brain_path)
                backend.add_task({
                    "id": "tsk-002",
                    "description": "SQLite test task",
                    "status": "pending",
                    "priority": 3,
                    "blocked_by": [],
                    "required_skills": ["python"],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                })

                assert mock_notify.called
                assert mock_notify.call_count == 1

    def test_sqlite_backend_update_task_signals_ledger(self):
        """SQLiteBackend.update_task should signal ChangeLedger when rows change."""
        from mcp_server_nucleus.runtime.db import SQLiteBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            brain_path = Path(tmpdir)
            backend = SQLiteBackend(brain_path)

            # Add a task first (outside mock to not count this call)
            backend.add_task({
                "id": "tsk-003",
                "description": "Task to update",
                "status": "pending",
                "priority": 5,
                "blocked_by": [],
                "required_skills": [],
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            })

            with patch(
                "mcp_server_nucleus.runtime.db._notify_tasks_changed"
            ) as mock_notify:
                result = backend.update_task("tsk-003", {"status": "done"})
                assert result is True
                assert mock_notify.called

    def test_sqlite_backend_update_nonexistent_no_signal(self):
        """SQLiteBackend.update_task should NOT signal if no rows changed."""
        from mcp_server_nucleus.runtime.db import SQLiteBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            brain_path = Path(tmpdir)
            backend = SQLiteBackend(brain_path)

            with patch(
                "mcp_server_nucleus.runtime.db._notify_tasks_changed"
            ) as mock_notify:
                result = backend.update_task("nonexistent", {"status": "done"})
                assert result is False
                assert not mock_notify.called


class TestNotifyTasksChangedFunction:
    """Test the _notify_tasks_changed helper directly."""

    def test_notify_calls_record_change(self):
        """_notify_tasks_changed should call ChangeLedger.record_change."""
        ledger = ChangeLedger()

        # Patch at the event_bus module level since _notify_tasks_changed
        # does `from .event_bus import get_change_ledger` internally
        with patch(
            "mcp_server_nucleus.runtime.event_bus._global_ledger",
            ledger,
        ):
            from mcp_server_nucleus.runtime.db import _notify_tasks_changed
            _notify_tasks_changed()

        assert ledger.get_global_version() == 1
        snap = ledger.get_snapshot()
        assert "brain://state" in snap["uri_versions"]
        assert "brain://context" in snap["uri_versions"]

    def test_notify_never_raises(self):
        """_notify_tasks_changed must never raise, even on import error."""
        # Simulate broken import by patching get_change_ledger to raise
        with patch(
            "mcp_server_nucleus.runtime.event_bus.get_change_ledger",
            side_effect=RuntimeError("boom"),
        ):
            from mcp_server_nucleus.runtime.db import _notify_tasks_changed
            # Should not raise
            _notify_tasks_changed()
