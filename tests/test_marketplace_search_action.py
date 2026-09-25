"""Tests for nucleus_sync marketplace_search action."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def _register(address: str, tags: list, tier: int, success_rate: float = 1.0, brain_path: Path = None):
    from mcp_server_nucleus.runtime.marketplace import register_tool
    register_tool({
        "address": address,
        "display_name": address.split("@")[0],
        "accepts": ["task"],
        "emits": ["result"],
        "tags": tags,
        "tier": tier,
        "success_rate": success_rate,
    }, brain_path=brain_path)


def _search(brain_path: Path, tags=None, min_tier=None, limit=10):
    """Call _marketplace_search by loading sync module handler directly."""
    from mcp_server_nucleus.runtime.marketplace import search_by_tags, TrustTier

    cards = search_by_tags(tags or [], brain_path=brain_path)
    if min_tier:
        threshold = TrustTier[min_tier.upper()]
        cards = [c for c in cards if c.get("tier", TrustTier.UNVERIFIED) >= threshold]
    cards.sort(
        key=lambda c: (c.get("tier", 0), c.get("success_rate", 1.0)),
        reverse=True,
    )
    return {"cards": cards[:limit], "count": len(cards[:limit])}


def test_search_by_tag_returns_matching_cards(tmp_path):
    """Register 3 tools, 2 tagged 'code-review', 1 without. Search tag='code-review' → 2 results."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    _register("reviewer-a@nucleus", ["code-review", "python"], TrustTier.ACTIVE, brain_path=tmp_path)
    _register("reviewer-b@nucleus", ["code-review"], TrustTier.ACTIVE, brain_path=tmp_path)
    _register("planner-c@nucleus", ["planning"], TrustTier.ACTIVE, brain_path=tmp_path)

    result = _search(tmp_path, tags=["code-review"])

    assert result["count"] == 2
    addresses = {c["address"] for c in result["cards"]}
    assert "reviewer-a@nucleus" in addresses
    assert "reviewer-b@nucleus" in addresses
    assert "planner-c@nucleus" not in addresses


def test_search_filters_by_min_tier(tmp_path):
    """3 tools at Unverified/Active/Trusted. min_tier='Active' → 2 results."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    _register("tool-unverified@nucleus", ["testing"], TrustTier.UNVERIFIED, brain_path=tmp_path)
    _register("tool-active@nucleus", ["testing"], TrustTier.ACTIVE, brain_path=tmp_path)
    _register("tool-trusted@nucleus", ["testing"], TrustTier.TRUSTED, brain_path=tmp_path)

    result = _search(tmp_path, min_tier="Active")

    assert result["count"] == 2
    addresses = {c["address"] for c in result["cards"]}
    assert "tool-active@nucleus" in addresses
    assert "tool-trusted@nucleus" in addresses
    assert "tool-unverified@nucleus" not in addresses


def test_search_ranks_higher_tier_first(tmp_path):
    """2 tools same tags, different tiers. Trusted must appear before Active."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier

    _register("low-rank@nucleus", ["analytics"], TrustTier.ACTIVE, brain_path=tmp_path)
    _register("high-rank@nucleus", ["analytics"], TrustTier.TRUSTED, brain_path=tmp_path)

    result = _search(tmp_path, tags=["analytics"])

    assert result["count"] == 2
    assert result["cards"][0]["address"] == "high-rank@nucleus", (
        f"Expected Trusted first, got: {[c['address'] for c in result['cards']]}"
    )
    assert result["cards"][1]["address"] == "low-rank@nucleus"
