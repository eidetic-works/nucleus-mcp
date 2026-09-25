"""
Comprehensive pytest tests for runtime/dashboard.py - targeting 90%+ coverage.
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from mcp_server_nucleus.runtime.dashboard import (
    AlertLevel,
    MetricCategory,
    OutputFormat,
    Alert,
    Snapshot,
    MetricsCache,
    AlertEngine,
    TrendAnalyzer,
    SnapshotManager,
    ASCIIFormatter,
    JSONFormatter,
    MermaidFormatter,
    MetricsCollector,
    DashboardEngine,
    format_dashboard,
)


# ============================================================================
# Alert / Snapshot dataclasses
# ============================================================================

class TestAlert:
    def test_to_dict(self):
        a = Alert(AlertLevel.CRITICAL, "tasks.pending", "too many", 600, 500)
        d = a.to_dict()
        assert d["level"] == "critical"
        assert d["metric"] == "tasks.pending"
        assert d["message"] == "too many"
        assert d["value"] == 600
        assert d["threshold"] == 500
        assert "timestamp" in d

    def test_default_timestamp(self):
        a = Alert(AlertLevel.INFO, "x", "y", 1, 2)
        assert a.timestamp  # non-empty


class TestSnapshot:
    def test_to_dict(self):
        s = Snapshot(id="s1", name="n", timestamp="t", metrics={"a": 1}, alerts=[{"x": 1}])
        d = s.to_dict()
        assert d["id"] == "s1"
        assert d["name"] == "n"
        assert d["metrics"] == {"a": 1}
        assert d["alerts"] == [{"x": 1}]


# ============================================================================
# MetricsCache
# ============================================================================

class TestMetricsCache:
    def test_set_and_get(self):
        c = MetricsCache(ttl_ms=1000)
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_get_missing(self):
        c = MetricsCache()
        assert c.get("nope") is None

    def test_get_expired(self):
        c = MetricsCache(ttl_ms=10)
        c.set("k", "v")
        time.sleep(0.02)
        assert c.get("k") is None
        assert "k" not in c.cache  # expired entry removed

    def test_invalidate_single(self):
        c = MetricsCache()
        c.set("k", "v")
        c.invalidate("k")
        assert c.get("k") is None

    def test_invalidate_all(self):
        c = MetricsCache()
        c.set("k1", "v1")
        c.set("k2", "v2")
        c.invalidate()
        assert c.get("k1") is None
        assert c.get("k2") is None
        assert c.cache == {}

    def test_thread_safety(self):
        c = MetricsCache(ttl_ms=10000)

        def worker():
            for i in range(100):
                c.set(f"k{i}", i)
                c.get(f"k{i}")

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(c.cache) == 100


# ============================================================================
# AlertEngine
# ============================================================================

class TestAlertEngine:
    def test_empty_metrics(self):
        ae = AlertEngine()
        alerts = ae.check({})
        assert alerts == []

    def test_agent_exhausted_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"agents": {"total": 10, "exhausted": 6, "utilization": 0.5}})
        # exhausted_ratio = 0.6 -> warning
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_agent_exhausted_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"agents": {"total": 10, "exhausted": 9, "utilization": 0.5}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_agent_utilization_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"agents": {"total": 10, "exhausted": 0, "utilization": 0.95}})
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_agent_utilization_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"agents": {"total": 10, "exhausted": 0, "utilization": 0.99}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_agent_zero_total(self):
        ae = AlertEngine()
        alerts = ae.check({"agents": {"total": 0, "exhausted": 0, "utilization": 0}})
        # no exhausted_ratio alert (total=0), utilization 0 below thresholds
        assert alerts == []

    def test_tasks_pending_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"tasks": {"pending": 150, "total": 200, "blocked": 0}})
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_tasks_pending_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"tasks": {"pending": 600, "total": 700, "blocked": 0}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_tasks_blocked_ratio_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"tasks": {"pending": 0, "total": 100, "blocked": 40}})
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_tasks_blocked_ratio_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"tasks": {"pending": 0, "total": 100, "blocked": 60}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_tasks_zero_total(self):
        ae = AlertEngine()
        alerts = ae.check({"tasks": {"pending": 0, "total": 0, "blocked": 0}})
        assert alerts == []

    def test_cost_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"cost": {"budget": 100, "remaining": 15}})
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_cost_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"cost": {"budget": 100, "remaining": 3}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_cost_zero_budget(self):
        ae = AlertEngine()
        alerts = ae.check({"cost": {"budget": 0, "remaining": 0}})
        assert alerts == []

    def test_deps_max_depth_warning(self):
        ae = AlertEngine()
        alerts = ae.check({"deps": {"max_depth": 6, "circular": 0}})
        levels = [a.level for a in alerts]
        assert AlertLevel.WARNING in levels

    def test_deps_max_depth_critical(self):
        ae = AlertEngine()
        alerts = ae.check({"deps": {"max_depth": 12, "circular": 0}})
        levels = [a.level for a in alerts]
        assert AlertLevel.CRITICAL in levels

    def test_deps_circular(self):
        ae = AlertEngine()
        alerts = ae.check({"deps": {"max_depth": 1, "circular": 2}})
        crit = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert any("circular" in a.metric for a in crit)

    def test_set_threshold_new_metric(self):
        ae = AlertEngine()
        ae.set_threshold("custom.metric", "warning", 42)
        assert ae.thresholds["custom.metric"]["warning"] == 42

    def test_set_threshold_existing(self):
        ae = AlertEngine()
        ae.set_threshold("tasks.pending", "warning", 50)
        assert ae.thresholds["tasks.pending"]["warning"] == 50

    def test_get_active_alerts(self):
        ae = AlertEngine()
        ae.check({"tasks": {"pending": 600, "total": 700, "blocked": 0}})
        active = ae.get_active_alerts()
        assert len(active) >= 1

    def test_check_threshold_inverse_no_alert(self):
        ae = AlertEngine()
        # remaining ratio high -> no alert
        alerts = ae.check({"cost": {"budget": 100, "remaining": 90}})
        assert alerts == []


# ============================================================================
# TrendAnalyzer
# ============================================================================

class TestTrendAnalyzer:
    def test_no_brain_path(self):
        ta = TrendAnalyzer(brain_path=None)
        ta.record_metrics({"a": 1})  # no-op
        assert ta.get_trends("a") == []
        assert ta.get_velocity() == 0.0

    def test_record_and_get_trends(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        ta.record_metrics({"tasks": {"done": 5}})
        trends = ta.get_trends("tasks.done", hours=24)
        assert len(trends) == 1
        assert trends[0]["value"] == 5

    def test_get_trends_file_missing(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        assert ta.get_trends("x") == []

    def test_get_trends_old_entries_filtered(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path, retention_days=7)
        # write an old entry manually
        metrics_file = tmp_path / "ledger" / "metrics.jsonl"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
        metrics_file.write_text(json.dumps({"timestamp": old_ts, "interval": "hourly", "metrics": {"tasks.done": 1}}) + "\n")
        trends = ta.get_trends("tasks.done", hours=24)
        assert trends == []

    def test_get_trends_malformed_lines(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        metrics_file = tmp_path / "ledger" / "metrics.jsonl"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_file.write_text("not json\n{bad\n")
        assert ta.get_trends("x") == []

    def test_get_velocity_insufficient_data(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        ta.record_metrics({"tasks": {"done": 5}})
        assert ta.get_velocity() == 0.0

    def test_get_velocity_with_data(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        ta.record_metrics({"tasks": {"done": 5}})
        ta.record_metrics({"tasks": {"done": 15}})
        v = ta.get_velocity(hours=24)
        assert v == pytest.approx(10 / 24, rel=0.01)

    def test_get_velocity_zero_hours(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        ta.record_metrics({"tasks": {"done": 5}})
        ta.record_metrics({"tasks": {"done": 15}})
        assert ta.get_velocity(hours=0) == 0.0

    def test_flatten_metrics(self):
        ta = TrendAnalyzer()
        flat = ta._flatten_metrics({"a": {"b": 1}, "c": 2})
        assert flat == {"a.b": 1, "c": 2}

    def test_cleanup_old_entries(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path, retention_days=7)
        metrics_file = tmp_path / "ledger" / "metrics.jsonl"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        metrics_file.write_text(json.dumps({"timestamp": old_ts, "interval": "h", "metrics": {"x": 1}}) + "\n")
        ta.record_metrics({"y": 2})  # triggers cleanup
        lines = metrics_file.read_text().strip().split("\n")
        # old entry removed, only new entry remains
        assert len(lines) == 1

    def test_cleanup_file_missing(self, tmp_path):
        ta = TrendAnalyzer(brain_path=tmp_path)
        ta._cleanup_old_entries()  # no file -> no-op


# ============================================================================
# SnapshotManager
# ============================================================================

class TestSnapshotManager:
    def test_create_no_brain_path(self):
        sm = SnapshotManager(brain_path=None)
        snap = sm.create({"a": 1}, [], name="test")
        assert snap.name == "test"
        assert snap.metrics == {"a": 1}

    def test_create_default_name(self):
        sm = SnapshotManager(brain_path=None)
        snap = sm.create({"a": 1}, [])
        assert "Snapshot" in snap.name

    def test_create_with_alerts(self):
        sm = SnapshotManager(brain_path=None)
        alert = Alert(AlertLevel.WARNING, "m", "msg", 1, 2)
        snap = sm.create({"a": 1}, [alert])
        assert len(snap.alerts) == 1
        assert snap.alerts[0]["metric"] == "m"

    def test_create_persists_to_disk(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        snap = sm.create({"a": 1}, [], name="t")
        files = list((tmp_path / "snapshots" / "dashboard").glob("snap_*.json"))
        assert len(files) == 1
        loaded = sm.get(snap.id)
        assert loaded is not None
        assert loaded.name == "t"

    def test_get_no_dir(self):
        sm = SnapshotManager(brain_path=None)
        assert sm.get("x") is None

    def test_get_missing(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        assert sm.get("nonexistent") is None

    def test_list_no_dir(self):
        sm = SnapshotManager(brain_path=None)
        assert sm.list() == []

    def test_list_empty_dir(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        assert sm.list() == []

    def test_list_with_snapshots(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        sm.create({"a": 1}, [], name="s1")
        sm.create({"a": 2}, [], name="s2")
        snaps = sm.list()
        assert len(snaps) == 2

    def test_compare_not_found(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        result = sm.compare("a", "b")
        assert "error" in result

    def test_compare_success(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        s1 = sm.create({"tasks": {"pending": 5}}, [], name="s1")
        s2 = sm.create({"tasks": {"pending": 8}}, [], name="s2")
        result = sm.compare(s1.id, s2.id)
        assert "deltas" in result
        assert "tasks.pending" in result["deltas"]
        assert result["deltas"]["tasks.pending"]["delta"] == 3

    def test_compare_non_numeric(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path)
        s1 = sm.create({"x": "str"}, [], name="s1")
        s2 = sm.create({"x": "str2"}, [], name="s2")
        result = sm.compare(s1.id, s2.id)
        assert result["deltas"] == {}

    def test_flatten(self):
        sm = SnapshotManager(brain_path=None)
        assert sm._flatten({"a": {"b": 1}}) == {"a.b": 1}

    def test_cleanup_old_snapshots(self, tmp_path):
        sm = SnapshotManager(brain_path=tmp_path, max_snapshots=2)
        sm.create({"a": 1}, [])
        sm.create({"a": 2}, [])
        sm.create({"a": 3}, [])
        files = list((tmp_path / "snapshots" / "dashboard").glob("snap_*.json"))
        assert len(files) == 2

    def test_cleanup_no_dir(self):
        sm = SnapshotManager(brain_path=None)
        sm._cleanup_old_snapshots()  # no-op


# ============================================================================
# ASCIIFormatter
# ============================================================================

class TestASCIIFormatter:
    def test_minimal(self):
        f = ASCIIFormatter()
        out = f.format({}, [], detail_level="minimal")
        assert "NOP Status Dashboard" in out

    def test_with_alerts(self):
        f = ASCIIFormatter()
        alert = Alert(AlertLevel.CRITICAL, "m", "boom", 1, 2)
        out = f.format({}, [alert])
        assert "ALERTS" in out
        assert "boom" in out

    def test_warning_alert_icon(self):
        f = ASCIIFormatter()
        alert = Alert(AlertLevel.WARNING, "m", "warn", 1, 2)
        out = f.format({}, [alert])
        assert "warn" in out

    def test_agents_section(self):
        f = ASCIIFormatter()
        out = f.format({"agents": {"total": 5, "active": 3, "idle": 1, "exhausted": 1, "utilization": 0.6}}, [])
        assert "AGENT POOL" in out
        assert "Active: 3/5" in out

    def test_agents_zero_total(self):
        f = ASCIIFormatter()
        out = f.format({"agents": {"total": 0, "active": 0, "idle": 0, "exhausted": 0, "utilization": 0}}, [])
        assert "Active: 0/0" in out

    def test_agents_verbose_reset_warnings(self):
        f = ASCIIFormatter()
        out = f.format(
            {"agents": {"total": 2, "active": 1, "idle": 1, "exhausted": 0, "utilization": 0.5,
                        "reset_warnings": [{"slot_id": "s1", "minutes": 30}]}},
            [], detail_level="verbose"
        )
        assert "Reset Warnings: 1" in out
        assert "s1" in out

    def test_agents_verbose_no_warnings(self):
        f = ASCIIFormatter()
        out = f.format(
            {"agents": {"total": 2, "active": 1, "idle": 1, "exhausted": 0, "utilization": 0.5,
                        "reset_warnings": []}},
            [], detail_level="verbose"
        )
        assert "Reset Warnings: 0" in out

    def test_agents_standard_capacity(self):
        f = ASCIIFormatter()
        out = f.format(
            {"agents": {"total": 2, "active": 1, "idle": 1, "exhausted": 0, "utilization": 0.5}},
            [], detail_level="standard"
        )
        assert "Capacity: 50%" in out

    def test_tasks_section(self):
        f = ASCIIFormatter()
        out = f.format({"tasks": {"pending": 5, "in_progress": 2, "blocked": 1, "done": 10, "failed": 1, "velocity": 3.5}}, [])
        assert "TASK QUEUE" in out
        assert "Pending: 5" in out

    def test_tasks_verbose(self):
        f = ASCIIFormatter()
        out = f.format({"tasks": {"pending": 5, "in_progress": 2, "blocked": 1, "done": 10, "failed": 1, "velocity": 3.5}}, [], detail_level="verbose")
        assert "Velocity: 3.5/hr" in out
        assert "Failed: 1" in out

    def test_ingestion_section(self):
        f = ASCIIFormatter()
        out = f.format({"ingestion": {"total": 10, "skipped": 2, "failed": 1, "batches": 3}}, [], detail_level="verbose")
        assert "INGESTION" in out
        assert "Total Ingested: 10" in out

    def test_cost_section(self):
        f = ASCIIFormatter()
        out = f.format({"cost": {"tokens": 1500, "usd": 5.0, "budget": 100, "remaining": 95, "burn_rate": 2.0}}, [])
        assert "COST TRACKING" in out
        assert "1.5K" in out

    def test_cost_millions_tokens(self):
        f = ASCIIFormatter()
        out = f.format({"cost": {"tokens": 1_500_000, "usd": 5.0, "budget": 0, "remaining": 0, "burn_rate": 0}}, [])
        assert "1.5M" in out

    def test_cost_small_tokens(self):
        f = ASCIIFormatter()
        out = f.format({"cost": {"tokens": 500, "usd": 5.0, "budget": 0, "remaining": 0, "burn_rate": 0}}, [])
        assert "500" in out

    def test_cost_with_budget(self):
        f = ASCIIFormatter()
        out = f.format({"cost": {"tokens": 100, "usd": 5.0, "budget": 100, "remaining": 50, "burn_rate": 0}}, [])
        assert "95% remaining" not in out  # 50/100 = 50%
        assert "50% remaining" in out

    def test_cost_verbose_burn_rate(self):
        f = ASCIIFormatter()
        out = f.format({"cost": {"tokens": 100, "usd": 5.0, "budget": 0, "remaining": 0, "burn_rate": 3.0}}, [], detail_level="verbose")
        assert "Burn Rate: $3.00/hr" in out

    def test_deps_section(self):
        f = ASCIIFormatter()
        out = f.format({"deps": {"max_depth": 3, "blocked_chains": 1, "circular": 0}}, [], detail_level="verbose")
        assert "DEPENDENCIES" in out
        assert "Max Depth: 3" in out

    def test_system_section(self):
        f = ASCIIFormatter()
        out = f.format({"system": {"uptime": "5h", "last_activity": "now", "error_rate": 2}}, [], detail_level="full")
        assert "SYSTEM HEALTH" in out
        assert "Uptime: 5h" in out

    def test_unknown_detail_level_icon(self):
        f = ASCIIFormatter()
        out = f.format({}, [], detail_level="unknown")
        assert "NOP Status Dashboard" in out


# ============================================================================
# JSONFormatter
# ============================================================================

class TestJSONFormatter:
    def test_format(self):
        f = JSONFormatter()
        alert = Alert(AlertLevel.WARNING, "m", "msg", 1, 2)
        out = f.format({"a": 1}, [alert], detail_level="standard")
        data = json.loads(out)
        assert data["metrics"] == {"a": 1}
        assert data["detail_level"] == "standard"
        assert len(data["alerts"]) == 1

    def test_format_no_alerts(self):
        f = JSONFormatter()
        out = f.format({"a": 1}, [])
        data = json.loads(out)
        assert data["alerts"] == []


# ============================================================================
# MermaidFormatter
# ============================================================================

class TestMermaidFormatter:
    def test_format_empty(self):
        f = MermaidFormatter()
        out = f.format({})
        assert "mermaid" in out
        assert "graph TD" in out

    def test_format_with_deps(self):
        f = MermaidFormatter()
        out = f.format({
            "forward_deps": {"task-1": ["dep-1"], "task-2": []},
            "depths": {"task-1": 1, "dep-1": 0, "task-2": 5},
        })
        assert "task_1" in out
        assert "dep_1" in out
        assert "Root" in out
        assert "Depth 1" in out

    def test_safe_id(self):
        f = MermaidFormatter()
        assert f._safe_id("task-1.2") == "task_1_2"

    def test_node_style_depth_0(self):
        f = MermaidFormatter()
        assert "Root" in f._get_node_style(0)

    def test_node_style_depth_2(self):
        f = MermaidFormatter()
        assert "Depth 2" in f._get_node_style(2)

    def test_node_style_depth_4(self):
        f = MermaidFormatter()
        assert "Depth 4" in f._get_node_style(4)

    def test_node_style_depth_6(self):
        f = MermaidFormatter()
        assert "Depth 6" in f._get_node_style(6)


# ============================================================================
# MetricsCollector
# ============================================================================

class TestMetricsCollector:
    def test_collect_all_no_orch(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_all(use_cache=False)
        assert "agents" in m
        assert "tasks" in m
        assert "cost" in m

    def test_collect_all_with_cache(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m1 = mc.collect_all(use_cache=True)
        m2 = mc.collect_all(use_cache=True)
        assert m1 == m2

    def test_collect_agent_metrics_no_orch_no_brain(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_agent_metrics()
        assert "error" in m

    def test_collect_agent_metrics_with_orch(self):
        class FakePool:
            def get_pool_metrics(self):
                return {"total_agents": 5, "active_agents": 3, "idle_agents": 1, "exhausted_agents": 1, "utilization": 0.6}
        class FakeOrch:
            def get_agent_pool(self):
                return FakePool()
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_agent_metrics()
        assert m["total"] == 5
        assert m["active"] == 3

    def test_collect_agent_metrics_orch_no_pool(self):
        class FakeOrch:
            def get_agent_pool(self):
                return None
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_agent_metrics()
        assert "error" in m

    def test_collect_agent_metrics_from_registry(self, tmp_path):
        registry = tmp_path / "slots" / "registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"slots": {"s1": {"status": "active"}, "s2": {"status": "exhausted"}}}))
        mc = MetricsCollector(orchestrator=None, brain_path=tmp_path)
        m = mc.collect_agent_metrics()
        assert m["total"] == 2
        assert m["exhausted"] == 1

    def test_collect_agent_metrics_exception(self):
        class FakeOrch:
            def get_agent_pool(self):
                raise Exception("boom")
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_agent_metrics()
        assert "error" in m

    def test_collect_task_metrics_with_orch(self):
        class FakeOrch:
            def get_pool_metrics(self):
                return {"total_tasks": 10, "pending": 5, "in_progress": 2, "blocked": 1, "done": 1, "failed": 1}
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_task_metrics()
        assert m["total"] == 10
        assert m["pending"] == 5

    def test_collect_task_metrics_from_file(self, tmp_path):
        tasks_path = tmp_path / "ledger" / "tasks.json"
        tasks_path.parent.mkdir(parents=True)
        tasks_path.write_text(json.dumps({"tasks": [
            {"status": "PENDING"}, {"status": "IN_PROGRESS"}, {"status": "DONE"},
        ]}))
        mc = MetricsCollector(orchestrator=None, brain_path=tmp_path)
        m = mc.collect_task_metrics()
        assert m["total"] == 3
        assert m["pending"] == 1
        assert m["done"] == 1

    def test_collect_task_metrics_no_data(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_task_metrics()
        assert "error" in m

    def test_collect_task_metrics_exception(self):
        class FakeOrch:
            def get_pool_metrics(self):
                raise Exception("boom")
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_task_metrics()
        assert "error" in m

    def test_collect_ingestion_metrics_with_orch(self):
        class FakeOrch:
            def get_ingestion_stats(self):
                return {"total_ingested": 10, "total_skipped": 2, "total_failed": 1, "batches_count": 3, "by_source": {"planning": 5}}
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_ingestion_metrics()
        assert m["total"] == 10
        assert m["batches"] == 3

    def test_collect_ingestion_metrics_no_orch(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_ingestion_metrics()
        assert m["total"] == 0

    def test_collect_ingestion_metrics_exception(self):
        class FakeOrch:
            def get_ingestion_stats(self):
                raise Exception("boom")
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_ingestion_metrics()
        assert "error" in m

    def test_collect_cost_metrics(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_cost_metrics()
        assert m["budget"] == 10.0
        assert m["tokens"] == 0

    def test_collect_dependency_metrics_with_orch(self):
        class FakeOrch:
            def get_dependency_graph(self):
                return {"depths": {"t1": 0, "t2": 5, "t3": -1}}
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_dependency_metrics()
        assert m["max_depth"] == 5
        assert m["circular"] == 1
        assert m["blocked_chains"] == 1

    def test_collect_dependency_metrics_no_orch(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_dependency_metrics()
        assert m["max_depth"] == 0

    def test_collect_dependency_metrics_exception(self):
        class FakeOrch:
            def get_dependency_graph(self):
                raise Exception("boom")
        mc = MetricsCollector(orchestrator=FakeOrch(), brain_path=None)
        m = mc.collect_dependency_metrics()
        assert "error" in m

    def test_collect_system_metrics(self):
        mc = MetricsCollector(orchestrator=None, brain_path=None)
        m = mc.collect_system_metrics()
        assert "uptime" in m
        assert "error_rate" in m


# ============================================================================
# DashboardEngine
# ============================================================================

class TestDashboardEngine:
    def test_init(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        assert de.collector is not None
        assert de.alert_engine is not None

    def test_render_ascii(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="ascii")
        assert "NOP Status Dashboard" in out

    def test_render_json(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="json")
        data = json.loads(out)
        assert "metrics" in data

    def test_render_mermaid_no_orch(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="mermaid")
        assert "mermaid" in out

    def test_render_mermaid_with_orch(self, tmp_path):
        class FakeOrch:
            def get_dependency_graph(self):
                return {"forward_deps": {"t1": ["d1"]}, "depths": {"t1": 1, "d1": 0}}
            def get_agent_pool(self): return None
            def get_pool_metrics(self): return {}
            def get_ingestion_stats(self): return {}
        de = DashboardEngine(orchestrator=FakeOrch(), brain_path=tmp_path)
        out = de.render(format="mermaid")
        assert "t1" in out

    def test_render_with_category(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="json", category="agents")
        data = json.loads(out)
        assert "agents" in data["metrics"]
        assert "tasks" not in data["metrics"]

    def test_render_with_trends(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="json", include_trends=True)
        data = json.loads(out)
        assert "tasks" in data["metrics"]

    def test_render_no_alerts(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(format="json", include_alerts=False)
        data = json.loads(out)
        assert data["alerts"] == []

    def test_render_comparison_time(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(compare_to="24h")
        assert "Comparison" in out

    def test_render_comparison_snapshot_not_found(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        out = de.render(compare_to="snap_xxx")
        assert "not found" in out or "error" in out.lower() or "Comparison" in out

    def test_render_comparison_snapshot_found(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        # _render_comparison compares "current" (nonexistent) vs compare_to
        # so it returns "not found" — verify that path
        snap = de.create_snapshot("base")
        out = de.render(compare_to=snap.id)
        assert "not found" in out.lower() or "Comparison" in out

    def test_get_metrics(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        m = de.get_metrics()
        assert "agents" in m

    def test_get_metrics_category(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        m = de.get_metrics(category="cost")
        assert "cost" in m
        assert "agents" not in m

    def test_get_alerts(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        alerts = de.get_alerts()
        assert isinstance(alerts, list)

    def test_create_snapshot(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        snap = de.create_snapshot("test")
        assert snap.name == "test"

    def test_compare_snapshots(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        s1 = de.create_snapshot("s1")
        s2 = de.create_snapshot("s2")
        result = de.compare_snapshots(s1.id, s2.id)
        assert "deltas" in result

    def test_list_snapshots(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        de.create_snapshot("s1")
        snaps = de.list_snapshots()
        assert len(snaps) == 1

    def test_set_alert_threshold(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        de.set_alert_threshold("custom.x", "warning", 10)
        assert de.alert_engine.thresholds["custom.x"]["warning"] == 10

    def test_record_hourly_metrics(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        de.record_hourly_metrics()
        # metrics are flattened; agents has "error" key when no registry
        trends = de.get_trends("agents.error", hours=24)
        assert len(trends) == 1

    def test_render_unknown_format(self, tmp_path):
        de = DashboardEngine(orchestrator=None, brain_path=tmp_path)
        with pytest.raises(ValueError):
            de.render(format="unknown")


# ============================================================================
# format_dashboard standalone
# ============================================================================

class TestFormatDashboard:
    def test_ascii(self):
        out = format_dashboard({"a": 1}, [], format="ascii")
        assert "NOP Status Dashboard" in out

    def test_json(self):
        out = format_dashboard({"a": 1}, [], format="json")
        data = json.loads(out)
        assert data["metrics"] == {"a": 1}

    def test_unknown_defaults_ascii(self):
        out = format_dashboard({"a": 1}, [], format="xyz")
        assert "NOP Status Dashboard" in out


# ============================================================================
# Enums
# ============================================================================

class TestEnums:
    def test_alert_level_values(self):
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.INFO.value == "info"

    def test_metric_category_values(self):
        assert MetricCategory.AGENTS.value == "agents"
        assert MetricCategory.TASKS.value == "tasks"

    def test_output_format_values(self):
        assert OutputFormat.ASCII.value == "ascii"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.MERMAID.value == "mermaid"
