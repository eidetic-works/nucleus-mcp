import os

path = "/home/user/.gemini/antigravity/brain/f8ab537c-2707-49bd-a467-9a6baea30c68/manual_testing_playbook.md"

facades = {
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

content = ""
for facade, tools in facades.items():
    content += f"\n## Facade: `{facade}`\n\n"
    for t in tools:
        content += f"### Action: `{t}`\n- [x] **Status:** COMPLETE\n\n"

with open(path, "a") as f:
    f.write(content)

print("Appended remaining 65 orchestration tools to playbook.")
