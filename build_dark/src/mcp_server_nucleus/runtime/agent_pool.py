"""
AgentPool - Multi-Agent Orchestration Layer
Manages agent lifecycle, reset cycles, exhaustion handling, and task reassignment.

Path A: Agent Registry + Lifecycle State Machine
- Spawned → Available → Busy → Exhausted → Respawning
- Reset cycle tracking (Gemini 5h, Opus unlimited)
- Graceful exhaustion with checkpointing
- Auto-reassignment of tasks
- Thread-safe for concurrent operations

Scales: 1 → 100 → 1000 agents (same code, same API)

Author: NOP V3.1 - January 2026
"""

import time
import threading
from typing import Dict, List, Optional, Set, Callable
from collections import defaultdict
from enum import Enum


class AgentStatus(str, Enum):
    """Agent lifecycle states."""
    SPAWNING = "SPAWNING"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    EXHAUSTED = "EXHAUSTED"
    RESPAWNING = "RESPAWNING"
    OFFLINE = "OFFLINE"


class ExhaustionReason(str, Enum):
    """Reasons for agent exhaustion."""
    RESET_CYCLE = "reset_cycle"
    RATE_LIMIT = "rate_limit"
    ERROR = "error"
    MANUAL = "manual"


class TaskTier(str, Enum):
    """Task difficulty tiers."""
    T1_PLANNING = "T1_PLANNING"
    T2_CODE = "T2_CODE"
    T3_REVIEW = "T3_REVIEW"
    T4_DEPLOY = "T4_DEPLOY"


# Model configurations with reset cycles
MODEL_CONFIGS = {
    "gemini_3_pro_high": {"reset_hours": 5, "cost_per_1k": 0.00125},
    "gemini_3_pro_low": {"reset_hours": 5, "cost_per_1k": 0.000625},
    "claude_opus_4_5": {"reset_hours": None, "cost_per_1k": 0.015},
    "claude_sonnet_4": {"reset_hours": None, "cost_per_1k": 0.003},
    "gpt_4o": {"reset_hours": None, "cost_per_1k": 0.005},
    "codex_5_1_max": {"reset_hours": 24, "cost_per_1k": 0.01},
}


class ExhaustionRecord:
    """Record of an agent exhaustion event."""

    def __init__(
        self,
        reason: str,
        tasks_affected: List[str],
        was_graceful: bool = True,
    ):
        self.timestamp = int(time.time() * 1000)
        self.reason = reason
        self.tasks_affected = tasks_affected
        self.recovery_time_seconds = 0
        self.was_graceful = was_graceful

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "reason": self.reason,
            "tasks_affected": self.tasks_affected,
            "recovery_time_seconds": self.recovery_time_seconds,
            "was_graceful": self.was_graceful,
        }


