"""Coverage tests for mcp_server_nucleus.runtime.tool_tiers."""
from mcp_server_nucleus.runtime.tool_tiers import (
    ToolTier,
    TOOL_TIER_MAPPING,
    get_tool_tier,
    is_authorized,
)


def test_tool_tier_values():
    assert ToolTier.T0_READ == 0
    assert ToolTier.T1_INFO == 1
    assert ToolTier.T2_CODE == 2
    assert ToolTier.T3_SYSTEM == 3


def test_get_tool_tier_known():
    assert get_tool_tier("nucleus_tasks", "list") == ToolTier.T0_READ
    assert get_tool_tier("nucleus_engrams", "audit_log") == ToolTier.T1_INFO
    assert get_tool_tier("nucleus_tasks", "add") == ToolTier.T2_CODE
    assert get_tool_tier("nucleus_governance", "lock") == ToolTier.T3_SYSTEM


def test_get_tool_tier_unknown_defaults_t2():
    assert get_tool_tier("unknown_facade", "unknown_action") == ToolTier.T2_CODE


def test_is_authorized_short_names():
    assert is_authorized("T0", "nucleus_tasks", "list") is True
    assert is_authorized("T0", "nucleus_tasks", "add") is False
    assert is_authorized("T1", "nucleus_engrams", "audit_log") is True
    assert is_authorized("T2", "nucleus_tasks", "add") is True
    assert is_authorized("T3", "nucleus_governance", "lock") is True


def test_is_authorized_full_names():
    assert is_authorized("T0_READ", "nucleus_tasks", "list") is True
    assert is_authorized("T2_CODE", "nucleus_tasks", "add") is True
    assert is_authorized("T3_SYSTEM", "nucleus_governance", "delete_file") is True


def test_is_authorized_empty_defaults_t1():
    # Empty string defaults to T1_INFO
    assert is_authorized("", "nucleus_tasks", "list") is True
    assert is_authorized("", "nucleus_tasks", "add") is False


def test_is_authorized_invalid_defaults_t1():
    assert is_authorized("INVALID", "nucleus_tasks", "list") is True
    assert is_authorized("XYZ", "nucleus_tasks", "add") is False


def test_is_authorized_lowercase_normalizes():
    assert is_authorized("t2", "nucleus_tasks", "add") is True
    assert is_authorized("t0", "nucleus_tasks", "add") is False


def test_is_authorized_t1_blocked_from_t2():
    assert is_authorized("T1", "nucleus_tasks", "add") is False


def test_is_authorized_t2_blocked_from_t3():
    assert is_authorized("T2", "nucleus_governance", "lock") is False


def test_is_authorized_none_agent_tier():
    # None is falsy, defaults to T1_INFO
    assert is_authorized(None, "nucleus_tasks", "list") is True
    assert is_authorized(None, "nucleus_tasks", "add") is False


def test_tier_mapping_not_empty():
    assert len(TOOL_TIER_MAPPING) > 10
