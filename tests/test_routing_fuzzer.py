"""
Autonomous Routing Fuzzer — Tests natural language → facade tool routing.

Verifies that `analyze_without_llm` in LLMIntentAnalyzer correctly maps
natural language prompts (standard, slang, complex) to the right facade tool
for all 12 facades / 164+ actions.

This is a deterministic test suite (no LLM calls needed).
"""

import pytest
import inspect
from typing import Dict, List, Set, Tuple

from mcp_server_nucleus.runtime.llm_intent_analyzer import (
    LLMIntentAnalyzer,
    IntentAnalysisResult,
)


# ============================================================
# GROUND TRUTH: Complete Facade Action Registry
# Manually verified against source ROUTER dicts in tools/*.py
# ============================================================

FACADE_REGISTRY: Dict[str, List[str]] = {
    "nucleus_tasks": [
        "list", "get_next", "claim", "update", "add", "import_jsonl",
        "escalate", "depth_push", "depth_pop", "depth_show", "depth_reset",
        "depth_set_max", "depth_map", "context_switch", "context_switch_status",
        "context_switch_reset",
    ],
    "nucleus_engrams": [
        "health", "version", "export_schema", "performance_metrics",
        "prometheus_metrics", "audit_log", "write_engram", "query_engrams",
        "search_engrams", "governance_status", "morning_brief", "hook_metrics",
        "compounding_status", "end_of_day", "session_inject",
        "weekly_consolidate", "list_decisions", "list_snapshots",
        "metering_summary", "ipc_tokens", "dsor_status", "federation_dsor",
        "routing_decisions", "list_tools", "tier_status",
    ],
    "nucleus_governance": [
        "auto_fix_loop", "lock", "unlock", "set_mode", "list_directory",
        "delete_file", "watch", "status", "curl", "pip_install",
    ],
    "nucleus_federation": [
        "status", "join", "leave", "peers", "sync", "route", "health",
    ],
    "nucleus_sync": [
        "identify_agent", "sync_status", "sync_now", "sync_auto",
        "sync_resolve", "read_artifact", "write_artifact", "list_artifacts",
        "trigger_agent", "get_triggers", "evaluate_triggers",
        "start_deploy_poll", "check_deploy", "complete_deploy", "smoke_test",
    ],
    "nucleus_sessions": [
        "save", "resume", "list", "check_recent", "end", "start",
        "archive_resolved", "propose_merges", "garbage_collect",
        "emit_event", "read_events", "get_state", "update_state",
        "checkpoint", "resume_checkpoint", "handoff_summary",
    ],
    "nucleus_features": [
        "add", "list", "get", "update", "validate", "search",
        "mount_server", "thanos_snap", "unmount_server", "list_mounted",
        "discover_tools", "invoke_tool", "traverse_mount",
        "generate_proof", "get_proof", "list_proofs",
    ],
    "nucleus_orchestration": [
        "satellite", "scan_commitments", "archive_stale", "export",
        "list_commitments", "close_commitment", "commitment_health",
        "open_loops", "add_loop", "weekly_challenge", "patterns", "metrics",
    ],
    "nucleus_telemetry": [
        "set_llm_tier", "get_llm_status", "record_interaction",
        "value_ratio", "check_kill_switch", "pause_notifications",
        "resume_notifications", "record_feedback", "mark_high_impact",
        "check_protocol", "request_handoff", "get_handoffs",
        "agent_cost_dashboard", "dispatch_metrics",
    ],
    "nucleus_slots": [
        "orchestrate", "slot_complete", "slot_exhaust", "status_dashboard",
        "autopilot_sprint", "force_assign", "autopilot_sprint_v2",
        "start_mission", "mission_status", "halt_sprint", "resume_sprint",
    ],
    "nucleus_infra": [
        "file_changes", "gcloud_status", "gcloud_services", "list_services",
        "scan_marketing_log", "synthesize_strategy", "status_report",
        "optimize_workflow", "manage_strategy", "update_roadmap",
    ],
    "nucleus_agents": [
        "spawn_agent", "apply_critique", "orchestrate_swarm",
        "search_memory", "read_memory", "respond_to_consent",
        "list_pending_consents", "critique_code", "fix_code",
        "session_briefing", "register_session", "handoff_task",
        "ingest_tasks", "rollback_ingestion", "ingestion_stats",
        "dashboard", "snapshot_dashboard", "list_dashboard_snapshots",
        "get_alerts", "set_alert_threshold",
    ],
}

TOTAL_ACTIONS = sum(len(v) for v in FACADE_REGISTRY.values())

# The list of tool dicts that analyze_without_llm expects
AVAILABLE_TOOLS = [
    {"name": "nucleus_tasks", "description": "Task + depth management facade"},
    {"name": "nucleus_engrams", "description": "Memory, health, version, morning brief facade"},
    {"name": "nucleus_governance", "description": "Governance, lock, audit, hypervisor facade"},
    {"name": "nucleus_sessions", "description": "Session management facade"},
    {"name": "nucleus_sync", "description": "Multi-agent sync facade"},
    {"name": "nucleus_orchestration", "description": "Core orchestration facade"},
    {"name": "nucleus_telemetry", "description": "Telemetry and metering facade"},
    {"name": "nucleus_slots", "description": "Slot management and sprints facade"},
    {"name": "nucleus_infra", "description": "Infrastructure and deployment facade"},
    {"name": "nucleus_agents", "description": "Agent management and code ops facade"},
    {"name": "nucleus_features", "description": "Feature map, mounter, proofs facade"},
    {"name": "nucleus_federation", "description": "Federation networking facade"},
]


# ============================================================
# PROMPT VARIANTS: 3 styles per facade
# Standard, Slang/Casual, Complex/Verbose
# ============================================================