class Agent:
    """Represents a single agent in the pool."""

    def __init__(
        self,
        agent_id: str,
        model: str,
        tier: str,
        capacity: int = 10,
        reset_cycle_hours: Optional[int] = None,
    ):
        self.id = agent_id
        self.model = model
        self.tier = tier
        self.capacity = capacity
        self.status = AgentStatus.SPAWNING
        self.current_tasks: Set[str] = set()
        self.spawned_at = int(time.time() * 1000)
        self.last_heartbeat = int(time.time() * 1000)
        self.tasks_completed = 0
        self.total_cost = 0.0
        self.exhaustion_history: List[ExhaustionRecord] = []

        # Reset cycle configuration
        if reset_cycle_hours is None:
            config = MODEL_CONFIGS.get(model, {})
            reset_cycle_hours = config.get("reset_hours")

        self.reset_cycle = None
        if reset_cycle_hours is not None:
            now_ms = int(time.time() * 1000)
            self.reset_cycle = {
                "hours": reset_cycle_hours,
                "last_reset_at": now_ms,
                "next_reset_at": now_ms + (reset_cycle_hours * 3600 * 1000),
                "warning_threshold_minutes": 30,
            }

        # Transition to available after spawn
        self.status = AgentStatus.AVAILABLE

    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        return (
            self.status == AgentStatus.AVAILABLE
            and len(self.current_tasks) < self.capacity
        )

    def has_capacity(self, min_capacity: int = 1) -> bool:
        """Check if agent has minimum capacity available."""
        return (
            self.status in [AgentStatus.AVAILABLE, AgentStatus.BUSY]
            and (self.capacity - len(self.current_tasks)) >= min_capacity
        )

    def assign_task(self, task_id: str) -> bool:
        """Assign task to agent."""
        if not self.has_capacity():
            return False
        self.current_tasks.add(task_id)
        if len(self.current_tasks) >= self.capacity:
            self.status = AgentStatus.BUSY
        return True

    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed."""
        if task_id not in self.current_tasks:
            return False
        self.current_tasks.discard(task_id)
        self.tasks_completed += 1
        if self.status == AgentStatus.BUSY and len(self.current_tasks) < self.capacity:
            self.status = AgentStatus.AVAILABLE
        return True

    def get_time_to_reset(self) -> Optional[int]:
        """Get minutes until reset cycle (None if unlimited)."""
        if self.reset_cycle is None:
            return None
        now_ms = int(time.time() * 1000)
        remaining_ms = self.reset_cycle["next_reset_at"] - now_ms
        return max(0, remaining_ms // (60 * 1000))

    def is_near_reset(self) -> bool:
        """Check if agent is approaching reset threshold."""
        if self.reset_cycle is None:
            return False
        minutes = self.get_time_to_reset()
        return minutes is not None and minutes <= self.reset_cycle["warning_threshold_minutes"]

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = int(time.time() * 1000)

    def is_stale(self, threshold_seconds: int = 300) -> bool:
        """Check if agent hasn't sent heartbeat recently."""
        now_ms = int(time.time() * 1000)
        threshold_ms = threshold_seconds * 1000
        return (now_ms - self.last_heartbeat) > threshold_ms

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "model": self.model,
            "tier": self.tier,
            "status": self.status.value,
            "capacity": self.capacity,
            "current_tasks": list(self.current_tasks),
            "available_capacity": self.capacity - len(self.current_tasks),
            "reset_cycle": self.reset_cycle,
            "exhaustion_history": [e.to_dict() for e in self.exhaustion_history],
            "spawned_at": self.spawned_at,
            "last_heartbeat": self.last_heartbeat,
            "tasks_completed": self.tasks_completed,
            "total_cost": self.total_cost,
            "time_to_reset_minutes": self.get_time_to_reset(),
            "is_near_reset": self.is_near_reset(),
        }


