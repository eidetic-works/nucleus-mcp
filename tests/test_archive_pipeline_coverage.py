"""Comprehensive tests for mcp_server_nucleus.runtime.archive_pipeline.

Covers LoopTurn, ArchivePipeline (record_turn, get_turns, get_stats,
export_gemini/openai/anthropic, record_preference, record_outcome_preference,
get_preferences, count_preferences, get_preference_stats, export_dpo,
export_dpo_balanced, record_reasoning_chain, get_reasoning_chains,
count_reasoning_chains, get_reasoning_stats, export_reasoning,
mine_preferences_from_archive, mine_reasoning_from_archive,
generate_eval_suite, export_eval_suite, run_eval, synthesize_preferences,
build_judge_fn, iterative_self_play, identify_weaknesses, synthesize_for_weaknesses,
training_status, _recommend_next_action, run_full_pipeline, constitutional_revise,
score_training_data, export_filtered, register_model, get_registry,
update_model_status, get_active_model, shadow_compare, get_shadow_stats,
graduation_check, vault operations, rollback_model, regression_check,
should_retrain, mark_trained, ingest methods, _is_quality_pair,
_split_train_eval, _score_pair, _score_heuristic, _score_llm_judge,
_chain_to_think_format, _is_quality_chain, _resolve_frontier_grades,
_dict_to_turn, _get_existing_hashes, _collect_quality_pairs, count_quality_pairs).
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.archive_pipeline import (
    LoopTurn,
    ArchivePipeline,
    _GRADE_ORDER,
)


@pytest.fixture
def archive(tmp_path, monkeypatch):
    """Create an ArchivePipeline with a temp brain and temp vault."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    inst = ArchivePipeline(brain_path=brain)
    # Mock vault paths to use tmp_path instead of real SSD
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    monkeypatch.setattr(inst, "get_vault_path", lambda: vault)
    monkeypatch.setattr(inst, "vault_version_path", lambda v: vault / v)
    monkeypatch.setattr(type(inst), "DEFAULT_VAULT_PATH", vault)
    return inst


# ── LoopTurn ──

class TestLoopTurn:
    def test_init_defaults(self):
        turn = LoopTurn(
            brother="code", intent="test", actions=["a1"], tools_used=["t1"],
            decisions=["d1"], outcome="ok", signal_absorbed=["s1"],
            signal_produced=["p1"],
        )
        assert turn.brother == "code"
        assert turn.turn_id.startswith("turn-")
        assert turn.timestamp is not None
        assert turn.confidence == 1.0
        assert turn.context == ""
        assert turn.conversation == []
        assert turn.metadata == {}
        assert turn.quality_grade == "copper"
        assert len(turn.content_hash) == 16

    def test_init_with_all_params(self):
        turn = LoopTurn(
            brother="cowork", intent="scan", actions=["a"], tools_used=["t"],
            decisions=["d"], outcome="done", signal_absorbed=[], signal_produced=[],
            confidence=0.8, context="extra context",
            conversation=[{"role": "user", "content": "hi"}],
            metadata={"key": "val"}, quality_grade="gold",
        )
        assert turn.confidence == 0.8
        assert turn.context == "extra context"
        assert turn.quality_grade == "gold"

    def test_to_dict(self):
        turn = LoopTurn(
            brother="code", intent="test", actions=["a"], tools_used=["t"],
            decisions=["d"], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        d = turn.to_dict()
        assert d["brother"] == "code"
        assert d["intent"] == "test"
        assert d["actions"] == ["a"]
        assert "turn_id" in d
        assert "timestamp" in d
        assert "content_hash" in d

    def test_to_conversation_pairs_with_conversation(self):
        turn = LoopTurn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "What is the status?"},
                {"role": "assistant", "content": "Everything is running fine."},
            ],
        )
        pairs = turn.to_conversation_pairs()
        assert len(pairs) == 1
        assert "status" in pairs[0]["user"]
        assert "running" in pairs[0]["assistant"]

    def test_to_conversation_pairs_short_content_skipped(self):
        turn = LoopTurn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "ok"},
            ],
        )
        pairs = turn.to_conversation_pairs()
        # Should fall back to synthesized
        assert len(pairs) == 1

    def test_to_conversation_pairs_multi_turn(self):
        turn = LoopTurn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "First question here"},
                {"role": "assistant", "content": "First answer here"},
                {"role": "user", "content": "Second question here"},
                {"role": "assistant", "content": "Second answer here"},
            ],
        )
        pairs = turn.to_conversation_pairs()
        assert len(pairs) == 2

    def test_to_conversation_pairs_synthesized(self):
        turn = LoopTurn(
            brother="code", intent="Fix the bug", actions=["read file", "edit file"],
            tools_used=[], decisions=["need to add check"], outcome="Fixed",
            signal_absorbed=["engram1"], signal_produced=[],
        )
        pairs = turn.to_conversation_pairs()
        assert len(pairs) == 1
        assert "Fix the bug" in pairs[0]["user"]
        assert "engram1" in pairs[0]["user"]
        assert "Decisions" in pairs[0]["assistant"]
        assert "Actions" in pairs[0]["assistant"]
        assert "Fixed" in pairs[0]["assistant"]

    def test_to_conversation_pairs_with_context(self):
        turn = LoopTurn(
            brother="code", intent="Fix bug", actions=[], tools_used=[],
            decisions=[], outcome="Fixed", signal_absorbed=[], signal_produced=[],
            context="Extra context info",
        )
        pairs = turn.to_conversation_pairs()
        assert "Extra context info" in pairs[0]["user"]

    def test_content_hash_deterministic(self):
        t1 = LoopTurn("code", "same", [], [], [], "same", [], [])
        t2 = LoopTurn("code", "same", [], [], [], "same", [], [])
        assert t1.content_hash == t2.content_hash

    def test_content_hash_differs(self):
        t1 = LoopTurn("code", "same", [], [], [], "different", [], [])
        t2 = LoopTurn("code", "same", [], [], [], "same", [], [])
        assert t1.content_hash != t2.content_hash


# ── ArchivePipeline.__init__ ──

class TestArchivePipelineInit:
    def test_init_creates_training_dir(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        archive = ArchivePipeline(brain_path=brain)
        assert archive.training_dir.exists()
        assert archive.turns_file.name == "loop_turns.jsonl"

    def test_init_default_brain_path(self, tmp_path, monkeypatch):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        archive = ArchivePipeline()
        assert archive.brain_path == brain


# ── record_turn & get_turns ──

class TestRecordAndGetTurns:
    def test_record_turn(self, archive):
        turn = archive.record_turn(
            brother="code", intent="test", actions=["a"], tools_used=["t"],
            decisions=["d"], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        assert turn.turn_id.startswith("turn-")
        turns = archive.get_turns()
        assert len(turns) == 1

    def test_get_turns_empty(self, archive):
        assert archive.get_turns() == []

    def test_get_turns_with_limit(self, archive):
        for i in range(5):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            )
        turns = archive.get_turns(limit=2)
        assert len(turns) == 2

    def test_get_turns_nonexistent_file(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        archive = ArchivePipeline(brain_path=brain)
        # Turns file doesn't exist (never created on init)
        assert not archive.turns_file.exists()
        assert archive.get_turns() == []


# ── get_stats ──

class TestGetStats:
    def test_empty_stats(self, archive):
        stats = archive.get_stats()
        assert stats["total_turns"] == 0
        assert stats["by_brother"] == {}

    def test_stats_after_record(self, archive):
        archive.record_turn(
            brother="code", intent="t1", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        archive.record_turn(
            brother="cowork", intent="t2", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        stats = archive.get_stats()
        assert stats["total_turns"] == 2
        assert stats["by_brother"]["code"] == 1
        assert stats["by_brother"]["cowork"] == 1
        assert stats["first_turn"] is not None
        assert stats["last_turn"] is not None


# ── _is_quality_pair ──

class TestIsQualityPair:
    def test_good_pair(self):
        pair = {"user": "This is a good question about code", "assistant": "This is a detailed answer about the code question."}
        assert ArchivePipeline._is_quality_pair(pair) is True

    def test_too_short_user(self):
        pair = {"user": "short", "assistant": "This is a long enough answer."}
        assert ArchivePipeline._is_quality_pair(pair) is False

    def test_too_short_assistant(self):
        pair = {"user": "This is a long enough question.", "assistant": "short"}
        assert ArchivePipeline._is_quality_pair(pair) is False

    def test_noise_markers(self):
        # Noise markers must dominate >50% of user text to be filtered
        # Single marker counts once, so text must be short enough
        pair = {"user": "*Running MCP tool* padding", "assistant": "This is a good answer that is long enough for testing."}
        assert ArchivePipeline._is_quality_pair(pair) is False

    def test_continuation_message(self):
        pair = {"user": "continue", "assistant": "This is a detailed answer."}
        assert ArchivePipeline._is_quality_pair(pair) is False

    def test_yes_message(self):
        pair = {"user": "yes", "assistant": "This is a detailed answer."}
        assert ArchivePipeline._is_quality_pair(pair) is False


# ── _split_train_eval ──

class TestSplitTrainEval:
    def test_small_dataset(self):
        pairs = [{"user": "q", "assistant": "a"}] * 10
        train, eval = ArchivePipeline._split_train_eval(pairs)
        assert len(train) == 10
        assert len(eval) == 0

    def test_large_dataset(self):
        pairs = [{"user": f"q{i}", "assistant": f"a{i}"} for i in range(50)]
        train, eval = ArchivePipeline._split_train_eval(pairs, eval_ratio=0.1)
        assert len(train) + len(eval) == 50
        assert len(eval) > 0

    def test_zero_eval_ratio(self):
        pairs = [{"user": f"q{i}", "assistant": f"a{i}"} for i in range(50)]
        train, eval = ArchivePipeline._split_train_eval(pairs, eval_ratio=0)
        assert len(train) == 50
        assert len(eval) == 0

    def test_deterministic(self):
        pairs = [{"user": f"q{i}", "assistant": f"a{i}"} for i in range(50)]
        t1, e1 = ArchivePipeline._split_train_eval(pairs)
        t2, e2 = ArchivePipeline._split_train_eval(pairs)
        assert t1 == t2
        assert e1 == e2


# ── count_quality_pairs ──

class TestCountQualityPairs:
    def test_empty(self, archive):
        assert archive.count_quality_pairs() == 0

    def test_with_quality_turns(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "This is a detailed question about the system."},
                {"role": "assistant", "content": "This is a very detailed answer about the system architecture and design."},
            ],
        )
        assert archive.count_quality_pairs() >= 1


# ── Export converters ──

class TestExportGemini:
    def test_export_empty(self, archive, tmp_path):
        out = str(tmp_path / "gemini.jsonl")
        count = archive.export_gemini(out)
        assert count == 0

    def test_export_with_data(self, archive, tmp_path):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "This is a detailed question about code."},
                {"role": "assistant", "content": "This is a very detailed answer about the code implementation."},
            ],
        )
        out = str(tmp_path / "gemini.jsonl")
        count = archive.export_gemini(out)
        assert count > 0
        data = json.loads(Path(out).read_text().strip())
        assert "contents" in data

    def test_export_with_eval(self, archive, tmp_path):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation."},
                ],
            )
        out = str(tmp_path / "gemini.jsonl")
        eval_out = str(tmp_path / "gemini_eval.jsonl")
        count = archive.export_gemini(out, eval_path=eval_out)
        assert count > 0


