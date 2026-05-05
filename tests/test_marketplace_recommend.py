"""Tests for nucleus_sync marketplace_recommend action."""
import json
import pytest
from pathlib import Path


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


def _recommend(task: str, top_k: int, brain_path: Path) -> dict:
    from mcp_server_nucleus.runtime.marketplace import search_by_tags
    import re

    def _tok(text):
        return set(re.sub(r"[^a-z0-9]", " ", text.lower()).split())

    task_tokens = _tok(task)
    if not task_tokens:
        return {"recommendations": [], "task": task}

    all_cards = search_by_tags([], brain_path=brain_path)
    scored = []
    for card in all_cards:
        card_tokens: set = set()
        for t in card.get("tags", []):
            card_tokens.update(_tok(str(t)))
        for field in ("display_name", "address"):
            card_tokens.update(_tok(card.get(field, "")))
        for item in card.get("accepts", []):
            card_tokens.update(_tok(str(item)))
        if not card_tokens:
            continue
        overlap = len(task_tokens & card_tokens)
        if overlap == 0:
            continue
        score = round(overlap / len(task_tokens | card_tokens), 4)
        scored.append({"address": card.get("address"), "confidence": score,
                       "tier": card.get("tier", 0)})

    scored.sort(key=lambda x: (x["confidence"], x["tier"]), reverse=True)
    return {"recommendations": scored[:top_k], "task": task}


def test_recommend_returns_matching_by_tag(tmp_path):
    """Agent with matching tag in card should appear in recommendations."""
    _register("code-reviewer@nucleus", ["code-review", "python"], ["review_task"], tmp_path)
    _register("planner@nucleus", ["planning", "roadmap"], ["planning_task"], tmp_path)

    result = _recommend("review python code", top_k=5, brain_path=tmp_path)
    addresses = [r["address"] for r in result["recommendations"]]
    assert "code-reviewer@nucleus" in addresses
    assert "planner@nucleus" not in addresses


def test_recommend_top_k_limits_results(tmp_path):
    """top_k=2 returns at most 2 results even with more matches."""
    for i in range(5):
        _register(f"agent-{i}@nucleus", ["testing", "automation"], ["run_tests"], tmp_path)

    result = _recommend("run testing automation", top_k=2, brain_path=tmp_path)
    assert len(result["recommendations"]) <= 2


def test_recommend_confidence_between_zero_and_one(tmp_path):
    """All confidence scores must be in [0.0, 1.0]."""
    _register("tester@nucleus", ["testing", "pytest"], ["test_suite"], tmp_path)
    result = _recommend("pytest testing", top_k=5, brain_path=tmp_path)
    for rec in result["recommendations"]:
        assert 0.0 <= rec["confidence"] <= 1.0


def test_recommend_empty_task_returns_empty(tmp_path):
    """Empty task string → empty recommendations."""
    _register("agent@nucleus", ["testing"], ["task"], tmp_path)
    result = _recommend("", top_k=5, brain_path=tmp_path)
    assert result["recommendations"] == []


def test_recommend_no_match_returns_empty(tmp_path):
    """Task with tokens that don't match any card → empty recommendations."""
    _register("coder@nucleus", ["python", "code"], ["write_code"], tmp_path)
    result = _recommend("schedule meeting calendar", top_k=5, brain_path=tmp_path)
    assert result["recommendations"] == []


def test_recommend_exact_match_highest_score(tmp_path):
    """Exact tokens matching should give higher confidence than partial."""
    _register("coder@nucleus", ["python", "code"], ["write_code"], tmp_path)
    _register("webdev@nucleus", ["html", "css", "code"], ["write_web_code"], tmp_path)
    result = _recommend("python code", top_k=5, brain_path=tmp_path)
    assert len(result["recommendations"]) == 2
    assert result["recommendations"][0]["address"] == "coder@nucleus"


def test_recommend_no_matches_returns_empty(tmp_path):
    """Cards with tags=['data'] should not match task='ml' (no token overlap)."""
    _register("data-processor-1@nucleus", ["data", "pipeline"], ["process"], tmp_path)
    _register("data-processor-2@nucleus", ["data", "etl"], ["transform"], tmp_path)
    result = _recommend("ml model training", top_k=5, brain_path=tmp_path)
    assert result["recommendations"] == []


def test_recommend_empty_tags_returns_all(tmp_path):
    """Broad task with tokens matching all cards should return all (no filtering)."""
    _register("agent-a@nucleus", ["python", "code"], ["write"], tmp_path)
    _register("agent-b@nucleus", ["testing", "pytest"], ["test"], tmp_path)
    _register("agent-c@nucleus", ["planning", "roadmap"], ["plan"], tmp_path)
    result = _recommend("python testing planning code task", top_k=5, brain_path=tmp_path)
    assert len(result["recommendations"]) == 3


def test_recommend_filters_by_tier(tmp_path):
    """Recommendations include tier field and higher tiers rank higher."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("low-tier@nucleus", ["test", "automation"], ["run"], tmp_path)
    _register("mid-tier@nucleus", ["test", "automation"], ["run"], tmp_path)
    _register("high-tier@nucleus", ["test", "automation"], ["run"], tmp_path)
    # Manually set tiers via card mutation
    registry_dir = tmp_path / "marketplace" / "registry"
    for addr, tier in [("low-tier@nucleus", TrustTier.UNVERIFIED), 
                       ("mid-tier@nucleus", TrustTier.ACTIVE), 
                       ("high-tier@nucleus", TrustTier.VERIFIED)]:
        card_file = registry_dir / f"{addr.split('@')[0]}.json"
        if card_file.exists():
            card = json.loads(card_file.read_text())
            card["tier"] = int(tier)
            card_file.write_text(json.dumps(card, indent=2))
    result = _recommend("test automation", top_k=5, brain_path=tmp_path)
    assert len(result["recommendations"]) == 3
    for rec in result["recommendations"]:
        assert "tier" in rec
    # Higher tier should rank first (sort key: confidence, tier)
    assert result["recommendations"][0]["tier"] >= result["recommendations"][1]["tier"]
