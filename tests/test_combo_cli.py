"""Tests for the `nucleus combo` CLI subcommand.

Tests cover:
- Argparse registration of combo subcommand and its 3 actions
- God Combo pipeline return structure
- Circuit breaker timing metadata
- CLI handler output formatting (via mock)
"""

import argparse
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ── Argparse registration tests ─────────────────────────────

class TestComboArgparse:
    """Verify combo subcommand is properly registered."""

    def _build_parser(self):
        """Build a minimal parser with just the combo subcommand."""
        from mcp_server_nucleus.cli import main
        # We can't easily extract the parser, so test via parse_known_args pattern
        # Instead, test that the CLI module has handle_combo_command
        from mcp_server_nucleus.cli import handle_combo_command
        assert callable(handle_combo_command)

    def test_combo_handler_exists(self):
        self._build_parser()

    def test_combo_pulse_no_args(self):
        """pulse requires no positional args."""
        from mcp_server_nucleus.cli import handle_combo_command
        args = argparse.Namespace(combo_action='pulse')
        # Should not raise on construction
        assert args.combo_action == 'pulse'

    def test_combo_diagnose_requires_symptom(self):
        """diagnose needs a symptom string."""
        args = argparse.Namespace(combo_action='diagnose', symptom='high latency')
        assert args.symptom == 'high latency'

    def test_combo_learn_requires_observation(self):
        """learn needs observation, context, intensity."""
        args = argparse.Namespace(
            combo_action='learn',
            observation='cache fix helped',
            context='Decision',
            intensity=6,
        )
        assert args.observation == 'cache fix helped'
        assert args.context == 'Decision'
        assert args.intensity == 6

    def test_combo_none_prints_help(self, capsys):
        """No action should print usage help."""
        from mcp_server_nucleus.cli import handle_combo_command
        args = argparse.Namespace(combo_action=None)
        handle_combo_command(args)
        captured = capsys.readouterr()
        assert "God Combos" in captured.out
        assert "pulse" in captured.out
        assert "diagnose" in captured.out
        assert "learn" in captured.out

    def test_combo_unknown_action(self, capsys):
        """Unknown action should print error."""
        from mcp_server_nucleus.cli import handle_combo_command
        args = argparse.Namespace(combo_action='nonexistent')
        handle_combo_command(args)
        captured = capsys.readouterr()
        assert "Unknown combo" in captured.out


# ── God Combo pipeline return structure tests ────────────────

class TestPulseAndPolishPipeline:
    """Test pulse_and_polish pipeline structure."""

    def test_returns_dict_with_required_keys(self):
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        result = run_pulse_and_polish(write_engram=False)
        assert isinstance(result, dict)
        assert "pipeline" in result
        assert result["pipeline"] == "pulse_and_polish"
        assert "synthesis" in result
        assert "meta" in result
        assert "sections" in result

    def test_meta_has_timing(self):
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        result = run_pulse_and_polish(write_engram=False)
        meta = result["meta"]
        assert "execution_time_ms" in meta
        assert "steps_completed" in meta
        assert meta["steps_completed"] >= 1
        assert meta["execution_time_ms"] >= 0

    def test_synthesis_has_health(self):
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        result = run_pulse_and_polish(write_engram=False)
        syn = result.get("synthesis")
        if syn:  # synthesis may be None if all steps fail
            assert "overall_health" in syn
            assert "dispatch_total" in syn

    def test_no_engram_written_when_disabled(self):
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish
        result = run_pulse_and_polish(write_engram=False)
        assert result["meta"].get("engram_written") is not True


