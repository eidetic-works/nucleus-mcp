"""
Agent Runtime V2 - Enhanced Agent Execution Engine
===================================================
Implements:
- Rate limiting for agent spawning
- Cost tracking per agent execution
- Agent execution dashboard metrics
- Agent timeout/cancellation support

Part of Phase 68: Agent Runtime V2 Enhancement
"""

import os
import json
import time
import threading
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
from enum import Enum

from .rate_limiter import TokenBucket, RateLimitError


# ============================================================
# CONFIGURATION
# ============================================================

BRAIN_PATH = Path(os.environ.get("NUCLEUS_BRAIN_PATH", "./.brain"))

# Agent spawn rate limits
AGENT_SPAWN_CAPACITY = float(os.environ.get("NUCLEUS_AGENT_SPAWN_CAPACITY", "10"))
AGENT_SPAWN_RATE = float(os.environ.get("NUCLEUS_AGENT_SPAWN_RATE", "2"))  # per second

# Agent timeout defaults
DEFAULT_AGENT_TIMEOUT = int(os.environ.get("NUCLEUS_AGENT_TIMEOUT", "300"))  # 5 min

# Cost tracking (token-based pricing model)
COST_PER_INPUT_TOKEN = float(os.environ.get("NUCLEUS_COST_INPUT", "0.000001"))
COST_PER_OUTPUT_TOKEN = float(os.environ.get("NUCLEUS_COST_OUTPUT", "0.000003"))


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class AgentCostRecord:
    """Cost tracking for a single agent execution."""
    agent_id: str
    persona: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    start_time: str = None
    end_time: str = None
    duration_ms: int = 0
    status: str = "pending"
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def estimated_cost_usd(self) -> float:
        return (self.input_tokens * COST_PER_INPUT_TOKEN + 
                self.output_tokens * COST_PER_OUTPUT_TOKEN)
    
    def finalize(self, status: str = "completed"):
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.status = status
        if self.start_time:
            start = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            self.duration_ms = int((end - start).total_seconds() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd
        }


@dataclass
class AgentExecution:
    """Tracks a running agent execution with cancellation support."""
    agent_id: str
    persona: str
    intent: str
    status: AgentStatus = AgentStatus.PENDING
    cost: AgentCostRecord = None
    cancel_event: threading.Event = None
    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT
    created_at: str = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.cost:
            self.cost = AgentCostRecord(
                agent_id=self.agent_id,
                persona=self.persona
            )
        if not self.cancel_event:
            self.cancel_event = threading.Event()
    
    def cancel(self) -> bool:
        """Request cancellation of this agent."""
        if self.status == AgentStatus.RUNNING:
            self.cancel_event.set()
            self.status = AgentStatus.CANCELLED
            self.cost.finalize("cancelled")
            return True
        return False
    
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "persona": self.persona,
            "intent": self.intent,
            "status": self.status.value,
            "cost": self.cost.to_dict() if self.cost else None,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at
        }


# ============================================================
# AGENT SPAWN RATE LIMITER
# ============================================================

class AgentSpawnLimiter:
    """
    Rate limiter specifically for agent spawning.
    Prevents runaway agent creation that could exhaust resources.
    """
    
    def __init__(
        self,
        capacity: float = AGENT_SPAWN_CAPACITY,
        fill_rate: float = AGENT_SPAWN_RATE
    ):
        self._bucket = TokenBucket(capacity, fill_rate)
        self._lock = threading.Lock()
        self._stats = defaultdict(int)
        self._persona_counts = defaultdict(int)
    
    def can_spawn(self, persona: str = "default") -> bool:
        """Check if agent spawn is allowed."""
        with self._lock:
            if self._bucket.consume(1.0):
                self._stats["allowed"] += 1
                self._persona_counts[persona] += 1
                return True
            self._stats["limited"] += 1
            return False
    
    def spawn_or_raise(self, persona: str = "default") -> None:
        """Check spawn limit, raise if exceeded."""
        if not self.can_spawn(persona):
            retry_after = self._bucket.time_until_available(1.0)
            raise RateLimitError(
                retry_after,
                f"Agent spawn rate limit exceeded for persona '{persona}'"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_allowed": self._stats["allowed"],
                "total_limited": self._stats["limited"],
                "tokens_available": self._bucket.tokens,
                "capacity": self._bucket.capacity,
                "fill_rate": self._bucket.fill_rate,
                "spawns_by_persona": dict(self._persona_counts)
            }
    
    def reset(self) -> None:
        with self._lock:
            self._bucket = TokenBucket(self._bucket.capacity, self._bucket.fill_rate)
            self._stats.clear()
            self._persona_counts.clear()


# ============================================================
# COST TRACKER
# ============================================================

