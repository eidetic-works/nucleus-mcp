"""Tests for canonical role→inbox-dir map (PR #1 fix to relay-arrival-invisible).

Validates:
- Canonical mapping per feedback_relay_inbox_dir_canonical_v1.md
- The specific bug fix: cc-tb role variants all map to canonical `cc_tb`
- _resolve_inbox_dir respects inbox_filter override
- Deprecated dir → canonical replacement logic
"""
from __future__ import annotations

from mcp_server_nucleus.runtime.relay_inbox_canonical import (
    CANONICAL_ROLE_TO_INBOX_DIR,
    DEPRECATED_DIR_TO_CANONICAL,
    resolve_canonical_inbox_name,
    is_deprecated_inbox,
    deprecated_to_canonical,
)


# ── The specific bug fix: cc-tb role variants ──


def test_cc_tb_role_maps_to_canonical_cc_tb():
    """LOAD-BEARING: closes 3-week-old gap. All cc-tb role variants map to cc_tb."""
    assert resolve_canonical_inbox_name("tb") == "cc_tb"
    assert resolve_canonical_inbox_name("cc_tb") == "cc_tb"
    assert resolve_canonical_inbox_name("claude_code_tb") == "cc_tb"  # legacy alias


def test_cc_tb_case_insensitive():
    assert resolve_canonical_inbox_name("TB") == "cc_tb"
    assert resolve_canonical_inbox_name("CC_TB") == "cc_tb"


def test_cc_tb_handles_hyphens_in_role():
    assert resolve_canonical_inbox_name("cc-tb") == "cc_tb"


# ── Main / peer mapping unchanged ──


def test_main_maps_to_claude_code_main():
    assert resolve_canonical_inbox_name("main") == "claude_code_main"
    assert resolve_canonical_inbox_name("claude_code_main") == "claude_code_main"


def test_peer_maps_to_claude_code_peer():
    assert resolve_canonical_inbox_name("peer") == "claude_code_peer"
    assert resolve_canonical_inbox_name("claude_code_peer") == "claude_code_peer"


# ── op-assistant / antigravity ──


def test_op_assistant_canonical():
    assert resolve_canonical_inbox_name("op_assistant") == "claude_code_operator_assistant"
    assert resolve_canonical_inbox_name("operator_assistant") == "claude_code_operator_assistant"


def test_ops_short_alias_maps_to_operator_assistant():
    """Task #62 F2: phone/Dispatch ergonomics — 'ops' is the shortest
    unambiguous alias for the operator-assistant inbox."""
    assert resolve_canonical_inbox_name("ops") == "claude_code_operator_assistant"
    assert resolve_canonical_inbox_name("OPS") == "claude_code_operator_assistant"


def test_agy_aliases_to_antigravity():
    assert resolve_canonical_inbox_name("agy") == "antigravity"
    assert resolve_canonical_inbox_name("antigravity") == "antigravity"


# ── Edge cases ──


def test_unknown_role_passes_through():
    """Unknown roles return name unchanged (defensive)."""
    assert resolve_canonical_inbox_name("future_agent_x") == "future_agent_x"


def test_empty_role_returns_empty():
    assert resolve_canonical_inbox_name("") == ""


# ── Deprecated dir detection + remapping ──


def test_deprecated_inbox_detection():
    assert is_deprecated_inbox("op_assistant")
    assert is_deprecated_inbox("claude_code_tb")
    assert is_deprecated_inbox("cowork")
    assert not is_deprecated_inbox("claude_code_main")
    assert not is_deprecated_inbox("cc_tb")


def test_deprecated_to_canonical_remaps():
    assert deprecated_to_canonical("op_assistant") == "claude_code_operator_assistant"
    assert deprecated_to_canonical("claude_code_tb") == "cc_tb"
    assert deprecated_to_canonical("claude_code_main") == "claude_code_main"  # not deprecated


# ── Canonical list completeness ──


def test_canonical_map_includes_all_5_active_fleet_roles():
    """Per feedback_relay_inbox_dir_canonical_v1.md: 5 canonical agents."""
    canonical_dirs = set(CANONICAL_ROLE_TO_INBOX_DIR.values())
    assert "claude_code_main" in canonical_dirs
    assert "claude_code_peer" in canonical_dirs
    assert "cc_tb" in canonical_dirs
    assert "claude_code_operator_assistant" in canonical_dirs
    assert "antigravity" in canonical_dirs


def test_deprecated_map_includes_known_misroutes():
    """Per cc-peer 9th scout finding: known misroutes that caused agy BOUNDARY GREEN loss."""
    assert "op_assistant" in DEPRECATED_DIR_TO_CANONICAL
    assert "operator_assistant" in DEPRECATED_DIR_TO_CANONICAL


# ── Map-key normalization invariant (PR #541 peer poke 4) ──


def test_canonical_values_resolve_round_trip():
    """Every canonical dir name must resolve to itself. Lookup keys are
    normalized ('-' -> '_') at resolve time, so a hyphenated map key is dead:
    'claude_code_main-debug' used to miss its own entry and pass through as
    'claude_code_main_debug', making HTTP-mode status silently report 0/0
    for a real on-disk inbox."""
    for v in set(CANONICAL_ROLE_TO_INBOX_DIR.values()):
        assert resolve_canonical_inbox_name(v) == v, (
            f"map value {v!r} fails resolve round-trip — key normalization "
            "invariant violated"
        )