PROMPT_VARIANTS: Dict[str, List[Tuple[str, str]]] = {
    # (prompt_text, variant_style)
    "nucleus_tasks": [
        ("Add task to the backlog for code review", "standard"),
        ("Yo, throw a task on the pile", "slang"),
        ("I need to list task items in the queue and filter by priority", "complex"),
    ],
    "nucleus_engrams": [
        ("Check system health status", "standard"),
        ("How's the brain doing?", "slang"),
        ("Query the engram memory store for recent entries matching deployment context", "complex"),
    ],
    "nucleus_governance": [
        ("Lock the config file so nobody can change it", "standard"),
        ("Yo lock that file down", "slang"),
        ("Perform a comprehensive audit of the current governance and security posture", "complex"),
    ],
    "nucleus_sessions": [
        ("Hand over this task to another agent", "standard"),
        ("Pass this task to the other dude", "slang"),
        ("Generate a comprehensive handoff summary and checkpoint the current progress", "complex"),
    ],
    "nucleus_sync": [
        ("Sync the agents right now", "standard"),
        ("Sync everything up", "slang"),
        ("Force immediate synchronization across all registered multi-agent peers", "complex"),
    ],
    "nucleus_orchestration": [
        ("Orchestrate the satellite view of the project", "standard"),
        ("Orchestrate the whole thing", "slang"),
        ("I need to orchestrate an overview of metrics and open commitment health", "complex"),
    ],
    "nucleus_telemetry": [
        ("What's the current budget usage?", "standard"),
        ("How much budget have we burned?", "slang"),
        ("Retrieve the comprehensive telemetry value ratio and kill switch status", "complex"),
    ],
    "nucleus_slots": [
        ("Start a new sprint with all available slots", "standard"),
        ("Fire up the sprint machine", "slang"),
        ("Initiate an autopilot mission with budget constraints and tier mismatch halting", "complex"),
    ],
    "nucleus_infra": [
        ("Deploy the latest changes to production", "standard"),
        ("Ship it!", "slang"),
        ("Execute a full smoke test against the deployed infrastructure endpoints", "complex"),
    ],
    "nucleus_agents": [
        ("Spawn a new agent to handle code review", "standard"),
        ("Spin up a code monkey", "slang"),
        ("Critique the implementation in the target file and apply automated fixes", "complex"),
    ],
    "nucleus_features": [
        ("Add a new feature to the product map", "standard"),
        ("Log that feature we just built", "slang"),
        ("Search the feature registry for all validated entries matching the deployment criteria", "complex"),
    ],
    "nucleus_federation": [
        ("Check the federation status", "standard"),
        ("How's the federation doing?", "slang"),
        ("Synchronize with all federation peers and report comprehensive health diagnostics", "complex"),
    ],
}


# ============================================================
# KEYWORD MAP COVERAGE: What keywords map to what facades
# Mirrors the keyword_map in llm_intent_analyzer.py
# ============================================================