class AgentCostTracker:
    """
    Tracks costs across all agent executions.
    Supports aggregation by persona, time period, etc.
    """
    
    def __init__(self, persist_path: Path = None):
        self._records: List[AgentCostRecord] = []
        self._active_records: Dict[str, AgentCostRecord] = {}
        self._lock = threading.Lock()
        self._persist_path = persist_path or (BRAIN_PATH / "metrics" / "agent_costs.jsonl")
        self._totals = {
            "total_executions": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tool_calls": 0,
            "total_cost_usd": 0.0,
            "total_duration_ms": 0
        }
    
    def start_tracking(self, agent_id: str, persona: str) -> AgentCostRecord:
        """Start tracking costs for an agent."""
        record = AgentCostRecord(agent_id=agent_id, persona=persona)
        with self._lock:
            self._active_records[agent_id] = record
        return record
    
    def record_tokens(self, agent_id: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record token usage for an agent."""
        with self._lock:
            if agent_id in self._active_records:
                self._active_records[agent_id].input_tokens += input_tokens
                self._active_records[agent_id].output_tokens += output_tokens
    
    def record_tool_call(self, agent_id: str) -> None:
        """Record a tool call for an agent."""
        with self._lock:
            if agent_id in self._active_records:
                self._active_records[agent_id].tool_calls += 1
    
    def finalize(self, agent_id: str, status: str = "completed") -> Optional[AgentCostRecord]:
        """Finalize cost tracking for an agent."""
        with self._lock:
            if agent_id not in self._active_records:
                return None
            
            record = self._active_records.pop(agent_id)
            record.finalize(status)
            self._records.append(record)
            
            # Update totals
            self._totals["total_executions"] += 1
            self._totals["total_input_tokens"] += record.input_tokens
            self._totals["total_output_tokens"] += record.output_tokens
            self._totals["total_tool_calls"] += record.tool_calls
            self._totals["total_cost_usd"] += record.estimated_cost_usd
            self._totals["total_duration_ms"] += record.duration_ms
            
            # Persist
            self._persist(record)
            
            return record
    
    def _persist(self, record: AgentCostRecord) -> None:
        """Persist record to disk."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary."""
        with self._lock:
            return {
                **self._totals,
                "active_agents": len(self._active_records),
                "avg_cost_per_agent": (
                    self._totals["total_cost_usd"] / self._totals["total_executions"]
                    if self._totals["total_executions"] > 0 else 0
                ),
                "avg_duration_ms": (
                    self._totals["total_duration_ms"] / self._totals["total_executions"]
                    if self._totals["total_executions"] > 0 else 0
                )
            }
    
    def get_by_persona(self) -> Dict[str, Dict[str, Any]]:
        """Get costs aggregated by persona."""
        with self._lock:
            by_persona = defaultdict(lambda: {
                "count": 0, "tokens": 0, "cost": 0.0, "duration_ms": 0
            })
            for record in self._records:
                by_persona[record.persona]["count"] += 1
                by_persona[record.persona]["tokens"] += record.total_tokens
                by_persona[record.persona]["cost"] += record.estimated_cost_usd
                by_persona[record.persona]["duration_ms"] += record.duration_ms
            return dict(by_persona)
    
    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent cost records."""
        with self._lock:
            return [r.to_dict() for r in self._records[-limit:]]


# ============================================================
# AGENT EXECUTION MANAGER
# ============================================================

class AgentExecutionManager:
    """
    Manages all agent executions with:
    - Rate limiting
    - Cost tracking
    - Timeout management
    - Cancellation support
    - Dashboard metrics
    """
    
    def __init__(self):
        self._spawn_limiter = AgentSpawnLimiter()
        self._cost_tracker = AgentCostTracker()
        self._executions: Dict[str, AgentExecution] = {}
        self._lock = threading.Lock()
        self._metrics = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
            "total_errors": 0
        }
    
    def spawn_agent(
        self,
        persona: str,
        intent: str,
        timeout_seconds: int = DEFAULT_AGENT_TIMEOUT
    ) -> AgentExecution:
        """
        Spawn a new agent with rate limiting.
        
        Raises:
            RateLimitError: If spawn rate limit exceeded
        """
        # Check rate limit
        self._spawn_limiter.spawn_or_raise(persona)
        
        # Create execution record
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        execution = AgentExecution(
            agent_id=agent_id,
            persona=persona,
            intent=intent,
            timeout_seconds=timeout_seconds
        )
        
        with self._lock:
            self._executions[agent_id] = execution
            self._metrics["total_spawned"] += 1
        
        # Start cost tracking
        self._cost_tracker.start_tracking(agent_id, persona)
        
        return execution
    
    def start_execution(self, agent_id: str) -> bool:
        """Mark agent as running."""
        with self._lock:
            if agent_id in self._executions:
                self._executions[agent_id].status = AgentStatus.RUNNING
                return True
            return False
    
    def record_tokens(self, agent_id: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record token usage."""
        self._cost_tracker.record_tokens(agent_id, input_tokens, output_tokens)
    
    def record_tool_call(self, agent_id: str) -> None:
        """Record tool call."""
        self._cost_tracker.record_tool_call(agent_id)
    
    def complete_execution(self, agent_id: str, status: str = "completed") -> Optional[AgentCostRecord]:
        """Complete agent execution."""
        cost = self._cost_tracker.finalize(agent_id, status)
        
        with self._lock:
            if agent_id in self._executions:
                execution = self._executions[agent_id]
                execution.status = AgentStatus(status) if status in [s.value for s in AgentStatus] else AgentStatus.COMPLETED
                
                # Update metrics
                if status == "completed":
                    self._metrics["total_completed"] += 1
                elif status == "cancelled":
                    self._metrics["total_cancelled"] += 1
                elif status == "timeout":
                    self._metrics["total_timeout"] += 1
                elif status == "error":
                    self._metrics["total_errors"] += 1
        
        return cost
    
    def cancel_agent(self, agent_id: str) -> bool:
        """Cancel a running agent."""
        with self._lock:
            if agent_id in self._executions:
                execution = self._executions[agent_id]
                if execution.cancel():
                    self._cost_tracker.finalize(agent_id, "cancelled")
                    self._metrics["total_cancelled"] += 1
                    return True
        return False
    
    def is_cancelled(self, agent_id: str) -> bool:
        """Check if agent is cancelled."""
        with self._lock:
            if agent_id in self._executions:
                return self._executions[agent_id].is_cancelled()
        return False
    
    def check_timeout(self, agent_id: str) -> bool:
        """Check if agent has timed out."""
        with self._lock:
            if agent_id not in self._executions:
                return False
            
            execution = self._executions[agent_id]
            if execution.status != AgentStatus.RUNNING:
                return False
            
            created = datetime.fromisoformat(execution.created_at.replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - created).total_seconds()
            
            if elapsed > execution.timeout_seconds:
                execution.status = AgentStatus.TIMEOUT
                execution.cost.finalize("timeout")
                self._metrics["total_timeout"] += 1
                return True
        
        return False
    
    def get_execution(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get execution details."""
        with self._lock:
            if agent_id in self._executions:
                return self._executions[agent_id].to_dict()
        return None
    
    def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get all active executions."""
        with self._lock:
            return [
                e.to_dict() for e in self._executions.values()
                if e.status in [AgentStatus.PENDING, AgentStatus.RUNNING]
            ]
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics."""
        return {
            "spawn_limiter": self._spawn_limiter.get_stats(),
            "cost_summary": self._cost_tracker.get_summary(),
            "cost_by_persona": self._cost_tracker.get_by_persona(),
            "execution_metrics": self._metrics.copy(),
            "active_agents": self.get_active_executions(),
            "recent_costs": self._cost_tracker.get_recent(10)
        }
    
    def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove old completed executions from memory."""
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
        removed = 0
        
        with self._lock:
            to_remove = []
            for agent_id, execution in self._executions.items():
                if execution.status not in [AgentStatus.PENDING, AgentStatus.RUNNING]:
                    created = datetime.fromisoformat(execution.created_at.replace('Z', '+00:00'))
                    if created.timestamp() < cutoff:
                        to_remove.append(agent_id)
            
            for agent_id in to_remove:
                del self._executions[agent_id]
                removed += 1
        
        return removed


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_execution_manager: Optional[AgentExecutionManager] = None


def get_execution_manager() -> AgentExecutionManager:
    """Get or create global execution manager."""
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = AgentExecutionManager()
    return _execution_manager


# ============================================================
# TIMEOUT DECORATOR
# ============================================================

def with_timeout(timeout_seconds: int = DEFAULT_AGENT_TIMEOUT):
    """
    Decorator to add timeout support to async agent functions.
    
    Usage:
        @with_timeout(60)
        async def my_agent_task(agent_id: str):
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            agent_id = kwargs.get('agent_id') or (args[0] if args else None)
            manager = get_execution_manager()
            
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
                return result
            except asyncio.TimeoutError:
                if agent_id:
                    manager.complete_execution(agent_id, "timeout")
                raise TimeoutError(f"Agent execution timed out after {timeout_seconds}s")
        
        return wrapper
    return decorator


# ============================================================
# CANCELLATION CHECKER
# ============================================================

def check_cancellation(agent_id: str) -> None:
    """
    Check if agent should be cancelled and raise if so.
    Call this periodically in long-running agent loops.
    
    Raises:
        InterruptedError: If agent was cancelled
    """
    manager = get_execution_manager()
    if manager.is_cancelled(agent_id):
        raise InterruptedError(f"Agent {agent_id} was cancelled")
    if manager.check_timeout(agent_id):
        raise TimeoutError(f"Agent {agent_id} timed out")