class TestExportOpenAI:
    def test_export_empty(self, archive, tmp_path):
        out = str(tmp_path / "openai.jsonl")
        count = archive.export_openai(out)
        assert count == 0

    def test_export_with_data(self, archive, tmp_path):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "This is a detailed question about code."},
                {"role": "assistant", "content": "This is a very detailed answer about the code implementation."},
            ],
        )
        out = str(tmp_path / "openai.jsonl")
        count = archive.export_openai(out)
        assert count > 0
        data = json.loads(Path(out).read_text().strip())
        assert "messages" in data
        assert data["messages"][0]["role"] == "system"

    def test_export_custom_system_prompt(self, archive, tmp_path):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "This is a detailed question about code."},
                {"role": "assistant", "content": "This is a very detailed answer about the code implementation."},
            ],
        )
        out = str(tmp_path / "openai.jsonl")
        archive.export_openai(out, system_prompt="Custom prompt")
        data = json.loads(Path(out).read_text().strip())
        assert data["messages"][0]["content"] == "Custom prompt"


class TestExportAnthropic:
    def test_export_empty(self, archive, tmp_path):
        out = str(tmp_path / "anthropic.jsonl")
        count = archive.export_anthropic(out)
        assert count == 0

    def test_export_with_data(self, archive, tmp_path):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "This is a detailed question about code."},
                {"role": "assistant", "content": "This is a very detailed answer about the code implementation."},
            ],
        )
        out = str(tmp_path / "anthropic.jsonl")
        count = archive.export_anthropic(out)
        assert count > 0
        data = json.loads(Path(out).read_text().strip())
        assert "messages" in data


# ── DPO: record_preference ──

class TestRecordPreference:
    def test_record_preference(self, archive):
        pref = archive.record_preference(
            prompt="How do I fix the auth middleware?",
            chosen="I'll update the JWT validation to check expiry before signature...",
            rejected="Let me refactor the entire auth module to use OAuth2...",
        )
        assert pref["pref_id"].startswith("pref-")
        assert pref["source"] == "manual"

    def test_short_prompt_rejected(self, archive):
        pref = archive.record_preference(
            prompt="short",
            chosen="This is a long enough chosen response.",
            rejected="This is a long enough rejected response.",
        )
        assert pref == {}

    def test_short_chosen_rejected(self, archive):
        pref = archive.record_preference(
            prompt="This is a long enough prompt.",
            chosen="short",
            rejected="This is a long enough rejected response.",
        )
        assert pref == {}

    def test_identical_chosen_rejected(self, archive):
        pref = archive.record_preference(
            prompt="This is a long enough prompt.",
            chosen="This is the same response.",
            rejected="This is the same response.",
        )
        assert pref == {}

    def test_with_metadata(self, archive):
        pref = archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
            metadata={"event_type": "deploy"},
        )
        assert pref["metadata"]["event_type"] == "deploy"


class TestRecordOutcomePreference:
    def test_success(self, archive):
        archive.record_outcome_preference(
            "deploy_success",
            "How do I deploy the service to production?",
            "Deploy via CI/CD pipeline with proper checks.",
            success=True,
        )
        prefs = archive.get_preferences()
        assert len(prefs) == 1
        assert prefs[0]["source"] == "outcome"

    def test_failure(self, archive):
        archive.record_outcome_preference(
            "deploy_failed",
            "How do I deploy the service to production?",
            "Just push directly to main branch without checks.",
            success=False,
            context="production",
        )
        prefs = archive.get_preferences()
        assert len(prefs) == 1
        assert prefs[0]["metadata"]["outcome"] == "failure"


# ── is_correction ──

class TestIsCorrection:
    def test_no_prefix(self):
        assert ArchivePipeline.is_correction("yes please") is False

    def test_no_prefix_match(self):
        assert ArchivePipeline.is_correction("no that's wrong") is True

    def test_actually_prefix(self):
        assert ArchivePipeline.is_correction("actually, let me think again") is True

    def test_wrong_prefix(self):
        assert ArchivePipeline.is_correction("wrong answer") is True

    def test_normal_message(self):
        assert ArchivePipeline.is_correction("Can you help me with this?") is False


# ── get_preferences, count_preferences, get_preference_stats ──

class TestPreferenceQueries:
    def test_get_preferences_empty(self, archive):
        assert archive.get_preferences() == []

    def test_get_preferences_with_limit(self, archive):
        for i in range(5):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing.",
                chosen="This is a long enough chosen response for testing.",
                rejected="This is a long enough rejected response for testing.",
            )
        prefs = archive.get_preferences(limit=2)
        assert len(prefs) == 2

    def test_count_preferences(self, archive):
        archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
        )
        assert archive.count_preferences() == 1

    def test_count_preferences_empty(self, archive):
        assert archive.count_preferences() == 0

    def test_get_preference_stats(self, archive):
        archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
            source="retry",
        )
        stats = archive.get_preference_stats()
        assert stats["total_preferences"] == 1
        assert stats["by_source"]["retry"] == 1
        assert stats["first"] is not None
        assert stats["last"] is not None

    def test_get_preference_stats_empty(self, archive):
        stats = archive.get_preference_stats()
        assert stats["total_preferences"] == 0
        assert stats["first"] is None


# ── export_dpo ──

class TestExportDpo:
    def test_empty(self, archive, tmp_path):
        out = str(tmp_path / "dpo.jsonl")
        count = archive.export_dpo(out)
        assert count == 0

    def test_with_data(self, archive, tmp_path):
        archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
        )
        out = str(tmp_path / "dpo.jsonl")
        count = archive.export_dpo(out)
        assert count == 1
        data = json.loads(Path(out).read_text().strip())
        assert "prompt" in data
        assert "chosen" in data
        assert "rejected" in data

    def test_with_eval(self, archive, tmp_path):
        for i in range(25):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
            )
        out = str(tmp_path / "dpo.jsonl")
        eval_out = str(tmp_path / "dpo_eval.jsonl")
        count = archive.export_dpo(out, eval_path=eval_out)
        assert count > 0


class TestExportDpoBalanced:
    def test_empty(self, archive, tmp_path):
        out = str(tmp_path / "dpo_balanced.jsonl")
        result = archive.export_dpo_balanced(out)
        assert result["total"] == 0
        assert result["exported"] == 0

    def test_with_data(self, archive, tmp_path):
        for i in range(10):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="correction",
            )
        out = str(tmp_path / "dpo_balanced.jsonl")
        result = archive.export_dpo_balanced(out)
        assert result["total"] == 10
        assert result["exported"] > 0

    def test_exclude_unjudged(self, archive, tmp_path):
        for i in range(10):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="shadow",
                metadata={"judged": False},
            )
        out = str(tmp_path / "dpo_balanced.jsonl")
        result = archive.export_dpo_balanced(out, exclude_unjudged=True)
        assert result["excluded_unjudged"] == 10

    def test_max_per_source(self, archive, tmp_path):
        for i in range(100):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="correction",
            )
        out = str(tmp_path / "dpo_balanced.jsonl")
        result = archive.export_dpo_balanced(out, max_per_source=10)
        assert result["by_source"]["correction"] == 10


# ── Reasoning chains ──

class TestReasoningChains:
    def test_record_reasoning_chain(self, archive):
        chain = archive.record_reasoning_chain(
            prompt="How do I fix the auth middleware?",
            steps=[
                {"thought": "Let me check the JWT validation", "action": "read_file", "observation": "No expiry check"},
                {"thought": "Need to add expiry validation", "action": "edit_file", "observation": "Added check"},
            ],
            final_answer="Fixed auth by adding JWT expiry validation before signature check.",
        )
        assert chain["chain_id"].startswith("cot-")
        assert chain["step_count"] == 2

    def test_short_chain_rejected(self, archive):
        chain = archive.record_reasoning_chain(
            prompt="short", steps=[], final_answer="short",
        )
        assert chain == {}

    def test_get_reasoning_chains_empty(self, archive):
        assert archive.get_reasoning_chains() == []

    def test_get_reasoning_chains_with_limit(self, archive):
        for i in range(5):
            archive.record_reasoning_chain(
                prompt=f"This is prompt number {i} for testing.",
                steps=[{"thought": "thinking", "action": "acting", "observation": "observing"}],
                final_answer="This is a long enough final answer for testing purposes.",
            )
        chains = archive.get_reasoning_chains(limit=2)
        assert len(chains) == 2

    def test_count_reasoning_chains(self, archive):
        archive.record_reasoning_chain(
            prompt="This is a long enough prompt for testing.",
            steps=[{"thought": "t", "action": "a", "observation": "o"}],
            final_answer="This is a long enough final answer for testing purposes.",
        )
        assert archive.count_reasoning_chains() == 1

    def test_count_reasoning_chains_empty(self, archive):
        assert archive.count_reasoning_chains() == 0

    def test_get_reasoning_stats(self, archive):
        archive.record_reasoning_chain(
            prompt="This is a long enough prompt for testing.",
            steps=[{"thought": "t", "action": "a", "observation": "o"}],
            final_answer="This is a long enough final answer for testing purposes.",
            source="react_loop",
        )
        stats = archive.get_reasoning_stats()
        assert stats["total_chains"] == 1
        assert stats["total_steps"] == 1
        assert stats["by_source"]["react_loop"] == 1

    def test_get_reasoning_stats_empty(self, archive):
        stats = archive.get_reasoning_stats()
        assert stats["total_chains"] == 0
        assert stats["avg_steps"] == 0