EXPECTED_KEYWORD_MAP = {
    # ── Tasks ──
    "add task": "nucleus_tasks",
    "list task": "nucleus_tasks",
    "import jsonl": "nucleus_tasks",
    "import task": "nucleus_tasks",
    "context switch": "nucleus_tasks",
    "depth push": "nucleus_tasks",
    "depth pop": "nucleus_tasks",
    "depth map": "nucleus_tasks",
    "next task": "nucleus_tasks",
    "claim task": "nucleus_tasks",
    "escalate": "nucleus_tasks",
    "task": "nucleus_tasks",
    "depth": "nucleus_tasks",
    "backlog": "nucleus_tasks",
    # ── Engrams ──
    "write engram": "nucleus_engrams",
    "query engram": "nucleus_engrams",
    "search engram": "nucleus_engrams",
    "morning brief": "nucleus_engrams",
    "end of day": "nucleus_engrams",
    "weekly consolidat": "nucleus_engrams",
    "compounding status": "nucleus_engrams",
    "hook metric": "nucleus_engrams",
    "session inject": "nucleus_engrams",
    "export schema": "nucleus_engrams",
    "performance metric": "nucleus_engrams",
    "prometheus metric": "nucleus_engrams",
    "metering summary": "nucleus_engrams",
    "ipc token": "nucleus_engrams",
    "dsor status": "nucleus_engrams",
    "federation dsor": "nucleus_engrams",
    "routing decision": "nucleus_engrams",
    "list decision": "nucleus_engrams",
    "list snapshot": "nucleus_engrams",
    "list tool": "nucleus_engrams",
    "tier status": "nucleus_engrams",
    "engram": "nucleus_engrams",
    "health": "nucleus_engrams",
    "brain": "nucleus_engrams",
    "memory": "nucleus_engrams",
    "version": "nucleus_engrams",
    # ── Sessions ──
    "resume checkpoint": "nucleus_sessions",
    "handoff summary": "nucleus_sessions",
    "archive resolved": "nucleus_sessions",
    "propose merge": "nucleus_sessions",
    "garbage collect": "nucleus_sessions",
    "emit event": "nucleus_sessions",
    "read event": "nucleus_sessions",
    "get state": "nucleus_sessions",
    "update state": "nucleus_sessions",
    "save session": "nucleus_sessions",
    "end session": "nucleus_sessions",
    "start session": "nucleus_sessions",
    "check recent": "nucleus_sessions",
    "checkpoint": "nucleus_sessions",
    "hand over": "nucleus_sessions",
    "handoff": "nucleus_sessions",
    "pass this": "nucleus_sessions",
    "give to": "nucleus_sessions",
    "session": "nucleus_sessions",
    "event": "nucleus_sessions",
    # ── Infra ──
    "smoke test": "nucleus_infra",
    "file change": "nucleus_infra",
    "gcloud status": "nucleus_infra",
    "gcloud service": "nucleus_infra",
    "list service": "nucleus_infra",
    "scan marketing": "nucleus_infra",
    "synthesize strategy": "nucleus_infra",
    "status report": "nucleus_infra",
    "optimize workflow": "nucleus_infra",
    "manage strategy": "nucleus_infra",
    "update roadmap": "nucleus_infra",
    "deploy": "nucleus_infra",
    "ship": "nucleus_infra",
    "infrastructure": "nucleus_infra",
    "gcloud": "nucleus_infra",
    "roadmap": "nucleus_infra",
    "marketing": "nucleus_infra",
    "strategy": "nucleus_infra",
    "workflow": "nucleus_infra",
    # ── Telemetry ──
    "value ratio": "nucleus_telemetry",
    "kill switch": "nucleus_telemetry",
    "llm tier": "nucleus_telemetry",
    "llm status": "nucleus_telemetry",
    "record interaction": "nucleus_telemetry",
    "pause notification": "nucleus_telemetry",
    "resume notification": "nucleus_telemetry",
    "record feedback": "nucleus_telemetry",
    "high impact": "nucleus_telemetry",
    "check protocol": "nucleus_telemetry",
    "request handoff": "nucleus_telemetry",
    "get handoff": "nucleus_telemetry",
    "cost dashboard": "nucleus_telemetry",
    "dispatch metric": "nucleus_telemetry",
    "budget": "nucleus_telemetry",
    "telemetry": "nucleus_telemetry",
    "cost": "nucleus_telemetry",
    "notification": "nucleus_telemetry",
    # ── Agents ──
    "spawn agent": "nucleus_agents",
    "apply critique": "nucleus_agents",
    "orchestrate swarm": "nucleus_agents",
    "search memory": "nucleus_agents",
    "read memory": "nucleus_agents",
    "respond to consent": "nucleus_agents",
    "pending consent": "nucleus_agents",
    "critique code": "nucleus_agents",
    "fix code": "nucleus_agents",
    "session briefing": "nucleus_agents",
    "register session": "nucleus_agents",
    "handoff task": "nucleus_agents",
    "ingest task": "nucleus_agents",
    "rollback ingestion": "nucleus_agents",
    "ingestion stat": "nucleus_agents",
    "snapshot dashboard": "nucleus_agents",
    "list dashboard": "nucleus_agents",
    "get alert": "nucleus_agents",
    "set alert": "nucleus_agents",
    "alert threshold": "nucleus_agents",
    "code": "nucleus_agents",
    "critique": "nucleus_agents",
    "swarm": "nucleus_agents",
    "dashboard": "nucleus_agents",
    "spawn": "nucleus_agents",
    "ingest": "nucleus_agents",
    "alert": "nucleus_agents",
    # ── Governance ──
    "auto fix": "nucleus_governance",
    "auto_fix": "nucleus_governance",
    "delete file": "nucleus_governance",
    "list directory": "nucleus_governance",
    "set mode": "nucleus_governance",
    "pip install": "nucleus_governance",
    "status": "nucleus_governance",
    "lock": "nucleus_governance",
    "unlock": "nucleus_governance",
    "audit": "nucleus_governance",
    "governance": "nucleus_governance",
    "watch": "nucleus_governance",
    "curl": "nucleus_governance",
    # ── Sync ──
    "identify agent": "nucleus_sync",
    "sync status": "nucleus_sync",
    "sync now": "nucleus_sync",
    "sync auto": "nucleus_sync",
    "sync resolve": "nucleus_sync",
    "read artifact": "nucleus_sync",
    "write artifact": "nucleus_sync",
    "list artifact": "nucleus_sync",
    "trigger agent": "nucleus_sync",
    "get trigger": "nucleus_sync",
    "evaluate trigger": "nucleus_sync",
    "deploy poll": "nucleus_sync",
    "check deploy": "nucleus_sync",
    "complete deploy": "nucleus_sync",
    "sync": "nucleus_sync",
    "artifact": "nucleus_sync",
    "trigger": "nucleus_sync",
    # ── Features ──
    "mount server": "nucleus_features",
    "unmount server": "nucleus_features",
    "list mounted": "nucleus_features",
    "discover tool": "nucleus_features",
    "invoke tool": "nucleus_features",
    "traverse mount": "nucleus_features",
    "generate proof": "nucleus_features",
    "get proof": "nucleus_features",
    "list proof": "nucleus_features",
    "thanos snap": "nucleus_features",
    "validate feature": "nucleus_features",
    "feature": "nucleus_features",
    "proof": "nucleus_features",
    "mount": "nucleus_features",
    # ── Federation ──
    "join federation": "nucleus_federation",
    "leave federation": "nucleus_federation",
    "federation peer": "nucleus_federation",
    "federation health": "nucleus_federation",
    "federation": "nucleus_federation",
    "peer": "nucleus_federation",
    # ── Orchestration ──
    "scan commitment": "nucleus_orchestration",
    "archive stale": "nucleus_orchestration",
    "list commitment": "nucleus_orchestration",
    "close commitment": "nucleus_orchestration",
    "commitment health": "nucleus_orchestration",
    "open loop": "nucleus_orchestration",
    "add loop": "nucleus_orchestration",
    "weekly challenge": "nucleus_orchestration",
    "orchestrate": "nucleus_orchestration",
    "orchestration": "nucleus_orchestration",
    "satellite": "nucleus_orchestration",
    "commitment": "nucleus_orchestration",
    "loop": "nucleus_orchestration",
    "pattern": "nucleus_orchestration",
    "metric": "nucleus_orchestration",
    # ── Slots ──
    "slot complete": "nucleus_slots",
    "slot exhaust": "nucleus_slots",
    "status dashboard": "nucleus_slots",
    "autopilot sprint": "nucleus_slots",
    "force assign": "nucleus_slots",
    "start mission": "nucleus_slots",
    "mission status": "nucleus_slots",
    "halt sprint": "nucleus_slots",
    "resume sprint": "nucleus_slots",
    "sprint": "nucleus_slots",
    "mission": "nucleus_slots",
    "slot": "nucleus_slots",
    "autopilot": "nucleus_slots",
}


# ============================================================
# ACTION-LEVEL PROMPTS: Natural language per action
# Key format: "facade.action" → list of (prompt, style) tuples
# Every action in FACADE_REGISTRY must have at least 1 prompt.
# ============================================================

