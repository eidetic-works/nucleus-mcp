"""
Comprehensive coverage tests for src/mcp_server_nucleus/runtime/emergence_rate.py.

Targets 90%+ line coverage. Tests:
  - Pattern dataclass (to_dict, defaults)
  - PatternCollector: engram/error_fix/tool_combo patterns, empty/missing files,
    malformed JSON, anonymization, collect_all, fallback brain path
  - PatternAggregator: load/save/merge, top patterns, stats, corrupted store
  - PatternSuggester: context mapping, onboarding hints
  - collect_and_aggregate convenience function
"""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.emergence_rate import (
    PATTERN_TYPES,
    Pattern,
    PatternAggregator,
    PatternCollector,
    PatternSuggester,
    collect_and_aggregate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def brain(tmp_path):
    b = tmp_path / "brain"
    b.mkdir()
    return b


def _write_engram_ledger(brain: Path, engrams):
    ledger = brain / "engrams" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "w") as f:
        for eng in engrams:
            f.write(json.dumps(eng) + "\n")


def _write_events(brain: Path, events):
    events_file = brain / "ledger" / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with open(events_file, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


# ---------------------------------------------------------------------------
# Pattern dataclass
# ---------------------------------------------------------------------------

class TestPattern:
    def test_defaults(self):
        p = Pattern(pattern_type="workflow", pattern_key="k1", pattern_value="desc")
        assert p.frequency == 1
        assert p.effectiveness == 0.0
        assert p.first_seen == ""
        assert p.last_seen == ""
        assert p.source_count == 1

    def test_to_dict(self):
        p = Pattern(
            pattern_type="error_fix", pattern_key="k1", pattern_value="v1",
            frequency=5, effectiveness=0.75, first_seen="2024-01-01",
            last_seen="2024-01-02", source_count=3,
        )
        d = p.to_dict()
        assert d["type"] == "error_fix"
        assert d["key"] == "k1"
        assert d["value"] == "v1"
        assert d["frequency"] == 5
        assert d["effectiveness"] == 0.75
        assert d["first_seen"] == "2024-01-01"
        assert d["last_seen"] == "2024-01-02"
        assert d["source_count"] == 3

    def test_to_dict_rounds_effectiveness(self):
        p = Pattern(pattern_type="t", pattern_key="k", pattern_value="v", effectiveness=0.123456)
        d = p.to_dict()
        assert d["effectiveness"] == 0.123

    def test_pattern_types_dict(self):
        assert "workflow" in PATTERN_TYPES
        assert "error_fix" in PATTERN_TYPES
        assert "recipe_usage" in PATTERN_TYPES
        assert "engram_context" in PATTERN_TYPES
        assert "session_depth" in PATTERN_TYPES
        assert "tool_combo" in PATTERN_TYPES


# ---------------------------------------------------------------------------
# PatternCollector
# ---------------------------------------------------------------------------

class TestPatternCollectorInit:
    def test_with_explicit_path(self, brain):
        c = PatternCollector(brain)
        assert c._brain_path == brain

    def test_fallback_to_common(self, monkeypatch, tmp_path):
        """When no path given and common.get_brain_path works, uses it."""
        fake_brain = tmp_path / "fallback_brain"
        fake_brain.mkdir()
        import mcp_server_nucleus.runtime.common as common
        monkeypatch.setattr(common, "get_brain_path", lambda: fake_brain)
        c = PatternCollector()
        assert c._brain_path == fake_brain

    def test_fallback_to_cwd(self, monkeypatch):
        """When no path and common import fails, uses cwd/.brain."""
        import mcp_server_nucleus.runtime.emergence_rate as em
        monkeypatch.setattr(em, "Path", Path)  # ensure Path works
        # Make get_brain_path raise so the except path is taken
        import mcp_server_nucleus.runtime.common as common
        monkeypatch.setattr(common, "get_brain_path", lambda: (_ for _ in ()).throw(RuntimeError("blocked")))
        c = PatternCollector()
        assert c._brain_path.name == ".brain"

    def test_anonymize(self):
        h = PatternCollector._anonymize("test_value")
        assert len(h) == 12
        assert h != "test_value"
        # Deterministic
        assert PatternCollector._anonymize("test_value") == h
        # Different input -> different hash
        assert PatternCollector._anonymize("other") != h


class TestCollectEngramPatterns:
    def test_no_ledger_returns_empty(self, brain):
        c = PatternCollector(brain)
        assert c.collect_engram_patterns() == []

    def test_collects_context_patterns(self, brain):
        _write_engram_ledger(brain, [
            {"context": "Feature", "intensity": 5},
            {"context": "Feature", "intensity": 7},
            {"context": "Strategy", "intensity": 9},
        ])
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 2
        ctx_keys = [p.pattern_key for p in patterns]
        assert "ctx_feature" in ctx_keys
        assert "ctx_strategy" in ctx_keys
        feature_p = next(p for p in patterns if "feature" in p.pattern_key)
        assert feature_p.frequency == 2
        assert feature_p.pattern_type == "engram_context"

    def test_default_context_unknown(self, brain):
        _write_engram_ledger(brain, [{"intensity": 5}])  # no context
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 1
        assert "unknown" in patterns[0].pattern_key

    def test_default_intensity(self, brain):
        _write_engram_ledger(brain, [{"context": "Feature"}])  # no intensity
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 1

    def test_empty_lines_skipped(self, brain):
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.write_text("\n  \n" + json.dumps({"context": "Feature", "intensity": 5}) + "\n")
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 1

    def test_malformed_json_skipped(self, brain):
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.write_text("not json\n" + json.dumps({"context": "Feature", "intensity": 5}) + "\n")
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 1

    def test_effectiveness_capped_at_1(self, brain):
        """When count > 50, effectiveness caps at 1.0."""
        engrams = [{"context": "Feature", "intensity": 5} for _ in range(60)]
        _write_engram_ledger(brain, engrams)
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert patterns[0].effectiveness == 1.0

    def test_top_10_only(self, brain):
        """Only top 10 contexts returned."""
        engrams = [{"context": f"Ctx{i}", "intensity": 5} for i in range(15)]
        _write_engram_ledger(brain, engrams)
        c = PatternCollector(brain)
        patterns = c.collect_engram_patterns()
        assert len(patterns) == 10


class TestCollectErrorFixPatterns:
    def test_no_file_returns_empty(self, brain):
        c = PatternCollector(brain)
        assert c.collect_error_fix_patterns() == []

    def test_collects_heal_events(self, brain):
        _write_events(brain, [
            {"event_type": "self_heal_fix", "data": {"error_type": "SyntaxError"}},
            {"event_type": "self_heal_fix", "data": {"error_type": "SyntaxError"}},
            {"event_type": "heal_attempt", "data": {"category": "ImportError"}},
            {"event_type": "other_event", "data": {}},
        ])
        c = PatternCollector(brain)
        patterns = c.collect_error_fix_patterns()
        assert len(patterns) == 2
        syntax_p = next(p for p in patterns if "SyntaxError" in p.pattern_value)
        assert syntax_p.frequency == 2
        assert syntax_p.pattern_type == "error_fix"

    def test_default_error_type_unknown(self, brain):
        _write_events(brain, [{"event_type": "self_heal", "data": {}}])
        c = PatternCollector(brain)
        patterns = c.collect_error_fix_patterns()
        assert len(patterns) == 1
        assert "unknown" in patterns[0].pattern_value

    def test_empty_lines_skipped(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.write_text("\n  \n" + json.dumps({"event_type": "self_heal", "data": {"error_type": "X"}}) + "\n")
        c = PatternCollector(brain)
        patterns = c.collect_error_fix_patterns()
        assert len(patterns) == 1

    def test_malformed_json_skipped(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.write_text("bad json\n" + json.dumps({"event_type": "heal", "data": {"error_type": "Y"}}) + "\n")
        c = PatternCollector(brain)
        patterns = c.collect_error_fix_patterns()
        assert len(patterns) == 1

    def test_non_heal_events_ignored(self, brain):
        _write_events(brain, [
            {"event_type": "tool_call", "data": {}},
            {"event_type": "LLM_GENERATE", "data": {}},
        ])
        c = PatternCollector(brain)
        assert c.collect_error_fix_patterns() == []


class TestCollectToolComboPatterns:
    def test_no_file_returns_empty(self, brain):
        c = PatternCollector(brain)
        assert c.collect_tool_combo_patterns() == []

    def test_collects_tool_combos(self, brain):
        # Need 3+ occurrences of the same combo
        events = []
        for _ in range(4):
            events.append({"event_type": "tool_search"})
            events.append({"event_type": "tool_read"})
            events.append({"event_type": "tool_search"})
            events.append({"event_type": "tool_read"})
        _write_events(brain, events)
        c = PatternCollector(brain)
        patterns = c.collect_tool_combo_patterns()
        assert len(patterns) > 0
        assert all(p.pattern_type == "tool_combo" for p in patterns)

    def test_llm_generate_counted_as_tool(self, brain):
        events = []
        for _ in range(4):
            events.append({"event_type": "LLM_GENERATE"})
            events.append({"event_type": "tool_write"})
        _write_events(brain, events)
        c = PatternCollector(brain)
        patterns = c.collect_tool_combo_patterns()
        assert len(patterns) > 0

    def test_combos_below_threshold_excluded(self, brain):
        """Combos seen fewer than 3 times are excluded."""
        _write_events(brain, [
            {"event_type": "tool_a"},
            {"event_type": "tool_b"},
        ])
        c = PatternCollector(brain)
        patterns = c.collect_tool_combo_patterns()
        assert patterns == []

    def test_empty_lines_skipped(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.write_text("\n\n" + json.dumps({"event_type": "tool_x"}) + "\n")
        c = PatternCollector(brain)
        # Only 1 event, no combos possible
        assert c.collect_tool_combo_patterns() == []

    def test_malformed_json_skipped(self, brain):
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.write_text("bad\n" + json.dumps({"event_type": "tool_x"}) + "\n")
        c = PatternCollector(brain)
        assert c.collect_tool_combo_patterns() == []

    def test_non_tool_events_ignored(self, brain):
        _write_events(brain, [
            {"event_type": "other_event"},
            {"event_type": "another_event"},
        ])
        c = PatternCollector(brain)
        assert c.collect_tool_combo_patterns() == []

    def test_engram_read_exception_swallowed(self, brain):
        """Ledger is a directory -> read_text raises, exception swallowed."""
        ledger = brain / "engrams" / "ledger.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.mkdir()
        c = PatternCollector(brain)
        assert c.collect_engram_patterns() == []

    def test_error_fix_read_exception_swallowed(self, brain):
        """Events file is a directory -> read_text raises, swallowed."""
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.mkdir()
        c = PatternCollector(brain)
        assert c.collect_error_fix_patterns() == []

    def test_tool_combo_read_exception_swallowed(self, brain):
        """Events file is a directory -> read_text raises, swallowed."""
        events_file = brain / "ledger" / "events.jsonl"
        events_file.parent.mkdir(parents=True)
        events_file.mkdir()
        c = PatternCollector(brain)
        assert c.collect_tool_combo_patterns() == []


class TestCollectAll:
    def test_collect_all_combines(self, brain):
        _write_engram_ledger(brain, [{"context": "Feature", "intensity": 5}])
        _write_events(brain, [{"event_type": "self_heal", "data": {"error_type": "X"}}])
        c = PatternCollector(brain)
        patterns = c.collect_all()
        types = {p.pattern_type for p in patterns}
        assert "engram_context" in types
        assert "error_fix" in types

    def test_collect_all_empty_brain(self, brain):
        c = PatternCollector(brain)
        assert c.collect_all() == []


# ---------------------------------------------------------------------------
# PatternAggregator
# ---------------------------------------------------------------------------

class TestPatternAggregator:
    def test_init_with_path(self, brain):
        a = PatternAggregator(brain)
        assert a._brain_path == brain
        assert a._patterns_file == brain / "emergence" / "patterns.json"

    def test_init_fallback_to_common(self, monkeypatch, tmp_path):
        """When no path given and common works, uses it."""
        fake_brain = tmp_path / "agg_brain"
        fake_brain.mkdir()
        import mcp_server_nucleus.runtime.common as common
        monkeypatch.setattr(common, "get_brain_path", lambda: fake_brain)
        a = PatternAggregator()
        assert a._brain_path == fake_brain

    def test_init_fallback_to_cwd(self, monkeypatch):
        """When no path and common import fails, uses cwd/.brain."""
        # Make get_brain_path raise so the except path is taken
        import mcp_server_nucleus.runtime.common as common
        monkeypatch.setattr(common, "get_brain_path", lambda: (_ for _ in ()).throw(RuntimeError("blocked")))
        a = PatternAggregator()
        assert a._brain_path.name == ".brain"

    def test_load_empty_returns_dict(self, brain):
        a = PatternAggregator(brain)
        assert a._load_patterns() == {}

    def test_merge_new_patterns(self, brain):
        a = PatternAggregator(brain)
        patterns = [
            Pattern(pattern_type="engram_context", pattern_key="ctx_feature", pattern_value="test", frequency=3),
        ]
        changes = a.merge(patterns)
        assert changes == 1
        assert (brain / "emergence" / "patterns.json").exists()

    def test_merge_updates_existing(self, brain):
        a = PatternAggregator(brain)
        p1 = Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v", frequency=3, effectiveness=0.5)
        a.merge([p1])
        p2 = Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v", frequency=2, effectiveness=0.7)
        changes = a.merge([p2])
        assert changes == 1
        loaded = a._load_patterns()
        assert loaded["k1"].frequency == 5
        assert abs(loaded["k1"].effectiveness - 0.6) < 0.01  # avg of 0.5 and 0.7
        assert loaded["k1"].source_count == 2

    def test_save_and_load_roundtrip(self, brain):
        a = PatternAggregator(brain)
        p = Pattern(pattern_type="error_fix", pattern_key="fix_abc", pattern_value="fix desc",
                    frequency=5, effectiveness=0.8, source_count=2)
        a.merge([p])
        b = PatternAggregator(brain)
        loaded = b._load_patterns()
        assert "fix_abc" in loaded
        assert loaded["fix_abc"].pattern_type == "error_fix"
        assert loaded["fix_abc"].frequency == 5
        assert loaded["fix_abc"].source_count == 2

    def test_load_corrupted_file_returns_empty(self, brain, caplog):
        store = brain / "emergence"
        store.mkdir(parents=True)
        (store / "patterns.json").write_text("not valid json")
        a = PatternAggregator(brain)
        with caplog.at_level("WARNING", logger="nucleus.emergence"):
            result = a._load_patterns()
        assert result == {}

    def test_load_missing_pattern_fields_defaults(self, brain):
        """Patterns with missing fields use defaults."""
        store = brain / "emergence"
        store.mkdir(parents=True)
        (store / "patterns.json").write_text(json.dumps({
            "patterns": {"k1": {"type": "workflow", "key": "k1", "value": "v"}}
        }))
        a = PatternAggregator(brain)
        loaded = a._load_patterns()
        assert loaded["k1"].frequency == 1
        assert loaded["k1"].effectiveness == 0.0
        assert loaded["k1"].source_count == 1

    def test_get_top_patterns_unfiltered(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="t1", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9, source_count=2),
            Pattern(pattern_type="t2", pattern_key="k2", pattern_value="v2", frequency=5, effectiveness=0.5, source_count=1),
        ])
        top = a.get_top_patterns(n=10)
        assert len(top) == 2
        # k1 has higher score (10*0.9*2=18 vs 5*0.5*1=2.5)
        assert top[0]["key"] == "k1"

    def test_get_top_patterns_filtered_by_type(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
            Pattern(pattern_type="error_fix", pattern_key="k2", pattern_value="v2", frequency=5, effectiveness=0.5),
        ])
        top = a.get_top_patterns(n=10, pattern_type="error_fix")
        assert len(top) == 1
        assert top[0]["type"] == "error_fix"

    def test_get_top_patterns_limit_n(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="t", pattern_key=f"k{i}", pattern_value=f"v{i}", frequency=i, effectiveness=0.5)
            for i in range(1, 6)
        ])
        top = a.get_top_patterns(n=3)
        assert len(top) == 3

    def test_get_top_patterns_empty(self, brain):
        a = PatternAggregator(brain)
        assert a.get_top_patterns() == []

    def test_get_stats_empty(self, brain):
        a = PatternAggregator(brain)
        stats = a.get_stats()
        assert stats["total_patterns"] == 0
        assert stats["total_observations"] == 0
        assert stats["patterns_by_type"] == {}
        assert "store_path" in stats

    def test_get_stats_with_patterns(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v", frequency=5),
            Pattern(pattern_type="engram_context", pattern_key="k2", pattern_value="v", frequency=3),
            Pattern(pattern_type="error_fix", pattern_key="k3", pattern_value="v", frequency=2),
        ])
        stats = a.get_stats()
        assert stats["total_patterns"] == 3
        assert stats["total_observations"] == 10
        assert stats["patterns_by_type"]["engram_context"] == 2
        assert stats["patterns_by_type"]["error_fix"] == 1

    def test_save_failure_logged(self, brain, monkeypatch, caplog):
        """If write fails, warning is logged but no exception raised."""
        a = PatternAggregator(brain)
        monkeypatch.setattr(Path, "write_text", lambda self, *a, **kw: (_ for _ in ()).throw(PermissionError("denied")))
        with caplog.at_level("WARNING", logger="nucleus.emergence"):
            a._save_patterns({"k": Pattern("t", "k", "v")})
        assert any("Failed to save patterns" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# PatternSuggester
# ---------------------------------------------------------------------------

class TestPatternSuggester:
    def test_get_suggestions_general(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
            Pattern(pattern_type="error_fix", pattern_key="k2", pattern_value="v2", frequency=5, effectiveness=0.5),
        ])
        s = PatternSuggester(brain)
        suggestions = s.get_suggestions(context="general", n=5)
        assert len(suggestions) == 2

    def test_get_suggestions_error_context(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
            Pattern(pattern_type="error_fix", pattern_key="k2", pattern_value="v2", frequency=5, effectiveness=0.5),
        ])
        s = PatternSuggester(brain)
        suggestions = s.get_suggestions(context="error", n=5)
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "error_fix"

    def test_get_suggestions_new_session_context(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
        ])
        s = PatternSuggester(brain)
        suggestions = s.get_suggestions(context="new_session")
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "engram_context"

    def test_get_suggestions_task_planning_context(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="tool_combo", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
        ])
        s = PatternSuggester(brain)
        suggestions = s.get_suggestions(context="task_planning")
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "tool_combo"

    def test_get_suggestions_unknown_context(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1", pattern_value="v1", frequency=10, effectiveness=0.9),
        ])
        s = PatternSuggester(brain)
        # Unknown context maps to None -> all patterns
        suggestions = s.get_suggestions(context="bogus")
        assert len(suggestions) == 1

    def test_get_suggestions_empty(self, brain):
        s = PatternSuggester(brain)
        assert s.get_suggestions() == []

    def test_get_onboarding_hints_engram(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1",
                    pattern_value="Engram context 'Feature' used 10 times", frequency=10, effectiveness=0.9),
        ])
        s = PatternSuggester(brain)
        hints = s.get_onboarding_hints()
        assert len(hints) == 1
        assert "Feature" in hints[0]
        assert "💡" in hints[0]

    def test_get_onboarding_hints_error_fix(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="error_fix", pattern_key="k1",
                    pattern_value="Self-healing fix for 'SyntaxError' applied 5 times",
                    frequency=5, effectiveness=0.8),
        ])
        s = PatternSuggester(brain)
        hints = s.get_onboarding_hints()
        assert len(hints) == 1
        assert "🔧" in hints[0]

    def test_get_onboarding_hints_tool_combo(self, brain):
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="tool_combo", pattern_key="k1",
                    pattern_value="Tool combo 'search → read' used 8 times",
                    frequency=8, effectiveness=0.7),
        ])
        s = PatternSuggester(brain)
        hints = s.get_onboarding_hints()
        assert len(hints) == 1
        assert "⚡" in hints[0]

    def test_get_onboarding_hints_empty(self, brain):
        s = PatternSuggester(brain)
        assert s.get_onboarding_hints() == []

    def test_get_onboarding_hints_value_without_quotes(self, brain):
        """Engram value without quotes still produces a hint."""
        a = PatternAggregator(brain)
        a.merge([
            Pattern(pattern_type="engram_context", pattern_key="k1",
                    pattern_value="no quotes here", frequency=10, effectiveness=0.9),
        ])
        s = PatternSuggester(brain)
        hints = s.get_onboarding_hints()
        assert len(hints) == 1
        assert "no quotes here" in hints[0]


