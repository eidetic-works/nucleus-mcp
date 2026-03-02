"""
Tests for Phase 72: Autonomous Tool Discovery (ToolRecommender)
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

from mcp_server_nucleus.runtime.tool_recommender import (
    ToolRecommender, ToolRecommendation, TOOL_CATEGORIES, get_tool_recommender
)


SAMPLE_TOOLS = [
    {"name": "nucleus_tasks", "description": "Task + depth management facade"},
    {"name": "nucleus_engrams", "description": "Memory, health, version, morning brief facade"},
    {"name": "nucleus_governance", "description": "Governance, lock, audit, hypervisor facade"},
    {"name": "nucleus_sessions", "description": "Session management facade"},
    {"name": "nucleus_sync", "description": "Multi-agent sync facade"},
    {"name": "nucleus_orchestration", "description": "Core orchestration facade"},
    {"name": "nucleus_telemetry", "description": "Telemetry and metering facade"},
    {"name": "nucleus_slots", "description": "Slot management and sprints facade"},
    {"name": "nucleus_infra", "description": "Infrastructure and deployment facade"},
    {"name": "nucleus_agents", "description": "Agent management and code ops facade"},
    {"name": "nucleus_features", "description": "Feature map, mounter, proofs facade"},
    {"name": "nucleus_federation", "description": "Federation networking facade"},
]


class TestToolRecommendation:
    def test_to_dict(self):
        rec = ToolRecommendation(
            recommended_tools=["nucleus_tasks"],
            categories_matched=["task_management"],
            confidence=0.8,
            reasoning="Matched task keywords"
        )
        d = rec.to_dict()
        assert d["tool_count"] == 1
        assert d["confidence"] == 0.8
        assert "task_management" in d["categories_matched"]


class TestToolRecommender:
    @pytest.fixture
    def recommender(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            r = ToolRecommender()
            r._usage_path = Path(tmpdir) / "metrics" / "tool_usage.json"
            yield r
            os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def test_empty_request(self, recommender):
        rec = recommender.recommend("", SAMPLE_TOOLS)
        assert len(rec.recommended_tools) == 0

    def test_task_request(self, recommender):
        rec = recommender.recommend("add a new task for the sprint", SAMPLE_TOOLS)
        assert "nucleus_tasks" in rec.recommended_tools
        assert "task_management" in rec.categories_matched

    def test_memory_request(self, recommender):
        rec = recommender.recommend("remember this important decision", SAMPLE_TOOLS)
        assert "nucleus_engrams" in rec.recommended_tools
        assert "memory" in rec.categories_matched

    def test_budget_request(self, recommender):
        rec = recommender.recommend("how much have we spent today", SAMPLE_TOOLS)
        assert "nucleus_telemetry" in rec.recommended_tools
        assert "budget" in rec.categories_matched

    def test_deploy_request(self, recommender):
        rec = recommender.recommend("deploy the latest build to production", SAMPLE_TOOLS)
        assert "nucleus_infra" in rec.recommended_tools
        assert "deployment" in rec.categories_matched

    def test_health_request(self, recommender):
        rec = recommender.recommend("is the system alive and healthy", SAMPLE_TOOLS)
        assert "nucleus_engrams" in rec.recommended_tools
        assert "system_health" in rec.categories_matched

    def test_code_request(self, recommender):
        rec = recommender.recommend("search code for the bug in auth module", SAMPLE_TOOLS)
        assert "nucleus_agents" in rec.recommended_tools
        assert "code_operations" in rec.categories_matched

    def test_agent_request(self, recommender):
        rec = recommender.recommend("spawn a new agent for research", SAMPLE_TOOLS)
        assert "nucleus_agents" in rec.recommended_tools
        assert "agent_operations" in rec.categories_matched

    def test_session_request(self, recommender):
        rec = recommender.recommend("checkpoint my current progress", SAMPLE_TOOLS)
        assert "nucleus_sessions" in rec.recommended_tools
        assert "session" in rec.categories_matched

    def test_depth_request(self, recommender):
        rec = recommender.recommend("push depth level for this rabbit hole", SAMPLE_TOOLS)
        assert "nucleus_tasks" in rec.recommended_tools
        assert "depth_tracking" in rec.categories_matched

    def test_governance_request(self, recommender):
        rec = recommender.recommend("lock this resource for security", SAMPLE_TOOLS)
        assert "nucleus_governance" in rec.recommended_tools
        assert "governance" in rec.categories_matched

    def test_feature_request(self, recommender):
        rec = recommender.recommend("check feature roadmap priority", SAMPLE_TOOLS)
        assert "nucleus_features" in rec.recommended_tools
        assert "feature_management" in rec.categories_matched

    def test_essential_tools_always_included(self, recommender):
        rec = recommender.recommend("something random with no keywords", SAMPLE_TOOLS)
        assert "nucleus_tasks" in rec.recommended_tools
        assert "nucleus_engrams" in rec.recommended_tools
        assert "nucleus_governance" in rec.recommended_tools

    def test_multi_category_match(self, recommender):
        rec = recommender.recommend("deploy and check health status", SAMPLE_TOOLS)
        assert "deployment" in rec.categories_matched
        assert "system_health" in rec.categories_matched
        assert rec.confidence > 0.6

    def test_filter_tools(self, recommender):
        filtered = recommender.filter_tools("add task items", SAMPLE_TOOLS)
        names = [t["name"] for t in filtered]
        assert "nucleus_tasks" in names
        # Should be less than all tools
        assert len(filtered) < len(SAMPLE_TOOLS)

    def test_record_usage(self, recommender):
        recommender.record_usage("nucleus_tasks")
        recommender.record_usage("nucleus_tasks")
        recommender.record_usage("nucleus_tasks")
        assert recommender._usage_counts["nucleus_tasks"] == 3

    def test_usage_affects_recommendation(self, recommender):
        # Record heavy usage of a tool
        for _ in range(20):
            recommender.record_usage("nucleus_governance")
        
        # Even for unrelated request, frequently used tool should appear
        rec = recommender.recommend("hello world", SAMPLE_TOOLS)
        assert "nucleus_governance" in rec.recommended_tools

    def test_save_and_load_usage(self, recommender):
        recommender.record_usage("nucleus_tasks")
        recommender.record_usage("nucleus_tasks")
        recommender._save_usage()
        
        new_recommender = ToolRecommender()
        new_recommender._usage_path = recommender._usage_path
        new_recommender._load_usage()
        assert new_recommender._usage_counts.get("nucleus_tasks") == 2

    def test_get_category_for_tool(self, recommender):
        cat = recommender.get_category_for_tool("nucleus_tasks")
        assert cat == "task_management"
        
        cat = recommender.get_category_for_tool("unknown_tool")
        assert cat is None

    def test_get_all_categories(self, recommender):
        categories = recommender.get_all_categories()
        assert "task_management" in categories
        assert "memory" in categories
        assert categories["task_management"]["tool_count"] > 0

    def test_get_usage_stats(self, recommender):
        recommender.record_usage("brain_add_task")
        stats = recommender.get_usage_stats()
        assert stats["total_tool_calls"] >= 1
        assert stats["total_categories"] == len(TOOL_CATEGORIES)

    def test_max_tools_cap(self, recommender):
        rec = recommender.recommend("deploy check health task agent budget", SAMPLE_TOOLS, max_tools=5)
        assert len(rec.recommended_tools) <= 5

    def test_singleton(self):
        r1 = get_tool_recommender()
        r2 = get_tool_recommender()
        assert r1 is r2


class TestToolCategories:
    def test_all_categories_have_required_fields(self):
        for name, cat in TOOL_CATEGORIES.items():
            assert "description" in cat, f"Category {name} missing description"
            assert "keywords" in cat, f"Category {name} missing keywords"
            assert "tools" in cat, f"Category {name} missing tools"
            assert len(cat["keywords"]) > 0, f"Category {name} has no keywords"
            assert len(cat["tools"]) > 0, f"Category {name} has no tools"

    def test_all_facade_tools_covered(self):
        all_tools = set()
        for cat in TOOL_CATEGORIES.values():
            all_tools.update(cat["tools"])
        # With facades, we expect all 12 to be covered across categories
        assert len(all_tools) == 12
