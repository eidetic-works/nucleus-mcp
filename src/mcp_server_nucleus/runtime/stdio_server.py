#!/usr/bin/env python3
import sys
from pathlib import Path

# Security: Ensure we can import our own package
# This makes the script standalone and robust against PYTHONPATH issues in Claude Desktop
current_path = Path(__file__).resolve()
current_dir = current_path.parent

# Robustly find the 'src' directory by looking for 'mcp_server_nucleus' in the path
# This handles cases where file structure might be slightly different or symlinked
src_p = current_path
while src_p.name != 'src' and src_p.parent != src_p:
    src_p = src_p.parent

if src_p.name == 'src':
    # found it
    pass
else:
    # Fallback to hardcoded relative path if traversal fails
    # script is in src/mcp_server_nucleus/runtime/stdio_server.py
    # we need src in path
    src_p = current_dir.parent.parent

src_root = str(src_p)

# Debug logging to stderr (because stdout is for JSON-RPC)
if "--help" not in sys.argv and "--status" not in sys.argv:
    sys.stderr.write("[Nucleus] Bootstrapping standalone server...\n")
    sys.stderr.write(f"[Nucleus] Script path: {current_path}\n")
    sys.stderr.write(f"[Nucleus] Injected src root: {src_root}\n")

if src_root not in sys.path:
    # Use insert(0) to prioritize our local source
    sys.path.insert(0, src_root)

try:
    import mcp_server_nucleus
    sys.stderr.write("[Nucleus] Successfully imported mcp_server_nucleus package.\n")
except ImportError as e:
    sys.stderr.write(f"[Nucleus] FATAL: Could not import mcp_server_nucleus: {e}\n")
    sys.stderr.write(f"[Nucleus] sys.path: {sys.path}\n")
    # Fallback to hardcoded relative path if traversal fails
    sys.path.append(src_root)

import json
import logging
import traceback
import time
import os
from typing import Any, Dict, Optional
from mcp_server_nucleus.hypervisor.locker import Locker
from mcp_server_nucleus.hypervisor.watchdog import Watchdog
from mcp_server_nucleus.hypervisor.injector import Injector
from mcp_server_nucleus.runtime.task_ops import (
    _list_tasks, _add_task, _update_task,
    _claim_task, _get_next_task
)
import asyncio
from mcp_server_nucleus.runtime.mounter_ops import get_mounter
from mcp_server_nucleus.tools._dispatch import dispatch

# Configure logging to stderr to not corrupt stdout (which is for JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format='[Nucleus] %(message)s')
logger = logging.getLogger("nucleus_server")

# Silence watchdog library internals to prevent stdout/stderr pollution from internal threads
logging.getLogger("watchdog").setLevel(logging.ERROR)

START_TIME = time.time()

def make_response(success: bool, data: Any = None, error: str = None) -> str:
    """Helper to create a formatted JSON response string."""
    response = {"success": success}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return json.dumps(response, indent=2)