# ---------------------------------------------------------------------------
# collect_and_aggregate
# ---------------------------------------------------------------------------

class TestCollectAndAggregate:
    def test_empty_brain(self, brain):
        result = collect_and_aggregate(brain)
        assert result["collected"] == 0
        assert result["merged_changes"] == 0
        assert result["total_patterns"] == 0

    def test_with_data(self, brain):
        _write_engram_ledger(brain, [
            {"context": "Feature", "intensity": 5},
            {"context": "Feature", "intensity": 7},
        ])
        _write_events(brain, [
            {"event_type": "self_heal", "data": {"error_type": "X"}},
        ])
        result = collect_and_aggregate(brain)
        assert result["collected"] >= 1
        assert result["merged_changes"] >= 1
        assert result["total_patterns"] >= 1
        assert "total_observations" in result
        assert "patterns_by_type" in result
        assert "store_path" in result

    def test_idempotent_merge(self, brain):
        """Running twice doesn't double-count patterns (updates existing)."""
        _write_engram_ledger(brain, [{"context": "Feature", "intensity": 5}])
        r1 = collect_and_aggregate(brain)
        r2 = collect_and_aggregate(brain)
        # Same pattern key, so total_patterns stays the same
        assert r1["total_patterns"] == r2["total_patterns"]
        # But frequency accumulates
        assert r2["total_observations"] > r1["total_observations"]
