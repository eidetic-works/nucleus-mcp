"""Comprehensive coverage tests for runtime/satellite_ops.py."""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
    b = tmp_path / ".brain"
    for sub in ["ledger", "artifacts", "archive", "config", "slots",
                "protocols", "memory", "sessions", "workflows", "meta"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


# ─── _generate_sparkline ───────────────────────────────────────────────────

class TestGenerateSparkline:
    def test_empty_counts(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([])
        assert result == "▁▁▁▁▁▁▁"

    def test_all_zeros(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([0, 0, 0])
        assert result == "▁▁▁"

    def test_normal_counts(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([1, 2, 3, 4, 5, 6, 7, 8])
        assert len(result) == 8
        assert result[0] != result[-1]  # different chars for different values

    def test_single_max(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([0, 5])
        # max=5, scale=7/5=1.4; 0*1.4=0 -> chars[0]; 5*1.4=7 -> chars[7]
        assert result[0] == "▁"
        assert result[1] == "█"

    def test_custom_chars(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([1, 2], chars="12345678")
        assert len(result) == 2

    def test_all_same_nonzero(self):
        from mcp_server_nucleus.runtime.satellite_ops import _generate_sparkline
        result = _generate_sparkline([5, 5, 5])
        # all map to max char
        assert all(c == "█" for c in result)


# ─── _get_activity_sparkline ───────────────────────────────────────────────

class TestGetActivitySparkline:
    def test_no_events_file(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        result = _get_activity_sparkline(days=7)
        assert result["sparkline"] == "▁▁▁▁▁▁▁"
        assert result["total_events"] == 0
        assert result["peak_day"] is None
        assert result["days_covered"] == 7

    def test_precomputed_summary(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        today = datetime.now().date()
        days = {}
        for i in range(7):
            day = (today - timedelta(days=i)).isoformat()
            days[day] = i + 1
        summary = {"days": days}
        (brain / "ledger" / "activity_summary.json").write_text(json.dumps(summary))
        result = _get_activity_sparkline(days=7)
        assert result["source"] == "precomputed"
        assert result["total_events"] == sum(range(1, 8))
        assert result["peak_day"] is not None

    def test_precomputed_summary_empty(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        summary = {"days": {}}
        (brain / "ledger" / "activity_summary.json").write_text(json.dumps(summary))
        # sum(counts) == 0, falls through to slow path
        result = _get_activity_sparkline(days=7)
        assert result["total_events"] == 0

    def test_precomputed_summary_corrupt(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        (brain / "ledger" / "activity_summary.json").write_text("not json")
        # Falls through to slow path (no events file)
        result = _get_activity_sparkline(days=7)
        assert result["total_events"] == 0

    def test_slow_path_with_events(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        today = datetime.now().date().isoformat()
        events = []
        for i in range(5):
            events.append(json.dumps({
                "event_id": f"evt-{i}",
                "timestamp": f"{today}T14:00:00+0530",
                "type": "test",
                "emitter": "test",
                "data": {},
                "description": ""
            }))
        events_path = brain / "ledger" / "events.jsonl"
        events_path.write_text("\n".join(events) + "\n")
        result = _get_activity_sparkline(days=7)
        assert result["total_events"] == 5
        assert result["peak_day"] == today

    def test_slow_path_corrupt_event_line(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        today = datetime.now().date().isoformat()
        events = [
            json.dumps({"timestamp": f"{today}T14:00:00+0530"}),
            "not valid json",
            json.dumps({"no_timestamp": True}),
        ]
        (brain / "ledger" / "events.jsonl").write_text("\n".join(events) + "\n")
        result = _get_activity_sparkline(days=7)
        # Only 1 valid event with timestamp
        assert result["total_events"] == 1

    def test_slow_path_empty_lines(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        (brain / "ledger" / "events.jsonl").write_text("\n\n\n")
        result = _get_activity_sparkline(days=7)
        assert result["total_events"] == 0

    def test_days_param_custom(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        result = _get_activity_sparkline(days=3)
        assert result["days_covered"] == 3

    def test_brain_path_error(self, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_activity_sparkline
        # Unset brain path and cwd to a place with no .brain
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _get_activity_sparkline(days=7)
        assert "error" in result
        assert result["total_events"] == 0


# ─── _get_health_stats ─────────────────────────────────────────────────────

class TestGetHealthStats:
    def test_empty_brain(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        result = _get_health_stats()
        assert result["artifacts_count"] == 0
        assert result["archive_count"] == 0
        assert result["stale_count"] == 0

    def test_with_artifacts(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        (brain / "artifacts" / "a.md").write_text("test")
        (brain / "artifacts" / "sub").mkdir(exist_ok=True)
        (brain / "artifacts" / "sub" / "b.md").write_text("test")
        result = _get_health_stats()
        assert result["artifacts_count"] == 2
        assert result["stale_count"] == 0

    def test_with_stale_artifacts(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        f = brain / "artifacts" / "stale.md"
        f.write_text("test")
        # Set mtime to 40 days ago
        old_time = time.time() - (40 * 24 * 60 * 60)
        import os
        os.utime(str(f), (old_time, old_time))
        result = _get_health_stats()
        assert result["artifacts_count"] == 1
        assert result["stale_count"] == 1

    def test_with_archive(self, brain):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        (brain / "archive" / "old1.md").write_text("test")
        (brain / "archive" / "old2.md").write_text("test")
        result = _get_health_stats()
        assert result["archive_count"] == 2

    def test_no_artifacts_dir(self, tmp_path, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        b = tmp_path / ".brain2"
        b.mkdir()
        (b / "ledger").mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
        result = _get_health_stats()
        assert result["artifacts_count"] == 0
        assert result["archive_count"] == 0

    def test_exception_path(self, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_health_stats
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _get_health_stats()
        assert "error" in result


# ─── _get_products_health ──────────────────────────────────────────────────

class TestGetProductsHealth:
    def test_basic(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_products_health
        monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", str(brain))
        result = _get_products_health()
        assert "nucleus_os" in result
        assert "ONLINE" in result["nucleus_os"]["status"]

    def test_offline_project(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_products_health
        monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", "/nonexistent/path/xyz")
        result = _get_products_health()
        assert "OFFLINE" in result["nucleus_os"]["status"]

    def test_with_satellites_config(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_products_health
        monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", str(brain))
        sat_config = {
            "satellite_1": {"path": str(brain)},
            "satellite_2": {"path": "/nonexistent"}
        }
        (brain / "config" / "satellites.json").write_text(json.dumps(sat_config))
        result = _get_products_health()
        assert "satellite_1" in result
        assert "ONLINE" in result["satellite_1"]["status"]
        assert "satellite_2" in result
        assert "OFFLINE" in result["satellite_2"]["status"]

    def test_satellites_config_corrupt(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_products_health
        monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", str(brain))
        (brain / "config" / "satellites.json").write_text("not json")
        result = _get_products_health()
        assert "nucleus_os" in result

    def test_no_satellites_config(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_products_health
        monkeypatch.setenv("NUCLEUS_PROJECT_ROOT", str(brain))
        result = _get_products_health()
        assert "nucleus_os" in result
        assert len(result) == 1


# ─── _get_satellite_view ───────────────────────────────────────────────────

class TestGetSatelliteView:
    def test_minimal_detail(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        # Mock lazy functions
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 2, "max_safe_depth": 5,
            "breadcrumbs": "a > b", "indicator": "🟢 ○○○○○"
        })
        result = _get_satellite_view(detail_level="minimal")
        assert result["detail_level"] == "minimal"
        assert result["depth"]["current"] == 2
        assert result["depth"]["max"] == 5
        assert "activity" not in result

    def test_minimal_depth_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        def _raise():
            raise Exception("boom")
        monkeypatch.setattr(m, "_depth_show", _raise)
        result = _get_satellite_view(detail_level="minimal")
        assert result["depth"]["current"] == 0
        assert result["depth"]["max"] == 5
        assert "not tracked" in result["depth"]["breadcrumbs"]

    def test_standard_detail(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        # Mock commitment_ledger
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {"total_open": 3, "green_tier": 2,
                                                 "yellow_tier": 1, "red_tier": 0},
                                       "last_scan": "2026-01-01"})
        result = _get_satellite_view(detail_level="standard")
        assert "activity" in result
        assert "health" in result
        assert "products" in result
        assert result["commitments"]["total_open"] == 3
        assert result["commitments"]["green"] == 2

    def test_standard_commitments_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        def _raise(b):
            raise Exception("boom")
        monkeypatch.setattr(m.commitment_ledger, "load_ledger", _raise)
        result = _get_satellite_view(detail_level="standard")
        assert result["commitments"] is None

    def test_sprint_detail(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        monkeypatch.setattr(m, "_get_state", lambda: {
            "sprint": {"name": "Sprint1", "focus": "Fix bugs", "status": "active"}
        })
        monkeypatch.setattr(m, "_list_tasks", lambda: [
            {"id": "t1", "description": "Task 1", "status": "READY"},
            {"id": "t2", "description": "Task 2", "status": "IN_PROGRESS"},
            {"id": "t3", "description": "Task 3", "status": "DONE"},
        ])
        result = _get_satellite_view(detail_level="sprint")
        assert result["sprint"]["name"] == "Sprint1"
        assert len(result["active_tasks"]) == 2

    def test_sprint_detail_state_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        def _raise():
            raise Exception("state error")
        monkeypatch.setattr(m, "_get_state", _raise)
        result = _get_satellite_view(detail_level="sprint")
        assert result["sprint"] is None
        assert result["active_tasks"] == []

    def test_sprint_detail_tasks_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        monkeypatch.setattr(m, "_get_state", lambda: {
            "sprint": {"name": "S", "focus": "F", "status": "active"}
        })
        def _raise():
            raise Exception("tasks error")
        monkeypatch.setattr(m, "_list_tasks", _raise)
        result = _get_satellite_view(detail_level="sprint")
        assert result["active_tasks"] == []

    def test_full_detail_with_sessions(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        monkeypatch.setattr(m, "_get_state", lambda: {
            "sprint": {"name": "S", "focus": "F", "status": "active"}
        })
        monkeypatch.setattr(m, "_list_tasks", lambda: [])
        monkeypatch.setattr(m, "_list_sessions", lambda: [
            {"session_id": "s1", "context": "ctx", "active_task": "t1", "saved_at": "now"}
        ])
        result = _get_satellite_view(detail_level="full")
        assert result["session"]["id"] == "s1"

    def test_full_detail_no_sessions(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        monkeypatch.setattr(m, "_get_state", lambda: {
            "sprint": {"name": "S", "focus": "F", "status": "active"}
        })
        monkeypatch.setattr(m, "_list_tasks", lambda: [])
        monkeypatch.setattr(m, "_list_sessions", lambda: [])
        result = _get_satellite_view(detail_level="full")
        assert result["session"] is None

    def test_full_detail_sessions_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.satellite_ops import _get_satellite_view
        import mcp_server_nucleus as m
        monkeypatch.setattr(m, "_depth_show", lambda: {
            "current_depth": 1, "max_safe_depth": 5,
            "breadcrumbs": "root", "indicator": "🟢 ○○○○○"
        })
        monkeypatch.setattr(m.commitment_ledger, "load_ledger",
                            lambda b: {"stats": {}, "last_scan": None})
        monkeypatch.setattr(m, "_get_state", lambda: {
            "sprint": {"name": "S", "focus": "F", "status": "active"}
        })
        monkeypatch.setattr(m, "_list_tasks", lambda: [])
        def _raise():
            raise Exception("sessions error")
        monkeypatch.setattr(m, "_list_sessions", _raise)
        result = _get_satellite_view(detail_level="full")
        assert result["session"] is None


# ─── _format_satellite_cli ─────────────────────────────────────────────────

class TestFormatSatelliteCli:
    def test_minimal_view(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {"depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "short"}}
        result = _format_satellite_cli(view)
        assert "NUCLEUS SATELLITE VIEW" in result
        assert "DEPTH" in result
        assert "short" in result

    def test_long_breadcrumbs_truncated(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        long_bc = "x" * 100
        view = {"depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": long_bc}}
        result = _format_satellite_cli(view)
        assert "..." in result

    def test_with_activity(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "activity": {"sparkline": "▁▂▃▄▅▆▇", "total_events": 42, "peak_day": "2026-01-15"}
        }
        result = _format_satellite_cli(view)
        assert "ACTIVITY" in result
        assert "42" in result
        assert "01-15" in result

    def test_with_activity_no_peak(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "activity": {"sparkline": "▁▁▁▁▁▁▁", "total_events": 0, "peak_day": None}
        }
        result = _format_satellite_cli(view)
        assert "N/A" in result

    def test_with_sprint(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "sprint": {"name": "Sprint Alpha", "focus": "Fix all bugs"},
            "active_tasks": [{"description": "Fix bug A"}, {"description": "Fix bug B"}]
        }
        result = _format_satellite_cli(view)
        assert "SPRINT" in result
        assert "Sprint Alpha" in result
        assert "Fix bug A" in result

    def test_with_sprint_no_focus(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "sprint": {"name": "Sprint", "focus": ""},
        }
        result = _format_satellite_cli(view)
        assert "SPRINT" in result

    def test_with_session(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "session": {"context": "my context", "active_task": "task 1"}
        }
        result = _format_satellite_cli(view)
        assert "SESSION" in result
        assert "my context" in result

    def test_with_health(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "health": {"artifacts_count": 5, "archive_count": 3, "stale_count": 0}
        }
        result = _format_satellite_cli(view)
        assert "HEALTH" in result
        assert "5" in result
        assert "3" in result

    def test_with_health_stale(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "health": {"artifacts_count": 5, "archive_count": 3, "stale_count": 2}
        }
        result = _format_satellite_cli(view)
        assert "stale" in result

    def test_with_products(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "products": {"nucleus_os": {"status": "🟢 ONLINE", "path": "nucleus"}}
        }
        result = _format_satellite_cli(view)
        assert "CORE PRODUCTS" in result
        assert "Nucleus Os" in result

    def test_with_commitments(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "commitments": {"total_open": 5, "green": 3, "yellow": 1, "red": 1}
        }
        result = _format_satellite_cli(view)
        assert "COMMITMENTS" in result
        assert "🔴" in result  # red > 0

    def test_with_commitments_yellow_load(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "commitments": {"total_open": 5, "green": 2, "yellow": 3, "red": 0}
        }
        result = _format_satellite_cli(view)
        assert "🟡" in result  # yellow > 2

    def test_with_commitments_green_load(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "commitments": {"total_open": 3, "green": 3, "yellow": 0, "red": 0}
        }
        result = _format_satellite_cli(view)
        assert "🟢" in result

    def test_with_commitments_empty(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        view = {
            "depth": {"indicator": "🟢 ○○○○○", "breadcrumbs": "bc"},
            "commitments": {"total_open": 0, "green": 0, "yellow": 0, "red": 0}
        }
        result = _format_satellite_cli(view)
        assert "✨" in result

    def test_empty_view(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        result = _format_satellite_cli({})
        assert "NUCLEUS SATELLITE VIEW" in result
        assert "not tracked" in result

    def test_no_depth_key(self):
        from mcp_server_nucleus.runtime.satellite_ops import _format_satellite_cli
        result = _format_satellite_cli({})
        # Should use defaults
        assert "⚪" in result
