"""Comprehensive tests for growth_ops module."""
import os
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import growth_ops
from mcp_server_nucleus.runtime.growth_ops import (
    GITHUB_REPO,
    PYPI_PACKAGE,
    GROWTH_ENGRAM_PREFIX,
    METRICS_ENGRAM_PREFIX,
    GATES,
    GROWTH_TRIGGER_EVENTS,
    GROWTH_HOOK_COOLDOWN_SECONDS,
    fetch_github_metrics,
    fetch_pypi_metrics,
    capture_metrics,
    _emit_growth_events,
    _write_metrics_engram,
    get_dogfood_streak,
    growth_pulse,
    growth_report,
    get_launch_tasks,
    compound_growth_insight,
    process_event_for_growth,
    reset_growth_hook_throttle,
)


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a temporary brain path."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "engrams").mkdir(exist_ok=True)
    (bp / "ledger").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


@pytest.fixture(autouse=True)
def reset_throttle():
    """Reset growth hook throttle before each test."""
    reset_growth_hook_throttle()
    yield
    reset_growth_hook_throttle()


# ── Constants ────────────────────────────────────────────────────

class TestConstants:
    def test_github_repo(self):
        assert GITHUB_REPO == os.environ.get("NUCLEUS_GITHUB_REPO", ""), (
            "GITHUB_REPO must come from the environment — it used to be a "
            "hardcoded org whose repos 404"
        )

    def test_pypi_package(self):
        assert PYPI_PACKAGE == "nucleus-mcp"

    def test_gates(self):
        assert "stars" in GATES
        assert "pip_installs_30d" in GATES
        assert "contributors" in GATES
        assert "github_issues" in GATES
        assert "dogfood_streak" in GATES

    def test_growth_trigger_events(self):
        assert "morning_brief_generated" in GROWTH_TRIGGER_EVENTS
        assert "task_completed_with_fence" in GROWTH_TRIGGER_EVENTS
        assert "deploy_complete" in GROWTH_TRIGGER_EVENTS

    def test_cooldown(self):
        assert GROWTH_HOOK_COOLDOWN_SECONDS == 3600


# ── fetch_github_metrics ─────────────────────────────────────────

class TestFetchGithubMetrics:
    def test_success(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "stargazers_count": 50,
            "forks_count": 10,
            "open_issues_count": 5,
            "subscribers_count": 3,
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
        result = fetch_github_metrics()
        assert result["stars"] == 50
        assert result["forks"] == 10
        assert result["open_issues"] == 5
        assert result["watchers"] == 3
        assert result["source"] == "github_api"

    def test_failure(self, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("network error")))
        result = fetch_github_metrics()
        assert "error" in result
        assert result["source"] == "github_api"


# ── fetch_pypi_metrics ───────────────────────────────────────────

class TestFetchPypiMetrics:
    def test_success(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": {"last_month": 100, "last_week": 30, "last_day": 5}
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
        result = fetch_pypi_metrics()
        assert result["last_month"] == 100
        assert result["last_week"] == 30
        assert result["last_day"] == 5
        assert result["source"] == "pypistats_api"

    def test_failure(self, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("network error")))
        result = fetch_pypi_metrics()
        assert "error" in result
        assert result["source"] == "pypistats_api"


# ── capture_metrics ──────────────────────────────────────────────

class TestCaptureMetrics:
    def test_capture_success(self, monkeypatch):
        # Mock fetch functions
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {
            "stars": 150, "forks": 20, "open_issues": 10, "source": "github_api"
        })
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {
            "last_month": 100, "source": "pypistats_api"
        })
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 25)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)
        monkeypatch.setattr(growth_ops, "_write_metrics_engram", lambda *a: True)

        result = capture_metrics(write_engram=True)
        assert result["github"]["stars"] == 150
        assert result["pypi"]["last_month"] == 100
        assert "gates" in result
        assert result["gates"]["stars"]["passed"] is True
        assert result["gates"]["stars"]["current"] == 150
        assert result["gates"]["stars"]["target"] == 100
        assert result["engram_written"] is True

    def test_capture_no_engram(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {"error": "fail", "source": "github_api"})
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {"error": "fail", "source": "pypistats_api"})
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 0)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)

        result = capture_metrics(write_engram=False)
        assert "engram_written" not in result
        # Gates should only have dogfood_streak (github and pypi had errors)
        assert "dogfood_streak" in result["gates"]
        assert "stars" not in result["gates"]

    def test_capture_gates_summary(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {
            "stars": 50, "forks": 5, "open_issues": 3, "source": "github_api"
        })
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {
            "last_month": 30, "source": "pypistats_api"
        })
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 10)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)
        monkeypatch.setattr(growth_ops, "_write_metrics_engram", lambda *a: True)

        result = capture_metrics()
        assert "passed" in result["gates_summary"]
        # stars: 50 < 100 -> not passed
        assert result["gates"]["stars"]["passed"] is False


