"""Tests for marketplace_trends action."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _write_admin_actions(brain_path: Path, actions: list):
    """Helper to write admin_actions.jsonl."""
    marketplace_dir = brain_path / "marketplace"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    admin_log = marketplace_dir / "admin_actions.jsonl"
    with open(admin_log, "w") as f:
        for action in actions:
            f.write(json.dumps(action) + "\n")


def _write_registry_cards(brain_path: Path, cards: list):
    """Helper to write registry cards."""
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        address = card.get("address")
        if address:
            slug = address.split("@")[0]
            card_path = registry_dir / f"{slug}.json"
            card_path.write_text(json.dumps(card, indent=2))


async def _call_marketplace_trends(brain_path: Path, days: int = 30, monkeypatch=None):
    """Helper to call marketplace_trends through the facade."""
    from mcp_server_nucleus.tools.sync import register

    # Patch get_brain_path in runtime module
    if monkeypatch:
        monkeypatch.setattr("mcp_server_nucleus.runtime.marketplace.get_brain_path", lambda: brain_path)

    # Create a minimal MCP mock
    class MockMCP:
        def tool(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    helpers = {
        "make_response": lambda data: data,
        "emit_event": lambda *args, **kwargs: None,
        "get_brain_path": lambda: brain_path,
    }

    tools = register(MockMCP(), helpers)
    sync_tool = tools[0][1]
    result = await sync_tool(action="marketplace_trends", params={"days": days, "brain_path": str(brain_path)})
    return json.loads(result)


async def test_marketplace_trends_empty_registry(tmp_path, monkeypatch):
    """Test marketplace_trends when registry is empty."""
    result = await _call_marketplace_trends(tmp_path, days=7, monkeypatch=monkeypatch)
    
    # Debug: print result if it's an error
    if "error" in result:
        print(f"Error: {result}")
    
    assert result["trend"] == "insufficient_data"
    assert result["days_analyzed"] == 7
    assert result["total_changes"] == 0
    assert len(result["snapshots"]) == 0


async def test_marketplace_trends_no_changes(tmp_path, monkeypatch):
    """Test marketplace_trends with registry but no tier changes."""
    now = datetime.now(timezone.utc)
    # Write some registry cards (registered before analysis window)
    cards = [
        {
            "address": "tool-a@nucleus",
            "display_name": "Tool A",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 0,
            "registered_at": (now - timedelta(days=20)).isoformat(),
        },
    ]
    _write_registry_cards(tmp_path, cards)

    result = await _call_marketplace_trends(tmp_path, days=7, monkeypatch=monkeypatch)
    
    assert result["trend"] == "stable"
    assert result["days_analyzed"] == 7
    assert result["total_changes"] == 0
    assert len(result["snapshots"]) == 8  # 7 days + today
    
    # Check distribution is consistent across snapshots
    first_dist = result["snapshots"][0]["distribution"]
    last_dist = result["snapshots"][-1]["distribution"]
    assert first_dist == last_dist
    # Single card at tier 0 (unverified) = 100% unverified
    assert first_dist["unverified"] == 100.0


async def test_marketplace_trends_hardening(tmp_path, monkeypatch):
    """Test marketplace_trends showing hardening trend (more high tiers)."""
    now = datetime.now(timezone.utc)
    
    # Write registry cards (current state: all at tier 2)
    cards = [
        {
            "address": "tool-a@nucleus",
            "display_name": "Tool A",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 2,
            "registered_at": (now - timedelta(days=20)).isoformat(),
        },
        {
            "address": "tool-b@nucleus",
            "display_name": "Tool B",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 2,
            "registered_at": (now - timedelta(days=15)).isoformat(),
        },
    ]
    _write_registry_cards(tmp_path, cards)

    # Write tier change history (both promoted from tier 0 to 2)
    actions = [
        {
            "timestamp": (now - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
            "action": "promote",
            "address": "tool-a@nucleus",
            "from_tier": 0,
            "to_tier": 2,
            "caller": "admin",
        },
        {
            "timestamp": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
            "action": "promote",
            "address": "tool-b@nucleus",
            "from_tier": 0,
            "to_tier": 2,
            "caller": "admin",
        },
    ]
    _write_admin_actions(tmp_path, actions)

    result = await _call_marketplace_trends(tmp_path, days=15, monkeypatch=monkeypatch)
    
    assert result["trend"] == "hardening"
    assert result["days_analyzed"] == 15
    assert result["total_changes"] == 2
    assert len(result["snapshots"]) == 16  # 15 days + today
    
    # Check first snapshot (before promotions) has more unverified
    first_dist = result["snapshots"][0]["distribution"]
    last_dist = result["snapshots"][-1]["distribution"]
    
    # Last snapshot should have 100% trusted (tier 2)
    assert last_dist["trusted"] == 100.0
    
    # First snapshot should have 100% unverified (before promotions)
    assert first_dist["unverified"] == 100.0


async def test_marketplace_trends_softening(tmp_path, monkeypatch):
    """Test marketplace_trends showing softening trend (fewer high tiers)."""
    now = datetime.now(timezone.utc)
    
    # Write registry cards (current state: all at tier 0)
    cards = [
        {
            "address": "tool-a@nucleus",
            "display_name": "Tool A",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 0,
            "registered_at": (now - timedelta(days=20)).isoformat(),
        },
        {
            "address": "tool-b@nucleus",
            "display_name": "Tool B",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 0,
            "registered_at": (now - timedelta(days=15)).isoformat(),
        },
    ]
    _write_registry_cards(tmp_path, cards)

    # Write tier change history (both were demoted from tier 2 to 0 via promote with lower tier)
    # Note: promote action can also demote if to_tier < from_tier
    actions = [
        {
            "timestamp": (now - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
            "action": "promote",
            "address": "tool-a@nucleus",
            "from_tier": 2,
            "to_tier": 0,
            "caller": "admin",
        },
        {
            "timestamp": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
            "action": "promote",
            "address": "tool-b@nucleus",
            "from_tier": 2,
            "to_tier": 0,
            "caller": "admin",
        },
    ]
    _write_admin_actions(tmp_path, actions)

    result = await _call_marketplace_trends(tmp_path, days=15, monkeypatch=monkeypatch)
    
    assert result["trend"] == "softening"
    assert result["days_analyzed"] == 15
    assert result["total_changes"] == 2
    
    # Check first snapshot (before demotions) has more trusted
    first_dist = result["snapshots"][0]["distribution"]
    last_dist = result["snapshots"][-1]["distribution"]
    
    # Last snapshot should have 100% unverified (tier 0)
    assert last_dist["unverified"] == 100.0
    
    # First snapshot should have 100% trusted (before demotions)
    assert first_dist["trusted"] == 100.0


async def test_marketplace_trends_custom_days(tmp_path, monkeypatch):
    """Test marketplace_trends with custom days parameter."""
    now = datetime.now(timezone.utc)
    cards = [
        {
            "address": "tool-a@nucleus",
            "display_name": "Tool A",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 0,
            "registered_at": (now - timedelta(days=20)).isoformat(),
        },
    ]
    _write_registry_cards(tmp_path, cards)

    result = await _call_marketplace_trends(tmp_path, days=5, monkeypatch=monkeypatch)
    
    assert result["days_analyzed"] == 5
    assert len(result["snapshots"]) == 6  # 5 days + today


async def test_marketplace_trends_missing_admin_log(tmp_path, monkeypatch):
    """Test marketplace_trends when admin_actions.jsonl doesn't exist."""
    now = datetime.now(timezone.utc)
    cards = [
        {
            "address": "tool-a@nucleus",
            "display_name": "Tool A",
            "accepts": ["test"],
            "emits": ["result"],
            "tier": 0,
            "registered_at": (now - timedelta(days=20)).isoformat(),
        },
    ]
    _write_registry_cards(tmp_path, cards)

    result = await _call_marketplace_trends(tmp_path, days=7, monkeypatch=monkeypatch)
    
    # Should still work, just with no changes
    assert result["trend"] == "stable"
    assert result["total_changes"] == 0
    assert len(result["snapshots"]) == 8
