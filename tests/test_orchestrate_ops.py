"""
Tests for Orchestrate Operations — Strategy context, engram boost, helpers
==========================================================================
Tests the pure functions directly (strategy loading, boost calculation).
The main orchestration function depends on lazy-loaded module globals,
so we test it with targeted mocking.
"""

import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta


@pytest.fixture
def brain_path(tmp_path):
    """Create a fresh isolated brain directory for each test."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    old = os.environ.get("NUCLEAR_BRAIN_PATH")
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)
    yield brain
    if old is not None:
        os.environ["NUCLEAR_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)


def _write_engrams(brain_path, engrams):
    """Write engrams to the ledger file."""
    ledger = brain_path / "engrams" / "ledger.jsonl"
    with open(ledger, "w", encoding="utf-8") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")


# ── Strategy Context Loading ──────────────────────────────────

class TestLoadStrategyContext:
    def test_empty_ledger(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        result = _load_strategy_context(brain_path)
        assert result == []

    def test_no_ledger_file(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        # Remove engrams dir to ensure no file
        ledger = brain_path / "engrams" / "ledger.jsonl"
        if ledger.exists():
            ledger.unlink()
        result = _load_strategy_context(brain_path)
        assert result == []

    def test_filters_by_strategy_context(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        now = datetime.now(timezone.utc).isoformat()
        _write_engrams(brain_path, [
            {"key": "s1", "value": "Strategy item", "context": "Strategy", "intensity": 8, "timestamp": now},
            {"key": "f1", "value": "Feature item", "context": "Feature", "intensity": 8, "timestamp": now},
        ])
        result = _load_strategy_context(brain_path)
        assert len(result) == 1
        assert result[0]["context"] == "Strategy"

    def test_filters_by_min_intensity_7(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        now = datetime.now(timezone.utc).isoformat()
        _write_engrams(brain_path, [
            {"key": "low", "value": "Low intensity", "context": "Strategy", "intensity": 5, "timestamp": now},
            {"key": "high", "value": "High intensity", "context": "Strategy", "intensity": 9, "timestamp": now},
        ])
        result = _load_strategy_context(brain_path)
        assert len(result) == 1
        assert result[0]["key"] == "high"

    def test_filters_by_recency_7_days(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        recent = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        _write_engrams(brain_path, [
            {"key": "recent", "value": "Recent strategy", "context": "Strategy", "intensity": 8, "timestamp": recent},
            {"key": "old", "value": "Old strategy", "context": "Strategy", "intensity": 8, "timestamp": old},
        ])
        result = _load_strategy_context(brain_path)
        assert len(result) == 1
        assert result[0]["key"] == "recent"

    def test_excludes_deleted(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        now = datetime.now(timezone.utc).isoformat()
        _write_engrams(brain_path, [
            {"key": "active", "value": "Active", "context": "Strategy", "intensity": 8, "timestamp": now},
            {"key": "deleted", "value": "Deleted", "context": "Strategy", "intensity": 8, "timestamp": now, "deleted": True},
        ])
        result = _load_strategy_context(brain_path)
        assert len(result) == 1

    def test_skips_corrupted_lines(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _load_strategy_context
        now = datetime.now(timezone.utc).isoformat()
        ledger = brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            f.write(json.dumps({"key": "s1", "value": "Good", "context": "Strategy", "intensity": 8, "timestamp": now}) + "\n")
            f.write("CORRUPTED\n")
        result = _load_strategy_context(brain_path)
        assert len(result) == 1


# ── Engram Boost Calculation ──────────────────────────────────

class TestComputeEngramBoost:
    def test_no_matching_words(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "build login page", "id": "t1"}
        engrams = [{"value": "completely unrelated xyz abc", "intensity": 8}]
        boost = _compute_engram_boost(task, engrams)
        assert boost == 0.0

    def test_matching_words_produce_boost(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "implement authentication login module", "id": "auth-task"}
        engrams = [{"value": "authentication login is critical priority", "intensity": 9}]
        boost = _compute_engram_boost(task, engrams)
        assert boost > 0.0

    def test_boost_capped_at_3(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "a b c d e f g h i j", "id": "x"}
        engrams = [
            {"value": "a b c d e f g h i j", "intensity": 10},
            {"value": "a b c d e f g h i j", "intensity": 10},
            {"value": "a b c d e f g h i j", "intensity": 10},
            {"value": "a b c d e f g h i j", "intensity": 10},
            {"value": "a b c d e f g h i j", "intensity": 10},
        ]
        boost = _compute_engram_boost(task, engrams)
        assert boost <= 3.0

    def test_higher_intensity_gives_higher_boost(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "deploy the api service", "id": "deploy-1"}
        low_engrams = [{"value": "deploy the api service now", "intensity": 7}]
        high_engrams = [{"value": "deploy the api service now", "intensity": 10}]
        low_boost = _compute_engram_boost(task, low_engrams)
        high_boost = _compute_engram_boost(task, high_engrams)
        assert high_boost >= low_boost

    def test_empty_engrams_list(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "some task", "id": "t1"}
        boost = _compute_engram_boost(task, [])
        assert boost == 0.0

    def test_requires_min_2_word_overlap(self):
        from mcp_server_nucleus.runtime.orchestrate_ops import _compute_engram_boost
        task = {"description": "build unique feature", "id": "t1"}
        engrams = [{"value": "build something else entirely", "intensity": 10}]
        # Only "build" overlaps (1 word) — should not produce boost
        boost = _compute_engram_boost(task, engrams)
        assert boost == 0.0


# ── Orchestrate Impl (with mocking) ──────────────────────────

class TestOrchestrate:
    def test_register_mode_requires_model(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _brain_orchestrate_impl
        from unittest.mock import patch, MagicMock

        # Mock lazy-loaded functions
        with patch("mcp_server_nucleus.runtime.orchestrate_ops._lazy") as mock_lazy:
            mock_lazy.return_value = MagicMock()
            mock_lazy.return_value.return_value = {}  # _get_slot_registry returns empty

            # Override specific lazy calls
            def lazy_side_effect(name):
                if name == "_get_slot_registry":
                    return lambda: {"slots": {}, "aliases": {}}
                if name == "_get_tier_definitions":
                    return lambda: {}
                return MagicMock()

            mock_lazy.side_effect = lazy_side_effect

            result = json.loads(_brain_orchestrate_impl(mode="register"))
            assert result["action"]["type"] == "ERROR"
            assert "model" in result["action"]["reason"].lower()

    def test_auto_mode_requires_slot_id(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _brain_orchestrate_impl
        from unittest.mock import patch, MagicMock

        def lazy_side_effect(name):
            if name == "_get_slot_registry":
                return lambda: {"slots": {}, "aliases": {}}
            if name == "_get_tier_definitions":
                return lambda: {}
            return MagicMock()

        with patch("mcp_server_nucleus.runtime.orchestrate_ops._lazy", side_effect=lazy_side_effect):
            result = json.loads(_brain_orchestrate_impl(mode="auto"))
            assert result["action"]["type"] == "ERROR"
            assert "slot_id" in result["action"]["reason"].lower()

    def test_error_handling_returns_json(self, brain_path):
        from mcp_server_nucleus.runtime.orchestrate_ops import _brain_orchestrate_impl
        from unittest.mock import patch, MagicMock

        # Patch _lazy so it returns callables, then patch get_brain_path to error
        def lazy_side_effect(name):
            return MagicMock(side_effect=Exception("Test error"))

        with patch("mcp_server_nucleus.runtime.orchestrate_ops._lazy", side_effect=lazy_side_effect):
            with patch("mcp_server_nucleus.runtime.orchestrate_ops.get_brain_path", side_effect=Exception("Brain error")):
                result = json.loads(_brain_orchestrate_impl())
                assert result["action"]["type"] == "ERROR"
