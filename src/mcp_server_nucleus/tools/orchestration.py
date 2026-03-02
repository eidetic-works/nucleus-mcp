"""Orchestration tools: satellite, commitments, LLM tiers, telemetry, slots,
sprints, file changes, gcloud, marketing, critic, swarm, memory, consent,
strategy, sessions, ingestion, and dashboard tools.

Super-Tools Facade: 65 orchestration tools split into 5 sub-facades:
  nucleus_orchestration  — satellite, commitments, loops, patterns, metrics, challenges
  nucleus_telemetry      — LLM tiers, telemetry, protocol, handoff
  nucleus_slots          — orchestrate, slot ops, sprints, missions
  nucleus_infra          — file changes, gcloud, render, marketing, strategy
  nucleus_agents         — spawn, critic, swarm, memory, consent, sessions, ingestion, dashboard
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ._dispatch import dispatch, async_dispatch

def _fix_code_impl(file_path, issues_context):
    try:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"status": "error", "message": "File not found"})
        original_content = path.read_text(encoding='utf-8')
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        backup_path.write_text(original_content, encoding='utf-8')
        system_prompt = (
            "You are 'The Fixer', an autonomous code repair agent. "
            "Your goal is to fix specific issues in the provided code while maintaining strict adherence to the project's style (Nucleus/Neon/Context-Aware). "
            "Return ONLY the full corrected file content inside a code block. Do not wrap in markdown or add commentary."
        )
        user_prompt = f"\n            TARGET: {file_path}\n            \n            ISSUES TO FIX:\n            {issues_context}\n            \n            CURRENT CONTENT:\n            ```\n            {original_content}\n            ```\n            \n            INSTRUCTIONS:\n            1. Fix the issues listed above.\n            2. Ensure accessibility (ARIA) and style compliance (Globals/Neon) if UI.\n            3. Do NOT break existing logic.\n            4. Return the COMPLETE new file content.\n            "
        from ..runtime.llm_client import DualEngineLLM
        llm = DualEngineLLM()
        fix_response = llm.generate_content(prompt=user_prompt, system_instruction=system_prompt)
        new_content = fix_response.text.strip()
        if "```" in new_content:
            parts = new_content.split("```")
            candidate = parts[1]
            if candidate.startswith(("typescript", "tsx", "python", "css", "javascript", "json")):
                candidate = "\n".join(candidate.split("\n")[1:])
            new_content = candidate
        path.write_text(new_content, encoding='utf-8')
        return json.dumps({"status": "success", "message": f"Applied fix to {path.name}", "backup": str(backup_path)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def register(mcp, helpers):
    """Register 5 orchestration sub-facade tools with the MCP server."""
    make_response = helpers["make_response"]
    _emit_event = helpers["emit_event"]
    get_brain_path = helpers["get_brain_path"]
    get_orch = helpers["get_orch"]

    from ..runtime.satellite_ops import _get_satellite_view, _format_satellite_cli
    from .. import commitment_ledger
    from ..runtime.telemetry_ops import (
        _brain_record_interaction_impl, _brain_value_ratio_impl,
        _brain_check_kill_switch_impl, _brain_pause_notifications_impl,
        _brain_resume_notifications_impl, _brain_record_feedback_impl,
        _brain_mark_high_impact_impl,
    )
    from ..runtime.task_ops import _list_tasks, _add_task
    from ..runtime.event_ops import _emit_event as _emit_ev, _read_events
    from ..runtime.artifact_ops import _read_artifact
    from ..runtime.trigger_ops import _trigger_agent_impl
    from ..runtime.orchestrate_ops import _brain_orchestrate_impl
    from ..runtime.deployment_ops import _start_deploy_poll, _check_deploy_status, _complete_deploy, _run_smoke_test
    from ..runtime.ingestion_ops import (
        _brain_ingest_tasks_impl, _brain_rollback_ingestion_impl, _brain_ingestion_stats_impl,
    )
    from ..runtime.dashboard_ops import (
        _brain_enhanced_dashboard_impl, _brain_snapshot_dashboard_impl,
        _brain_list_snapshots_impl, _brain_get_alerts_impl, _brain_set_alert_threshold_impl,
    )
    from ..runtime.sprint_ops import (
        _brain_autopilot_sprint_v2_impl, _brain_start_mission_impl,
        _brain_mission_status_impl, _brain_halt_sprint_impl, _brain_resume_sprint_impl,
    )

    # ════════════════════════════════════════════════════════════
    # FACADE 1: nucleus_orchestration
    # ════════════════════════════════════════════════════════════

    def _h_satellite(detail_level="standard"):
        view = _get_satellite_view(detail_level)
        return make_response(True, data=_format_satellite_cli(view))

    def _h_scan_commitments():
        try:
            brain = get_brain_path()
            result = commitment_ledger.scan_for_commitments(brain)
            return f"✅ Scan complete. Found {result.get('new_found', 0)} new items."
        except Exception as e:
            return f"Error: {e}"

    def _h_archive_stale():
        try:
            brain = get_brain_path()
            count = commitment_ledger.auto_archive_stale(brain)
            return f"✅ Archive complete. Archived {count} stale items."
        except Exception as e:
            return f"Error: {e}"

    def _h_export():
        try:
            brain = get_brain_path()
            if hasattr(commitment_ledger, 'export_brain'):
                result = commitment_ledger.export_brain(brain)
                return f"✅ {result}"
            return "Error: export_brain validation failed (function missing)."
        except Exception as e:
            return f"Error: {e}"

    def _h_list_commitments(tier=None):
        try:
            brain = get_brain_path()
            ledger = commitment_ledger.load_ledger(brain)
            all_commitments = ledger.get('commitments', [])
            commitments = [c for c in all_commitments if c.get('status') == 'open']
            if tier:
                commitments = [c for c in commitments if c.get('tier') == tier]
            if not commitments:
                return "✅ No open commitments!"
            output = f"**Open Commitments ({len(commitments)} total)**\n\n"
            for comm in commitments:
                tier_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(comm["tier"], "⚪")
                output += f"{tier_emoji} **{comm['description'][:60]}**\n"
                output += f"   Age: {comm['age_days']} days | Suggested: {comm['suggested_action']}\n"
                output += f"   Reason: {comm['suggested_reason']}\n"
                output += f"   ID: `{comm['id']}`\n\n"
            return output
        except Exception as e:
            return f"Error: {e}"

    def _h_close_commitment(commitment_id, method):
        try:
            brain = get_brain_path()
            commitment = commitment_ledger.close_commitment(brain, commitment_id, method)
            _emit_event("commitment_closed", "user",
                        {"commitment_id": commitment_id, "method": method},
                        description=f"Closed: {commitment['description'][:50]}")
            return f"✅ Commitment closed!\n\n**Description:** {commitment['description']}\n**Method:** {method}\n**Was open:** {commitment['age_days']} days\n**Closed at:** {commitment['closed_at']}"
        except Exception as e:
            return f"Error: {e}"

    def _h_commitment_health():
        try:
            brain = get_brain_path()
            ledger = commitment_ledger.load_ledger(brain)
            stats = ledger.get("stats", {})
            total = stats.get("total_open", 0)
            green = stats.get("green_tier", 0)
            yellow = stats.get("yellow_tier", 0)
            red = stats.get("red_tier", 0)
            by_type = stats.get("by_type", {})
            if red > 0:
                mental_load, advice = "🔴 HIGH", "Focus on red-tier items first"
            elif yellow > 2:
                mental_load, advice = "🟡 MEDIUM", "Clear yellow items before they go red"
            elif total == 0:
                mental_load, advice = "✨ ZERO", "No open loops - guilt-free operation!"
            else:
                mental_load, advice = "🟢 LOW", "Looking good, maintain momentum"
            type_str = ", ".join([f"{t}: {c}" for t, c in by_type.items()]) if by_type else "(none)"
            return f"## 🎯 Commitment Health\n\n**Open loops:** {total}\n- 🟢 Green: {green}\n- 🟡 Yellow: {yellow}\n- 🔴 Red: {red}\n\n**By type:** {type_str}\n\n**Mental load:** {mental_load}\n**Advice:** {advice}\n\n**Last scan:** {ledger.get('last_scan', 'Never')[:16] if ledger.get('last_scan') else 'Never'}"
        except Exception as e:
            return f"Error: {e}"

    def _h_open_loops(type_filter=None, tier_filter=None):
        try:
            brain = get_brain_path()
            ledger = commitment_ledger.load_ledger(brain)
            open_comms = [c for c in ledger["commitments"] if c["status"] == "open"]
            if type_filter:
                open_comms = [c for c in open_comms if c.get("type") == type_filter]
            if tier_filter:
                open_comms = [c for c in open_comms if c.get("tier") == tier_filter]
            if not open_comms:
                return "✅ No open loops! Guilt-free operation."
            by_type = {}
            for c in open_comms:
                t = c.get("type", "unknown")
                by_type.setdefault(t, []).append(c)
            output = f"## 📋 Open Loops ({len(open_comms)} total)\n\n"
            type_emoji = {"task": "🔧", "todo": "☑️", "draft": "📝", "decision": "🤔"}
            for t, items in by_type.items():
                output += f"### {type_emoji.get(t, '📌')} {t.upper()} ({len(items)})\n\n"
                items.sort(key=lambda x: ({"red": 0, "yellow": 1, "green": 2}.get(x.get("tier"), 3), -x.get("age_days", 0)))
                for c in items[:5]:
                    te = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(c.get("tier"), "⚪")
                    output += f"{te} **{c['description'][:50]}**\n   {c.get('age_days', 0)}d old | Suggested: {c.get('suggested_action')}\n   ID: `{c['id']}`\n\n"
                if len(items) > 5:
                    output += f"   ...and {len(items) - 5} more\n\n"
            return output
        except Exception as e:
            return f"Error: {e}"

    def _h_add_loop(description, loop_type="task", priority=3):
        try:
            brain = get_brain_path()
            commitment = commitment_ledger.add_commitment(brain, source_file="manual", source_line=0, description=description, comm_type=loop_type, source="manual", priority=priority)
            try:
                _emit_event("commitment_created", "brain_add_loop", {"commitment_id": commitment['id'], "type": loop_type, "description": description[:60], "priority": priority}, description=f"New {loop_type}: {description[:40]}")
            except Exception:
                pass
            return f"✅ Loop created!\n\n**ID:** `{commitment['id']}`\n**Type:** {loop_type}\n**Description:** {description}\n**Priority:** {priority}\n**Suggested:** {commitment['suggested_action']} - {commitment['suggested_reason']}"
        except Exception as e:
            return f"Error: {e}"

    def _h_weekly_challenge(action="get", challenge_id=None):
        try:
            brain = get_brain_path()
            if action == "list":
                challenges = commitment_ledger.get_starter_challenges()
                output = "## 🏆 Weekly Challenges\n\n"
                for c in challenges:
                    output += f"**{c['title']}** (`{c['id']}`)\n{c['description']}\n🏆 Reward: {c['reward']}\n\n"
                return output
            if action == "set":
                if not challenge_id:
                    return "⚠️ Please provide `challenge_id` to set a challenge."
                challenges = commitment_ledger.get_starter_challenges()
                selected = next((c for c in challenges if c["id"] == challenge_id), None)
                if not selected:
                    return f"❌ Challenge `{challenge_id}` not found."
                selected["started_at"] = datetime.now().isoformat()
                selected["status"] = "active"
                commitment_ledger.set_challenge(brain, selected)
                return f"✅ **Challenge Accepted: {selected['title']}**\n\nGoal: {selected['description']}\nGo get it!"
            challenge = commitment_ledger.load_challenge(brain)
            if not challenge:
                return "No active challenge. Run `nucleus_orchestration(action='weekly_challenge', params={'action': 'list'})` to pick one!"
            return f"## 🏆 Current Challenge: {challenge['title']}\n\n📝 **Goal:** {challenge['description']}\n📅 **Started:** {challenge['started_at'][:10]}\n🎁 **Reward:** {challenge['reward']}\n\nKeep pushing!"
        except Exception as e:
            return f"Error: {e}"

    def _h_patterns(action="list"):
        try:
            brain = get_brain_path()
            if action == "learn":
                patterns = commitment_ledger.learn_patterns(brain)
                return f"✅ Learning complete. Total patterns: {len(patterns)}"
            patterns = commitment_ledger.load_patterns(brain)
            if not patterns:
                return "No patterns learned yet."
            output = "## 🧠 Learned Patterns\n\n"
            for p in patterns:
                output += f"**{p['name']}**\n• Keywords: {', '.join(p['keywords'])}\n• Action: {p['action']}\n\n"
            return output
        except Exception as e:
            return f"Error: {e}"

    def _h_metrics():
        try:
            brain = get_brain_path()
            metrics = commitment_ledger.calculate_metrics(brain)
            output = f"## 📊 Coordination Metrics (Last 7 Days)\n\n**🚀 Velocity:** {metrics['velocity_7d']} items closed\n**⏱️ Speed:** {metrics['avg_days_to_close']} days avg\n\n**📈 Closure Rates by Type:**\n"
            if metrics['closure_rates']:
                for t, rate in metrics['closure_rates'].items():
                    output += f"- {t}: {rate}\n"
            else:
                output += "(No closed items yet)\n"
            output += f"\n**🧠 Current Load:**\n- Total Open: {metrics['current_load']['total']}\n- Red Tier: {metrics['current_load']['red']}\n"
            return output
        except Exception as e:
            return f"Error: {e}"

    ORCH_ROUTER = {
        "satellite": _h_satellite,
        "scan_commitments": _h_scan_commitments,
        "archive_stale": _h_archive_stale,
        "export": _h_export,
        "list_commitments": _h_list_commitments,
        "close_commitment": _h_close_commitment,
        "commitment_health": _h_commitment_health,
        "open_loops": _h_open_loops,
        "add_loop": _h_add_loop,
        "weekly_challenge": _h_weekly_challenge,
        "patterns": _h_patterns,
        "metrics": _h_metrics,
    }

    @mcp.tool()
    def nucleus_orchestration(action: str, params: dict = {}) -> str:
        """Satellite view, commitments, loops, patterns & metrics.

