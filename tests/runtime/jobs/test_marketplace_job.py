"""Tests for the marketplace tier promotion loop."""

import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.marketplace import ReputationSignals, TrustTier, register_tool
from mcp_server_nucleus.runtime.jobs.marketplace_job import run_tier_promotion_loop

@pytest.fixture
def brain(tmp_path: Path) -> Path:
    """Create a minimal .brain structure."""
    return tmp_path / ".brain"

def test_tier_promotion_loop(brain: Path) -> None:
    # 1. Register a tool
    card_data = {
        "address": "promotable@nucleus",
        "display_name": "Test Tool",
        "accepts": ["in"],
        "emits": ["out"]
    }
    register_tool(card_data, brain_path=brain)
    
    # Verify initial state
    registry_dir = brain / "marketplace" / "registry"
    card_file = registry_dir / "promotable.json"
    card = json.loads(card_file.read_text())
    assert card["tier"] == TrustTier.UNVERIFIED
    
    # 2. Add reputation signals to make it ACTIVE (>= 5 conns, >= 90% success)
    for i in range(5):
        ReputationSignals.record_interaction("promotable@nucleus", f"user_{i}", 100, True, brain_path=brain)
        
    # 3. Run job
    result = run_tier_promotion_loop(brain_path=brain)
    assert result["ok"] is True
    assert result["updated"] == 1
    assert result["total"] == 1
    
    # 4. Verify new state
    card = json.loads(card_file.read_text())
    assert card["tier"] == TrustTier.ACTIVE
    assert card["tier_badge"] == "Active"
    assert card["connection_count"] == 5
    assert card["success_rate"] == 1.0
    
    # 5. Run job again (no changes expected)
    result = run_tier_promotion_loop(brain_path=brain)
    assert result["updated"] == 0
