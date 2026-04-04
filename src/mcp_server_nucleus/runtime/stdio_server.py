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
            def _schema(actions, action_desc, param_desc):
                return {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": actions,
                            "description": action_desc
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
                    "description": "Governance, hypervisor, and security controls for the Nucleus Agent OS. Use this tool to enforce file integrity, control security posture, and run automated fix loops. Actions: 'lock' and 'unlock' set/remove immutable flags on files (destructive: unlock removes protection). 'set_mode' switches between 'red' (restricted) and 'blue' (permissive) security modes. 'auto_fix_loop' runs a verify-diagnose-fix-retry cycle on a file until a verification command passes. 'delete_file' permanently removes a file (destructive, irreversible). 'watch' monitors a path for changes. 'curl' makes HTTP requests. 'pip_install' installs Python packages. 'status' returns current governance state. Prerequisites: requires a .brain directory. No authentication needed for local operations.",
                    "inputSchema": _schema(
                        ["auto_fix_loop", "lock", "unlock", "set_mode", "list_directory", "delete_file", "watch", "status", "curl", "pip_install"],
                        "Select the governance action to execute. 'auto_fix_loop' runs automated verification and repair. 'lock'/'unlock' control file immutability. 'set_mode' changes security posture. 'delete_file' is destructive and irreversible. 'curl' proxies external HTTP requests. 'pip_install' installs packages into the current environment.",
                        "Action-specific parameters as key-value pairs. auto_fix_loop: {file_path: string (required, path to verify), verification_command: string (required, shell command that returns 0 on success)}. lock/unlock: {path: string (required, file or directory path)}. set_mode: {mode: string (required, 'red' or 'blue')}. list_directory: {path: string (defaults to brain root)}. delete_file: {path: string (required, DESTRUCTIVE)}. watch: {path: string (required), duration: integer (seconds, default 30)}. curl: {url: string (required), method: string (default 'GET'), headers: object, body: string}. pip_install: {package: string (required, PyPI package name)}."
                    )
                },
                {
                    "name": "nucleus_engrams",
                    "description": "Persistent memory (engrams), health monitoring, observability, and context graphs. Use this tool to store and retrieve knowledge that persists across AI sessions. Engrams are the fundamental memory unit — each has content, tags, source attribution, and metadata. Actions: 'write_engram' stores new knowledge (side effect: writes to .brain/engrams/). 'query_engrams' retrieves by tag/context filter. 'search_engrams' does full-text search. 'health' checks brain integrity. 'version' returns Nucleus version info. 'audit_log' shows decision history. 'morning_brief' generates a daily status report. 'context_graph' builds a relationship map between engrams. 'pulse_and_polish' and 'fusion_reactor' are compound operations that analyze and improve stored knowledge. Prerequisites: .brain directory must exist. All reads are non-destructive.",
                    "inputSchema": _schema(
                        ["health", "version", "audit_log", "write_engram", "query_engrams", "search_engrams", "governance_status", "morning_brief", "pulse_and_polish", "self_healing_sre", "fusion_reactor", "context_graph", "engram_neighbors", "render_graph", "billing_summary"],
                        "Select the engram or observability action. 'write_engram' persists new knowledge. 'query_engrams' filters by context/tags. 'search_engrams' does full-text search. 'health'/'version'/'audit_log' are read-only diagnostics. 'morning_brief' generates a daily summary. 'context_graph' maps engram relationships.",
                        "Action-specific parameters as key-value pairs. write_engram: {content: string (required, the knowledge to store), tags: string[] (optional, categorization), source: string (optional, origin attribution), metadata: object (optional, arbitrary key-value data)}. query_engrams: {query: string (optional), limit: integer (default 10), tags: string[] (optional filter)}. search_engrams: {query: string (required, search term), limit: integer (default 10)}. audit_log: {limit: integer (default 20), level: string ('info'|'warning'|'error')}. context_graph: {engram_id: string (optional, center node)}. engram_neighbors: {engram_id: string (required), depth: integer (default 1, traversal depth)}."
                    )
                },
                {
                    "name": "nucleus_tasks",
                    "description": "Task queue with priority levels, escalation, HITL gates, and cognitive depth tracking. Use this tool to manage work items through their lifecycle and prevent context-switch overhead. Actions: 'add' creates a task with priority (critical/high/medium/low). 'list' shows tasks filtered by status. 'claim' assigns a task to the current agent. 'update' changes status (pending/in_progress/done/blocked). 'escalate' flags a task for human review. 'depth_push'/'depth_pop'/'depth_show' track cognitive nesting depth to prevent rabbit-holing — when depth exceeds max, the system warns before going deeper. 'context_switch' saves current task state and loads another task's context. 'import_jsonl' bulk-imports tasks from a file. Side effects: all mutations write to .brain/tasks/. Prerequisites: .brain directory.",
                    "inputSchema": _schema(
                        ["list", "get_next", "claim", "update", "add", "import_jsonl", "escalate", "depth_push", "depth_pop", "depth_show", "depth_reset", "depth_set_max", "depth_map", "context_switch", "context_switch_status", "context_switch_reset"],
                        "Select the task management action. 'add' creates a new task. 'list'/'get_next' are read-only. 'claim'/'update'/'escalate' modify task state. 'depth_*' actions track cognitive nesting. 'context_switch' saves and restores working context between tasks.",
                        "Action-specific parameters as key-value pairs. add: {title: string (required), description: string (optional), priority: string ('critical'|'high'|'medium'|'low', default 'medium'), tags: string[] (optional)}. update: {task_id: string (required), status: string ('pending'|'in_progress'|'done'|'blocked'), notes: string (optional)}. claim: {task_id: string (required)}. escalate: {task_id: string (required), reason: string (required)}. depth_set_max: {max_depth: integer (required, typically 3-5)}. context_switch: {to_task_id: string (required)}. import_jsonl: {file_path: string (required, path to .jsonl file)}. list: {status: string (optional filter), limit: integer (default 20)}."
                    )
                },
                {
                    "name": "nucleus_sessions",
                    "description": "Session lifecycle management with save, resume, events, state persistence, and checkpoints. Use this tool to maintain continuity across AI conversations. Actions: 'start' begins a new session with a goal. 'save' persists current session state. 'resume' restores a previous session with full context. 'end' closes the active session. 'emit_event' records a structured event (side effect: appends to event log). 'read_events' retrieves event history. 'get_state'/'update_state' manage key-value session state. 'checkpoint' creates a named snapshot for rollback. 'handoff_summary' generates context for session transitions. 'archive_resolved' and 'garbage_collect' clean up old sessions (destructive: removes data). Prerequisites: .brain directory. Sessions persist in .brain/sessions/.",
                    "inputSchema": _schema(
                        ["save", "resume", "list", "check_recent", "end", "start", "archive_resolved", "propose_merges", "garbage_collect", "emit_event", "read_events", "get_state", "update_state", "checkpoint", "resume_checkpoint", "handoff_summary"],
                        "Select the session lifecycle action. 'start'/'end' control session boundaries. 'save'/'resume' persist and restore context. 'emit_event'/'read_events' manage the event log. 'checkpoint'/'resume_checkpoint' create rollback points. 'archive_resolved'/'garbage_collect' are destructive cleanup operations.",
                        "Action-specific parameters as key-value pairs. start: {goal: string (required, session objective), tags: string[] (optional)}. save: {session_id: string (optional, auto-detected), notes: string (optional)}. resume: {session_id: string (required)}. emit_event: {event_type: string (required), data: object (required, event payload)}. read_events: {session_id: string (optional), limit: integer (default 20), event_type: string (optional filter)}. update_state: {key: string (required), value: any (required)}. checkpoint: {label: string (required, descriptive name)}. resume_checkpoint: {checkpoint_id: string (required)}. handoff_summary: {target_agent: string (optional)}."
                    )
                },
                {
                    "name": "nucleus_sync",
                    "description": "Multi-agent synchronization, artifact storage, trigger-based automation, and deployment orchestration. Use this tool to coordinate state across multiple AI agents and manage deployments. Actions: 'identify_agent' registers the current agent identity. 'sync_now' forces immediate state sync between brains. 'write_artifact'/'read_artifact' store and retrieve named data blobs for cross-session sharing (side effect: writes to .brain/artifacts/). 'trigger_agent' dispatches an event to another agent. 'evaluate_triggers' checks all trigger conditions. 'start_deploy_poll' begins monitoring a deployment. 'smoke_test' validates a deployed service endpoint. 'shared_write'/'shared_read' manage a shared key-value store across agents. Prerequisites: .brain directory. Sync requires at least two configured brains.",
                    "inputSchema": _schema(
                        ["identify_agent", "sync_status", "sync_now", "sync_auto", "sync_resolve", "read_artifact", "write_artifact", "list_artifacts", "trigger_agent", "get_triggers", "evaluate_triggers", "start_deploy_poll", "check_deploy", "complete_deploy", "smoke_test", "shared_read", "shared_write", "shared_list"],
                        "Select the synchronization or deployment action. 'identify_agent'/'sync_status' are read-only. 'sync_now' forces a sync (may overwrite remote state). 'write_artifact'/'shared_write' persist data. 'trigger_agent' dispatches events. 'start_deploy_poll'/'smoke_test' manage deployments.",
                        "Action-specific parameters as key-value pairs. write_artifact: {name: string (required, unique identifier), content: string (required), mime_type: string (default 'text/plain')}. read_artifact: {name: string (required)}. trigger_agent: {agent_id: string (required), event: string (required), payload: object (optional)}. start_deploy_poll: {service: string (required), environment: string (required, e.g. 'production')}. smoke_test: {url: string (required), expected_status: integer (default 200)}. shared_write: {key: string (required), value: any (required)}. shared_read: {key: string (required)}. sync_now: {target: string (optional, brain path)}."
                    )
                },
                {
                    "name": "nucleus_features",
                    "description": "Feature lifecycle tracking, cryptographic execution proofs, and external MCP server mounting. Use this tool to track features from proposal to validation, generate tamper-evident proofs of code execution, and compose MCP servers. Actions: 'add' creates a feature record. 'update' changes feature status. 'validate' marks a feature as verified. 'search' finds features by keyword. 'generate_proof' creates a cryptographic receipt of an action for audit compliance (side effect: writes proof to .brain/proofs/). 'mount_server' connects an external MCP server as a sub-tool (side effect: spawns a child process). 'invoke_tool' calls a tool on a mounted server. 'thanos_snap'/'unmount_server' disconnect mounted servers (destructive: kills child process). Prerequisites: .brain directory. Mounting requires the external server's command to be installed.",
                    "inputSchema": _schema(
                        ["add", "list", "get", "update", "validate", "search", "mount_server", "thanos_snap", "unmount_server", "list_mounted", "discover_tools", "invoke_tool", "traverse_mount", "generate_proof", "get_proof", "list_proofs"],
                        "Select the feature, proof, or mount action. 'add'/'update'/'validate' manage feature records. 'search'/'list'/'get' are read-only queries. 'generate_proof' creates audit-grade receipts. 'mount_server' connects external MCP servers. 'unmount_server'/'thanos_snap' disconnect them (destructive).",
                        "Action-specific parameters as key-value pairs. add: {name: string (required), description: string (required), status: string (default 'proposed')}. update: {feature_id: string (required), status: string ('proposed'|'in_progress'|'done'|'cancelled'), notes: string (optional)}. get: {feature_id: string (required)}. search: {query: string (required)}. mount_server: {name: string (required, display name), command: string (required, executable), args: string[] (optional), env: object (optional, environment variables)}. invoke_tool: {server_name: string (required), tool_name: string (required), arguments: object (optional)}. generate_proof: {action: string (required, what was executed), evidence: object (required, execution artifacts)}."
                    )
                },
                {
                    "name": "nucleus_federation",
                    "description": "Federation management for multi-brain coordination across distributed Nucleus instances. Use this tool when multiple AI agents need to share memory, synchronize decisions, or coordinate work across separate .brain directories. Actions: 'join' connects the current brain to a federation (side effect: writes federation config). 'leave' disconnects from a federation. 'peers' lists all connected brains. 'sync' replicates state between brains (mode 'full' overwrites, 'delta' merges changes only). 'route' forwards a request to a specific brain in the federation. 'health' checks connectivity to all peers. 'status' shows current federation membership. Prerequisites: .brain directory. Federation requires network access between brain hosts for remote peers, or filesystem access for local peers.",
                    "inputSchema": _schema(
                        ["status", "join", "leave", "peers", "sync", "route", "health"],
                        "Select the federation action. 'status'/'peers'/'health' are read-only queries. 'join'/'leave' modify federation membership. 'sync' replicates data between brains ('full' mode is destructive — overwrites target). 'route' forwards requests to other brains.",
                        "Action-specific parameters as key-value pairs. join: {federation_id: string (required, unique federation name), brain_path: string (required, path to remote .brain)}. leave: {federation_id: string (required)}. route: {target_brain: string (required, brain identifier), action: string (required, tool action to execute), params: object (optional, forwarded parameters)}. sync: {peer_id: string (required), mode: string ('full' overwrites target or 'delta' merges, default 'delta')}. health: no parameters needed. peers: no parameters needed. status: no parameters needed."
                    )
                },
                {
                    "name": "nucleus_orchestration",
                    "description": "High-level orchestration with satellite overview, commitment tracking, open loop management, pattern detection, and data export. Use this tool for strategic awareness of all active work. Actions: 'satellite' returns a bird's-eye view of tasks, sessions, commitments, and health. 'scan_commitments' extracts promises from session transcripts. 'list_commitments' shows all tracked commitments. 'close_commitment' marks a commitment as fulfilled. 'open_loops' shows unfinished work items. 'add_loop' registers something that needs follow-up. 'patterns' detects recurring themes in work. 'metrics' shows system-wide statistics. 'export' dumps data in json/csv/markdown format. 'weekly_challenge' generates a focus challenge. 'archive_stale' removes old commitments (destructive). Prerequisites: .brain directory with session history for best results.",
                    "inputSchema": _schema(
                        ["satellite", "scan_commitments", "archive_stale", "export", "list_commitments", "close_commitment", "commitment_health", "open_loops", "add_loop", "weekly_challenge", "patterns", "metrics"],
                        "Select the orchestration action. 'satellite'/'list_commitments'/'open_loops'/'patterns'/'metrics' are read-only overviews. 'scan_commitments' analyzes session transcripts. 'close_commitment' resolves a tracked promise. 'archive_stale' is destructive. 'export' generates formatted output.",
                        "Action-specific parameters as key-value pairs. close_commitment: {commitment_id: string (required), resolution: string (required, how it was fulfilled)}. add_loop: {description: string (required), context: string (optional), priority: string ('high'|'medium'|'low', default 'medium')}. export: {format: string ('json'|'csv'|'markdown', default 'json'), target: string (optional, file path)}. archive_stale: {days_old: integer (required, commitments older than this are removed)}. scan_commitments: {session_id: string (optional, defaults to current session)}. satellite: no parameters needed. metrics: no parameters needed."
                    )
                },
                {
                    "name": "nucleus_telemetry",
                    "description": "LLM tier management, interaction recording, cost tracking, kill switch controls, and notification management. Use this tool to configure which AI models are used, track usage costs, and manage safety controls. Actions: 'set_llm_tier' configures model selection (opus/sonnet/haiku) for different task types. 'record_interaction' logs tool usage for training signal generation (side effect: appends to telemetry log). 'value_ratio' calculates cost-effectiveness metrics. 'check_kill_switch' queries whether operations should halt. 'pause_notifications'/'resume_notifications' control PEFS alert delivery. 'record_feedback' captures human ratings on AI outputs. 'mark_high_impact' flags interactions for review. 'agent_cost_dashboard' shows per-agent spending. 'request_handoff' transfers work between agents. Prerequisites: .brain directory. Kill switch state persists in .brain/governance/.",
                    "inputSchema": _schema(
                        ["set_llm_tier", "get_llm_status", "record_interaction", "value_ratio", "check_kill_switch", "pause_notifications", "resume_notifications", "record_feedback", "mark_high_impact", "check_protocol", "request_handoff", "get_handoffs", "agent_cost_dashboard", "dispatch_metrics"],
                        "Select the telemetry or control action. 'get_llm_status'/'value_ratio'/'check_kill_switch'/'agent_cost_dashboard'/'dispatch_metrics' are read-only. 'set_llm_tier' changes model config. 'record_interaction'/'record_feedback'/'mark_high_impact' write telemetry data. 'pause_notifications'/'resume_notifications' toggle alerts.",
                        "Action-specific parameters as key-value pairs. set_llm_tier: {tier: string (required, 'opus'|'sonnet'|'haiku'), context: string (optional, task type this applies to)}. record_interaction: {tool_name: string (required), tokens_in: integer (required), tokens_out: integer (required), latency_ms: integer (required)}. record_feedback: {interaction_id: string (required), rating: integer (required, 1-5 scale), comment: string (optional)}. mark_high_impact: {interaction_id: string (required), reason: string (required)}. request_handoff: {from_agent: string (required), to_agent: string (required), context: object (required, handoff payload)}. check_kill_switch: no parameters needed."
                    )
                },
                {
                    "name": "nucleus_slots",
                    "description": "Orchestration slot management, time-boxed sprint automation, and multi-sprint mission control. Use this tool to structure focused work periods and automate task execution. Actions: 'orchestrate' assigns tasks to time-boxed slots based on strategy. 'autopilot_sprint' runs an automated work cycle that claims tasks, executes them, and reports results. 'start_mission' creates a multi-sprint goal with automatic sprint sequencing. 'status_dashboard' shows all active slots and their progress. 'slot_complete' marks a slot as finished. 'slot_exhaust' marks a slot as time-expired. 'force_assign' overrides automatic assignment (destructive: replaces current slot occupant). 'halt_sprint'/'resume_sprint' pause and continue autopilot execution. Prerequisites: .brain directory with tasks. Sprints require task queue to have claimable items.",
                    "inputSchema": _schema(
                        ["orchestrate", "slot_complete", "slot_exhaust", "status_dashboard", "autopilot_sprint", "force_assign", "autopilot_sprint_v2", "start_mission", "mission_status", "halt_sprint", "resume_sprint"],
                        "Select the slot or sprint action. 'status_dashboard'/'mission_status' are read-only. 'orchestrate' assigns tasks to slots. 'autopilot_sprint' runs automated work cycles. 'start_mission' creates multi-sprint goals. 'force_assign' overrides slot assignment. 'halt_sprint'/'resume_sprint' control execution.",
                        "Action-specific parameters as key-value pairs. orchestrate: {strategy: string (optional, 'fifo'|'priority'|'balanced'), max_slots: integer (default 3)}. slot_complete: {slot_id: string (required), result: string (required, completion summary)}. force_assign: {slot_id: string (required), task_id: string (required)}. start_mission: {name: string (required), goal: string (required), sprint_count: integer (default 3)}. autopilot_sprint: {duration_minutes: integer (default 25, pomodoro-style), focus_tags: string[] (optional, filter tasks by tag)}. mission_status: {mission_id: string (optional, defaults to active mission)}. halt_sprint: no parameters needed. resume_sprint: no parameters needed."
                    )
                },
                {
                    "name": "nucleus_infra",
                    "description": "Infrastructure monitoring, Google Cloud operations, service health checks, and strategic planning tools. Use this tool for operational awareness and infrastructure management. Actions: 'file_changes' lists recently modified files in the project (read-only). 'gcloud_status' checks Google Cloud Platform health. 'gcloud_services' lists enabled GCP services for a project. 'list_services' shows running local services. 'status_report' generates a formatted summary of system state. 'synthesize_strategy' analyzes data and recommends strategic actions. 'optimize_workflow' suggests process improvements for a target area. 'manage_strategy' reads and writes strategy documents (side effect: writes to .brain/strategy/). 'update_roadmap' modifies roadmap items (side effect: writes to .brain/roadmap.json). Prerequisites: .brain directory. GCloud actions require gcloud CLI installed and authenticated.",
                    "inputSchema": _schema(
                        ["file_changes", "gcloud_status", "gcloud_services", "list_services", "scan_marketing_log", "synthesize_strategy", "status_report", "optimize_workflow", "manage_strategy", "update_roadmap"],
                        "Select the infrastructure or strategy action. 'file_changes'/'gcloud_status'/'list_services'/'status_report' are read-only. 'gcloud_services' requires project_id. 'manage_strategy'/'update_roadmap' modify persistent data. 'synthesize_strategy'/'optimize_workflow' generate recommendations.",
                        "Action-specific parameters as key-value pairs. file_changes: {since: string (optional, ISO date or relative like '24h'), path: string (optional, directory to scan)}. gcloud_services: {project_id: string (required, GCP project ID)}. status_report: {format: string ('markdown'|'json', default 'markdown'), scope: string (optional, 'full'|'summary')}. update_roadmap: {item: string (required, roadmap item name), status: string (required, new status), notes: string (optional)}. optimize_workflow: {target_area: string (required, area to analyze)}. manage_strategy: {operation: string ('read'|'write'), key: string, value: string}."
                    )
                },
                {
                    "name": "nucleus_agents",
                    "description": "Multi-agent lifecycle management with spawning, code review, swarm orchestration, memory search, task ingestion, and real-time dashboards. Use this tool to coordinate multiple AI agents working in parallel. Actions: 'spawn_agent' creates a sub-agent with a specific role and goal (side effect: may start a new process). 'critique_code'/'fix_code' run automated code review and repair. 'orchestrate_swarm' coordinates multiple agents on a complex task. 'search_memory'/'read_memory' query the persistent engram store (read-only). 'ingest_tasks' imports tasks from external sources like GitHub issues or CSV files. 'rollback_ingestion' undoes a previous import (destructive). 'dashboard' shows live system metrics. 'set_alert_threshold' configures monitoring alerts. 'respond_to_consent' handles human-in-the-loop approval flows. Prerequisites: .brain directory. Swarm orchestration benefits from multiple agent slots.",
                    "inputSchema": _schema(
                        ["spawn_agent", "apply_critique", "orchestrate_swarm", "search_memory", "read_memory", "respond_to_consent", "list_pending_consents", "critique_code", "fix_code", "session_briefing", "register_session", "handoff_task", "ingest_tasks", "rollback_ingestion", "ingestion_stats", "dashboard", "snapshot_dashboard", "list_dashboard_snapshots", "get_alerts", "set_alert_threshold"],
                        "Select the agent management action. 'search_memory'/'read_memory'/'dashboard'/'get_alerts'/'ingestion_stats' are read-only. 'spawn_agent' creates new agents. 'critique_code'/'fix_code' review and repair code. 'ingest_tasks' imports external tasks. 'rollback_ingestion' is destructive. 'set_alert_threshold' configures monitoring.",
                        "Action-specific parameters as key-value pairs. spawn_agent: {role: string (required, e.g. 'reviewer'|'implementer'|'researcher'), goal: string (required), tools: string[] (optional, tool names to grant)}. critique_code: {file_path: string (required), diff: string (optional, specific diff to review)}. fix_code: {file_path: string (required), issue: string (required, description of the problem)}. search_memory: {query: string (required), limit: integer (default 10)}. ingest_tasks: {source: string (required, 'github'|'csv'|'jsonl'), file_path: string (required)}. set_alert_threshold: {metric: string (required), threshold: number (required), operator: string ('gt'|'lt'|'eq', default 'gt')}. handoff_task: {task_id: string (required), to_agent: string (required), context: object (optional)}."
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
