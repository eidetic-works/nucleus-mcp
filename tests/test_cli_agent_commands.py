"""Tests for v1.4.0 Agent CLI commands (engram, task, session, growth, outbound).

These tests mock the runtime functions to avoid needing a real .brain directory.
They verify that CLI handlers correctly parse args, call runtime, and format output.
"""

import json
import sys
import argparse
import pytest
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.cli import (
    handle_engram_command,
    handle_task_command,
    handle_session_command,
    handle_growth_command,
    handle_outbound_command,
    _setup_agent_env,
    _get_fmt,
)


def _make_args(**kwargs):
    """Create a namespace object simulating parsed CLI args."""
    defaults = {"format": "json", "brain_path": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ════════════════════════════════════════════════════════════════
# _setup_agent_env
# ════════════════════════════════════════════════════════════════

class TestSetupAgentEnv:
    def test_sets_env_when_brain_path_provided(self):
        args = _make_args(brain_path="/tmp/test_brain")
        with patch.dict("os.environ", {}, clear=False):
            _setup_agent_env(args)
            import os
            assert "NUCLEAR_BRAIN_PATH" in os.environ

    def test_noop_when_no_brain_path(self):
        args = _make_args(brain_path=None)
        import os
        original = os.environ.get("NUCLEAR_BRAIN_PATH")
        _setup_agent_env(args)
        assert os.environ.get("NUCLEAR_BRAIN_PATH") == original


# ════════════════════════════════════════════════════════════════
# Engram Commands
# ════════════════════════════════════════════════════════════════

class TestEngramCommand:
    def test_search_success(self, capsys):
        args = _make_args(
            engram_action="search", query="test", limit=10
        )
        mock_response = json.dumps({
            "success": True,
            "data": [
                {"key": "k1", "value": "v1", "context": "Decision", "intensity": 5}
            ]
        })
        with patch("mcp_server_nucleus.cli.handle_engram_command.__module__", "mcp_server_nucleus.cli"):
            with patch("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", return_value=mock_response):
                code = handle_engram_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out.strip())
        assert parsed["key"] == "k1"

    def test_search_error(self, capsys):
        args = _make_args(engram_action="search", query="test", limit=10)
        mock_response = json.dumps({"success": False, "error": "brain not found"})
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_search_engrams_impl", return_value=mock_response):
            code = handle_engram_command(args)
        assert code == 3  # EXIT_NOT_FOUND — semantic exit code for "not found"
        err = capsys.readouterr().err
        assert "brain not found" in err

    def test_write_success(self, capsys):
        args = _make_args(
            engram_action="write", key="test_key", value="test_value",
            context="Decision", intensity=7
        )
        mock_response = json.dumps({"success": True, "data": {"op": "ADD"}})
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_write_engram_impl", return_value=mock_response):
            code = handle_engram_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["key"] == "test_key"
        assert parsed["status"] == "written"

    def test_query_success(self, capsys):
        args = _make_args(
            engram_action="query", context="Strategy", min_intensity=3, limit=5
        )
        mock_response = json.dumps({
            "success": True,
            "data": [
                {"key": "strat1", "value": "go big", "context": "Strategy", "intensity": 8}
            ]
        })
        with patch("mcp_server_nucleus.runtime.engram_ops._brain_query_engrams_impl", return_value=mock_response):
            code = handle_engram_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out.strip())
        assert parsed["key"] == "strat1"

    def test_no_action_returns_error(self, capsys):
        args = _make_args(engram_action=None)
        code = handle_engram_command(args)
        assert code == 1
        err = capsys.readouterr().err
        assert "Usage" in err


# ════════════════════════════════════════════════════════════════
# Task Commands
# ════════════════════════════════════════════════════════════════

class TestTaskCommand:
    def test_list_success(self, capsys):
        args = _make_args(task_action="list", status=None, priority=None)
        mock_data = {
            "tasks": [
                {"task_id": "t1", "description": "do stuff", "status": "READY", "priority": 2}
            ],
            "count": 1
        }
        with patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=mock_data):
            code = handle_task_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out.strip())
        assert parsed["task_id"] == "t1"

    def test_add_success(self, capsys):
        args = _make_args(task_action="add", description="new task", priority=2)
        mock_result = {"success": True, "task": {"task_id": "t-abc123"}}
        with patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value=mock_result):
            code = handle_task_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["task_id"] == "t-abc123"
        assert parsed["status"] == "created"

    def test_add_failure(self, capsys):
        args = _make_args(task_action="add", description="bad task", priority=2)
        mock_result = {"success": False, "error": "duplicate task"}
        with patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value=mock_result):
            code = handle_task_command(args)
        assert code == 1
        err = capsys.readouterr().err
        assert "duplicate task" in err

    def test_update_success(self, capsys):
        args = _make_args(
            task_action="update", task_id="t1",
            status="DONE", priority=None, description=None
        )
        mock_result = {"success": True}
        with patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value=mock_result):
            code = handle_task_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["status"] == "updated"

    def test_update_no_fields(self, capsys):
        args = _make_args(
            task_action="update", task_id="t1",
            status=None, priority=None, description=None
        )
        code = handle_task_command(args)
        assert code == 1
        err = capsys.readouterr().err
        assert "No updates specified" in err

    def test_no_action_returns_error(self, capsys):
        args = _make_args(task_action=None)
        code = handle_task_command(args)
        assert code == 1


