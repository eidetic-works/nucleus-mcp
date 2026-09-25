"""Comprehensive tests for plugin_loader module."""
import sys
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.plugin_loader import PluginLoader
from mcp_server_nucleus.runtime.budget import BudgetAuditor
from mcp_server_nucleus.runtime.capabilities.base import Capability


@pytest.fixture
def brain_path(tmp_path):
    """Create a temporary brain path with tools dir."""
    bp = tmp_path / ".brain"
    bp.mkdir(parents=True, exist_ok=True)
    (bp / "tools" / "installed").mkdir(parents=True, exist_ok=True)
    return bp


@pytest.fixture
def auditor(brain_path):
    return BudgetAuditor(brain_path)


def make_valid_plugin(path: Path, name: str = "test_tool"):
    """Create a valid plugin file with get_capability()."""
    code = f'''
from mcp_server_nucleus.runtime.capabilities.base import Capability

class TestCap(Capability):
    @property
    def name(self):
        return "{name}"
    
    @property
    def description(self):
        return "Test capability"
    
    def get_tools(self):
        return [{{"name": "test_tool"}}]

def get_capability():
    return TestCap()
'''
    path.write_text(code)


def make_invalid_plugin_no_entry(path: Path):
    """Create a plugin without get_capability()."""
    path.write_text("x = 1\n")


def make_invalid_plugin_wrong_type(path: Path):
    """Create a plugin that returns non-Capability."""
    path.write_text("def get_capability():\n    return 'not a capability'\n")


def make_broken_plugin(path: Path):
    """Create a plugin that raises on import."""
    path.write_text("raise Exception('import error')\n")


class TestPluginLoaderInit:
    def test_init(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        assert loader.brain_path == brain_path
        assert loader.auditor == auditor
        assert loader.installed_tools_dir == brain_path / "tools" / "installed"


class TestLoadAgentTools:
    def test_agent_dir_not_found(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        result = loader.load_agent_tools("nonexistent_agent", ["tool1"])
        assert result == []

    def test_load_valid_plugin(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_valid_plugin(agent_dir / "test_tool.py", "test_tool")
        result = loader.load_agent_tools("agent1", ["test_tool"])
        assert len(result) == 1
        # Should be wrapped in BudgetGuard
        from mcp_server_nucleus.runtime.budget import BudgetGuard
        assert isinstance(result[0], BudgetGuard)

    def test_load_missing_tool_file(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        result = loader.load_agent_tools("agent1", ["nonexistent_tool"])
        assert result == []

    def test_load_plugin_no_entry_point(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_invalid_plugin_no_entry(agent_dir / "no_entry.py")
        result = loader.load_agent_tools("agent1", ["no_entry"])
        assert result == []

    def test_load_plugin_wrong_type(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_invalid_plugin_wrong_type(agent_dir / "wrong_type.py")
        result = loader.load_agent_tools("agent1", ["wrong_type"])
        assert result == []

    def test_load_broken_plugin(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_broken_plugin(agent_dir / "broken.py")
        result = loader.load_agent_tools("agent1", ["broken"])
        assert result == []

    def test_load_multiple_plugins(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_valid_plugin(agent_dir / "tool1.py", "tool1")
        make_valid_plugin(agent_dir / "tool2.py", "tool2")
        result = loader.load_agent_tools("agent1", ["tool1", "tool2"])
        assert len(result) == 2

    def test_load_mixed_valid_invalid(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_valid_plugin(agent_dir / "good.py", "good")
        make_invalid_plugin_no_entry(agent_dir / "bad.py")
        result = loader.load_agent_tools("agent1", ["good", "bad"])
        assert len(result) == 1

    def test_budget_guard_default_zero(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_valid_plugin(agent_dir / "test_tool.py", "test_tool")
        result = loader.load_agent_tools("agent1", ["test_tool"])
        assert result[0].max_budget_usd == 0.0

    def test_empty_authorized_modules(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        result = loader.load_agent_tools("agent1", [])
        assert result == []

    def test_adds_to_sys_path(self, brain_path, auditor):
        loader = PluginLoader(brain_path, auditor)
        agent_dir = brain_path / "tools" / "installed" / "agent1"
        agent_dir.mkdir(parents=True)
        make_valid_plugin(agent_dir / "test_tool.py", "test_tool")
        loader.load_agent_tools("agent1", ["test_tool"])
        assert str(agent_dir) in sys.path