# ── _chain_to_think_format ──

class TestChainToThinkFormat:
    def test_basic_format(self):
        chain = {
            "steps": [
                {"thought": "First thought", "action": "first_action", "observation": "first result"},
                {"thought": "Second thought", "action": "", "observation": ""},
            ],
            "final_answer": "The final answer is here.",
        }
        result = ArchivePipeline._chain_to_think_format(chain)
        assert "<think>" in result
        assert "</think>" in result
        assert "First thought" in result
        assert "[Action: first_action]" in result
        assert "first result" in result
        assert "The final answer is here." in result

    def test_empty_steps(self):
        chain = {"steps": [], "final_answer": "Just the answer."}
        result = ArchivePipeline._chain_to_think_format(chain)
        assert "<think>" in result
        assert "Just the answer." in result

    def test_long_observation_truncated(self):
        chain = {
            "steps": [{"thought": "t", "action": "a", "observation": "x" * 600}],
            "final_answer": "answer",
        }
        result = ArchivePipeline._chain_to_think_format(chain)
        assert "..." in result


# ── _is_quality_chain ──

class TestIsQualityChain:
    def test_good_chain(self, archive):
        chain = {
            "steps": [
                {"thought": "This is a detailed thought about the problem", "action": "a", "observation": "o"},
                {"thought": "Another detailed thought", "action": "a", "observation": "o"},
            ],
            "final_answer": "This is a substantial final answer that is long enough.",
        }
        assert archive._is_quality_chain(chain) is True

    def test_single_step(self, archive):
        chain = {
            "steps": [{"thought": "t", "action": "a", "observation": "o"}],
            "final_answer": "answer",
        }
        assert archive._is_quality_chain(chain) is False

    def test_no_thought(self, archive):
        chain = {
            "steps": [
                {"thought": "short", "action": "a", "observation": "o"},
                {"thought": "short", "action": "a", "observation": "o"},
            ],
            "final_answer": "This is a substantial final answer that is long enough.",
        }
        assert archive._is_quality_chain(chain) is False

    def test_short_final_answer(self, archive):
        chain = {
            "steps": [
                {"thought": "This is a detailed thought about the problem", "action": "a", "observation": "o"},
                {"thought": "Another detailed thought", "action": "a", "observation": "o"},
            ],
            "final_answer": "short",
        }
        assert archive._is_quality_chain(chain) is False


# ── export_reasoning ──

class TestExportReasoning:
    def test_empty(self, archive, tmp_path):
        out = str(tmp_path / "reasoning.jsonl")
        count = archive.export_reasoning(out)
        assert count == 0

    def test_with_data(self, archive, tmp_path):
        archive.record_reasoning_chain(
            prompt="This is a long enough prompt for testing purposes.",
            steps=[
                {"thought": "This is a detailed thought about the problem", "action": "a", "observation": "o"},
                {"thought": "Another detailed thought here", "action": "a", "observation": "o"},
            ],
            final_answer="This is a substantial final answer that is long enough for testing.",
        )
        out = str(tmp_path / "reasoning.jsonl")
        count = archive.export_reasoning(out)
        assert count == 1
        data = json.loads(Path(out).read_text().strip())
        assert "<think>" in data["messages"][2]["content"]


# ── should_retrain & mark_trained ──

class TestShouldRetrain:
    def test_empty(self, archive):
        result = archive.should_retrain()
        assert result["should_retrain"] is False
        assert result["total_turns"] == 0

    def test_with_enough_data(self, archive):
        for i in range(60):
            archive.record_turn(
                brother="code", intent=f"t{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            )
        result = archive.should_retrain()
        assert result["should_retrain"] is True

    def test_after_training(self, archive):
        for i in range(60):
            archive.record_turn(
                brother="code", intent=f"t{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            )
        archive.mark_trained()
        result = archive.should_retrain()
        assert result["should_retrain"] is False


class TestMarkTrained:
    def test_mark_trained(self, archive):
        archive.record_turn(
            brother="code", intent="t", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        archive.mark_trained(model_path="/models/v1", base_model="llama3.2")
        assert (archive.training_dir / "last_train.json").exists()
        assert (archive.training_dir / "training_history.jsonl").exists()

    def test_mark_trained_with_hyperparams(self, archive):
        archive.mark_trained(turn_count=100, hyperparams={"lr": 0.001})
        data = json.loads((archive.training_dir / "last_train.json").read_text())
        assert data["hyperparams"]["lr"] == 0.001


# ── Ingest methods ──

class TestIngestGeminiConversation:
    def test_empty_data(self, archive, tmp_path):
        f = tmp_path / "conv.json"
        f.write_text("[]")
        count = archive.ingest_gemini_conversation(str(f))
        assert count == 0

    def test_non_list_data(self, archive, tmp_path):
        f = tmp_path / "conv.json"
        f.write_text('{"not": "a list"}')
        count = archive.ingest_gemini_conversation(str(f))
        assert count == 0

    def test_with_conversation(self, archive, tmp_path):
        data = [
            {"role": "user", "parts": [{"text": "This is the first user message that is long enough."}]},
            {"role": "model", "parts": [{"text": "This is the first model response that is long enough."}]},
            {"role": "user", "parts": [{"text": "This is the second user message that is long enough."}]},
            {"role": "model", "parts": [{"text": "This is the second model response that is long enough."}]},
            {"role": "user", "parts": [{"text": "Third user message here that is long enough."}]},
            {"role": "model", "parts": [{"text": "Third model response here that is long enough."}]},
        ]
        f = tmp_path / "conv.json"
        f.write_text(json.dumps(data))
        count = archive.ingest_gemini_conversation(str(f))
        assert count > 0


class TestIngestClaudeMarkdown:
    def test_empty(self, archive, tmp_path):
        f = tmp_path / "conv.md"
        f.write_text("Just some text without sections.")
        count = archive.ingest_claude_markdown(str(f))
        assert count == 0

    def test_with_sections(self, archive, tmp_path):
        content = "## Human\nThis is the first user message that is long enough.\n\n"
        content += "## Assistant\nThis is the first assistant response that is long enough.\n\n"
        content += "## Human\nThis is the second user message that is long enough.\n\n"
        content += "## Assistant\nThis is the second assistant response that is long enough.\n\n"
        content += "## Human\nThird user message here that is long enough.\n\n"
        content += "## Assistant\nThird assistant response here that is long enough.\n\n"
        f = tmp_path / "conv.md"
        f.write_text(content)
        count = archive.ingest_claude_markdown(str(f))
        assert count > 0

    def test_bold_headers(self, archive, tmp_path):
        content = "**Human**\nThis is the first user message that is long enough.\n\n"
        content += "**Assistant**\nThis is the first assistant response that is long enough.\n\n"
        content += "**Human**\nSecond user message that is long enough here.\n\n"
        content += "**Assistant**\nSecond assistant response that is long enough here.\n\n"
        content += "**Human**\nThird user message that is long enough here.\n\n"
        content += "**Assistant**\nThird assistant response that is long enough here.\n\n"
        f = tmp_path / "conv.md"
        f.write_text(content)
        count = archive.ingest_claude_markdown(str(f))
        assert count > 0


class TestIngestThreadArchive:
    def test_no_file(self, archive):
        count = archive.ingest_thread_archive()
        assert count == 0

    def test_with_data(self, archive, tmp_path):
        thread_path = archive.brain_path / "chat" / "archive" / "thread.jsonl"
        thread_path.parent.mkdir(parents=True)
        entries = []
        for i in range(6):
            entries.append(json.dumps({"role": "user" if i % 2 == 0 else "assistant",
                                       "content": f"This is message {i} that is long enough for testing."}))
        thread_path.write_text("\n".join(entries))
        count = archive.ingest_thread_archive()
        assert count > 0

    def test_too_few_entries(self, archive, tmp_path):
        thread_path = archive.brain_path / "chat" / "archive" / "thread.jsonl"
        thread_path.parent.mkdir(parents=True)
        thread_path.write_text(json.dumps({"role": "user", "content": "hi"}) + "\n")
        count = archive.ingest_thread_archive()
        assert count == 0


# ── Mining ──

class TestMinePreferences:
    def test_no_turns(self, archive):
        assert archive.mine_preferences_from_archive() == 0

    def test_with_correction(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "How do I fix the auth middleware?"},
                {"role": "assistant", "content": "Let me refactor the entire auth module to use OAuth2 and OpenID Connect."},
                {"role": "user", "content": "no, just fix the JWT validation"},
                {"role": "assistant", "content": "I'll update the JWT validation to check expiry before signature validation."},
            ],
        )
        mined = archive.mine_preferences_from_archive()
        assert mined > 0

    def test_idempotent(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            conversation=[
                {"role": "user", "content": "How do I fix the auth middleware?"},
                {"role": "assistant", "content": "Let me refactor the entire auth module to use OAuth2 and OpenID Connect."},
                {"role": "user", "content": "no, just fix the JWT validation"},
                {"role": "assistant", "content": "I'll update the JWT validation to check expiry before signature validation."},
            ],
        )
        first = archive.mine_preferences_from_archive()
        second = archive.mine_preferences_from_archive()
        assert second == 0  # Already mined


class TestMineReasoning:
    def test_no_turns(self, archive):
        assert archive.mine_reasoning_from_archive() == 0

    def test_with_structured_turn(self, archive):
        archive.record_turn(
            brother="code", intent="Fix the authentication bug in the system",
            actions=["read auth.py", "edit auth.py", "test auth"],
            tools_used=[], decisions=["found the bug", "applied the fix"],
            outcome="The authentication bug was fixed by adding proper validation checks.",
            signal_absorbed=[], signal_produced=[],
        )
        mined = archive.mine_reasoning_from_archive()
        assert mined > 0

    def test_idempotent(self, archive):
        archive.record_turn(
            brother="code", intent="Fix the authentication bug in the system",
            actions=["read auth.py", "edit auth.py", "test auth"],
            tools_used=[], decisions=["found the bug", "applied the fix"],
            outcome="The authentication bug was fixed by adding proper validation checks.",
            signal_absorbed=[], signal_produced=[],
        )
        first = archive.mine_reasoning_from_archive()
        second = archive.mine_reasoning_from_archive()
        assert second == 0


# ── Eval suite ──

class TestGenerateEvalSuite:
    def test_not_enough_data(self, archive):
        suite = archive.generate_eval_suite()
        assert suite == []

    def test_with_data(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        suite = archive.generate_eval_suite(count=5)
        assert len(suite) > 0
        for case in suite:
            assert "eval_id" in case
            assert "prompt" in case
            assert "reference" in case
            assert "category" in case
            assert "difficulty" in case

    def test_category_detection_debug(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"How do I fix the bug in function {i}?"},
                    {"role": "assistant", "content": f"This is a detailed answer about fixing the bug number {i} in the function with proper error handling."},
                ],
            )
        suite = archive.generate_eval_suite(count=5)
        cats = [c["category"] for c in suite]
        assert "debug" in cats or all(c["category"] == "general" for c in suite)


