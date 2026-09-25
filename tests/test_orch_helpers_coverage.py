"""Comprehensive coverage tests for runtime/orch_helpers.py."""
import json
import time
from pathlib import Path

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
    b = tmp_path / ".brain"
    for sub in ["ledger", "slots", "protocols", "config", "artifacts"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


@pytest.fixture
def tier_defs():
    """Standard tier definitions for testing."""
    return {
        "tiers": {
            "heavy": {"level": 1, "models": ["gpt_4", "claude_opus"]},
            "standard": {"level": 2, "models": ["gpt_3.5_turbo", "claude_sonnet"]},
            "light": {"level": 3, "models": ["gpt_3.5_haiku", "llama_7b"]},
        },
        "tier_priority_mapping": {
            "1": "heavy",
            "2": "standard",
            "3": "standard",
        },
        "model_costs": {
            "gpt_4": 0.03,
            "gpt_3.5_turbo": 0.002,
            "claude_sonnet": 0.015,
            "llama_7b": 0.001,
        }
    }


@pytest.fixture
def tier_defs_file(brain, tier_defs):
    """Write tier definitions to disk."""
    (brain / "protocols" / "tiers.json").write_text(json.dumps(tier_defs))
    return tier_defs


def _use_json_backend(brain):
    """Configure JSON storage backend (avoids SQLite column validation issues)."""
    (brain / "config").mkdir(exist_ok=True)
    (brain / "config" / "nucleus.yaml").write_text("storage:\n  backend: json\n")


# ─── _get_slot_registry ────────────────────────────────────────────────────

class TestGetSlotRegistry:
    def test_no_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_slot_registry
        result = _get_slot_registry()
        assert result == {"slots": {}, "aliases": {}}

    def test_with_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_slot_registry
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {"a1": "s1"}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        result = _get_slot_registry()
        assert "s1" in result["slots"]
        assert result["aliases"]["a1"] == "s1"


# ─── _save_slot_registry ───────────────────────────────────────────────────

class TestSaveSlotRegistry:
    def test_save_and_load(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _save_slot_registry, _get_slot_registry
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        _save_slot_registry(reg)
        loaded = _get_slot_registry()
        assert "s1" in loaded["slots"]
        assert "last_updated" in loaded

    def test_save_creates_dir(self, tmp_path, monkeypatch):
        from mcp_server_nucleus.runtime.orch_helpers import _save_slot_registry
        b = tmp_path / ".brain3"
        b.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
        # slots dir doesn't exist yet
        reg = {"slots": {}}
        _save_slot_registry(reg)
        assert (b / "slots" / "registry.json").exists()


# ─── _get_tier_definitions ─────────────────────────────────────────────────

class TestGetTierDefinitions:
    def test_no_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_definitions
        result = _get_tier_definitions()
        assert result == {"tiers": {}, "tier_priority_mapping": {}}

    def test_with_file(self, brain, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_definitions
        (brain / "protocols" / "tiers.json").write_text(json.dumps(tier_defs))
        result = _get_tier_definitions()
        assert "heavy" in result["tiers"]


# ─── _resolve_slot_id ──────────────────────────────────────────────────────

class TestResolveSlotId:
    def test_direct_match(self):
        from mcp_server_nucleus.runtime.orch_helpers import _resolve_slot_id
        registry = {"slots": {"s1": {}}, "aliases": {"a1": "s1"}}
        assert _resolve_slot_id("s1", registry) == "s1"

    def test_alias_match(self):
        from mcp_server_nucleus.runtime.orch_helpers import _resolve_slot_id
        registry = {"slots": {"s1": {}}, "aliases": {"a1": "s1"}}
        assert _resolve_slot_id("a1", registry) == "s1"

    def test_no_match_returns_original(self):
        from mcp_server_nucleus.runtime.orch_helpers import _resolve_slot_id
        registry = {"slots": {}, "aliases": {}}
        assert _resolve_slot_id("unknown", registry) == "unknown"

    def test_empty_registry(self):
        from mcp_server_nucleus.runtime.orch_helpers import _resolve_slot_id
        assert _resolve_slot_id("x", {}) == "x"


# ─── _get_tier_for_model ───────────────────────────────────────────────────

class TestGetTierForModel:
    def test_exact_match(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_for_model
        assert _get_tier_for_model("gpt-4", tier_defs) == "heavy"
        assert _get_tier_for_model("claude-sonnet", tier_defs) == "standard"

    def test_case_insensitive(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_for_model
        assert _get_tier_for_model("GPT-4", tier_defs) == "heavy"

    def test_fuzzy_match(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_for_model
        # "gpt-4-turbo" contains "gpt-4"
        assert _get_tier_for_model("gpt-4-turbo", tier_defs) == "heavy"

    def test_no_match_default(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_for_model
        assert _get_tier_for_model("unknown-model", tier_defs) == "standard"

    def test_empty_tier_defs(self):
        from mcp_server_nucleus.runtime.orch_helpers import _get_tier_for_model
        assert _get_tier_for_model("gpt-4", {"tiers": {}}) == "standard"


# ─── _infer_task_tier ──────────────────────────────────────────────────────

class TestInferTaskTier:
    def test_explicit_required_tier(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {"required_tier": "heavy", "priority": 1}
        assert _infer_task_tier(task, tier_defs) == "heavy"

    def test_human_environment(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {"environment": "human"}
        assert _infer_task_tier(task, tier_defs) == "human"

    def test_from_priority_mapping(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {"priority": 1}
        assert _infer_task_tier(task, tier_defs) == "heavy"

    def test_priority_not_in_mapping(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {"priority": 99}
        assert _infer_task_tier(task, tier_defs) == "standard"

    def test_no_priority(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {}
        assert _infer_task_tier(task, tier_defs) == "standard"

    def test_empty_tier_defs(self):
        from mcp_server_nucleus.runtime.orch_helpers import _infer_task_tier
        task = {"priority": 1}
        assert _infer_task_tier(task, {"tier_priority_mapping": {}}) == "standard"


# ─── _can_slot_run_task ────────────────────────────────────────────────────

class TestCanSlotRunTask:
    def test_human_task_always_false(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        assert _can_slot_run_task("heavy", "human", tier_defs) is False

    def test_slot_can_run(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        # heavy level=1, standard level=2; 1 <= 2 -> True
        assert _can_slot_run_task("heavy", "standard", tier_defs) is True

    def test_slot_cannot_run(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        # light level=3, heavy level=1; 3 <= 1 -> False
        assert _can_slot_run_task("light", "heavy", tier_defs) is False

    def test_equal_levels(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        assert _can_slot_run_task("standard", "standard", tier_defs) is True

    def test_unknown_tiers(self):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        # Unknown slot tier -> level 99, unknown task tier -> level 1
        # 99 <= 1 -> False
        assert _can_slot_run_task("unknown", "unknown", {"tiers": {}}) is False

    def test_unknown_task_tier(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _can_slot_run_task
        # heavy level=1, unknown task -> level 1 (default); 1 <= 1 -> True
        assert _can_slot_run_task("heavy", "unknown_tier", tier_defs) is True


# ─── _compute_slot_blockers ────────────────────────────────────────────────

class TestComputeSlotBlockers:
    def test_no_blockers(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_slot_blockers
        task = {"blocked_by": []}
        tasks = []
        result = _compute_slot_blockers(task, tasks, {})
        assert result == []

    def test_blocker_done(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_slot_blockers
        task = {"blocked_by": ["t1"]}
        tasks = [{"id": "t1", "status": "DONE"}]
        result = _compute_slot_blockers(task, tasks, {})
        assert result == []

    def test_blocker_not_done_claimed(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_slot_blockers
        task = {"blocked_by": ["t1"]}
        tasks = [{"id": "t1", "status": "IN_PROGRESS", "claimed_by": "slot_a"}]
        result = _compute_slot_blockers(task, tasks, {})
        assert "slot_a" in result

    def test_blocker_not_found(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_slot_blockers
        task = {"blocked_by": ["t_missing"]}
        tasks = []
        result = _compute_slot_blockers(task, tasks, {})
        assert result == []

    def test_multiple_blockers(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_slot_blockers
        task = {"blocked_by": ["t1", "t2"]}
        tasks = [
            {"id": "t1", "status": "IN_PROGRESS", "claimed_by": "slot_a"},
            {"id": "t2", "status": "IN_PROGRESS", "claimed_by": "slot_b"},
        ]
        result = _compute_slot_blockers(task, tasks, {})
        assert set(result) == {"slot_a", "slot_b"}


# ─── _get_fence_counter ────────────────────────────────────────────────────

class TestGetFenceCounter:
    def test_no_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_fence_counter
        result = _get_fence_counter()
        assert result["value"] == 100
        assert result["last_issued"] is None
        assert result["history"] == []

    def test_with_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_fence_counter
        counter = {"value": 200, "last_issued": "2026-01-01", "history": [199]}
        (brain / "ledger" / "fence_counter.json").write_text(json.dumps(counter))
        result = _get_fence_counter()
        assert result["value"] == 200


# ─── _increment_fence_token ────────────────────────────────────────────────

class TestIncrementFenceToken:
    def test_increment_from_default(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token
        token = _increment_fence_token()
        assert token == 101

    def test_increment_twice(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token
        t1 = _increment_fence_token()
        t2 = _increment_fence_token()
        assert t2 == t1 + 1

    def test_persists_to_disk(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token, _get_fence_counter
        _increment_fence_token()
        counter = _get_fence_counter()
        assert counter["value"] == 101
        assert counter["last_issued"] is not None

    def test_creates_dir(self, tmp_path, monkeypatch):
        from mcp_server_nucleus.runtime.orch_helpers import _increment_fence_token
        b = tmp_path / ".brain_new"
        b.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
        token = _increment_fence_token()
        assert token == 101
        assert (b / "ledger" / "fence_counter.json").exists()


# ─── _get_model_cost ───────────────────────────────────────────────────────

class TestGetModelCost:
    def test_direct_lookup(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _get_model_cost
        assert _get_model_cost("gpt-4") == 0.03

    def test_fuzzy_match(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _get_model_cost
        # "gpt-4-turbo" -> normalized "gpt_4_turbo" contains "gpt_4"
        assert _get_model_cost("gpt-4-turbo") == 0.03

    def test_no_match_default(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _get_model_cost
        assert _get_model_cost("unknown-model") == 0.010

    def test_no_tier_file(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _get_model_cost
        assert _get_model_cost("gpt-4") == 0.010


# ─── _compute_dependency_graph ─────────────────────────────────────────────

class TestComputeDependencyGraph:
    def test_empty_tasks(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        result = _compute_dependency_graph([], {})
        assert result["task_to_task"] == {}
        assert result["circular_deps"] == []
        assert result["slot_to_slot"] == {}

    def test_simple_chain(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": []},
            {"id": "t2", "blocked_by": ["t1"]},
        ]
        result = _compute_dependency_graph(tasks, {})
        assert result["task_to_task"]["t2"] == ["t1"]
        assert result["blocking_chains"]["t2"] == ["t1"]
        assert result["circular_deps"] == []

    def test_circular_dependency(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": ["t2"]},
            {"id": "t2", "blocked_by": ["t1"]},
        ]
        result = _compute_dependency_graph(tasks, {})
        assert len(result["circular_deps"]) > 0

    def test_slot_blocking(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": [], "claimed_by": "slot_a", "status": "IN_PROGRESS"},
            {"id": "t2", "blocked_by": ["t1"], "claimed_by": "slot_b"},
        ]
        result = _compute_dependency_graph(tasks, {})
        assert "slot_b" in result["slot_to_slot"]
        assert "slot_a" in result["slot_to_slot"]["slot_b"]

    def test_blocking_chains_transitive(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": []},
            {"id": "t2", "blocked_by": ["t1"]},
            {"id": "t3", "blocked_by": ["t2"]},
        ]
        result = _compute_dependency_graph(tasks, {})
        assert "t1" in result["blocking_chains"]["t3"]
        assert "t2" in result["blocking_chains"]["t3"]

    def test_blocking_chains_circular_safe(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": ["t2"]},
            {"id": "t2", "blocked_by": ["t1"]},
        ]
        result = _compute_dependency_graph(tasks, {})
        # Should not infinite loop
        assert "t1" in result["blocking_chains"]

    def test_computed_at_timestamp(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        result = _compute_dependency_graph([], {})
        assert "computed_at" in result

    def test_blocker_done_not_blocking(self):
        from mcp_server_nucleus.runtime.orch_helpers import _compute_dependency_graph
        tasks = [
            {"id": "t1", "blocked_by": [], "claimed_by": "slot_a", "status": "DONE"},
            {"id": "t2", "blocked_by": ["t1"], "claimed_by": "slot_b"},
        ]
        result = _compute_dependency_graph(tasks, {})
        # t1 is DONE so no slot blocking
        assert "t2" not in result["task_to_slot"]


# ─── _score_slot_for_task ──────────────────────────────────────────────────

class TestScoreSlotForTask:
    def test_perfect_match(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "required_skills": [], "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["score"] >= 80
        assert result["recommendation"] == "EXCELLENT match"

    def test_tier_mismatch_too_weak(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 1, "required_tier": "heavy", "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "light", "status": "active",
                "current_task": None, "model": "llama-7b", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["tier_match"] == 0
        assert any("TIER_MISMATCH" in w for w in result["warnings"])

    def test_overpowered_slot(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 3, "required_tier": "light", "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "heavy", "status": "active",
                "current_task": None, "model": "gpt-4", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["tier_match"] == 25

    def test_slightly_underpowered(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 1, "required_tier": "heavy", "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["tier_match"] == 10

    def test_slot_busy(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": "other_task", "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["availability"] == 10

    def test_slot_not_active(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "exhausted",
                "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["availability"] == 0
        assert any("exhausted" in w for w in result["warnings"])

    def test_capability_match(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "required_skills": ["python", "rust"], "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo",
                "capabilities": ["python", "rust", "go"], "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["capability"] == 20

    def test_capability_partial_match(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "required_skills": ["python", "rust"], "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo",
                "capabilities": ["python"], "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["capability"] == 10  # 50% overlap

    def test_no_skills_required(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["capability"] == 15

    def test_cost_efficiency_cheap(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "llama-7b", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs_file)
        assert result["breakdown"]["cost"] == 15

    def test_cost_efficiency_mid(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "claude-sonnet", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs_file)
        assert result["breakdown"]["cost"] == 10

    def test_cost_efficiency_expensive(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 1, "required_tier": "heavy", "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "heavy", "status": "active",
                "current_task": None, "model": "gpt-4", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs_file)
        assert result["breakdown"]["cost"] == 5

    def test_health_score(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo", "success_rate": 0.5}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["breakdown"]["health"] == 5

    def test_recommendation_good(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": "other", "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["recommendation"] == "GOOD match"

    def test_recommendation_not_recommended(self, tier_defs):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 1, "required_tier": "heavy", "estimated_tokens": 1000}
        slot = {"id": "s1", "tier": "light", "status": "exhausted",
                "model": "llama-7b", "success_rate": 0.0}
        result = _score_slot_for_task(task, slot, tier_defs)
        assert result["recommendation"] == "NOT RECOMMENDED"

    def test_estimated_cost(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _score_slot_for_task
        task = {"priority": 2, "estimated_tokens": 5000}
        slot = {"id": "s1", "tier": "standard", "status": "active",
                "current_task": None, "model": "gpt-3.5-turbo", "success_rate": 1.0}
        result = _score_slot_for_task(task, slot, tier_defs_file)
        # 0.002 * 5000 / 1000 = 0.01
        assert result["estimated_cost"] == pytest.approx(0.01, rel=1e-3)


# ─── _claim_with_fence ─────────────────────────────────────────────────────

class TestClaimWithFence:
    def test_claim_success(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))

        result = _claim_with_fence("t1", "s1")
        assert result["success"] is True
        assert "fence_token" in result

    def test_claim_task_not_found(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        result = _claim_with_fence("nonexistent", "s1")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_claim_already_claimed_by_other(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "IN_PROGRESS",
                          "priority": 2, "blocked_by": [], "required_skills": [],
                          "claimed_by": "other_slot", "fence_token": 100})
        result = _claim_with_fence("t1", "s1")
        assert result["success"] is False
        assert "already claimed" in result["error"]

    def test_claim_already_claimed_by_same_slot(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "IN_PROGRESS",
                          "priority": 2, "blocked_by": [], "required_skills": [],
                          "claimed_by": "s1", "fence_token": 100})
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        result = _claim_with_fence("t1", "s1")
        assert result["success"] is True

    def test_claim_slot_not_in_registry(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        # No registry file
        result = _claim_with_fence("t1", "unknown_slot")
        assert result["success"] is True  # Still claims, just doesn't update slot

    def test_claim_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.orch_helpers import _claim_with_fence
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _claim_with_fence("t1", "s1")
        assert result["success"] is False
        assert "error" in result


# ─── _complete_with_fence ──────────────────────────────────────────────────

class TestCompleteWithFence:
    def test_complete_success(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence, _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        claim = _claim_with_fence("t1", "s1")
        token = claim["fence_token"]
        result = _complete_with_fence("t1", "s1", token, "success")
        assert result["success"] is True
        assert result["outcome"] == "success"

    def test_complete_failed_outcome(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence, _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        claim = _claim_with_fence("t1", "s1")
        result = _complete_with_fence("t1", "s1", claim["fence_token"], "failed")
        assert result["success"] is True
        assert result["outcome"] == "failed"

    def test_complete_task_not_found(self, brain):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence
        result = _complete_with_fence("nonexistent", "s1", 100)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_complete_stale_fence_token(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence, _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        reg = {"slots": {"s1": {"id": "s1"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        _claim_with_fence("t1", "s1")
        result = _complete_with_fence("t1", "s1", 99999)
        assert result["success"] is False
        assert "Stale" in result["error"]

    def test_complete_wrong_claimer(self, brain, tier_defs_file):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence, _claim_with_fence
        _use_json_backend(brain)
        from mcp_server_nucleus.runtime.db import get_storage_backend
        storage = get_storage_backend(brain)
        storage.add_task({"id": "t1", "description": "test", "status": "PENDING",
                          "priority": 2, "blocked_by": [], "required_skills": []})
        reg = {"slots": {"s1": {"id": "s1"}, "s2": {"id": "s2"}}, "aliases": {}}
        (brain / "slots" / "registry.json").write_text(json.dumps(reg))
        claim = _claim_with_fence("t1", "s1")
        result = _complete_with_fence("t1", "s2", claim["fence_token"])
        assert result["success"] is False
        assert "different slot" in result["error"]

    def test_complete_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.orch_helpers import _complete_with_fence
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _complete_with_fence("t1", "s1", 100)
        assert result["success"] is False
        assert "error" in result
