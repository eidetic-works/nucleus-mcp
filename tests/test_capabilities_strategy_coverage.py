"""Comprehensive tests for mcp_server_nucleus.runtime.capabilities.strategy.

Covers StrategyTool: __init__, name, description, get_tools,
_validate_path, execute (read + write), and get_capability.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.capabilities.strategy import (
    StrategyTool,
    get_capability,
)


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    b.mkdir()
    return b


@pytest.fixture
def strategy_dir(brain):
    """Create a strategy directory in brain and return its path."""
    s = brain / "strategy"
    s.mkdir()
    return s


class TestInit:
    def test_init_resolves_paths(self, brain):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        assert tool.brain_path == brain
        assert tool._name == "strategy_ops"
        assert tool._desc == "Read and Evolve Strategic Protocols"
        # Path should be resolved with ${BRAIN_PATH} replaced
        assert tool.allowed_paths[0] == (brain / "strategy").resolve()

    def test_init_multiple_paths(self, brain):
        tool = StrategyTool(
            brain,
            ["${BRAIN_PATH}/strategy", "${BRAIN_PATH}/protocols"],
        )
        assert len(tool.allowed_paths) == 2


class TestProperties:
    def test_name(self, brain):
        tool = StrategyTool(brain, [])
        assert tool.name == "strategy_ops"

    def test_description(self, brain):
        tool = StrategyTool(brain, [])
        assert tool.description == "Read and Evolve Strategic Protocols"


class TestGetTools:
    def test_tools_structure(self, brain):
        tool = StrategyTool(brain, [])
        tools = tool.get_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "read_strategy" in names
        assert "evolve_protocol" in names

    def test_read_tool_params(self, brain):
        tool = StrategyTool(brain, [])
        tools = tool.get_tools()
        read_tool = [t for t in tools if t["name"] == "read_strategy"][0]
        assert "filename" in read_tool["parameters"]["properties"]
        assert "filename" in read_tool["parameters"]["required"]

    def test_evolve_tool_params(self, brain):
        tool = StrategyTool(brain, [])
        tools = tool.get_tools()
        evolve_tool = [t for t in tools if t["name"] == "evolve_protocol"][0]
        props = evolve_tool["parameters"]["properties"]
        assert "filename" in props
        assert "content" in props
        assert "reason" in props
        required = evolve_tool["parameters"]["required"]
        assert "filename" in required
        assert "content" in required
        assert "reason" in required


class TestValidatePath:
    def test_valid_file_in_allowed_dir(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        target = tool._validate_path("strategy/test.md")
        assert target == (brain / "strategy" / "test.md").resolve()

    def test_valid_exact_file_match(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy/SOVEREIGN.md"])
        target = tool._validate_path("strategy/SOVEREIGN.md")
        assert target is not None

    def test_access_denied(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        target = tool._validate_path("secrets/passwords.md")
        assert target is None

    def test_oserror_on_is_dir(self, brain, strategy_dir):
        from unittest.mock import MagicMock
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        # Replace allowed_paths with a mock that raises OSError on is_dir
        mock_path = MagicMock()
        mock_path.is_dir.side_effect = OSError("fail")
        mock_path.__eq__ = lambda self, other: False
        mock_path.__str__ = lambda self: str(brain / "strategy")
        tool.allowed_paths = [mock_path]
        target = tool._validate_path("strategy/test.md")
        assert target is None


class TestExecuteRead:
    def test_read_success(self, brain, strategy_dir):
        (strategy_dir / "test.md").write_text("# Test Strategy")
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({"filename": "strategy/test.md"})
        assert result == "# Test Strategy"

    def test_read_file_not_found(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({"filename": "strategy/nonexistent.md"})
        assert result == "Error: File not found"

    def test_read_access_denied(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({"filename": "secrets/secret.md"})
        assert result == "Error: Access Denied"

    def test_read_no_filename(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        # filename is None, _validate_path(None) raises TypeError
        with pytest.raises(TypeError):
            tool.execute({})


class TestExecuteWrite:
    def test_write_success(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({
            "filename": "strategy/new.md",
            "content": "# New Protocol",
            "reason": "Updated for v2",
        })
        assert "evolved" in result.lower()
        assert (strategy_dir / "new.md").read_text() == "# New Protocol"
        # Check evolution log
        log_path = brain / "decisions" / "evolution_log.jsonl"
        assert log_path.exists()
        log_entry = json.loads(log_path.read_text().strip())
        assert log_entry["file"] == "strategy/new.md"
        assert log_entry["reason"] == "Updated for v2"

    def test_write_access_denied(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({
            "filename": "secrets/secret.md",
            "content": "content",
            "reason": "test",
        })
        assert result == "Error: Access Denied"

    def test_write_to_new_file(self, brain, strategy_dir):
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({
            "filename": "strategy/brand_new.md",
            "content": "# Brand New",
            "reason": "Creating new protocol",
        })
        assert "evolved" in result.lower()
        # len_delta should be 0 for new file (path.exists() is False)
        log_path = brain / "decisions" / "evolution_log.jsonl"
        log_entry = json.loads(log_path.read_text().strip())
        assert log_entry["len_delta"] == len("# Brand New")

    def test_write_overwrite_existing(self, brain, strategy_dir):
        existing = strategy_dir / "existing.md"
        existing.write_text("short")
        tool = StrategyTool(brain, ["${BRAIN_PATH}/strategy"])
        result = tool.execute({
            "filename": "strategy/existing.md",
            "content": "this is much longer content than before",
            "reason": "Expanding protocol",
        })
        assert "evolved" in result.lower()
        log_path = brain / "decisions" / "evolution_log.jsonl"
        log_entry = json.loads(log_path.read_text().strip())
        assert log_entry["len_delta"] == len("this is much longer content than before") - len("short")


class TestGetCapability:
    def test_get_capability_with_paths(self, brain):
        config = {"paths": ["${BRAIN_PATH}/strategy"]}
        tool = get_capability(brain, config)
        assert isinstance(tool, StrategyTool)
        assert len(tool.allowed_paths) == 1

    def test_get_capability_no_paths(self, brain):
        config = {}
        tool = get_capability(brain, config)
        assert isinstance(tool, StrategyTool)
        assert tool.allowed_paths == []
