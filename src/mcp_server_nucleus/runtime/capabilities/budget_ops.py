"""
Budget Operations Capability - MCP Tools for Budget Monitoring
===============================================================
Provides MCP tools for monitoring and managing agent execution budgets.

Part of Phase 68: Agent Runtime V2 Enhancement
"""

from typing import Dict, Any, List
from .base import Capability
from ..budget_alerts import get_budget_monitor


class BudgetOps(Capability):
    """
    MCP tools for budget monitoring and alerts.
    
    Tools:
    - brain_budget_status: Get current budget status
    - brain_budget_set_thresholds: Set budget thresholds
    - brain_budget_reset: Reset spend counters
    """
    
    @property
    def name(self) -> str:
        return "budget_ops"
    
    @property
    def description(self) -> str:
        return "Budget monitoring and cost threshold management"
    
    def __init__(self):
        self.monitor = get_budget_monitor()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_budget_status",
                "description": "Get current budget status including daily, hourly, and per-agent limits",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_budget_set_daily",
                "description": "Set the daily budget threshold in USD",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount_usd": {
                            "type": "number",
                            "description": "Daily budget in USD"
                        }
                    },
                    "required": ["amount_usd"]
                }
            },
            {
                "name": "brain_budget_set_hourly",
                "description": "Set the hourly budget threshold in USD",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount_usd": {
                            "type": "number",
                            "description": "Hourly budget in USD"
                        }
                    },
                    "required": ["amount_usd"]
                }
            },
            {
                "name": "brain_budget_set_per_agent",
                "description": "Set the per-agent budget threshold in USD",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount_usd": {
                            "type": "number",
                            "description": "Per-agent budget in USD"
                        }
                    },
                    "required": ["amount_usd"]
                }
            },
            {
                "name": "brain_budget_reset_counters",
                "description": "Reset the hourly and daily spend counters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reset_type": {
                            "type": "string",
                            "enum": ["hourly", "daily", "all"],
                            "description": "Which counters to reset",
                            "default": "all"
                        }
                    },
                    "required": []
                }
            }
        ]
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "brain_budget_status":
            return self._get_status()
        elif tool_name == "brain_budget_set_daily":
            return self._set_daily(args["amount_usd"])
        elif tool_name == "brain_budget_set_hourly":
            return self._set_hourly(args["amount_usd"])
        elif tool_name == "brain_budget_set_per_agent":
            return self._set_per_agent(args["amount_usd"])
        elif tool_name == "brain_budget_reset_counters":
            return self._reset_counters(args.get("reset_type", "all"))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _get_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return self.monitor.get_status()
    
    def _set_daily(self, amount_usd: float) -> Dict[str, Any]:
        """Set daily budget threshold."""
        old_value = self.monitor.daily_budget_usd
        self.monitor.daily_budget_usd = amount_usd
        return {
            "success": True,
            "daily_budget_usd": amount_usd,
            "previous_value": old_value
        }
    
    def _set_hourly(self, amount_usd: float) -> Dict[str, Any]:
        """Set hourly budget threshold."""
        old_value = self.monitor.hourly_budget_usd
        self.monitor.hourly_budget_usd = amount_usd
        return {
            "success": True,
            "hourly_budget_usd": amount_usd,
            "previous_value": old_value
        }
    
    def _set_per_agent(self, amount_usd: float) -> Dict[str, Any]:
        """Set per-agent budget threshold."""
        old_value = self.monitor.per_agent_budget_usd
        self.monitor.per_agent_budget_usd = amount_usd
        return {
            "success": True,
            "per_agent_budget_usd": amount_usd,
            "previous_value": old_value
        }
    
    def _reset_counters(self, reset_type: str = "all") -> Dict[str, Any]:
        """Reset spend counters."""
        from datetime import datetime, timezone
        
        if reset_type in ["hourly", "all"]:
            self.monitor._hourly_spend = 0.0
            self.monitor._last_hourly_reset = datetime.now(timezone.utc)
        
        if reset_type in ["daily", "all"]:
            self.monitor._daily_spend = 0.0
            self.monitor._last_daily_reset = datetime.now(timezone.utc)
        
        # Clear sent alerts
        self.monitor._alerts_sent.clear()
        
        return {
            "success": True,
            "reset_type": reset_type,
            "status": self.monitor.get_status()
        }
