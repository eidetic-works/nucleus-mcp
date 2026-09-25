"""Comprehensive tests for runtime/loops/fixer.py — FixerLoop."""
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_server_nucleus.runtime.loops.fixer import FixerLoop


class TestFixerLoop:
    def test_init(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("print('hello')")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda path, ctx: '{"status": "ok"}',
            max_retries=3,
        )
        assert loop.target_file == target
        assert loop.verification_command == f"{sys.executable} -c 'pass'"
        assert loop.max_retries == 3
        assert loop.logs == []

    def test_run_file_not_found(self, tmp_path):
        loop = FixerLoop(
            target_file=str(tmp_path / "nonexistent.py"),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        result = loop.run()
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_run_initial_pass(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("print('hello')")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        result = loop.run()
        assert result["status"] == "success"
        assert "passed verification initially" in result["message"]
        assert "logs" in result

    def test_run_fix_succeeds(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("broken code")

        call_count = [0]

        def mock_fixer(path, context):
            call_count[0] += 1
            return json.dumps({"status": "ok", "message": "fixed"})

        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=mock_fixer,
            max_retries=3,
        )

        # First verification fails, second passes
        results = [(False, "error output"), (True, "ok")]
        with patch.object(loop, "_run_verification", side_effect=results):
            result = loop.run()
        assert result["status"] == "success"
        assert "Fixed in 1 attempts" in result["message"]
        assert call_count[0] == 1

    def test_run_all_retries_fail(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("broken code")

        def mock_fixer(path, context):
            return json.dumps({"status": "ok"})

        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=mock_fixer,
            max_retries=2,
        )

        # All verifications fail
        with patch.object(loop, "_run_verification", return_value=(False, "always fails")):
            result = loop.run()
        assert result["status"] == "failure"
        assert "Failed to fix after 2 attempts" in result["message"]
        assert result["last_output"] == "always fails"

    def test_run_fixer_returns_error_status(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("broken")

        def mock_fixer(path, context):
            return json.dumps({"status": "error", "message": "can't fix"})

        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=mock_fixer,
            max_retries=1,
        )

        results = [(False, "error"), (True, "ok")]
        with patch.object(loop, "_run_verification", side_effect=results):
            result = loop.run()
        assert result["status"] == "success"

    def test_run_fixer_raises_exception(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("broken")

        def mock_fixer(path, context):
            raise RuntimeError("fixer crashed")

        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=mock_fixer,
            max_retries=1,
        )

        results = [(False, "error"), (True, "ok")]
        with patch.object(loop, "_run_verification", side_effect=results):
            result = loop.run()
        assert result["status"] == "success"

    def test_run_fixer_returns_invalid_json(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("broken")

        def mock_fixer(path, context):
            return "not json"

        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=mock_fixer,
            max_retries=1,
        )

        results = [(False, "error"), (True, "ok")]
        with patch.object(loop, "_run_verification", side_effect=results):
            result = loop.run()
        assert result["status"] == "success"

    def test_log_appends_to_logs(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        loop._log("test message")
        assert len(loop.logs) == 1
        assert "test message" in loop.logs[0]
        assert "[" in loop.logs[0]  # timestamp prefix

    def test_run_verification_success(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        success, output = loop._run_verification()
        assert success is True
        assert isinstance(output, str)

    def test_run_verification_failure(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'raise SystemExit(1)'",
            fixer_func=lambda p, c: '{}',
        )
        success, output = loop._run_verification()
        assert success is False

    def test_run_verification_timeout(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'import time; time.sleep(120)'",
            fixer_func=lambda p, c: '{}',
        )
        with patch("mcp_server_nucleus.runtime.loops.fixer.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(cmd="test", timeout=60)):
            success, output = loop._run_verification()
        assert success is False
        assert "timed out" in output.lower()

    def test_run_verification_exception(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command="",  # Empty command
            fixer_func=lambda p, c: '{}',
        )
        # Empty shlex.split returns empty list, subprocess.run with empty list raises
        success, output = loop._run_verification()
        assert success is False
        assert "failed to run" in output.lower()

    def test_max_retries_default(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        assert loop.max_retries == 3

    def test_logs_included_in_result(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("print('hello')")
        loop = FixerLoop(
            target_file=str(target),
            verification_command=f"{sys.executable} -c 'pass'",
            fixer_func=lambda p, c: '{}',
        )
        result = loop.run()
        assert "logs" in result
        assert len(result["logs"]) > 0