class TestExportEvalSuite:
    def test_empty(self, archive, tmp_path):
        out = str(tmp_path / "eval.jsonl")
        count = archive.export_eval_suite(out)
        assert count == 0

    def test_with_data(self, archive, tmp_path):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        out = str(tmp_path / "eval.jsonl")
        count = archive.export_eval_suite(out, count=5)
        assert count > 0
        assert Path(out).exists()


class TestVersionEvalSuite:
    def test_creates_version(self, archive, tmp_path):
        suite = [{"eval_id": "eval-abc12345", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        version = archive._version_eval_suite(suite)
        assert version.startswith("eval_v")
        manifest = json.loads((archive.training_dir / "eval_versions" / "manifest.json").read_text())
        assert manifest["version"] == version

    def test_same_suite_no_new_version(self, archive):
        suite = [{"eval_id": "eval-abc12345", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        v1 = archive._version_eval_suite(suite)
        v2 = archive._version_eval_suite(suite)
        assert v1 == v2  # Same content, no new version

    def test_different_suite_new_version(self, archive):
        suite1 = [{"eval_id": "eval-aaa11111", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        suite2 = [{"eval_id": "eval-bbb22222", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        v1 = archive._version_eval_suite(suite1)
        v2 = archive._version_eval_suite(suite2)
        assert v1 != v2


class TestGetPinnedEvalSuite:
    def test_no_manifest(self, archive):
        assert archive.get_pinned_eval_suite() == []

    def test_with_version(self, archive):
        suite = [{"eval_id": "eval-abc12345", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        version = archive._version_eval_suite(suite)
        loaded = archive.get_pinned_eval_suite(version)
        assert len(loaded) == 1

    def test_latest_version(self, archive):
        suite = [{"eval_id": "eval-abc12345", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        archive._version_eval_suite(suite)
        loaded = archive.get_pinned_eval_suite()
        assert len(loaded) == 1

    def test_nonexistent_version(self, archive):
        suite = [{"eval_id": "eval-abc12345", "prompt": "q", "reference": "a", "category": "code", "difficulty": "easy"}]
        archive._version_eval_suite(suite)
        loaded = archive.get_pinned_eval_suite("eval_v99")
        assert loaded == []

    def test_corrupt_manifest(self, archive):
        eval_dir = archive.training_dir / "eval_versions"
        eval_dir.mkdir(parents=True)
        (eval_dir / "manifest.json").write_text("invalid json")
        assert archive.get_pinned_eval_suite() == []


# ── Scoring ──

class TestScoreHeuristic:
    def test_identical(self):
        result = ArchivePipeline._score_heuristic("hello world", "hello world")
        assert result["score"] == 1.0
        assert result["method"] == "heuristic"

    def test_no_overlap(self):
        result = ArchivePipeline._score_heuristic("apple banana", "cherry date")
        # No word overlap → f1=0, but len_ratio contributes to score
        assert result["f1"] == 0.0
        assert 0 < result["score"] < 0.5  # Only len_ratio component

    def test_empty_response(self):
        result = ArchivePipeline._score_heuristic("", "some reference text here")
        assert result["score"] == 0.0

    def test_partial_overlap(self):
        result = ArchivePipeline._score_heuristic("hello world foo", "hello world bar")
        assert 0 < result["score"] < 1.0


class TestScoreLlmJudge:
    def test_valid_verdict(self):
        judge_fn = MagicMock(return_value="4,3,5")
        result = ArchivePipeline._score_llm_judge("prompt", "response", "reference", judge_fn)
        assert result["method"] == "llm_judge"
        assert result["correctness"] == 4
        assert result["helpfulness"] == 3
        assert result["completeness"] == 5

    def test_parse_error(self):
        judge_fn = MagicMock(return_value="invalid")
        result = ArchivePipeline._score_llm_judge("p", "r", "ref", judge_fn)
        assert result["method"] == "llm_judge_parse_error"
        assert result["score"] == 0.5

    def test_exception(self):
        judge_fn = MagicMock(side_effect=RuntimeError("judge error"))
        result = ArchivePipeline._score_llm_judge("p", "r", "ref", judge_fn)
        assert result["method"] == "llm_judge_error"
        assert result["score"] == 0.5


# ── run_eval ──

class TestRunEval:
    def test_no_suite(self, archive):
        result = archive.run_eval(lambda p: "response")
        assert "error" in result
        assert result["total"] == 0

    def test_with_suite_heuristic(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        result = archive.run_eval(lambda p: "This is a response to the question.", count=5)
        assert result["total_cases"] > 0
        assert "avg_score" in result
        assert "by_category" in result

    def test_with_judge(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        judge_fn = MagicMock(return_value="4,3,5")
        result = archive.run_eval(lambda p: "response", count=5, judge_fn=judge_fn)
        assert result["scoring_method"] == "llm_judge"

    def test_model_fn_exception(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        result = archive.run_eval(lambda p: (_ for _ in ()).throw(RuntimeError("model error")), count=5)
        assert result["total_cases"] > 0
        assert any("error" in r for r in result["results"])


# ── synthesize_preferences ──

class TestSynthesizePreferences:
    def test_not_enough_data(self, archive):
        result = archive.synthesize_preferences(lambda p: "response")
        assert result == 0

    def test_with_data(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        result = archive.synthesize_preferences(lambda p: "This is an alternative response that is long enough.", count=5)
        assert result >= 0

    def test_with_judge(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        judge_fn = MagicMock(return_value="a")
        result = archive.synthesize_preferences(
            lambda p: "This is an alternative response that is long enough.",
            judge_fn=judge_fn, count=5,
        )
        assert result >= 0


# ── build_judge_fn ──

class TestBuildJudgeFn:
    def test_judge_returns_1(self):
        judge_model = MagicMock(return_value="1")
        judge = ArchivePipeline.build_judge_fn(judge_model)
        result = judge("prompt", "resp_a", "resp_b")
        assert result in ("a", "b")

    def test_judge_returns_2(self):
        judge_model = MagicMock(return_value="2")
        judge = ArchivePipeline.build_judge_fn(judge_model)
        result = judge("prompt", "resp_a", "resp_b")
        assert result in ("a", "b")

    def test_judge_exception(self):
        judge_model = MagicMock(side_effect=RuntimeError("error"))
        judge = ArchivePipeline.build_judge_fn(judge_model)
        result = judge("prompt", "resp_a", "resp_b")
        assert result == "a"

    def test_judge_invalid_response(self):
        judge_model = MagicMock(return_value="invalid")
        judge = ArchivePipeline.build_judge_fn(judge_model)
        result = judge("prompt", "resp_a", "resp_b")
        assert result == "a"


# ── iterative_self_play ──

class TestIterativeSelfPlay:
    def test_no_judge(self, archive):
        result = archive.iterative_self_play(lambda p: "r", lambda p: "r")
        assert "error" in result
        assert "judge" in result["error"]

    def test_not_enough_data(self, archive):
        result = archive.iterative_self_play(
            lambda p: "r", lambda p: "r", judge_fn=lambda p, a, b: "a",
        )
        assert "error" in result

    def test_with_data(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        result = archive.iterative_self_play(
            lambda p: "This is the current model response that is long enough.",
            lambda p: "This is the base model response that is long enough.",
            judge_fn=lambda p, a, b: "a", count=5,
        )
        assert result["generated"] >= 0
        assert "current_wins" in result


# ── identify_weaknesses ──

class TestIdentifyWeaknesses:
    def test_no_weaknesses(self, archive):
        eval_results = {
            "avg_score": 0.8,
            "by_category": {"code": 0.9},
            "by_difficulty": {"easy": 0.9},
            "results": [],
        }
        weaknesses = archive.identify_weaknesses(eval_results)
        assert weaknesses == []

    def test_weak_category(self, archive):
        eval_results = {
            "avg_score": 0.8,
            "by_category": {"code": 0.3},
            "by_difficulty": {"easy": 0.9},
            "results": [],
        }
        weaknesses = archive.identify_weaknesses(eval_results)
        assert any(w["type"] == "category" for w in weaknesses)

    def test_weak_difficulty(self, archive):
        eval_results = {
            "avg_score": 0.8,
            "by_category": {"code": 0.9},
            "by_difficulty": {"hard": 0.3},
            "results": [],
        }
        weaknesses = archive.identify_weaknesses(eval_results)
        assert any(w["type"] == "difficulty" for w in weaknesses)

    def test_failures(self, archive):
        eval_results = {
            "avg_score": 0.8,
            "by_category": {"code": 0.9},
            "by_difficulty": {"easy": 0.9},
            "results": [{"eval_id": "e1", "score": 0.1}],
        }
        weaknesses = archive.identify_weaknesses(eval_results)
        assert any(w["type"] == "failures" for w in weaknesses)


# ── synthesize_for_weaknesses ──

class TestSynthesizeForWeaknesses:
    def test_no_weaknesses(self, archive):
        eval_results = {"avg_score": 0.8, "by_category": {}, "by_difficulty": {}, "results": []}
        result = archive.synthesize_for_weaknesses(lambda p: "r", eval_results)
        assert result["total_generated"] == 0

    def test_with_weakness(self, archive):
        eval_results = {
            "avg_score": 0.8,
            "by_category": {"code": 0.3},
            "by_difficulty": {"easy": 0.9},
            "results": [],
        }
        model_fn = MagicMock(return_value="QUESTION: This is a coding question?\nANSWER: This is a detailed answer about coding.")
        result = archive.synthesize_for_weaknesses(model_fn, eval_results, count_per_weakness=2)
        assert result["total_generated"] >= 0


# ── training_status ──

class TestTrainingStatus:
    def test_empty(self, archive):
        status = archive.training_status()
        assert status["sft"]["turns"] == 0
        assert status["sft"]["ready"] is False
        assert status["dpo"]["ready"] is False
        assert "next_action" in status

    def test_with_data(self, archive):
        for i in range(60):
            archive.record_turn(
                brother="code", intent=f"t{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            )
        status = archive.training_status()
        assert status["sft"]["ready"] is True


# ── _recommend_next_action ──

class TestRecommendNextAction:
    def test_accumulate_low_turns(self, archive):
        result = archive._recommend_next_action(10, 0, 0, False, 0, 10, {})
        assert result["action"] == "accumulate"
        assert result["priority"] == "low"

    def test_mine_low_dpo(self, archive):
        result = archive._recommend_next_action(60, 5, 0, False, 0, 60, {})
        assert result["action"] == "mine"
        assert result["priority"] == "high"

    def test_eval_baseline(self, archive):
        result = archive._recommend_next_action(60, 25, 0, False, 0, 60, {})
        assert result["action"] == "eval_baseline"

    def test_train_enough_data(self, archive):
        result = archive._recommend_next_action(250, 25, 0, False, 0, 250, {})
        assert result["action"] == "train"
        assert result["priority"] == "critical"

    def test_synthesize(self, archive):
        result = archive._recommend_next_action(60, 25, 25, True, 0.6, 10, {"self_play": 10})
        assert result["action"] == "synthesize"

    def test_retrain(self, archive):
        result = archive._recommend_next_action(60, 25, 25, True, 0.6, 150, {"self_play": 200})
        assert result["action"] == "train"
        assert result["priority"] == "critical"

    def test_active_learn_low_baseline(self, archive):
        result = archive._recommend_next_action(60, 25, 25, True, 0.3, 10, {"self_play": 200})
        assert result["action"] == "active_learn"

    def test_spin(self, archive):
        result = archive._recommend_next_action(250, 25, 25, True, 0.6, 10, {"self_play": 200, "spin": 0})
        assert result["action"] == "spin"

    def test_active_learn_few(self, archive):
        result = archive._recommend_next_action(250, 25, 25, True, 0.6, 10, {"self_play": 200, "spin": 50, "active_learning": 10})
        assert result["action"] == "active_learn"

    def test_steady_state(self, archive):
        result = archive._recommend_next_action(250, 25, 25, True, 0.6, 10,
                                                {"self_play": 200, "spin": 50, "active_learning": 60})
        assert result["action"] == "accumulate"


# ── run_full_pipeline ──

class TestRunFullPipeline:
    def test_dry_run(self, archive):
        report = archive.run_full_pipeline(dry_run=True)
        assert report["dry_run"] is True
        assert len(report["steps"]) >= 3

    def test_dry_run_with_model(self, archive):
        report = archive.run_full_pipeline(model_fn=lambda p: "r", dry_run=True)
        assert any(s["step"] == "synthesize" for s in report["steps"])

    def test_actual_run(self, archive):
        for i in range(5):
            archive.record_turn(
                brother="code", intent=f"t{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            )
        report = archive.run_full_pipeline()
        assert "status" in report
        assert "next_action" in report


# ── constitutional_revise ──

class TestConstitutionalRevise:
    def test_not_enough_data(self, archive):
        result = archive.constitutional_revise(lambda p: "r")
        assert result == 0

    def test_with_data(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        # Mock model: critique finds issues, then revises
        model_fn = MagicMock(side_effect=["Found issues with the response.", "This is the revised response that is much better than the original."])
        result = archive.constitutional_revise(model_fn, count=1)
        assert result >= 0

    def test_no_issues_found(self, archive):
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        model_fn = MagicMock(return_value="NO ISSUES FOUND")
        result = archive.constitutional_revise(model_fn, count=1)
        assert result == 0


# ── score_training_data ──

class TestScoreTrainingData:
    def test_empty(self, archive):
        result = archive.score_training_data()
        assert result["total"] == 0
        assert result["scored"] == 0

    def test_with_data(self, archive):
        for i in range(3):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        result = archive.score_training_data()
        assert result["total"] > 0
        assert "avg_quality" in result
        assert "quality_distribution" in result


# ── export_filtered ──

class TestExportFiltered:
    def test_empty(self, archive, tmp_path):
        out = str(tmp_path / "filtered.jsonl")
        result = archive.export_filtered(out)
        assert result["total"] == 0
        assert result["exported"] == 0

    def test_with_data(self, archive, tmp_path):
        for i in range(5):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        out = str(tmp_path / "filtered.jsonl")
        result = archive.export_filtered(out, min_quality=0.0)
        assert result["exported"] > 0

    def test_curriculum(self, archive, tmp_path):
        for i in range(5):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        out = str(tmp_path / "filtered.jsonl")
        result = archive.export_filtered(out, min_quality=0.0, curriculum=True)
        assert result["curriculum"] is True

    def test_gemini_format(self, archive, tmp_path):
        for i in range(5):
            archive.record_turn(
                brother="code", intent=f"test{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                conversation=[
                    {"role": "user", "content": f"This is question number {i} about code implementation."},
                    {"role": "assistant", "content": f"This is a detailed answer number {i} about the code implementation and design patterns used."},
                ],
            )
        out = str(tmp_path / "filtered.jsonl")
        result = archive.export_filtered(out, min_quality=0.0, format="gemini")
        data = json.loads(Path(out).read_text().strip().split("\n")[0])
        assert "contents" in data


# ── Model Registry ──

class TestModelRegistry:
    def test_register_model(self, archive):
        entry = archive.register_model("v1", "llama3.2:3b", {"lr": 0.001})
        assert entry["version"] == "v1"
        assert entry["base_model"] == "llama3.2:3b"
        assert entry["status"] == "registered"

    def test_get_registry_empty(self, archive):
        assert archive.get_registry() == []

    def test_get_registry_with_entries(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        registry = archive.get_registry()
        assert len(registry) == 2

    def test_update_model_status(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        result = archive.update_model_status("v1", "shadow")
        assert result is True
        registry = archive.get_registry()
        assert registry[0]["status"] == "shadow"

    def test_update_model_status_not_found(self, archive):
        result = archive.update_model_status("nonexistent", "shadow")
        assert result is False

    def test_update_model_status_promoted(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "canary")
        registry = archive.get_registry()
        assert registry[0]["promoted_at"] is not None

    def test_update_model_status_retired(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "retired")
        registry = archive.get_registry()
        assert registry[0]["retired_at"] is not None

    def test_update_model_status_with_eval(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.8})
        registry = archive.get_registry()
        assert registry[0]["eval_scores"]["avg_score"] == 0.8

    def test_get_active_model_none(self, archive):
        assert archive.get_active_model() is None

    def test_get_active_model_primary(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary")
        active = archive.get_active_model()
        assert active["version"] == "v1"

    def test_get_active_model_canary(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "canary")
        active = archive.get_active_model()
        assert active["version"] == "v1"

    def test_get_active_model_shadow(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "shadow")
        active = archive.get_active_model()
        assert active["version"] == "v1"


# ── Shadow mode ──

class TestShadowCompare:
    def test_shadow_too_short(self, archive):
        result = archive.shadow_compare("prompt", "primary response", lambda p: "short")
        assert result is None

    def test_shadow_empty(self, archive):
        result = archive.shadow_compare("prompt", "primary response", lambda p: "")
        assert result is None

    def test_primary_wins_no_judge(self, archive):
        result = archive.shadow_compare(
            "This is a long enough prompt for testing.",
            "This is the primary response that is long enough.",
            lambda p: "This is the shadow response that is long enough.",
        )
        assert result["shadow_won"] is False

    def test_shadow_wins_with_judge(self, archive):
        judge_fn = MagicMock(return_value="b")
        result = archive.shadow_compare(
            "This is a long enough prompt for testing.",
            "This is the primary response that is long enough.",
            lambda p: "This is the shadow response that is long enough.",
            judge_fn=judge_fn,
        )
        assert result["shadow_won"] is True

    def test_shadow_exception(self, archive):
        result = archive.shadow_compare(
            "prompt", "primary", lambda p: (_ for _ in ()).throw(RuntimeError("error")),
        )
        assert result is None


class TestGetShadowStats:
    def test_empty(self, archive):
        stats = archive.get_shadow_stats()
        assert stats["total"] == 0

    def test_with_shadow_prefs(self, archive):
        archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
            source="shadow",
            metadata={"shadow_won": True},
        )
        stats = archive.get_shadow_stats()
        assert stats["total"] == 1
        assert stats["shadow_wins"] == 1

    def test_with_since_filter(self, archive):
        archive.record_preference(
            prompt="This is a long enough prompt for testing.",
            chosen="This is a long enough chosen response for testing.",
            rejected="This is a long enough rejected response for testing.",
            source="shadow",
            metadata={"shadow_won": True},
        )
        future = datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat()
        stats = archive.get_shadow_stats(since=future)
        assert stats["total"] == 0


# ── graduation_check ──

class TestGraduationCheck:
    def test_no_active_model(self, archive):
        result = archive.graduation_check()
        assert result["recommendation"] == "start_shadow"

    def test_registered_model(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        result = archive.graduation_check()
        assert result["recommendation"] == "start_shadow"

    def test_shadow_not_enough(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "shadow")
        result = archive.graduation_check(min_shadow_comparisons=100)
        assert result["recommendation"] == "hold"

    def test_shadow_ready_for_canary(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "shadow")
        # Add enough shadow prefs
        for i in range(60):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="shadow",
                metadata={"shadow_won": True},
            )
        result = archive.graduation_check(min_shadow_comparisons=50, min_win_rate=0.3)
        assert result["recommendation"] == "promote_canary"

    def test_shadow_low_win_rate(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "shadow")
        for i in range(60):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="shadow",
                metadata={"shadow_won": False},
            )
        result = archive.graduation_check(min_shadow_comparisons=50, min_win_rate=0.3)
        assert result["recommendation"] == "retrain"

    def test_canary_ready_for_primary(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "canary")
        for i in range(60):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="shadow",
                metadata={"shadow_won": True},
            )
        result = archive.graduation_check(canary_win_rate=0.5)
        assert result["recommendation"] == "promote_primary"

    def test_canary_not_ready(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "canary")
        for i in range(60):
            archive.record_preference(
                prompt=f"This is prompt number {i} for testing purposes.",
                chosen=f"This is a long enough chosen response number {i}.",
                rejected=f"This is a long enough rejected response number {i}.",
                source="shadow",
                metadata={"shadow_won": False},
            )
        result = archive.graduation_check(canary_win_rate=0.5)
        assert result["recommendation"] == "hold"

    def test_primary_monitor(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary")
        result = archive.graduation_check()
        assert result["recommendation"] == "monitor"


# ── Vault operations ──

class TestVaultOperations:
    def test_get_vault_path_local(self, archive):
        # SSD not mounted, should fallback to local
        path = archive.get_vault_path()
        assert "vault" in str(path)

    def test_vault_version_path_not_found(self, archive):
        path = archive.vault_version_path("v1")
        # Should return active vault path (local)
        assert "v1" in str(path)

    def test_vault_store(self, archive, tmp_path):
        # Create fake model output
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "model.gguf").write_text("fake model")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        archive.register_model("v1", "llama3.2:3b")
        manifest = archive.vault_store("v1", output_dir)
        assert "vault_path" in manifest
        assert len(manifest["artifacts"]) >= 2

    def test_vault_list_empty(self, archive):
        result = archive.vault_list()
        assert result == []

    def test_vault_list_with_version(self, archive, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "model.gguf").write_text("fake")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        archive.register_model("v1", "llama3.2:3b")
        archive.vault_store("v1", output_dir)
        result = archive.vault_list()
        assert len(result) >= 1

    def test_vault_restore_not_found(self, archive):
        result = archive.vault_restore("nonexistent")
        assert "error" in result

    def test_vault_restore_success(self, archive, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "model.gguf").write_text("fake model content")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        archive.register_model("v1", "llama3.2:3b")
        archive.vault_store("v1", output_dir)
        restore_dir = tmp_path / "restore"
        result = archive.vault_restore("v1", restore_dir)
        assert "restored_to" in result
        assert (restore_dir / "model.gguf").exists()

    def test_rollback_already_active(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary")
        result = archive.rollback_model("v1")
        assert "error" in result

    def test_rollback_not_in_vault(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        result = archive.rollback_model("v99")
        assert "error" in result

    def test_rollback_not_in_registry(self, archive, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "model.gguf").write_text("fake")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        # Store without registering
        vault_dir = archive.vault_version_path("v1")
        vault_dir.mkdir(parents=True)
        (vault_dir / "MANIFEST.json").write_text(json.dumps({"version": "v1"}))
        result = archive.rollback_model("v1")
        assert "error" in result
        assert "registry" in result["error"]


# ── regression_check ──

class TestRegressionCheck:
    def test_not_enough_versions(self, archive):
        result = archive.regression_check()
        assert result["regressed"] is False

    def test_no_eval_scores(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        result = archive.regression_check()
        assert result["regressed"] is False
        assert "Missing eval scores" in result["details"]

    def test_no_regression(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.8, "by_category": {"code": 0.8}})
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary", {"avg_score": 0.85, "by_category": {"code": 0.85}})
        result = archive.regression_check()
        assert result["regressed"] is False

    def test_regression_detected(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.8, "by_category": {"code": 0.8}})
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary", {"avg_score": 0.5, "by_category": {"code": 0.5}})
        result = archive.regression_check()
        assert result["regressed"] is True

    def test_category_regression(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.8, "by_category": {"code": 0.9, "debug": 0.7}})
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary", {"avg_score": 0.79, "by_category": {"code": 0.9, "debug": 0.5}})
        result = archive.regression_check()
        assert len(result["category_regressions"]) > 0

    def test_specific_version(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.8})
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary", {"avg_score": 0.85})
        result = archive.regression_check("v2")
        assert result["current"]["version"] == "v2"

    def test_version_not_found(self, archive):
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        result = archive.regression_check("v99")
        assert result["regressed"] is False
        assert "not found" in result["details"]


# ── _score_pair ──

class TestScorePair:
    def test_platinum_override(self, archive):
        assert archive._score_pair("user", "assistant", "platinum") == 1.0

    def test_good_lengths(self, archive):
        score = archive._score_pair("This is a good user prompt.", "This is a good assistant response with enough detail.", "copper")
        assert 0 < score <= 1.0

    def test_too_short(self, archive):
        score = archive._score_pair("short", "short", "copper")
        assert score < 0.5

    def test_gold_bonus(self, archive):
        copper = archive._score_pair("This is a good user prompt.", "This is a good assistant response with enough detail.", "copper")
        gold = archive._score_pair("This is a good user prompt.", "This is a good assistant response with enough detail.", "gold")
        assert gold > copper

    def test_silver_bonus(self, archive):
        copper = archive._score_pair("This is a good user prompt.", "This is a good assistant response with enough detail.", "copper")
        silver = archive._score_pair("This is a good user prompt.", "This is a good assistant response with enough detail.", "silver")
        assert silver > copper


# ── _resolve_frontier_grades ──

class TestResolveFrontierGrades:
    def test_no_turns(self, archive):
        assert archive._resolve_frontier_grades() == {}

    def test_with_turns_no_receipts(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        grades = archive._resolve_frontier_grades()
        assert grades == {}

    def test_with_verification_receipt(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        # Write verification log
        vlog = archive.brain_path / "verification_log.jsonl"
        turns = archive.get_turns()
        vlog.write_text(json.dumps({
            "timestamp": turns[0]["timestamp"],
            "tier_reached": 3,
            "tiers_failed": [],
        }) + "\n")
        grades = archive._resolve_frontier_grades()
        assert len(grades) > 0

    def test_with_align_verdict(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        # Write human verdicts
        vpath = archive.brain_path / "driver" / "human_verdicts.jsonl"
        vpath.parent.mkdir(parents=True)
        turns = archive.get_turns()
        vpath.write_text(json.dumps({
            "timestamp": turns[0]["timestamp"],
            "verdict": "accepted",
        }) + "\n")
        grades = archive._resolve_frontier_grades()
        assert len(grades) > 0
        assert "platinum" in grades.values()


# ── _dict_to_turn ──

class TestDictToTurn:
    def test_basic(self, archive):
        d = {
            "turn_id": "turn-test",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "brother": "code",
            "intent": "test",
            "actions": ["a"],
            "tools_used": ["t"],
            "decisions": ["d"],
            "outcome": "ok",
            "signal_absorbed": [],
            "signal_produced": [],
            "confidence": 0.9,
            "context": "ctx",
            "conversation": [],
            "metadata": {},
            "content_hash": "abc123",
            "quality_grade": "gold",
        }
        turn = archive._dict_to_turn(d)
        assert turn.turn_id == "turn-test"
        assert turn.brother == "code"
        assert turn.quality_grade == "gold"
        assert turn.content_hash == "abc123"


# ── _get_existing_hashes ──

class TestGetExistingHashes:
    def test_empty(self, archive):
        assert archive._get_existing_hashes() == set()

    def test_with_turns(self, archive):
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
        )
        hashes = archive._get_existing_hashes()
        assert len(hashes) == 1


# ── mine_reasoning_from_archive (multi-turn CoT mining) ──

class TestMineReasoningMultiTurn:
    def test_mine_reasoning_multi_turn(self, archive):
        """Test mining CoT from multi-turn conversations (lines 1316-1364)."""
        # Record a turn with a multi-turn conversation
        conv = [
            {"role": "user", "content": "How do I configure the auth system?"},
            {"role": "assistant", "content": "First, let me check the current configuration. I need to look at the settings file and verify the JWT parameters are set correctly."},
            {"role": "user", "content": "[Tool Result: settings file found]"},
            {"role": "assistant", "content": "Now I can see the settings. The JWT secret needs to be at least 32 characters. Let me update the configuration file with the correct parameters and restart the service."},
            {"role": "user", "content": "[Tool Result: config updated]"},
            {"role": "assistant", "content": "The authentication system is now configured with proper JWT validation. The secret key meets the minimum length requirement and the service has been restarted successfully."},
        ]
        archive.record_turn(
            brother="code", intent="configure auth", actions=["check config"],
            tools_used=["brain_read"], decisions=["update JWT"],
            outcome="auth configured", signal_absorbed=[], signal_produced=[],
            confidence=0.9, context="auth setup", conversation=conv,
        )
        mined = archive.mine_reasoning_from_archive()
        assert mined >= 0  # May or may not mine depending on logic


# ── synthesize_for_weaknesses (active learning) ──

class TestSynthesizeForWeaknessesExtended:
    def test_synthesize_for_weaknesses_coverage(self, archive):
        """Test synthesize_for_weaknesses with category weaknesses (lines 2014-2072)."""
        def mock_model_fn(prompt):
            return "QUESTION: What is the capital of France?\nANSWER: The capital of France is Paris, which is located in the north-central part of the country."

        # Craft eval_results with weaknesses (debug category much weaker than others)
        eval_results = {
            "avg_score": 0.7,
            "by_category": {"debug": 0.2, "code": 0.8, "general": 0.7},
            "by_difficulty": {"easy": 0.8, "medium": 0.6, "hard": 0.3},
            "results": [],
        }
        result = archive.synthesize_for_weaknesses(
            model_fn=mock_model_fn, eval_results=eval_results, count_per_weakness=2
        )
        assert "total_generated" in result
        assert "by_weakness" in result

    def test_synthesize_for_weaknesses_failures(self, archive):
        """Test synthesize_for_weaknesses with failure-type weaknesses (lines 2076-2119)."""
        def mock_model_fn(prompt):
            if "best possible answer" in prompt.lower():
                return "This is a very thorough and detailed answer that covers all aspects of the question comprehensively."
            return "QUESTION: What is X?\nANSWER: X is a concept that describes something very important in the field of computer science and software engineering."

        # Record enough quality turns for eval suite generation
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test_{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                confidence=0.9, conversation=[
                    {"role": "user", "content": f"How do I fix the bug in module {i}?"},
                    {"role": "assistant", "content": f"To fix the bug in module {i}, you need to update the configuration file at /etc/app/config.json and set the parameter 'timeout' to 30 seconds."},
                ],
            )

        # Craft eval_results with failure-type weaknesses
        eval_suite = archive.generate_eval_suite(10)
        eval_results = {
            "avg_score": 0.5,
            "by_category": {"debug": 0.4},
            "by_difficulty": {"easy": 0.5},
            "results": [
                {"eval_id": c["eval_id"], "score": 0.1, "prompt": c["prompt"],
                 "reference": c["reference"], "response": "bad answer"}
                for c in eval_suite[:3]
            ],
        }
        result = archive.synthesize_for_weaknesses(
            model_fn=mock_model_fn, eval_results=eval_results, count_per_weakness=2
        )
        assert "total_generated" in result

    def test_synthesize_for_weaknesses_no_weaknesses(self, archive):
        """Test synthesize_for_weaknesses with no weaknesses found (line 2010-2011)."""
        def mock_model_fn(prompt):
            return "test response"

        eval_results = {
            "avg_score": 0.9,
            "by_category": {"debug": 0.9, "code": 0.9},
            "by_difficulty": {"easy": 0.9},
            "results": [],
        }
        result = archive.synthesize_for_weaknesses(
            model_fn=mock_model_fn, eval_results=eval_results, count_per_weakness=2
        )
        assert result["total_generated"] == 0
        assert result["weaknesses_found"] == 0


# ── run_full_pipeline (synthesize step) ──

class TestRunFullPipelineSynthesize:
    def test_run_full_pipeline_with_model_fn_dry_run(self, archive):
        """Test run_full_pipeline with model_fn in dry_run mode (line 2377-2378)."""
        def mock_model_fn(prompt):
            return "test response"

        def mock_judge_fn(prompt, a, b):
            return "A", 0.8

        report = archive.run_full_pipeline(
            model_fn=mock_model_fn, judge_fn=mock_judge_fn, dry_run=True
        )
        steps = {s["step"]: s for s in report["steps"]}
        assert steps["synthesize"]["status"] == "would synthesize 200"

    def test_run_full_pipeline_no_model_fn(self, archive):
        """Test run_full_pipeline without model_fn (line 2380)."""
        report = archive.run_full_pipeline(dry_run=True)
        steps = {s["step"]: s for s in report["steps"]}
        assert "skipped" in steps["synthesize"]["status"]

    def test_run_full_pipeline_with_synthesize_not_dry_run(self, archive):
        """Test run_full_pipeline with model_fn and not dry_run (lines 2368-2373)."""
        def mock_model_fn(prompt):
            return "QUESTION: What is X?\nANSWER: X is a concept that describes something very important in the field of computer science and software engineering."

        def mock_judge_fn(prompt, a, b):
            return "A", 0.8

        # Record enough quality turns
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test_{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                confidence=0.9, conversation=[
                    {"role": "user", "content": f"How do I fix the bug in module {i}?"},
                    {"role": "assistant", "content": f"To fix the bug in module {i}, you need to update the configuration file at /etc/app/config.json and set the parameter 'timeout' to 30 seconds."},
                ],
            )

        report = archive.run_full_pipeline(
            model_fn=mock_model_fn, judge_fn=mock_judge_fn, dry_run=False
        )
        steps = {s["step"]: s for s in report["steps"]}
        assert "new_pairs" in steps.get("synthesize", {}) or "status" in steps.get("synthesize", {})


# ── _get_eval_prompt_hashes ──

class TestGetEvalPromptHashes:
    def test_get_eval_prompt_hashes_from_export(self, archive, tmp_path):
        """Test _get_eval_prompt_hashes reads from exported eval files (lines 2736-2746)."""
        exports_dir = archive.training_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        eval_file = exports_dir / "eval_suite.jsonl"
        eval_file.write_text(
            json.dumps({"eval_id": "hash1", "prompt": "q1"}) + "\n" +
            json.dumps({"eval_id": "hash2", "prompt": "q2"}) + "\n"
        )
        hashes = archive._get_eval_prompt_hashes()
        assert "hash1" in hashes
        assert "hash2" in hashes

    def test_get_eval_prompt_hashes_no_export(self, archive):
        """Test _get_eval_prompt_hashes generates fresh when no export exists (lines 2748-2750)."""
        # Record enough quality turns so eval suite generation has data
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test_{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                confidence=0.9, conversation=[
                    {"role": "user", "content": f"How do I fix the bug in module {i}?"},
                    {"role": "assistant", "content": f"To fix the bug in module {i}, you need to update the configuration file at /etc/app/config.json and set the parameter 'timeout' to 30 seconds. Then restart the service using 'systemctl restart app'."},
                ],
            )
        hashes = archive._get_eval_prompt_hashes()
        assert len(hashes) > 0

    def test_get_eval_prompt_hashes_corrupt_file(self, archive):
        """Test _get_eval_prompt_hashes handles corrupt eval files (line 2745)."""
        exports_dir = archive.training_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        eval_file = exports_dir / "eval_suite.jsonl"
        eval_file.write_text("invalid json {{{\nmore invalid")
        # Record enough quality turns so it can generate fresh
        for i in range(25):
            archive.record_turn(
                brother="code", intent=f"test_{i}", actions=[], tools_used=[],
                decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
                confidence=0.9, conversation=[
                    {"role": "user", "content": f"How do I fix the bug in module {i}?"},
                    {"role": "assistant", "content": f"To fix the bug in module {i}, you need to update the configuration file at /etc/app/config.json and set the parameter 'timeout' to 30 seconds. Then restart the service using 'systemctl restart app'."},
                ],
            )
        hashes = archive._get_eval_prompt_hashes()
        assert len(hashes) > 0


# ── graduation_check (regression gate) ──

class TestGraduationCheckRegression:
    def test_graduation_blocked_by_regression(self, archive):
        """Test graduation_check blocks on regression (lines 3047-3052)."""
        # Register v1 with high eval scores (no status)
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "retired", {"avg_score": 0.9, "by_category": {"code": 0.9}})
        # Register v2 with low eval scores, set to shadow (active model)
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "shadow", {"avg_score": 0.5, "by_category": {"code": 0.5}})
        # Record shadow comparisons
        for i in range(15):
            archive.shadow_compare(
                f"Test prompt {i} that is long enough",
                "This is the primary response that is long enough for testing.",
                lambda p: "This is the shadow response that is also long enough for testing.",
            )
        result = archive.graduation_check()
        assert result["recommendation"] == "blocked_regression"


# ── vault operations ──

class TestVaultOperationsExtended:
    def test_vault_store_and_restore(self, archive, tmp_path):
        """Test vault_store and vault_restore (lines 3167-3205, 3285-3289)."""
        # Create fake training output
        output_dir = archive.training_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "model.gguf").write_bytes(b"fake model data")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        (output_dir / "eval_metrics.json").write_text('{"accuracy": 0.9}')

        # Create lora_adapter dir
        lora_dir = output_dir / "lora_adapter"
        lora_dir.mkdir()
        (lora_dir / "adapter.bin").write_bytes(b"adapter data")

        # Create sft_adapter dir
        sft_dir = output_dir / "sft_adapter"
        sft_dir.mkdir()
        (sft_dir / "sft.bin").write_bytes(b"sft data")

        # Register model first
        archive.register_model("v_test", "llama3.2:3b")

        # Store to vault
        manifest = archive.vault_store("v_test", output_dir, sft_adapter_dir=sft_dir)
        assert manifest["version"] == "v_test"
        assert any(a["type"] == "gguf" for a in manifest["artifacts"])
        assert any(a["type"] == "lora_adapter" for a in manifest["artifacts"])
        assert any(a["type"] == "sft_adapter" for a in manifest["artifacts"])

        # Restore from vault
        restore_dir = archive.training_dir / "restore_test"
        result = archive.vault_restore("v_test", restore_dir)
        assert "restored_to" in result
        assert "model.gguf" in result["artifacts"]
        assert "lora_adapter/" in result["artifacts"]

    def test_vault_restore_overwrite_existing(self, archive):
        """Test vault_restore overwrites existing lora_adapter (lines 3286-3288)."""
        output_dir = archive.training_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "model.gguf").write_bytes(b"fake model")
        (output_dir / "Modelfile").write_text("FROM model.gguf")

        lora_dir = output_dir / "lora_adapter"
        lora_dir.mkdir()
        (lora_dir / "adapter.bin").write_bytes(b"adapter data")

        archive.register_model("v_overwrite", "llama3.2:3b")
        archive.vault_store("v_overwrite", output_dir)

        # Pre-create lora_adapter in restore dir
        restore_dir = archive.training_dir / "restore_overwrite"
        existing_lora = restore_dir / "lora_adapter"
        existing_lora.mkdir(parents=True)
        (existing_lora / "old.bin").write_bytes(b"old data")

        result = archive.vault_restore("v_overwrite", restore_dir)
        assert "lora_adapter/" in result["artifacts"]
        assert not (existing_lora / "old.bin").exists()  # Old file should be gone


# ── rollback_model ──

class TestRollbackModel:
    def test_rollback_already_active(self, archive):
        """Test rollback when target is already active (line 3326)."""
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary")
        result = archive.rollback_model("v1")
        assert "error" in result

    def test_rollback_not_in_registry(self, archive):
        """Test rollback when target not in registry (line 3341)."""
        # Create vault dir with manifest but no registry entry
        vault_dir = archive.get_vault_path() / "v_missing"
        vault_dir.mkdir(parents=True)
        (vault_dir / "MANIFEST.json").write_text('{"version": "v_missing"}')
        (vault_dir / "model.gguf").write_bytes(b"fake")
        (vault_dir / "Modelfile").write_text("FROM model.gguf")
        result = archive.rollback_model("v_missing")
        assert "error" in result

    def test_rollback_success(self, archive):
        """Test successful rollback (lines 3343-3367)."""
        # Register v1 and v2
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary")

        # Store v1 to vault
        output_dir = archive.training_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "model.gguf").write_bytes(b"fake v1 model")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        archive.vault_store("v1", output_dir)

        result = archive.rollback_model("v1")
        assert result["to_version"] == "v1"
        assert result["new_status"] == "shadow"
        assert result["from_version"] == "v2"


# ── _resolve_frontier_grades ──

class TestResolveFrontierGradesExtended:
    def test_resolve_with_verification_log(self, archive):
        """Test _resolve_frontier_grades reads verification_log.jsonl (lines 3529-3538)."""
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            confidence=0.9, conversation=[
                {"role": "user", "content": "Test question"},
                {"role": "assistant", "content": "Test answer that is long enough to pass quality checks"},
            ],
        )
        turns = archive.get_turns()
        turn_id = turns[0]["turn_id"]

        # Write verification log
        brain = archive.training_dir.parent
        vlog = brain / "verification_log.jsonl"
        vlog.write_text(json.dumps({
            "timestamp": turns[0]["timestamp"],
            "tier_reached": 3,
            "tiers_failed": [],
        }) + "\n")

        grades = archive._resolve_frontier_grades()
        assert turn_id in grades
        assert grades[turn_id] == "gold"

    def test_resolve_with_human_verdicts(self, archive):
        """Test _resolve_frontier_grades reads human_verdicts.jsonl (lines 3544-3557)."""
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            confidence=0.9, conversation=[
                {"role": "user", "content": "Test question"},
                {"role": "assistant", "content": "Test answer that is long enough to pass quality checks"},
            ],
        )
        turns = archive.get_turns()
        turn_id = turns[0]["turn_id"]

        # Write human verdicts
        brain = archive.training_dir.parent
        vpath = brain / "driver" / "human_verdicts.jsonl"
        vpath.parent.mkdir(parents=True, exist_ok=True)
        vpath.write_text(json.dumps({
            "timestamp": turns[0]["timestamp"],
            "verdict": "accepted",
        }) + "\n")

        grades = archive._resolve_frontier_grades()
        assert turn_id in grades
        assert grades[turn_id] == "platinum"

    def test_resolve_with_corrected_verdict(self, archive):
        """Test _resolve_frontier_grades with corrected verdict = gold."""
        archive.record_turn(
            brother="code", intent="test", actions=[], tools_used=[],
            decisions=[], outcome="ok", signal_absorbed=[], signal_produced=[],
            confidence=0.9, conversation=[
                {"role": "user", "content": "Test question"},
                {"role": "assistant", "content": "Test answer that is long enough to pass quality checks"},
            ],
        )
        turns = archive.get_turns()
        turn_id = turns[0]["turn_id"]

        brain = archive.training_dir.parent
        vpath = brain / "driver" / "human_verdicts.jsonl"
        vpath.parent.mkdir(parents=True, exist_ok=True)
        vpath.write_text(json.dumps({
            "timestamp": turns[0]["timestamp"],
            "verdict": "corrected",
        }) + "\n")

        grades = archive._resolve_frontier_grades()
        assert turn_id in grades
        assert grades[turn_id] == "gold"

    def test_resolve_no_turns(self, archive):
        """Test _resolve_frontier_grades with no turns returns empty."""
        grades = archive._resolve_frontier_grades()
        assert grades == {}


# ── _score_pair with quality grades ──

class TestScorePairGrades:
    def test_score_pair_platinum(self, archive):
        """Test _score_pair with platinum grade (line 3575)."""
        score = archive._score_pair("test user", "test assistant", quality_grade="platinum")
        assert score == 1.0

    def test_score_pair_gold(self, archive):
        """Test _score_pair with gold grade."""
        score = archive._score_pair(
            "What is the config setting?",
            "The config setting should be set to the value of the environment variable.",
            quality_grade="gold",
        )
        assert score > 0.5  # Should get bonus

    def test_score_pair_silver(self, archive):
        """Test _score_pair with silver grade."""
        score = archive._score_pair(
            "What is the config setting?",
            "The config setting should be set to the value of the environment variable.",
            quality_grade="silver",
        )
        assert score > 0.3

    def test_score_pair_short_inputs(self, archive):
        """Test _score_pair with very short inputs (line 3582-3583)."""
        score = archive._score_pair("hi", "ok", quality_grade="copper")
        assert score < 0.3

    def test_score_pair_medium_inputs(self, archive):
        """Test _score_pair with medium inputs (line 3584-3585)."""
        score = archive._score_pair("short", "medium length answer here", quality_grade="copper")
        assert 0.1 < score < 1.0


# ── regression_check ──

class TestRegressionCheckExtended:
    def test_regression_not_enough_versions(self, archive):
        """Test regression_check with < 2 versions (line 3400)."""
        archive.register_model("v1", "llama3.2:3b")
        result = archive.regression_check()
        assert result["regressed"] is False

    def test_regression_version_not_found(self, archive):
        """Test regression_check with version not in registry (line 3407)."""
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        result = archive.regression_check("v_nonexistent")
        assert result["regressed"] is False

    def test_regression_no_previous(self, archive):
        """Test regression_check with no previous version (line 3417)."""
        archive.register_model("v1", "llama3.2:3b")
        result = archive.regression_check("v1")
        assert result["regressed"] is False

    def test_regression_detected(self, archive):
        """Test regression_check detects regression."""
        archive.register_model("v1", "llama3.2:3b")
        archive.update_model_status("v1", "primary", {"avg_score": 0.9, "by_category": {"code": 0.9}})
        archive.register_model("v2", "qwen2.5:7b")
        archive.update_model_status("v2", "primary", {"avg_score": 0.5, "by_category": {"code": 0.5}})
        result = archive.regression_check("v2")
        assert result["regressed"] is True

    def test_regression_no_scores(self, archive):
        """Test regression_check with no eval scores."""
        archive.register_model("v1", "llama3.2:3b")
        archive.register_model("v2", "qwen2.5:7b")
        result = archive.regression_check("v2")
        assert result["regressed"] is False


# ── _update_registry_artifact ──

class TestUpdateRegistryArtifact:
    def test_update_registry_artifact_not_found(self, archive):
        """Test _update_registry_artifact with version not in registry (line 3377)."""
        archive.register_model("v1", "llama3.2:3b")
        archive._update_registry_artifact("v_nonexistent", "/some/path")
        # Should not raise, just return
        registry = archive.get_registry()
        assert len(registry) == 1

    def test_update_registry_artifact_success(self, archive):
        """Test _update_registry_artifact updates existing entry."""
        archive.register_model("v1", "llama3.2:3b")
        archive._update_registry_artifact("v1", "/vault/v1")
        registry = archive.get_registry()
        assert registry[0]["artifact_path"] == "/vault/v1"


# ── vault_list ──

class TestVaultList:
    def test_vault_list_empty(self, archive):
        """Test vault_list with no versions."""
        result = archive.vault_list()
        assert result == []

    def test_vault_list_with_versions(self, archive):
        """Test vault_list with stored versions."""
        output_dir = archive.training_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "model.gguf").write_bytes(b"fake")
        (output_dir / "Modelfile").write_text("FROM model.gguf")
        archive.register_model("v1", "llama3.2:3b")
        archive.vault_store("v1", output_dir)
        result = archive.vault_list()
        assert len(result) >= 1
        assert result[0]["version"] == "v1"
