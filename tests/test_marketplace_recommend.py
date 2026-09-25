"""Tests for nucleus_sync marketplace_recommend action.

These tests exercise the REAL ``_marketplace_recommend`` closure produced by
``mcp_server_nucleus.tools._marketplace_core.register`` — not a local
reimplementation. A broken production function must fail these tests.
"""
import json
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.tools import _marketplace_core as mp


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    bp = tmp_path / ".brain"
    bp.mkdir()
    (bp / "marketplace").mkdir()
    (bp / "marketplace" / "registry").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


@pytest.fixture
def handlers(brain_path):
    """Real marketplace handlers bound to an isolated brain_path."""
    emit_event = mock.MagicMock()
    get_brain_path = mock.MagicMock(return_value=brain_path)
    return mp.register(emit_event, get_brain_path)


def _register(address: str, tags: list, accepts: list, brain_path: Path):
    from mcp_server_nucleus.runtime.marketplace import register_tool, TrustTier
    register_tool({
        "address": address,
        "display_name": address.split("@")[0],
        "accepts": accepts,
        "emits": ["result"],
        "tags": tags,
        "tier": TrustTier.ACTIVE,
    }, brain_path=brain_path)


def _recommend(handlers, task: str, top_k: int) -> dict:
    """Call the real handler and parse its JSON-string result."""
    return json.loads(handlers["marketplace_recommend"](task, top_k))


def test_recommend_returns_matching_by_tag(handlers, brain_path):
    """Agent with matching tag in card should appear in recommendations."""
    _register("code-reviewer@nucleus", ["code-review", "python"], ["review_task"], brain_path)
    _register("planner@nucleus", ["planning", "roadmap"], ["planning_task"], brain_path)

    result = _recommend(handlers, "review python code", top_k=5)
    addresses = [r["address"] for r in result["recommendations"]]
    assert "code-reviewer@nucleus" in addresses
    assert "planner@nucleus" not in addresses


def test_recommend_top_k_limits_results(handlers, brain_path):
    """top_k=2 returns at most 2 results even with more matches."""
    for i in range(5):
        _register(f"agent-{i}@nucleus", ["testing", "automation"], ["run_tests"], brain_path)

    result = _recommend(handlers, "run testing automation", top_k=2)
    assert len(result["recommendations"]) <= 2


def test_recommend_confidence_between_zero_and_one(handlers, brain_path):
    """All confidence scores must be in [0.0, 1.0]."""
    _register("tester@nucleus", ["testing", "pytest"], ["test_suite"], brain_path)
    result = _recommend(handlers, "pytest testing", top_k=5)
    for rec in result["recommendations"]:
        assert 0.0 <= rec["confidence"] <= 1.0


def test_recommend_empty_task_returns_empty(handlers, brain_path):
    """Empty task string → empty recommendations."""
    _register("agent@nucleus", ["testing"], ["task"], brain_path)
    result = _recommend(handlers, "", top_k=5)
    assert result["recommendations"] == []


def test_recommend_no_match_returns_empty(handlers, brain_path):
    """Task with tokens that don't match any card → empty recommendations."""
    _register("coder@nucleus", ["python", "code"], ["write_code"], brain_path)
    result = _recommend(handlers, "schedule meeting calendar", top_k=5)
    assert result["recommendations"] == []


def test_recommend_exact_match_highest_score(handlers, brain_path):
    """Exact tokens matching should give higher confidence than partial."""
    _register("coder@nucleus", ["python", "code"], ["write_code"], brain_path)
    _register("webdev@nucleus", ["html", "css", "code"], ["write_web_code"], brain_path)
    result = _recommend(handlers, "python code", top_k=5)
    assert len(result["recommendations"]) == 2
    assert result["recommendations"][0]["address"] == "coder@nucleus"


def test_recommend_no_matches_returns_empty(handlers, brain_path):
    """Cards with tags=['data'] should not match task='ml' (no token overlap)."""
    _register("data-processor-1@nucleus", ["data", "pipeline"], ["process"], brain_path)
    _register("data-processor-2@nucleus", ["data", "etl"], ["transform"], brain_path)
    result = _recommend(handlers, "ml model training", top_k=5)
    assert result["recommendations"] == []


def test_recommend_empty_tags_returns_all(handlers, brain_path):
    """Broad task with tokens matching all cards should return all (no filtering)."""
    _register("agent-a@nucleus", ["python", "code"], ["write"], brain_path)
    _register("agent-b@nucleus", ["testing", "pytest"], ["test"], brain_path)
    _register("agent-c@nucleus", ["planning", "roadmap"], ["plan"], brain_path)
    result = _recommend(handlers, "python testing planning code task", top_k=5)
    assert len(result["recommendations"]) == 3


def test_recommend_filters_by_tier(handlers, brain_path):
    """Recommendations include tier field and higher tiers rank higher."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("low-tier@nucleus", ["test", "automation"], ["run"], brain_path)
    _register("mid-tier@nucleus", ["test", "automation"], ["run"], brain_path)
    _register("high-tier@nucleus", ["test", "automation"], ["run"], brain_path)
    # Manually set tiers via card mutation
    registry_dir = brain_path / "marketplace" / "registry"
    for addr, tier in [("low-tier@nucleus", TrustTier.UNVERIFIED),
                       ("mid-tier@nucleus", TrustTier.ACTIVE),
                       ("high-tier@nucleus", TrustTier.VERIFIED)]:
        card_file = registry_dir / f"{addr.split('@')[0]}.json"
        if card_file.exists():
            card = json.loads(card_file.read_text())
            card["tier"] = int(tier)
            card_file.write_text(json.dumps(card, indent=2))
    result = _recommend(handlers, "test automation", top_k=5)
    assert len(result["recommendations"]) == 3
    for rec in result["recommendations"]:
        assert "tier" in rec
    # Higher tier should rank first (sort key: confidence, tier)
    assert result["recommendations"][0]["tier"] >= result["recommendations"][1]["tier"]