# ── _emit_growth_events ──────────────────────────────────────────

class TestEmitGrowthEvents:
    def test_emit_events(self, monkeypatch):
        mock_emit = MagicMock()
        mock_record_delta = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.event_ops._emit_event", mock_emit)
        monkeypatch.setattr("mcp_server_nucleus.runtime.delta_ops.record_delta", mock_record_delta)
        gates = {
            "stars": {"current": 50, "target": 100, "passed": False},
            "pip_installs_30d": {"current": 60, "target": 50, "passed": True},
        }
        _emit_growth_events(gates)
        assert mock_emit.call_count == 2
        assert mock_record_delta.call_count == 2

    def test_emit_events_no_event_ops(self, monkeypatch):
        # If event_ops can't be imported, should return silently
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if "event_ops" in name:
                raise ImportError("not found")
            return real_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        gates = {"stars": {"current": 50, "target": 100, "passed": False}}
        _emit_growth_events(gates)  # should not raise

    def test_emit_events_with_delta(self, monkeypatch):
        mock_emit = MagicMock()
        mock_record_delta = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.event_ops._emit_event", mock_emit)
        monkeypatch.setattr("mcp_server_nucleus.runtime.delta_ops.record_delta", mock_record_delta)
        gates = {"stars": {"current": 50, "target": 100, "passed": False}}
        _emit_growth_events(gates)
        mock_record_delta.assert_called()

    def test_emit_events_zero_target(self, monkeypatch):
        mock_emit = MagicMock()
        mock_record_delta = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.event_ops._emit_event", mock_emit)
        monkeypatch.setattr("mcp_server_nucleus.runtime.delta_ops.record_delta", mock_record_delta)
        gates = {"custom": {"current": 0, "target": 0, "passed": True}}
        _emit_growth_events(gates)
        mock_emit.assert_called()


# ── _write_metrics_engram ────────────────────────────────────────

class TestWriteMetricsEngram:
    def test_success(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        result = _write_metrics_engram({"stars": 50}, {"last_month": 30}, 2, 5)
        assert result is True
        mock_write.assert_called_once()

    def test_failure(self, monkeypatch):
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl",
                            MagicMock(side_effect=Exception("write failed")))
        result = _write_metrics_engram({}, {}, 0, 0)
        assert result is False


# ── get_dogfood_streak ───────────────────────────────────────────

class TestGetDogfoodStreak:
    def test_success(self, monkeypatch):
        mock_search = MagicMock()
        mock_search.return_value = json.dumps({
            "data": {"engrams": [
                {"key": "growth_metrics_20240101"},
                {"key": "growth_metrics_20240102"},
                {"key": "growth_metrics_20240101"},  # duplicate date
                {"key": "other_key"},
            ]}
        })
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", mock_search)
        result = get_dogfood_streak()
        assert result == 2  # 2 unique dates

    def test_no_engrams(self, monkeypatch):
        mock_search = MagicMock()
        mock_search.return_value = json.dumps({"data": {"engrams": []}})
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", mock_search)
        result = get_dogfood_streak()
        assert result == 0

    def test_exception(self, monkeypatch):
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl",
                            MagicMock(side_effect=Exception("search failed")))
        result = get_dogfood_streak()
        assert result == 0

    def test_invalid_date_format_ignored(self, monkeypatch):
        mock_search = MagicMock()
        mock_search.return_value = json.dumps({
            "data": {"engrams": [
                {"key": "growth_metrics_20240101"},
                {"key": "growth_metrics_invalid"},
                {"key": "growth_metrics_123"},
            ]}
        })
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", mock_search)
        result = get_dogfood_streak()
        assert result == 1  # Only the valid 8-digit date


# ── growth_pulse ─────────────────────────────────────────────────