class AgentPool:
    """
    Multi-agent orchestration layer.

    Key capabilities:
    - Agent lifecycle management (spawn, exhaust, respawn)
    - Reset cycle tracking (Gemini 5h, Opus unlimited)
    - Graceful exhaustion with task checkpointing
    - Auto-reassignment of tasks from exhausted agents
    - Real-time pool metrics
    - Thread-safe for concurrent operations

    Scales: 1 → 100 → 1000 agents (same code, same API)
    """

    def __init__(
        self,
        max_agents: int = 1000,
        checkpoint_callback: Optional[Callable[[str], Dict]] = None,
        handoff_callback: Optional[Callable[[str], Dict]] = None,
    ):
        """
        Initialize agent pool.

        Args:
            max_agents: Maximum number of agents allowed
            checkpoint_callback: Function to checkpoint task (task_id) -> result
            handoff_callback: Function to generate handoff summary (task_id) -> result
        """
        self.max_agents = max_agents
        self.checkpoint_callback = checkpoint_callback
        self.handoff_callback = handoff_callback

        self.agent_registry: Dict[str, Agent] = {}
        self.tier_index: Dict[str, Set[str]] = defaultdict(set)  # tier -> agent_ids
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id

        self.lock = threading.RLock()

        # Metrics
        self.metrics = {
            "total_spawned": 0,
            "total_exhausted": 0,
            "total_respawned": 0,
            "total_tasks_assigned": 0,
            "total_tasks_completed": 0,
            "total_tasks_reassigned": 0,
        }

    def spawn_agent(
        self,
        agent_id: str,
        model: str,
        tier: str,
        capacity: int = 10,
        reset_cycle_hours: Optional[int] = None,
    ) -> Dict:
        """
        Spawn new agent into pool.

        Args:
            agent_id: Unique identifier
            model: Model name (gemini_3_pro_high, claude_opus_4_5, etc.)
            tier: Task tier (T1_PLANNING, T2_CODE, T3_REVIEW, T4_DEPLOY)
            capacity: Max concurrent tasks
            reset_cycle_hours: Hours until reset (None = use model default or unlimited)

        Returns:
            Agent dict with status

        Raises:
            ValueError: If agent_id already exists or pool is full
        """
        with self.lock:
            if agent_id in self.agent_registry:
                raise ValueError(f"Agent {agent_id} already exists")

            if len(self.agent_registry) >= self.max_agents:
                raise ValueError(f"Pool at capacity ({self.max_agents} agents)")

            agent = Agent(
                agent_id=agent_id,
                model=model,
                tier=tier,
                capacity=capacity,
                reset_cycle_hours=reset_cycle_hours,
            )

            self.agent_registry[agent_id] = agent
            self.tier_index[tier].add(agent_id)
            self.metrics["total_spawned"] += 1

            return agent.to_dict()

    def exhaust_agent(
        self,
        agent_id: str,
        reason: str = ExhaustionReason.RESET_CYCLE.value,
        graceful: bool = True,
    ) -> Dict:
        """
        Mark agent as exhausted, handle task reassignment.

        If graceful=True:
        1. Checkpoint all in-progress tasks
        2. Generate handoff summaries
        3. Reassign to available agents

        Args:
            agent_id: Agent to exhaust
            reason: Exhaustion reason
            graceful: Whether to checkpoint and reassign

        Returns:
            Exhaustion record with affected tasks
        """
        with self.lock:
            if agent_id not in self.agent_registry:
                return {"success": False, "error": f"Agent {agent_id} not found"}

            agent = self.agent_registry[agent_id]
            affected_tasks = list(agent.current_tasks)
            reassigned = []
            failed_reassign = []

            if graceful and affected_tasks:
                # Checkpoint all in-progress tasks
                for task_id in affected_tasks:
                    if self.checkpoint_callback:
                        try:
                            self.checkpoint_callback(task_id)
                        except Exception:
                            pass  # Best effort

                    if self.handoff_callback:
                        try:
                            self.handoff_callback(task_id)
                        except Exception:
                            pass  # Best effort

                # Reassign tasks to available agents
                for task_id in affected_tasks:
                    agent.current_tasks.discard(task_id)
                    del self.task_assignments[task_id]

                    new_agent_id = self._find_available_agent_internal(agent.tier)
                    if new_agent_id and new_agent_id != agent_id:
                        new_agent = self.agent_registry[new_agent_id]
                        if new_agent.assign_task(task_id):
                            self.task_assignments[task_id] = new_agent_id
                            reassigned.append({"task_id": task_id, "to": new_agent_id})
                            self.metrics["total_tasks_reassigned"] += 1
                        else:
                            failed_reassign.append(task_id)
                    else:
                        failed_reassign.append(task_id)

            # Mark agent as exhausted
            agent.status = AgentStatus.EXHAUSTED
            agent.current_tasks.clear()

            # Record exhaustion
            record = ExhaustionRecord(
                reason=reason,
                tasks_affected=affected_tasks,
                was_graceful=graceful,
            )
            agent.exhaustion_history.append(record)
            self.metrics["total_exhausted"] += 1

            return {
                "success": True,
                "agent_id": agent_id,
                "exhaustion_record": record.to_dict(),
                "tasks_reassigned": reassigned,
                "tasks_pending": failed_reassign,
            }

    def respawn_agent(
        self,
        agent_id: str,
        new_capacity: Optional[int] = None,
    ) -> Dict:
        """
        Respawn exhausted agent with fresh capacity.

        Args:
            agent_id: Agent to respawn
            new_capacity: New capacity (None = keep existing)

        Returns:
            Updated agent dict
        """
        with self.lock:
            if agent_id not in self.agent_registry:
                return {"success": False, "error": f"Agent {agent_id} not found"}

            agent = self.agent_registry[agent_id]

            if agent.status != AgentStatus.EXHAUSTED:
                return {
                    "success": False,
                    "error": f"Agent {agent_id} is not exhausted (status: {agent.status.value})",
                }

            agent.status = AgentStatus.RESPAWNING

            # Update capacity if specified
            if new_capacity is not None:
                agent.capacity = new_capacity

            # Reset cycle tracking
            if agent.reset_cycle is not None:
                now_ms = int(time.time() * 1000)
                agent.reset_cycle["last_reset_at"] = now_ms
                agent.reset_cycle["next_reset_at"] = now_ms + (
                    agent.reset_cycle["hours"] * 3600 * 1000
                )

            # Update heartbeat
            agent.update_heartbeat()

            # Mark as available
            agent.status = AgentStatus.AVAILABLE

            # Update recovery time in last exhaustion record
            if agent.exhaustion_history:
                last_record = agent.exhaustion_history[-1]
                last_record.recovery_time_seconds = (
                    int(time.time() * 1000) - last_record.timestamp
                ) // 1000

            self.metrics["total_respawned"] += 1

            return {"success": True, "agent": agent.to_dict()}

    def get_available_agent(
        self,
        tier: str,
        min_capacity: int = 1,
    ) -> Optional[str]:
        """
        Find available agent for tier with minimum capacity.

        Args:
            tier: Task tier to match
            min_capacity: Minimum available capacity required

        Returns:
            agent_id or None if no available agent
        """
        with self.lock:
            return self._find_available_agent_internal(tier, min_capacity)

    def _find_available_agent_internal(
        self,
        tier: str,
        min_capacity: int = 1,
    ) -> Optional[str]:
        """Internal: Find available agent (caller must hold lock)."""
        tier_agents = self.tier_index.get(tier, set())

        # Sort by available capacity (descending) for load balancing
        candidates = []
        for agent_id in tier_agents:
            agent = self.agent_registry.get(agent_id)
            if agent and agent.has_capacity(min_capacity):
                available = agent.capacity - len(agent.current_tasks)
                candidates.append((available, agent.tasks_completed, agent_id))

        if not candidates:
            return None

        # Sort by: available capacity (desc), tasks completed (asc for fairness)
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][2]

    def assign_task(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> Dict:
        """
        Assign task to specific agent or auto-select.

        Args:
            task_id: Task to assign
            agent_id: Specific agent (None for auto-select)
            tier: Task tier (required if auto-selecting)

        Returns:
            Assignment result with agent_id
        """
        with self.lock:
            # Check if task already assigned
            if task_id in self.task_assignments:
                current_agent = self.task_assignments[task_id]
                return {
                    "success": False,
                    "error": f"Task {task_id} already assigned to {current_agent}",
                }

            # Auto-select if no agent specified
            if agent_id is None:
                if tier is None:
                    return {"success": False, "error": "tier required for auto-select"}
                agent_id = self._find_available_agent_internal(tier)
                if agent_id is None:
                    return {
                        "success": False,
                        "error": f"No available agent for tier {tier}",
                        "queued": True,
                    }

            # Verify agent exists and has capacity
            if agent_id not in self.agent_registry:
                return {"success": False, "error": f"Agent {agent_id} not found"}

            agent = self.agent_registry[agent_id]
            if not agent.assign_task(task_id):
                return {
                    "success": False,
                    "error": f"Agent {agent_id} at capacity",
                    "queued": True,
                }

            self.task_assignments[task_id] = agent_id
            self.metrics["total_tasks_assigned"] += 1

            return {
                "success": True,
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_status": agent.status.value,
                "agent_capacity": agent.capacity - len(agent.current_tasks),
            }

    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        cost: float = 0.0,
    ) -> Dict:
        """
        Mark task complete, update agent metrics.

        Args:
            task_id: Task that completed
            agent_id: Agent that completed it
            cost: Cost incurred (USD)

        Returns:
            Completion result
        """
        with self.lock:
            if agent_id not in self.agent_registry:
                return {"success": False, "error": f"Agent {agent_id} not found"}

            agent = self.agent_registry[agent_id]

            # Verify task assignment
            if task_id not in self.task_assignments:
                return {"success": False, "error": f"Task {task_id} not assigned"}

            if self.task_assignments[task_id] != agent_id:
                return {
                    "success": False,
                    "error": f"Task {task_id} assigned to {self.task_assignments[task_id]}, not {agent_id}",
                }

            # Complete task
            if not agent.complete_task(task_id):
                return {"success": False, "error": f"Task {task_id} not in agent's queue"}

            del self.task_assignments[task_id]
            agent.total_cost += cost
            self.metrics["total_tasks_completed"] += 1

            return {
                "success": True,
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_tasks_completed": agent.tasks_completed,
                "agent_total_cost": agent.total_cost,
            }

    def check_reset_warnings(self) -> List[Dict]:
        """
        Check all agents for approaching reset cycles.

        Returns:
            List of warning dicts for agents near reset
        """
        with self.lock:
            warnings = []

            for agent in self.agent_registry.values():
                if agent.is_near_reset():
                    warnings.append({
                        "agent_id": agent.id,
                        "model": agent.model,
                        "tier": agent.tier,
                        "minutes_to_reset": agent.get_time_to_reset(),
                        "current_tasks": list(agent.current_tasks),
                        "action": "checkpoint_and_prepare_reassignment",
                    })

            return warnings

    def get_pool_status(self) -> Dict:
        """
        Get comprehensive pool status and metrics.

        Returns:
            PoolMetrics dict
        """
        with self.lock:
            by_status = defaultdict(int)
            by_tier = defaultdict(int)
            total_capacity = 0
            used_capacity = 0

            for agent in self.agent_registry.values():
                by_status[agent.status.value] += 1
                by_tier[agent.tier] += 1
                total_capacity += agent.capacity
                used_capacity += len(agent.current_tasks)

            utilization = (used_capacity / total_capacity) if total_capacity > 0 else 0

            # Calculate exhaustion rate (exhaustions per hour)
            now_ms = int(time.time() * 1000)
            hour_ago = now_ms - (3600 * 1000)
            recent_exhaustions = 0
            for agent in self.agent_registry.values():
                for record in agent.exhaustion_history:
                    if record.timestamp >= hour_ago:
                        recent_exhaustions += 1

            return {
                "total_agents": len(self.agent_registry),
                "by_status": dict(by_status),
                "by_tier": dict(by_tier),
                "total_capacity": total_capacity,
                "used_capacity": used_capacity,
                "available_capacity": total_capacity - used_capacity,
                "utilization": round(utilization, 3),
                "active_tasks": len(self.task_assignments),
                "exhaustion_rate_per_hour": recent_exhaustions,
                "metrics": self.metrics.copy(),
                "agents_near_reset": len(self.check_reset_warnings()),
            }

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get single agent status."""
        with self.lock:
            agent = self.agent_registry.get(agent_id)
            return agent.to_dict() if agent else None

    def get_all_agents(self) -> List[Dict]:
        """Get all agents in pool."""
        with self.lock:
            return [agent.to_dict() for agent in self.agent_registry.values()]

    def get_tier_agents(self, tier: str) -> List[Dict]:
        """Get agents for specific tier."""
        with self.lock:
            agents = []
            for agent_id in self.tier_index.get(tier, set()):
                agent = self.agent_registry.get(agent_id)
                if agent:
                    agents.append(agent.to_dict())
            return agents

    def get_available_agents(self, tier: Optional[str] = None) -> List[Dict]:
        """Get all available agents, optionally filtered by tier."""
        with self.lock:
            agents = []
            for agent in self.agent_registry.values():
                if agent.is_available():
                    if tier is None or agent.tier == tier:
                        agents.append(agent.to_dict())
            return agents

    def heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp."""
        with self.lock:
            agent = self.agent_registry.get(agent_id)
            if agent:
                agent.update_heartbeat()
                return True
            return False

    def cleanup_stale_agents(
        self,
        stale_threshold_seconds: int = 300,
    ) -> List[str]:
        """
        Mark agents without recent heartbeat as offline.

        Args:
            stale_threshold_seconds: Seconds without heartbeat to consider stale

        Returns:
            List of agent_ids marked offline
        """
        with self.lock:
            stale_agents = []

            for agent in self.agent_registry.values():
                if agent.status not in [AgentStatus.OFFLINE, AgentStatus.EXHAUSTED]:
                    if agent.is_stale(stale_threshold_seconds):
                        # Exhaust gracefully before marking offline
                        self.exhaust_agent(
                            agent.id,
                            reason=ExhaustionReason.ERROR.value,
                            graceful=True,
                        )
                        agent.status = AgentStatus.OFFLINE
                        stale_agents.append(agent.id)

            return stale_agents

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove agent from pool entirely.

        Args:
            agent_id: Agent to remove

        Returns:
            True if removed, False if not found
        """
        with self.lock:
            if agent_id not in self.agent_registry:
                return False

            agent = self.agent_registry[agent_id]

            # Exhaust first if has tasks
            if agent.current_tasks:
                self.exhaust_agent(agent_id, reason="manual", graceful=True)

            # Remove from tier index
            self.tier_index[agent.tier].discard(agent_id)

            # Remove from registry
            del self.agent_registry[agent_id]

            return True

    def get_task_agent(self, task_id: str) -> Optional[str]:
        """Get agent_id assigned to task."""
        with self.lock:
            return self.task_assignments.get(task_id)

    def get_agent_tasks(self, agent_id: str) -> List[str]:
        """Get list of tasks assigned to agent."""
        with self.lock:
            agent = self.agent_registry.get(agent_id)
            if agent:
                return list(agent.current_tasks)
            return []

    def auto_exhaust_on_reset(self) -> List[Dict]:
        """
        Auto-exhaust agents that have passed their reset time.

        Returns:
            List of exhaustion results
        """
        with self.lock:
            results = []
            now_ms = int(time.time() * 1000)

            for agent in self.agent_registry.values():
                if agent.reset_cycle is None:
                    continue

                if agent.status in [AgentStatus.EXHAUSTED, AgentStatus.OFFLINE]:
                    continue

                if now_ms >= agent.reset_cycle["next_reset_at"]:
                    result = self.exhaust_agent(
                        agent.id,
                        reason=ExhaustionReason.RESET_CYCLE.value,
                        graceful=True,
                    )
                    results.append(result)

            return results