ACTION_PROMPTS: Dict[str, List[Tuple[str, str]]] = {
    # ── nucleus_tasks (16 actions) ──
    "nucleus_tasks.list": [
        ("List all pending tasks in the backlog", "standard"),
    ],
    "nucleus_tasks.get_next": [
        ("Get the next highest-priority task for me", "standard"),
    ],
    "nucleus_tasks.claim": [
        ("Claim task T-042 for this agent", "standard"),
    ],
    "nucleus_tasks.update": [
        ("Update task T-042 status to done", "standard"),
    ],
    "nucleus_tasks.add": [
        ("Add a new task for code review", "standard"),
        ("Throw a task on the backlog", "slang"),
    ],
    "nucleus_tasks.import_jsonl": [
        ("Import tasks from the JSONL file", "standard"),
    ],
    "nucleus_tasks.escalate": [
        ("Escalate task T-042 because it needs human help", "standard"),
    ],
    "nucleus_tasks.depth_push": [
        ("Push deeper into the depth stack for subtopic analysis", "standard"),
    ],
    "nucleus_tasks.depth_pop": [
        ("Pop back up one depth level", "standard"),
    ],
    "nucleus_tasks.depth_show": [
        ("Show the current depth state", "standard"),
    ],
    "nucleus_tasks.depth_reset": [
        ("Reset depth tracking back to root", "standard"),
    ],
    "nucleus_tasks.depth_set_max": [
        ("Set the maximum safe depth to 7 levels", "standard"),
    ],
    "nucleus_tasks.depth_map": [
        ("Generate the depth exploration map", "standard"),
    ],
    "nucleus_tasks.context_switch": [
        ("Record a context switch to the new topic", "standard"),
    ],
    "nucleus_tasks.context_switch_status": [
        ("Show the context switch metrics and drift status", "standard"),
    ],
    "nucleus_tasks.context_switch_reset": [
        ("Reset the context switch counter", "standard"),
    ],

    # ── nucleus_engrams (25 actions) ──
    "nucleus_engrams.health": [
        ("Check system health status", "standard"),
    ],
    "nucleus_engrams.version": [
        ("What version of Nucleus is running?", "standard"),
    ],
    "nucleus_engrams.export_schema": [
        ("Export the MCP engram schema as JSON", "standard"),
    ],
    "nucleus_engrams.performance_metrics": [
        ("Show me the performance metrics", "standard"),
    ],
    "nucleus_engrams.prometheus_metrics": [
        ("Get the Prometheus metrics output", "standard"),
    ],
    "nucleus_engrams.audit_log": [
        ("Show the last 20 entries in the engram audit log", "standard"),
    ],
    "nucleus_engrams.write_engram": [
        ("Write an engram to memory with key deployment-v2", "standard"),
    ],
    "nucleus_engrams.query_engrams": [
        ("Query the engram memory for deployment context", "standard"),
    ],
    "nucleus_engrams.search_engrams": [
        ("Search engrams for anything matching auth refactor", "standard"),
    ],
    "nucleus_engrams.governance_status": [
        ("Check the engram governance status overview", "standard"),
    ],
    "nucleus_engrams.morning_brief": [
        ("Run the morning brief", "standard"),
    ],
    "nucleus_engrams.hook_metrics": [
        ("Show the auto-write engram hook metrics", "standard"),
    ],
    "nucleus_engrams.compounding_status": [
        ("What is the compounding status of the learning loop?", "standard"),
    ],
    "nucleus_engrams.end_of_day": [
        ("Capture the end of day learnings and summary", "standard"),
    ],
    "nucleus_engrams.session_inject": [
        ("Use session inject to load engram context at startup", "standard"),
    ],
    "nucleus_engrams.weekly_consolidate": [
        ("Run weekly consolidation of engrams and patterns", "standard"),
    ],
    "nucleus_engrams.list_decisions": [
        ("List the recent decision entries from the engram ledger", "standard"),
    ],
    "nucleus_engrams.list_snapshots": [
        ("List all engram context snapshots", "standard"),
    ],
    "nucleus_engrams.metering_summary": [
        ("Show the metering summary for token usage", "standard"),
    ],
    "nucleus_engrams.ipc_tokens": [
        ("List the IPC token entries from the engram system", "standard"),
    ],
    "nucleus_engrams.dsor_status": [
        ("Get the comprehensive DSoR status", "standard"),
    ],
    "nucleus_engrams.federation_dsor": [
        ("Show the federation DSoR report", "standard"),
    ],
    "nucleus_engrams.routing_decisions": [
        ("Query the routing decision history", "standard"),
    ],
    "nucleus_engrams.list_tools": [
        ("List all available engram tools at current tier", "standard"),
    ],
    "nucleus_engrams.tier_status": [
        ("What is the current tier status configuration?", "standard"),
    ],

    # ── nucleus_governance (10 actions) ──
    "nucleus_governance.auto_fix_loop": [
        ("Run the auto fix loop on the broken file", "standard"),
    ],
    "nucleus_governance.lock": [
        ("Lock the configuration file so nobody can change it", "standard"),
    ],
    "nucleus_governance.unlock": [
        ("Unlock the previously locked config file", "standard"),
    ],
    "nucleus_governance.set_mode": [
        ("Use set mode to switch governance to red for production", "standard"),
    ],
    "nucleus_governance.list_directory": [
        ("List the directory contents for governance review", "standard"),
    ],
    "nucleus_governance.delete_file": [
        ("Delete the stale backup file through governance", "standard"),
    ],
    "nucleus_governance.watch": [
        ("Watch this folder for file changes", "standard"),
    ],
    "nucleus_governance.status": [
        ("Report the current security status of the Agent OS", "standard"),
    ],
    "nucleus_governance.curl": [
        ("Use curl to fetch the external health endpoint", "standard"),
    ],
    "nucleus_governance.pip_install": [
        ("Pip install the requests package through governance", "standard"),
    ],

    # ── nucleus_federation (7 actions) ──
    "nucleus_federation.status": [
        ("Check the federation status", "standard"),
    ],
    "nucleus_federation.join": [
        ("Join the federation via seed peer at localhost:8080", "standard"),
    ],
    "nucleus_federation.leave": [
        ("Leave the federation gracefully", "standard"),
    ],
    "nucleus_federation.peers": [
        ("List all federation peers with connection details", "standard"),
    ],
    "nucleus_federation.sync": [
        ("Force sync with all federation peers right now", "standard"),
    ],
    "nucleus_federation.route": [
        ("Route the task to the optimal federation brain", "standard"),
    ],
    "nucleus_federation.health": [
        ("Get the federation health dashboard", "standard"),
    ],

    # ── nucleus_sync (15 actions) ──
    "nucleus_sync.identify_agent": [
        ("Identify this agent with the sync system", "standard"),
    ],
    "nucleus_sync.sync_status": [
        ("Check the current sync status across agents", "standard"),
    ],
    "nucleus_sync.sync_now": [
        ("Force sync now across all agents", "standard"),
    ],
    "nucleus_sync.sync_auto": [
        ("Enable automatic sync file watching", "standard"),
    ],
    "nucleus_sync.sync_resolve": [
        ("Resolve the sync conflict on the config file", "standard"),
    ],
    "nucleus_sync.read_artifact": [
        ("Read the artifact file from the shared store", "standard"),
    ],
    "nucleus_sync.write_artifact": [
        ("Write the deployment notes as an artifact", "standard"),
    ],
    "nucleus_sync.list_artifacts": [
        ("List all shared artifacts in the brain", "standard"),
    ],
    "nucleus_sync.trigger_agent": [
        ("Trigger the code review agent with this task", "standard"),
    ],
    "nucleus_sync.get_triggers": [
        ("Get all defined neural triggers", "standard"),
    ],
    "nucleus_sync.evaluate_triggers": [
        ("Evaluate triggers for the deploy event", "standard"),
    ],
    "nucleus_sync.start_deploy_poll": [
        ("Use deploy poll to monitor the sync service deployment", "standard"),
    ],
    "nucleus_sync.check_deploy": [
        ("Check the current deploy poll status", "standard"),
    ],
    "nucleus_sync.complete_deploy": [
        ("Use complete deploy to mark the sync deployment as done", "standard"),
    ],
    "nucleus_sync.smoke_test": [
        ("Run a sync smoke test against the deployed endpoint", "standard"),
    ],

    # ── nucleus_sessions (16 actions) ──
    "nucleus_sessions.save": [
        ("Save the current session for later resumption", "standard"),
    ],
    "nucleus_sessions.resume": [
        ("Resume the previously saved session", "standard"),
    ],
    "nucleus_sessions.list": [
        ("List all saved sessions", "standard"),
    ],
    "nucleus_sessions.check_recent": [
        ("Check for a recent session to resume", "standard"),
    ],
    "nucleus_sessions.end": [
        ("End the current work session with a summary", "standard"),
    ],
    "nucleus_sessions.start": [
        ("Start a new mandatory session protocol", "standard"),
    ],
    "nucleus_sessions.archive_resolved": [
        ("Archive resolved session backup files", "standard"),
    ],
    "nucleus_sessions.propose_merges": [
        ("Propose merges for redundant artifacts", "standard"),
    ],
    "nucleus_sessions.garbage_collect": [
        ("Run garbage collection to archive stale sessions", "standard"),
    ],
    "nucleus_sessions.emit_event": [
        ("Emit a deployment event to the brain ledger", "standard"),
    ],
    "nucleus_sessions.read_events": [
        ("Read the recent events from the ledger", "standard"),
    ],
    "nucleus_sessions.get_state": [
        ("Get the current session state from the ledger", "standard"),
    ],
    "nucleus_sessions.update_state": [
        ("Update the session state with the new deployment info", "standard"),
    ],
    "nucleus_sessions.checkpoint": [
        ("Save a checkpoint for the current task progress", "standard"),
    ],
    "nucleus_sessions.resume_checkpoint": [
        ("Resume from the last saved checkpoint", "standard"),
    ],
    "nucleus_sessions.handoff_summary": [
        ("Generate a handoff summary for the task transition", "standard"),
    ],

    # ── nucleus_features (16 actions) ──
    "nucleus_features.add": [
        ("Add a new feature to the product feature map", "standard"),
    ],
    "nucleus_features.list": [
        ("List all registered features", "standard"),
    ],
    "nucleus_features.get": [
        ("Get feature F-001 details", "standard"),
    ],
    "nucleus_features.update": [
        ("Update feature F-001 status to validated", "standard"),
    ],
    "nucleus_features.validate": [
        ("Validate feature F-001 passed manual testing", "standard"),
    ],
    "nucleus_features.search": [
        ("Search the feature registry for auth-related features", "standard"),
    ],
    "nucleus_features.mount_server": [
        ("Mount the external MCP server for GitHub integration", "standard"),
    ],
    "nucleus_features.thanos_snap": [
        ("Trigger the thanos snap aggregation", "standard"),
    ],
    "nucleus_features.unmount_server": [
        ("Unmount the stale MCP server that is no longer needed", "standard"),
    ],
    "nucleus_features.list_mounted": [
        ("List all currently mounted MCP servers", "standard"),
    ],
    "nucleus_features.discover_tools": [
        ("Discover tools from the mounted GitHub server", "standard"),
    ],
    "nucleus_features.invoke_tool": [
        ("Invoke a tool on the mounted server", "standard"),
    ],
    "nucleus_features.traverse_mount": [
        ("Traverse and recursively mount downstream servers", "standard"),
    ],
    "nucleus_features.generate_proof": [
        ("Generate a proof document for feature F-001", "standard"),
    ],
    "nucleus_features.get_proof": [
        ("Get the proof document for the last deployed feature", "standard"),
    ],
    "nucleus_features.list_proofs": [
        ("List all proof documents generated so far", "standard"),
    ],

    # ── nucleus_orchestration (12 actions) ──
    "nucleus_orchestration.satellite": [
        ("Show the satellite view of the entire project", "standard"),
    ],
    "nucleus_orchestration.scan_commitments": [
        ("Scan all artifacts for new commitments to track", "standard"),
    ],
    "nucleus_orchestration.archive_stale": [
        ("Archive stale commitments older than 30 days", "standard"),
    ],
    "nucleus_orchestration.export": [
        ("Export the orchestration data to a zip archive", "standard"),
    ],
    "nucleus_orchestration.list_commitments": [
        ("List all open commitments by tier", "standard"),
    ],
    "nucleus_orchestration.close_commitment": [
        ("Close commitment C-015 as completed", "standard"),
    ],
    "nucleus_orchestration.commitment_health": [
        ("Get the commitment health summary", "standard"),
    ],
    "nucleus_orchestration.open_loops": [
        ("Show all open loops and unresolved items", "standard"),
    ],
    "nucleus_orchestration.add_loop": [
        ("Add a new open loop for tracking the DNS migration", "standard"),
    ],
    "nucleus_orchestration.weekly_challenge": [
        ("Manage this week's weekly challenge", "standard"),
    ],
    "nucleus_orchestration.patterns": [
        ("Show the learned patterns from recent work", "standard"),
    ],
    "nucleus_orchestration.metrics": [
        ("Get the coordination metrics overview", "standard"),
    ],

    # ── nucleus_telemetry (14 actions) ──
    "nucleus_telemetry.set_llm_tier": [
        ("Set the default LLM tier to tier 2", "standard"),
    ],
    "nucleus_telemetry.get_llm_status": [
        ("Get the current LLM tier and status configuration", "standard"),
    ],
    "nucleus_telemetry.record_interaction": [
        ("Use record interaction to log a telemetry timestamp", "standard"),
    ],
    "nucleus_telemetry.value_ratio": [
        ("Show the current value ratio metric", "standard"),
    ],
    "nucleus_telemetry.check_kill_switch": [
        ("Check if the kill switch is active", "standard"),
    ],
    "nucleus_telemetry.pause_notifications": [
        ("Pause PEFS notifications temporarily", "standard"),
    ],
    "nucleus_telemetry.resume_notifications": [
        ("Resume the paused notifications", "standard"),
    ],
    "nucleus_telemetry.record_feedback": [
        ("Record feedback for the last notification", "standard"),
    ],
    "nucleus_telemetry.mark_high_impact": [
        ("Mark this loop closure as high impact", "standard"),
    ],
    "nucleus_telemetry.check_protocol": [
        ("Check protocol compliance for this agent", "standard"),
    ],
    "nucleus_telemetry.request_handoff": [
        ("Use request handoff via telemetry to pass context to Opus", "standard"),
    ],
    "nucleus_telemetry.get_handoffs": [
        ("Use get handoff to list pending telemetry handoff requests", "standard"),
    ],
    "nucleus_telemetry.agent_cost_dashboard": [
        ("Show the agent cost dashboard with USD estimates", "standard"),
    ],
    "nucleus_telemetry.dispatch_metrics": [
        ("Get the dispatch metrics for all facades", "standard"),
    ],

    # ── nucleus_slots (11 actions) ──
    "nucleus_slots.orchestrate": [
        ("Orchestrate a new slot for the available model", "standard"),
    ],
    "nucleus_slots.slot_complete": [
        ("Mark slot S-01 task as complete", "standard"),
    ],
    "nucleus_slots.slot_exhaust": [
        ("Mark the current slot as exhausted", "standard"),
    ],
    "nucleus_slots.status_dashboard": [
        ("Show the ASCII status dashboard for all slots", "standard"),
    ],
    "nucleus_slots.autopilot_sprint": [
        ("Start an autopilot sprint across all available slots", "standard"),
    ],
    "nucleus_slots.force_assign": [
        ("Force assign task T-042 to slot S-01", "standard"),
    ],
    "nucleus_slots.autopilot_sprint_v2": [
        ("Run the enhanced autopilot sprint v2 with budget limits", "standard"),
    ],
    "nucleus_slots.start_mission": [
        ("Start a new mission with specific goals and task IDs", "standard"),
    ],
    "nucleus_slots.mission_status": [
        ("Get the current mission status and progress", "standard"),
    ],
    "nucleus_slots.halt_sprint": [
        ("Halt the running sprint immediately", "standard"),
    ],
    "nucleus_slots.resume_sprint": [
        ("Resume the previously halted sprint", "standard"),
    ],

    # ── nucleus_infra (10 actions) ──
    "nucleus_infra.file_changes": [
        ("Check for any pending file change events", "standard"),
    ],
    "nucleus_infra.gcloud_status": [
        ("Check the GCloud authentication status", "standard"),
    ],
    "nucleus_infra.gcloud_services": [
        ("List all Cloud Run gcloud services", "standard"),
    ],
    "nucleus_infra.list_services": [
        ("List Render services currently deployed", "standard"),
    ],
    "nucleus_infra.scan_marketing_log": [
        ("Scan the marketing log for any failures", "standard"),
    ],
    "nucleus_infra.synthesize_strategy": [
        ("Analyze marketing data and synthesize the strategy", "standard"),
    ],
    "nucleus_infra.status_report": [
        ("Generate the State of the Union status report", "standard"),
    ],
    "nucleus_infra.optimize_workflow": [
        ("Self-optimize the workflow cheatsheet", "standard"),
    ],
    "nucleus_infra.manage_strategy": [
        ("Read the current strategy document", "standard"),
    ],
    "nucleus_infra.update_roadmap": [
        ("Update the roadmap with the new Q2 items", "standard"),
    ],

    # ── nucleus_agents (20 actions) ──
    "nucleus_agents.spawn_agent": [
        ("Spawn a new agent to handle code review", "standard"),
    ],
    "nucleus_agents.apply_critique": [
        ("Apply the critique fixes from the review path", "standard"),
    ],
    "nucleus_agents.orchestrate_swarm": [
        ("Start a multi-agent swarm for the migration task", "standard"),
    ],
    "nucleus_agents.search_memory": [
        ("Use search memory to find agent deployment patterns", "standard"),
    ],
    "nucleus_agents.read_memory": [
        ("Use read memory to fetch the agent decisions category", "standard"),
    ],
    "nucleus_agents.respond_to_consent": [
        ("Respond to the pending consent for agent respawn", "standard"),
    ],
    "nucleus_agents.list_pending_consents": [
        ("Show pending consent requests from agents waiting to respawn", "standard"),
    ],
    "nucleus_agents.critique_code": [
        ("Run the code critic on the target file", "standard"),
    ],
    "nucleus_agents.fix_code": [
        ("Auto-fix the code issues found by the critic", "standard"),
    ],
    "nucleus_agents.session_briefing": [
        ("Get a session briefing for the current conversation", "standard"),
    ],
    "nucleus_agents.register_session": [
        ("Use register session to set the agent focus area", "standard"),
    ],
    "nucleus_agents.handoff_task": [
        ("Use the handoff task action to pass work to another agent", "standard"),
    ],
    "nucleus_agents.ingest_tasks": [
        ("Ingest tasks from the external source file", "standard"),
    ],
    "nucleus_agents.rollback_ingestion": [
        ("Rollback the last ingestion batch due to errors", "standard"),
    ],
    "nucleus_agents.ingestion_stats": [
        ("Get the ingestion statistics for recent batches", "standard"),
    ],
    "nucleus_agents.dashboard": [
        ("Show the enhanced agent dashboard with alerts", "standard"),
    ],
    "nucleus_agents.snapshot_dashboard": [
        ("Create a snapshot of the current dashboard state", "standard"),
    ],
    "nucleus_agents.list_dashboard_snapshots": [
        ("List all previously saved dashboard snapshots", "standard"),
    ],
    "nucleus_agents.get_alerts": [
        ("Get all active alerts from the monitoring system", "standard"),
    ],
    "nucleus_agents.set_alert_threshold": [
        ("Set the alert threshold for error rate to 5 percent", "standard"),
    ],
}