Actions:
  satellite         - Unified satellite view. params: {detail_level?}
  scan_commitments  - Scan artifacts for new commitments
  archive_stale     - Auto-archive commitments older than 30 days
  export            - Export brain to zip
  list_commitments  - List open commitments. params: {tier?}
  close_commitment  - Close a commitment. params: {commitment_id, method}
  commitment_health - Get commitment health summary
  open_loops        - View all open loops. params: {type_filter?, tier_filter?}
  add_loop          - Add a new open loop. params: {description, loop_type?, priority?}
  weekly_challenge  - Manage weekly challenge. params: {action?, challenge_id?}
  patterns          - Manage learned patterns. params: {action?}
  metrics           - Get coordination metrics
"""
        return dispatch(action, params, ORCH_ROUTER, "nucleus_orchestration")

    # ════════════════════════════════════════════════════════════
    # FACADE 2: nucleus_telemetry
    # ════════════════════════════════════════════════════════════

    def _h_set_llm_tier(tier):
        import os
        valid_tiers = ["premium", "standard", "economy", "local_paid", "local_free"]
        if tier.lower() not in valid_tiers:
            return f"❌ Invalid tier '{tier}'. Valid tiers: {', '.join(valid_tiers)}"
        os.environ["NUCLEUS_LLM_TIER"] = tier.lower()
        return f"✅ LLM tier set to '{tier}'."

    def _h_get_llm_status():
        import os
        brain = get_brain_path()
        tier_status_path = brain / "tier_status.json"
        output = "## 🧠 LLM Tier Status\n\n"
        current_tier = os.environ.get("NUCLEUS_LLM_TIER", "auto (standard)")
        force_vertex = os.environ.get("FORCE_VERTEX", "1")
        output += f"**Current Tier:** {current_tier}\n**Vertex Mode:** {'Enabled' if force_vertex == '1' else 'Disabled'}\n\n"
        if tier_status_path.exists():
            try:
                with open(tier_status_path, encoding='utf-8') as f:
                    status = json.load(f)
                output += "### Available Tiers\n| Tier | Model | Status | Latency |\n|------|-------|--------|--------|\n"
                for tier_name, result in status.get("tier_results", {}).items():
                    se = "✅" if result.get("status") == "SUCCESS" else "❌"
                    lat = f"{result.get('latency_ms', '-')}ms" if result.get('latency_ms') else "-"
                    output += f"| {tier_name} | {result.get('model', 'unknown')} | {se} {result.get('status')} | {lat} |\n"
                output += f"\n**Recommended:** {status.get('recommended_tier', 'standard')}\n"
            except Exception as e:
                output += f"Could not load tier status: {e}\n"
        else:
            output += "No benchmark data available.\n"
        return output

    def _h_check_protocol(agent_id):
        from ..runtime.slot_ops import _check_protocol_compliance
        return json.dumps(_check_protocol_compliance(agent_id), indent=2)

    def _h_request_handoff(to_agent, context, request, priority=3, artifacts=None):
        from ..runtime.slot_ops import _brain_request_handoff_impl
        return _brain_request_handoff_impl(to_agent, context, request, priority, artifacts)

    def _h_get_handoffs(agent_id=None):
        from ..runtime.slot_ops import _brain_get_handoffs_impl
        return _brain_get_handoffs_impl(agent_id)

    def _h_agent_cost_dashboard():
        from ..runtime.agent_runtime_v2 import get_execution_manager
        return get_execution_manager().get_dashboard_metrics()

    def _h_dispatch_metrics():
        from ._dispatch import get_dispatch_telemetry
        return get_dispatch_telemetry().get_metrics()

    TELEM_ROUTER = {
        "set_llm_tier": _h_set_llm_tier,
        "get_llm_status": _h_get_llm_status,
        "record_interaction": lambda: _brain_record_interaction_impl(),
        "value_ratio": lambda: _brain_value_ratio_impl(),
        "check_kill_switch": lambda: _brain_check_kill_switch_impl(),
        "pause_notifications": lambda: _brain_pause_notifications_impl(),
        "resume_notifications": lambda: _brain_resume_notifications_impl(),
        "record_feedback": lambda notification_type, score: _brain_record_feedback_impl(notification_type, score),
        "mark_high_impact": lambda: _brain_mark_high_impact_impl(),
        "check_protocol": _h_check_protocol,
        "request_handoff": _h_request_handoff,
        "get_handoffs": _h_get_handoffs,
        "agent_cost_dashboard": _h_agent_cost_dashboard,
        "dispatch_metrics": _h_dispatch_metrics,
    }

    @mcp.tool()
    def nucleus_telemetry(action: str, params: dict = {}) -> str:
        """LLM tiers, telemetry, PEFS notifications & protocol tools.

