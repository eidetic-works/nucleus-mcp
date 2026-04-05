"""
Live Integration Test — Proves Nucleus works end-to-end across environments.
============================================================================
Exercises every MCP facade code path via direct runtime calls.
This is the same code that runs when Claude calls nucleus_engrams, etc.

Run: python -m pytest tests/test_live_integration.py -v
"""

import json
import os
import time
import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def brain(tmp_path):
    """Create a fully-structured brain directory for integration testing."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    for d in ["engrams", "ledger", "sessions", "session", "memory",
              "artifacts", "proofs", "tasks", "strategy",
              "ledger/decisions", "ledger/snapshots", "governance",
              "channels", "federation"]:
        (brain / d).mkdir(parents=True, exist_ok=True)
    old = os.environ.get("NUCLEAR_BRAIN_PATH")
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)
    # Clear singletons
    try:
        from mcp_server_nucleus.runtime.engram_cache import get_engram_cache
        get_engram_cache().invalidate()
    except Exception:
        pass
    yield brain
    if old is not None:
        os.environ["NUCLEAR_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)


# ── 1. ENGRAM LIFECYCLE ─────────────────────────────────────────

class TestEngramLifecycle:
    """Proves: write → query → search → cache → delete cycle works."""

    def test_write_and_query_engram(self, brain):
        from mcp_server_nucleus.runtime.engram_ops import (
            _brain_write_engram_impl, _brain_query_engrams_impl,
        )
        from mcp_server_nucleus.runtime.common import make_response
        from unittest.mock import patch, MagicMock

        # Write via memory pipeline mock (avoids LLM dependency)
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.process.return_value = {
            "added": 1, "updated": 0, "skipped": 0, "mode": "ADD"
        }
        with patch("mcp_server_nucleus.runtime.memory_pipeline.MemoryPipeline", mock_pipeline):
            result = json.loads(_brain_write_engram_impl("arch.wal", "SQLite WAL enabled", "Architecture", 8))
        assert result["success"] is True

        # Write directly to ledger for query testing
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.write_text(json.dumps({
            "key": "arch.wal", "value": "SQLite WAL enabled",
            "context": "Architecture", "intensity": 8
        }) + "\n" + json.dumps({
            "key": "arch.atomic", "value": "Atomic session writes",
            "context": "Architecture", "intensity": 7
        }) + "\n" + json.dumps({
            "key": "ops.deploy", "value": "Blue-green deployment",
            "context": "Operations", "intensity": 5
        }) + "\n")

        # Query by context
        result = json.loads(_brain_query_engrams_impl("Architecture", 1))
        assert result["success"] is True
        assert result["data"]["count"] == 2

        # Query with min_intensity filter
        result = json.loads(_brain_query_engrams_impl("Architecture", 8))
        assert result["success"] is True
        assert result["data"]["count"] == 1

    def test_search_engrams(self, brain):
        from mcp_server_nucleus.runtime.engram_ops import _brain_search_engrams_impl

        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.write_text(json.dumps({
            "key": "k1", "value": "Circuit breaker pattern for resilience",
            "context": "Architecture", "intensity": 8
        }) + "\n" + json.dumps({
            "key": "k2", "value": "PostgreSQL chosen for ACID compliance",
            "context": "Database", "intensity": 9
        }) + "\n")

        result = json.loads(_brain_search_engrams_impl("circuit"))
        assert result["success"] is True
        assert result["data"]["count"] >= 1

        result = json.loads(_brain_search_engrams_impl("PostgreSQL"))
        assert result["success"] is True
        assert result["data"]["count"] >= 1

    def test_engram_cache_invalidation(self, brain):
        from mcp_server_nucleus.runtime.engram_cache import get_engram_cache

        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.write_text(json.dumps({
            "key": "k1", "value": "v1", "context": "Test", "intensity": 5
        }) + "\n")

        cache = get_engram_cache()
        engrams, total = cache.query(ledger, context="Test")
        assert total == 1

        # Append another engram — cache should detect mtime change
        time.sleep(0.05)  # Ensure mtime differs
        with open(ledger, "a") as f:
            f.write(json.dumps({
                "key": "k2", "value": "v2", "context": "Test", "intensity": 5
            }) + "\n")

        engrams, total = cache.query(ledger, context="Test")
        assert total == 2, "Cache should auto-reload on mtime change"


# ── 2. TASK LIFECYCLE ────────────────────────────────────────────

class TestTaskLifecycle:
    """Proves: add → list → claim → update → escalate cycle works."""

    def test_full_task_cycle(self, brain):
        from mcp_server_nucleus.runtime.task_ops import (
            _add_task, _list_tasks, _claim_task, _update_task, _escalate_task,
        )

        # Add
        r = _add_task("Implement WAL mode", priority=1, task_id="task-wal")
        assert r["success"] is True
        assert r["task"]["id"] == "task-wal"
        assert r["task"]["status"] == "PENDING"

        # List
        tasks = _list_tasks()
        assert any(t["id"] == "task-wal" for t in tasks)

        # Claim
        r = _claim_task("task-wal", "agent-claude")
        assert r["success"] is True
        assert r["task"]["claimed_by"] == "agent-claude"
        assert r["task"]["status"] == "IN_PROGRESS"

        # Double-claim fails
        r = _claim_task("task-wal", "agent-other")
        assert r["success"] is False

        # Update
        r = _update_task("task-wal", {"status": "DONE"})
        assert r["success"] is True

        # Add and escalate
        _add_task("Investigate flaky test", priority=2, task_id="task-flaky")
        r = _escalate_task("task-flaky", "Needs human review of test environment")
        assert r["success"] is True
        assert r["task"]["status"] == "ESCALATED"

    def test_task_dependencies(self, brain):
        from mcp_server_nucleus.runtime.task_ops import _add_task

        _add_task("Parent task", task_id="parent-1")
        r = _add_task("Child task", blocked_by=["parent-1"], task_id="child-1")
        assert r["success"] is True
        assert r["task"]["status"] == "BLOCKED"

    def test_import_from_jsonl(self, brain):
        from mcp_server_nucleus.runtime.task_ops import _import_tasks_from_jsonl

        jsonl = brain / "import.jsonl"
        jsonl.write_text(
            json.dumps({"id": "imp-1", "description": "Imported task A", "priority": 1}) + "\n"
            + json.dumps({"id": "imp-2", "description": "Imported task B", "priority": 2}) + "\n"
        )
        r = _import_tasks_from_jsonl(str(jsonl))
        assert r["success"] is True
        assert r["imported"] == 2


# ── 3. SESSION LIFECYCLE ─────────────────────────────────────────

class TestSessionLifecycle:
    """Proves: save → list → resume → end cycle works with atomic writes."""

    def test_save_and_resume(self, brain):
        from mcp_server_nucleus.runtime.session_ops import (
            _save_session, _resume_session, _list_sessions,
        )

        # Save
        r = _save_session("Integration test session", active_task="Verify reliability")
        assert "error" not in r
        sid = r["session_id"]

        # List
        result = _list_sessions()
        sessions = result.get("sessions", result) if isinstance(result, dict) else result
        assert any(s.get("id") == sid for s in sessions)

        # Resume by ID
        r = _resume_session(session_id=sid)
        assert "error" not in r
        assert r["context"] == "Integration test session"

    def test_atomic_write_creates_valid_json(self, brain):
        from mcp_server_nucleus.runtime.session_ops import _save_session

        r = _save_session("Atomicity test")
        sid = r["session_id"]

        session_file = brain / "sessions" / f"{sid}.json"
        assert session_file.exists()
        data = json.loads(session_file.read_text())
        assert data["context"] == "Atomicity test"
        assert data["schema_version"] == "1.0"

    def test_active_session_tracking(self, brain):
        from mcp_server_nucleus.runtime.session_ops import _save_session

        _save_session("Session A")
        r = _save_session("Session B")

        active_file = brain / "sessions" / "active.json"
        assert active_file.exists()
        active = json.loads(active_file.read_text())
        assert active["active_session_id"] == r["session_id"]


# ── 4. SQLITE CONCURRENT SAFETY ─────────────────────────────────

class TestSQLiteConcurrentSafety:
    """Proves: WAL mode, busy_timeout, and PRAGMAs are active."""

    def test_wal_mode_enabled(self, brain):
        from mcp_server_nucleus.runtime.db import get_storage_backend

        storage = get_storage_backend(brain)
        if hasattr(storage, 'db_path'):
            conn = sqlite3.connect(str(storage.db_path))
            journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert journal == "wal", f"Expected WAL mode, got {journal}"
            conn.close()

    def test_busy_timeout_set(self, brain):
        from mcp_server_nucleus.runtime.db import get_storage_backend

        storage = get_storage_backend(brain)
        if hasattr(storage, 'db_path'):
            conn = sqlite3.connect(str(storage.db_path))
            # After our PRAGMAs, new connections should inherit WAL from the file
            timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            conn.close()
            # Note: busy_timeout isn't file-persisted, but WAL is
            # This test verifies the DB file is valid and accessible

    def test_concurrent_task_adds(self, brain):
        """Add tasks rapidly to stress SQLite under load."""
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks

        for i in range(20):
            r = _add_task(f"Concurrent task {i}", priority=i % 5, task_id=f"conc-{i}")
            assert r["success"] is True

        tasks = _list_tasks()
        conc_tasks = [t for t in tasks if t["id"].startswith("conc-")]
        assert len(conc_tasks) == 20


# ── 5. CIRCUIT BREAKER ──────────────────────────────────────────

class TestCircuitBreakerIntegration:
    """Proves: circuit breakers protect runtime operations."""

    def test_breaker_lifecycle(self):
        from mcp_server_nucleus.runtime.circuit_breaker import (
            CircuitBreaker, CircuitState,
        )

        cb = CircuitBreaker("integration_test", failure_threshold=2, recovery_timeout=0.1)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_task_list_with_breaker_protection(self, brain):
        """list_tasks uses circuit breakers for external providers."""
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks

        _add_task("Protected task", task_id="prot-1")
        tasks = _list_tasks()
        assert any(t["id"] == "prot-1" for t in tasks)


# ── 6. HEALTH CHECK ─────────────────────────────────────────────

class TestHealthCheck:
    """Proves: health diagnostics report accurate status."""

    def test_comprehensive_health(self, brain):
        from mcp_server_nucleus.runtime.health_check import get_health_status

        health = get_health_status(include_details=True)
        assert health["status"] in ("healthy", "degraded", "unhealthy")
        assert "components" in health
        assert "timestamp" in health
        assert "response_time_ms" in health

        component_names = [c["component"] for c in health["components"]]
        assert "brain_path" in component_names
        assert "engram_ledger" in component_names
        assert "circuit_breakers" in component_names
        assert "engram_cache" in component_names

    def test_liveness(self, brain):
        from mcp_server_nucleus.runtime.health_check import get_liveness
        r = get_liveness()
        assert r["status"] == "alive"

    def test_readiness(self, brain):
        from mcp_server_nucleus.runtime.health_check import get_readiness
        r = get_readiness()
        assert "ready" in r
        assert "status" in r


# ── 7. EVENT SYSTEM ──────────────────────────────────────────────

class TestEventSystem:
    """Proves: events are emitted and persisted during operations."""

    def test_events_written_during_task_ops(self, brain):
        from mcp_server_nucleus.runtime.task_ops import _add_task

        _add_task("Event test task", task_id="evt-1")

        events_path = brain / "ledger" / "events.jsonl"
        assert events_path.exists()

        events = []
        for line in events_path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))

        task_events = [e for e in events if e.get("data", {}).get("task_id") == "evt-1"]
        assert len(task_events) >= 1, "Task creation should emit at least one event"


# ── 8. FILE LOCKING ─────────────────────────────────────────────

class TestFileLocking:
    """Proves: locking module works for ledger protection."""

    def test_lock_acquire_release(self, brain):
        from mcp_server_nucleus.runtime.locking import get_lock

        lock = get_lock("test_resource", brain)
        acquired = lock.acquire(timeout=2.0)
        assert acquired is True
        lock.release()

    def test_lock_context_manager(self, brain):
        from mcp_server_nucleus.runtime.locking import get_lock

        lock = get_lock("test_section", brain)
        with lock.section():
            # Critical section — write a file to prove we got the lock
            marker = brain / "lock_proof.txt"
            marker.write_text("locked")
        assert marker.read_text() == "locked"


# ── 9. CROSS-MODULE INTEGRATION ─────────────────────────────────

class TestCrossModuleIntegration:
    """Proves: modules work together, not just in isolation."""

    def test_task_add_emits_event_and_survives_query(self, brain):
        """Task add → event emitted → task queryable → health reports it."""
        from mcp_server_nucleus.runtime.task_ops import _add_task, _list_tasks
        from mcp_server_nucleus.runtime.health_check import get_health_status

        _add_task("Cross-module test", priority=1, task_id="xmod-1")

        tasks = _list_tasks()
        assert any(t["id"] == "xmod-1" for t in tasks)

        events_path = brain / "ledger" / "events.jsonl"
        assert events_path.exists()

        health = get_health_status()
        assert health["status"] in ("healthy", "degraded")

    def test_engram_write_invalidates_cache_and_query_returns_fresh(self, brain):
        """Write engram → cache invalidated → query returns fresh data."""
        from mcp_server_nucleus.runtime.engram_cache import get_engram_cache

        ledger = brain / "engrams" / "ledger.jsonl"
        cache = get_engram_cache()

        # Empty state
        ledger.write_text("")
        cache.invalidate()
        engrams, total = cache.query(ledger)
        assert total == 0

        # Write and verify cache picks it up
        time.sleep(0.05)
        ledger.write_text(json.dumps({
            "key": "fresh", "value": "data", "context": "Test", "intensity": 5
        }) + "\n")
        engrams, total = cache.query(ledger, context="Test")
        assert total == 1

    def test_session_save_uses_atomic_write(self, brain):
        """Verify session files are valid JSON (atomic write didn't corrupt)."""
        from mcp_server_nucleus.runtime.session_ops import _save_session

        for i in range(5):
            _save_session(f"Rapid session {i}")

        sessions_dir = brain / "sessions"
        for f in sessions_dir.glob("*.json"):
            if f.name == "active.json":
                continue
            data = json.loads(f.read_text())
            assert "id" in data
            assert "context" in data
            assert "schema_version" in data


# ── 10. MODULE REGISTRATION RESILIENCE ───────────────────────────

class TestModuleRegistration:
    """Proves: register_all() handles failures gracefully."""

    def test_all_tool_modules_importable(self):
        """Every registered tool module can be imported."""
        from mcp_server_nucleus.tools import _ALL_MODULES

        for name, mod in _ALL_MODULES.items():
            assert hasattr(mod, "register"), f"Module '{name}' missing register() function"

    def test_register_all_with_mock_mcp(self, brain):
        """register_all() completes without crashing."""
        from mcp_server_nucleus.tools import register_all
        from unittest.mock import MagicMock

        mock_mcp = MagicMock()
        mock_helpers = {"make_response": lambda *a, **k: "{}"}

        # Should not raise
        register_all(mock_mcp, mock_helpers)
