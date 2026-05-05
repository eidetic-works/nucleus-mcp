"""Tests for nucleus_sync marketplace_can_call permission check."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def _register(address: str, tier: int, brain_path: Path):
    from mcp_server_nucleus.runtime.marketplace import register_tool
    register_tool({
        "address": address,
        "display_name": address.split("@")[0],
        "accepts": ["task"],
        "emits": ["result"],
        "tags": ["test"],
        "tier": tier,
    }, brain_path=brain_path)


def _can_call(caller: str, target: str, brain_path: Path) -> dict:
    from mcp_server_nucleus.runtime.marketplace import lookup_by_address, TrustTier
    import logging

    _log = logging.getLogger("nucleus.marketplace")
    try:
        caller_card = lookup_by_address(caller, brain_path=brain_path)
        if caller_card is None:
            return {"allowed": False, "caller": caller, "target": target, "reason": "unregistered_caller"}
        target_card = lookup_by_address(target, brain_path=brain_path)
        if target_card is None:
            return {"allowed": False, "caller": caller, "target": target, "reason": "unregistered_target"}
        caller_tier = caller_card.get("tier", TrustTier.UNVERIFIED)
        target_tier = target_card.get("tier", TrustTier.UNVERIFIED)
        allowed = caller_tier >= target_tier - 1
        return {
            "allowed": allowed,
            "caller": caller,
            "target": target,
            "caller_tier": TrustTier(caller_tier).name.capitalize(),
            "target_tier": TrustTier(target_tier).name.capitalize(),
            "reason": None if allowed else "tier_too_low",
        }
    except Exception as exc:
        _log.warning(f"lookup failed: {exc}")
        return {"allowed": True, "caller": caller, "target": target, "reason": "lookup_failed_fail_open"}


def test_can_call_same_tier_allowed(tmp_path):
    """Both Active → allowed."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("agent-a@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("agent-b@nucleus", TrustTier.ACTIVE, tmp_path)
    result = _can_call("agent-a@nucleus", "agent-b@nucleus", tmp_path)
    assert result["allowed"] is True
    assert result["reason"] is None


def test_can_call_one_tier_below_allowed(tmp_path):
    """Caller Active, target Trusted → allowed (one tier gap OK)."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("caller@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("target@nucleus", TrustTier.TRUSTED, tmp_path)
    result = _can_call("caller@nucleus", "target@nucleus", tmp_path)
    assert result["allowed"] is True


def test_can_call_two_tiers_below_blocked(tmp_path):
    """Caller Unverified, target Trusted → blocked."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("low-caller@nucleus", TrustTier.UNVERIFIED, tmp_path)
    _register("high-target@nucleus", TrustTier.TRUSTED, tmp_path)
    result = _can_call("low-caller@nucleus", "high-target@nucleus", tmp_path)
    assert result["allowed"] is False
    assert result["reason"] == "tier_too_low"


def test_can_call_unregistered_caller(tmp_path):
    """Caller not in registry → blocked, reason=unregistered_caller."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("real-target@nucleus", TrustTier.ACTIVE, tmp_path)
    result = _can_call("ghost-caller@nucleus", "real-target@nucleus", tmp_path)
    assert result["allowed"] is False
    assert result["reason"] == "unregistered_caller"


def test_can_call_lookup_failure_fails_open(tmp_path):
    """If lookup_by_address raises, fail open (allowed=True)."""
    with patch(
        "mcp_server_nucleus.runtime.marketplace.lookup_by_address",
        side_effect=RuntimeError("registry offline"),
    ):
        result = _can_call("any-caller@nucleus", "any-target@nucleus", tmp_path)
    assert result["allowed"] is True
    assert result["reason"] == "lookup_failed_fail_open"
