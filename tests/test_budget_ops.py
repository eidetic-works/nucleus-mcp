"""
Tests for Budget Operations Capability
"""

import pytest
from mcp_server_nucleus.runtime.capabilities.budget_ops import BudgetOps


class TestBudgetOps:
    """Tests for BudgetOps capability."""
    
    @pytest.fixture
    def ops(self):
        return BudgetOps()
    
    def test_get_tools(self, ops):
        tools = ops.get_tools()
        assert len(tools) == 5
        tool_names = [t["name"] for t in tools]
        assert "brain_budget_status" in tool_names
        assert "brain_budget_set_daily" in tool_names
        assert "brain_budget_set_hourly" in tool_names
        assert "brain_budget_set_per_agent" in tool_names
        assert "brain_budget_reset_counters" in tool_names
    
    def test_get_status(self, ops):
        result = ops.execute("brain_budget_status", {})
        assert "daily" in result
        assert "hourly" in result
        assert "per_agent_limit_usd" in result
    
    def test_set_daily(self, ops):
        result = ops.execute("brain_budget_set_daily", {"amount_usd": 25.0})
        assert result["success"] is True
        assert result["daily_budget_usd"] == 25.0
        
        # Verify it's set
        status = ops.execute("brain_budget_status", {})
        assert status["daily"]["budget_usd"] == 25.0
    
    def test_set_hourly(self, ops):
        result = ops.execute("brain_budget_set_hourly", {"amount_usd": 5.0})
        assert result["success"] is True
        assert result["hourly_budget_usd"] == 5.0
    
    def test_set_per_agent(self, ops):
        result = ops.execute("brain_budget_set_per_agent", {"amount_usd": 1.0})
        assert result["success"] is True
        assert result["per_agent_budget_usd"] == 1.0
    
    def test_reset_counters(self, ops):
        # Record some spend
        ops.monitor.record_spend(1.0)
        
        # Reset
        result = ops.execute("brain_budget_reset_counters", {"reset_type": "all"})
        assert result["success"] is True
        assert result["status"]["hourly"]["spent_usd"] == 0.0
        assert result["status"]["daily"]["spent_usd"] == 0.0
    
    def test_reset_hourly_only(self, ops):
        ops.monitor.record_spend(1.0)
        
        result = ops.execute("brain_budget_reset_counters", {"reset_type": "hourly"})
        assert result["success"] is True
        assert result["status"]["hourly"]["spent_usd"] == 0.0
    
    def test_unknown_tool(self, ops):
        result = ops.execute("brain_unknown_tool", {})
        assert "error" in result
