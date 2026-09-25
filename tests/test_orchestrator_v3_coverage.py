"""
Comprehensive coverage tests for runtime/orchestrator_v3.py.

Tests cover all public methods, edge cases, error paths, and dataclass
initialization. External dependencies (AgentPool, TaskIngestionEngine)
are mocked.
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mcp_server_nucleus.runtime import orchestrator_v3 as orch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def brain_path(tmp_path):
    """Create a temporary brain path with required subdirs."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "ledger").mkdir(parents=True, exist_ok=True)
    (bp / "slots").mkdir(parents=True, exist_ok=True)
    return bp


@pytest.fixture
def orchestrator(brain_path, monkeypatch):
    """Create a fresh NucleusOrchestratorV3 instance with temp brain."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
    # Reset singleton
    orch._orchestrator = None
    # Reset lazy-loaded globals
    orch._agent_pool = None
    orch._ingestion_engine = None
    o = orch.NucleusOrchestratorV3(brain_path=brain_path)
    yield o
    orch._orchestrator = None
    orch._agent_pool = None
    orch._ingestion_engine = None


@pytest.fixture
def orchestrator_with_tasks(orchestrator):
    """Orchestrator with a few tasks added."""
    t1 = orchestrator.add_task("Task 1", priority=1, tier="T2_CODE")
    time.sleep(0.002)
    t2 = orchestrator.add_task("Task 2", priority=2, tier="T2_CODE")
    time.sleep(0.002)
    t3 = orchestrator.add_task("Task 3", priority=3, tier="T2_CODE")
    return orchestrator, [t1["task"]["id"], t2["task"]["id"], t3["task"]["id"]]


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_reset_cycle_info_defaults(self):
        rci = orch.ResetCycleInfo()
        assert rci.hours is None
        assert rci.last_reset_at is None
        assert rci.next_reset_at is None
        assert rci.warning_threshold_minutes == 30

    def test_reset_cycle_info_custom(self):
        rci = orch.ResetCycleInfo(hours=5, last_reset_at="2026-01-01", next_reset_at="2026-01-02", warning_threshold_minutes=15)
        assert rci.hours == 5
        assert rci.warning_threshold_minutes == 15

    def test_checkpoint_defaults(self):
        cp = orch.Checkpoint()
        assert cp.enabled is False
        assert cp.last_checkpoint_at is None
        assert cp.data == {}

    def test_checkpoint_custom(self):
        cp = orch.Checkpoint(enabled=True, last_checkpoint_at="now", data={"step": 5})
        assert cp.enabled is True
        assert cp.data == {"step": 5}

    def test_context_summary_defaults(self):
        cs = orch.ContextSummary()
        assert cs.generated_at is None
        assert cs.summary == ""
        assert cs.key_decisions == []
        assert cs.handoff_notes == ""

    def test_context_summary_custom(self):
        cs = orch.ContextSummary(generated_at="now", summary="test", key_decisions=["d1"], handoff_notes="notes")
        assert cs.summary == "test"
        assert cs.key_decisions == ["d1"]


# ---------------------------------------------------------------------------
# Module-level function tests
# ---------------------------------------------------------------------------

class TestModuleFunctions:
    def test_get_brain_path_default(self, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        result = orch.get_brain_path()
        assert result == Path("./.brain")

    def test_get_brain_path_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "custom_brain"))
        result = orch.get_brain_path()
        assert "custom_brain" in str(result)

    def test_get_agent_pool_lazy_load(self, monkeypatch):
        orch._agent_pool = None
        mock_pool = MagicMock()
        with patch("mcp_server_nucleus.runtime.orchestrator_v3.AgentPool", create=True) as mock_cls:
            # Can't directly patch since AgentPool is imported lazily
            pass
        # Patch the import mechanism
        import sys
        mock_module = MagicMock()
        mock_module.AgentPool = MagicMock(return_value=mock_pool)
        with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.agent_pool": mock_module}):
            result = orch._get_agent_pool()
            assert result is mock_pool
        orch._agent_pool = None

    def test_get_agent_pool_import_error(self, monkeypatch):
        """Test that _get_agent_pool returns None when AgentPool can't be imported."""
        orch._agent_pool = None
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if "agent_pool" in name:
                raise ImportError("not available")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = orch._get_agent_pool()
        assert result is None
        orch._agent_pool = None

    def test_get_agent_pool_cached(self, monkeypatch):
        mock_pool = MagicMock()
        orch._agent_pool = mock_pool
        result = orch._get_agent_pool()
        assert result is mock_pool
        orch._agent_pool = None

    def test_get_ingestion_engine_lazy_load(self, monkeypatch):
        orch._ingestion_engine = None
        mock_engine = MagicMock()
        import sys
        mock_module = MagicMock()
        mock_module.TaskIngestionEngine = MagicMock(return_value=mock_engine)
        with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.task_ingestion": mock_module}):
            result = orch._get_ingestion_engine(brain_path=Path("/tmp/test"))
            assert result is mock_engine
        orch._ingestion_engine = None

    def test_get_ingestion_engine_import_error(self, monkeypatch):
        """Test that _get_ingestion_engine returns None when it can't be imported."""
        orch._ingestion_engine = None
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if "task_ingestion" in name:
                raise ImportError("not available")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = orch._get_ingestion_engine()
        assert result is None
        orch._ingestion_engine = None

    def test_get_ingestion_engine_cached(self):
        mock_engine = MagicMock()
        orch._ingestion_engine = mock_engine
        result = orch._get_ingestion_engine()
        assert result is mock_engine
        orch._ingestion_engine = None

    def test_get_orchestrator_singleton(self, brain_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        orch._orchestrator = None
        o1 = orch.get_orchestrator()
        o2 = orch.get_orchestrator()
        assert o1 is o2
        orch._orchestrator = None


# ---------------------------------------------------------------------------
# NucleusOrchestratorV3 - Initialization and legacy JSON
# ---------------------------------------------------------------------------

class TestOrchestratorInit:
    def test_init_default_brain_path(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
        (tmp_path / ".brain" / "ledger").mkdir(parents=True, exist_ok=True)
        orch._orchestrator = None
        o = orch.NucleusOrchestratorV3()
        assert o.brain_path == tmp_path / ".brain"
        assert o.replica_id.startswith("nucleus_")
        assert o.task_store is not None
        assert o.scheduler is not None
        orch._orchestrator = None

    def test_init_custom_brain_path(self, brain_path):
        o = orch.NucleusOrchestratorV3(brain_path=brain_path)
        assert o.brain_path == brain_path

    def test_load_from_legacy_json_no_file(self, orchestrator):
        """No tasks.json exists — should not crash."""
        assert orchestrator.task_store.get_all_tasks() == []

    def test_load_from_legacy_json_with_tasks(self, brain_path, monkeypatch):
        """Load tasks from existing tasks.json."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        tasks_path = brain_path / "ledger" / "tasks.json"
        tasks_data = {
            "tasks": [
                {"id": "legacy_1", "description": "Legacy task", "status": "PENDING",
                 "required_tier": "T2_CODE", "priority": 2, "claimed_by": None,
                 "blocked_by": ["other_task"]},
                {"id": "legacy_2", "title": "Task by title", "status": "DONE",
                 "priority": 1}
            ],
            "metadata": {"version": "3.0"}
        }
        with open(tasks_path, "w") as f:
            json.dump(tasks_data, f)

        orch._orchestrator = None
        o = orch.NucleusOrchestratorV3(brain_path=brain_path)
        tasks = o.get_all_tasks()
        assert len(tasks) == 2
        ids = {t["id"] for t in tasks}
        assert "legacy_1" in ids
        assert "legacy_2" in ids
        orch._orchestrator = None

    def test_load_from_legacy_json_corrupt(self, brain_path, monkeypatch):
        """Corrupt tasks.json — should print warning, not crash."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_path))
        tasks_path = brain_path / "ledger" / "tasks.json"
        tasks_path.write_text("not valid json")

        orch._orchestrator = None
        o = orch.NucleusOrchestratorV3(brain_path=brain_path)
        assert o.get_all_tasks() == []
        orch._orchestrator = None

    def test_save_to_legacy_json(self, orchestrator, brain_path):
        """Test saving tasks to legacy JSON."""
        orchestrator.add_task("Test task", priority=1)
        tasks_path = brain_path / "ledger" / "tasks.json"
        assert tasks_path.exists()
        with open(tasks_path) as f:
            data = json.load(f)
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["description"] == "Test task"
        assert "last_synced" in data.get("metadata", {})

    def test_save_to_legacy_json_preserves_existing(self, orchestrator, brain_path):
        """Test that saving preserves existing metadata."""
        tasks_path = brain_path / "ledger" / "tasks.json"
        existing = {"tasks": [], "metadata": {"version": "3.0", "custom": "data"}}
        with open(tasks_path, "w") as f:
            json.dump(existing, f)

        orchestrator.add_task("New task")
        with open(tasks_path) as f:
            data = json.load(f)
        assert data["metadata"]["version"] == "3.0"
        assert data["metadata"]["custom"] == "data"
        assert len(data["tasks"]) == 1


# ---------------------------------------------------------------------------
# Core Operations
# ---------------------------------------------------------------------------

class TestCoreOperations:
    def test_get_task_existing(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        task = o.get_task(ids[0])
        assert task is not None
        assert task["id"] == ids[0]

    def test_get_task_nonexistent(self, orchestrator):
        result = orchestrator.get_task("nonexistent")
        assert result is None

    def test_get_all_tasks_no_filter(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        tasks = o.get_all_tasks()
        assert len(tasks) == 3

    def test_get_all_tasks_with_filter(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        # All should be PENDING
        tasks = o.get_all_tasks(status="PENDING")
        assert len(tasks) == 3
        # Filter for non-existent status
        tasks = o.get_all_tasks(status="DONE")
        assert len(tasks) == 0

    def test_claim_task_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.claim_task(ids[0], "agent_1")
        assert result["success"] is True
        assert result["task"]["claimed_by"] == "agent_1"
        assert result["task"]["status"] == "IN_PROGRESS"
        assert "claimed_at" in result["task"]

    def test_claim_task_not_found(self, orchestrator):
        result = orchestrator.claim_task("nonexistent", "agent_1")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_claim_task_already_claimed(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        o.claim_task(ids[0], "agent_1")
        result = o.claim_task(ids[0], "agent_2")
        assert result["success"] is False
        assert "already claimed" in result["error"]

    def test_claim_task_same_agent(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        o.claim_task(ids[0], "agent_1")
        result = o.claim_task(ids[0], "agent_1")
        assert result["success"] is True

    def test_complete_task_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.complete_task(ids[0], "agent_1", outcome="success")
        assert result["success"] is True
        assert result["task"]["status"] == "DONE"
        assert "completed_at" in result["task"]
        assert result["task"]["completed_by"] == "agent_1"

    def test_complete_task_failed(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.complete_task(ids[0], "agent_1", outcome="failure")
        assert result["success"] is True
        assert result["task"]["status"] == "FAILED"

    def test_complete_task_not_found(self, orchestrator):
        result = orchestrator.complete_task("nonexistent", "agent_1")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_add_task(self, orchestrator):
        result = orchestrator.add_task("New task", priority=2, tier="T1_VERIFY",
                                        blocked_by=["task_1"], source="api",
                                        required_skills=["python"])
        assert result["success"] is True
        task = result["task"]
        assert task["title"] == "New task"
        assert task["status"] == "PENDING"
        assert task["tier"] == "T1_VERIFY"
        assert task["priority"] == 2
        assert task["blocked_by"] == ["task_1"]
        assert task["source"] == "api"
        assert task["required_skills"] == ["python"]
        assert task["checkpoint"] is None
        assert task["context_summary"] is None
        assert "dependency_metadata" in task

    def test_add_task_defaults(self, orchestrator):
        result = orchestrator.add_task("Simple task")
        assert result["success"] is True
        task = result["task"]
        assert task["priority"] == 3
        assert task["tier"] == "T2_CODE"
        assert task["blocked_by"] == []
        assert task["required_skills"] == []
        assert task["source"] == "user"

    def test_update_task_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.update_task(ids[0], {"priority": 1, "status": "BLOCKED"})
        assert result["success"] is True
        assert result["task"]["priority"] == 1
        assert result["task"]["status"] == "BLOCKED"
        assert "updated_at" in result["task"]

    def test_update_task_protects_id(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        original_id = ids[0]
        result = o.update_task(ids[0], {"id": "hacked_id"})
        assert result["task"]["id"] == original_id

    def test_update_task_not_found(self, orchestrator):
        result = orchestrator.update_task("nonexistent", {"priority": 1})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_get_next_task(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        # Task 1 has priority 1 (highest)
        result = o.get_next_task()
        assert result is not None
        assert result["id"] == ids[0]

    def test_get_next_task_with_blocked(self, orchestrator):
        """Test that blocked tasks are excluded."""
        orchestrator.add_task("Blocked task", priority=1, blocked_by=["nonexistent_done"])
        time.sleep(0.002)
        orchestrator.add_task("Free task", priority=2)
        result = orchestrator.get_next_task()
        assert result is not None
        assert result["title"] == "Free task"

    def test_get_next_task_all_blocked(self, orchestrator):
        """All tasks blocked — should return None."""
        orchestrator.add_task("Blocked 1", priority=1, blocked_by=["task_x"])
        result = orchestrator.get_next_task()
        assert result is None

    def test_get_next_task_no_tasks(self, orchestrator):
        result = orchestrator.get_next_task()
        assert result is None

    def test_get_next_task_with_done_deps(self, orchestrator):
        """Test that tasks with done dependencies are unblocked."""
        t1 = orchestrator.add_task("Done task", priority=2)
        time.sleep(0.002)
        orchestrator.complete_task(t1["task"]["id"], "agent_1")
        orchestrator.add_task("Dependent task", priority=1, blocked_by=[t1["task"]["id"]])
        result = orchestrator.get_next_task()
        assert result is not None
        assert result["title"] == "Dependent task"

    def test_resume_from_checkpoint_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        o.checkpoint_task(ids[0], {"step": 5})
        result = o.resume_from_checkpoint(ids[0])
        assert result["success"] is True
        assert result["task_id"] == ids[0]
        assert "checkpoint" in result
        assert "step 5" in result["resume_instructions"]

    def test_resume_from_checkpoint_no_checkpoint(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.resume_from_checkpoint(ids[0])
        assert result["success"] is False
        assert "No checkpoint" in result["error"]

    def test_resume_from_checkpoint_not_found(self, orchestrator):
        result = orchestrator.resume_from_checkpoint("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_resume_from_checkpoint_no_step(self, orchestrator_with_tasks):
        """Test checkpoint with no step data."""
        o, ids = orchestrator_with_tasks
        o.checkpoint_task(ids[0], {"other": "data"})
        result = o.resume_from_checkpoint(ids[0])
        assert result["success"] is True
        assert "unknown" in result["resume_instructions"]

    def test_escalate_task_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.escalate_task(ids[0], "needs human review")
        assert result["success"] is True
        assert result["task"]["status"] == "ESCALATED"
        assert result["task"]["escalation"]["reason"] == "needs human review"
        assert result["task"]["escalation"]["resolved"] is False

    def test_escalate_task_not_found(self, orchestrator):
        result = orchestrator.escalate_task("nonexistent", "reason")
        assert result["success"] is False
        assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# V3.1 Features
# ---------------------------------------------------------------------------

class TestV31Features:
    def test_checkpoint_task_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.checkpoint_task(ids[0], {"step": 3, "data": "value"})
        assert result["success"] is True
        assert result["checkpoint"]["enabled"] is True
        assert result["checkpoint"]["data"]["step"] == 3
        assert "last_checkpoint_at" in result["checkpoint"]

    def test_checkpoint_task_not_found(self, orchestrator):
        result = orchestrator.checkpoint_task("nonexistent", {"step": 1})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_generate_context_summary_success(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.generate_context_summary(
            ids[0], "Task in progress", key_decisions=["dec1", "dec2"],
            handoff_notes="handoff to agent 2"
        )
        assert result["success"] is True
        cs = result["context_summary"]
        assert cs["summary"] == "Task in progress"
        assert cs["key_decisions"] == ["dec1", "dec2"]
        assert cs["handoff_notes"] == "handoff to agent 2"
        assert "generated_at" in cs

    def test_generate_context_summary_defaults(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        result = o.generate_context_summary(ids[0], "Summary only")
        assert result["success"] is True
        assert result["context_summary"]["key_decisions"] == []
        assert result["context_summary"]["handoff_notes"] == ""

    def test_generate_context_summary_not_found(self, orchestrator):
        result = orchestrator.generate_context_summary("nonexistent", "summary")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_check_reset_warnings_no_registry(self, orchestrator):
        """No registry file — should return empty list."""
        result = orchestrator.check_reset_warnings()
        assert result == []

    def test_check_reset_warnings_with_approaching_reset(self, orchestrator, brain_path):
        """Test warning when reset is approaching."""
        registry_path = brain_path / "slots" / "registry.json"
        soon = (datetime.now() + timedelta(minutes=15)).isoformat()
        registry = {
            "slots": {
                "slot_1": {
                    "reset_cycle": {
                        "next_reset_at": soon,
                        "warning_threshold_minutes": 30
                    }
                }
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        warnings = orchestrator.check_reset_warnings()
        assert len(warnings) == 1
        assert warnings[0]["slot_id"] == "slot_1"
        assert warnings[0]["action"] == "PREPARE_HANDOFF"

    def test_check_reset_warnings_no_reset_cycle(self, orchestrator, brain_path):
        """Slot without reset_cycle — should be skipped."""
        registry_path = brain_path / "slots" / "registry.json"
        registry = {
            "slots": {
                "slot_1": {"reset_cycle": None},
                "slot_2": {"reset_cycle": {}},
                "slot_3": {}
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        warnings = orchestrator.check_reset_warnings()
        assert warnings == []

    def test_check_reset_warnings_far_future(self, orchestrator, brain_path):
        """Reset far in the future — no warning."""
        registry_path = brain_path / "slots" / "registry.json"
        far = (datetime.now() + timedelta(hours=10)).isoformat()
        registry = {
            "slots": {
                "slot_1": {
                    "reset_cycle": {
                        "next_reset_at": far,
                        "warning_threshold_minutes": 30
                    }
                }
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        warnings = orchestrator.check_reset_warnings()
        assert warnings == []

    def test_check_reset_warnings_past_reset(self, orchestrator, brain_path):
        """Reset in the past — no warning (time_remaining <= 0)."""
        registry_path = brain_path / "slots" / "registry.json"
        past = (datetime.now() - timedelta(minutes=10)).isoformat()
        registry = {
            "slots": {
                "slot_1": {
                    "reset_cycle": {
                        "next_reset_at": past,
                        "warning_threshold_minutes": 30
                    }
                }
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        warnings = orchestrator.check_reset_warnings()
        assert warnings == []

    def test_check_reset_warnings_invalid_date(self, orchestrator, brain_path):
        """Invalid date — should be skipped."""
        registry_path = brain_path / "slots" / "registry.json"
        registry = {
            "slots": {
                "slot_1": {
                    "reset_cycle": {
                        "next_reset_at": "not-a-date",
                        "warning_threshold_minutes": 30
                    }
                }
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        warnings = orchestrator.check_reset_warnings()
        assert warnings == []

    def test_record_exhaustion_success(self, orchestrator, brain_path):
        """Test recording exhaustion event."""
        registry_path = brain_path / "slots" / "registry.json"
        registry = {
            "slots": {
                "slot_1": {"model": "claude", "tier": "T2_CODE"}
            }
        }
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        result = orchestrator.record_exhaustion("slot_1", "rate_limit_hit", ["task_1", "task_2"])
        assert result["success"] is True
        assert result["event"]["reason"] == "rate_limit_hit"
        assert result["event"]["tasks_affected"] == ["task_1", "task_2"]
        assert result["event"]["recovery_time_seconds"] == 300

    def test_record_exhaustion_other_reason(self, orchestrator, brain_path):
        """Test recording exhaustion with non-rate-limit reason."""
        registry_path = brain_path / "slots" / "registry.json"
        registry = {"slots": {"slot_1": {"model": "claude"}}}
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        result = orchestrator.record_exhaustion("slot_1", "quota_exceeded")
        assert result["success"] is True
        assert result["event"]["recovery_time_seconds"] == 18000

    def test_record_exhaustion_no_registry(self, orchestrator):
        result = orchestrator.record_exhaustion("slot_1", "rate_limit")
        assert result["success"] is False
        assert "Registry not found" in result["error"]

    def test_record_exhaustion_slot_not_found(self, orchestrator, brain_path):
        registry_path = brain_path / "slots" / "registry.json"
        registry = {"slots": {"slot_1": {"model": "claude"}}}
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        result = orchestrator.record_exhaustion("nonexistent_slot", "rate_limit")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_record_exhaustion_keeps_last_10(self, orchestrator, brain_path):
        """Test that exhaustion history is capped at 10 events."""
        registry_path = brain_path / "slots" / "registry.json"
        registry = {"slots": {"slot_1": {"model": "claude", "exhaustion_history": []}}}
        with open(registry_path, "w") as f:
            json.dump(registry, f)

        for i in range(15):
            orchestrator.record_exhaustion("slot_1", "rate_limit")

        with open(registry_path) as f:
            data = json.load(f)
        assert len(data["slots"]["slot_1"]["exhaustion_history"]) == 10


# ---------------------------------------------------------------------------
# Agent Pool Operations (pool is None)
# ---------------------------------------------------------------------------

class TestAgentPoolOps:
    def test_get_agent_pool(self, orchestrator):
        """Test get_agent_pool returns the lazy-loaded pool."""
        mock_pool = MagicMock()
        orch._agent_pool = mock_pool
        result = orchestrator.get_agent_pool()
        assert result is mock_pool
        orch._agent_pool = None

    def test_spawn_agent_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.spawn_agent("claude-3", "T2_CODE")
        assert result["success"] is False
        assert "not available" in result["error"]

    def test_spawn_agent_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.spawn_agent = MagicMock(return_value={"success": True, "agent_id": "a1"})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.spawn_agent("claude-3", "T2_CODE", alias="myagent")
        assert result["success"] is True
        mock_pool.spawn_agent.assert_called_once_with(model="claude-3", tier="T2_CODE", alias="myagent")

    def test_get_agent_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.get_agent("agent_1")
        assert result is None

    def test_get_agent_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.get_agent = MagicMock(return_value={"id": "agent_1"})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.get_agent("agent_1")
        assert result == {"id": "agent_1"}

    def test_mark_agent_exhausted_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.mark_agent_exhausted("agent_1")
        assert result["success"] is False
        assert "not available" in result["error"]

    def test_mark_agent_exhausted_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.exhaust_agent = MagicMock(return_value={"success": True})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.mark_agent_exhausted("agent_1", reason="quota")
        assert result["success"] is True
        mock_pool.exhaust_agent.assert_called_once_with("agent_1", reason="quota")

    def test_respawn_agent_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.respawn_agent("agent_1")
        assert result["success"] is False

    def test_respawn_agent_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.respawn_agent = MagicMock(return_value={"success": True})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.respawn_agent("agent_1")
        assert result["success"] is True

    def test_get_available_agent_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.get_available_agent(tier="T2_CODE")
        assert result is None

    def test_get_available_agent_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.get_available_agent = MagicMock(return_value="agent_1")
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.get_available_agent(tier="T2_CODE")
        assert result == "agent_1"

    def test_assign_task_to_agent_no_pool(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=None):
            result = orchestrator.assign_task_to_agent("task_1", "agent_1")
        assert result["success"] is False

    def test_assign_task_to_agent_with_pool(self, orchestrator):
        mock_pool = MagicMock()
        mock_pool.assign_task = MagicMock(return_value={"success": True})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.assign_task_to_agent("task_1", "agent_1")
        assert result["success"] is True

    def test_assign_task_to_agent_auto_assign(self, orchestrator):
        """Test auto-assigning with tier but no agent_id."""
        mock_pool = MagicMock()
        mock_pool.get_available_agent = MagicMock(return_value="agent_2")
        mock_pool.assign_task = MagicMock(return_value={"success": True})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.assign_task_to_agent("task_1", agent_id=None, tier="T2_CODE")
        assert result["success"] is True
        mock_pool.get_available_agent.assert_called_once_with(tier="T2_CODE")

    def test_assign_task_to_agent_no_available(self, orchestrator):
        """Test auto-assign when no agent available for tier."""
        mock_pool = MagicMock()
        mock_pool.get_available_agent = MagicMock(return_value=None)
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_agent_pool", return_value=mock_pool):
            result = orchestrator.assign_task_to_agent("task_1", agent_id=None, tier="T4_VISION")
        assert result["success"] is False
        assert "No available agent" in result["error"]


# ---------------------------------------------------------------------------
# Task Ingestion Operations
# ---------------------------------------------------------------------------

class TestTaskIngestion:
    def test_get_ingestion_engine(self, orchestrator):
        mock_engine = MagicMock()
        orch._ingestion_engine = mock_engine
        result = orchestrator.get_ingestion_engine()
        assert result is mock_engine
        orch._ingestion_engine = None

    def test_ingest_tasks_no_engine(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=None):
            result = orchestrator.ingest_tasks("some text")
        assert result["success"] is False
        assert "not available" in result["error"]

    def test_ingest_tasks_from_file(self, orchestrator, tmp_path):
        """Test ingesting from a file path."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"success": True, "count": 5})
        mock_engine.ingest_from_file = MagicMock(return_value=mock_result)

        test_file = tmp_path / "tasks.md"
        test_file.write_text("# Tasks")

        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=mock_engine):
            result = orchestrator.ingest_tasks(
                str(test_file), source_type="markdown", session_id="s1",
                auto_assign=True, skip_dedup=False, dry_run=False
            )
        assert result["success"] is True
        mock_engine.ingest_from_file.assert_called_once()

    def test_ingest_tasks_from_text(self, orchestrator):
        """Test ingesting from text (not a file path)."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"success": True, "count": 3})
        mock_engine.ingest_from_text = MagicMock(return_value=mock_result)

        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=mock_engine):
            result = orchestrator.ingest_tasks(
                "Some task text", source_type="auto", session_id="s1"
            )
        assert result["success"] is True
        mock_engine.ingest_from_text.assert_called_once()
        # Check that source_type "auto" was converted to "manual"
        call_args = mock_engine.ingest_from_text.call_args
        assert call_args.kwargs["source_type"] == "manual"

    def test_ingest_tasks_from_text_explicit_type(self, orchestrator):
        """Test ingesting from text with explicit source_type."""
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"success": True, "count": 1})
        mock_engine.ingest_from_text = MagicMock(return_value=mock_result)

        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=mock_engine):
            result = orchestrator.ingest_tasks("text", source_type="github")
        assert result["success"] is True
        call_args = mock_engine.ingest_from_text.call_args
        assert call_args.kwargs["source_type"] == "github"

    def test_rollback_ingestion_no_engine(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=None):
            result = orchestrator.rollback_ingestion("batch_1")
        assert result["success"] is False
        assert "not available" in result["error"]

    def test_rollback_ingestion_success(self, orchestrator):
        mock_engine = MagicMock()
        mock_engine.rollback = MagicMock(return_value={"success": True})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=mock_engine):
            result = orchestrator.rollback_ingestion("batch_1", reason="test")
        assert result["success"] is True
        mock_engine.rollback.assert_called_once_with("batch_1", "test")

    def test_get_ingestion_stats_no_engine(self, orchestrator):
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=None):
            result = orchestrator.get_ingestion_stats()
        assert "error" in result
        assert "not available" in result["error"]

    def test_get_ingestion_stats_success(self, orchestrator):
        mock_engine = MagicMock()
        mock_engine.get_ingestion_stats = MagicMock(return_value={"total": 10})
        with patch("mcp_server_nucleus.runtime.orchestrator_v3._get_ingestion_engine", return_value=mock_engine):
            result = orchestrator.get_ingestion_stats()
        assert result == {"total": 10}


# ---------------------------------------------------------------------------
# Metrics & Monitoring
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_get_pool_metrics_empty(self, orchestrator):
        metrics = orchestrator.get_pool_metrics()
        assert metrics["total_tasks"] == 0
        assert metrics["pending"] == 0
        assert metrics["in_progress"] == 0
        assert metrics["done"] == 0
        assert metrics["failed"] == 0
        assert metrics["with_checkpoints"] == 0
        assert metrics["with_summaries"] == 0

    def test_get_pool_metrics_with_tasks(self, orchestrator_with_tasks):
        o, ids = orchestrator_with_tasks
        o.claim_task(ids[0], "agent_1")
        o.complete_task(ids[1], "agent_1", outcome="success")
        o.complete_task(ids[2], "agent_1", outcome="failure")
        o.checkpoint_task(ids[0], {"step": 1})
        o.generate_context_summary(ids[0], "summary")

        metrics = o.get_pool_metrics()
        assert metrics["total_tasks"] == 3
        assert metrics["in_progress"] == 1
        assert metrics["done"] == 1
        assert metrics["failed"] == 1
        assert metrics["with_checkpoints"] == 1
        assert metrics["with_summaries"] == 1

    def test_get_pool_metrics_blocked(self, orchestrator):
        orchestrator.add_task("Blocked", priority=1)
        orchestrator.update_task(orchestrator.get_all_tasks()[0]["id"], {"status": "BLOCKED"})
        metrics = orchestrator.get_pool_metrics()
        assert metrics["blocked"] == 1


# ---------------------------------------------------------------------------
# Dependency Graph
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_get_dependency_graph_empty(self, orchestrator):
        graph = orchestrator.get_dependency_graph()
        assert graph["forward_deps"] == {}
        assert graph["reverse_deps"] == {}
        assert graph["depths"] == {}
        assert "computed_at" in graph

    def test_get_dependency_graph_simple(self, orchestrator):
        """Test dependency graph with simple chain."""
        t1 = orchestrator.add_task("Task 1", priority=1)
        t1_id = t1["task"]["id"]
        time.sleep(0.002)
        t2 = orchestrator.add_task("Task 2", priority=2, blocked_by=[t1_id])
        t2_id = t2["task"]["id"]

        graph = orchestrator.get_dependency_graph()
        assert t1_id in graph["forward_deps"]
        assert t2_id in graph["forward_deps"]
        assert graph["forward_deps"][t2_id] == [t1_id]
        assert t2_id in graph["reverse_deps"][t1_id]
        assert graph["depths"][t1_id] == 0
        assert graph["depths"][t2_id] == 1

    def test_get_dependency_graph_cycle(self, orchestrator):
        """Test dependency graph with a cycle."""
        t1 = orchestrator.add_task("Task 1", priority=1, blocked_by=["task_cyclic_2"])
        t1_id = t1["task"]["id"]
        time.sleep(0.002)
        # Create a cycle: t1 depends on t2, t2 depends on t1
        t2 = orchestrator.add_task("Task 2", priority=2, blocked_by=[t1_id])
        t2_id = t2["task"]["id"]
        # Update t1 to depend on t2 (creating a cycle)
        orchestrator.update_task(t1_id, {"blocked_by": [t2_id]})

        graph = orchestrator.get_dependency_graph()
        # Cycle should result in depth -1
        assert graph["depths"][t1_id] == -1 or graph["depths"][t2_id] == -1

    def test_get_dependency_graph_with_depends_on(self, orchestrator):
        """Test that depends_on is also used for dependencies."""
        t1 = orchestrator.add_task("Task 1", priority=1)
        t1_id = t1["task"]["id"]
        time.sleep(0.002)
        t2 = orchestrator.add_task("Task 2", priority=2)
        t2_id = t2["task"]["id"]
        # Add depends_on via update
        orchestrator.update_task(t2_id, {"depends_on": [t1_id]})

        graph = orchestrator.get_dependency_graph()
        assert t1_id in graph["reverse_deps"]
        assert t2_id in graph["reverse_deps"][t1_id]