class StdioServer:
    def __init__(self):
        # Resolve paths first
        self.brain_path = Path(os.environ.get("NUCLEAR_BRAIN_PATH", ".")).resolve()
        workspace_root = self.brain_path
        
        self.locker = Locker()
        self.injector = Injector(str(workspace_root))
        self.watchdog = Watchdog(str(workspace_root))
        
        try:
            self.watchdog.start()
        except Exception as e:
            logger.error(f"Failed to start watchdog: {e}")
            
        self.mounter = get_mounter(self.brain_path)

    async def run(self):
        # Restore mounts from persistence
        await self.mounter.restore_mounts()
        
        loop = asyncio.get_running_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    
                    response = await self.handle_request(request)
                    if response:
                        out = json.dumps(response)
                        print(out, flush=True)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from line: {repr(line)}")
            except Exception as e:
                logger.error(f"Server loop error: {e}")
                traceback.print_exc(file=sys.stderr)

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        msg_id = request.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05", # Updated protocol version
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "nucleus",
                        "version": "1.0.9"
                    }
                }
            }
        
        elif method == "notifications/initialized":
            # No response needed for notification
            return None
            
        elif method == "tools/list":
            # ── 12 Facade Tools with rich schemas for TDQS ──────────────
            def _schema(actions, param_desc="Action-specific parameters. Pass as key-value pairs."):
                return {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": actions,
                            "description": "The action to execute."
                        },
                        "params": {
                            "type": "object",
                            "description": param_desc,
                            "default": {}
                        }
                    },
                    "required": ["action"]
                }

            tools = [
                {
                    "name": "nucleus_governance",
                    "description": "Governance, hypervisor, and security controls for the Nucleus Agent OS. Lock and unlock files with immutable flags, set red/blue security modes, run auto-fix verification loops (verify-diagnose-fix-retry), list directories, watch file changes, check governance status, and manage system-level operations like curl and pip_install.",
                    "inputSchema": _schema(
                        ["auto_fix_loop", "lock", "unlock", "set_mode", "list_directory", "delete_file", "watch", "status", "curl", "pip_install"],
                        "Parameters vary by action. auto_fix_loop: {file_path, verification_command}. lock/unlock: {path}. set_mode: {mode: 'red'|'blue'}. list_directory: {path}. delete_file: {path}. watch: {path, duration}. curl: {url, method, headers, body}. pip_install: {package}."
                    )
                },
                {
                    "name": "nucleus_engrams",
                    "description": "Persistent memory (engrams), health checks, observability, and context graph for the Nucleus Agent OS. Write and query engrams that survive across sessions. Run health checks, version info, audit logs. Generate morning briefs, pulse-and-polish reports, self-healing SRE diagnostics. Build and traverse context graphs of related engrams. Track billing summaries.",
                    "inputSchema": _schema(
                        ["health", "version", "audit_log", "write_engram", "query_engrams", "search_engrams", "governance_status", "morning_brief", "pulse_and_polish", "self_healing_sre", "fusion_reactor", "context_graph", "engram_neighbors", "render_graph", "billing_summary"],
                        "Parameters vary by action. write_engram: {content, tags[], source, metadata{}}. query_engrams: {query, limit, tags[]}. search_engrams: {query, limit}. audit_log: {limit, level}. context_graph: {engram_id}. engram_neighbors: {engram_id, depth}."
                    )
                },
                {
                    "name": "nucleus_tasks",
                    "description": "Task queue management with priority, escalation, and ADHD-aware context-switch protection. Add tasks with priority levels, claim and update task status, import tasks from JSONL files. Track cognitive depth to prevent rabbit-holing (push/pop/show/reset depth). Context-switch tools save and restore working state when switching between tasks.",
                    "inputSchema": _schema(
                        ["list", "get_next", "claim", "update", "add", "import_jsonl", "escalate", "depth_push", "depth_pop", "depth_show", "depth_reset", "depth_set_max", "depth_map", "context_switch", "context_switch_status", "context_switch_reset"],
                        "Parameters vary by action. add: {title, description, priority: 'critical'|'high'|'medium'|'low', tags[]}. update: {task_id, status: 'pending'|'in_progress'|'done'|'blocked', notes}. claim: {task_id}. escalate: {task_id, reason}. depth_set_max: {max_depth}. context_switch: {to_task_id}. import_jsonl: {file_path}."
                    )
                },
                {
                    "name": "nucleus_sessions",
                    "description": "Session lifecycle management with save/resume, events, state, and checkpoints. Start and end work sessions with automatic context capture. Save session state and resume later with full context restoration. Emit and read structured events. Create checkpoints for rollback. Generate handoff summaries for session transitions. Archive resolved sessions and garbage collect stale ones.",
                    "inputSchema": _schema(
                        ["save", "resume", "list", "check_recent", "end", "start", "archive_resolved", "propose_merges", "garbage_collect", "emit_event", "read_events", "get_state", "update_state", "checkpoint", "resume_checkpoint", "handoff_summary"],
                        "Parameters vary by action. start: {goal, tags[]}. save: {session_id, notes}. resume: {session_id}. emit_event: {event_type, data{}}. read_events: {session_id, limit, event_type}. update_state: {key, value}. checkpoint: {label}. resume_checkpoint: {checkpoint_id}."
                    )
                },
                {
                    "name": "nucleus_sync",
                    "description": "Multi-agent synchronization, artifact management, trigger system, and deployment orchestration. Identify agents and sync state across distributed brains. Read and write named artifacts for cross-session data sharing. Define and evaluate triggers for automated workflows. Manage deployment lifecycles with poll, check, complete, and smoke test stages.",
                    "inputSchema": _schema(
                        ["identify_agent", "sync_status", "sync_now", "sync_auto", "sync_resolve", "read_artifact", "write_artifact", "list_artifacts", "trigger_agent", "get_triggers", "evaluate_triggers", "start_deploy_poll", "check_deploy", "complete_deploy", "smoke_test", "shared_read", "shared_write", "shared_list"],
                        "Parameters vary by action. write_artifact: {name, content, mime_type}. read_artifact: {name}. trigger_agent: {agent_id, event, payload{}}. start_deploy_poll: {service, environment}. smoke_test: {url, expected_status}. shared_write: {key, value}. shared_read: {key}."
                    )
                },
                {
                    "name": "nucleus_features",
                    "description": "Feature tracking, execution proof generation, and MCP server mounting. Track features through their lifecycle (add, update, validate, search). Generate cryptographic proofs of code execution for audit trails. Mount external MCP servers as sub-tools, discover their capabilities, and invoke their tools through Nucleus orchestration.",
                    "inputSchema": _schema(
                        ["add", "list", "get", "update", "validate", "search", "mount_server", "thanos_snap", "unmount_server", "list_mounted", "discover_tools", "invoke_tool", "traverse_mount", "generate_proof", "get_proof", "list_proofs"],
                        "Parameters vary by action. add: {name, description, status}. update: {feature_id, status, notes}. get: {feature_id}. search: {query}. mount_server: {name, command, args[], env{}}. invoke_tool: {server_name, tool_name, arguments{}}. generate_proof: {action, evidence{}}."
                    )
                },
                {
                    "name": "nucleus_federation",
                    "description": "Federation management for multi-brain coordination across distributed Nucleus instances. Check federation status, join or leave federations, list connected peers, sync state between brains, route requests to the appropriate brain, and monitor federation health. Enables multiple AI agents to share memory and coordinate work.",
                    "inputSchema": _schema(
                        ["status", "join", "leave", "peers", "sync", "route", "health"],
                        "Parameters vary by action. join: {federation_id, brain_path}. leave: {federation_id}. route: {target_brain, action, params{}}. sync: {peer_id, mode: 'full'|'delta'}."
                    )
                },
                {
                    "name": "nucleus_orchestration",
                    "description": "High-level orchestration with satellite view, commitment tracking, open loops, patterns, and metrics. Get a satellite overview of all active work. Scan and manage commitments (promises made during sessions). Track open loops that need closure. Detect recurring patterns in work. Export data and generate weekly challenges. View system-wide metrics.",
                    "inputSchema": _schema(
                        ["satellite", "scan_commitments", "archive_stale", "export", "list_commitments", "close_commitment", "commitment_health", "open_loops", "add_loop", "weekly_challenge", "patterns", "metrics"],
                        "Parameters vary by action. close_commitment: {commitment_id, resolution}. add_loop: {description, context, priority}. export: {format: 'json'|'csv'|'markdown', target}. archive_stale: {days_old}. scan_commitments: {session_id}."
                    )
                },
                {
                    "name": "nucleus_telemetry",
                    "description": "LLM tier management, interaction telemetry, cost tracking, and notification controls. Set and query LLM tier preferences (which models to use for which tasks). Record interactions for training signal generation. Track value ratios and cost dashboards. Manage kill switches for emergency stops. Control PEFS notification pausing/resuming. Record user feedback and mark high-impact interactions.",
                    "inputSchema": _schema(
                        ["set_llm_tier", "get_llm_status", "record_interaction", "value_ratio", "check_kill_switch", "pause_notifications", "resume_notifications", "record_feedback", "mark_high_impact", "check_protocol", "request_handoff", "get_handoffs", "agent_cost_dashboard", "dispatch_metrics"],
                        "Parameters vary by action. set_llm_tier: {tier: 'opus'|'sonnet'|'haiku', context}. record_interaction: {tool_name, tokens_in, tokens_out, latency_ms}. record_feedback: {interaction_id, rating, comment}. mark_high_impact: {interaction_id, reason}. request_handoff: {from_agent, to_agent, context{}}."
                    )
                },
                {
                    "name": "nucleus_slots",
                    "description": "Orchestration slot management, sprint automation, and mission control. Assign work to time-boxed slots for focused execution. Run autopilot sprints that automatically claim and execute tasks. Start and track missions (multi-sprint goals). View status dashboards, halt and resume sprints, force-assign tasks to specific slots.",
                    "inputSchema": _schema(
                        ["orchestrate", "slot_complete", "slot_exhaust", "status_dashboard", "autopilot_sprint", "force_assign", "autopilot_sprint_v2", "start_mission", "mission_status", "halt_sprint", "resume_sprint"],
                        "Parameters vary by action. orchestrate: {strategy, max_slots}. slot_complete: {slot_id, result}. force_assign: {slot_id, task_id}. start_mission: {name, goal, sprint_count}. autopilot_sprint: {duration_minutes, focus_tags[]}."
                    )
                },
                {
                    "name": "nucleus_infra",
                    "description": "Infrastructure monitoring, cloud operations, and strategic planning tools. Track file changes across the project. Check Google Cloud status and services. List running services. Scan marketing logs and synthesize strategy recommendations. Generate status reports, optimize workflows, manage strategy documents, and update roadmaps.",
                    "inputSchema": _schema(
                        ["file_changes", "gcloud_status", "gcloud_services", "list_services", "scan_marketing_log", "synthesize_strategy", "status_report", "optimize_workflow", "manage_strategy", "update_roadmap"],
                        "Parameters vary by action. file_changes: {since, path}. gcloud_services: {project_id}. status_report: {format: 'markdown'|'json', scope}. update_roadmap: {item, status, notes}. optimize_workflow: {target_area}."
                    )
                },
                {
                    "name": "nucleus_agents",
                    "description": "Multi-agent spawning, code review, swarm orchestration, memory search, task ingestion, and real-time dashboards. Spawn specialized sub-agents for parallel work. Apply critic reviews to code changes. Orchestrate agent swarms for complex tasks. Search and read persistent memory. Manage consent flows for sensitive operations. Ingest tasks from external sources. View live dashboards with alerts and thresholds.",
                    "inputSchema": _schema(
                        ["spawn_agent", "apply_critique", "orchestrate_swarm", "search_memory", "read_memory", "respond_to_consent", "list_pending_consents", "critique_code", "fix_code", "session_briefing", "register_session", "handoff_task", "ingest_tasks", "rollback_ingestion", "ingestion_stats", "dashboard", "snapshot_dashboard", "list_dashboard_snapshots", "get_alerts", "set_alert_threshold"],
                        "Parameters vary by action. spawn_agent: {role, goal, tools[]}. critique_code: {file_path, diff}. fix_code: {file_path, issue}. search_memory: {query, limit}. ingest_tasks: {source, file_path}. set_alert_threshold: {metric, threshold, operator: 'gt'|'lt'|'eq'}. handoff_task: {task_id, to_agent, context{}}."
                    )
                },
            ]

            # Aggregate Tools from Mounts
            try:
                mounted_tools = await self.mounter.list_tools()
                tools.extend(mounted_tools)
            except Exception as e:
                logger.error(f"Failed to list mounted tools: {e}")

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": tools
                }
            }
            
        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            try:
                # --- MOUNTER DISPATCH (namespaced tools from mounted servers) ---
                if "__" in name:
                    result = await self.mounter.call_tool(name, args)
                    content = []
                    if hasattr(result, "content"):
                         for item in result.content:
                             item_dict = item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                             content.append(item_dict)
                    else:
                        content = [{"type": "text", "text": str(result)}]
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": content,
                            "isError": getattr(result, "isError", False)
                        }
                    }

                # --- FACADE DISPATCH (12 nucleus_* facade tools) ---
                if name.startswith("nucleus_"):
                    action = args.get("action", "")
                    facade_params = args.get("params", {})
                    result_text = await self._dispatch_facade(name, action, facade_params)
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}],
                            "isError": False
                        }
                    }

                # --- UNKNOWN TOOL ---
                raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                }

    def _get_facade_routers(self) -> Dict[str, Dict[str, Any]]:
        """Build facade routers lazily. Same _impl functions as FastMCP facades."""
        if hasattr(self, "_facade_cache"):
            return self._facade_cache

        def _make_response(success, data=None, error=None):
            r = {"success": success}
            if data is not None:
                r["data"] = data
            if error is not None:
                r["error"] = error
            return r

        # ── nucleus_governance ──
        from mcp_server_nucleus.runtime.hypervisor_ops import (
            lock_resource_impl, unlock_resource_impl, set_hypervisor_mode_impl,
            nucleus_list_directory_impl, nucleus_delete_file_impl,
            watch_resource_impl, hypervisor_status_impl,
        )
        from mcp_server_nucleus.core.egress_proxy import nucleus_curl_impl, nucleus_pip_install_impl

        governance_router = {
            "lock": lambda path: lock_resource_impl(path),
            "unlock": lambda path: unlock_resource_impl(path),
            "set_mode": lambda mode: set_hypervisor_mode_impl(mode),
            "list_directory": lambda path: nucleus_list_directory_impl(path),
            "delete_file": lambda path, confirm=False: nucleus_delete_file_impl(path, confirm=confirm),
            "watch": lambda path: watch_resource_impl(path),
            "status": lambda: hypervisor_status_impl(),
            "curl": lambda url, method="GET": nucleus_curl_impl(url, method),
            "pip_install": lambda package: nucleus_pip_install_impl(package),
        }

        # ── nucleus_engrams ──
        from mcp_server_nucleus.runtime.health_ops import (
            _brain_health_impl, _brain_version_impl, _brain_audit_log_impl,
        )
        from mcp_server_nucleus.runtime.engram_ops import (
            _brain_write_engram_impl, _brain_query_engrams_impl,
            _brain_search_engrams_impl, _brain_governance_status_impl,
        )
        from mcp_server_nucleus.runtime.morning_brief_ops import _morning_brief_impl
        from mcp_server_nucleus.runtime.context_graph import build_context_graph, get_engram_neighbors, render_ascii_graph
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        engrams_router = {
            "health": lambda: _brain_health_impl(),
            "version": lambda: _brain_version_impl(),
            "audit_log": lambda limit=20: _brain_audit_log_impl(limit),
            "write_engram": lambda key, value, context="Decision", intensity=5: _brain_write_engram_impl(key, value, context, intensity),
            "query_engrams": lambda context=None, min_intensity=1, limit=50: _brain_query_engrams_impl(context, min_intensity, limit),
            "search_engrams": lambda query, case_sensitive=False, limit=50: _brain_search_engrams_impl(query, case_sensitive, limit),
            "governance_status": lambda: _brain_governance_status_impl(),
            "morning_brief": lambda: _make_response(True, data=_morning_brief_impl()),
            # Phase 3: God Combos
            "pulse_and_polish": lambda write_engram=True: _make_response(True, data=run_pulse_and_polish(write_engram=write_engram)),
            "self_healing_sre": lambda symptom, write_engram=True: _make_response(True, data=run_self_healing_sre(symptom=symptom, write_engram=write_engram)),
            "fusion_reactor": lambda observation, context="Decision", intensity=6, write_engrams=True: _make_response(True, data=run_fusion_reactor(observation=observation, context=context, intensity=intensity, write_engrams=write_engrams)),
            # Phase 3: Context Graph
            "context_graph": lambda include_edges=True, min_intensity=1: _make_response(True, data=build_context_graph(include_edges=include_edges, min_intensity=min_intensity)),
            "engram_neighbors": lambda key, max_depth=1: _make_response(True, data=get_engram_neighbors(key=key, max_depth=max_depth)),
            "render_graph": lambda max_nodes=30, min_intensity=1: _make_response(True, data={"ascii": render_ascii_graph(max_nodes=max_nodes, min_intensity=min_intensity)}),
            # Phase 3: Billing
            "billing_summary": lambda since_hours=None, group_by="tool": _make_response(True, data=compute_usage_summary(since_hours=since_hours, group_by=group_by)),
        }

        # ── nucleus_tasks ──
        tasks_router = {
            "list": lambda status=None, priority=None, skill=None, claimed_by=None: _make_response(True, data=_list_tasks(status, priority, skill, claimed_by)),
            "get_next": lambda skills: _make_response(True, data=_get_next_task(skills)),
            "claim": lambda task_id, agent_id: _claim_task(task_id, agent_id),
            "update": lambda task_id, updates: _update_task(task_id, updates),
            "add": lambda description, priority=3, blocked_by=None, required_skills=None, source="stdio_server", task_id=None, skip_dep_check=False: _add_task(description, priority, blocked_by, required_skills, source, task_id, skip_dep_check),
        }

        # ── nucleus_sessions (minimal — delegates to session_ops) ──
        from mcp_server_nucleus.runtime.session_ops import (
            _save_session, _resume_session, _list_sessions,
        )
        sessions_router = {
            "save": lambda context, **kw: _save_session(context, **kw),
            "resume": lambda session_id=None: _resume_session(session_id),
            "list": lambda: _list_sessions(),
        }

        # ── nucleus_telemetry (minimal — core metrics) ──
        from mcp_server_nucleus.tools._dispatch import get_dispatch_telemetry

        telemetry_router = {
            "dispatch_metrics": lambda: get_dispatch_telemetry().get_metrics(),
        }

        self._facade_cache = {
            "nucleus_governance": governance_router,
            "nucleus_engrams": engrams_router,
            "nucleus_tasks": tasks_router,
            "nucleus_sessions": sessions_router,
            "nucleus_telemetry": telemetry_router,
            # Remaining facades fall through to a "not available in stdio mode" message
        }
        return self._facade_cache

    async def _dispatch_facade(self, facade_name: str, action: str, params: dict) -> str:
        """Route a facade tool call through the appropriate router."""
        routers = self._get_facade_routers()
        router = routers.get(facade_name)
        if not router:
            return json.dumps({
                "error": f"Facade '{facade_name}' is not available in stdio fallback mode. "
                         f"Use the FastMCP server for full facade support.",
                "available_facades": sorted(routers.keys()),
            }, indent=2)
        return dispatch(action, params, router, facade_name)