Actions:
  set_llm_tier         - Set default LLM tier. params: {tier}
  get_llm_status       - Get LLM tier configuration
  record_interaction   - Record user interaction timestamp
  value_ratio          - Get Value Ratio metric
  check_kill_switch    - Check Kill Switch status
  pause_notifications  - Pause PEFS notifications
  resume_notifications - Resume PEFS notifications
  record_feedback      - Record notification feedback. params: {notification_type, score}
  mark_high_impact     - Mark loop closure as high-impact
  check_protocol       - Check protocol compliance. params: {agent_id}
  request_handoff      - Request agent handoff. params: {to_agent, context, request, priority?, artifacts?}
  get_handoffs         - Get pending handoffs. params: {agent_id?}
  agent_cost_dashboard - Get agent cost tracking dashboard
  dispatch_metrics     - Get dispatch telemetry (per-action timing, error rates)
"""
        return dispatch(action, params, TELEM_ROUTER, "nucleus_telemetry")

    # ════════════════════════════════════════════════════════════
    # FACADE 3: nucleus_slots
    # ════════════════════════════════════════════════════════════

    def _h_slot_complete(slot_id, task_id, outcome="success", notes=None):
        from ..runtime.slot_ops import _brain_slot_complete_impl
        result = _brain_slot_complete_impl(slot_id, task_id, outcome, verification_notes=notes)
        next_task = _brain_orchestrate_impl(slot_id=slot_id, mode="auto")
        return f"{result}\n\nNext Task:\n{next_task}"

    def _h_slot_exhaust(slot_id, reset_hours=5):
        from ..runtime.slot_ops import _brain_slot_exhaust_impl
        reset_at = time.time() + (reset_hours * 3600)
        reset_at_str = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(reset_at))
        return _brain_slot_exhaust_impl(slot_id, reason="Model usage limit", reset_at=reset_at_str)

    def _h_autopilot_sprint(slots=None, mode="auto", halt_on_blocker=True, halt_on_tier_mismatch=False, max_tasks_per_slot=10, budget_limit=None, dry_run=False):
        from ..runtime.slot_ops import _brain_autopilot_sprint_impl
        return _brain_autopilot_sprint_impl(slots, mode, halt_on_blocker, halt_on_tier_mismatch, max_tasks_per_slot, budget_limit, dry_run)

    SLOTS_ROUTER = {
        "orchestrate": lambda slot_id=None, model=None, alias=None, mode="auto": _brain_orchestrate_impl(slot_id, model, alias, mode),
        "slot_complete": _h_slot_complete,
        "slot_exhaust": _h_slot_exhaust,
        "status_dashboard": lambda detail_level="standard": __import__('mcp_server_nucleus.runtime.slot_ops', fromlist=['_brain_status_dashboard_impl'])._brain_status_dashboard_impl(),
        "autopilot_sprint": _h_autopilot_sprint,
        "force_assign": lambda slot_id, task_id, acknowledge_risk=False: __import__('mcp_server_nucleus.runtime.slot_ops', fromlist=['_brain_force_assign_impl'])._brain_force_assign_impl(slot_id, task_id, acknowledge_risk),
        "autopilot_sprint_v2": lambda slots=None, mode="auto", halt_on_blocker=True, halt_on_tier_mismatch=False, max_tasks_per_slot=10, budget_limit=None, time_limit_hours=None, dry_run=False: _brain_autopilot_sprint_v2_impl(slots, mode, halt_on_blocker, halt_on_tier_mismatch, max_tasks_per_slot, budget_limit, time_limit_hours, dry_run),
        "start_mission": lambda name, goal, task_ids, slot_ids=None, budget_limit=10.0, time_limit_hours=4.0, success_criteria=None: _brain_start_mission_impl(name, goal, task_ids, slot_ids, budget_limit, time_limit_hours, success_criteria),
        "mission_status": lambda mission_id=None: _brain_mission_status_impl(mission_id),
        "halt_sprint": lambda reason="User requested halt": _brain_halt_sprint_impl(reason),
        "resume_sprint": lambda sprint_id=None: _brain_resume_sprint_impl(sprint_id),
    }

    @mcp.tool()
    def nucleus_slots(action: str, params: dict = {}) -> str:
        """Orchestration slots, sprints & mission management.

