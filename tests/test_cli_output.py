"""Tests for cli_output.py — v1.4.0 output formatter module."""

import json
import sys
import io
import pytest
from unittest.mock import patch

from mcp_server_nucleus.cli_output import (
    is_tty,
    detect_format,
    format_json,
    format_table,
    format_tsv,
    format_scalar,
    output,
    parse_runtime_response,
)


# ════════════════════════════════════════════════════════════════
# TTY Detection
# ════════════════════════════════════════════════════════════════

class TestIsTty:
    def test_returns_bool(self):
        result = is_tty()
        assert isinstance(result, bool)

    def test_non_tty_when_piped(self):
        fake_stdout = io.StringIO()
        with patch.object(sys, 'stdout', fake_stdout):
            assert is_tty() is False


class TestDetectFormat:
    def test_explicit_json(self):
        assert detect_format("json") == "json"

    def test_explicit_table(self):
        assert detect_format("table") == "table"

    def test_explicit_tsv(self):
        assert detect_format("tsv") == "tsv"

    def test_explicit_case_insensitive(self):
        assert detect_format("JSON") == "json"
        assert detect_format("Table") == "table"

    def test_auto_detect_piped(self):
        fake_stdout = io.StringIO()
        with patch.object(sys, 'stdout', fake_stdout):
            assert detect_format(None) == "json"

    def test_explicit_overrides_auto(self):
        fake_stdout = io.StringIO()
        with patch.object(sys, 'stdout', fake_stdout):
            assert detect_format("table") == "table"


# ════════════════════════════════════════════════════════════════
# JSON Formatting
# ════════════════════════════════════════════════════════════════

class TestFormatJson:
    def test_dict(self):
        result = format_json({"key": "value"})
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_list_produces_jsonl(self):
        data = [{"a": 1}, {"a": 2}]
        result = format_json(data)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}
        assert json.loads(lines[1]) == {"a": 2}

    def test_empty_list(self):
        assert format_json([]) == ""

    def test_handles_non_serializable(self):
        from datetime import datetime
        result = format_json({"ts": datetime(2026, 1, 1)})
        assert "2026" in result

    def test_string_passthrough(self):
        result = format_json("hello")
        assert json.loads(result) == "hello"


# ════════════════════════════════════════════════════════════════
# Table Formatting
# ════════════════════════════════════════════════════════════════

class TestFormatTable:
    def test_empty_rows(self):
        assert format_table([]) == "(empty)"

    def test_basic_table(self):
        rows = [{"name": "alice", "age": 30}, {"name": "bob", "age": 25}]
        result = format_table(rows)
        assert "NAME" in result
        assert "AGE" in result
        assert "alice" in result
        assert "bob" in result

    def test_custom_columns(self):
        rows = [{"a": 1, "b": 2, "c": 3}]
        result = format_table(rows, columns=["b", "a"])
        lines = result.split("\n")
        assert "B" in lines[0]
        assert "A" in lines[0]
        assert "C" not in lines[0]

    def test_none_values(self):
        rows = [{"key": "test", "value": None}]
        result = format_table(rows)
        assert "test" in result

    def test_long_values_truncated(self):
        rows = [{"key": "x" * 100}]
        result = format_table(rows)
        assert "..." in result

    def test_separator_line(self):
        rows = [{"a": 1}]
        result = format_table(rows)
        lines = result.split("\n")
        assert "─" in lines[1]


# ════════════════════════════════════════════════════════════════
# TSV Formatting
# ════════════════════════════════════════════════════════════════

class TestFormatTsv:
    def test_empty_rows(self):
        assert format_tsv([]) == ""

    def test_basic_tsv(self):
        rows = [{"a": 1, "b": 2}]
        result = format_tsv(rows)
        lines = result.split("\n")
        assert lines[0] == "a\tb"
        assert lines[1] == "1\t2"

    def test_custom_columns(self):
        rows = [{"x": 10, "y": 20, "z": 30}]
        result = format_tsv(rows, columns=["y", "x"])
        lines = result.split("\n")
        assert lines[0] == "y\tx"
        assert lines[1] == "20\t10"


