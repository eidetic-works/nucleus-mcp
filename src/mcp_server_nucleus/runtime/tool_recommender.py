"""
Tool Recommender - Context-Aware Tool Discovery
=================================================
Phase 72: Autonomous Tool Discovery

Solves: "Why do I need to remember 160 tools?"
Answer: You don't. The system recommends the right tools automatically.

Instead of showing ALL 152+ tools to the LLM (causing cognitive overload),
this module recommends only the relevant tools for each request.

Uses:
1. Enhanced tool metadata (when_to_use, examples, categories)
2. Keyword matching for fast recommendation
3. Usage frequency tracking
4. LLM-based recommendation (optional, for complex cases)
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("nucleus.tool_recommender")

# Phase 73: Resilience imports (lazy)
def _get_file_ops():
    from .file_resilience import get_resilient_file_ops
    return get_resilient_file_ops()

# ============================================================
# TOOL METADATA REGISTRY
# ============================================================
# Enhanced metadata for each tool category.
# This is the "self-describing" layer that makes tools discoverable.

TOOL_CATEGORIES = {
    "task_management": {
        "description": "Creating, listing, and managing tasks (via nucleus_tasks facade)",
        "keywords": ["task", "todo", "add", "create", "list", "pending", "assign", "claim", "complete"],
        "tools": ["nucleus_tasks"]
    },
    "memory": {
        "description": "Writing and querying long-term memory engrams (via nucleus_engrams facade)",
        "keywords": ["remember", "memory", "engram", "recall", "learn", "pattern", "forget", "note"],
        "tools": ["nucleus_engrams"]
    },
    "agent_operations": {
        "description": "Spawning, monitoring, and managing agents (via nucleus_agents facade)",
        "keywords": ["agent", "spawn", "swarm", "mission", "cancel", "active", "dashboard"],
        "tools": ["nucleus_agents"]
    },
    "budget": {
        "description": "Monitoring and managing execution costs (via nucleus_telemetry facade)",
        "keywords": ["budget", "cost", "spend", "spent", "money", "dollar", "expense", "threshold", "limit"],
        "tools": ["nucleus_telemetry"]
    },
    "deployment": {
        "description": "Deploying and monitoring services (via nucleus_infra facade)",
        "keywords": ["deploy", "release", "ship", "smoke", "test", "production", "staging", "rollback"],
        "tools": ["nucleus_infra"]
    },
    "session": {
        "description": "Saving and restoring work sessions (via nucleus_sessions facade)",
        "keywords": ["checkpoint", "save", "resume", "session", "handoff", "restore", "progress"],
        "tools": ["nucleus_sessions"]
    },
    "system_health": {
        "description": "Monitoring system health and status (via nucleus_engrams + nucleus_governance)",
        "keywords": ["health", "status", "alive", "check", "monitor", "uptime", "diagnostic"],
        "tools": ["nucleus_engrams", "nucleus_governance"]
    },
    "code_operations": {
        "description": "Code critique and fixes (via nucleus_agents facade)",
        "keywords": ["code", "search", "analyze", "refactor", "fix", "bug", "lint", "review"],
        "tools": ["nucleus_agents"]
    },
    "orchestration": {
        "description": "Core orchestration: satellite view, loops, commitments, metrics",
        "keywords": ["orchestrate", "satellite", "loop", "commitment", "metrics", "performance"],
        "tools": ["nucleus_orchestration"]
    },
    "infrastructure": {
        "description": "Managing infrastructure, mounts, and servers (via nucleus_features facade)",
        "keywords": ["mount", "server", "infrastructure", "connect", "curl", "pip", "install"],
        "tools": ["nucleus_features"]
    },
    "governance": {
        "description": "Locking resources, audit logs, and governance (via nucleus_governance facade)",
        "keywords": ["lock", "audit", "governance", "security", "permission", "protect", "watch"],
        "tools": ["nucleus_governance"]
    },
    "feature_management": {
        "description": "Tracking and managing product features (via nucleus_features facade)",
        "keywords": ["feature", "roadmap", "backlog", "priority", "milestone", "release"],
        "tools": ["nucleus_features"]
    },
    "depth_tracking": {
        "description": "Managing conversation depth and focus (via nucleus_tasks facade)",
        "keywords": ["depth", "focus", "rabbit", "hole", "scope", "level", "push", "pop"],
        "tools": ["nucleus_tasks"]
    },
    "sync": {
        "description": "Multi-agent sync and artifact management (via nucleus_sync facade)",
        "keywords": ["sync", "artifact", "agent", "identify", "resolve", "conflict"],
        "tools": ["nucleus_sync"]
    },
    "federation": {
        "description": "Federation: multi-brain networking (via nucleus_federation facade)",
        "keywords": ["federation", "peer", "join", "leave", "route", "network"],
        "tools": ["nucleus_federation"]
    },
    "slots": {
        "description": "Slot management, missions, and sprints (via nucleus_slots facade)",
        "keywords": ["slot", "sprint", "autopilot", "mission", "halt"],
        "tools": ["nucleus_slots"]
    },
    "god_combos": {
        "description": "Multi-tool automation pipelines: pulse_and_polish, self_healing_sre, fusion_reactor (via nucleus_engrams)",
        "keywords": ["combo", "pipeline", "automate", "pulse", "polish", "sre", "heal", "fusion", "reactor", "diagnosis"],
        "tools": ["nucleus_engrams"]
    },
    "context_graph": {
        "description": "Engram relationship visualization: context_graph, engram_neighbors, render_graph (via nucleus_engrams)",
        "keywords": ["graph", "relationship", "neighbor", "cluster", "edge", "visualize", "ascii", "density", "connected"],
        "tools": ["nucleus_engrams"]
    },
    "billing": {
        "description": "Usage cost tracking from audit logs: billing_summary (via nucleus_engrams)",
        "keywords": ["billing", "usage", "cost", "tier", "unit", "charge", "pricing", "invoice", "spend"],
        "tools": ["nucleus_engrams"]
    }
}


class ToolRecommendation:
    """A recommendation of tools relevant to a request."""
    
    def __init__(self, recommended_tools: List[str], categories_matched: List[str],
                 confidence: float, reasoning: str):
        self.recommended_tools = recommended_tools
        self.categories_matched = categories_matched
        self.confidence = confidence
        self.reasoning = reasoning
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_tools": self.recommended_tools,
            "categories_matched": self.categories_matched,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "tool_count": len(self.recommended_tools)
        }


class ToolRecommender:
    """
    Recommends relevant tools for a given request.
    
    Instead of showing ALL 152+ tools (overwhelming the LLM),
    this recommends only the 10-20 most relevant tools.
    
    Uses:
    1. Category-keyword matching (fast, no LLM needed)
    2. Usage frequency tracking (learn from past usage)
    3. Always includes "essential" tools (health, tasks)
    """
    
    # Facade tools that should ALWAYS be recommended
    ESSENTIAL_TOOLS = {"nucleus_tasks", "nucleus_engrams", "nucleus_governance"}
    
    def __init__(self):
        self._usage_counts: Dict[str, int] = {}
        self._usage_path = Path(
            os.getenv("NUCLEUS_BRAIN_PATH", "./.brain")
        ) / "metrics" / "tool_usage.json"
        self._load_usage()
    
    def _load_usage(self):
        """Load tool usage data from disk (Phase 73: resilient read)."""
        try:
            data = _get_file_ops().read_json(self._usage_path, default={})
            if isinstance(data, dict):
                self._usage_counts = data
        except Exception:
            pass
    
    def _save_usage(self):
        """Save tool usage data to disk (Phase 73: atomic write)."""
        _get_file_ops().write_json(self._usage_path, self._usage_counts)
    
    def record_usage(self, tool_name: str):
        """Record that a tool was used (for frequency tracking)."""
        self._usage_counts[tool_name] = self._usage_counts.get(tool_name, 0) + 1
        # Periodic save (every 10 uses)
        total = sum(self._usage_counts.values())
        if total % 10 == 0:
            self._save_usage()
    
    def recommend(self, user_request: str, available_tools: List[Dict[str, Any]],
                  max_tools: int = 25) -> ToolRecommendation:
        """
        Recommend relevant tools for a user request.
        
        Args:
            user_request: The user's request
            available_tools: All available MCP tools
            max_tools: Maximum tools to recommend
            
        Returns:
            ToolRecommendation with relevant tools
        """
        if not user_request:
            return ToolRecommendation([], [], 0.0, "Empty request")
        
        request_lower = user_request.lower()
        available_names = {t["name"] for t in available_tools}
        
        matched_tools: Set[str] = set()
        matched_categories: List[str] = []
        
        # Step 1: Category-keyword matching
        for category_name, category in TOOL_CATEGORIES.items():
            keywords = category["keywords"]
            if any(kw in request_lower for kw in keywords):
                matched_categories.append(category_name)
                for tool in category["tools"]:
                    if tool in available_names:
                        matched_tools.add(tool)
        
        # Step 2: Always include essential tools
        for tool in self.ESSENTIAL_TOOLS:
            if tool in available_names:
                matched_tools.add(tool)
        
        # Step 3: Add frequently used tools (top 5 by usage)
        if self._usage_counts:
            sorted_usage = sorted(
                self._usage_counts.items(), key=lambda x: -x[1]
            )
            for tool_name, _ in sorted_usage[:5]:
                if tool_name in available_names:
                    matched_tools.add(tool_name)
        
        # Step 4: Cap at max_tools
        recommended = list(matched_tools)[:max_tools]
        
        # Calculate confidence
        if matched_categories:
            confidence = min(0.9, 0.5 + 0.1 * len(matched_categories))
        else:
            confidence = 0.3  # Low confidence if only essential tools matched
        
        reasoning = (
            f"Matched categories: {matched_categories}" if matched_categories
            else "No categories matched; showing essential tools only"
        )
        
        return ToolRecommendation(
            recommended_tools=recommended,
            categories_matched=matched_categories,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def filter_tools(self, user_request: str, 
                     available_tools: List[Dict[str, Any]],
                     max_tools: int = 25) -> List[Dict[str, Any]]:
        """
        Filter available tools to only the recommended ones.
        
        Returns full tool definitions (not just names) for injection
        into the agent's system prompt.
        """
        recommendation = self.recommend(user_request, available_tools, max_tools)
        recommended_names = set(recommendation.recommended_tools)
        
        return [t for t in available_tools if t["name"] in recommended_names]
    
    def get_category_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the category a tool belongs to."""
        for cat_name, cat in TOOL_CATEGORIES.items():
            if tool_name in cat["tools"]:
                return cat_name
        return None
    
    def get_all_categories(self) -> Dict[str, Any]:
        """Get all tool categories with descriptions."""
        return {
            name: {
                "description": cat["description"],
                "tool_count": len(cat["tools"]),
                "tools": cat["tools"]
            }
            for name, cat in TOOL_CATEGORIES.items()
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        total = sum(self._usage_counts.values())
        top_tools = sorted(self._usage_counts.items(), key=lambda x: -x[1])[:10]
        return {
            "total_tool_calls": total,
            "unique_tools_used": len(self._usage_counts),
            "top_10_tools": dict(top_tools),
            "total_categories": len(TOOL_CATEGORIES),
            "total_cataloged_tools": sum(len(c["tools"]) for c in TOOL_CATEGORIES.values())
        }


# Singleton
_recommender_instance: Optional[ToolRecommender] = None

def get_tool_recommender() -> ToolRecommender:
    """Get singleton tool recommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = ToolRecommender()
    return _recommender_instance
