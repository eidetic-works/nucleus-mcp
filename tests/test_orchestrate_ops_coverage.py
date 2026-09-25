"""Comprehensive tests for runtime/orchestrate_ops.py."""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.orchestrate_ops import (
    _brain_orchestrate_impl,
    _load_strategy_context,
    _compute_engram_boost,
    _lazy,
)


# ── _lazy ────────────────────────────────────────────────────────

class TestLazy:
    def test_lazy_returns_attribute(self):
        result = _lazy("__version__")
        assert result is not None


# ── _load_strategy_context ───────────────────────────────────────

class TestLoadStrategyContext:
    def test_no_ledger_file(self, tmp_path):
        brain = tmp_path / "brain"
        result = _load_strategy_context(brain)
        assert result == []

    def test_empty_ledger(self, tmp_path):
        brain = tmp_path / "brain"
        engrams_dir = brain / "engrams"
        engrams_dir.mkdir(parents=True)
        ledger_path = engrams_dir / "ledger.jsonl"
        ledger_path.write_text("")
        result = _load_strategy_context(brain)
        assert result == []

    def test_with_strategy_engrams(self, tmp_path):
        brain = tmp_path / "brain"
        engrams_dir = brain / "engrams"
        engrams_dir.mkdir(parents=True)
        ledger_path = engrams_dir / "ledger.jsonl"
        recent_ts = datetime.now(timezone.utc).isoformat()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        entries = [
            {"context": "Strategy", "intensity": 8, "deleted": False, "timestamp": recent_ts, "value": "important strategy"},
            {"context": "Strategy", "intensity": 5, "deleted": False, "timestamp": recent_ts, "value": "low intensity"},
            {"context": "Strategy", "intensity": 9, "deleted": True, "timestamp": recent_ts, "value": "deleted"},
            {"context": "Strategy", "intensity": 7, "deleted": False, "timestamp": old_ts, "value": "old strategy"},
            {"context": "Decision", "intensity": 9, "deleted": False, "timestamp": recent_ts, "value": "not strategy"},
        ]
        with open(ledger_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        result = _load_strategy_context(brain)
        # Only the first entry matches: Strategy, intensity >= 7, not deleted, recent
        assert len(result) == 1
        assert result[0]["value"] == "important strategy"

    def test_corrupt_lines_skipped(self, tmp_path):
        brain = tmp_path / "brain"
        engrams_dir = brain / "engrams"
        engrams_dir.mkdir(parents=True)
        ledger_path = engrams_dir / "ledger.jsonl"
        recent_ts = datetime.now(timezone.utc).isoformat()
        with open(ledger_path, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({"context": "Strategy", "intensity": 8, "deleted": False, "timestamp": recent_ts, "value": "ok"}) + "\n")
        result = _load_strategy_context(brain)
        assert len(result) == 1

    def test_oserror_handled(self, tmp_path):
        brain = tmp_path / "brain"
        engrams_dir = brain / "engrams"
        engrams_dir.mkdir(parents=True)
        ledger_path = engrams_dir / "ledger.jsonl"
        ledger_path.write_text("{}")
        # Make it a directory to trigger OSError
        ledger_path.unlink()
        ledger_path.mkdir()
        result = _load_strategy_context(brain)
        assert result == []


# ── _compute_engram_boost ────────────────────────────────────────

class TestComputeEngramBoost:
    def test_no_engrams(self):
        task = {"description": "test", "id": "t1"}
        boost = _compute_engram_boost(task, [])
        assert boost == 0.0

    def test_no_overlap(self):
        task = {"description": "alpha beta", "id": "t1"}
        engrams = [{"value": "gamma delta", "intensity": 8}]
        boost = _compute_engram_boost(task, engrams)
        assert boost == 0.0

    def test_with_overlap(self):
        task = {"description": "fix auth bug", "id": "task_auth_1"}
        engrams = [{"value": "auth fix needed", "intensity": 8}]
        boost = _compute_engram_boost(task, engrams)
        assert boost > 0.0

    def test_boost_capped_at_3(self):
        task = {"description": "a b c d e", "id": "x"}
        engrams = []
        for i in range(100):
            engrams.append({"value": "a b c d e", "intensity": 10})
        boost = _compute_engram_boost(task, engrams)
        assert boost == 3.0

    def test_overlap_threshold_2(self):
        task = {"description": "one word", "id": "t"}
        engrams = [{"value": "one", "intensity": 10}]
        # Only 1 overlapping word, should be 0
        boost = _compute_engram_boost(task, engrams)
        assert boost == 0.0

    def test_empty_task(self):
        boost = _compute_engram_boost({}, [{"value": "test", "intensity": 8}])
        assert boost == 0.0


# ── _brain_orchestrate_impl ──────────────────────────────────────

class TestBrainOrchestrateImpl:
    @pytest.fixture
    def setup_brain(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        (brain / "ledger").mkdir()
        (brain / "slots").mkdir()
        (brain / "engrams").mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        return brain

    @pytest.fixture
    def mock_lazy_funcs(self, monkeypatch):
        """Mock all lazy-loaded functions."""
        registry = {"slots": {}, "aliases": {}}
        tier_defs = {
            "T1": {"can_run": ["T1", "T2", "T3", "T4"]},
            "T2": {"can_run": ["T2", "T3", "T4"]},
            "standard": {"can_run": ["T1", "T2", "T3", "T4"]},
        }

        def mock_get_slot_registry():
            return registry

        def mock_get_tier_definitions():
            return tier_defs

        def mock_get_tier_for_model(model, defs):
            return "standard"

        def mock_save_slot_registry(reg):
            nonlocal registry
            registry = reg

        def mock_emit_event(event_type, source, data):
            pass

        def mock_resolve_slot_id(slot_id, reg):
            if slot_id in reg.get("slots", {}):
                return slot_id
            if slot_id in reg.get("aliases", {}):
                return reg["aliases"][slot_id]
            return slot_id

        def mock_infer_task_tier(task, defs):
            return "standard"

        def mock_can_slot_run_task(slot_tier, task_tier, defs):
            return True

        def mock_compute_slot_blockers(task, tasks, reg):
            return []

        def mock_claim_task(task_id, agent_id):
            return {"success": True}

        # Patch _lazy to return our mocks
        original_lazy = _lazy

        def patched_lazy(name):
            mapping = {
                "_get_slot_registry": mock_get_slot_registry,
                "_get_tier_definitions": mock_get_tier_definitions,
                "_get_tier_for_model": mock_get_tier_for_model,
                "_save_slot_registry": mock_save_slot_registry,
                "_emit_event": mock_emit_event,
                "_resolve_slot_id": mock_resolve_slot_id,
                "_infer_task_tier": mock_infer_task_tier,
                "_can_slot_run_task": mock_can_slot_run_task,
                "_compute_slot_blockers": mock_compute_slot_blockers,
                "_claim_task": mock_claim_task,
            }
            return mapping.get(name, original_lazy(name))

        monkeypatch.setattr("mcp_server_nucleus.runtime.orchestrate_ops._lazy", patched_lazy)
        return registry

    def test_register_mode_no_model(self, setup_brain, mock_lazy_funcs):
        result = _brain_orchestrate_impl(mode="register")
        data = json.loads(result)
        assert data["action"]["type"] == "ERROR"
        assert "model parameter required" in data["action"]["reason"]

    def test_register_mode_with_model(self, setup_brain, mock_lazy_funcs):
        result = _brain_orchestrate_impl(mode="register", model="claude-opus-4", alias="myalias")
        data = json.loads(result)
        assert data["action"]["type"] == "REGISTERED"
        assert data["slot"] is not None
        assert data["slot"]["model"] == "claude-opus-4"
        assert data["slot"]["alias"] == "myalias"

    def test_register_mode_generates_slot_id(self, setup_brain, mock_lazy_funcs):
        result = _brain_orchestrate_impl(mode="register", model="gpt-4o")
        data = json.loads(result)
        assert data["action"]["type"] == "REGISTERED"
        assert data["slot"]["id"].startswith("slot_")

    def test_no_slot_id(self, setup_brain, mock_lazy_funcs):
        result = _brain_orchestrate_impl(mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "ERROR"
        assert "slot_id required" in data["action"]["reason"]

    def test_slot_not_found(self, setup_brain, mock_lazy_funcs):
        result = _brain_orchestrate_impl(slot_id="nonexistent", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "REGISTER_REQUIRED"

    def test_exhausted_slot(self, setup_brain, mock_lazy_funcs):
        # Register a slot then mark it exhausted
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        mock_lazy_funcs["slots"]["slot1"]["status"] = "exhausted"
        result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "EXHAUSTED"

    def test_report_mode(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        result = _brain_orchestrate_impl(slot_id="slot1", mode="report")
        data = json.loads(result)
        assert data["action"]["type"] == "REPORT"

    def test_wait_mode_no_tasks(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = []
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "WAIT"

    def test_auto_mode_claims_task(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [{"id": "t1", "status": "PENDING", "priority": 1, "description": "test task"}]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "WORK"
        assert data["action"]["task_id"] == "t1"
        assert data["action"]["claimed"] is True

    def test_guided_mode(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [{"id": "t1", "status": "PENDING", "priority": 1, "description": "test task"}]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="guided")
        data = json.loads(result)
        assert data["action"]["type"] == "CHOOSE"
        assert data["action"]["claimed"] is False

    def test_blocked_tasks(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [
            {"id": "t1", "status": "PENDING", "priority": 1, "description": "task1", "blocked_by": ["t2"]},
            {"id": "t2", "status": "IN_PROGRESS", "priority": 1, "description": "task2"},
        ]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "BLOCKED"

    def test_all_blocked(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [
            {"id": "t1", "status": "PENDING", "priority": 1, "description": "task1", "blocked_by": ["t2"]},
            {"id": "t2", "status": "IN_PROGRESS", "priority": 1, "description": "task2"},
        ]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "BLOCKED"
        assert len(data["queue"]["blocked"]) == 1

    def test_claim_failure(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [{"id": "t1", "status": "PENDING", "priority": 1, "description": "test task"}]

        # Build a patched _lazy that uses the fixture's mocks but overrides _claim_task
        from mcp_server_nucleus.runtime.orchestrate_ops import _lazy as real_lazy

        def patched_lazy_fail(name):
            if name == "_claim_task":
                return lambda task_id, agent_id: {"success": False, "error": "already claimed"}
            # Fall back to the fixture's patched _lazy (which is currently active)
            return real_lazy(name)

        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            with patch("mcp_server_nucleus.runtime.orchestrate_ops._lazy", patched_lazy_fail):
                result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "ERROR"
        assert "Claim failed" in data["action"]["reason"]

    def test_handoffs_loaded(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        handoffs_path = setup_brain / "ledger" / "handoffs.json"
        handoffs = [
            {"to_agent": "slot1", "status": "pending", "task_id": "h1"},
            {"to_agent": "slot2", "status": "pending", "task_id": "h2"},
        ]
        handoffs_path.write_text(json.dumps(handoffs))
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = []
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert len(data["handoffs"]["pending_for_me"]) == 1

    def test_protocol_warnings(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [
            {"id": "t1", "status": "IN_PROGRESS", "claimed_by": "slot2", "description": "other task"},
        ]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert len(data["protocol_status"]["warnings"]) > 0

    def test_exception_handling(self, setup_brain, mock_lazy_funcs):
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_brain_path", side_effect=Exception("brain error")):
            result = _brain_orchestrate_impl(mode="auto")
        data = json.loads(result)
        assert data["action"]["type"] == "ERROR"
        assert "brain error" in data["action"]["reason"]

    def test_artery3_disabled(self, setup_brain, mock_lazy_funcs, monkeypatch):
        monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_3", "1")
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [{"id": "t1", "status": "PENDING", "priority": 1, "description": "test"}]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert "strategy_context" not in data

    def test_system_stats(self, setup_brain, mock_lazy_funcs):
        _brain_orchestrate_impl(mode="register", model="gpt-4o", slot_id="slot1")
        tasks = [
            {"id": "t1", "status": "PENDING", "priority": 1, "description": "p"},
            {"id": "t2", "status": "IN_PROGRESS", "claimed_by": "slot1", "description": "ip"},
            {"id": "t3", "status": "DONE", "priority": 1, "description": "d"},
            {"id": "t4", "status": "BLOCKED", "priority": 1, "description": "b"},
        ]
        with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_storage_backend") as mock_backend:
            mock_backend.return_value.list_tasks.return_value = tasks
            result = _brain_orchestrate_impl(slot_id="slot1", mode="auto")
        data = json.loads(result)
        assert data["system"]["total_pending"] == 1
        assert data["system"]["total_in_progress"] == 1
        assert data["system"]["total_done"] == 1
        assert data["system"]["total_blocked"] == 1