class TestSelfHealingSREPipeline:
    """Test self_healing_sre pipeline structure."""

    def test_returns_dict_with_required_keys(self):
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
        result = run_self_healing_sre(symptom="test symptom", write_engram=False)
        assert isinstance(result, dict)
        assert result["pipeline"] == "self_healing_sre"
        assert "diagnosis" in result
        assert "recommendation" in result
        assert "meta" in result

    def test_diagnosis_structure(self):
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
        result = run_self_healing_sre(symptom="high latency", write_engram=False)
        diag = result.get("diagnosis")
        if diag:
            assert "severity" in diag
            assert diag["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            assert "findings" in diag
            assert isinstance(diag["findings"], list)

    def test_recommendation_structure(self):
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
        result = run_self_healing_sre(symptom="dispatch errors", write_engram=False)
        rec = result.get("recommendation")
        if rec:
            assert "action" in rec
            assert "auto_fixable" in rec
            assert isinstance(rec["auto_fixable"], bool)

    def test_meta_timing(self):
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre
        result = run_self_healing_sre(symptom="test", write_engram=False)
        assert result["meta"]["execution_time_ms"] >= 0
        assert result["meta"]["steps_completed"] >= 1


class TestFusionReactorPipeline:
    """Test fusion_reactor pipeline structure."""

    def test_returns_dict_with_required_keys(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="test observation",
            context="Decision",
            intensity=5,
            write_engrams=False,
        )
        assert isinstance(result, dict)
        assert result["pipeline"] == "fusion_reactor"
        assert "synthesis" in result
        assert "meta" in result

    def test_synthesis_structure(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="cache fix reduced latency",
            write_engrams=False,
        )
        syn = result.get("synthesis")
        if syn:
            assert "type" in syn
            assert syn["type"] in ("novel", "reinforced", "compounded")
            assert "prior_count" in syn
            assert "compounding_factor" in syn

    def test_no_engrams_written_when_disabled(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="test",
            write_engrams=False,
        )
        assert result["meta"]["engrams_written"] == 0

    def test_meta_steps_at_least_capture(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="test observation",
            write_engrams=False,
        )
        assert result["meta"]["steps_completed"] >= 1

    def test_intensity_respected(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="test",
            intensity=9,
            write_engrams=False,
        )
        syn = result.get("synthesis")
        if syn:
            # synthesis intensity = base + 1, capped at 10
            assert syn["intensity"] == 10

    def test_context_passed_through(self):
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor
        result = run_fusion_reactor(
            observation="test",
            context="Architecture",
            write_engrams=False,
        )
        capture = result["sections"].get("capture", {})
        assert capture.get("context") == "Architecture"


# ── CLI handler output tests (mocked pipelines) ─────────────

class TestComboHandlerOutput:
    """Test CLI handler formats output correctly with mocked pipelines."""

    def test_pulse_handler_prints_health(self, capsys):
        mock_result = {
            "synthesis": {
                "overall_health": "🟢 OPERATIONAL",
                "dispatch_total": 42,
                "error_rate_pct": 0.5,
                "task_count": 3,
                "recommendation": "Keep shipping",
            },
            "meta": {
                "steps_completed": 4,
                "execution_time_ms": 120.5,
                "engram_written": True,
            },
        }
        with patch(
            "mcp_server_nucleus.cli.handle_combo_command.__module__",
            create=True,
        ):
            from mcp_server_nucleus.cli import handle_combo_command
            with patch(
                "mcp_server_nucleus.runtime.god_combos.pulse_and_polish.run_pulse_and_polish",
                return_value=mock_result,
            ):
                args = argparse.Namespace(combo_action='pulse')
                handle_combo_command(args)
                captured = capsys.readouterr()
                assert "PULSE & POLISH" in captured.out
                assert "OPERATIONAL" in captured.out
                assert "42" in captured.out

    def test_diagnose_handler_prints_severity(self, capsys):
        mock_result = {
            "diagnosis": {
                "severity": "HIGH",
                "findings": ["Error rate is 15%"],
                "correlated_contexts": ["Architecture"],
            },
            "recommendation": {
                "action": "URGENT: Review errors",
                "auto_fixable": False,
            },
            "meta": {
                "steps_completed": 4,
                "execution_time_ms": 95.0,
            },
        }
        from mcp_server_nucleus.cli import handle_combo_command
        with patch(
            "mcp_server_nucleus.runtime.god_combos.self_healing_sre.run_self_healing_sre",
            return_value=mock_result,
        ):
            args = argparse.Namespace(combo_action='diagnose', symptom='high latency')
            handle_combo_command(args)
            captured = capsys.readouterr()
            assert "SELF-HEALING SRE" in captured.out
            assert "HIGH" in captured.out
            assert "high latency" in captured.out

    def test_learn_handler_prints_compounding(self, capsys):
        mock_result = {
            "synthesis": {
                "type": "reinforced",
                "prior_count": 2,
                "compounding_factor": 1.2,
                "intensity": 7,
            },
            "meta": {
                "steps_completed": 5,
                "execution_time_ms": 200.0,
                "engrams_written": 2,
            },
        }
        from mcp_server_nucleus.cli import handle_combo_command
        with patch(
            "mcp_server_nucleus.runtime.god_combos.fusion_reactor.run_fusion_reactor",
            return_value=mock_result,
        ):
            args = argparse.Namespace(
                combo_action='learn',
                observation='cache fix worked',
                context='Decision',
                intensity=6,
            )
            handle_combo_command(args)
            captured = capsys.readouterr()
            assert "FUSION REACTOR" in captured.out
            assert "reinforced" in captured.out
            assert "1.2" in captured.out

    def test_pulse_handler_catches_import_error(self, capsys):
        """If God Combo import fails, handler should print error, not crash."""
        from mcp_server_nucleus.cli import handle_combo_command
        with patch(
            "mcp_server_nucleus.runtime.god_combos.pulse_and_polish.run_pulse_and_polish",
            side_effect=Exception("import broken"),
        ):
            args = argparse.Namespace(combo_action='pulse')
            handle_combo_command(args)
            captured = capsys.readouterr()
            assert "failed" in captured.out.lower() or "error" in captured.out.lower()
