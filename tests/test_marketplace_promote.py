"""Tests for marketplace_promote admin action."""
import json
from pathlib import Path


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


def _promote(address: str, new_tier: str, caller: str, brain_path: Path) -> dict:
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

    try:
        tier_val = TrustTier[new_tier.upper()]
    except KeyError:
        return {"ok": False, "reason": f"unknown_tier '{new_tier}'"}

    old_tier = target_card.get("tier", TrustTier.UNVERIFIED)
    target_card["tier"] = int(tier_val)
    target_card["tier_badge"] = TrustTier.get_display_badge(tier_val)
    target_card["last_promoted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    registry_dir = _get_registry_dir(brain_path)
    card_path = _get_card_path(address, registry_dir)
    card_path.write_text(json.dumps(target_card, indent=2))

    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {"action": "promote", "address": address, "from_tier": old_tier,
             "to_tier": int(tier_val), "caller": caller}
    with open(admin_log, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"ok": True, "address": address, "old_tier": old_tier, "new_tier": int(tier_val)}


def test_promote_verified_caller_succeeds(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, lookup_by_address
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    _register("target@nucleus", TrustTier.UNVERIFIED, tmp_path)
    result = _promote("target@nucleus", "trusted", "root@nucleus", tmp_path)
    assert result["ok"] is True
    card = lookup_by_address("target@nucleus", brain_path=tmp_path)
    assert card["tier"] == TrustTier.TRUSTED


def test_promote_non_verified_caller_blocked(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("lowcaller@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("target@nucleus", TrustTier.UNVERIFIED, tmp_path)
    result = _promote("target@nucleus", "trusted", "lowcaller@nucleus", tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "caller_not_verified"


def test_promote_audit_log_written(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    _register("agent@nucleus", TrustTier.UNVERIFIED, tmp_path)
    _promote("agent@nucleus", "active", "root@nucleus", tmp_path)
    admin_log = tmp_path / "marketplace" / "admin_actions.jsonl"
    assert admin_log.exists()
    entries = [json.loads(l) for l in admin_log.read_text().strip().splitlines()]
    assert any(e["action"] == "promote" and e["address"] == "agent@nucleus" for e in entries)


def test_promote_unregistered_target_blocked(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, tmp_path)
    result = _promote("ghost@nucleus", "trusted", "root@nucleus", tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "unregistered_target"