def main():
    # Handle diagnostic flags for smoke tests
    if "--help" in sys.argv or "--status" in sys.argv:
        print("NUCLEUS MCP SERVER - OPERATIONAL")
        print(f"Version: 1.0.9")
        print(f"Platform: {sys.platform}")
        print(f"Python: {sys.version.split()[0]}")
        
        # Resolve brain path properly for status report
        brain_env = os.environ.get('NUCLEAR_BRAIN_PATH')
        resolved_brain = Path(brain_env).resolve() if brain_env else Path('.').resolve()
        print(f"Brain Path: {resolved_brain}")
        
        # Build tool list
        server = StdioServer()
        try:
            # Manually trigger the tools/list request
            mcp_output = asyncio.run(server.handle_request({
                "jsonrpc": "2.0",
                "id": "diag",
                "method": "tools/list",
                "params": {}
            }))
            # handle_request might return a dict directly or a JSON string depending on caller
            if isinstance(mcp_output, str):
                mcp_output = json.loads(mcp_output)
                
            tools = [t["name"] for t in mcp_output["result"]["tools"]]
            print(f"Registered Tools: {', '.join(tools)}")
            
            import mcp_server_nucleus
            print("Import Status: OK")
        except Exception as e:
            print(f"Import Status: FAILED ({e})")
            
        sys.exit(0)

    server = StdioServer()
    # Run async main loop
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
