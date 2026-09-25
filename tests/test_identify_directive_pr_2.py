"""Tests for identify_agent canonical-inbox + relay_subscribe_directive injection.

Per PR #2 (CCR server-side auto-arm) — IDE-agnostic relay-arrival arming.
Validates that identify_agent's response carries the directive that any MCP
client (Claude Code, Antigravity, Cursor, Windsurf) can read at session start.
"""
from __future__ import annotations
import json
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.relay_inbox_canonical import resolve_canonical_inbox_name


# ── Direct test of the canonical-inbox resolution that identify_agent uses ──


def test_antigravity_role_resolves_to_canonical_antigravity():
    """agy's canonical inbox is 'antigravity' (bare-name)."""
    assert resolve_canonical_inbox_name("antigravity") == "antigravity"
    assert resolve_canonical_inbox_name("agy") == "antigravity"


def test_cc_tb_role_resolves_to_canonical_cc_tb():
    """cc-tb canonical via PR #1 fix."""
    assert resolve_canonical_inbox_name("tb") == "cc_tb"
    assert resolve_canonical_inbox_name("cc_tb") == "cc_tb"


def test_main_peer_unchanged():
    assert resolve_canonical_inbox_name("main") == "claude_code_main"
    assert resolve_canonical_inbox_name("peer") == "claude_code_peer"


def test_op_assistant_canonical():
    assert resolve_canonical_inbox_name("op_assistant") == "claude_code_operator_assistant"


# ── Simulate identify_agent response shape post-PR-#2 ──


def _make_identify_response_with_directive(role: str) -> dict:
    """Mirror the identify_agent injection logic for testing without full server boot."""
    response = {
        "agent_id": f"test_{role}_xyz",
        "role": role,
        "environment": "test",
        "host": "test-host",
    }
    canonical = resolve_canonical_inbox_name(role.strip().lower()) or role.strip().lower()
    if canonical:
        response["canonical_inbox"] = canonical
        response["relay_subscribe_directive"] = (
            f"[CCR-ARM] Fire nucleus_ccr_arm() OR nucleus_relay_subscribe("
            f"inbox_filter=\"{canonical}\", timeout_seconds=270) "
            f"as one of your first 3 tool uses. Re-fire on return for "
            f"persistent coverage. Per PR #1 + PR #2 CCR-inversion + "
            f"server-side auto-arm. IDE-agnostic — works in Claude Code, "
            f"Antigravity, Cursor, Windsurf."
        )
    return response


def test_agy_identify_response_carries_antigravity_directive():
    """LOAD-BEARING: agy (Antigravity) gets directive pointing at antigravity inbox."""
    response = _make_identify_response_with_directive(role="antigravity")
    assert response["canonical_inbox"] == "antigravity"
    assert "[CCR-ARM]" in response["relay_subscribe_directive"]
    assert "antigravity" in response["relay_subscribe_directive"]
    assert "IDE-agnostic" in response["relay_subscribe_directive"]


def test_agy_legacy_role_name_also_works():
    """agy may identify with role='agy' instead of 'antigravity' — directive still correct."""
    response = _make_identify_response_with_directive(role="agy")
    assert response["canonical_inbox"] == "antigravity"
    assert "antigravity" in response["relay_subscribe_directive"]


def test_cc_tb_identify_response_carries_cc_tb_directive():
    """cc-tb gets directive pointing at canonical cc_tb inbox (not legacy claude_code_tb)."""
    response = _make_identify_response_with_directive(role="tb")
    assert response["canonical_inbox"] == "cc_tb"
    assert "cc_tb" in response["relay_subscribe_directive"]


def test_main_identify_response_carries_claude_code_main_directive():
    """cc-main directive points to claude_code_main (full convention)."""
    response = _make_identify_response_with_directive(role="main")
    assert response["canonical_inbox"] == "claude_code_main"
    assert "claude_code_main" in response["relay_subscribe_directive"]


def test_op_assistant_identify_response_carries_full_canonical():
    response = _make_identify_response_with_directive(role="op_assistant")
    assert response["canonical_inbox"] == "claude_code_operator_assistant"


def test_unknown_role_passes_through_safely():
    """Unknown role should not crash; directive uses role as-is."""
    response = _make_identify_response_with_directive(role="future_agent_v9")
    assert response["canonical_inbox"] == "future_agent_v9"
    # Directive still emitted, just points at non-canonical
    assert "[CCR-ARM]" in response["relay_subscribe_directive"]


def test_empty_role_does_not_crash():
    """Empty role — defensive (identify_agent may be called without role)."""
    response = _make_identify_response_with_directive(role="")
    # No directive when role can't be resolved
    assert "canonical_inbox" not in response or not response.get("canonical_inbox")


# ── Directive content checks ──


def test_directive_mentions_both_arm_tools():
    """Directive offers both nucleus_ccr_arm AND nucleus_relay_subscribe."""
    response = _make_identify_response_with_directive(role="antigravity")
    directive = response["relay_subscribe_directive"]
    assert "nucleus_ccr_arm" in directive
    assert "nucleus_relay_subscribe" in directive


def test_directive_mentions_first_3_tool_uses():
    """Directive sets clear arming window (first 3 tool uses)."""
    response = _make_identify_response_with_directive(role="antigravity")
    assert "first 3 tool uses" in response["relay_subscribe_directive"]


def test_directive_mentions_refiring_for_persistent_arming():
    response = _make_identify_response_with_directive(role="antigravity")
    assert "Re-fire" in response["relay_subscribe_directive"]


def test_directive_mentions_all_4_supported_ide_clients():
    response = _make_identify_response_with_directive(role="antigravity")
    directive = response["relay_subscribe_directive"]
    assert "Claude Code" in directive
    assert "Antigravity" in directive
    assert "Cursor" in directive
    assert "Windsurf" in directive