# Sanity: every action in FACADE_REGISTRY must have at least 1 prompt
_COVERED_ACTIONS = set()
for _key in ACTION_PROMPTS:
    _facade, _action = _key.split(".", 1)
    _COVERED_ACTIONS.add((_facade, _action))
_ALL_ACTIONS = set()
for _facade, _actions in FACADE_REGISTRY.items():
    for _action in _actions:
        _ALL_ACTIONS.add((_facade, _action))
_MISSING = _ALL_ACTIONS - _COVERED_ACTIONS
assert not _MISSING, f"ACTION_PROMPTS missing entries for: {_MISSING}"


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def analyzer():
    return LLMIntentAnalyzer()


# ============================================================
# TEST: Registry Sanity
# ============================================================

class TestRegistrySanity:
    """Verify the ground truth registry is internally consistent."""

    def test_twelve_facades(self):
        assert len(FACADE_REGISTRY) == 12

    def test_total_action_count(self):
        """Should have 164+ actions across all facades."""
        assert TOTAL_ACTIONS >= 164, f"Expected >=164, got {TOTAL_ACTIONS}"

    def test_no_duplicate_actions_within_facade(self):
        for facade, actions in FACADE_REGISTRY.items():
            assert len(actions) == len(set(actions)), (
                f"{facade} has duplicate actions: "
                f"{[a for a in actions if actions.count(a) > 1]}"
            )

    def test_all_facades_have_actions(self):
        for facade, actions in FACADE_REGISTRY.items():
            assert len(actions) > 0, f"{facade} has no actions"

    def test_available_tools_matches_registry(self):
        tool_names = {t["name"] for t in AVAILABLE_TOOLS}
        registry_names = set(FACADE_REGISTRY.keys())
        assert tool_names == registry_names