# ════════════════════════════════════════════════════════════════
# Scalar Formatting
# ════════════════════════════════════════════════════════════════

class TestFormatScalar:
    def test_json_format(self):
        result = format_scalar({"a": 1}, "json")
        parsed = json.loads(result)
        assert parsed == {"a": 1}

    def test_table_format_dict(self):
        result = format_scalar({"key": "val", "num": 42}, "table")
        assert "key: val" in result
        assert "num: 42" in result

    def test_string_passthrough(self):
        assert format_scalar("hello", "table") == "hello"


# ════════════════════════════════════════════════════════════════
# Output Function
# ════════════════════════════════════════════════════════════════

class TestOutput:
    def test_error_prints_to_stderr(self, capsys):
        code = output(None, "json", error="something broke")
        assert code == 1
        captured = capsys.readouterr()
        assert "something broke" in captured.err

    def test_json_list_to_stdout(self, capsys):
        code = output([{"a": 1}], "json")
        assert code == 0
        captured = capsys.readouterr()
        assert json.loads(captured.out.strip()) == {"a": 1}

    def test_table_list_to_stdout(self, capsys):
        code = output([{"x": "hello"}], "table")
        assert code == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_tsv_list(self, capsys):
        code = output([{"a": 1, "b": 2}], "tsv")
        assert code == 0
        captured = capsys.readouterr()
        assert "a\tb" in captured.out

    def test_scalar_json(self, capsys):
        code = output({"status": "ok"}, "json")
        assert code == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["status"] == "ok"

    def test_scalar_table(self, capsys):
        code = output({"status": "ok"}, "table")
        assert code == 0
        captured = capsys.readouterr()
        assert "status: ok" in captured.out

    def test_tsv_scalar_falls_back_to_json(self, capsys):
        code = output({"status": "ok"}, "tsv")
        assert code == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["status"] == "ok"


# ════════════════════════════════════════════════════════════════
# Parse Runtime Response
# ════════════════════════════════════════════════════════════════

class TestParseRuntimeResponse:
    def test_success_json_string(self):
        raw = json.dumps({"success": True, "data": {"key": "val"}, "error": None})
        ok, data, err = parse_runtime_response(raw)
        assert ok is True
        assert data == {"key": "val"}
        assert err is None

    def test_error_json_string(self):
        raw = json.dumps({"success": False, "data": None, "error": "bad input"})
        ok, data, err = parse_runtime_response(raw)
        assert ok is False
        assert data is None
        assert err == "bad input"

    def test_dict_passthrough_success(self):
        ok, data, err = parse_runtime_response({"success": True, "data": [1, 2, 3]})
        assert ok is True
        assert data == [1, 2, 3]

    def test_dict_passthrough_error(self):
        ok, data, err = parse_runtime_response({"success": False, "error": "nope"})
        assert ok is False
        assert err == "nope"

    def test_plain_string(self):
        ok, data, err = parse_runtime_response("hello world")
        assert ok is True
        assert data == "hello world"
        assert err is None

    def test_dict_without_success_key(self):
        ok, data, err = parse_runtime_response({"foo": "bar", "baz": 42})
        assert ok is True
        assert data == {"foo": "bar", "baz": 42}

    def test_error_only_dict(self):
        ok, data, err = parse_runtime_response({"error": "something failed"})
        assert ok is False
        assert err == "something failed"

    def test_non_json_string(self):
        ok, data, err = parse_runtime_response("not json at all")
        assert ok is True
        assert data == "not json at all"

    def test_none_value(self):
        ok, data, err = parse_runtime_response(None)
        assert ok is True
        assert data is None

    def test_integer_value(self):
        ok, data, err = parse_runtime_response(42)
        assert ok is True
        assert data == 42
