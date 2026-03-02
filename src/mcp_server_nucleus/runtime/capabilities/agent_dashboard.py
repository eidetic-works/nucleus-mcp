"""
Agent Dashboard Capability - MCP Tools for Agent Runtime V2
============================================================
Provides MCP tools for monitoring and managing agent executions.

Part of Phase 68: Agent Runtime V2 Enhancement
"""

from typing import Dict, Any, List, Optional
from .base import Capability
from ..agent_runtime_v2 import (
    get_execution_manager,
    AgentStatus
)


class AgentDashboardOps(Capability):
    """
    MCP tools for Agent Runtime V2 dashboard and management.
    
    Tools:
    - brain_agent_dashboard: Get comprehensive agent metrics
    - brain_agent_spawn_stats: Get agent spawn rate limiting stats
    - brain_agent_costs: Get cost tracking summary
    - brain_agent_list_active: List active agent executions
    - brain_agent_cancel: Cancel a running agent
    - brain_agent_cleanup: Clean up completed executions
    """
    
    @property
    def name(self) -> str:
        return "agent_dashboard"
    
    @property
    def description(self) -> str:
        return "Agent Runtime V2 dashboard and management tools"
    
    def __init__(self):
        self.manager = get_execution_manager()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "brain_agent_dashboard",
                "description": "Get comprehensive agent execution dashboard with metrics, costs, and active agents",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_agent_spawn_stats",
                "description": "Get agent spawn rate limiting statistics",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_agent_costs",
                "description": "Get agent cost tracking summary with breakdown by persona",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_recent": {
                            "type": "boolean",
                            "description": "Include recent cost records",
                            "default": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent records to include",
                            "default": 10
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "brain_agent_list_active",
                "description": "List all currently active (pending or running) agent executions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "brain_agent_cancel",
                "description": "Cancel a running agent execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to cancel"
                        }
                    },
                    "required": ["agent_id"]
                }
            },
            {
                "name": "brain_agent_cleanup",
                "description": "Clean up old completed agent executions from memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_age_hours": {
                            "type": "integer",
                            "description": "Remove executions older than this many hours",
                            "default": 1
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "brain_agent_get",
                "description": "Get details of a specific agent execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to get details for"
                        }
                    },
                    "required": ["agent_id"]
                }
            }
        ]
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "brain_agent_dashboard":
            return self._get_dashboard()
        elif tool_name == "brain_agent_spawn_stats":
            return self._get_spawn_stats()
        elif tool_name == "brain_agent_costs":
            return self._get_costs(
                include_recent=args.get("include_recent", True),
                limit=args.get("limit", 10)
            )
        elif tool_name == "brain_agent_list_active":
            return self._list_active()
        elif tool_name == "brain_agent_cancel":
            return self._cancel_agent(args["agent_id"])
        elif tool_name == "brain_agent_cleanup":
            return self._cleanup(args.get("max_age_hours", 1))
        elif tool_name == "brain_agent_get":
            return self._get_agent(args["agent_id"])
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _get_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics."""
        return self.manager.get_dashboard_metrics()
    
    def _get_spawn_stats(self) -> Dict[str, Any]:
        """Get spawn rate limiting stats."""
        return self.manager._spawn_limiter.get_stats()
    
    def _get_costs(self, include_recent: bool = True, limit: int = 10) -> Dict[str, Any]:
        """Get cost tracking summary."""
        result = {
            "summary": self.manager._cost_tracker.get_summary(),
            "by_persona": self.manager._cost_tracker.get_by_persona()
        }
        if include_recent:
            result["recent"] = self.manager._cost_tracker.get_recent(limit)
        return result
    
    def _list_active(self) -> List[Dict[str, Any]]:
        """List active executions."""
        return self.manager.get_active_executions()
    
    def _cancel_agent(self, agent_id: str) -> Dict[str, Any]:
        """Cancel an agent."""
        success = self.manager.cancel_agent(agent_id)
        return {
            "agent_id": agent_id,
            "cancelled": success,
            "message": "Agent cancelled successfully" if success else "Agent not found or not running"
        }
    
    def _cleanup(self, max_age_hours: int = 1) -> Dict[str, Any]:
        """Clean up old executions."""
        removed = self.manager.cleanup_completed(max_age_seconds=max_age_hours * 3600)
        return {
            "removed": removed,
            "max_age_hours": max_age_hours
        }
    
    def _get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent details."""
        execution = self.manager.get_execution(agent_id)
        if execution:
            return execution
        return {"error": f"Agent {agent_id} not found"}