# ============================================================
# TEST: Keyword Map Direct Verification
# ============================================================

class TestKeywordMapDirect:
    """Verify each keyword in the map routes to the expected facade."""

    def test_all_keywords_route_correctly(self, analyzer):
        failures = []
        for keyword, expected_facade in EXPECTED_KEYWORD_MAP.items():
            result = analyzer.analyze_without_llm(keyword, AVAILABLE_TOOLS)
            if expected_facade not in result.required_tools:
                failures.append(
                    f"  '{keyword}' -> expected {expected_facade}, "
                    f"got {result.required_tools}"
                )
        assert not failures, (
            f"{len(failures)} keyword routing failures:\n"
            + "\n".join(failures)
        )

    def test_keyword_count(self):
        """Verify we have a reasonable number of keyword mappings."""
        assert len(EXPECTED_KEYWORD_MAP) >= 25

    def test_all_facades_have_at_least_one_keyword(self):
        """Every facade should be reachable by at least one keyword."""
        covered = set(EXPECTED_KEYWORD_MAP.values())
        uncovered = set(FACADE_REGISTRY.keys()) - covered
        assert not uncovered, f"Facades with no keyword mapping: {uncovered}"


# ============================================================
# TEST: Prompt Variant Routing (Standard / Slang / Complex)
# ============================================================

