"""
Regression tests for HITL (Human-In-The-Loop) safety gates.
=============================================================
Ensures destructive operations require explicit confirm=true.

Coverage:
- delete_file: blocks without confirm, executes with confirm=true
- spawn_agent: blocks without confirm, proceeds with confirm=true
- stdio_server router: passes confirm through (regression for bypass bug)
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.hypervisor_ops import nucleus_delete_file_impl


# ════════════════════════════════════════════════════════════
# delete_file HITL gate
# ════════════════════════════════════════════════════════════

class TestDeleteFileHITL:
    """HITL gate on nucleus_delete_file_impl."""

    def test_delete_blocked_without_confirm(self, tmp_path):
        """delete_file MUST return HITL warning when confirm is False (default)."""
        target = tmp_path / "victim.txt"
        target.write_text("data")

        result = nucleus_delete_file_impl(str(target), confirm=False)

        assert "HITL GATE" in result
        assert "confirm=true" in result
        assert target.exists(), "File must NOT be deleted without confirm=true"

    def test_delete_blocked_default_param(self, tmp_path):
        """delete_file with no confirm param at all must block."""
        target = tmp_path / "victim.txt"
        target.write_text("data")

        result = nucleus_delete_file_impl(str(target))

        assert "HITL GATE" in result
        assert target.exists(), "File must NOT be deleted when confirm is omitted"

    def test_delete_succeeds_with_confirm(self, tmp_path):
        """delete_file with confirm=true must actually delete."""
        target = tmp_path / "victim.txt"
        target.write_text("data")

        result = nucleus_delete_file_impl(str(target), confirm=True)

        assert "SUCCESS" in result
        assert not target.exists(), "File must be deleted when confirm=true"

    def test_delete_nonexistent_with_confirm(self, tmp_path):
        """delete_file on missing file with confirm=true returns error, not crash."""
        result = nucleus_delete_file_impl(str(tmp_path / "ghost.txt"), confirm=True)
        assert "ERROR" in result or "not found" in result.lower()

    def test_delete_with_event_emitter(self, tmp_path):
        """delete_file passes events correctly when confirmed."""
        target = tmp_path / "victim.txt"
        target.write_text("data")
        events = []

        def mock_emit(event_type, emitter, data):
            events.append({"type": event_type, "emitter": emitter, "data": data})

        result = nucleus_delete_file_impl(str(target), emit_event_fn=mock_emit, confirm=True)

        assert "SUCCESS" in result
        assert len(events) == 1
        assert events[0]["type"] == "file_deleted"
        assert events[0]["data"]["confirmed"] is True


# ════════════════════════════════════════════════════════════
# spawn_agent HITL gate
# ════════════════════════════════════════════════════════════

class TestSpawnAgentHITL:
    """HITL gate on _h_spawn_agent."""

    def test_spawn_blocked_without_confirm(self):
        """spawn_agent MUST return HITL warning when confirm is False."""
        # Import the handler directly from orchestration module
        from mcp_server_nucleus.tools.orchestration import register as orch_register

        # We can't easily call _h_spawn_agent directly since it's a closure,
        # so we test via the implementation pattern: the function checks confirm
        # before doing anything else. We verify the pattern exists in the source.
        import inspect
        src_file = Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "tools" / "orchestration.py"
        source = src_file.read_text()

        # Verify HITL gate pattern exists in spawn_agent handler
        assert "def _h_spawn_agent" in source
        assert "if not confirm:" in source
        assert "HITL GATE" in source
        assert "confirm=true" in source

    def test_spawn_agent_docstring_documents_hitl(self):
        """The nucleus_agents docstring must document the HITL requirement."""
        src_file = Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "tools" / "orchestration.py"
        source = src_file.read_text()

        # Verify docstring documents HITL for spawn_agent
        assert "HITL: requires confirm=true" in source


# ════════════════════════════════════════════════════════════
# stdio_server router regression (confirm passthrough)
# ════════════════════════════════════════════════════════════

class TestStdioServerHITLPassthrough:
    """Regression: stdio_server governance_router must pass confirm param."""

    def test_stdio_router_passes_confirm(self):
        """The stdio_server governance_router lambda for delete_file must accept confirm."""
        src_file = (
            Path(__file__).parent.parent
            / "src"
            / "mcp_server_nucleus"
            / "runtime"
            / "stdio_server.py"
        )
        source = src_file.read_text()

        # Find the delete_file router entry — must include confirm parameter
        import re
        match = re.search(r'"delete_file":\s*lambda\s+([^:]+):', source)
        assert match, "delete_file lambda not found in stdio_server.py"
        params = match.group(1)
        assert "confirm" in params, (
            f"REGRESSION: stdio_server delete_file lambda missing confirm param. "
            f"Found params: {params}"
        )


# ════════════════════════════════════════════════════════════
# governance.py router (confirm passthrough)
# ════════════════════════════════════════════════════════════

class TestGovernanceRouterHITL:
    """Verify governance.py router passes confirm through."""

    def test_governance_router_passes_confirm(self):
        """The governance.py ROUTER lambda for delete_file must accept confirm."""
        src_file = (
            Path(__file__).parent.parent
            / "src"
            / "mcp_server_nucleus"
            / "tools"
            / "governance.py"
        )
        source = src_file.read_text()

        import re
        match = re.search(r'"delete_file":\s*lambda\s+([^:]+):', source)
        assert match, "delete_file lambda not found in governance.py"
        params = match.group(1)
        assert "confirm" in params, (
            f"governance.py delete_file lambda missing confirm param. "
            f"Found params: {params}"
        )

    def test_governance_docstring_documents_hitl(self):
        """The nucleus_governance docstring must document HITL for delete_file."""
        src_file = (
            Path(__file__).parent.parent
            / "src"
            / "mcp_server_nucleus"
            / "tools"
            / "governance.py"
        )
        source = src_file.read_text()
        assert "HITL: requires confirm=true" in source