Actions:
  orchestrate        - THE GOD COMMAND. params: {slot_id?, model?, alias?, mode?}
  slot_complete      - Mark task complete. params: {slot_id, task_id, outcome?, notes?}
  slot_exhaust       - Mark slot exhausted. params: {slot_id, reset_hours?}
  status_dashboard   - ASCII dashboard. params: {detail_level?}
  autopilot_sprint   - Sprint command. params: {slots?, mode?, halt_on_blocker?, halt_on_tier_mismatch?, max_tasks_per_slot?, budget_limit?, dry_run?}
  force_assign       - Force assign task. params: {slot_id, task_id, acknowledge_risk?}
  autopilot_sprint_v2 - Enhanced sprint V3.1. params: {slots?, mode?, halt_on_blocker?, halt_on_tier_mismatch?, max_tasks_per_slot?, budget_limit?, time_limit_hours?, dry_run?}
  start_mission      - Start mission. params: {name, goal, task_ids, slot_ids?, budget_limit?, time_limit_hours?, success_criteria?}
  mission_status     - Get mission status. params: {mission_id?}
  halt_sprint        - Halt sprint. params: {reason?}
  resume_sprint      - Resume sprint. params: {sprint_id?}
"""
        return dispatch(action, params, SLOTS_ROUTER, "nucleus_slots")

    # ════════════════════════════════════════════════════════════
    # FACADE 4: nucleus_infra
    # ════════════════════════════════════════════════════════════

    def _h_file_changes():
        try:
            from ..runtime.file_monitor import get_file_monitor
            from ..runtime.event_bus import get_event_bus
            monitor = get_file_monitor()
            bus = get_event_bus()
            if not monitor:
                bus_events = bus.get_recent(50)
                return json.dumps({"status": "degraded", "event_count": len(bus_events), "events": [e.to_dict() for e in bus_events]})
            if not monitor.is_running:
                return json.dumps({"status": "stopped", "events": []})
            events = monitor.get_pending_events()
            return json.dumps({"status": "active", "event_count": len(events), "events": [e.to_dict() for e in events]})
        except ImportError:
            return json.dumps({"status": "unavailable", "message": "watchdog not installed"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _h_gcloud_status():
        try:
            from ..runtime.gcloud_ops import get_gcloud_ops
            return json.dumps(get_gcloud_ops().check_auth_status(), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _h_gcloud_services(project=None, region="us-central1"):
        try:
            from ..runtime.gcloud_ops import GCloudOps
            ops = GCloudOps(project=project, region=region)
            if not ops.is_available:
                return json.dumps({"error": "gcloud CLI not found"})
            result = ops.list_cloud_run_services()
            return json.dumps(result.to_dict(), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _h_list_services():
        try:
            from ..runtime.render_ops import get_render_ops
            return json.dumps(get_render_ops().list_services(), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _h_scan_marketing_log():
        try:
            log_path = Path("docs/marketing/marketing_log.md")
            if not log_path.exists():
                log_path = Path("/path/to/your/project/docs/marketing/marketing_log.md")
            if not log_path.exists():
                return json.dumps({"status": "error", "error": "Marketing log not found"})
            failures = []
            with open(log_path, "r", encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if "[FAILURE]" in line:
                        tag = "UNKNOWN"
                        for t in ["AUTH_LOCKED", "SELECTOR_MISSING", "TIMEOUT", "RATE_LIMIT"]:
                            if f"[{t}]" in line:
                                tag = t
                                break
                        failures.append({"line_number": i + 1, "tag": tag, "content": line.strip()})
            failures.reverse()
            return json.dumps({"status": "healthy" if not failures else "degraded", "failure_count": len(failures), "failures": failures[:5]}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})

    def _h_synthesize_strategy(focus_topic=None):
        try:
            from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_synthesize_strategy as _impl
            result = _impl(project_root=str(Path.cwd()), focus_topic=focus_topic)
            return f"✅ Strategy Updated.\nPath: {result.get('path')}" if result.get("status") == "success" else f"❌ Failed: {result.get('message')}"
        except Exception as e:
            return f"❌ Error: {e}"

    def _h_status_report(focus="roadmap"):
        try:
            from mcp_server_nucleus.runtime.capabilities.synthesizer import brain_synthesize_status_report as _impl
            result = _impl(project_root=str(Path.cwd()), focus=focus)
            return result.get("report") if result.get("status") == "success" else f"❌ Failed: {result.get('message')}"
        except Exception as e:
            return f"❌ Error: {e}"

    def _h_optimize_workflow():
        try:
            from mcp_server_nucleus.runtime.capabilities.marketing_engine import brain_optimize_workflow as _impl
            result = _impl(project_root=str(Path.cwd()))
            if result.get("status") == "success":
                return f"✅ Workflow Optimized."
            elif result.get("status") == "skipped":
                return f"ℹ️ Skipped: {result.get('message')}"
            return f"❌ Failed: {result.get('message')}"
        except Exception as e:
            return f"❌ Error: {e}"

    def _h_manage_strategy(action, content=None):
        try:
            from ..runtime.strategy import _manage_strategy
            return _manage_strategy(action, content)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def _h_update_roadmap(action, item=None):
        try:
            from ..runtime.strategy import _update_roadmap
            return _update_roadmap(action, item)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    INFRA_ROUTER = {
        "file_changes": _h_file_changes,
        "gcloud_status": _h_gcloud_status,
        "gcloud_services": _h_gcloud_services,
        "list_services": _h_list_services,
        "scan_marketing_log": _h_scan_marketing_log,
        "synthesize_strategy": _h_synthesize_strategy,
        "status_report": _h_status_report,
        "optimize_workflow": _h_optimize_workflow,
        "manage_strategy": _h_manage_strategy,
        "update_roadmap": _h_update_roadmap,
    }

    @mcp.tool()
    def nucleus_infra(action: str, params: dict = {}) -> str:
        """Infrastructure: file changes, cloud, marketing & strategy tools.

