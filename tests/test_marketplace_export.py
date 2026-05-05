"""Tests for marketplace_export action."""
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


def _export(brain_path: Path) -> dict:
    from mcp_server_nucleus.runtime.marketplace import search_by_tags, ReputationSignals
    cards = search_by_tags([], brain_path=brain_path)
    snapshot = []
    for card in cards:
        address = card.get("address", "")
        rep = {}
        try:
            rep = ReputationSignals.compute_signals(address, brain_path=brain_path)
        except Exception:
            pass
        snapshot.append({**card, "reputation": rep})
    return {"snapshot": snapshot, "total": len(snapshot)}


def test_export_includes_all_cards(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("agent-a@nucleus", TrustTier.ACTIVE, tmp_path)
    _register("agent-b@nucleus", TrustTier.TRUSTED, tmp_path)
    result = _export(tmp_path)
    assert result["total"] == 2
    addresses = {c["address"] for c in result["snapshot"]}
    assert "agent-a@nucleus" in addresses
    assert "agent-b@nucleus" in addresses


def test_export_empty_registry_returns_zero(tmp_path):
    result = _export(tmp_path)
    assert result["total"] == 0
    assert result["snapshot"] == []


def test_export_cards_have_reputation_key(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("agent-c@nucleus", TrustTier.ACTIVE, tmp_path)
    result = _export(tmp_path)
    assert "reputation" in result["snapshot"][0]


def test_export_reflects_tier_after_promote(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, lookup_by_address, _get_registry_dir, _get_card_path
    _register("agent-p@nucleus", TrustTier.ACTIVE, tmp_path)
    registry_dir = _get_registry_dir(tmp_path)
    card_path = _get_card_path("agent-p@nucleus", registry_dir)
    card = json.loads(card_path.read_text())
    card["tier"] = int(TrustTier.VERIFIED)
    card_path.write_text(json.dumps(card, indent=2))
    result = _export(tmp_path)
    exported = {c["address"]: c for c in result["snapshot"]}
    assert exported["agent-p@nucleus"]["tier"] == int(TrustTier.VERIFIED)


def test_export_reflects_quarantine_flag(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, _get_registry_dir, _get_card_path
    _register("agent-q@nucleus", TrustTier.ACTIVE, tmp_path)
    registry_dir = _get_registry_dir(tmp_path)
    card_path = _get_card_path("agent-q@nucleus", registry_dir)
    card = json.loads(card_path.read_text())
    card["quarantined"] = True
    card_path.write_text(json.dumps(card, indent=2))
    result = _export(tmp_path)
    exported = {c["address"]: c for c in result["snapshot"]}
    assert exported["agent-q@nucleus"].get("quarantined") is True


def test_export_returns_valid_json_structure(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("agent-s@nucleus", TrustTier.TRUSTED, tmp_path)
    result = _export(tmp_path)
    assert isinstance(result, dict)
    assert "snapshot" in result
    assert "total" in result
    assert isinstance(result["snapshot"], list)
    assert result["total"] == len(result["snapshot"])
    card = result["snapshot"][0]
    for key in ("address", "tier", "reputation"):
        assert key in card, f"missing key: {key}"


def test_export_mixed_tiers_returns_all(tmp_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    tiers = [TrustTier.UNVERIFIED, TrustTier.ACTIVE, TrustTier.TRUSTED, TrustTier.VERIFIED]
    for i, tier in enumerate(tiers):
        _register(f"agent-m{i}@nucleus", tier, tmp_path)
    result = _export(tmp_path)
    assert result["total"] == 4
    exported_tiers = {c["tier"] for c in result["snapshot"]}
    assert exported_tiers == {int(t) for t in tiers}
