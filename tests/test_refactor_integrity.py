#!/usr/bin/env python3
"""Refactor Integrity Sentinel Test.

This test verifies that all @mcp.tool() registered functions remain importable
from the mcp_server_nucleus package after any refactoring or extraction.

If any function is accidentally deleted during monolith decomposition,
this test will fail and identify exactly which function(s) are missing.

Generated from __init__.py v1.0.7 — 146 registered MCP tools.
"""

import os
import tempfile
import unittest

# Set up test environment before importing
_test_dir = tempfile.mkdtemp(prefix="nucleus_integrity_env_")
os.environ.setdefault("NUCLEAR_BRAIN_PATH", _test_dir)
os.environ.setdefault("NUCLEUS_SKIP_AUTOSTART", "true")
os.environ.setdefault("NUCLEUS_UNSAFE_SYNC", "true")


# Complete list of @mcp.tool() decorated functions that must remain importable
EXPECTED_MCP_TOOLS = [
    # Hypervisor tools
    "brain_auto_fix_loop",
    "lock_resource",
    "unlock_resource",
    "set_hypervisor_mode",
    "nucleus_list_directory",
    "nucleus_delete_file",
    "watch_resource",
    "hypervisor_status",
    
    # Feature Map tools
    "brain_add_feature",
    "brain_list_features",
    "brain_get_feature",
    "brain_update_feature",
    "brain_mark_validated",
    
    # Consolidation tools
    "brain_archive_resolved",
    "brain_propose_merges",
    "brain_emit_event",
    "brain_read_events",
    "brain_get_state",
    "brain_update_state",
    
    # Multi-Agent Sync tools
    "brain_identify_agent",
    
    # Mounter/Mount tools
    "brain_list_mounted",
    "brain_list_tools",
    
    # Proof tools
    "brain_generate_proof",
    "brain_list_proofs",
    "brain_get_proof",
    
    # Session tools
    "brain_register_session",
    "brain_list_sessions",
    "brain_check_recent_session",
    
    # Deploy tools
    "brain_start_deploy_poll",
    "brain_check_deploy",
    "brain_complete_deploy",
    "brain_smoke_test",
    
    # Task Management tools
    "brain_add_task",
    "brain_list_tasks",
    "brain_update_task",
    "brain_claim_task",
    "brain_get_next_task",
    "brain_checkpoint_task",
    "brain_resume_from_checkpoint",
    "brain_import_tasks_from_jsonl",
    "brain_force_assign",
    "brain_handoff_task",
    "brain_escalate",
    
    # Artifact tools
    "brain_read_artifact",
    "brain_write_artifact",
    "brain_list_artifacts",
    "brain_trigger_agent",
    "brain_get_triggers",
    "brain_evaluate_triggers",
    
    # Governance tools
    "brain_audit_log",
    "brain_governance_status",
    "brain_health",
    
    # Engram tools
    "brain_write_engram",
    "brain_query_engrams",
    "brain_search_engrams",
    
    # Depth tools
    "brain_depth_push",
    "brain_depth_pop",
    "brain_depth_show",
    "brain_depth_map",
    "brain_depth_set_max",
    "brain_depth_reset",
    
    # Mission & Strategy tools
    "brain_start_mission",
    "brain_mission_status",
    "brain_manage_strategy",
    "brain_status_dashboard",
    "brain_dashboard",
    "brain_version",
    
    # Sprint tools
    "brain_autopilot_sprint",
    "brain_autopilot_sprint_v2",
    "brain_halt_sprint",
    "brain_resume_sprint",
    
    # Decision System tools
    "brain_dsor_status",
    "brain_list_decisions",
    "brain_list_snapshots",
    "brain_snapshot_dashboard",
    
    # Loop tools
    "brain_add_loop",
    "brain_open_loops",
    
    # Commitment tools
    "brain_scan_commitments",
    "brain_list_commitments",
    "brain_close_commitment",
    "brain_commitment_health",
    "brain_mark_high_impact",
    
    # Session management
    "brain_session_start",
    "brain_session_briefing",
    "brain_save_session",
    "brain_resume_session",
    "brain_generate_handoff_summary",
    "brain_request_handoff",
    "brain_get_handoffs",
    
    # Protocol tools
    "brain_check_protocol",
    "brain_check_kill_switch",
    
    # GCloud tools
    "brain_gcloud_status",
    "brain_gcloud_services",
    
    # Render tools
    "brain_list_services",
    
    # Ingestion tools
    "brain_ingest_tasks",
    "brain_rollback_ingestion",
    "brain_ingestion_stats",
    
    # Memory & Sync tools
    "brain_sync_status",
    "brain_sync_now",
    "brain_sync_auto",
    "brain_sync_resolve",
    "brain_read_memory",
    "brain_search_memory",
    
    # Export & Archive
    "brain_export",
    "brain_archive_stale",
    "brain_file_changes",
    "brain_synthesize_status_report",
    
    # LLM/AI tools
    "brain_get_llm_status",
    "brain_set_llm_tier",
    "brain_critique_code",
    "brain_apply_critique",
    "brain_fix_code",
    
    # Federation tools
    "brain_federation_status",
    "brain_federation_join",
    "brain_federation_leave",
    "brain_federation_peers",
    "brain_federation_sync",
    "brain_federation_route",
    "brain_federation_health",
    "brain_federation_dsor_status",
    
    # Metering & Metrics
    "brain_metering_summary",
    "brain_slot_exhaust",
    "brain_slot_complete",
    "brain_metrics",
    "brain_performance_metrics",
    "brain_prometheus_metrics",
    
    # Other tools
    "brain_search_features",
    "brain_value_ratio",
    "brain_tier_status",
    "brain_ipc_tokens",
    "brain_patterns",
    "brain_optimize_workflow",
    "brain_orchestrate",
    "brain_satellite_view",
    "brain_routing_decisions",
    "brain_record_feedback",
    "brain_record_interaction",
    "brain_weekly_challenge",
    "brain_update_roadmap",
    "brain_synthesize_strategy",
    "brain_scan_marketing_log",
    "brain_get_alerts",
    "brain_set_alert_threshold",
    "brain_pause_notifications",
    "brain_resume_notifications",
]


