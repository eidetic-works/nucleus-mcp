"""
Coverage tests for runtime/capabilities/depth_tracker.py
"""
import os
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime.capabilities.depth_tracker import DepthTracker


@pytest.fixture
def depth_tracker(monkeypatch, tmp_path):
    """Create DepthTracker with a temp brain path."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "session").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return DepthTracker()


# ---------------------------------------------------------------------------
# Properties & Init
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, depth_tracker):
        assert depth_tracker.name == "depth_tracker"

    def test_description(self, depth_tracker):
        assert "depth" in depth_tracker.description.lower()

    def test_init_does_not_pin_the_process_brain_path(self, monkeypatch, tmp_path):
        """DS-8: the constructor used to write NUCLEUS_BRAIN_PATH=".brain".

        Three things were wrong with that. The value is relative, so it named no
        particular brain. It is process-wide, written from a constructor built
        per request on a long-lived server, so the first request arriving without
        a brain pinned every request after it. And it short-circuited
        get_brain_path()'s own resolution order, which answers the same question
        properly. Nothing needed it: depth_ops calls get_brain_path() itself.
        """
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        DepthTracker()
        assert "NUCLEUS_BRAIN_PATH" not in os.environ, (
            "constructing a DepthTracker wrote a process-wide brain path again; "
            "on a long-lived server that pins every later request"
        )


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_four_tools(self, depth_tracker):
        tools = depth_tracker.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_depth_push" in names
        assert "brain_depth_pop" in names
        assert "brain_depth_show" in names
        assert "brain_depth_reset" in names

    def test_push_required(self, depth_tracker):
        tools = depth_tracker.get_tools()
        tool = [t for t in tools if t["name"] == "brain_depth_push"][0]
        assert tool["parameters"]["required"] == ["topic"]


# ---------------------------------------------------------------------------
# execute_tool - brain_depth_push
# ---------------------------------------------------------------------------
class TestDepthPush:
    def test_push_success(self, depth_tracker, monkeypatch):
        mock_push = MagicMock(return_value={
            "current_depth": 1,
            "topic": "subtopic",
            "warning": None,
            "indicator": "[█░░░░]"
        })
        monkeypatch.setattr("mcp_server_nucleus._depth_push", mock_push)
        result = depth_tracker.execute_tool("brain_depth_push", {"topic": "subtopic"})
        assert "Level 1" in result
        assert "subtopic" in result

    def test_push_with_warning(self, depth_tracker, monkeypatch):
        mock_push = MagicMock(return_value={
            "current_depth": 5,
            "topic": "deep",
            "warning": "RABBIT HOLE!",
            "indicator": "[█████]"
        })
        monkeypatch.setattr("mcp_server_nucleus._depth_push", mock_push)
        result = depth_tracker.execute_tool("brain_depth_push", {"topic": "deep"})
        assert "RABBIT HOLE" in result

    def test_push_error(self, depth_tracker, monkeypatch):
        mock_push = MagicMock(return_value={"error": "Max depth exceeded"})
        monkeypatch.setattr("mcp_server_nucleus._depth_push", mock_push)
        result = depth_tracker.execute_tool("brain_depth_push", {"topic": "x"})
        assert "Error" in result
        assert "Max depth exceeded" in result

    def test_push_none_topic(self, depth_tracker, monkeypatch):
        mock_push = MagicMock(return_value={"error": "topic required"})
        monkeypatch.setattr("mcp_server_nucleus._depth_push", mock_push)
        result = depth_tracker.execute_tool("brain_depth_push", {"topic": None})
        assert "Error" in result


# ---------------------------------------------------------------------------
# execute_tool - brain_depth_pop
# ---------------------------------------------------------------------------
class TestDepthPop:
    def test_pop_success(self, depth_tracker, monkeypatch):
        mock_pop = MagicMock(return_value={
            "message": "Resurfaced to root",
            "indicator": "[░░░░░]"
        })
        monkeypatch.setattr("mcp_server_nucleus._depth_pop", mock_pop)
        result = depth_tracker.execute_tool("brain_depth_pop", {})
        assert "Resurfaced" in result

    def test_pop_error(self, depth_tracker, monkeypatch):
        mock_pop = MagicMock(return_value={"error": "Already at root"})
        monkeypatch.setattr("mcp_server_nucleus._depth_pop", mock_pop)
        result = depth_tracker.execute_tool("brain_depth_pop", {})
        assert "Error" in result
        assert "Already at root" in result


# ---------------------------------------------------------------------------
# execute_tool - brain_depth_show
# ---------------------------------------------------------------------------
class TestDepthShow:
    def test_show_success(self, depth_tracker, monkeypatch):
        mock_show = MagicMock(return_value={
            "indicator": "[█░░░░]",
            "status": "🟢 SAFE",
            "breadcrumbs": "root → subtopic",
            "tree": "0: root\n1: subtopic"
        })
        monkeypatch.setattr("mcp_server_nucleus._depth_show", mock_show)
        result = depth_tracker.execute_tool("brain_depth_show", {})
        assert "🟢 SAFE" in result
        assert "root → subtopic" in result

    def test_show_error(self, depth_tracker, monkeypatch):
        mock_show = MagicMock(return_value={"error": "State corrupted"})
        monkeypatch.setattr("mcp_server_nucleus._depth_show", mock_show)
        result = depth_tracker.execute_tool("brain_depth_show", {})
        assert "Error" in result


# ---------------------------------------------------------------------------
# execute_tool - brain_depth_reset
# ---------------------------------------------------------------------------
class TestDepthReset:
    def test_reset_success(self, depth_tracker, monkeypatch):
        mock_reset = MagicMock(return_value={"message": "Depth reset to root."})
        monkeypatch.setattr("mcp_server_nucleus._depth_reset", mock_reset)
        result = depth_tracker.execute_tool("brain_depth_reset", {})
        assert "Depth reset" in result

    def test_reset_error(self, depth_tracker, monkeypatch):
        mock_reset = MagicMock(return_value={"error": "Cannot reset"})
        monkeypatch.setattr("mcp_server_nucleus._depth_reset", mock_reset)
        result = depth_tracker.execute_tool("brain_depth_reset", {})
        assert "Error" in result

    def test_reset_no_message(self, depth_tracker, monkeypatch):
        mock_reset = MagicMock(return_value={})
        monkeypatch.setattr("mcp_server_nucleus._depth_reset", mock_reset)
        result = depth_tracker.execute_tool("brain_depth_reset", {})
        assert "Reset complete" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------
class TestUnknownTool:
    def test_unknown_tool(self, depth_tracker):
        result = depth_tracker.execute_tool("nonexistent", {})
        assert "not found" in result
