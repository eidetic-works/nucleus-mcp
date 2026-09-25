"""Atom 4: marketplace_whoami MCP action tests."""
import json
import pytest

from mcp_server_nucleus.runtime.marketplace import register_tool


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)
    return brain


def _call_whoami(params=None):
    """Call the whoami logic directly (mirrors sync.py handler, avoids MCP scaffolding)."""
    import os
    from mcp_server_nucleus.runtime.marketplace import (
        lookup_by_address,
        ReputationSignals,
        TrustTier,
    )

    p = params or {}
    role = p.get("role") or os.environ.get("CC_SESSION_ROLE", "")
    if role:
        address = f"{role.lower().replace('_', '-')}@nucleus"
    else:
        return {"registered": False, "reason": "CC_SESSION_ROLE not set and no role param"}

    card = lookup_by_address(address)
    if card is None:
        return {"registered": False, "address": address}

    metrics = ReputationSignals.compute_signals(address)
    tier_int = card.get("tier", TrustTier.UNVERIFIED)
    tier_badge = card.get("tier_badge", TrustTier.get_display_badge(TrustTier.UNVERIFIED))

    return {
        "registered": True,
        "address": address,
        "display_name": card.get("display_name"),
        "tier": tier_int,
        "tier_badge": tier_badge,
        "connection_count": metrics.get("connection_count", 0),
        "success_rate": metrics.get("success_rate", 1.0),
        "avg_response_ms": metrics.get("avg_response_ms", 0),
        "last_seen_at": metrics.get("last_seen_at"),
        "last_promoted_at": card.get("last_promoted_at"),
        "inactive": card.get("inactive", False),
    }


def test_whoami_registered_address(isolated_brain, monkeypatch):
    """Registered address must return full identity dict."""
    monkeypatch.setenv("CC_SESSION_ROLE", "claude_code_main")

    # Register a card for the address that whoami will resolve
    register_tool(
        {
            "address": "claude-code-main@nucleus",
            "display_name": "Claude Code Main",
            "accepts": ["*"],
            "emits": ["*"],
            "tags": ["claude"],
        },
        brain_path=isolated_brain,
    )

    result = _call_whoami()
    assert result["registered"] is True
    assert result["address"] == "claude-code-main@nucleus"
    assert "tier" in result
    assert "tier_badge" in result
    assert "connection_count" in result


def test_whoami_unregistered_returns_false(isolated_brain, monkeypatch):
    """Unregistered address must return {registered: false} — not 404."""
    monkeypatch.setenv("CC_SESSION_ROLE", "unknown_agent")

    result = _call_whoami()
    assert result["registered"] is False
    assert "address" in result


def test_whoami_no_role_env_no_param(isolated_brain):
    """No env var and no role param must return {registered: false} gracefully."""
    result = _call_whoami()
    assert result["registered"] is False
    assert "reason" in result
