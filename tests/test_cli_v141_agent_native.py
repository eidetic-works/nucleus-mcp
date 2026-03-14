"""Tests for v1.4.1 Agent-Native CLI features.

Tests cover:
- Structured error envelope (JSON errors on stdout)
- Error classification and semantic exit codes
- --quiet flag (bare output)
- --help examples presence
- format_quiet() function
"""

import json
import sys
import argparse
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.cli_output import (
    classify_error,
    format_quiet,
    output,
    detect_format,
    EXIT_OK,
    EXIT_ERROR,
    EXIT_USAGE,
    EXIT_NOT_FOUND,
)


# ── Exit Code Constants ────────────────────────────────────────

class TestExitCodeConstants:
    def test_exit_ok_is_zero(self):
        assert EXIT_OK == 0

    def test_exit_error_is_one(self):
        assert EXIT_ERROR == 1

    def test_exit_usage_is_two(self):
        assert EXIT_USAGE == 2

    def test_exit_not_found_is_three(self):
        assert EXIT_NOT_FOUND == 3


# ── Error Classification ──────────────────────────────────────

class TestClassifyError:
    def test_not_found_pattern(self):
        etype, code = classify_error("Engram not found for key 'abc'")
        assert etype == "not_found"
        assert code == EXIT_NOT_FOUND

    def test_no_match_pattern(self):
        etype, code = classify_error("No engrams match query 'xyz'")
        assert etype == "not_found"
        assert code == EXIT_NOT_FOUND

    def test_does_not_exist_pattern(self):
        etype, code = classify_error("Task does not exist: task-123")
        assert etype == "not_found"
        assert code == EXIT_NOT_FOUND

    def test_usage_error_pattern(self):
        etype, code = classify_error("Usage: nucleus engram <search|write|query>")
        assert etype == "usage_error"
        assert code == EXIT_USAGE

    def test_missing_argument_pattern(self):
        etype, code = classify_error("Missing required argument: key")
        assert etype == "usage_error"
        assert code == EXIT_USAGE

    def test_generic_error(self):
        etype, code = classify_error("Failed to write engram")
        assert etype == "runtime_error"
        assert code == EXIT_ERROR

    def test_empty_message(self):
        etype, code = classify_error("")
        assert etype == "runtime_error"
        assert code == EXIT_ERROR


# ── Structured Error Envelope ─────────────────────────────────

class TestStructuredErrors:
    def test_json_error_outputs_envelope_on_stdout(self):
        captured_out = StringIO()
        captured_err = StringIO()
        with patch('sys.stdout', captured_out), patch('sys.stderr', captured_err):
            code = output(None, "json", error="Engram not found for key 'test'")
        stdout_text = captured_out.getvalue()
        stderr_text = captured_err.getvalue()
        assert "error:" in stderr_text
        envelope = json.loads(stdout_text)
        assert envelope["ok"] is False
        assert envelope["error"] == "not_found"
        assert "not found" in envelope["message"].lower()
        assert envelope["exit_code"] == EXIT_NOT_FOUND
        assert code == EXIT_NOT_FOUND

    def test_json_error_runtime_type(self):
        captured_out = StringIO()
        captured_err = StringIO()
        with patch('sys.stdout', captured_out), patch('sys.stderr', captured_err):
            code = output(None, "json", error="Failed to connect to brain")
        envelope = json.loads(captured_out.getvalue())
        assert envelope["error"] == "runtime_error"
        assert code == EXIT_ERROR

    def test_json_error_usage_type(self):
        captured_out = StringIO()
        captured_err = StringIO()
        with patch('sys.stdout', captured_out), patch('sys.stderr', captured_err):
            code = output(None, "json", error="Usage: nucleus engram <search|write|query>")
        envelope = json.loads(captured_out.getvalue())
        assert envelope["error"] == "usage_error"
        assert code == EXIT_USAGE

    def test_table_error_no_json_on_stdout(self):
        captured_out = StringIO()
        captured_err = StringIO()
        with patch('sys.stdout', captured_out), patch('sys.stderr', captured_err):
            code = output(None, "table", error="Something failed")
        assert captured_out.getvalue() == ""
        assert "error:" in captured_err.getvalue()
        assert code == EXIT_ERROR


# ── --quiet / format_quiet ────────────────────────────────────

class TestFormatQuiet:
    def test_quiet_extracts_first_key(self):
        rows = [{"key": "a", "value": "x"}, {"key": "b", "value": "y"}]
        result = format_quiet(rows)
        assert result == "a\nb"

    def test_quiet_with_explicit_key_field(self):
        rows = [{"task_id": "t1", "status": "READY"}, {"task_id": "t2", "status": "DONE"}]
        result = format_quiet(rows, key_field="task_id")
        assert result == "t1\nt2"

    def test_quiet_empty_list(self):
        assert format_quiet([]) == ""

    def test_quiet_handles_none_values(self):
        rows = [{"key": None}, {"key": "b"}]
        result = format_quiet(rows)
        assert result == "None\nb"


class TestQuietOutput:
    def test_quiet_list_output(self):
        captured = StringIO()
        with patch('sys.stdout', captured):
            output([{"key": "a"}, {"key": "b"}], "quiet")
        assert captured.getvalue().strip() == "a\nb"

    def test_quiet_dict_output(self):
        captured = StringIO()
        with patch('sys.stdout', captured):
            output({"key": "test_key", "status": "written"}, "quiet")
        assert captured.getvalue().strip() == "test_key"

    def test_quiet_string_output(self):
        captured = StringIO()
        with patch('sys.stdout', captured):
            output("hello", "quiet")
        assert captured.getvalue().strip() == "hello"


# ── detect_format with quiet ──────────────────────────────────

class TestDetectFormatQuiet:
    def test_quiet_overrides_explicit(self):
        assert detect_format(explicit="json", quiet=True) == "quiet"

    def test_quiet_overrides_none(self):
        assert detect_format(explicit=None, quiet=True) == "quiet"

    def test_no_quiet_uses_explicit(self):
        assert detect_format(explicit="tsv", quiet=False) == "tsv"


# ── Help Examples Presence ────────────────────────────────────

class TestHelpExamples:
    """Verify that --help output contains Examples section for agent subcommands."""

    @pytest.fixture
    def cli_module(self):
        import mcp_server_nucleus.cli as cli_mod
        return cli_mod

    def _get_help(self, cmd_args):
        """Capture --help output for a command."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "mcp_server_nucleus.cli"] + cmd_args + ["--help"],
            capture_output=True, text=True, timeout=30,
            env={**__import__('os').environ, "NUCLEAR_BRAIN_PATH": "/tmp/test_brain"}
        )
        return result.stdout

    def test_engram_search_has_examples(self):
        help_text = self._get_help(["engram", "search"])
        assert "Examples:" in help_text
        assert "nucleus engram search" in help_text

    def test_task_list_has_examples(self):
        help_text = self._get_help(["task", "list"])
        assert "Examples:" in help_text
        assert "nucleus task list" in help_text

    def test_outbound_plan_has_examples(self):
        help_text = self._get_help(["outbound", "plan"])
        assert "Examples:" in help_text
        assert "nucleus outbound plan" in help_text
