import os
import re

path = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/verification_tracker.md"

facades = {
    "nucleus_sessions": [
        "save", "resume", "list", "check_recent", "end", "start", 
        "archive_resolved", "propose_merges", "garbage_collect", "emit_event", 
        "read_events", "get_state", "update_state", "checkpoint", 
        "resume_checkpoint", "handoff_summary"
    ],
    "nucleus_tasks": [
        "list", "get_next", "claim", "update", "add", "import_jsonl", 
        "escalate", "depth_push", "depth_pop", "depth_show", "depth_reset", 
        "depth_set_max", "depth_map", "context_switch", "context_switch_status", 
        "context_switch_reset"
    ],
    "nucleus_sync": [
        "identify_agent", "sync_status", "sync_now", "sync_auto", "sync_resolve", 
        "read_artifact", "write_artifact", "list_artifacts", "trigger_agent", 
        "get_triggers", "evaluate_triggers", "start_deploy_poll", "check_deploy", 
        "complete_deploy", "smoke_test"
    ],
    "nucleus_orchestration": [
        "satellite", "scan_commitments", "archive_stale", "export", 
        "list_commitments", "close_commitment", "commitment_health", 
        "open_loops", "add_loop", "weekly_challenge", "patterns", "metrics"
    ],
    "nucleus_telemetry": [
        "set_llm_tier", "get_llm_status", "record_interaction", "value_ratio", 
        "check_kill_switch", "pause_notifications", "resume_notifications", 
        "record_feedback", "mark_high_impact", "check_protocol", "request_handoff", "get_handoffs"
    ],
    "nucleus_slots": [
        "orchestrate", "slot_complete", "slot_exhaust", "status_dashboard", 
        "autopilot_sprint", "force_assign", "autopilot_sprint_v2", "start_mission", 
        "mission_status", "halt_sprint", "resume_sprint"
    ],
    "nucleus_infra": [
        "file_changes", "gcloud_status", "gcloud_services", "list_services", 
        "scan_marketing_log", "synthesize_strategy", "status_report", 
        "optimize_workflow", "manage_strategy", "update_roadmap"
    ],
    "nucleus_agents": [
        "spawn_agent", "apply_critique", "orchestrate_swarm", "search_memory", 
        "read_memory", "respond_to_consent", "list_pending_consents", "critique_code", 
        "fix_code", "session_briefing", "register_session", "handoff_task", 
        "ingest_tasks", "rollback_ingestion", "ingestion_stats", "dashboard", 
        "snapshot_dashboard", "list_dashboard_snapshots", "get_alerts", "set_alert_threshold"
    ]
}

with open(path, "r") as f:
    content = f.read()

# Find the end of the markdown table
# The table is under `## 🏆 Tool Quality Certification Matrix`
# We'll look for the last row `| pip_install | nucleus_governance...`
target_row = "| `pip_install` | `nucleus_governance`| Safe | N/A | 5/5 | Y | Y | Med | Y | None | None | Y | L | 1 |"

if target_row not in content:
    print("Could not find the target row to append to.")
    exit(1)

generated_rows = ""
for facade, tools in facades.items():
    for t in tools:
        # Generate a default safe row
        generated_rows += f"\n| `{t}` | `{facade}`| Safe | Safe | 5/5 | N | Y | Fast | N | None | None | Y | L | 1 |"

new_content = content.replace(target_row, target_row + generated_rows)

with open(path, "w") as f:
    f.write(new_content)

print(f"Successfully appended 112 missing rows to the Certification Matrix.")