class TestGrowthPulse:
    def test_full_pulse(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {
            "stars": 150, "forks": 20, "open_issues": 10, "source": "github_api"
        })
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {
            "last_month": 100, "source": "pypistats_api"
        })
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 25)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)
        monkeypatch.setattr(growth_ops, "_write_metrics_engram", lambda *a: True)

        # Mock morning brief
        mock_brief = MagicMock()
        mock_brief.return_value = {"sections": {"memory": {"count": 5}, "tasks": {"total_tasks": 3}},
                                   "recommendation": {"action": "START"}}
        monkeypatch.setattr("mcp_server_nucleus.runtime.morning_brief_ops._morning_brief_impl", mock_brief)

        # Mock fusion reactor
        mock_fusion = MagicMock()
        mock_fusion.return_value = {"sections": {"recall": {"matches": 3}}, "meta": {"engrams_written": 2}}
        monkeypatch.setattr("mcp_server_nucleus.runtime.god_combos.fusion_reactor.run_fusion_reactor", mock_fusion)

        result = growth_pulse(write_engrams=True)
        assert result["pipeline"] == "growth_pulse"
        assert result["meta"]["steps_completed"] == 4
        assert "brief" in result["sections"]
        assert "metrics" in result["sections"]
        assert "streak" in result["sections"]
        assert "compound" in result["sections"]

    def test_pulse_no_engrams(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {
            "stars": 150, "forks": 20, "open_issues": 10, "source": "github_api"
        })
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {
            "last_month": 100, "source": "pypistats_api"
        })
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 25)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)
        monkeypatch.setattr(growth_ops, "_write_metrics_engram", lambda *a: True)

        mock_brief = MagicMock()
        mock_brief.return_value = {"sections": {"memory": {"count": 5}, "tasks": {"total_tasks": 3}},
                                   "recommendation": {"action": "START"}}
        monkeypatch.setattr("mcp_server_nucleus.runtime.morning_brief_ops._morning_brief_impl", mock_brief)

        result = growth_pulse(write_engrams=False)
        assert "compound" not in result["sections"]
        assert result["meta"]["steps_completed"] == 3

    def test_pulse_brief_error(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "fetch_github_metrics", lambda: {
            "stars": 150, "forks": 20, "open_issues": 10, "source": "github_api"
        })
        monkeypatch.setattr(growth_ops, "fetch_pypi_metrics", lambda: {
            "last_month": 100, "source": "pypistats_api"
        })
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 25)
        monkeypatch.setattr(growth_ops, "_emit_growth_events", lambda x: None)
        monkeypatch.setattr(growth_ops, "_write_metrics_engram", lambda *a: True)

        monkeypatch.setattr("mcp_server_nucleus.runtime.morning_brief_ops._morning_brief_impl",
                            MagicMock(side_effect=Exception("brief failed")))

        result = growth_pulse(write_engrams=False)
        assert "error" in result["sections"]["brief"]

    def test_pulse_metrics_error(self, monkeypatch):
        monkeypatch.setattr(growth_ops, "capture_metrics", MagicMock(side_effect=Exception("metrics failed")))
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 0)

        mock_brief = MagicMock()
        mock_brief.return_value = {"sections": {}, "recommendation": {}}
        monkeypatch.setattr("mcp_server_nucleus.runtime.morning_brief_ops._morning_brief_impl", mock_brief)

        result = growth_pulse(write_engrams=False)
        assert "error" in result["sections"]["metrics"]


# ── growth_report ────────────────────────────────────────────────

class TestGrowthReport:
    def test_success(self, monkeypatch):
        mock_search = MagicMock()
        mock_search.return_value = json.dumps({
            "data": {"engrams": [
                {"key": "growth_metrics_20240101", "value": "stars=50"},
                {"key": "growth_compound_001", "value": "insight"},
                {"key": "growth_other", "value": "other"},
            ]}
        })
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", mock_search)
        monkeypatch.setattr(growth_ops, "capture_metrics", lambda write_engram: {"gates": {"stars": {"passed": True}}})
        monkeypatch.setattr(growth_ops, "get_dogfood_streak", lambda: 5)

        result = growth_report()
        assert result["total_growth_engrams"] == 3
        assert result["metrics_snapshots"] == 1
        assert result["compound_insights"] == 1
        assert result["dogfood_streak"] == 5

    def test_exception(self, monkeypatch):
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl",
                            MagicMock(side_effect=Exception("search failed")))
        result = growth_report()
        assert "error" in result