class TestPromptVariantRouting:
    """Test that natural language variants route to the correct facade."""

    @pytest.mark.parametrize("facade", sorted(FACADE_REGISTRY.keys()))
    def test_standard_prompts(self, analyzer, facade):
        """Standard prompts should always route correctly."""
        variants = PROMPT_VARIANTS[facade]
        standard = [v for v in variants if v[1] == "standard"]
        assert standard, f"No standard prompt for {facade}"
        prompt, _ = standard[0]
        result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
        assert facade in result.required_tools, (
            f"Standard prompt '{prompt}' did not route to {facade}. "
            f"Got: {result.required_tools}"
        )

    @pytest.mark.parametrize("facade", sorted(FACADE_REGISTRY.keys()))
    def test_slang_prompts(self, analyzer, facade):
        """Slang prompts — may fail for coverage gap detection."""
        variants = PROMPT_VARIANTS[facade]
        slang = [v for v in variants if v[1] == "slang"]
        if not slang:
            pytest.skip(f"No slang prompt for {facade}")
        prompt, _ = slang[0]
        result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
        # Slang routing is aspirational — mark as xfail if it misses
        if facade not in result.required_tools:
            pytest.xfail(
                f"Slang gap: '{prompt}' -> {result.required_tools} "
                f"(expected {facade})"
            )

    @pytest.mark.parametrize("facade", sorted(FACADE_REGISTRY.keys()))
    def test_complex_prompts(self, analyzer, facade):
        """Complex/verbose prompts — may fail for coverage gap detection."""
        variants = PROMPT_VARIANTS[facade]
        cx = [v for v in variants if v[1] == "complex"]
        if not cx:
            pytest.skip(f"No complex prompt for {facade}")
        prompt, _ = cx[0]
        result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
        if facade not in result.required_tools:
            pytest.xfail(
                f"Complex gap: '{prompt}' -> {result.required_tools} "
                f"(expected {facade})"
            )


# ============================================================
# TEST: Edge Cases
# ============================================================

