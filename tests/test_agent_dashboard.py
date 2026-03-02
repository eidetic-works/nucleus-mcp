"""
Tests for Agent Dashboard Capability
"""

import pytest
from mcp_server_nucleus.runtime.capabilities.agent_dashboard import AgentDashboardOps
from mcp_server_nucleus.runtime.agent_runtime_v2 import (
    AgentExecutionManager,
    get_execution_manager
)


class TestAgentDashboardOps:
    """Tests for AgentDashboardOps capability."""
    
    @pytest.fixture
    def ops(self):
        return AgentDashboardOps()
    
    def test_get_tools(self, ops):
        tools = ops.get_tools()
        assert len(tools) == 7
        tool_names = [t["name"] for t in tools]
        assert "brain_agent_dashboard" in tool_names
        assert "brain_agent_spawn_stats" in tool_names
        assert "brain_agent_costs" in tool_names
        assert "brain_agent_list_active" in tool_names
        assert "brain_agent_cancel" in tool_names
        assert "brain_agent_cleanup" in tool_names
        assert "brain_agent_get" in tool_names
    
    def test_dashboard(self, ops):
        result = ops.execute("brain_agent_dashboard", {})
        assert "spawn_limiter" in result
        assert "cost_summary" in result
        assert "execution_metrics" in result
    
    def test_spawn_stats(self, ops):
        result = ops.execute("brain_agent_spawn_stats", {})
        assert "total_allowed" in result
        assert "capacity" in result
    
    def test_costs(self, ops):
        result = ops.execute("brain_agent_costs", {"include_recent": True, "limit": 5})
        assert "summary" in result
        assert "by_persona" in result
    
    def test_list_active(self, ops):
        result = ops.execute("brain_agent_list_active", {})
        assert isinstance(result, list)
    
    def test_cancel_nonexistent(self, ops):
        result = ops.execute("brain_agent_cancel", {"agent_id": "nonexistent"})
        assert result["cancelled"] is False
    
    def test_cleanup(self, ops):
        result = ops.execute("brain_agent_cleanup", {"max_age_hours": 1})
        assert "removed" in result
    
    def test_get_nonexistent(self, ops):
        result = ops.execute("brain_agent_get", {"agent_id": "nonexistent"})
        assert "error" in result
    
    def test_full_lifecycle(self, ops):
        # Spawn an agent via the manager
        manager = get_execution_manager()
        execution = manager.spawn_agent("test_persona", "test intent")
        agent_id = execution.agent_id
        
        # Get it via the capability
        result = ops.execute("brain_agent_get", {"agent_id": agent_id})
        assert result["agent_id"] == agent_id
        assert result["persona"] == "test_persona"
        
        # Start it
        manager.start_execution(agent_id)
        
        # List active
        active = ops.execute("brain_agent_list_active", {})
        assert any(a["agent_id"] == agent_id for a in active)
        
        # Cancel it
        cancel_result = ops.execute("brain_agent_cancel", {"agent_id": agent_id})
        assert cancel_result["cancelled"] is True
        
        # Verify cancelled
        result = ops.execute("brain_agent_get", {"agent_id": agent_id})
        assert result["status"] == "cancelled"
