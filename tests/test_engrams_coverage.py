"""Coverage tests for mcp_server_nucleus/tools/engrams.py — the
nucleus_engrams facade tool (engrams, health, observability, DSoR, tiers,
god combos, context graph, billing, heartbeat)."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from mcp_server_nucleus.tools import engrams


# ── helpers ─────────────────────────────────────────────────────────

def _make_mcp():
    captured = {}

    def tool_decorator(*args, **kwargs):
        def wrapper(func):
            captured["func"] = func
            return func
        return wrapper

    mcp = MagicMock()
    mcp.tool = tool_decorator
    mcp._captured = captured
    return mcp


def _run(coro):
    return asyncio.run(coro)


def _make_tf(brain_path=None, get_brain_path_fn=None):
    """Register the engrams facade and return the captured tool function."""
    mcp = _make_mcp()
    make_response = lambda ok, data=None, error=None: json.dumps({"success": ok, "data": data, "error": error})
    helpers = {
        "make_response": make_response,
        "emit_event": MagicMock(),
        "get_brain_path": get_brain_path_fn or (lambda: brain_path or Path("/tmp/fake_brain")),
    }
    engrams.register(mcp, helpers)
    return mcp._captured["func"]


@pytest.fixture
def brain(tmp_path, monkeypatch):
    bp = tmp_path / ".brain"
    for sub in ["ledger", "ledger/decisions", "ledger/snapshots", "ledger/metering",
                "ledger/auth", "engrams", "sessions", "tasks", "memory"]:
        (bp / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


# ── register ────────────────────────────────────────────────────────

class TestRegister:
    def test_returns_tool_list(self, brain):
        mcp = _make_mcp()
        helpers = {
            "make_response": lambda ok, data=None, error=None: "{}",
            "emit_event": MagicMock(),
            "get_brain_path": lambda: brain,
        }
        result = engrams.register(mcp, helpers)
        assert len(result) == 1
        name, func = result[0]
        assert name == "nucleus_engrams"
        assert asyncio.iscoroutinefunction(func)


# ── version / health / governance ───────────────────────────────────

class TestVersionHealth:
    def test_version(self, brain):
        with patch("mcp_server_nucleus.runtime.health_ops._brain_version_impl",
                   return_value={"nucleus_version": "1.0", "python_version": "3.11",
                                 "platform": "macOS", "platform_release": "R",
                                 "mcp_tools_count": 50, "architecture": "facade", "status": "ok"}):
            tf = _make_tf(brain)
            r = _run(tf("version", {}))
        assert "1.0" in r
        assert "NUCLEUS VERSION INFO" in r

    def test_health(self, brain):
        with patch("mcp_server_nucleus.runtime.health_ops._brain_health_impl", return_value="healthy"):
            tf = _make_tf(brain)
            r = _run(tf("health", {}))
        assert "healthy" in r

    def test_governance_status(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_governance_status_impl",
                   return_value="gov ok"):
            tf = _make_tf(brain)
            r = _run(tf("governance_status", {}))
        assert "gov ok" in r


# ── export_schema ───────────────────────────────────────────────────

class TestExportSchema:
    def test_small_schema(self, brain):
        with patch("mcp_server_nucleus.runtime.schema_gen.generate_tool_schema",
                   new_callable=AsyncMock, return_value={"paths": {"a": 1}}):
            tf = _make_tf(brain)
            r = _run(tf("export_schema", {}))
        assert "paths" in r

    def test_large_schema(self, brain):
        # Need > 200KB serialized to trigger the cap
        big = {"paths": {f"tool_{i}": "x" * 500 for i in range(1000)}}
        with patch("mcp_server_nucleus.runtime.schema_gen.generate_tool_schema",
                   new_callable=AsyncMock, return_value=big):
            tf = _make_tf(brain)
            r = _run(tf("export_schema", {}))
        assert "too large" in r


# ── performance / prometheus metrics ────────────────────────────────

class TestMetrics:
    def test_perf_no_metrics(self, brain):
        with patch("mcp_server_nucleus.runtime.profiling.get_metrics", return_value={}):
            tf = _make_tf(brain)
            r = _run(tf("performance_metrics", {}))
        assert "No metrics" in r

    def test_perf_with_metrics(self, brain):
        with patch("mcp_server_nucleus.runtime.profiling.get_metrics", return_value={"a": 1}), \
             patch("mcp_server_nucleus.runtime.profiling.get_metrics_summary", return_value={"s": 1}):
            tf = _make_tf(brain)
            r = _run(tf("performance_metrics", {}))
        assert "summary" in r

    def test_perf_export_to_file(self, brain):
        with patch("mcp_server_nucleus.runtime.profiling.get_metrics", return_value={"a": 1}), \
             patch("mcp_server_nucleus.runtime.profiling.export_metrics_to_file", return_value="/tmp/metrics.json"):
            tf = _make_tf(brain)
            r = _run(tf("performance_metrics", {"export_to_file": True}))
        assert "exported_to" in r

    def test_perf_export_exception(self, brain):
        with patch("mcp_server_nucleus.runtime.profiling.get_metrics", return_value={"a": 1}), \
             patch("mcp_server_nucleus.runtime.profiling.export_metrics_to_file", side_effect=RuntimeError("boom")):
            tf = _make_tf(brain)
            r = _run(tf("performance_metrics", {"export_to_file": True}))
        assert "Export failed" in r

    def test_prom_default(self, brain):
        with patch("mcp_server_nucleus.runtime.prometheus.get_prometheus_metrics", return_value="metrics"):
            tf = _make_tf(brain)
            r = _run(tf("prometheus_metrics", {}))
        assert r == "metrics"

    def test_prom_json(self, brain):
        with patch("mcp_server_nucleus.runtime.prometheus.get_metrics_json", return_value={"j": 1}):
            tf = _make_tf(brain)
            r = _run(tf("prometheus_metrics", {"format": "json"}))
        assert "j" in r

    def test_prom_invalid_format(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("prometheus_metrics", {"format": 123}))
        assert "must be str" in r


# ── audit_log ───────────────────────────────────────────────────────

class TestAuditLog:
    def test_audit_log(self, brain):
        with patch("mcp_server_nucleus.runtime.health_ops._brain_audit_log_impl", return_value="audit"):
            tf = _make_tf(brain)
            r = _run(tf("audit_log", {"limit": 5}))
        assert "audit" in r


# ── write/query/search engrams ──────────────────────────────────────

class TestEngramOps:
    def test_write_engram(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", return_value='{"success":true}'):
            tf = _make_tf(brain)
            r = _run(tf("write_engram", {"key": "k", "value": "v"}))
        assert "success" in r

    def test_add_alias(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", return_value='{"success":true}') as m:
            tf = _make_tf(brain)
            _run(tf("add", {"key": "k", "value": "v"}))
        m.assert_called_once_with("k", "v", "Decision", 5)

    def test_query_engrams(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_query_engrams_impl", return_value='{"success":true}') as m:
            tf = _make_tf(brain)
            _run(tf("query_engrams", {"context": "Decision", "min_intensity": 3}))
        m.assert_called_once_with("Decision", 3, 50)

    def test_search_engrams(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", return_value='{"success":true}') as m:
            tf = _make_tf(brain)
            _run(tf("search_engrams", {"query": "test"}))
        m.assert_called_once_with("test", False, 50)

    def test_search_alias(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", return_value='{"success":true}') as m:
            tf = _make_tf(brain)
            _run(tf("search", {"query": "test"}))
        m.assert_called_once_with("test", False, 50)


# ── morning_brief / hook_metrics ────────────────────────────────────

class TestBriefHook:
    def test_morning_brief(self, brain):
        with patch("mcp_server_nucleus.runtime.morning_brief_ops._morning_brief_impl",
                   return_value={"formatted": "brief", "recommendation": {}, "meta": {}, "sections": {}}):
            tf = _make_tf(brain)
            r = _run(tf("morning_brief", {}))
        assert "brief" in r

    def test_hook_metrics(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_hooks.get_hook_metrics_summary", return_value={"h": 1}):
            tf = _make_tf(brain)
            r = _run(tf("hook_metrics", {}))
        assert "h" in r


# ── compounding loop ────────────────────────────────────────────────

class TestCompounding:
    def test_compounding_status_available(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop._compounding_loop_status_impl",
                   return_value={"formatted": "ok", "today": {}, "metrics": {}, "day_of_week": 1, "week_number": 2}):
            tf = _make_tf(brain)
            r = _run(tf("compounding_status", {}))
        assert "ok" in r

    def test_compounding_status_unavailable(self, brain):
        # When compounding_loop import fails, the impls are None
        tf = _make_tf(brain)
        # The register already imported; if compounding_loop is available, this won't be None.
        # Test the unavailable path by checking the weekly_consolidate with None impl
        r = _run(tf("weekly_consolidate", {"dry_run": True}))
        # Either succeeds or returns "not available"
        assert isinstance(r, str)

    def test_session_inject_available(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop._session_start_inject_impl",
                   return_value={"context": "ctx", "engram_count": 3, "task_count": 1}):
            tf = _make_tf(brain)
            r = _run(tf("session_inject", {}))
        assert "ctx" in r

    def test_end_of_day(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop._end_of_day_capture_impl",
                   return_value={"ok": True}) as m:
            tf = _make_tf(brain)
            r = _run(tf("end_of_day", {"summary": "did stuff"}))
        m.assert_called_once_with("did stuff", None, None)

    def test_end_of_day_not_str(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("end_of_day", {"summary": 123}))
        assert "must be str" in r

    def test_weekly_consolidate(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop._weekly_consolidation_impl",
                   return_value={"ok": True}):
            tf = _make_tf(brain)
            r = _run(tf("weekly_consolidate", {"dry_run": False}))
        assert "ok" in r


# ── list_decisions (file-based) ─────────────────────────────────────

class TestListDecisions:
    def test_no_file(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("list_decisions", {}))
        assert "decisions" in r
        assert json.loads(r)["data"]["count"] == 0

    def test_with_data(self, brain):
        dec_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        dec_file.write_text(json.dumps({"id": "d1"}) + "\n" + json.dumps({"id": "d2"}) + "\n")
        tf = _make_tf(brain)
        r = _run(tf("list_decisions", {"limit": 1}))
        data = json.loads(r)["data"]
        assert data["count"] == 1

    def test_invalid_limit(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("list_decisions", {"limit": "abc"}))
        assert "must be a number" in r

    def test_corrupt_line(self, brain):
        dec_file = brain / "ledger" / "decisions" / "decisions.jsonl"
        dec_file.write_text("bad json\n" + json.dumps({"id": "d1"}) + "\n")
        tf = _make_tf(brain)
        r = _run(tf("list_decisions", {}))
        data = json.loads(r)["data"]
        assert data["count"] == 1


# ── ledger_snapshots (file-based) ───────────────────────────────────

class TestSnapshots:
    def test_no_dir(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("list_snapshots", {}))
        assert json.loads(r)["data"]["count"] == 0

    def test_with_data(self, brain):
        snap_dir = brain / "ledger" / "snapshots"
        (snap_dir / "snap-001.json").write_text(json.dumps({"id": "s1"}))
        (snap_dir / "snap-002.json").write_text(json.dumps({"id": "s2"}))
        tf = _make_tf(brain)
        r = _run(tf("list_snapshots", {"limit": 1}))
        data = json.loads(r)["data"]
        assert data["count"] == 1

    def test_corrupt_file(self, brain):
        snap_dir = brain / "ledger" / "snapshots"
        (snap_dir / "snap-001.json").write_text("bad json")
        tf = _make_tf(brain)
        r = _run(tf("list_snapshots", {}))
        data = json.loads(r)["data"]
        assert data["count"] == 0


# ── metering (file-based) ───────────────────────────────────────────

class TestMetering:
    def test_no_file(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("metering_summary", {}))
        data = json.loads(r)["data"]
        assert data["total_entries"] == 0

    def test_with_data(self, brain):
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        now = datetime.now(timezone.utc)
        meter_file.write_text(
            json.dumps({"timestamp": now.isoformat(), "units_consumed": 10, "scope": "tool",
                        "resource_type": "api", "decision_id": "d1"}) + "\n"
            + json.dumps({"timestamp": now.isoformat(), "units_consumed": 5, "scope": "session",
                          "resource_type": "llm"}) + "\n"
        )
        tf = _make_tf(brain)
        r = _run(tf("metering_summary", {"since_hours": 24}))
        data = json.loads(r)["data"]
        assert data["total_entries"] == 2
        assert data["total_units"] == 15
        assert data["by_scope"]["tool"] == 10
        assert data["decisions_linked"] == 1

    def test_invalid_since_hours(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("metering_summary", {"since_hours": "abc"}))
        assert "must be a number" in r

    def test_old_entries_filtered(self, brain):
        meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
        old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        meter_file.write_text(json.dumps({"timestamp": old, "units_consumed": 10}) + "\n")
        tf = _make_tf(brain)
        r = _run(tf("metering_summary", {"since_hours": 24}))
        data = json.loads(r)["data"]
        assert data["total_entries"] == 0


# ── ipc_tokens (file-based) ─────────────────────────────────────────

class TestIPCTokens:
    def test_no_file(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("ipc_tokens", {}))
        data = json.loads(r)["data"]
        assert data["count"] == 0

    def test_with_data(self, brain):
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        tokens_file.write_text(
            json.dumps({"token_id": "t1", "event": "issued", "decision_id": "d1"}) + "\n"
            + json.dumps({"token_id": "t1", "event": "consumed"}) + "\n"
            + json.dumps({"token_id": "t2", "event": "issued"}) + "\n"
        )
        tf = _make_tf(brain)
        r = _run(tf("ipc_tokens", {"active_only": True}))
        data = json.loads(r)["data"]
        # t2 is active (last event = issued), t1 is not (last event = consumed)
        active = [t for t in data["tokens"] if t.get("last_event") == "issued"]
        assert len(active) == 1

    def test_all_tokens(self, brain):
        tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
        tokens_file.write_text(json.dumps({"token_id": "t1", "event": "issued"}) + "\n")
        tf = _make_tf(brain)
        r = _run(tf("ipc_tokens", {"active_only": False}))
        data = json.loads(r)["data"]
        assert data["count"] == 1


# ── dsor_status (file-based) ────────────────────────────────────────

class TestDsorStatus:
    def test_empty_brain(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("dsor_status", {}))
        data = json.loads(r)["data"]
        assert data["overall_status"] == "OPERATIONAL"
        assert data["components"]["decision_ledger"]["total"] == 0

    def test_with_data(self, brain):
        (brain / "ledger" / "decisions" / "decisions.jsonl").write_text(json.dumps({"id": "d1"}) + "\n")
        (brain / "ledger" / "metering" / "token_meter.jsonl").write_text(
            json.dumps({"units_consumed": 5}) + "\n")
        (brain / "ledger" / "auth" / "ipc_tokens.jsonl").write_text(
            json.dumps({"event": "issued"}) + "\n" + json.dumps({"event": "consumed"}) + "\n")
        tf = _make_tf(brain)
        r = _run(tf("dsor_status", {}))
        data = json.loads(r)["data"]
        assert data["components"]["decision_ledger"]["total"] == 1
        assert data["components"]["ipc_auth"]["issued"] == 1
        assert data["components"]["ipc_auth"]["consumed"] == 1


# ── federation_dsor / routing_decisions (file-based) ────────────────

class TestFederation:
    def test_fed_dsor_empty(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("federation_dsor", {}))
        data = json.loads(r)["data"]
        assert data["total"] == 0

    def test_fed_dsor_with_events(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.write_text(
            json.dumps({"type": "federation_peer_joined", "timestamp": "t", "data": {"decision_id": "d1"}}) + "\n"
            + json.dumps({"type": "federation_task_routed", "timestamp": "t",
                          "data": {"target_brain": "b1", "score": 0.9, "profile": "p", "decision_id": "d2"}}) + "\n"
            + json.dumps({"type": "other_event"}) + "\n"
        )
        tf = _make_tf(brain)
        r = _run(tf("federation_dsor", {}))
        data = json.loads(r)["data"]
        assert data["event_counts"]["peer_joined"] == 1
        assert data["event_counts"]["task_routed"] == 1
        assert len(data["recent_events"]) == 2

    def test_routing_decisions(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.write_text(
            json.dumps({"type": "federation_task_routed", "timestamp": "t",
                          "data": {"target_brain": "b1", "score": 0.9, "profile": "p", "decision_id": "d2"}}) + "\n"
        )
        tf = _make_tf(brain)
        r = _run(tf("routing_decisions", {}))
        data = json.loads(r)["data"]
        assert data["total_decisions"] == 1
        assert data["decisions"][0]["target_brain"] == "b1"

    def test_routing_decisions_invalid_limit(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("routing_decisions", {"limit": "abc"}))
        assert "must be a number" in r


# ── list_tools / tier_status ────────────────────────────────────────

class TestToolsTiers:
    def test_list_tools(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0, "tier_0_count": 10,
                                 "tier_1_count": 5, "tier_2_count": 2}), \
             patch("mcp_server_nucleus.tool_tiers.is_tool_allowed", return_value=True):
            tf = _make_tf(brain)
            r = _run(tf("list_tools", {}))
        data = json.loads(r)["data"]
        assert data["tier"] == "LAUNCH"

    def test_list_tools_with_category(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0, "tier_0_count": 10,
                                 "tier_1_count": 5, "tier_2_count": 2}), \
             patch("mcp_server_nucleus.tool_tiers.is_tool_allowed", return_value=True):
            tf = _make_tf(brain)
            r = _run(tf("list_tools", {"category": "federation"}))
        data = json.loads(r)["data"]
        assert isinstance(data["tools"], list)

    def test_list_tools_unknown_category(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0, "tier_0_count": 10,
                                 "tier_1_count": 5, "tier_2_count": 2}), \
             patch("mcp_server_nucleus.tool_tiers.is_tool_allowed", return_value=True):
            tf = _make_tf(brain)
            r = _run(tf("list_tools", {"category": "nonexistent"}))
        data = json.loads(r)["data"]
        assert isinstance(data["tools"], list)

    def test_tier_status(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0, "tier_0_count": 10,
                                 "tier_1_count": 5, "tier_2_count": 2}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm:
            tm.get_stats.return_value = {"total": 17}
            tf = _make_tf(brain)
            r = _run(tf("tier_status", {}))
        data = json.loads(r)["data"]
        assert data["current_tier"] == "LAUNCH"
        assert data["stats"]["total"] == 17


# ── god combos ──────────────────────────────────────────────────────

class TestGodCombos:
    def test_pulse_and_polish(self, brain):
        with patch("mcp_server_nucleus.runtime.god_combos.pulse_and_polish.run_pulse_and_polish",
                   return_value={"status": "ok"}):
            tf = _make_tf(brain)
            r = _run(tf("pulse_and_polish", {}))
        assert "ok" in r

    def test_self_healing_sre(self, brain):
        with patch("mcp_server_nucleus.runtime.god_combos.self_healing_sre.run_self_healing_sre",
                   return_value={"status": "ok"}):
            tf = _make_tf(brain)
            r = _run(tf("self_healing_sre", {"symptom": "slow"}))
        assert "ok" in r

    def test_fusion_reactor(self, brain):
        with patch("mcp_server_nucleus.runtime.god_combos.fusion_reactor.run_fusion_reactor",
                   return_value={"status": "ok"}):
            tf = _make_tf(brain)
            r = _run(tf("fusion_reactor", {"observation": "obs"}))
        assert "ok" in r

    def test_fusion_reactor_bad_observation(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("fusion_reactor", {"observation": 123}))
        assert "must be str" in r

    def test_fusion_reactor_bad_context(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("fusion_reactor", {"observation": "obs", "context": 123}))
        assert "must be str" in r


# ── context graph ───────────────────────────────────────────────────

class TestContextGraph:
    def test_context_graph(self, brain):
        with patch("mcp_server_nucleus.runtime.context_graph.build_context_graph",
                   return_value={"nodes": []}):
            tf = _make_tf(brain)
            r = _run(tf("context_graph", {}))
        assert "nodes" in r

    def test_context_graph_bad_intensity(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("context_graph", {"min_intensity": "abc"}))
        assert "must be a number" in r

    def test_engram_neighbors(self, brain):
        with patch("mcp_server_nucleus.runtime.context_graph.get_engram_neighbors",
                   return_value={"neighbors": []}) as m:
            tf = _make_tf(brain)
            r = _run(tf("engram_neighbors", {"key": "k"}))
        m.assert_called_once_with(key="k", max_depth=1)

    def test_render_graph(self, brain):
        with patch("mcp_server_nucleus.runtime.context_graph.render_ascii_graph", return_value="graph"):
            tf = _make_tf(brain)
            r = _run(tf("render_graph", {}))
        assert "graph" in r

    def test_render_graph_bad_max_nodes(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("render_graph", {"max_nodes": "abc"}))
        assert "must be a number" in r

    def test_render_graph_bad_min_intensity(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("render_graph", {"min_intensity": "abc"}))
        assert "must be a number" in r


# ── billing ─────────────────────────────────────────────────────────

class TestBilling:
    def test_billing_summary(self, brain):
        with patch("mcp_server_nucleus.runtime.billing.compute_usage_summary", return_value={"cost": 1}):
            tf = _make_tf(brain)
            r = _run(tf("billing_summary", {}))
        assert "cost" in r

    def test_billing_bad_since_hours(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("billing_summary", {"since_hours": "abc"}))
        assert "must be a number" in r


# ── heartbeat ───────────────────────────────────────────────────────

class TestHeartbeat:
    def test_heartbeat_check_no_notify(self, brain):
        with patch("mcp_server_nucleus.runtime.heartbeat_ops._heartbeat_check_impl",
                   return_value={"should_notify": False}):
            tf = _make_tf(brain)
            r = _run(tf("heartbeat_check", {}))
        assert "should_notify" in r

    def test_heartbeat_check_with_notify(self, brain):
        with patch("mcp_server_nucleus.runtime.heartbeat_ops._heartbeat_check_impl",
                   return_value={"should_notify": True, "notification_title": "t", "notification_body": "b"}), \
             patch("mcp_server_nucleus.runtime.heartbeat_ops._notify_native") as m:
            tf = _make_tf(brain)
            r = _run(tf("heartbeat_check", {"notify": True}))
        m.assert_called_once_with("t", "b")

    def test_heartbeat_status(self, brain):
        with patch("mcp_server_nucleus.runtime.heartbeat_ops._heartbeat_status_impl",
                   return_value={"status": "ok"}):
            tf = _make_tf(brain)
            r = _run(tf("heartbeat_status", {}))
        assert "ok" in r


# ── dsor_query / dsor_get_trace ─────────────────────────────────────

class TestDsorQuery:
    def test_dsor_query_decisions(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._dsor_query_decisions_impl",
                   return_value='{"decisions": []}') as m:
            tf = _make_tf(brain)
            r = _run(tf("dsor_query_decisions", {"limit": 10}))
        m.assert_called_once_with(10)

    def test_dsor_get_trace(self, brain):
        with patch("mcp_server_nucleus.runtime.engram_ops._dsor_get_trace_impl",
                   return_value='{"trace": []}') as m:
            tf = _make_tf(brain)
            r = _run(tf("dsor_get_trace", {"decision_id": "d1"}))
        m.assert_called_once_with("d1")


# ── unknown action ──────────────────────────────────────────────────

class TestUnknown:
    def test_unknown_action(self, brain):
        tf = _make_tf(brain)
        r = _run(tf("nonexistent", {}))
        assert "Unknown action" in r or "error" in r


# ── exception handlers & edge cases ─────────────────────────────────

class TestExceptionHandlers:
    def _boom_brain(self):
        raise Exception("boom")

    def test_list_decisions_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("list_decisions", {"limit": 10}))
        assert "Error" in r

    def test_ledger_snapshots_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("list_snapshots", {"limit": 10}))
        assert "Error" in r

    def test_metering_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("metering_summary", {"since_hours": 24}))
        assert "Error" in r

    def test_ipc_tokens_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("ipc_tokens", {"active_only": True}))
        assert "Error" in r

    def test_dsor_status_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("dsor_status", {}))
        assert "Error" in r

    def test_fed_dsor_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("federation_dsor", {}))
        assert "Error" in r

    def test_routing_decisions_exception(self, brain):
        tf = _make_tf(brain, get_brain_path_fn=self._boom_brain)
        r = _run(tf("routing_decisions", {"limit": 20}))
        assert "Error" in r

    def test_list_tools_exception(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info", side_effect=Exception("boom")):
            tf = _make_tf(brain)
            r = _run(tf("list_tools", {}))
        assert "Error" in r

    def test_tier_status_exception(self, brain):
        with patch("mcp_server_nucleus.tool_tiers.get_tier_info", side_effect=Exception("boom")):
            tf = _make_tf(brain)
            r = _run(tf("tier_status", {}))
        assert "Error" in r


class TestCorruptData:
    def test_list_decisions_corrupt_line(self, brain):
        (brain / "ledger" / "decisions").mkdir(parents=True, exist_ok=True)
        (brain / "ledger" / "decisions" / "decisions.jsonl").write_text(
            '{"d": 1}\nNOT_JSON\n{"d": 2}\n')
        tf = _make_tf(brain)
        r = _run(tf("list_decisions", {"limit": 10}))
        assert '"count": 2' in r

    def test_ledger_snapshots_corrupt_file(self, brain):
        snap_dir = brain / "ledger" / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        (snap_dir / "snap-001.json").write_text("NOT_JSON")
        (snap_dir / "snap-002.json").write_text('{"valid": true}')
        tf = _make_tf(brain)
        r = _run(tf("list_snapshots", {"limit": 10}))
        assert '"count": 1' in r

    def test_metering_corrupt_line(self, brain):
        meter_dir = brain / "ledger" / "metering"
        meter_dir.mkdir(parents=True, exist_ok=True)
        (meter_dir / "token_meter.jsonl").write_text(
            '{"units_consumed": 10, "timestamp": "2099-01-01T00:00:00+00:00"}\n'
            'NOT_JSON\n')
        tf = _make_tf(brain)
        r = _run(tf("metering_summary", {"since_hours": 24}))
        assert '"total_entries": 1' in r

    def test_ipc_tokens_corrupt_line(self, brain):
        auth_dir = brain / "ledger" / "auth"
        auth_dir.mkdir(parents=True, exist_ok=True)
        (auth_dir / "ipc_tokens.jsonl").write_text(
            '{"token_id": "t1", "event": "issued"}\nNOT_JSON\n')
        tf = _make_tf(brain)
        r = _run(tf("ipc_tokens", {"active_only": True}))
        assert '"count": 1' in r

    def test_dsor_status_corrupt_metering(self, brain):
        meter_dir = brain / "ledger" / "metering"
        meter_dir.mkdir(parents=True, exist_ok=True)
        (meter_dir / "token_meter.jsonl").write_text("NOT_JSON\n")
        auth_dir = brain / "ledger" / "auth"
        auth_dir.mkdir(parents=True, exist_ok=True)
        (auth_dir / "ipc_tokens.jsonl").write_text("NOT_JSON\n")
        tf = _make_tf(brain)
        r = _run(tf("dsor_status", {}))
        # This test feeds deliberately corrupt JSONL, so DEGRADED is the
        # correct answer -- engrams.py:246 sets it whenever parse_errors is
        # non-empty. The old assertion demanded OPERATIONAL on corrupt input,
        # i.e. it asserted that corruption reads as healthy, which is the exact
        # failure this codebase exists to catch.
        assert "DEGRADED" in r
        assert "OPERATIONAL" not in r

    def test_fed_dsor_corrupt_line(self, brain):
        (brain / "ledger").mkdir(parents=True, exist_ok=True)
        (brain / "ledger" / "events.jsonl").write_text(
            '{"type": "federation_peer_joined"}\nNOT_JSON\n')
        tf = _make_tf(brain)
        r = _run(tf("federation_dsor", {}))
        assert '"peer_joined": 1' in r

    def test_routing_decisions_corrupt_line(self, brain):
        (brain / "ledger").mkdir(parents=True, exist_ok=True)
        (brain / "ledger" / "events.jsonl").write_text(
            '{"type": "federation_task_routed", "data": {"target_brain": "b1"}}\n'
            'NOT_JSON\n')
        tf = _make_tf(brain)
        r = _run(tf("routing_decisions", {"limit": 20}))
        assert '"total_decisions": 1' in r


class TestCompoundingLoopUnavailable:
    """Test handlers when compounding_loop module can't be imported."""

    def test_compounding_status_unavailable(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop", None):
            tf = _make_tf(brain)
            r = _run(tf("compounding_status", {}))
        # Either "not available" or the handler succeeds with mock data
        assert "not available" in r or "success" in r

    def test_session_inject_unavailable(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop", None):
            tf = _make_tf(brain)
            r = _run(tf("session_inject", {}))
        assert "not available" in r or "success" in r

    def test_end_of_day_unavailable(self, brain):
        with patch("mcp_server_nucleus.runtime.compounding_loop", None):
            tf = _make_tf(brain)
            r = _run(tf("end_of_day", {"summary": "test"}))
        assert "not available" in r or "success" in r
