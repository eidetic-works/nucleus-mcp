#!/usr/bin/env python3
"""Refactor Integrity Sentinel Test.

This test verifies that all facade tools registered by the Super-Tools pattern
remain importable from the mcp_server_nucleus package.

Updated for v2.0 Super-Tools Facade: ~170 individual tools consolidated into
12 facade tools, each routing to original handlers via action dispatchers.
"""

import os
import tempfile
import unittest

# Set up test environment before importing
_test_dir = tempfile.mkdtemp(prefix="nucleus_integrity_env_")
os.environ.setdefault("NUCLEAR_BRAIN_PATH", _test_dir)
os.environ.setdefault("NUCLEUS_SKIP_AUTOSTART", "true")
os.environ.setdefault("NUCLEUS_UNSAFE_SYNC", "true")


# All 12 facade tools that must be registered after the Super-Tools refactor.
# Each facade consolidates multiple original tools via action routing.
EXPECTED_FACADE_TOOLS = [
    # governance.py → 1 facade (10 actions)
    "nucleus_governance",
    # federation.py → 1 facade (7 actions)
    "nucleus_federation",
    # sync.py → 1 facade (15 actions)
    "nucleus_sync",
    # tasks.py → 1 facade (16 actions)
    "nucleus_tasks",
    # features.py → 1 facade (16 actions)
    "nucleus_features",
    # sessions.py → 1 facade (16 actions)
    "nucleus_sessions",
    # engrams.py → 1 facade (25 actions)
    "nucleus_engrams",
    # orchestration.py → 5 sub-facades (65 actions total)
    "nucleus_orchestration",
    "nucleus_telemetry",
    "nucleus_slots",
    "nucleus_infra",
    "nucleus_agents",
]

# Mapping of facade → expected action names (spot-check subset)
FACADE_ACTION_CHECKS = {
    "nucleus_governance": ["auto_fix", "lock", "unlock", "mode", "status"],
    "nucleus_federation": ["status", "join", "leave", "peers", "health"],
    "nucleus_sync": ["identify", "sync_status", "sync_now", "read_artifact", "write_artifact"],
    "nucleus_tasks": ["list", "add", "claim", "update", "depth_push"],
    "nucleus_features": ["add", "list", "get", "mount_server", "generate_proof"],
    "nucleus_sessions": ["save", "resume", "start", "emit_event", "checkpoint"],
    "nucleus_engrams": ["health", "version", "write_engram", "morning_brief", "dsor_status"],
    "nucleus_orchestration": ["satellite", "scan_commitments", "open_loops", "metrics"],
    "nucleus_telemetry": ["set_llm_tier", "record_interaction", "check_protocol"],
    "nucleus_slots": ["orchestrate", "slot_complete", "start_mission", "halt_sprint"],
    "nucleus_infra": ["file_changes", "gcloud_status", "manage_strategy"],
    "nucleus_agents": ["spawn_agent", "critique_code", "dashboard", "ingest_tasks"],
}


class TestRefactorIntegrity(unittest.TestCase):
    """Sentinel test: verifies all facade tools remain importable after refactoring."""

    def test_all_facade_tools_importable(self):
        """Every facade tool must be importable from mcp_server_nucleus."""
        import mcp_server_nucleus

        missing = []
        for tool_name in EXPECTED_FACADE_TOOLS:
            if not hasattr(mcp_server_nucleus, tool_name):
                missing.append(tool_name)

        self.assertEqual(
            missing, [],
            f"\n\n🛑 FACADE INTEGRITY FAILURE!\n"
            f"The following {len(missing)} facade tool(s) are no longer importable "
            f"from mcp_server_nucleus:\n"
            + "\n".join(f"  ❌ {name}" for name in missing)
            + "\n\nThese facade tools MUST remain registered via their "
            "respective tools/*.py modules."
        )

    def test_mcp_object_exists(self):
        """The mcp FastMCP instance must exist."""
        import mcp_server_nucleus
        self.assertTrue(
            hasattr(mcp_server_nucleus, 'mcp'),
            "mcp FastMCP instance not found in mcp_server_nucleus"
        )

    def test_facade_tool_count(self):
        """Ensure correct number of facade tools are registered."""
        import mcp_server_nucleus

        tool_count = sum(
            1 for name in dir(mcp_server_nucleus)
            if name.startswith("nucleus_") and callable(getattr(mcp_server_nucleus, name, None))
        )

        self.assertGreaterEqual(
            tool_count, 12,
            f"Only {tool_count} facade tools found — expected at least 12. "
            "Facade tool loss detected during refactoring."
        )

    def test_facade_tools_are_callable(self):
        """Each facade tool must be callable."""
        import mcp_server_nucleus

        for tool_name in EXPECTED_FACADE_TOOLS:
            func = getattr(mcp_server_nucleus, tool_name, None)
            self.assertTrue(
                callable(func),
                f"Facade tool '{tool_name}' exists but is not callable."
            )

    def test_dispatch_module_exists(self):
        """The shared dispatcher module must be importable."""
        from mcp_server_nucleus.tools._dispatch import dispatch, async_dispatch
        self.assertTrue(callable(dispatch))
        self.assertTrue(callable(async_dispatch))

    def test_module_whitelisting(self):
        """NUCLEUS_ACTIVE_MODULES env var should filter modules."""
        from mcp_server_nucleus.tools import _get_active_modules, _ALL_MODULES

        # All modules when no whitelist
        os.environ.pop("NUCLEUS_ACTIVE_MODULES", None)
        all_mods = _get_active_modules()
        self.assertEqual(len(all_mods), len(_ALL_MODULES))

        # Filtered when whitelist is set
        os.environ["NUCLEUS_ACTIVE_MODULES"] = "governance,tasks"
        filtered = _get_active_modules()
        self.assertEqual(len(filtered), 2)
        os.environ.pop("NUCLEUS_ACTIVE_MODULES", None)


if __name__ == "__main__":
    unittest.main()
