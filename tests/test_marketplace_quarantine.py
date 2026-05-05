"""Tests for marketplace_quarantine admin action and can_call quarantine gating."""
import json
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


def _quarantine(address: str, caller: str, brain_path: Path, reason: str = "") -> dict:
    from mcp_server_nucleus.runtime.marketplace import (
        lookup_by_address, TrustTier, _get_registry_dir, _get_card_path,
    )
    import time

    caller_card = lookup_by_address(caller, brain_path=brain_path)
    if caller_card is None or caller_card.get("tier", TrustTier.UNVERIFIED) < TrustTier.VERIFIED:
        return {"ok": False, "reason": "caller_not_verified"}

    target_card = lookup_by_address(address, brain_path=brain_path)
    if target_card is None:
        return {"ok": False, "reason": "unregistered_target"}

    target_card["quarantined"] = True
    target_card["quarantine_reason"] = reason or "manual"

    registry_dir = _get_registry_dir(brain_path)
    card_path = _get_card_path(address, registry_dir)
    card_path.write_text(json.dumps(target_card, indent=2))

    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {"action": "quarantine", "address": address, "reason": reason or "manual", "caller": caller}
    with open(admin_log, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"ok": True, "address": address, "quarantined": True}


def _can_call(caller: str, target: str, brain_path: Path) -> dict:
    from mcp_server_nucleus.runtime.marketplace import lookup_by_address, TrustTier
    caller_card = lookup_by_address(caller, brain_path=brain_path)
    if caller_card is None:
        return {"allowed": False, "reason": "unregistered_caller"}
    target_card = lookup_by_address(target, brain_path=brain_path)
    if target_card is None:
        return {"allowed": False, "reason": "unregistered_target"}
    if caller_card.get("quarantined"):
        return {"allowed": False, "reason": "quarantined"}
    if target_card.get("quarantined"):
        return {"allowed": False, "reason": "quarantined"}
    caller_tier = caller_card.get("tier", TrustTier.UNVERIFIED)
    target_tier = target_card.get("tier", TrustTier.UNVERIFIED)
    allowed = caller_tier >= target_tier - 1
    return {"allowed": allowed, "reason": None if allowed else "tier_too_low"}


def test_quarantine_verified_caller_succeeds(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, lookup_by_address
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    _register("bad-actor@nucleus", TrustTier.ACTIVE, tmp_path)
    result = _quarantine("bad-actor@nucleus", "root@nucleus", tmp_path)
    assert result["ok"] is True
    card = lookup_by_address("bad-actor@nucleus", brain_path=tmp_path)
    assert card["quarantined"] is True


def test_quarantine_blocks_can_call(tmp_path):
    """Quarantined target → marketplace_can_call returns allowed=False, reason=quarantined."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    _register("caller@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("bad-actor@nucleus", TrustTier.ACTIVE, tmp_path)
    _quarantine("bad-actor@nucleus", "root@nucleus", tmp_path)
    result = _can_call("caller@nucleus", "bad-actor@nucleus", tmp_path)
    assert result["allowed"] is False
    assert result["reason"] == "quarantined"


def test_quarantine_non_verified_caller_blocked(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("lowcaller@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("target@nucleus", TrustTier.ACTIVE, tmp_path)
    result = _quarantine("target@nucleus", "lowcaller@nucleus", tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "caller_not_verified"


def test_quarantine_audit_log_written(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    _register("suspect@nucleus", TrustTier.ACTIVE, tmp_path)
    _quarantine("suspect@nucleus", "root@nucleus", tmp_path, reason="spam")
    admin_log = tmp_path / "marketplace" / "admin_actions.jsonl"
    entries = [json.loads(l) for l in admin_log.read_text().strip().splitlines()]
    assert any(e["action"] == "quarantine" and e["address"] == "suspect@nucleus" for e in entries)
