"""Comprehensive tests for morning_brief_ops module."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import morning_brief_ops
from mcp_server_nucleus.runtime.morning_brief_ops import (
    _find_engram_by_key,
    _check_recommendation_followed,
    _retrieve_top_engrams,
    _retrieve_tasks,
    _retrieve_yesterday,
    _retrieve_hook_health,
    _retrieve_adhd_status,
    _retrieve_growth_status,
    _retrieve_frontier_health,
    _generate_recommendation,
    _format_brief,
    _morning_brief_impl,
)


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a temporary brain path with required subdirs."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "engrams").mkdir(exist_ok=True)
    (bp / "ledger").mkdir(exist_ok=True)
    (bp / "driver").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


def write_engrams(brain: Path, engrams: list):
    """Write engrams to ledger.jsonl."""
    ledger = brain / "engrams" / "ledger.jsonl"
    with open(ledger, "w") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")


def write_tasks(brain: Path, tasks: list):
    """Write tasks to tasks.jsonl."""
    path = brain / "ledger" / "tasks.jsonl"
    with open(path, "w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")


def write_events(brain: Path, events: list):
    """Write events to events.jsonl."""
    path = brain / "ledger" / "events.jsonl"
    with open(path, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


# ── _find_engram_by_key ──────────────────────────────────────────

class TestFindEngramByKey:
    def test_no_ledger(self, brain_path):
        assert _find_engram_by_key(brain_path, "key1") is None

    def test_found(self, brain_path):
        write_engrams(brain_path, [
            {"key": "key1", "value": "val1"},
            {"key": "key2", "value": "val2"},
        ])
        result = _find_engram_by_key(brain_path, "key1")
        assert result is not None
        assert result["key"] == "key1"

    def test_deleted_skipped(self, brain_path):
        write_engrams(brain_path, [
            {"key": "key1", "value": "val1", "deleted": True},
            {"key": "key1", "value": "val2"},
        ])
        result = _find_engram_by_key(brain_path, "key1")
        assert result["value"] == "val2"

    def test_not_found(self, brain_path):
        write_engrams(brain_path, [{"key": "key1", "value": "val1"}])
        assert _find_engram_by_key(brain_path, "nonexistent") is None

    def test_corrupt_line_skipped(self, brain_path):
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write('{"key": "key1", "value": "val1"}\n')
            f.write('corrupt json line\n')
            f.write('{"key": "key2", "value": "val2"}\n')
        result = _find_engram_by_key(brain_path, "key2")
        assert result is not None

    def test_os_error_returns_none(self, brain_path):
        ledger = brain_path / "engrams" / "ledger.jsonl"
        ledger.write_text('{"key": "key1"}')
        # Make it a directory to cause OSError
        ledger.unlink()
        ledger.mkdir()
        result = _find_engram_by_key(brain_path, "key1")
        assert result is None


# ── _check_recommendation_followed ───────────────────────────────

class TestCheckRecommendationFollowed:
    def test_no_task_ref(self):
        result = _check_recommendation_followed({"value": "no bracket"}, {}, [])
        assert result is False

    def test_short_ref(self):
        result = _check_recommendation_followed({"value": "[START] do"}, {}, [])
        assert result is False

    def test_followed_via_event(self):
        rec = {"value": "[CONTINUE] implement feature auth"}
        events = [{"event": "task_completed", "detail": {"description": "implement the auth feature"}}]
        result = _check_recommendation_followed(rec, {}, events)
        assert result is True

    def test_followed_via_in_progress_task(self):
        rec = {"value": "[CONTINUE] implement feature auth"}
        tasks = {"in_progress": [{"description": "implement the auth feature"}]}
        result = _check_recommendation_followed(rec, tasks, [])
        assert result is True

    def test_not_followed(self):
        rec = {"value": "[START] implement feature auth"}
        tasks = {"in_progress": [{"description": "unrelated work"}]}
        result = _check_recommendation_followed(rec, tasks, [])
        assert result is False

    def test_followed_via_pending_not_counted(self):
        rec = {"value": "[START] implement feature auth"}
        tasks = {"pending": [{"description": "implement the auth feature"}]}
        result = _check_recommendation_followed(rec, tasks, [])
        assert result is False

    def test_event_type_variants(self):
        rec = {"value": "[CONTINUE] implement feature auth"}
        for evt_type in ("task_completed", "task_claimed", "slot_task_completed",
                         "task_completed_with_fence", "task_state_changed"):
            events = [{"event": evt_type, "detail": {"description": "implement the auth feature"}}]
            assert _check_recommendation_followed(rec, {}, events) is True

    def test_event_with_type_key(self):
        rec = {"value": "[CONTINUE] implement feature auth"}
        events = [{"type": "task_completed", "data": {"description": "implement the auth feature"}}]
        assert _check_recommendation_followed(rec, {}, events) is True

    def test_empty_events_and_tasks(self):
        rec = {"value": "[START] implement feature auth"}
        assert _check_recommendation_followed(rec, {}, []) is False


# ── _retrieve_top_engrams ────────────────────────────────────────

class TestRetrieveTopEngrams:
    def test_no_ledger(self, brain_path):
        result = _retrieve_top_engrams(brain_path)
        assert result["engrams"] == []
        assert result["count"] == 0
        assert "No engrams" in result["message"]

    def test_with_engrams(self, brain_path):
        write_engrams(brain_path, [
            {"key": "k1", "value": "v1", "context": "C1", "intensity": 8},
            {"key": "k2", "value": "v2", "context": "C2", "intensity": 3},
        ])
        result = _retrieve_top_engrams(brain_path)
        assert result["count"] == 2
        assert result["showing"] == 2
        # Higher intensity should be first
        assert result["engrams"][0]["key"] == "k1"

    def test_deleted_excluded(self, brain_path):
        write_engrams(brain_path, [
            {"key": "k1", "value": "v1", "intensity": 8, "deleted": True},
            {"key": "k2", "value": "v2", "intensity": 3},
        ])
        result = _retrieve_top_engrams(brain_path)
        assert result["count"] == 1
        assert result["engrams"][0]["key"] == "k2"

    def test_quarantined_excluded(self, brain_path):
        write_engrams(brain_path, [
            {"key": "k1", "value": "v1", "intensity": 8, "quarantined": True},
            {"key": "k2", "value": "v2", "intensity": 3},
        ])
        result = _retrieve_top_engrams(brain_path)
        assert result["count"] == 1

    def test_recency_bonus(self, brain_path):
        now = datetime.now().isoformat()
        old = (datetime.now() - timedelta(days=60)).isoformat()
        write_engrams(brain_path, [
            {"key": "old", "value": "v", "intensity": 5, "timestamp": old},
            {"key": "new", "value": "v", "intensity": 5, "timestamp": now},
        ])
        result = _retrieve_top_engrams(brain_path)
        # Recent should score higher (5*2 + 2 = 12 vs 5*2 + 0 = 10)
        assert result["engrams"][0]["key"] == "new"

    def test_limit(self, brain_path):
        engrams = [{"key": f"k{i}", "value": f"v{i}", "intensity": i} for i in range(15)]
        write_engrams(brain_path, engrams)
        result = _retrieve_top_engrams(brain_path, limit=5)
        assert result["showing"] == 5
        assert result["count"] == 15

    def test_corrupt_line_skipped(self, brain_path):
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write('{"key": "k1", "value": "v1", "intensity": 8}\n')
            f.write('corrupt\n')
        result = _retrieve_top_engrams(brain_path)
        assert result["count"] == 1

    def test_value_truncated(self, brain_path):
        long_val = "x" * 300
        write_engrams(brain_path, [{"key": "k1", "value": long_val, "intensity": 5}])
        result = _retrieve_top_engrams(brain_path)
        assert len(result["engrams"][0]["value"]) <= 200

    def test_invalid_timestamp(self, brain_path):
        write_engrams(brain_path, [
            {"key": "k1", "value": "v1", "intensity": 5, "timestamp": "invalid"},
        ])
        result = _retrieve_top_engrams(brain_path)
        assert result["count"] == 1


# ── _retrieve_tasks ──────────────────────────────────────────────

class TestRetrieveTasks:
    def test_no_tasks_file(self, brain_path):
        result = _retrieve_tasks(brain_path)
        assert result["pending"] == []
        assert result["in_progress"] == []
        assert result["count"] == 0

    def test_with_tasks(self, brain_path):
        write_tasks(brain_path, [
            {"id": "t1", "description": "Task 1", "priority": 5, "status": "pending"},
            {"id": "t2", "description": "Task 2", "priority": 8, "status": "in_progress"},
        ])
        result = _retrieve_tasks(brain_path)
        assert result["total_tasks"] == 2
        assert len(result["pending"]) == 1
        assert len(result["in_progress"]) == 1

    def test_status_variants(self, brain_path):
        write_tasks(brain_path, [
            {"id": "t1", "description": "Task 1", "status": "open"},
            {"id": "t2", "description": "Task 2", "status": "todo"},
            {"id": "t3", "description": "Task 3", "status": "claimed"},
            {"id": "t4", "description": "Task 4", "status": "active"},
        ])
        result = _retrieve_tasks(brain_path)
        assert len(result["pending"]) == 2
        assert len(result["in_progress"]) == 2

    def test_sorted_by_priority(self, brain_path):
        write_tasks(brain_path, [
            {"id": "t1", "description": "Low", "priority": 1, "status": "pending"},
            {"id": "t2", "description": "High", "priority": 10, "status": "pending"},
        ])
        result = _retrieve_tasks(brain_path)
        assert result["pending"][0]["id"] == "t2"

    def test_limited_to_5(self, brain_path):
        tasks = [{"id": f"t{i}", "description": f"Task {i}", "priority": i, "status": "pending"} for i in range(10)]
        write_tasks(brain_path, tasks)
        result = _retrieve_tasks(brain_path)
        assert len(result["pending"]) == 5

    def test_corrupt_line_skipped(self, brain_path):
        path = brain_path / "ledger" / "tasks.jsonl"
        with open(path, "w") as f:
            f.write('{"id": "t1", "description": "Task 1", "status": "pending"}\n')
            f.write('corrupt\n')
        result = _retrieve_tasks(brain_path)
        assert result["total_tasks"] == 1

    def test_task_id_fallback(self, brain_path):
        write_tasks(brain_path, [
            {"task_id": "t1", "description": "Task 1", "status": "pending"},
        ])
        result = _retrieve_tasks(brain_path)
        assert result["pending"][0]["id"] == "t1"

    def test_description_truncated(self, brain_path):
        write_tasks(brain_path, [
            {"id": "t1", "description": "x" * 200, "status": "pending"},
        ])
        result = _retrieve_tasks(brain_path)
        assert len(result["pending"][0]["description"]) <= 150


# ── _retrieve_yesterday ──────────────────────────────────────────

class TestRetrieveYesterday:
    def test_no_events_file(self, brain_path):
        result = _retrieve_yesterday(brain_path)
        assert result["events"] == []
        assert result["count"] == 0

    def test_with_recent_events(self, brain_path):
        now = datetime.now().isoformat()
        write_events(brain_path, [
            {"event_type": "test_event", "emitter": "test", "timestamp": now, "data": {"k": "v"}},
        ])
        result = _retrieve_yesterday(brain_path)
        assert result["count"] == 1
        assert result["events"][0]["event"] == "test_event"

    def test_old_events_excluded(self, brain_path):
        old = (datetime.now() - timedelta(hours=48)).isoformat()
        write_events(brain_path, [
            {"event_type": "old_event", "emitter": "test", "timestamp": old},
        ])
        result = _retrieve_yesterday(brain_path)
        assert result["count"] == 0

    def test_limited_to_15(self, brain_path):
        now = datetime.now().isoformat()
        events = [{"event_type": f"ev{i}", "emitter": "test", "timestamp": now} for i in range(20)]
        write_events(brain_path, events)
        result = _retrieve_yesterday(brain_path)
        assert len(result["events"]) == 15

    def test_corrupt_line_skipped(self, brain_path):
        path = brain_path / "ledger" / "events.jsonl"
        now = datetime.now().isoformat()
        with open(path, "w") as f:
            f.write(json.dumps({"event_type": "ev1", "emitter": "test", "timestamp": now}) + "\n")
            f.write('corrupt\n')
        result = _retrieve_yesterday(brain_path)
        assert result["count"] == 1

    def test_invalid_timestamp_skipped(self, brain_path):
        write_events(brain_path, [
            {"event_type": "ev1", "emitter": "test", "timestamp": "invalid"},
        ])
        result = _retrieve_yesterday(brain_path)
        assert result["count"] == 0

    def test_event_key_fallback(self, brain_path):
        now = datetime.now().isoformat()
        write_events(brain_path, [
            {"event": "ev1", "emitter": "test", "timestamp": now, "metadata": "some data"},
        ])
        result = _retrieve_yesterday(brain_path)
        assert result["events"][0]["event"] == "ev1"

    def test_detail_truncated(self, brain_path):
        now = datetime.now().isoformat()
        long_data = "x" * 200
        write_events(brain_path, [
            {"event_type": "ev1", "emitter": "test", "timestamp": now, "data": long_data},
        ])
        result = _retrieve_yesterday(brain_path)
        assert len(result["events"][0]["detail"]) <= 100

    def test_reversed_order(self, brain_path):
        now = datetime.now().isoformat()
        write_events(brain_path, [
            {"event_type": "first", "emitter": "test", "timestamp": now},
            {"event_type": "second", "emitter": "test", "timestamp": now},
        ])
        result = _retrieve_yesterday(brain_path)
        # Most recent first (reversed)
        assert result["events"][0]["event"] == "second"


# ── _retrieve_hook_health ────────────────────────────────────────

class TestRetrieveHookHealth:
    def test_exception_returns_default(self, brain_path):
        result = _retrieve_hook_health(brain_path)
        assert "total_executions" in result
        assert result["total_executions"] == 0

    def test_with_mock(self, brain_path):
        with patch("mcp_server_nucleus.runtime.engram_hooks.get_hook_metrics_summary",
                   return_value={"total_executions": 5}):
            result = _retrieve_hook_health(brain_path)
            assert result["total_executions"] == 5


# ── _retrieve_adhd_status ────────────────────────────────────────

class TestRetrieveAdhdStatus:
    def test_exception_returns_default(self):
        result = _retrieve_adhd_status()
        assert "focus_status" in result
        assert result["switch_count"] == 0

    def test_with_mock(self):
        with patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status",
                   return_value={"status": "🟡 CAUTION", "switch_count": 3, "max_switches": 5, "recommendation": "Slow down"}):
            with patch("mcp_server_nucleus.runtime.depth_ops._depth_show",
                       return_value={"current_depth": 2, "max_safe_depth": 5, "status": "🟢 SAFE"}):
                result = _retrieve_adhd_status()
                assert result["focus_status"] == "🟡 CAUTION"
                assert result["switch_count"] == 3
                assert result["depth"] == 2


# ── _retrieve_growth_status ──────────────────────────────────────

class TestRetrieveGrowthStatus:
    def test_no_ledger(self, brain_path):
        result = _retrieve_growth_status(brain_path)
        assert "No growth data" in result["message"]

    def test_no_growth_engrams(self, brain_path):
        write_engrams(brain_path, [{"key": "other_key", "value": "val"}])
        result = _retrieve_growth_status(brain_path)
        assert "No growth metrics" in result["message"]

    def test_with_growth_engram(self, brain_path):
        write_engrams(brain_path, [
            {"key": "growth_metrics_20240101", "value": "stars=50 forks=10"},
        ])
        result = _retrieve_growth_status(brain_path)
        assert result["latest_date"] == "20240101"
        assert "stars=50" in result["value"]

    def test_corrupt_line_skipped(self, brain_path):
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write('corrupt\n')
            f.write('{"key": "growth_metrics_20240101", "value": "stars=50"}\n')
        result = _retrieve_growth_status(brain_path)
        assert result["latest_date"] == "20240101"


# ── _retrieve_frontier_health ────────────────────────────────────

class TestRetrieveFrontierHealth:
    def test_empty_brain(self, brain_path):
        result = _retrieve_frontier_health(brain_path)
        assert "message" in result
        assert "No frontier data" in result["message"]

    def test_with_verification_log(self, brain_path):
        vlog = brain_path / "verification_log.jsonl"
        with open(vlog, "w") as f:
            f.write(json.dumps({"tiers_failed": None}) + "\n")
            f.write(json.dumps({"tiers_failed": ["T1"]}) + "\n")
        result = _retrieve_frontier_health(brain_path)
        assert "ground" in result
        assert result["ground"]["total"] == 2
        assert result["ground"]["pass_rate"] == 50.0

    def test_with_verdicts(self, brain_path):
        vpath = brain_path / "driver" / "human_verdicts.jsonl"
        with open(vpath, "w") as f:
            f.write(json.dumps({"verdict": "approved"}) + "\n")
            f.write(json.dumps({"verdict": "pending"}) + "\n")
        result = _retrieve_frontier_health(brain_path)
        assert "align" in result
        assert result["align"]["total_reviews"] == 1
        assert result["align"]["pending"] == 1


# ── _generate_recommendation ─────────────────────────────────────

class TestGenerateRecommendation:
    def test_continue_in_progress(self):
        sections = {
            "tasks": {"in_progress": [{"id": "t1", "description": "Active task", "priority": 8}]},
            "memory": {"engrams": [{"value": "context"}]},
            "yesterday": {"events": []},
        }
        rec = _generate_recommendation(sections)
        assert rec["action"] == "CONTINUE"
        assert rec["task"] == "Active task"
        assert rec["task_id"] == "t1"
        assert rec["context_reminder"] == "context"

    def test_start_pending(self):
        sections = {
            "tasks": {"in_progress": [], "pending": [{"id": "t1", "description": "Pending task", "priority": 5}]},
            "memory": {"engrams": [{"value": "context"}]},
            "yesterday": {"events": []},
        }
        rec = _generate_recommendation(sections)
        assert rec["action"] == "START"
        assert rec["task"] == "Pending task"

    def test_reflect_with_events(self):
        sections = {
            "tasks": {"in_progress": [], "pending": []},
            "memory": {"engrams": [{"value": "context"}]},
            "yesterday": {"events": [{"event": "test", "emitter": "e"}]},
        }
        rec = _generate_recommendation(sections)
        assert rec["action"] == "REFLECT"

    def test_bootstrap_empty(self):
        sections = {
            "tasks": {},
            "memory": {},
            "yesterday": {},
        }
        rec = _generate_recommendation(sections)
        assert rec["action"] == "BOOTSTRAP"
        assert rec["context_reminder"] is None

    def test_continue_no_engrams(self):
        sections = {
            "tasks": {"in_progress": [{"id": "t1", "description": "Active", "priority": 5}]},
            "memory": {"engrams": []},
            "yesterday": {"events": []},
        }
        rec = _generate_recommendation(sections)
        assert rec["context_reminder"] is None

    def test_start_no_engrams(self):
        sections = {
            "tasks": {"in_progress": [], "pending": [{"id": "t1", "description": "P", "priority": 5}]},
            "memory": {"engrams": []},
            "yesterday": {"events": []},
        }
        rec = _generate_recommendation(sections)
        assert rec["context_reminder"] is None

    def test_reflect_no_engrams(self):
        sections = {
            "tasks": {"in_progress": [], "pending": []},
            "memory": {"engrams": []},
            "yesterday": {"events": [{"event": "e"}]},
        }
        rec = _generate_recommendation(sections)
        assert rec["context_reminder"] is None


# ── _format_brief ────────────────────────────────────────────────

class TestFormatBrief:
    def test_minimal_brief(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
            },
            "recommendation": {"action": "BOOTSTRAP", "task": "Start", "reason": "Begin", "context_reminder": None},
            "meta": {"generation_time_ms": 10.0},
        }
        result = _format_brief(brief)
        assert "NUCLEUS MORNING BRIEF" in result
        assert "TODAY YOU SHOULD" in result
        assert "BOOTSTRAP" in result

    def test_with_engrams(self):
        brief = {
            "sections": {
                "memory": {"engrams": [{"key": "k1", "value": "v1", "intensity": 7}], "showing": 1, "count": 1},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "k1" in result

    def test_with_tasks(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {
                    "in_progress": [{"id": "t1", "description": "Active", "priority": 8}],
                    "pending": [{"id": "t2", "description": "Pending", "priority": 3}],
                },
                "yesterday": {"events": [], "count": 0},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "Active" in result
        assert "Pending" in result

    def test_with_events(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [{"event": "ev1", "emitter": "test"}], "count": 1},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "ev1" in result

    def test_with_hook_health(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
                "hook_health": {"total_executions": 10, "outcomes": {"ADD": 5, "NOOP": 3, "ERROR": 2},
                               "efficiency": 0.5, "error_rate": 0.2, "avg_latency_ms": 15.0},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "HOOK HEALTH" in result

    def test_with_adhd_status(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
                "adhd_status": {"switch_count": 3, "depth": 2, "focus_status": "🟡 CAUTION",
                               "depth_status": "🟢 SAFE", "max_switches": 5, "max_depth": 5,
                               "recommendation": "Slow down"},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "ADHD GUARDRAIL" in result

    def test_with_training(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
                "training": {"total_turns": 100, "new_turns": 10, "should_retrain": True, "reason": "enough data"},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "THIRD BROTHER" in result
        assert "RETRAIN" in result

    def test_with_relay(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
                "relay": {"has_messages": True, "total_unread": 3, "summary": "You have messages", "urgent_count": 1},
            },
            "recommendation": None,
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "RELAY INBOX" in result

    def test_with_recommendation_and_context(self):
        brief = {
            "sections": {
                "memory": {"engrams": [], "showing": 0, "count": 0},
                "tasks": {"in_progress": [], "pending": []},
                "yesterday": {"events": [], "count": 0},
            },
            "recommendation": {"action": "START", "task": "Do something", "reason": "Because",
                              "context_reminder": "Remember this"},
            "meta": {"generation_time_ms": 5.0},
        }
        result = _format_brief(brief)
        assert "START" in result
        assert "Do something" in result
        assert "Remember this" in result


# ── _morning_brief_impl ──────────────────────────────────────────

class TestMorningBriefImpl:
    def test_empty_brain(self, brain_path):
        result = _morning_brief_impl()
        assert "sections" in result
        assert "recommendation" in result
        assert "meta" in result
        assert "formatted" in result
        assert result["meta"]["generation_time_ms"] >= 0

    def test_with_data(self, brain_path):
        write_engrams(brain_path, [{"key": "k1", "value": "v1", "intensity": 8}])
        write_tasks(brain_path, [{"id": "t1", "description": "Task 1", "priority": 5, "status": "pending"}])
        write_events(brain_path, [{"event_type": "ev1", "emitter": "test", "timestamp": datetime.now().isoformat()}])
        result = _morning_brief_impl()
        assert result["sections"]["memory"]["count"] == 1
        assert result["sections"]["tasks"]["total_tasks"] == 1
        assert result["sections"]["yesterday"]["count"] == 1

    def test_artery_disabled(self, brain_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_1", "1")
        result = _morning_brief_impl()
        assert "sections" in result

    def test_recommendation_generated(self, brain_path):
        write_tasks(brain_path, [{"id": "t1", "description": "Active", "priority": 8, "status": "in_progress"}])
        result = _morning_brief_impl()
        assert result["recommendation"] is not None
        assert result["recommendation"]["action"] == "CONTINUE"