# ── get_launch_tasks ─────────────────────────────────────────────

class TestGetLaunchTasks:
    def test_no_tasks_file(self, brain_path):
        result = get_launch_tasks()
        assert "error" in result
        assert "No tasks file" in result["error"]

    def test_no_growth_tasks(self, brain_path):
        tasks_file = brain_path / "ledger" / "tasks.json"
        tasks_file.write_text(json.dumps([{"id": "t1", "source": "other"}]))
        result = get_launch_tasks()
        assert "message" in result
        assert "No growth tasks" in result["message"]

    def test_with_growth_tasks(self, brain_path):
        tasks_file = brain_path / "ledger" / "tasks.json"
        tasks_file.write_text(json.dumps([
            {"id": "t1", "source": "recipe:growth", "status": "DONE", "description": "Done task"},
            {"id": "t2", "source": "recipe:growth", "status": "READY", "description": "Ready task"},
        ]))
        result = get_launch_tasks()
        assert result["total"] == 2
        assert result["done"] == 1
        assert result["ready"] == 1
        assert len(result["next_actions"]) == 1

    def test_exception(self, brain_path):
        tasks_file = brain_path / "ledger" / "tasks.json"
        tasks_file.write_text("invalid json{{{")
        result = get_launch_tasks()
        assert "error" in result


# ── compound_growth_insight ──────────────────────────────────────

class TestCompoundGrowthInsight:
    def test_success(self, monkeypatch):
        mock_fusion = MagicMock()
        mock_fusion.return_value = {"result": "insight"}
        monkeypatch.setattr("mcp_server_nucleus.runtime.god_combos.fusion_reactor.run_fusion_reactor", mock_fusion)
        result = compound_growth_insight("test observation")
        assert result["result"] == "insight"
        mock_fusion.assert_called_once()

    def test_exception(self, monkeypatch):
        monkeypatch.setattr("mcp_server_nucleus.runtime.god_combos.fusion_reactor.run_fusion_reactor",
                            MagicMock(side_effect=Exception("fusion failed")))
        result = compound_growth_insight("test")
        assert "error" in result


# ── process_event_for_growth ─────────────────────────────────────

class TestProcessEventForGrowth:
    def test_not_trigger_event(self):
        result = process_event_for_growth("unknown_event", {"data": "value"})
        assert result is None

    def test_trigger_event_success(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        result = process_event_for_growth("morning_brief_generated", {
            "engram_count": 5, "task_count": 3, "action": "START"
        })
        assert result is not None
        assert result["event_type"] == "morning_brief_generated"
        assert result["action"] == "engram_written"
        mock_write.assert_called_once()

    def test_throttle(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        # First call should work
        result1 = process_event_for_growth("morning_brief_generated", {"engram_count": 5, "task_count": 3, "action": "START"})
        assert result1 is not None
        # Second call within cooldown should be throttled
        result2 = process_event_for_growth("morning_brief_generated", {"engram_count": 5, "task_count": 3, "action": "START"})
        assert result2 is None

    def test_empty_event_data(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        result = process_event_for_growth("deploy_complete", {})
        assert result is not None
        assert "observation" in result

    def test_none_event_data(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        result = process_event_for_growth("deploy_complete", None)
        assert result is not None

    def test_write_failure(self, monkeypatch):
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl",
                            MagicMock(side_effect=Exception("write failed")))
        result = process_event_for_growth("morning_brief_generated", {"engram_count": 5, "task_count": 3, "action": "START"})
        assert result is None

    def test_template_formatting(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        result = process_event_for_growth("task_completed_with_fence", {
            "task_id": "t1", "outcome": "success"
        })
        assert result is not None
        assert "t1" in result["observation"]
        assert "success" in result["observation"]

    def test_reset_throttle(self, monkeypatch):
        mock_write = MagicMock()
        monkeypatch.setattr("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", mock_write)
        # First call
        process_event_for_growth("morning_brief_generated", {"engram_count": 5, "task_count": 3, "action": "START"})
        # Reset throttle
        reset_growth_hook_throttle()
        # Second call should work now
        result = process_event_for_growth("morning_brief_generated", {"engram_count": 5, "task_count": 3, "action": "START"})
        assert result is not None
