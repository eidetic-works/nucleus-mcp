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
from mcp_server_nucleus import __version__ as _nucleus_version

# Hypervisor imports — graceful degradation if unavailable
try:
    from mcp_server_nucleus.hypervisor.locker import Locker
except ImportError:
    Locker = None
try:
    from mcp_server_nucleus.hypervisor.watchdog import Watchdog
except ImportError:
    Watchdog = None
try:
    from mcp_server_nucleus.hypervisor.injector import Injector
except ImportError:
    Injector = None

from mcp_server_nucleus.runtime.task_ops import (
    _list_tasks, _add_task, _update_task,
    _claim_task, _get_next_task
)
import asyncio

try:
    from mcp_server_nucleus.runtime.mounter_ops import get_mounter
except ImportError:
    get_mounter = None

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
        
        # Hypervisor components — graceful degradation if unavailable
        self.locker = Locker() if Locker else None
        self.injector = Injector(str(workspace_root)) if Injector else None
        self.watchdog = None
        if Watchdog:
            try:
                self.watchdog = Watchdog(str(workspace_root))
                self.watchdog.start()
            except Exception as e:
                logger.error(f"Failed to start watchdog: {e}")

        self.mounter = get_mounter(self.brain_path) if get_mounter else None

    async def run(self):
        # Restore mounts from persistence
        if self.mounter:
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
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {},
                        "prompts": {},
                    },
                    "serverInfo": {
                        "name": "nucleus",
                        "version": _nucleus_version
                    },
                    "instructions": (
                        "Nucleus is a persistent Agent OS providing memory, governance, "
                        "and compliance for AI agents. Use brain:// resources for live "
                        "context, nucleus_* tools for actions. Start with the cold_start "
                        "prompt or brain://context resource for orientation."
                    ),
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

            def _tool(name, desc, schema, *, title=None, read_only=False, destructive=False, open_world=False, idempotent=False):
                t = {"name": name, "description": desc, "inputSchema": schema}
                t["annotations"] = {
                    "title": title or name.replace("nucleus_", "Nucleus ").replace("_", " ").title(),
                    "readOnlyHint": read_only,
                    "destructiveHint": destructive,
                    "idempotentHint": idempotent,
                    "openWorldHint": open_world,
                }
                return t

            tools = [
                _tool("nucleus_governance",
                    "Enforce file integrity, security posture, and automated verification loops for the Nucleus Agent OS. Use this tool when you need to lock files against modification, switch security modes, or run auto-fix cycles. Do NOT use for task management (use nucleus_tasks), session state (use nucleus_sessions), or memory storage (use nucleus_engrams). Actions: 'lock' sets an immutable flag on a file preventing modification. 'unlock' removes that flag (destructive: re-enables writes). 'set_mode' switches between 'red' (restricted, blocks dangerous ops) and 'blue' (permissive) security modes. 'auto_fix_loop' runs a verify-diagnose-fix-retry cycle: it executes your verification_command, and if it fails, attempts to fix the file, then retries until the command passes or max retries exceeded. 'delete_file' permanently removes a file (destructive, irreversible). 'watch' monitors a file path and returns changes detected within the duration window. 'curl' proxies HTTP requests through Nucleus egress controls. 'pip_install' installs Python packages with governance audit logging. 'status' returns current security mode and lock state. 'list_directory' returns directory contents. Side effects: lock/unlock modify filesystem extended attributes. delete_file removes data permanently. Prerequisites: .brain directory must exist. Returns JSON with {success: boolean, data: object}. Example: {action: 'auto_fix_loop', params: {file_path: 'src/app.py', verification_command: 'python -m py_compile src/app.py'}} returns {success: true, data: {iterations: 2, fixed: true}}.",
                    _schema(
                        ["auto_fix_loop", "lock", "unlock", "set_mode", "list_directory", "delete_file", "watch", "status", "curl", "pip_install"],
                        "Select the governance action to execute. 'auto_fix_loop' runs automated verification and repair. 'lock'/'unlock' control file immutability. 'set_mode' changes security posture between 'red' (restricted) and 'blue' (permissive). 'delete_file' is destructive and irreversible. 'status'/'list_directory' are read-only. 'curl' proxies external HTTP requests through egress controls. 'pip_install' installs packages with audit logging.",
                        "Action-specific parameters as key-value pairs. auto_fix_loop: {file_path: string (required, path to verify), verification_command: string (required, shell command that returns exit code 0 on success)}. lock: {path: string (required, file or directory to make immutable)}. unlock: {path: string (required, file or directory to make writable again)}. set_mode: {mode: string (required, 'red' or 'blue')}. list_directory: {path: string (optional, defaults to .brain root)}. delete_file: {path: string (required, DESTRUCTIVE — permanently removes file)}. watch: {path: string (required, file or directory to monitor), duration: integer (optional, seconds to watch, default 30)}. curl: {url: string (required), method: string (optional, 'GET'|'POST'|'PUT'|'DELETE', default 'GET'), headers: object (optional), body: string (optional)}. pip_install: {package: string (required, PyPI package name)}. status: no parameters needed."
                    ),
                    title="Nucleus Governance", destructive=True, open_world=True
                ),
                _tool("nucleus_engrams",
                    "Store, query, and search persistent memory (engrams) that survives across AI sessions, plus health monitoring and context graph visualization. Use this tool when you need to remember something for future sessions, recall past decisions, search the knowledge base, or check system health. Do NOT use for task tracking (use nucleus_tasks), session lifecycle (use nucleus_sessions), or agent coordination (use nucleus_agents). Engrams are the fundamental memory unit — each has content, optional tags for categorization, source attribution, and arbitrary metadata. Actions: 'write_engram' persists new knowledge to .brain/engrams/ (side effect: creates a JSONL entry). 'query_engrams' retrieves engrams filtered by tag, context, or intensity. 'search_engrams' performs full-text search across all stored knowledge. 'health' checks brain directory integrity and returns file counts and sizes. 'version' returns Nucleus version, Python version, and platform info. 'audit_log' shows the decision audit trail with timestamps. 'morning_brief' generates a daily status report with task summaries, session history, and recommendations. 'governance_status' shows current security mode and lock state. 'context_graph' builds a relationship map between related engrams. 'engram_neighbors' traverses the graph from a specific engram. 'pulse_and_polish' analyzes engram quality and suggests improvements. 'fusion_reactor' cross-references multiple engrams to generate insights. 'billing_summary' shows resource usage. All read operations are non-destructive. Prerequisites: .brain directory must exist. Returns JSON with {success: boolean, data: object}. Example: {action: 'write_engram', params: {content: 'Auth uses JWT with 24h expiry', tags: ['architecture', 'auth']}} returns {success: true, data: {key: 'engram_a1b2c3', stored: true}}.",
                    _schema(
                        ["health", "version", "audit_log", "write_engram", "query_engrams", "search_engrams", "governance_status", "morning_brief", "pulse_and_polish", "self_healing_sre", "fusion_reactor", "context_graph", "engram_neighbors", "render_graph", "billing_summary"],
                        "Select the engram or observability action. 'write_engram' persists new knowledge to disk. 'query_engrams' filters by context, tags, or intensity. 'search_engrams' does full-text search. 'health'/'version'/'audit_log'/'governance_status'/'billing_summary' are read-only diagnostics. 'morning_brief' generates a daily summary. 'context_graph'/'engram_neighbors'/'render_graph' map relationships between engrams. 'pulse_and_polish'/'fusion_reactor' are compound analysis operations.",
                        "Action-specific parameters as key-value pairs. write_engram: {content: string (required, the knowledge to store), tags: string[] (optional, e.g. ['architecture','decision']), source: string (optional, origin attribution like 'code_review'), metadata: object (optional, arbitrary key-value data)}. query_engrams: {query: string (optional, filter text), limit: integer (optional, default 10, max results), tags: string[] (optional, filter by tags)}. search_engrams: {query: string (required, full-text search term), limit: integer (optional, default 10)}. audit_log: {limit: integer (optional, default 20), level: string (optional, 'info'|'warning'|'error')}. context_graph: {engram_id: string (optional, center node ID)}. engram_neighbors: {engram_id: string (required), depth: integer (optional, default 1, traversal depth)}. health/version/morning_brief/governance_status/billing_summary: no parameters needed."
                    ),
                    title="Nucleus Engrams"
                ),
                _tool("nucleus_tasks",
                    "Manage a priority task queue with escalation, human-in-the-loop (HITL) gates, and cognitive depth tracking to prevent context-switch overhead and rabbit-holing. Use this tool when you need to create, assign, update, or track work items. Do NOT use for persistent knowledge storage (use nucleus_engrams), session management (use nucleus_sessions), or multi-agent coordination (use nucleus_agents). Actions: 'add' creates a new task with a priority level (critical/high/medium/low) and optional tags. 'list' shows tasks filtered by status — returns an array of task objects. 'get_next' returns the highest-priority unclaimed task. 'claim' assigns a task to the current agent (side effect: sets status to in_progress). 'update' changes task status (pending/in_progress/done/blocked) with optional notes. 'escalate' flags a task for human review with a reason. 'import_jsonl' bulk-imports tasks from a JSONL file. 'depth_push' increments cognitive nesting depth (tracks how deep into subtasks you've gone). 'depth_pop' decrements it. 'depth_show' returns current depth and max. 'depth_reset' clears depth to zero. 'depth_set_max' sets the maximum allowed depth — system warns when exceeded. 'depth_map' visualizes the full depth tree. 'context_switch' saves current task state and loads another task's context. All mutations write to .brain/tasks/. Prerequisites: .brain directory. Returns JSON with {success: boolean, data: object}. Example: {action: 'add', params: {title: 'Fix auth bug', priority: 'high', tags: ['backend']}} returns {success: true, data: {task_id: 'task_x1y2', created: true}}.",
                    _schema(
                        ["list", "get_next", "claim", "update", "add", "import_jsonl", "escalate", "depth_push", "depth_pop", "depth_show", "depth_reset", "depth_set_max", "depth_map", "context_switch", "context_switch_status", "context_switch_reset"],
                        "Select the task management action. 'add' creates a new task. 'list'/'get_next'/'depth_show'/'depth_map'/'context_switch_status' are read-only. 'claim' assigns a task to the current agent. 'update' changes task status. 'escalate' flags for human review. 'import_jsonl' bulk-imports from file. 'depth_push'/'depth_pop'/'depth_reset'/'depth_set_max' track cognitive nesting depth. 'context_switch' saves and restores working context between tasks.",
                        "Action-specific parameters as key-value pairs. add: {title: string (required), description: string (optional), priority: string (optional, 'critical'|'high'|'medium'|'low', default 'medium'), tags: string[] (optional)}. update: {task_id: string (required), status: string (required, 'pending'|'in_progress'|'done'|'blocked'), notes: string (optional)}. claim: {task_id: string (required)}. escalate: {task_id: string (required), reason: string (required, why escalation is needed)}. depth_set_max: {max_depth: integer (required, typically 3-5)}. context_switch: {to_task_id: string (required)}. import_jsonl: {file_path: string (required, path to .jsonl file with task objects)}. list: {status: string (optional, filter by 'pending'|'in_progress'|'done'|'blocked'), limit: integer (optional, default 20)}. get_next/depth_push/depth_pop/depth_show/depth_reset/depth_map/context_switch_status/context_switch_reset: no parameters needed."
                    ),
                    title="Nucleus Tasks"
                ),
                _tool("nucleus_sessions",
                    "Manage session lifecycles with save/resume, structured event logging, key-value state persistence, and named checkpoints for rollback. Use this tool to maintain continuity across AI conversations, track what happened during a work session, and hand off context between sessions or agents. Do NOT use for persistent knowledge (use nucleus_engrams), task tracking (use nucleus_tasks), or multi-agent sync (use nucleus_sync). Actions: 'start' begins a new session with a stated goal and optional tags. 'save' persists current session state to .brain/sessions/. 'resume' restores a previous session with full context including events, state, and active tasks. 'end' closes the active session and records duration. 'emit_event' appends a structured event to the session log (side effect: writes to events.jsonl). 'read_events' retrieves event history with optional filters. 'get_state' reads the session's key-value state. 'update_state' sets a key-value pair. 'checkpoint' creates a named snapshot of current state for later rollback. 'resume_checkpoint' restores state from a checkpoint. 'handoff_summary' generates context for transitioning to a new session or agent. 'archive_resolved' removes completed sessions (destructive: deletes session files). 'garbage_collect' removes stale sessions older than threshold (destructive). Prerequisites: .brain directory. Returns JSON with {success: boolean, data: object}. Example: {action: 'start', params: {goal: 'Fix authentication bug', tags: ['backend', 'auth']}} returns {success: true, data: {session_id: 'sess_abc123', started: true}}.",
                    _schema(
                        ["save", "resume", "list", "check_recent", "end", "start", "archive_resolved", "propose_merges", "garbage_collect", "emit_event", "read_events", "get_state", "update_state", "checkpoint", "resume_checkpoint", "handoff_summary"],
                        "Select the session lifecycle action. 'start'/'end' control session boundaries. 'save'/'resume' persist and restore full session context. 'emit_event' appends to the event log (write). 'read_events'/'get_state'/'list'/'check_recent'/'handoff_summary' are read-only. 'update_state' modifies key-value session state. 'checkpoint'/'resume_checkpoint' create and restore named rollback points. 'archive_resolved'/'garbage_collect' are destructive cleanup operations that delete session data.",
                        "Action-specific parameters as key-value pairs. start: {goal: string (required, session objective), tags: string[] (optional, categorization)}. save: {session_id: string (optional, auto-detected from active session), notes: string (optional)}. resume: {session_id: string (required, ID from 'list' output)}. emit_event: {event_type: string (required, e.g. 'decision'|'error'|'milestone'), data: object (required, event payload)}. read_events: {session_id: string (optional, defaults to active), limit: integer (optional, default 20), event_type: string (optional, filter by type)}. update_state: {key: string (required), value: any (required)}. checkpoint: {label: string (required, descriptive name like 'before-refactor')}. resume_checkpoint: {checkpoint_id: string (required)}. handoff_summary: {target_agent: string (optional, who receives the handoff)}. end/list/check_recent/get_state/archive_resolved/garbage_collect/propose_merges: no parameters needed."
                    ),
                    title="Nucleus Sessions", destructive=True
                ),
                _tool("nucleus_sync",
                    "Coordinate state across multiple AI agents, store and retrieve named artifacts, manage trigger-based automation, and orchestrate deployments. Use this tool when multiple agents need to share data, when you need to persist artifacts for cross-session use, or when managing deployment workflows. Do NOT use for persistent memory (use nucleus_engrams), session state (use nucleus_sessions), or task assignment (use nucleus_tasks). Actions: 'identify_agent' registers the current agent's identity in the brain. 'sync_status' shows sync state. 'sync_now' forces immediate state replication between brains (may overwrite remote data). 'write_artifact' stores a named data blob in .brain/artifacts/ for cross-session sharing (side effect: creates file). 'read_artifact' retrieves a stored artifact. 'list_artifacts' shows all stored artifacts. 'trigger_agent' dispatches an event to another registered agent. 'get_triggers'/'evaluate_triggers' manage automated trigger rules. 'start_deploy_poll' begins monitoring a deployment service for readiness. 'check_deploy' queries deployment status. 'complete_deploy' marks deployment as finished. 'smoke_test' validates a deployed service endpoint by hitting its URL. 'shared_read'/'shared_write'/'shared_list' manage a shared key-value store visible to all agents. Prerequisites: .brain directory. Sync operations require at least two configured brains. Deploy actions require network access. Returns JSON with {success: boolean, data: object}. Example: {action: 'write_artifact', params: {name: 'api_schema', content: '{...}', mime_type: 'application/json'}} returns {success: true, data: {stored: true, path: '.brain/artifacts/api_schema'}}.",
                    _schema(
                        ["identify_agent", "sync_status", "sync_now", "sync_auto", "sync_resolve", "read_artifact", "write_artifact", "list_artifacts", "trigger_agent", "get_triggers", "evaluate_triggers", "start_deploy_poll", "check_deploy", "complete_deploy", "smoke_test", "shared_read", "shared_write", "shared_list"],
                        "Select the synchronization, artifact, trigger, or deployment action. 'identify_agent'/'sync_status'/'read_artifact'/'list_artifacts'/'get_triggers'/'check_deploy'/'shared_read'/'shared_list' are read-only. 'sync_now' forces state replication (may overwrite remote). 'write_artifact'/'shared_write' persist data. 'trigger_agent' dispatches events to other agents. 'evaluate_triggers' runs all trigger rules. 'start_deploy_poll'/'smoke_test' interact with external services.",
                        "Action-specific parameters as key-value pairs. write_artifact: {name: string (required, unique identifier), content: string (required, artifact data), mime_type: string (optional, default 'text/plain')}. read_artifact: {name: string (required)}. trigger_agent: {agent_id: string (required), event: string (required, event name), payload: object (optional)}. start_deploy_poll: {service: string (required, service name), environment: string (required, e.g. 'production'|'staging')}. smoke_test: {url: string (required, endpoint URL), expected_status: integer (optional, default 200)}. shared_write: {key: string (required), value: any (required)}. shared_read: {key: string (required)}. sync_now: {target: string (optional, target brain path)}. identify_agent/sync_status/list_artifacts/get_triggers/evaluate_triggers/check_deploy/complete_deploy/shared_list/sync_auto/sync_resolve: no parameters needed."
                    ),
                    title="Nucleus Sync", open_world=True
                ),
                _tool("nucleus_features",
                    "Track features through their lifecycle, generate cryptographic execution proofs for audit compliance, and mount external MCP servers as composable sub-tools. Use this tool when you need to register a feature, verify code execution, or integrate another MCP server. Do NOT use for task tracking (use nucleus_tasks), memory storage (use nucleus_engrams), or agent spawning (use nucleus_agents). Actions: 'add' creates a feature record with name, description, and initial status. 'update' changes feature status through its lifecycle (proposed/in_progress/done/cancelled). 'validate' marks a feature as verified with evidence. 'list' shows all features. 'get' retrieves one feature by ID. 'search' finds features by keyword. 'generate_proof' creates a cryptographic Ed25519-signed receipt of a code execution for audit compliance (side effect: writes to .brain/proofs/). 'get_proof'/'list_proofs' retrieve stored proofs. 'mount_server' connects an external MCP server as a sub-tool (side effect: spawns a child process). 'discover_tools' lists tools available on a mounted server. 'invoke_tool' calls a tool on a mounted server and returns its result. 'traverse_mount' navigates the mount hierarchy. 'thanos_snap'/'unmount_server' disconnect mounted servers (destructive: kills child process, removes mount config). Prerequisites: .brain directory. Mounting requires the external server command to be installed locally. Returns JSON with {success: boolean, data: object}. Example: {action: 'add', params: {name: 'JWT Auth', description: 'Token-based authentication', status: 'in_progress'}} returns {success: true, data: {feature_id: 'feat_xyz', created: true}}.",
                    _schema(
                        ["add", "list", "get", "update", "validate", "search", "mount_server", "thanos_snap", "unmount_server", "list_mounted", "discover_tools", "invoke_tool", "traverse_mount", "generate_proof", "get_proof", "list_proofs"],
                        "Select the feature, proof, or mount action. 'add'/'update'/'validate' manage feature lifecycle records. 'search'/'list'/'get'/'list_mounted'/'discover_tools'/'get_proof'/'list_proofs'/'traverse_mount' are read-only queries. 'generate_proof' creates a cryptographic execution receipt. 'mount_server' connects an external MCP server (spawns process). 'invoke_tool' calls a mounted server's tool. 'unmount_server'/'thanos_snap' disconnect and remove mounted servers (destructive: kills process).",
                        "Action-specific parameters as key-value pairs. add: {name: string (required), description: string (required), status: string (optional, default 'proposed')}. update: {feature_id: string (required), status: string (required, 'proposed'|'in_progress'|'done'|'cancelled'), notes: string (optional)}. get: {feature_id: string (required)}. search: {query: string (required, keyword search)}. validate: {feature_id: string (required), evidence: string (optional)}. mount_server: {name: string (required, display name), command: string (required, executable path), args: string[] (optional, command arguments), env: object (optional, environment variables)}. invoke_tool: {server_name: string (required, mounted server name), tool_name: string (required), arguments: object (optional)}. generate_proof: {action: string (required, what was executed), evidence: object (required, execution artifacts)}. unmount_server: {name: string (required)}. list/list_mounted/discover_tools/get_proof/list_proofs/traverse_mount: no parameters needed."
                    ),
                    title="Nucleus Features", destructive=True
                ),
                _tool("nucleus_federation",
                    "Coordinate multiple Nucleus brain instances across distributed environments by joining federations, syncing state between peers, and routing requests to the appropriate brain. Use this tool when multiple AI agents on different machines or projects need to share memory, synchronize decisions, or coordinate work across separate .brain directories. Do NOT use for single-brain agent coordination (use nucleus_agents), artifact sharing within one brain (use nucleus_sync), or session handoffs (use nucleus_sessions). Actions: 'status' returns current federation membership and connection state (read-only). 'join' connects the current brain to a named federation (side effect: writes federation config to .brain/federation/). 'leave' disconnects from a federation. 'peers' lists all connected brains with their last-sync timestamps. 'sync' replicates state between brains — 'delta' mode merges only changes (safe), 'full' mode overwrites the target entirely (destructive). 'route' forwards a tool request to a specific peer brain and returns its response. 'health' checks connectivity and latency to all peers. Prerequisites: .brain directory. Federation requires filesystem access for local peers or network access for remote peers. Returns JSON with {success: boolean, data: object}. Example: {action: 'join', params: {federation_id: 'team-alpha', brain_path: '/shared/project/.brain'}} returns {success: true, data: {joined: true, peer_count: 3}}.",
                    _schema(
                        ["status", "join", "leave", "peers", "sync", "route", "health"],
                        "Select the federation action. 'status'/'peers'/'health' are read-only queries returning federation state. 'join' connects to a federation (writes config). 'leave' disconnects. 'sync' replicates data between brains — 'full' mode is destructive and overwrites the target brain. 'route' forwards a request to a specific peer brain.",
                        "Action-specific parameters as key-value pairs. join: {federation_id: string (required, unique federation name), brain_path: string (required, filesystem path to remote .brain directory)}. leave: {federation_id: string (required)}. route: {target_brain: string (required, brain identifier from 'peers' output), action: string (required, tool action to execute on remote), params: object (optional, parameters forwarded to remote tool)}. sync: {peer_id: string (required, brain identifier), mode: string (optional, 'full' overwrites target entirely or 'delta' merges changes only, default 'delta')}. status/peers/health: no parameters needed."
                    ),
                    title="Nucleus Federation"
                ),
                _tool("nucleus_orchestration",
                    "Get strategic awareness of all active work through satellite overviews, commitment tracking, open loop management, pattern detection, and data export. Use this tool when you need a high-level view of project state, want to track promises made during sessions, identify recurring patterns, or export data. Do NOT use for individual task CRUD (use nucleus_tasks), session management (use nucleus_sessions), or slot-based sprint execution (use nucleus_slots). Actions: 'satellite' returns a comprehensive bird's-eye view of tasks, sessions, commitments, health scores, and frontier status — the best starting point for understanding current state. 'scan_commitments' extracts promises and action items from session transcripts. 'list_commitments' shows all tracked commitments. 'close_commitment' marks a commitment as fulfilled with a resolution note. 'commitment_health' scores how well commitments are being met. 'open_loops' shows unfinished work items that need closure. 'add_loop' registers something that needs follow-up. 'patterns' detects recurring themes across sessions and tasks. 'metrics' shows system-wide statistics (tool usage, event counts, memory growth). 'export' dumps data in json/csv/markdown format. 'weekly_challenge' generates a focused challenge based on recent activity. 'archive_stale' removes commitments older than N days (destructive: deletes records). Prerequisites: .brain directory with session history for best results. Returns JSON with {success: boolean, data: object}. Example: {action: 'satellite'} returns {success: true, data: {tasks: {total: 12, in_progress: 3}, sessions: {active: 'sess_abc'}, commitments: {open: 5, overdue: 1}}}.",
                    _schema(
                        ["satellite", "scan_commitments", "archive_stale", "export", "list_commitments", "close_commitment", "commitment_health", "open_loops", "add_loop", "weekly_challenge", "patterns", "metrics"],
                        "Select the orchestration action. 'satellite'/'list_commitments'/'commitment_health'/'open_loops'/'patterns'/'metrics' are read-only overviews. 'scan_commitments' analyzes session transcripts to extract promises. 'close_commitment' resolves a tracked commitment. 'add_loop' registers an open item. 'export' generates formatted output. 'weekly_challenge' creates a focus challenge. 'archive_stale' removes old commitments (destructive: deletes data).",
                        "Action-specific parameters as key-value pairs. close_commitment: {commitment_id: string (required), resolution: string (required, how the commitment was fulfilled)}. add_loop: {description: string (required, what needs follow-up), context: string (optional, background info), priority: string (optional, 'high'|'medium'|'low', default 'medium')}. export: {format: string (optional, 'json'|'csv'|'markdown', default 'json'), target: string (optional, file path to write to)}. archive_stale: {days_old: integer (required, commitments older than this many days are removed)}. scan_commitments: {session_id: string (optional, defaults to current session)}. satellite/list_commitments/commitment_health/open_loops/patterns/metrics/weekly_challenge: no parameters needed."
                    ),
                    title="Nucleus Orchestration", destructive=True
                ),
                _tool("nucleus_telemetry",
                    "Configure LLM model tiers, record interaction telemetry for training signal generation, track costs, and manage safety controls including kill switches and notification pausing. Use this tool when you need to set which AI models are used for different task types, log usage data, check cost dashboards, or control emergency stops. Do NOT use for persistent memory (use nucleus_engrams), task management (use nucleus_tasks), or agent lifecycle (use nucleus_agents). Actions: 'set_llm_tier' configures which model (opus/sonnet/haiku) to use for specific task contexts. 'get_llm_status' returns current tier configuration. 'record_interaction' logs a tool invocation with token counts and latency for training signal generation (side effect: appends to telemetry log). 'value_ratio' calculates cost-effectiveness metrics across recent interactions. 'check_kill_switch' queries whether all operations should halt — returns boolean. 'pause_notifications' temporarily stops PEFS alert delivery. 'resume_notifications' re-enables alerts. 'record_feedback' captures human ratings (1-5 scale) on AI outputs for DPO training pairs. 'mark_high_impact' flags an interaction for human review. 'agent_cost_dashboard' shows per-agent token spending and cost breakdown. 'request_handoff' initiates a work transfer between agents. 'dispatch_metrics' shows tool dispatch statistics. Prerequisites: .brain directory. Kill switch state persists in .brain/governance/kill_switch.json. Returns JSON with {success: boolean, data: object}. Example: {action: 'record_feedback', params: {interaction_id: 'int_abc', rating: 5, comment: 'Perfect fix'}} returns {success: true, data: {recorded: true, dpo_pair_created: true}}.",
                    _schema(
                        ["set_llm_tier", "get_llm_status", "record_interaction", "value_ratio", "check_kill_switch", "pause_notifications", "resume_notifications", "record_feedback", "mark_high_impact", "check_protocol", "request_handoff", "get_handoffs", "agent_cost_dashboard", "dispatch_metrics"],
                        "Select the telemetry or safety control action. 'get_llm_status'/'value_ratio'/'check_kill_switch'/'agent_cost_dashboard'/'dispatch_metrics'/'check_protocol'/'get_handoffs' are read-only queries. 'set_llm_tier' changes model configuration. 'record_interaction'/'record_feedback'/'mark_high_impact' write telemetry data to disk. 'pause_notifications'/'resume_notifications' toggle PEFS alert delivery. 'request_handoff' initiates agent-to-agent work transfer.",
                        "Action-specific parameters as key-value pairs. set_llm_tier: {tier: string (required, 'opus'|'sonnet'|'haiku'), context: string (optional, task type this tier applies to, e.g. 'code_review')}. record_interaction: {tool_name: string (required), tokens_in: integer (required), tokens_out: integer (required), latency_ms: integer (required)}. record_feedback: {interaction_id: string (required), rating: integer (required, 1 to 5 scale), comment: string (optional)}. mark_high_impact: {interaction_id: string (required), reason: string (required, why this is high-impact)}. request_handoff: {from_agent: string (required), to_agent: string (required), context: object (required, handoff payload with task info)}. get_llm_status/value_ratio/check_kill_switch/pause_notifications/resume_notifications/check_protocol/get_handoffs/agent_cost_dashboard/dispatch_metrics: no parameters needed."
                    ),
                    title="Nucleus Telemetry"
                ),
                _tool("nucleus_slots",
                    "Structure focused work into time-boxed slots, run automated sprints that claim and execute tasks, and manage multi-sprint missions with automatic sequencing. Use this tool when you want to organize execution into focused work periods, automate task execution cycles, or track progress toward multi-sprint goals. Do NOT use for individual task CRUD (use nucleus_tasks), session lifecycle (use nucleus_sessions), or strategic overview (use nucleus_orchestration). Actions: 'orchestrate' assigns tasks to time-boxed slots based on a strategy (fifo/priority/balanced). 'autopilot_sprint' runs an automated 25-minute pomodoro-style work cycle — it claims the next task, executes it, records results, and moves to the next until time expires. 'start_mission' creates a multi-sprint goal with automatic sprint sequencing. 'status_dashboard' shows all active slots, their assigned tasks, and progress. 'mission_status' shows progress toward a mission goal. 'slot_complete' marks a slot as finished with a result summary. 'slot_exhaust' marks a slot as time-expired without completion. 'force_assign' overrides automatic slot assignment (destructive: replaces current slot occupant). 'halt_sprint' pauses an active autopilot sprint. 'resume_sprint' continues a halted sprint. Prerequisites: .brain directory with tasks in the queue. Sprints require claimable tasks to be available. Returns JSON with {success: boolean, data: object}. Example: {action: 'autopilot_sprint', params: {duration_minutes: 25, focus_tags: ['backend']}} returns {success: true, data: {sprint_id: 'sprint_001', tasks_completed: 3, duration: '24m'}}.",
                    _schema(
                        ["orchestrate", "slot_complete", "slot_exhaust", "status_dashboard", "autopilot_sprint", "force_assign", "autopilot_sprint_v2", "start_mission", "mission_status", "halt_sprint", "resume_sprint"],
                        "Select the slot, sprint, or mission action. 'status_dashboard'/'mission_status' are read-only progress views. 'orchestrate' assigns tasks to time-boxed slots. 'autopilot_sprint'/'autopilot_sprint_v2' run automated work cycles. 'start_mission' creates multi-sprint goals. 'slot_complete'/'slot_exhaust' close slots. 'force_assign' overrides slot assignment (destructive: replaces occupant). 'halt_sprint'/'resume_sprint' pause and continue sprint execution.",
                        "Action-specific parameters as key-value pairs. orchestrate: {strategy: string (optional, 'fifo'|'priority'|'balanced', default 'priority'), max_slots: integer (optional, default 3, maximum concurrent slots)}. slot_complete: {slot_id: string (required), result: string (required, completion summary)}. slot_exhaust: {slot_id: string (required)}. force_assign: {slot_id: string (required), task_id: string (required)}. start_mission: {name: string (required), goal: string (required, mission objective), sprint_count: integer (optional, default 3)}. autopilot_sprint: {duration_minutes: integer (optional, default 25, pomodoro-style), focus_tags: string[] (optional, only claim tasks with these tags)}. mission_status: {mission_id: string (optional, defaults to active mission)}. status_dashboard/halt_sprint/resume_sprint: no parameters needed."
                    ),
                    title="Nucleus Slots"
                ),
                _tool("nucleus_infra",
                    "Monitor infrastructure health, manage Google Cloud Platform services, track file changes across your project, and generate strategic planning reports. Use this tool when you need operational awareness of your development environment, GCP service status, or strategic recommendations. Do NOT use for code-level tasks (use nucleus_tasks), memory (use nucleus_engrams), or deployment orchestration (use nucleus_sync with deploy actions). Actions: 'file_changes' lists recently modified files in the project directory with timestamps and sizes (read-only, useful for detecting unexpected modifications). 'gcloud_status' checks Google Cloud Platform availability and incident status. 'gcloud_services' lists all enabled GCP services for a project (requires project_id). 'list_services' shows locally running services detected on common ports. 'status_report' generates a formatted markdown or JSON summary of brain health, task status, session state, and frontier metrics. 'synthesize_strategy' analyzes accumulated data (engrams, patterns, metrics) and recommends strategic actions. 'optimize_workflow' suggests process improvements for a named area. 'manage_strategy' reads and writes strategy documents to .brain/strategy/ (side effect: creates or modifies files). 'update_roadmap' modifies roadmap items in .brain/roadmap.json (side effect: modifies file). 'scan_marketing_log' analyzes marketing-related log entries. Prerequisites: .brain directory. GCloud actions require 'gcloud' CLI installed and authenticated via 'gcloud auth login'. Returns JSON with {success: boolean, data: object}. Example: {action: 'file_changes', params: {since: '24h', path: 'src/'}} returns {success: true, data: {changes: [{path: 'src/app.py', modified: '2026-04-04T10:00:00Z', size: 1234}]}}.",
                    _schema(
                        ["file_changes", "gcloud_status", "gcloud_services", "list_services", "scan_marketing_log", "synthesize_strategy", "status_report", "optimize_workflow", "manage_strategy", "update_roadmap"],
                        "Select the infrastructure, cloud, or strategy action. 'file_changes'/'gcloud_status'/'gcloud_services'/'list_services'/'status_report' are read-only queries. 'scan_marketing_log' analyzes log data. 'synthesize_strategy'/'optimize_workflow' generate recommendations without side effects. 'manage_strategy' reads or writes strategy documents to disk. 'update_roadmap' modifies the roadmap file.",
                        "Action-specific parameters as key-value pairs. file_changes: {since: string (optional, ISO date like '2026-04-01' or relative like '24h'|'7d', default '24h'), path: string (optional, directory to scan, default project root)}. gcloud_services: {project_id: string (required, GCP project ID, e.g. 'my-project-123')}. status_report: {format: string (optional, 'markdown'|'json', default 'markdown'), scope: string (optional, 'full'|'summary', default 'full')}. update_roadmap: {item: string (required, roadmap item name), status: string (required, new status value), notes: string (optional)}. optimize_workflow: {target_area: string (required, area to analyze, e.g. 'testing'|'deployment'|'code_review')}. manage_strategy: {operation: string (required, 'read'|'write'), key: string (optional, strategy document name), value: string (optional, content for write)}. gcloud_status/list_services/scan_marketing_log/synthesize_strategy: no parameters needed."
                    ),
                    title="Nucleus Infrastructure", open_world=True
                ),
                _tool("nucleus_agents",
                    "Manage multi-agent lifecycles including spawning specialized sub-agents, running automated code review and repair, orchestrating agent swarms for complex tasks, searching persistent memory, ingesting tasks from external sources, and viewing real-time dashboards. Use this tool when you need to create new agents, review or fix code, coordinate parallel work, or query the knowledge base. Do NOT use for individual task CRUD (use nucleus_tasks), session management (use nucleus_sessions), or cross-brain sync (use nucleus_federation). Actions: 'spawn_agent' creates a sub-agent with a specific role (reviewer/implementer/researcher) and goal (side effect: may start a new process). 'critique_code' runs automated code review on a file, returning issues and suggestions. 'fix_code' attempts automated repair of a described issue in a file. 'apply_critique' applies review feedback. 'orchestrate_swarm' coordinates multiple agents working on a complex task in parallel. 'search_memory' queries the persistent engram store by keyword (read-only). 'read_memory' retrieves a specific engram by key. 'ingest_tasks' imports tasks from external sources like GitHub issues, CSV, or JSONL files (side effect: creates tasks). 'rollback_ingestion' undoes a previous import (destructive: deletes imported tasks). 'ingestion_stats' shows import history. 'dashboard' shows live system metrics including agent count, task throughput, and memory usage. 'snapshot_dashboard'/'list_dashboard_snapshots' manage dashboard snapshots. 'get_alerts'/'set_alert_threshold' configure monitoring alerts. 'respond_to_consent'/'list_pending_consents' handle human-in-the-loop approval flows for sensitive operations. Prerequisites: .brain directory. Returns JSON with {success: boolean, data: object}. Example: {action: 'search_memory', params: {query: 'authentication', limit: 5}} returns {success: true, data: {results: [{key: 'engram_x', content: 'Auth uses JWT...', score: 0.95}]}}.",
                    _schema(
                        ["spawn_agent", "apply_critique", "orchestrate_swarm", "search_memory", "read_memory", "respond_to_consent", "list_pending_consents", "critique_code", "fix_code", "session_briefing", "register_session", "handoff_task", "ingest_tasks", "rollback_ingestion", "ingestion_stats", "dashboard", "snapshot_dashboard", "list_dashboard_snapshots", "get_alerts", "set_alert_threshold"],
                        "Select the agent management action. 'search_memory'/'read_memory'/'dashboard'/'get_alerts'/'ingestion_stats'/'list_pending_consents'/'session_briefing'/'list_dashboard_snapshots' are read-only. 'spawn_agent' creates a new sub-agent. 'critique_code'/'fix_code'/'apply_critique' handle automated code review and repair. 'orchestrate_swarm' coordinates parallel agents. 'ingest_tasks' imports from external sources. 'rollback_ingestion' is destructive (deletes imported tasks). 'set_alert_threshold' configures monitoring. 'respond_to_consent' approves/denies sensitive operations.",
                        "Action-specific parameters as key-value pairs. spawn_agent: {role: string (required, 'reviewer'|'implementer'|'researcher'|'planner'), goal: string (required, what the agent should accomplish), tools: string[] (optional, tool names to grant access to)}. critique_code: {file_path: string (required, path to file to review), diff: string (optional, specific diff to focus review on)}. fix_code: {file_path: string (required), issue: string (required, description of the problem to fix)}. search_memory: {query: string (required, search term), limit: integer (optional, default 10)}. read_memory: {key: string (required, engram key)}. ingest_tasks: {source: string (required, 'github'|'csv'|'jsonl'), file_path: string (required, path to source file)}. set_alert_threshold: {metric: string (required, metric name), threshold: number (required), operator: string (optional, 'gt'|'lt'|'eq', default 'gt')}. handoff_task: {task_id: string (required), to_agent: string (required), context: object (optional)}. respond_to_consent: {consent_id: string (required), approved: boolean (required)}. rollback_ingestion/ingestion_stats/dashboard/snapshot_dashboard/list_dashboard_snapshots/get_alerts/list_pending_consents/session_briefing/register_session/apply_critique/orchestrate_swarm: no parameters needed."
                    ),
                    title="Nucleus Agents", destructive=True
                ),
            ]

            # Aggregate Tools from Mounts
            if self.mounter:
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
                if "__" in name and self.mounter:
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

            except ValueError as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": str(e)}
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resources": self._get_resources_list()}
            }

        elif method == "resources/read":
            uri = request.get("params", {}).get("uri", "")
            try:
                content = self._read_resource(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [{"uri": uri, "mimeType": "application/json", "text": content}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": str(e)}
                }

        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {
                            "name": "activate_synthesizer",
                            "description": "Activate Synthesizer agent to orchestrate the current sprint.",
                            "arguments": []
                        },
                        {
                            "name": "start_sprint",
                            "description": "Initialize a new sprint with the given goal.",
                            "arguments": [
                                {"name": "goal", "description": "Sprint goal (default: 'MVP Launch')", "required": False}
                            ]
                        },
                        {
                            "name": "cold_start",
                            "description": "Get instant context when starting a new session. Call this first.",
                            "arguments": []
                        },
                    ]
                }
            }

        elif method == "prompts/get":
            prompt_name = request.get("params", {}).get("name", "")
            prompt_args = request.get("params", {}).get("arguments", {})
            try:
                text = self._get_prompt(prompt_name, prompt_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "description": f"Prompt: {prompt_name}",
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": text}}
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": str(e)}
                }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method.startswith("notifications/"):
            # All notifications (initialized, cancelled, etc.) — no response per spec
            return None

        else:
            # JSON-RPC 2.0: unknown methods MUST return -32601
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
            return None

    def _get_resources_list(self):
        """Return 8 brain:// resource descriptors."""
        return [
            {"uri": "brain://state", "name": "Brain State",
             "description": "Live state.json content — current session, active tasks, config",
             "mimeType": "application/json"},
            {"uri": "brain://events", "name": "Brain Events",
             "description": "Recent events from the event ledger with timestamps",
             "mimeType": "application/json"},
            {"uri": "brain://triggers", "name": "Trigger Definitions",
             "description": "Automation trigger rules and their evaluation state",
             "mimeType": "application/json"},
            {"uri": "brain://depth", "name": "Depth Tracking",
             "description": "Current cognitive depth state — shows nesting level in task tree",
             "mimeType": "application/json"},
            {"uri": "brain://context", "name": "Cold Start Context",
             "description": "Full context for new sessions — read this first in any new conversation",
             "mimeType": "text/plain"},
            {"uri": "brain://changes", "name": "Change Ledger",
             "description": "Monotonic version tracker — poll to detect staleness across all resources",
             "mimeType": "application/json"},
            {"uri": "brain://traces", "name": "Decision Traces",
             "description": "Recent DecisionMade traces from the DSoR decision ledger",
             "mimeType": "application/json"},
            {"uri": "brain://health", "name": "Three Frontiers Health",
             "description": "GROUND/ALIGN/COMPOUND status — verification pass rates, alignment verdicts, delta counts",
             "mimeType": "application/json"},
        ]

    def _read_resource(self, uri: str) -> str:
        """Read a brain:// resource by URI. Lazy imports to avoid startup cost."""
        try:
            if uri == "brain://state":
                from mcp_server_nucleus.runtime.common import _get_state
                return json.dumps(_get_state(), indent=2)
            elif uri == "brain://events":
                from mcp_server_nucleus.runtime.event_ops import _read_events
                return json.dumps(_read_events(limit=20), indent=2)
            elif uri == "brain://triggers":
                from mcp_server_nucleus.runtime.trigger_ops import _get_triggers_impl
                return json.dumps(_get_triggers_impl(), indent=2)
            elif uri == "brain://depth":
                from mcp_server_nucleus.runtime.depth_ops import _depth_show
                return json.dumps(_depth_show(), indent=2)
            elif uri == "brain://context":
                from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
                return _resource_context_impl()
            elif uri == "brain://changes":
                from mcp_server_nucleus.runtime.event_bus import get_change_ledger
                return json.dumps(get_change_ledger().get_snapshot(), indent=2)
            elif uri == "brain://traces":
                from mcp_server_nucleus.runtime.engram_ops import _dsor_query_decisions_impl
                return _dsor_query_decisions_impl(limit=50)
            elif uri == "brain://health":
                return self._read_health_resource()
            else:
                raise ValueError(f"Unknown resource URI: {uri}")
        except ValueError:
            raise
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _read_health_resource(self) -> str:
        """Three Frontiers health — shared with server.py."""
        try:
            from mcp_server_nucleus.runtime.common import get_brain_path
            from mcp_server_nucleus.runtime.hardening import safe_read_jsonl
            from datetime import datetime, timezone
            brain = get_brain_path()
            result = {}
            # GROUND
            vlog = Path(brain) / "verification_log.jsonl"
            if vlog.exists():
                receipts = safe_read_jsonl(vlog)
                passed = sum(1 for r in receipts if not r.get("tiers_failed"))
                result["ground"] = {"total": len(receipts), "pass_rate": round(passed / max(len(receipts), 1) * 100, 1)}
            else:
                result["ground"] = {"total": 0}
            # ALIGN
            vpath = Path(brain) / "driver" / "human_verdicts.jsonl"
            if vpath.exists():
                verdicts = safe_read_jsonl(vpath)
                non_pending = [v for v in verdicts if v.get("verdict") != "pending"]
                result["align"] = {
                    "total": len(non_pending),
                    "corrected": sum(1 for v in non_pending if v.get("verdict") == "corrected"),
                    "accepted": sum(1 for v in non_pending if v.get("verdict") == "accepted"),
                }
            else:
                result["align"] = {"total": 0}
            # COMPOUND
            deltas_path = Path(brain) / "deltas" / "deltas.jsonl"
            if deltas_path.exists():
                deltas = safe_read_jsonl(deltas_path)
                result["compound"] = {"deltas": len(deltas)}
            else:
                result["compound"] = {"deltas": 0}
            result["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_prompt(self, name: str, arguments: dict) -> str:
        """Get a prompt by name. Lazy imports."""
        try:
            from mcp_server_nucleus.runtime.context_ops import (
                _activate_synthesizer_prompt,
                _start_sprint_prompt,
                _cold_start_prompt,
            )
        except ImportError:
            return f"Prompt '{name}' not available (context_ops not installed)"

        if name == "activate_synthesizer":
            return _activate_synthesizer_prompt()
        elif name == "start_sprint":
            goal = arguments.get("goal", "MVP Launch")
            return _start_sprint_prompt(goal)
        elif name == "cold_start":
            return _cold_start_prompt()
        else:
            raise ValueError(f"Unknown prompt: {name}")

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
        # Optional modules — guarded so core engram ops survive missing deps
        try:
            from mcp_server_nucleus.runtime.morning_brief_ops import _morning_brief_impl
        except ImportError:
            _morning_brief_impl = None
        try:
            from mcp_server_nucleus.runtime.context_graph import build_context_graph, get_engram_neighbors, render_ascii_graph
        except ImportError:
            build_context_graph = get_engram_neighbors = render_ascii_graph = None
        try:
            from mcp_server_nucleus.runtime.billing import compute_usage_summary
        except ImportError:
            compute_usage_summary = None

        def _optional_missing(name):
            return _make_response(False, error=f"{name} not available in this build")

        # God Combos: lazy imports to prevent startup crashes if modules are missing
        def _lazy_pulse_and_polish(write_engram=True):
            from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
            return _make_response(True, data=run_pulse_and_polish(write_engram=write_engram))

        def _lazy_self_healing_sre(symptom, write_engram=True):
            from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
            return _make_response(True, data=run_self_healing_sre(symptom=symptom, write_engram=write_engram))

        def _lazy_fusion_reactor(observation, context="Decision", intensity=6, write_engrams=True):
            from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
            return _make_response(True, data=run_fusion_reactor(observation=observation, context=context, intensity=intensity, write_engrams=write_engrams))

        engrams_router = {
            "health": lambda: _brain_health_impl(),
            "version": lambda: _brain_version_impl(),
            "audit_log": lambda limit=20: _brain_audit_log_impl(limit),
            "write_engram": lambda key, value, context="Decision", intensity=5: _brain_write_engram_impl(key, value, context, intensity),
            "query_engrams": lambda context=None, min_intensity=1, limit=50: _brain_query_engrams_impl(context, min_intensity, limit),
            "search_engrams": lambda query, case_sensitive=False, limit=50: _brain_search_engrams_impl(query, case_sensitive, limit),
            "governance_status": lambda: _brain_governance_status_impl(),
            "morning_brief": (lambda: _make_response(True, data=_morning_brief_impl())) if _morning_brief_impl else (lambda: _optional_missing("morning_brief")),
            # Phase 3: God Combos (lazy imports — never block server startup)
            "pulse_and_polish": _lazy_pulse_and_polish,
            "self_healing_sre": _lazy_self_healing_sre,
            "fusion_reactor": _lazy_fusion_reactor,
            # Phase 3: Context Graph
            "context_graph": (lambda include_edges=True, min_intensity=1: _make_response(True, data=build_context_graph(include_edges=include_edges, min_intensity=min_intensity))) if build_context_graph else (lambda **kw: _optional_missing("context_graph")),
            "engram_neighbors": (lambda key, max_depth=1: _make_response(True, data=get_engram_neighbors(key=key, max_depth=max_depth))) if get_engram_neighbors else (lambda **kw: _optional_missing("engram_neighbors")),
            "render_graph": (lambda max_nodes=30, min_intensity=1: _make_response(True, data={"ascii": render_ascii_graph(max_nodes=max_nodes, min_intensity=min_intensity)})) if render_ascii_graph else (lambda **kw: _optional_missing("render_graph")),
            # Phase 3: Billing
            "billing_summary": (lambda since_hours=None, group_by="tool": _make_response(True, data=compute_usage_summary(since_hours=since_hours, group_by=group_by))) if compute_usage_summary else (lambda **kw: _optional_missing("billing_summary")),
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
        print(f"Version: {_nucleus_version}")
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