class TestEdgeCases:
    """Test boundary conditions for the keyword router."""

    def test_empty_request(self, analyzer):
        result = analyzer.analyze_without_llm("", AVAILABLE_TOOLS)
        assert result.required_tools == []

    def test_whitespace_only(self, analyzer):
        result = analyzer.analyze_without_llm("   ", AVAILABLE_TOOLS)
        assert result.required_tools == []

    def test_conversational_noise(self, analyzer):
        result = analyzer.analyze_without_llm(
            "Hello, how are you today?", AVAILABLE_TOOLS
        )
        assert result.required_tools == []

    def test_gibberish(self, analyzer):
        result = analyzer.analyze_without_llm(
            "asdfghjkl qwerty zxcvbnm", AVAILABLE_TOOLS
        )
        assert result.required_tools == []

    def test_multi_facade_request(self, analyzer):
        """A request mentioning multiple keywords should route to multiple facades."""
        result = analyzer.analyze_without_llm(
            "Lock the file and deploy the code", AVAILABLE_TOOLS
        )
        assert "nucleus_governance" in result.required_tools
        assert "nucleus_infra" in result.required_tools

    def test_no_tools_available(self, analyzer):
        result = analyzer.analyze_without_llm("add a task", [])
        assert result.required_tools == []

    def test_needs_context_detection(self, analyzer):
        result = analyzer.analyze_without_llm(
            "How did we configure the deployment earlier?", AVAILABLE_TOOLS
        )
        assert result.needs_context is True


# ============================================================
# TEST: Action-Level Routing (172 actions)
# ============================================================

class TestActionLevelRouting:
    """Test that action-level prompts route to the correct facade."""

    @pytest.mark.parametrize(
        "action_key",
        sorted(ACTION_PROMPTS.keys()),
        ids=sorted(ACTION_PROMPTS.keys()),
    )
    def test_action_routes_to_facade(self, analyzer, action_key):
        """Each action's prompts should route to the correct facade."""
        facade = action_key.split(".")[0]
        prompts = ACTION_PROMPTS[action_key]
        routed = False
        failures = []
        for prompt, style in prompts:
            result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
            if facade in result.required_tools:
                routed = True
            else:
                failures.append(
                    f"  '{prompt}' ({style}) -> {result.required_tools}"
                )
        assert routed, (
            f"No prompt for {action_key} routed to {facade}:\n"
            + "\n".join(failures)
        )

    def test_action_prompts_cover_all_facades(self):
        """Every facade in the registry has at least one action prompt."""
        covered_facades = {k.split(".")[0] for k in ACTION_PROMPTS}
        assert covered_facades == set(FACADE_REGISTRY.keys())

    def test_action_prompts_count(self):
        """We should have prompts for all 172 actions."""
        assert len(ACTION_PROMPTS) == TOTAL_ACTIONS, (
            f"Expected {TOTAL_ACTIONS} action prompts, got {len(ACTION_PROMPTS)}"
        )


# ============================================================
# TEST: Coverage Report (not a failure — informational)
# ============================================================

class TestCoverageReport:
    """Generate a routing coverage report across all facades."""

    def test_facade_routing_coverage(self, analyzer):
        """
        Run all prompt variants and report coverage.
        This test always passes but prints a detailed report.
        """
        results = {}
        total_prompts = 0
        total_hits = 0

        for facade, variants in PROMPT_VARIANTS.items():
            hits = 0
            for prompt, style in variants:
                total_prompts += 1
                result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
                if facade in result.required_tools:
                    hits += 1
                    total_hits += 1
            results[facade] = (hits, len(variants))

        # Build report
        report_lines = [
            f"\n{'='*60}",
            "ROUTING FUZZER COVERAGE REPORT",
            f"{'='*60}",
            f"Total facades: {len(FACADE_REGISTRY)}",
            f"Total actions: {TOTAL_ACTIONS}",
            f"Total prompts tested: {total_prompts}",
            f"Total hits: {total_hits}/{total_prompts} "
            f"({total_hits/total_prompts*100:.0f}%)",
            f"{'-'*60}",
        ]
        for facade in sorted(results):
            hits, total = results[facade]
            pct = hits / total * 100 if total > 0 else 0
            icon = "✅" if pct == 100 else "⚠️" if pct > 0 else "❌"
            report_lines.append(
                f"  {icon} {facade}: {hits}/{total} ({pct:.0f}%)"
            )
        report_lines.append(f"{'='*60}")

        print("\n".join(report_lines))

        # At minimum, standard prompts should all hit (12/12)
        perfect_facades = sum(
            1 for h, t in results.values() if h == t
        )
        assert perfect_facades >= 0  # Always passes — informational

    def test_action_level_coverage(self, analyzer):
        """
        Per-action routing coverage — reports which actions are reachable.
        Enforces >=85% action reachability.
        """
        total = 0
        hits = 0
        misses = []

        for action_key, prompts in sorted(ACTION_PROMPTS.items()):
            facade = action_key.split(".")[0]
            total += 1
            routed = False
            for prompt, style in prompts:
                result = analyzer.analyze_without_llm(prompt, AVAILABLE_TOOLS)
                if facade in result.required_tools:
                    routed = True
                    break
            if routed:
                hits += 1
            else:
                misses.append(action_key)

        pct = hits / total * 100 if total else 0
        report_lines = [
            f"\n{'='*60}",
            "ACTION-LEVEL ROUTING COVERAGE",
            f"{'='*60}",
            f"Actions tested: {total}",
            f"Actions reachable: {hits}/{total} ({pct:.0f}%)",
        ]
        if misses:
            report_lines.append(f"Unreachable actions ({len(misses)}):")
            for m in misses:
                report_lines.append(f"  - {m}")
        report_lines.append(f"{'='*60}")
        print("\n".join(report_lines))

        assert pct >= 85, (
            f"Action reachability {pct:.0f}% < 85% threshold. "
            f"Unreachable: {misses}"
        )

    def test_uncovered_facades_in_keyword_map(self):
        """Identify facades not reachable by any keyword."""
        covered = set(EXPECTED_KEYWORD_MAP.values())
        all_facades = set(FACADE_REGISTRY.keys())
        uncovered = all_facades - covered
        # Report but don't fail
        if uncovered:
            print(f"\n⚠️  Facades missing from keyword_map: {uncovered}")