class TestRefactorIntegrity(unittest.TestCase):
    """Sentinel test: verifies all MCP tools remain importable after refactoring."""

    def test_all_mcp_tools_importable(self):
        """Every @mcp.tool() function must be importable from mcp_server_nucleus."""
        import mcp_server_nucleus
        
        missing = []
        for tool_name in EXPECTED_MCP_TOOLS:
            if not hasattr(mcp_server_nucleus, tool_name):
                missing.append(tool_name)
        
        self.assertEqual(
            missing, [],
            f"\n\n🛑 REFACTOR INTEGRITY FAILURE!\n"
            f"The following {len(missing)} MCP tool(s) are no longer importable "
            f"from mcp_server_nucleus:\n"
            + "\n".join(f"  ❌ {name}" for name in missing)
            + "\n\nThese tools MUST remain as @mcp.tool() decorated functions "
            "in __init__.py (they can delegate to runtime/ modules)."
        )

    def test_mcp_object_exists(self):
        """The mcp FastMCP instance must exist."""
        import mcp_server_nucleus
        self.assertTrue(
            hasattr(mcp_server_nucleus, 'mcp'),
            "mcp FastMCP instance not found in mcp_server_nucleus"
        )

    def test_tool_count_minimum(self):
        """Ensure we haven't accidentally lost a large batch of tools."""
        import mcp_server_nucleus
        
        tool_count = sum(
            1 for name in dir(mcp_server_nucleus)
            if name.startswith("brain_") or name in [
                "lock_resource", "unlock_resource", "set_hypervisor_mode",
                "hypervisor_status", "watch_resource",
                "nucleus_list_directory", "nucleus_delete_file"
            ]
        )
        
        self.assertGreaterEqual(
            tool_count, 100,
            f"Only {tool_count} tools found — expected at least 100. "
            "Major tool loss detected during refactoring."
        )


if __name__ == "__main__":
    unittest.main()