Actions:
  file_changes        - Get pending file change events
  gcloud_status       - Check GCloud auth status
  gcloud_services     - List Cloud Run services. params: {project?, region?}
  list_services       - List Render.com services
  scan_marketing_log  - Scan marketing log for failures
  synthesize_strategy - Analyze marketing & update strategy. params: {focus_topic?}
  status_report       - Generate State of the Union. params: {focus?}
  optimize_workflow   - Self-optimize workflow cheatsheet
  manage_strategy     - Read/Update strategy doc. params: {action, content?}
  update_roadmap      - Read/Update roadmap. params: {action, item?}
"""
        return dispatch(action, params, INFRA_ROUTER, "nucleus_infra")

    # ════════════════════════════════════════════════════════════
    # FACADE 5: nucleus_agents
    # ════════════════════════════════════════════════════════════

    async def _h_spawn_agent(intent, execute_now=True, persona=None, confirm=False):
        # HITL Gate: spawning agents is a resource-consuming operation
        if not confirm:
            return (
                f"⚠️ HITL GATE: spawn_agent requires confirm=true.\n"
                f"Intent: {intent}\n"
                f"Persona: {persona or 'default'}\n"
                f"Re-call with confirm=true to proceed. Agent spawning consumes compute resources."
            )
        from ..runtime.agent_runtime_v2 import get_execution_manager, RateLimitError
        exec_mgr = get_execution_manager()
        try:
            # Rate-limit check via AgentExecutionManager
            execution = exec_mgr.spawn_agent(
                persona=persona or "default",
                intent=intent,
            )
            agent_id = execution.agent_id
            exec_mgr.start_execution(agent_id)
        except RateLimitError as e:
            return f"⚠️ Agent spawn rate-limited: {e}. Retry after {e.retry_after:.1f}s."

        try:
            from uuid import uuid4
            from ..runtime.llm_client import DualEngineLLM, LLMTier, TierRouter
            session_id = f"spawn-{str(uuid4())[:8]}"
            from ..runtime.factory import ContextFactory
            from ..runtime.agent import EphemeralAgent
            factory = ContextFactory()
            context = factory.create_context_for_persona(session_id, persona, intent) if persona else factory.create_context(session_id, intent)
            job_type = context.get("job_type", "ORCHESTRATION")
            output = f"## 🏭 NAR Factory Receipt\n**Intent:** {intent}\n**Persona:** {context.get('persona', 'Unknown')}\n**Job Type:** {job_type}\n**Capabilities:** {', '.join(context['capabilities'])}\n**Tools Mapped:** {len(context['tools'])}\n**Agent ID:** {agent_id}\n"
            if not context['tools']:
                exec_mgr.complete_execution(agent_id, "error")
                return output + "\n❌ No tools mapped."
            if execute_now:
                output += "\n--- Executive Trace ---\n"
                llm = DualEngineLLM(job_type=job_type)
                output += f">> 🎯 Tier: {llm.tier.value if llm.tier else 'default'}\n>> 🧠 Model: {llm.model_name}\n>> ⚡ Engine: {llm.active_engine}\n"
                agent = EphemeralAgent(context, model=llm)
                # Record tool calls during execution
                exec_mgr.record_tool_call(agent_id)
                log = await agent.run()
                output += log + "\n✅ Ephemeral Agent executed.\n"
            cost = exec_mgr.complete_execution(agent_id, "completed")
            if cost:
                output += f"\n--- Cost ---\n**Tokens:** {cost.total_tokens} | **Est. Cost:** ${cost.estimated_cost_usd:.6f}\n"
            return output
        except Exception as e:
            exec_mgr.complete_execution(agent_id, "error")
            return f"Error spawning agent: {e}"

    def _h_apply_critique(review_path):
        try:
            path_str = str(review_path)
            if "artifacts/" in path_str:
                path_str = path_str.split("artifacts/")[-1]
            content_str = _read_artifact(path_str)
            if content_str.startswith("Error"):
                return {"error": content_str}
            review = json.loads(content_str)
            payload = review.get("payload", {})
            target = payload.get("target")
            issues = payload.get("issues", [])
            if not target or not issues:
                return {"error": "Invalid critique format"}
            description = f"Fix {len(issues)} issues in {target} identified by Critic.\n\nIssues:\n"
            for i in issues:
                description += f"- [{i.get('severity')}] {i.get('description')}\n"
            result = _trigger_agent_impl(agent="developer", task_description=description, context_files=[path_str, target])
            return {"success": True, "message": result}
        except Exception as e:
            return {"error": f"Failed: {str(e)}"}

    async def _h_orchestrate_swarm(mission, agents=None):
        try:
            orch = get_orch()
            return await orch.start_mission(mission, agents=agents)
        except Exception as e:
            return make_response(False, error=f"Swarm failed: {str(e)}")

    def _h_critique_code(file_path, context="General Review"):
        from ..runtime.llm_client import DualEngineLLM
        try:
            brain = get_brain_path()
            target_file = Path(file_path)
            if not target_file.exists():
                return json.dumps({"error": f"File not found: {file_path}"})
            code_content = target_file.read_text()
            critic_persona_path = brain / "agents" / "critic.md"
            system_prompt = critic_persona_path.read_text() if critic_persona_path.exists() else "You are The Critic. Find bugs, security flaws, and style issues."
            prompt_parts = [f"\nCRITIQUE THIS FILE: {file_path}\nCONTEXT: {context}\nReturn JSON: {{'status': 'PASS/FAIL/WARN', 'score': 0-100, 'issues': [...]}}\n", "\nCODE:\n```\n", code_content, "\n```\n"]
            client = DualEngineLLM(system_instruction=system_prompt)
            response = client.generate_content(prompt_parts)
            text = response.text.replace("```json", "").replace("```", "").strip()
            try:
                critique = json.loads(text)
            except Exception:
                critique = {"status": "WARN", "score": 0, "summary": text, "issues": []}
            _emit_event("code_critiqued", "critic", {"file": file_path, "status": critique.get("status"), "score": critique.get("score")})
            return json.dumps(critique, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _h_session_briefing(conversation_id=None):
        from ..runtime.common import get_brain_path as _gbp
        lines = ["## 📋 Session Briefing", ""]
        if conversation_id:
            try:
                brain = _gbp()
                registry_path = brain / "meta" / "thread_registry.md"
                if registry_path.exists():
                    content = registry_path.read_text()
                    short_id = conversation_id[:8]
                    for line in content.split("\n"):
                        if short_id in line and "|" in line:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 5:
                                lines += [f"### 🪪 Your Identity", f"- **Thread:** `{conversation_id[:12]}...`", f"- **Role:** {parts[3]}", f"- **Focus:** {parts[2]}", ""]
                                break
            except Exception:
                pass
        try:
            from ..runtime.common import get_brain_path as _gbp2
            brain = _gbp2()
            sessions_path = brain / "ledger" / "active_sessions.json"
            if sessions_path.exists():
                with open(sessions_path, "r", encoding='utf-8') as f:
                    active = json.load(f).get("sessions", {})
                if active:
                    lines.append(f"### 👥 Active Sessions ({len(active)})")
                    for sid, info in list(active.items())[:5]:
                        lines.append(f"- `{sid[:8]}`: {info.get('focus', 'Unknown')}")
                    lines.append("")
        except Exception:
            pass
        in_progress = _list_tasks(status="IN_PROGRESS")
        if in_progress:
            lines.append(f"### 🔄 In Progress ({len(in_progress)})")
            for t in in_progress[:3]:
                lines.append(f"- {t['description'][:50]}... (by {t.get('claimed_by', 'unknown')})")
            lines.append("")
        pending = _list_tasks(status="PENDING")
        if pending:
            lines.append(f"### 📌 Pending ({len(pending)})")
            for t in pending[:5]:
                pri = "🔴" if t.get("priority", 3) <= 2 else "🟡" if t.get("priority") == 3 else "⚪"
                lines.append(f"- {pri} {t['description'][:60]}")
        if not in_progress and not pending:
            lines.append("✨ **All clear!** No pending tasks.")
        return "\n".join(lines)

    def _h_register_session(conversation_id, focus_area):
        try:
            from ..runtime.common import get_brain_path as _gbp
            brain = _gbp()
            sessions_path = brain / "ledger" / "active_sessions.json"
            sessions = {}
            if sessions_path.exists():
                with open(sessions_path, "r", encoding='utf-8') as f:
                    sessions = json.load(f)
            sessions.setdefault("sessions", {})[conversation_id] = {"focus": focus_area, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "last_active": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            sessions_path.parent.mkdir(parents=True, exist_ok=True)
            with open(sessions_path, "w", encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
            _emit_event("session_registered", "nucleus_mcp", {"conversation_id": conversation_id, "focus_area": focus_area})
            return f"Registered session {conversation_id[:8]}... focused on: {focus_area}"
        except Exception as e:
            return f"Error: {e}"

    def _h_handoff_task(task_description, target_session_id=None, priority=3):
        try:
            desc = f"{'@' + target_session_id[:8] + ': ' if target_session_id else ''}{task_description}"
            result = _add_task(description=desc, priority=priority, source="handoff")
            if not result.get("success"):
                return f"Error: {result.get('error')}"
            task = result.get("task", {})
            try:
                brain = get_brain_path()
                handoffs_path = brain / "ledger" / "handoffs.json"
                handoffs = []
                if handoffs_path.exists():
                    with open(handoffs_path, "r", encoding='utf-8') as f:
                        handoffs = json.load(f)
                handoffs.append({"task_id": task.get("id"), "description": task_description, "target": target_session_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
                with open(handoffs_path, "w", encoding='utf-8') as f:
                    json.dump(handoffs, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            target_msg = f"for session {target_session_id[:8]}" if target_session_id else "to shared queue"
            return f"✅ Task handed off {target_msg}. ID: {task.get('id')}"
        except Exception as e:
            return f"Error: {e}"

    AGENTS_ROUTER = {
        "spawn_agent": _h_spawn_agent,
        "apply_critique": _h_apply_critique,
        "orchestrate_swarm": _h_orchestrate_swarm,
        "search_memory": lambda query: __import__('mcp_server_nucleus.runtime.memory', fromlist=['_search_memory'])._search_memory(query),
        "read_memory": lambda category: __import__('mcp_server_nucleus.runtime.memory', fromlist=['_read_memory'])._read_memory(category),
        "respond_to_consent": lambda agent_id, choice="cold": {"success": True, "agent_id": agent_id, "choice": choice.upper(), "message": f"Consent recorded. Agent will respawn in {choice.upper()} mode."},
        "list_pending_consents": lambda: {"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."},
        "critique_code": _h_critique_code,
        "fix_code": _fix_code_impl,
        "session_briefing": _h_session_briefing,
        "register_session": _h_register_session,
        "handoff_task": _h_handoff_task,
        "ingest_tasks": lambda source, source_type="auto", session_id=None, auto_assign=False, skip_dedup=False, dry_run=False: _brain_ingest_tasks_impl(source, source_type, session_id, auto_assign, skip_dedup, dry_run),
        "rollback_ingestion": lambda batch_id, reason=None: _brain_rollback_ingestion_impl(batch_id, reason),
        "ingestion_stats": lambda: _brain_ingestion_stats_impl(),
        "dashboard": lambda detail_level="standard", format="ascii", include_alerts=True, include_trends=False, category=None: _brain_enhanced_dashboard_impl(detail_level, format, include_alerts, include_trends, category),
        "snapshot_dashboard": lambda name=None: _brain_snapshot_dashboard_impl(name),
        "list_dashboard_snapshots": lambda limit=10: _brain_list_snapshots_impl(limit),
        "get_alerts": lambda: _brain_get_alerts_impl(),
        "set_alert_threshold": lambda metric, level, value: _brain_set_alert_threshold_impl(metric, level, value),
    }

    @mcp.tool()
    async def nucleus_agents(action: str, params: dict = {}) -> str:
        """Agent spawning, critic, swarm, memory, ingestion & dashboard tools.

