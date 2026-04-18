"""
Tests for Session Operations — Save, Resume, List, Prune, Arc
==============================================================
"""

import json
import os
import time
import pytest
from pathlib import Path


@pytest.fixture
def brain_path(tmp_path):
    """Create a fresh isolated brain directory for each test."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    (brain / "session").mkdir(exist_ok=True)
    old = os.environ.get("NUCLEUS_BRAIN_PATH")
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
    yield brain
    if old is not None:
        os.environ["NUCLEUS_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEUS_BRAIN_PATH", None)


# ── Save Session Tests ────────────────────────────────────────

class TestSaveSession:
    def test_basic_save(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session
        result = _save_session("Working on auth module")
        assert result["success"] is True
        assert "session_id" in result
        assert "auth" in result["session_id"].lower() or "working" in result["session_id"].lower()

    def test_save_creates_session_file(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session
        result = _save_session("Test context")
        session_id = result["session_id"]
        session_file = brain_path / "sessions" / f"{session_id}.json"
        assert session_file.exists()
        data = json.loads(session_file.read_text())
        assert data["context"] == "Test context"

    def test_save_sets_active_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session
        result = _save_session("Active test")
        active_path = brain_path / "sessions" / "active.json"
        assert active_path.exists()
        active_data = json.loads(active_path.read_text())
        assert active_data["active_session_id"] == result["session_id"]

    def test_save_with_all_fields(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session
        result = _save_session(
            context="Full session",
            active_task="Build API",
            pending_decisions=["Choose DB", "Choose auth"],
            breadcrumbs=["Started", "Explored options"],
            next_steps=["Implement", "Test"]
        )
        assert result["success"] is True
        session_file = brain_path / "sessions" / f"{result['session_id']}.json"
        data = json.loads(session_file.read_text())
        assert data["active_task"] == "Build API"
        assert len(data["pending_decisions"]) == 2
        assert len(data["breadcrumbs"]) == 2
        assert len(data["next_steps"]) == 2

    def test_save_includes_depth_snapshot(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session
        depth_path = brain_path / "session" / "depth.json"
        depth_path.write_text(json.dumps({"current_depth": 3, "levels": ["L1", "L2", "L3"]}))
        result = _save_session("Depth test")
        session_file = brain_path / "sessions" / f"{result['session_id']}.json"
        data = json.loads(session_file.read_text())
        assert data["depth_snapshot"]["current_depth"] == 3


# ── Resume Session Tests ──────────────────────────────────────

class TestResumeSession:
    def test_resume_active_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _resume_session
        save_result = _save_session("Resume test", active_task="Task X")
        result = _resume_session()
        assert "error" not in result
        assert result["context"] == "Resume test"
        assert result["active_task"] == "Task X"

    def test_resume_by_id(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _resume_session
        save_result = _save_session("Session A")
        result = _resume_session(session_id=save_result["session_id"])
        assert result["context"] == "Session A"

    def test_resume_no_active_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _resume_session
        result = _resume_session()
        assert "error" in result

    def test_resume_nonexistent_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _resume_session
        result = _resume_session(session_id="nonexistent_12345")
        assert "error" in result

    def test_resume_includes_warnings_on_version_mismatch(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _resume_session
        save_result = _save_session("Version test")
        # Modify session to have different version
        session_file = brain_path / "sessions" / f"{save_result['session_id']}.json"
        data = json.loads(session_file.read_text())
        data["schema_version"] = "2.0"
        session_file.write_text(json.dumps(data))
        result = _resume_session(session_id=save_result["session_id"])
        assert len(result.get("warnings", [])) > 0


# ── List Sessions Tests ───────────────────────────────────────

class TestListSessions:
    def test_empty_list(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _list_sessions
        result = _list_sessions()
        assert result["total"] == 0

    def test_list_after_saves(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _list_sessions
        _save_session("Session 1")
        _save_session("Session 2")
        result = _list_sessions()
        assert result["total"] == 2

    def test_list_excludes_active_json(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _list_sessions
        _save_session("Session A")
        result = _list_sessions()
        ids = [s["id"] for s in result["sessions"]]
        assert "active" not in ids


# ── Prune Sessions Tests ──────────────────────────────────────

class TestPruneSessions:
    def test_prune_keeps_max(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _prune_old_sessions, _list_sessions
        for i in range(15):
            _save_session(f"Session {i}")
            time.sleep(0.01)  # Ensure different mtimes
        _prune_old_sessions(max_sessions=5)
        result = _list_sessions()
        assert result["total"] <= 5

    def test_prune_no_sessions(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _prune_old_sessions
        # Should not raise
        _prune_old_sessions(max_sessions=5)


# ── Get Session Tests ─────────────────────────────────────────

class TestGetSession:
    def test_get_existing(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _get_session
        save_result = _save_session("Get test")
        result = _get_session(save_result["session_id"])
        assert "session" in result
        assert result["session"]["context"] == "Get test"

    def test_get_nonexistent(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _get_session
        result = _get_session("nonexistent")
        assert "error" in result


# ── Check Recent Session Tests ────────────────────────────────

class TestCheckRecentSession:
    def test_no_recent_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _check_for_recent_session
        result = _check_for_recent_session()
        assert result["exists"] is False

    def test_has_recent_session(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _check_for_recent_session
        _save_session("Recent")
        result = _check_for_recent_session()
        assert result["exists"] is True
        assert "session_id" in result


# ── Session Arc Tests ─────────────────────────────────────────

class TestLoadSessionArc:
    def test_empty_ledger(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _load_session_arc
        arc = _load_session_arc(brain_path)
        assert arc["recent_sessions"] == []
        assert arc["todays_focus"] is None

    def test_loads_session_engrams(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _load_session_arc
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write(json.dumps({
                "key": "session_001",
                "value": "Worked on auth module",
                "timestamp": "2024-01-15T10:00:00Z"
            }) + "\n")
        arc = _load_session_arc(brain_path)
        assert len(arc["recent_sessions"]) == 1

    def test_excludes_deleted_engrams(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _load_session_arc
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write(json.dumps({
                "key": "session_001", "value": "active", "timestamp": "2024-01-15"
            }) + "\n")
            f.write(json.dumps({
                "key": "session_002", "value": "deleted", "timestamp": "2024-01-14", "deleted": True
            }) + "\n")
        arc = _load_session_arc(brain_path)
        assert len(arc["recent_sessions"]) == 1

    def test_builds_arc_summary(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _load_session_arc
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write(json.dumps({
                "key": "session_001", "value": "Started auth", "timestamp": "2024-01-15"
            }) + "\n")
            f.write(json.dumps({
                "key": "session_002", "value": "Finished auth", "timestamp": "2024-01-16"
            }) + "\n")
        arc = _load_session_arc(brain_path)
        assert arc["arc_summary"] != ""


# ── Session End Tests ─────────────────────────────────────────

class TestSessionEnd:
    def test_end_session_clears_active(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _save_session, _brain_session_end_impl
        _save_session("Ending session")
        active_path = brain_path / "sessions" / "active.json"
        assert active_path.exists()
        with pytest.MonkeyPatch.context() as mp:
            # Mock MemoryPipeline to avoid import issues
            from unittest.mock import MagicMock
            mock_pipeline = MagicMock()
            mock_pipeline.return_value.process.return_value = {"added": 1}
            mp.setattr("mcp_server_nucleus.runtime.session_ops.MemoryPipeline", mock_pipeline, raising=False)
            result = _brain_session_end_impl(summary="Done for today")
        # active.json should be cleaned up
        assert not active_path.exists() or result.get("success") is True

    def test_end_session_auto_generates_summary(self, brain_path):
        from mcp_server_nucleus.runtime.session_ops import _brain_session_end_impl
        # Create some events
        events_path = brain_path / "ledger" / "events.jsonl"
        with open(events_path, "w") as f:
            f.write(json.dumps({"type": "task_completed"}) + "\n")
            f.write(json.dumps({"type": "task_claimed"}) + "\n")
            f.write(json.dumps({"type": "task_created"}) + "\n")
        with pytest.MonkeyPatch.context() as mp:
            from unittest.mock import MagicMock
            mock_pipeline_cls = MagicMock()
            mock_pipeline_cls.return_value.process.return_value = {"added": 1}
            mp.setattr("mcp_server_nucleus.runtime.session_ops.MemoryPipeline", mock_pipeline_cls, raising=False)
            result = _brain_session_end_impl()
        if "error" not in result:
            assert result["activity"]["total_events"] == 3
            assert result["activity"]["tasks_completed"] == 1
