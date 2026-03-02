"""Engram, health, version, audit, morning brief, compounding loop,
DSoR, and tier system tools.

Super-Tools Facade: All 25 engram/health/observability actions exposed via
a single `nucleus_engrams(action, params)` MCP tool.
"""

import json
from typing import Dict, List, Optional

from ._dispatch import dispatch, async_dispatch


def register(mcp, helpers):
    """Register the nucleus_engrams facade tool with the MCP server."""
    make_response = helpers["make_response"]
    _emit_event = helpers["emit_event"]
    get_brain_path = helpers["get_brain_path"]

    from ..runtime.health_ops import (
        _brain_health_impl, _brain_version_impl, _brain_audit_log_impl,
    )
    from ..runtime.engram_ops import (
        _brain_write_engram_impl, _brain_query_engrams_impl,
        _brain_search_engrams_impl, _brain_governance_status_impl,
    )
    from ..runtime.morning_brief_ops import _morning_brief_impl
    from ..runtime.engram_hooks import get_hook_metrics_summary
    from ..runtime.compounding_loop import (
        _compounding_loop_status_impl, _end_of_day_capture_impl,
        _session_start_inject_impl, _weekly_consolidation_impl,
    )
    from ..tool_tiers import get_tier_info, is_tool_allowed, tier_manager
    from ..runtime.schema_gen import generate_tool_schema

    # ── Handler functions ─────────────────────────────────────

    def _h_version():
        info = _brain_version_impl()
        return f"🧠 NUCLEUS VERSION INFO\n═══════════════════════════════════════\n\n📦 VERSION\n   Nucleus: {info['nucleus_version']}\n   Python: {info['python_version']}\n   Platform: {info['platform']} {info['platform_release']}\n\n🔧 CAPABILITIES\n   MCP Tools: {info['mcp_tools_count']}+\n   Architecture: {info['architecture']}\n   Status: {info['status']}\n\n   GitHub: https://github.com/eidetic-works/nucleus-mcp\n   PyPI: pip install nucleus-mcp\n   Docs: https://nucleusos.dev"

    async def _h_export_schema():
        schema = await generate_tool_schema(mcp)
        raw = json.dumps(schema, indent=2)
        MAX_SCHEMA_CHARS = 200_000  # ~200KB cap to prevent context exhaustion
        if len(raw) > MAX_SCHEMA_CHARS:
            tool_count = len(schema.get("paths", {}))
            return make_response(True, data={
                "message": f"Schema too large ({len(raw):,} chars, {tool_count} paths). Use export_to_file instead.",
                "tool_count": tool_count,
                "size_chars": len(raw),
                "cap": MAX_SCHEMA_CHARS,
                "hint": "Call performance_metrics with export_to_file=true, or use the CLI: nucleus export-schema"
            })
        return raw

    def _h_perf_metrics(export_to_file=False):
        from ..runtime.profiling import get_metrics, get_metrics_summary, export_metrics_to_file
        metrics = get_metrics()
        if not metrics:
            return make_response(True, data={"message": "No metrics collected. Set NUCLEUS_PROFILING=true."})
        if export_to_file:
            try:
                filepath = export_metrics_to_file()
                return make_response(True, data={"metrics": metrics, "exported_to": filepath})
            except Exception as e:
                return make_response(False, error=f"Export failed: {e}")
        return make_response(True, data={"summary": get_metrics_summary(), "metrics": metrics})

    def _h_prom_metrics(format="prometheus"):
        from ..runtime.prometheus import get_prometheus_metrics, get_metrics_json
        if format.lower() == "json":
            return make_response(True, data=get_metrics_json())
        return get_prometheus_metrics()

    def _h_morning_brief():
        result = _morning_brief_impl()
        return make_response(True, data={
            "brief": result.get("formatted", ""),
            "recommendation": result.get("recommendation", {}),
            "meta": result.get("meta", {}),
            "sections": result.get("sections", {}),
        })

    def _h_compounding_status():
        result = _compounding_loop_status_impl()
        return make_response(True, data={
            "formatted": result.get("formatted", ""),
            "today": result.get("today", {}),
            "metrics": result.get("metrics", {}),
            "day": result.get("day_of_week"),
            "week": result.get("week_number"),
        })

    def _h_session_inject():
        result = _session_start_inject_impl()
        return make_response(True, data={
            "context": result.get("context", ""),
            "engram_count": result.get("engram_count", 0),
            "task_count": result.get("task_count", 0),
        })

    def _h_list_decisions(limit=20):
        try:
            brain = get_brain_path()
            decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
            if not decisions_file.exists():
                return make_response(True, data={"decisions": [], "count": 0})
            decisions = []
            with open(decisions_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try: decisions.append(json.loads(line))
                        except: continue
            decisions = decisions[-limit:][::-1]
            return make_response(True, data={"decisions": decisions, "count": len(decisions)})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_ledger_snapshots(limit=10):
        try:
            brain = get_brain_path()
            snapshots_dir = brain / "ledger" / "snapshots"
            if not snapshots_dir.exists():
                return make_response(True, data={"snapshots": [], "count": 0})
            snapshots = []
            for snap_file in sorted(snapshots_dir.glob("snap-*.json"), reverse=True)[:limit]:
                try:
                    with open(snap_file, encoding='utf-8') as f:
                        snapshots.append(json.load(f))
                except: continue
            return make_response(True, data={"snapshots": snapshots, "count": len(snapshots)})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_metering(since_hours=24):
        try:
            brain = get_brain_path()
            meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
            if not meter_file.exists():
                return make_response(True, data={"total_entries": 0, "total_units": 0})
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
            entries = []
            with open(meter_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get("timestamp", "") >= cutoff:
                                entries.append(entry)
                        except: continue
            summary = {"total_entries": len(entries), "total_units": sum(e.get("units_consumed", 0) for e in entries), "by_scope": {}, "by_resource_type": {}, "decisions_linked": sum(1 for e in entries if e.get("decision_id")), "since_hours": since_hours}
            for e in entries:
                scope = e.get("scope", "unknown")
                rtype = e.get("resource_type", "unknown")
                units = e.get("units_consumed", 0)
                summary["by_scope"][scope] = summary["by_scope"].get(scope, 0) + units
                summary["by_resource_type"][rtype] = summary["by_resource_type"].get(rtype, 0) + units
            return make_response(True, data=summary)
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_ipc_tokens(active_only=True):
        try:
            brain = get_brain_path()
            tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
            if not tokens_file.exists():
                return make_response(True, data={"tokens": [], "count": 0})
            events = []
            with open(tokens_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try: events.append(json.loads(line))
                        except: continue
            token_states = {}
            for event in events:
                tid = event.get("token_id")
                if tid:
                    token_states.setdefault(tid, {"token_id": tid, "events": []})
                    token_states[tid]["events"].append(event)
                    token_states[tid]["last_event"] = event.get("event")
                    token_states[tid]["decision_id"] = event.get("decision_id")
            tokens = list(token_states.values())
            if active_only:
                tokens = [t for t in tokens if t.get("last_event") == "issued"]
            return make_response(True, data={"tokens": tokens[-20:], "count": len(tokens), "active_only": active_only})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_dsor_status():
        try:
            brain = get_brain_path()
            decisions_file = brain / "ledger" / "decisions" / "decisions.jsonl"
            decision_count = sum(1 for line in open(decisions_file) if line.strip()) if decisions_file.exists() else 0
            snapshots_dir = brain / "ledger" / "snapshots"
            snapshot_count = len(list(snapshots_dir.glob("snap-*.json"))) if snapshots_dir.exists() else 0
            meter_file = brain / "ledger" / "metering" / "token_meter.jsonl"
            meter_count, total_units = 0, 0
            if meter_file.exists():
                for line in open(meter_file):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            meter_count += 1; total_units += entry.get("units_consumed", 0)
                        except: pass
            tokens_file = brain / "ledger" / "auth" / "ipc_tokens.jsonl"
            token_issued, token_consumed = 0, 0
            if tokens_file.exists():
                for line in open(tokens_file):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("event") == "issued": token_issued += 1
                            elif event.get("event") == "consumed": token_consumed += 1
                        except: pass
            return make_response(True, data={"version": "0.6.0", "feature": "DSoR", "components": {"decision_ledger": {"status": "ACTIVE" if decision_count else "READY", "total": decision_count}, "snapshots": {"status": "ACTIVE" if snapshot_count else "READY", "total": snapshot_count}, "ipc_auth": {"status": "ACTIVE" if token_issued else "READY", "issued": token_issued, "consumed": token_consumed}, "metering": {"status": "ACTIVE" if meter_count else "READY", "entries": meter_count, "units": total_units}}, "overall_status": "OPERATIONAL"})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_fed_dsor():
        try:
            brain = get_brain_path()
            events_file = brain / "ledger" / "events.jsonl"
            fed_events = {"peer_joined": 0, "peer_left": 0, "peer_suspect": 0, "leader_elected": 0, "task_routed": 0, "state_synced": 0}
            recent = []
            if events_file.exists():
                for line in open(events_file):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            et = event.get("type", "")
                            for key in fed_events:
                                if et == f"federation_{key}":
                                    fed_events[key] += 1
                            if et.startswith("federation_"):
                                recent.append({"type": et, "timestamp": event.get("timestamp"), "decision_id": event.get("data", {}).get("decision_id")})
                        except: pass
            return make_response(True, data={"event_counts": fed_events, "total": sum(fed_events.values()), "recent_events": recent[-10:]})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_routing_decisions(limit=20):
        try:
            brain = get_brain_path()
            events_file = brain / "ledger" / "events.jsonl"
            decisions = []
            if events_file.exists():
                for line in open(events_file):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("type") == "federation_task_routed":
                                data = event.get("data", {})
                                decisions.append({"timestamp": event.get("timestamp"), "target_brain": data.get("target_brain"), "score": data.get("score"), "profile": data.get("profile"), "decision_id": data.get("decision_id")})
                        except: pass
            return make_response(True, data={"total_decisions": len(decisions[-limit:]), "decisions": decisions[-limit:]})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_list_tools(category=None):
        try:
            tier_info_val = get_tier_info()
            import mcp_server_nucleus as nucleus
            all_funcs = [name for name in dir(nucleus) if name.startswith('brain_') or name.startswith('nucleus_') and is_tool_allowed(name)]
            all_tools = sorted(all_funcs)
            if category:
                cat_map = {"federation": ["nucleus_federation"], "memory": ["brain_write_engram", "brain_query_engrams"], "governance": ["nucleus_governance"]}
                if category.lower() in cat_map:
                    target = set(cat_map[category.lower()])
                    all_tools = [t for t in all_tools if t in target]
                else:
                    all_tools = [t for t in all_tools if category.lower() in t.lower()]
            return make_response(True, data={"tier": tier_info_val["tier_name"], "tier_level": tier_info_val["active_tier"], "total_tools": len(all_tools), "tools": all_tools})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_tier_status():
        try:
            info = get_tier_info()
            stats = tier_manager.get_stats()
            return make_response(True, data={"version": "0.6.0", "current_tier": info["tier_name"], "tier_level": info["active_tier"], "tier_breakdown": {"tier_0": info["tier_0_count"], "tier_1": info["tier_1_count"], "tier_2": info["tier_2_count"]}, "stats": stats})
        except Exception as e:
            return make_response(False, error=f"Error: {e}")

    def _h_pulse_and_polish(write_engram=True):
        from ..runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        return make_response(True, data=run_pulse_and_polish(write_engram=write_engram))

    def _h_self_healing_sre(symptom, write_engram=True):
        from ..runtime.god_combos.self_healing_sre import run_self_healing_sre
        return make_response(True, data=run_self_healing_sre(symptom=symptom, write_engram=write_engram))

    def _h_fusion_reactor(observation, context="Decision", intensity=6, write_engrams=True):
        from ..runtime.god_combos.fusion_reactor import run_fusion_reactor
        return make_response(True, data=run_fusion_reactor(observation=observation, context=context, intensity=intensity, write_engrams=write_engrams))

    def _h_context_graph(include_edges=True, min_intensity=1):
        from ..runtime.context_graph import build_context_graph
        return make_response(True, data=build_context_graph(include_edges=include_edges, min_intensity=min_intensity))

    def _h_engram_neighbors(key, max_depth=1):
        from ..runtime.context_graph import get_engram_neighbors
        return make_response(True, data=get_engram_neighbors(key=key, max_depth=max_depth))

    def _h_billing_summary(since_hours=None, group_by="tool"):
        from ..runtime.billing import compute_usage_summary
        return make_response(True, data=compute_usage_summary(since_hours=since_hours, group_by=group_by))

    def _h_render_graph(max_nodes=30, min_intensity=1):
        from ..runtime.context_graph import render_ascii_graph
        return make_response(True, data={"ascii": render_ascii_graph(max_nodes=max_nodes, min_intensity=min_intensity)})

    ROUTER = {
        "health": lambda: _brain_health_impl(),
        "version": _h_version,
        "export_schema": _h_export_schema,
        "performance_metrics": _h_perf_metrics,
        "prometheus_metrics": _h_prom_metrics,
        "audit_log": lambda limit=20: _brain_audit_log_impl(limit),
        "write_engram": lambda key, value, context="Decision", intensity=5: _brain_write_engram_impl(key, value, context, intensity),
        "query_engrams": lambda context=None, min_intensity=1, limit=50: _brain_query_engrams_impl(context, min_intensity, limit),
        "search_engrams": lambda query, case_sensitive=False, limit=50: _brain_search_engrams_impl(query, case_sensitive, limit),
        "governance_status": lambda: _brain_governance_status_impl(),
        "morning_brief": _h_morning_brief,
        "hook_metrics": lambda: make_response(True, data=get_hook_metrics_summary()),
        "compounding_status": _h_compounding_status,
        "end_of_day": lambda summary, key_decisions=None, blockers=None: make_response(True, data=_end_of_day_capture_impl(summary, key_decisions, blockers)),
        "session_inject": _h_session_inject,
        "weekly_consolidate": lambda dry_run=True: make_response(True, data=_weekly_consolidation_impl(dry_run)),
        "list_decisions": _h_list_decisions,
        "list_snapshots": _h_ledger_snapshots,
        "metering_summary": _h_metering,
        "ipc_tokens": _h_ipc_tokens,
        "dsor_status": _h_dsor_status,
        "federation_dsor": _h_fed_dsor,
        "routing_decisions": _h_routing_decisions,
        "list_tools": _h_list_tools,
        "tier_status": _h_tier_status,
        "pulse_and_polish": lambda write_engram=True: _h_pulse_and_polish(write_engram),
        "self_healing_sre": lambda symptom, write_engram=True: _h_self_healing_sre(symptom, write_engram),
        "fusion_reactor": lambda observation, context="Decision", intensity=6, write_engrams=True: _h_fusion_reactor(observation, context, intensity, write_engrams),
        "context_graph": lambda include_edges=True, min_intensity=1: _h_context_graph(include_edges, min_intensity),
        "engram_neighbors": lambda key, max_depth=1: _h_engram_neighbors(key, max_depth),
        "billing_summary": lambda since_hours=None, group_by="tool": _h_billing_summary(since_hours, group_by),
        "render_graph": lambda max_nodes=30, min_intensity=1: _h_render_graph(max_nodes, min_intensity),
    }

    @mcp.tool()
    async def nucleus_engrams(action: str, params: dict = {}) -> str:
        """Engrams, health, observability, DSoR & tier system tools.

Actions:
  health              - Get system health status
  version             - Get Nucleus version info
  export_schema       - Export MCP toolset as JSON Schema
  performance_metrics - Get perf metrics. params: {export_to_file?}
  prometheus_metrics  - Get Prometheus metrics. params: {format?}
  audit_log           - View cryptographic interaction log. params: {limit?}
  write_engram        - Write engram to memory. params: {key, value, context?, intensity?}. context: Feature|Architecture|Brand|Strategy|Decision. intensity: 1-10.
  query_engrams       - Query engrams. params: {context?, min_intensity?, limit?}. limit default 50, max 500.
  search_engrams      - Search engrams. params: {query, case_sensitive?, limit?}. limit default 50, max 500.
  governance_status   - Get governance status
  morning_brief       - Daily Nucleus Morning Brief
  hook_metrics        - Monitor auto-write engram hooks
  compounding_status  - Compounding Loop status
  end_of_day          - Capture EOD learnings. params: {summary, key_decisions?, blockers?}
  session_inject      - Session-start context injection
  weekly_consolidate  - Weekly consolidation. params: {dry_run?}
  list_decisions      - List DecisionMade events. params: {limit?}
  list_snapshots      - List context snapshots. params: {limit?}
  metering_summary    - Token metering summary. params: {since_hours?}
  ipc_tokens          - List IPC auth tokens. params: {active_only?}
  dsor_status         - Comprehensive DSoR status
  pulse_and_polish    - God Combo: automated health check pipeline. params: {write_engram?}. Runs prometheus→audit→brief→engram.
  self_healing_sre    - God Combo: SRE diagnosis pipeline. params: {symptom, write_engram?}. Runs search→metrics→diagnose→recommend.
  fusion_reactor      - God Combo: self-reinforcing memory loop. params: {observation, context?, intensity?, write_engrams?}. Compounds knowledge.
  context_graph       - Build engram relationship graph. params: {include_edges?, min_intensity?}. Returns nodes, edges, clusters.
  engram_neighbors    - Get neighborhood of an engram. params: {key, max_depth?}. BFS traversal of context graph.
  billing_summary     - Usage cost tracking from audit logs. params: {since_hours?, group_by?}. group_by: tool|tier|session.
  render_graph        - ASCII visualization of engram context graph. params: {max_nodes?, min_intensity?}.
  federation_dsor     - Federation DSoR status
  routing_decisions   - Query routing decision history. params: {limit?}
  list_tools          - List tools at current tier. params: {category?}
  tier_status         - Get tier configuration status
"""
        return await async_dispatch(action, params, ROUTER, "nucleus_engrams")

    return [("nucleus_engrams", nucleus_engrams)]
