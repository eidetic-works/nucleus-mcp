"""Atom 3: CapabilityRegistry.mark_stale() tests."""
import json
import pytest
from datetime import datetime, timezone, timedelta

from mcp_server_nucleus.runtime.marketplace import (
    CapabilityRegistry,
    register_tool,
)


@pytest.fixture
def registry(tmp_path, monkeypatch):
    """Isolated .brain directory with a fresh registry."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


def _make_card(brain, address: str, last_seen_at: str) -> None:
    """Helper: write a bare capability card directly to registry."""
    reg_dir = brain / "marketplace" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    slug = address.split("@")[0]
    card = {
        "address": address,
        "display_name": slug,
        "accepts": ["*"],
        "emits": ["*"],
        "registered_at": last_seen_at,
        "last_seen_at": last_seen_at,
        "tags": [],
    }
    (reg_dir / f"{slug}.json").write_text(json.dumps(card))


def test_recent_address_not_marked(registry):
    """An address active today must NOT be marked inactive."""
    now = datetime.now(timezone.utc)
    recent_ts = now.isoformat().replace("+00:00", "Z")
    _make_card(registry, "fresh-tool@nucleus", recent_ts)

    result = CapabilityRegistry.mark_stale(threshold_days=90, brain_path=registry, now=now)

    assert "fresh-tool@nucleus" not in result["marked"]
    assert result["total"] == 1

    # Card must NOT have inactive flag
    card_path = registry / "marketplace" / "registry" / "fresh-tool.json"
    card = json.loads(card_path.read_text())
    assert card.get("inactive") is not True


def test_100_day_stale_marked(registry):
    """An address last seen 100 days ago must be marked inactive."""
    now = datetime.now(timezone.utc)
    stale_ts = (now - timedelta(days=100)).isoformat().replace("+00:00", "Z")
    _make_card(registry, "old-tool@nucleus", stale_ts)

    result = CapabilityRegistry.mark_stale(threshold_days=90, brain_path=registry, now=now)

    assert "old-tool@nucleus" in result["marked"]
    assert result["total"] == 1

    # Card must carry inactive flag
    card_path = registry / "marketplace" / "registry" / "old-tool.json"
    card = json.loads(card_path.read_text())
    assert card.get("inactive") is True
    assert "inactive_since" in card
    assert "inactive_reason" in card


def test_mark_stale_idempotent(registry):
    """Calling mark_stale twice must not double-count or corrupt the card."""
    now = datetime.now(timezone.utc)
    stale_ts = (now - timedelta(days=100)).isoformat().replace("+00:00", "Z")
    _make_card(registry, "idempotent-tool@nucleus", stale_ts)

    result1 = CapabilityRegistry.mark_stale(threshold_days=90, brain_path=registry, now=now)
    result2 = CapabilityRegistry.mark_stale(threshold_days=90, brain_path=registry, now=now)

    assert "idempotent-tool@nucleus" in result1["marked"]
    # Second run: the entry is already stale, the file will be re-written
    # but the mark list should still contain it (not a bug, just idempotent)
    card_path = registry / "marketplace" / "registry" / "idempotent-tool.json"
    card = json.loads(card_path.read_text())
    assert card["inactive"] is True