Actions:
  spawn_agent          - Spawn Ephemeral Agent. params: {intent, execute_now?, persona?, confirm?}. HITL: requires confirm=true.
  apply_critique       - Apply critique fixes. params: {review_path}
  orchestrate_swarm    - Start multi-agent swarm. params: {mission, agents?}
  search_memory        - Search long-term memory. params: {query}
  read_memory          - Read memory category. params: {category}
  respond_to_consent   - Respond to respawn consent. params: {agent_id, choice?}
  list_pending_consents - List agents awaiting consent
  critique_code        - Run Critic review. params: {file_path, context?}
  fix_code             - Auto-fix code. params: {file_path, issues_context}
  session_briefing     - Get session briefing. params: {conversation_id?}
  register_session     - Register session focus. params: {conversation_id, focus_area}
  handoff_task         - Hand off task. params: {task_description, target_session_id?, priority?}
  ingest_tasks         - Ingest tasks. params: {source, source_type?, session_id?, auto_assign?, skip_dedup?, dry_run?}
  rollback_ingestion   - Rollback ingestion. params: {batch_id, reason?}
  ingestion_stats      - Get ingestion statistics
  dashboard            - Enhanced dashboard. params: {detail_level?, format?, include_alerts?, include_trends?, category?}
  snapshot_dashboard   - Create dashboard snapshot. params: {name?}
  list_dashboard_snapshots - List snapshots. params: {limit?}
  get_alerts           - Get active alerts
  set_alert_threshold  - Set alert threshold. params: {metric, level, value}
"""
        return await async_dispatch(action, params, AGENTS_ROUTER, "nucleus_agents")

    return [
        ("nucleus_orchestration", nucleus_orchestration),
        ("nucleus_telemetry", nucleus_telemetry),
        ("nucleus_slots", nucleus_slots),
        ("nucleus_infra", nucleus_infra),
        ("nucleus_agents", nucleus_agents),
    ]