# ════════════════════════════════════════════════════════════════
# Session Commands
# ════════════════════════════════════════════════════════════════

class TestSessionCommand:
    def test_save_success(self, capsys):
        args = _make_args(session_action="save", context="working on CLI", task=None)
        mock_result = {"success": True, "session_id": "sess-123"}
        with patch("mcp_server_nucleus.runtime.session_ops._save_session", return_value=mock_result):
            code = handle_session_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["session_id"] == "sess-123"

    def test_save_failure(self, capsys):
        args = _make_args(session_action="save", context="test", task=None)
        mock_result = {"success": False, "error": "disk full"}
        with patch("mcp_server_nucleus.runtime.session_ops._save_session", return_value=mock_result):
            code = handle_session_command(args)
        assert code == 1
        err = capsys.readouterr().err
        assert "disk full" in err

    def test_resume_success(self, capsys):
        args = _make_args(session_action="resume", id=None)
        mock_result = {"session_id": "sess-123", "context": "was working on CLI"}
        with patch("mcp_server_nucleus.runtime.session_ops._resume_session", return_value=mock_result):
            code = handle_session_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["session_id"] == "sess-123"

    def test_resume_not_found(self, capsys):
        args = _make_args(session_action="resume", id="nonexistent")
        with patch("mcp_server_nucleus.runtime.session_ops._resume_session", return_value=None):
            code = handle_session_command(args)
        assert code == 3  # EXIT_NOT_FOUND — semantic exit code for "not found"
        err = capsys.readouterr().err
        assert "No session found" in err

    def test_no_action_returns_error(self, capsys):
        args = _make_args(session_action=None)
        code = handle_session_command(args)
        assert code == 1


# ════════════════════════════════════════════════════════════════
# Growth Commands
# ════════════════════════════════════════════════════════════════

class TestGrowthCommand:
    def test_pulse_success(self, capsys):
        args = _make_args(growth_action="pulse")
        mock_result = {"brief": "Growth pulse ran", "metrics": {"stars": 10}}
        with patch("mcp_server_nucleus.runtime.growth_ops.growth_pulse", return_value=mock_result):
            code = handle_growth_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "brief" in parsed

    def test_status_success(self, capsys):
        args = _make_args(growth_action="status")
        mock_result = {"github": {"stars": 5}, "pypi": {"last_month": 100}}
        with patch("mcp_server_nucleus.runtime.growth_ops.capture_metrics", return_value=mock_result):
            code = handle_growth_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["github"]["stars"] == 5

    def test_no_action_returns_error(self, capsys):
        args = _make_args(growth_action=None)
        code = handle_growth_command(args)
        assert code == 1


# ════════════════════════════════════════════════════════════════
# Outbound Commands
# ════════════════════════════════════════════════════════════════

class TestOutboundCommand:
    def test_check_success(self, capsys):
        args = _make_args(
            outbound_action="check", channel="reddit",
            identifier="r/ClaudeAI", body=""
        )
        mock_result = {"already_posted": False, "can_post": True}
        with patch("mcp_server_nucleus.runtime.outbound_ops.outbound_check", return_value=mock_result):
            code = handle_outbound_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["can_post"] is True

    def test_record_success(self, capsys):
        args = _make_args(
            outbound_action="record", channel="reddit",
            identifier="r/ClaudeAI", body="test post",
            permalink="https://reddit.com/123", workhorse="manual"
        )
        mock_result = {"recorded": True, "engram_key": "outbound_reddit_abc"}
        with patch("mcp_server_nucleus.runtime.outbound_ops.outbound_record", return_value=mock_result):
            code = handle_outbound_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["recorded"] is True

    def test_plan_success(self, capsys):
        args = _make_args(outbound_action="plan", channel=None)
        mock_result = {"ready": [], "already_posted": [], "summary": {"ready_count": 0}}
        with patch("mcp_server_nucleus.runtime.outbound_ops.outbound_plan", return_value=mock_result):
            code = handle_outbound_command(args)
        assert code == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "summary" in parsed

    def test_no_action_returns_error(self, capsys):
        args = _make_args(outbound_action=None)
        code = handle_outbound_command(args)
        assert code == 1
