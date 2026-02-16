"""
NOP V3.1 Unified Orchestrator

Converges Track A (Pure Python Core) with Track B (MCP Integration):
- CRDTTaskStore: 15K+ writes/sec, LWW + vector clocks
- TaskScheduler: 423K tasks/sec, intelligent routing  
- V3.1 Features: Reset cycles, checkpoints, context summaries

This is the CORE orchestration engine that MCP tools delegate to.
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from .crdt_task_store import CRDTTaskStore
from .task_scheduler import TaskScheduler

# V3.1 Components - lazy loaded to avoid circular imports
_agent_pool = None
_ingestion_engine = None


def _get_agent_pool():
    """Lazy load AgentPool to avoid circular imports."""
    global _agent_pool
    if _agent_pool is None:
        try:
            from .agent_pool import AgentPool
            _agent_pool = AgentPool()
        except ImportError:
            pass
    return _agent_pool


def _get_ingestion_engine(brain_path=None):
    """Lazy load TaskIngestionEngine."""
    global _ingestion_engine
    if _ingestion_engine is None:
        try:
            from .task_ingestion import TaskIngestionEngine
            _ingestion_engine = TaskIngestionEngine(brain_path=brain_path)
        except ImportError:
            pass
    return _ingestion_engine


def get_brain_path() -> Path:
    """Get brain path from environment or default."""
    return Path(os.getenv("NUCLEAR_BRAIN_PATH", "/Users/lokeshgarg/ai-mvp-backend/.brain"))


@dataclass
class ResetCycleInfo:
    """V3.1: Reset cycle configuration for model-specific limits."""
    hours: Optional[int] = None  # None = unlimited (Opus 4.5)
    last_reset_at: Optional[str] = None
    next_reset_at: Optional[str] = None
    warning_threshold_minutes: int = 30


@dataclass
class Checkpoint:
    """V3.1: Checkpoint for long-running tasks."""
    enabled: bool = False
    last_checkpoint_at: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSummary:
    """V3.1: Context summary for handoffs."""
    generated_at: Optional[str] = None
    summary: str = ""
    key_decisions: List[str] = field(default_factory=list)
    handoff_notes: str = ""


class NucleusOrchestratorV3:
    """
    Unified orchestration engine for NOP V3.1.
    
    Combines:
    - CRDTTaskStore (conflict-free task storage)
    - TaskScheduler (intelligent task assignment)
    - V3.1 features (checkpoints, context summaries, reset cycles)
    
    Provides:
    - All internal _impl functions for MCP tools
    - Backward compatibility with V3.0 tools
    - High-performance operations from Track A
    """
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self.replica_id = f"nucleus_{int(time.time())}"
        
        # Initialize Track A components
        self.task_store = CRDTTaskStore(replica_id=self.replica_id)
        self.scheduler = TaskScheduler(max_agents=1000)
        
        # Load existing state from JSON files (backward compat)
        self._load_from_legacy_json()
    
    def _load_from_legacy_json(self):
        """Load existing tasks from V3.0/V3.1 JSON files."""
        tasks_path = self.brain_path / "ledger" / "tasks.json"
        if tasks_path.exists():
            try:
                with open(tasks_path) as f:
                    data = json.load(f)
                
                for task in data.get("tasks", []):
                    # Map to CRDT format
                    crdt_task = {
                        "id": task.get("id"),
                        "title": task.get("description", task.get("title", "")),
                        "status": task.get("status", "PENDING"),
                        "tier": task.get("required_tier", "T2_CODE"),
                        "priority": task.get("priority", 3),
                        "claimed_by": task.get("claimed_by"),
                        "blocked_by": task.get("blocked_by", []),
                        # V3.1 fields
                        "checkpoint": task.get("checkpoint"),
                        "context_summary": task.get("context_summary"),
                        "dependency_metadata": task.get("dependency_metadata", {})
                    }
                    self.task_store.add_task(crdt_task)
            except Exception as e:
                print(f"Warning: Failed to load legacy tasks: {e}")
    
    def _save_to_legacy_json(self):
        """Save CRDT state back to legacy JSON format."""
        tasks_path = self.brain_path / "ledger" / "tasks.json"
        
        # Load existing to preserve metadata
        existing = {"tasks": [], "metadata": {"version": "3.1"}}
        if tasks_path.exists():
            with open(tasks_path) as f:
                existing = json.load(f)
        
        # Convert CRDT tasks to legacy format
        crdt_tasks = self.task_store.get_all_tasks()
        legacy_tasks = []
        
        for task in crdt_tasks:
            legacy_task = {
                "id": task["id"],
                "description": task.get("title", ""),
                "status": task.get("status", "PENDING"),
                "priority": task.get("priority", 3),
                "required_tier": task.get("tier", "standard"),
                "claimed_by": task.get("claimed_by"),
                "blocked_by": task.get("blocked_by", []),
                "checkpoint": task.get("checkpoint"),
                "context_summary": task.get("context_summary"),
                "dependency_metadata": task.get("dependency_metadata", {})
            }
            legacy_tasks.append(legacy_task)
        
        existing["tasks"] = legacy_tasks
        existing["metadata"]["last_synced"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        with open(tasks_path, "w") as f:
            json.dump(existing, f, indent=2)
    
    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a single task by ID."""
        return self.task_store.get_task(task_id)
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """Get all tasks, optionally filtered by status."""
        tasks = self.task_store.get_all_tasks()
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks
    
    def claim_task(self, task_id: str, agent_id: str) -> Dict:
        """Atomic task claiming with conflict detection."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        if task.get("claimed_by") and task["claimed_by"] != agent_id:
            return {
                "success": False, 
                "error": f"Task already claimed by {task['claimed_by']}"
            }
        
        # Update task with claim
        task["claimed_by"] = agent_id
        task["status"] = "IN_PROGRESS"
        task["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        
        return {"success": True, "task": task}
    
    def complete_task(self, task_id: str, agent_id: str, outcome: str = "success") -> Dict:
        """Mark task as complete."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        task["status"] = "DONE" if outcome == "success" else "FAILED"
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        task["completed_by"] = agent_id
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        
        return {"success": True, "task": task}
    
    def add_task(self, description: str, priority: int = 3, 
                 tier: str = "T2_CODE", blocked_by: List[str] = None,
                 source: str = "user", required_skills: List[str] = None) -> Dict:
        """Create new task via orchestrator."""
        task_id = f"task_{int(time.time() * 1000)}"
        task = {
            "id": task_id,
            "title": description,
            "description": description,
            "status": "PENDING",
            "tier": tier,
            "priority": priority,
            "blocked_by": blocked_by or [],
            "required_skills": required_skills or [],
            "source": source,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            # V3.1 fields
            "checkpoint": None,
            "context_summary": None,
            "dependency_metadata": {"depth": 0, "blocks": []}
        }
        self.task_store.add_task(task)
        self._save_to_legacy_json()
        return {"success": True, "task": task}
    
    def update_task(self, task_id: str, updates: Dict) -> Dict:
        """Update task fields."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Apply updates (never update ID)
        for key, value in updates.items():
            if key != "id":
                task[key] = value
        task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        return {"success": True, "task": task}
    
    def get_next_task(self, skills: List[str] = None, 
                      agent_tier: str = None) -> Optional[Dict]:
        """Get highest priority unblocked task."""
        tasks = self.task_store.get_all_tasks()
        
        # Filter to pending/ready tasks
        available = [t for t in tasks if t.get("status") in ["PENDING", "READY"]]
        
        # Filter out blocked tasks
        done_ids = {t["id"] for t in tasks if t.get("status") == "DONE"}
        unblocked = []
        for t in available:
            deps = t.get("blocked_by", []) + t.get("depends_on", [])
            if all(d in done_ids for d in deps):
                unblocked.append(t)
        
        if not unblocked:
            return None
        
        # Sort by priority (lower = higher priority)
        unblocked.sort(key=lambda x: x.get("priority", 3))
        return unblocked[0]
    
    def resume_from_checkpoint(self, task_id: str) -> Dict:
        """Get checkpoint data for task resumption."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        checkpoint = task.get("checkpoint")
        if not checkpoint:
            return {"success": False, "error": "No checkpoint found for task"}
        
        return {
            "success": True,
            "task_id": task_id,
            "checkpoint": checkpoint,
            "context_summary": task.get("context_summary"),
            "resume_instructions": f"Resume from step {checkpoint.get('data', {}).get('step', 'unknown')}"
        }
    
    def escalate_task(self, task_id: str, reason: str) -> Dict:
        """Mark task as needing human intervention."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        task["status"] = "ESCALATED"
        task["escalation"] = {
            "reason": reason,
            "escalated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "resolved": False
        }
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        return {"success": True, "task": task}
    
    # =========================================================================
    # V3.1 FEATURES
    # =========================================================================
    
    def checkpoint_task(self, task_id: str, checkpoint_data: Dict) -> Dict:
        """Save checkpoint for long-running task."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        task["checkpoint"] = {
            "enabled": True,
            "last_checkpoint_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "data": checkpoint_data
        }
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        
        return {"success": True, "checkpoint": task["checkpoint"]}
    
    def generate_context_summary(self, task_id: str, summary: str, 
                                  key_decisions: List[str] = None,
                                  handoff_notes: str = "") -> Dict:
        """Generate handoff context summary for a task."""
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        task["context_summary"] = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "summary": summary,
            "key_decisions": key_decisions or [],
            "handoff_notes": handoff_notes
        }
        
        self.task_store.update_task(task_id, task)
        self._save_to_legacy_json()
        
        return {"success": True, "context_summary": task["context_summary"]}
    
    def check_reset_warnings(self) -> List[Dict]:
        """Check all slots for approaching resets."""
        warnings = []
        registry_path = self.brain_path / "slots" / "registry.json"
        
        if not registry_path.exists():
            return warnings
        
        with open(registry_path) as f:
            registry = json.load(f)
        
        now = datetime.now()
        
        for slot_id, slot in registry.get("slots", {}).items():
            reset_cycle = slot.get("reset_cycle")
            if not reset_cycle or not reset_cycle.get("next_reset_at"):
                continue
            
            try:
                next_reset = datetime.fromisoformat(reset_cycle["next_reset_at"].replace("Z", "+00:00"))
                time_remaining = (next_reset - now).total_seconds() / 60
                threshold = reset_cycle.get("warning_threshold_minutes", 30)
                
                if time_remaining <= threshold and time_remaining > 0:
                    warnings.append({
                        "slot_id": slot_id,
                        "minutes_remaining": int(time_remaining),
                        "next_reset_at": reset_cycle["next_reset_at"],
                        "action": "PREPARE_HANDOFF"
                    })
            except (ValueError, TypeError):
                continue
        
        return warnings
    
    def record_exhaustion(self, slot_id: str, reason: str, 
                          tasks_affected: List[str] = None) -> Dict:
        """Record slot exhaustion event."""
        registry_path = self.brain_path / "slots" / "registry.json"
        
        if not registry_path.exists():
            return {"success": False, "error": "Registry not found"}
        
        with open(registry_path) as f:
            registry = json.load(f)
        
        slot = registry.get("slots", {}).get(slot_id)
        if not slot:
            return {"success": False, "error": f"Slot {slot_id} not found"}
        
        # Initialize exhaustion_history if needed
        if "exhaustion_history" not in slot:
            slot["exhaustion_history"] = []
        
        # Add exhaustion event
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "reason": reason,
            "tasks_affected": tasks_affected or [],
            "recovery_time_seconds": 300 if reason == "rate_limit_hit" else 18000
        }
        slot["exhaustion_history"].append(event)
        
        # Keep only last 10 events
        slot["exhaustion_history"] = slot["exhaustion_history"][-10:]
        
        registry["slots"][slot_id] = slot
        
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        
        return {"success": True, "event": event}
    
    # =========================================================================
    # AGENT POOL OPERATIONS (V3.1)
    # =========================================================================
    
    def get_agent_pool(self):
        """Get the AgentPool instance."""
        return _get_agent_pool()
    
    def spawn_agent(self, model: str, tier: str = "T2_CODE", 
                    alias: str = None) -> Dict:
        """Spawn a new agent in the pool."""
        pool = _get_agent_pool()
        if pool is None:
            return {"success": False, "error": "AgentPool not available"}
        return pool.spawn_agent(model=model, tier=tier, alias=alias)
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent by ID."""
        pool = _get_agent_pool()
        if pool is None:
            return None
        return pool.get_agent(agent_id)
    
    def mark_agent_exhausted(self, agent_id: str, reason: str = "rate_limit") -> Dict:
        """Mark an agent as exhausted."""
        pool = _get_agent_pool()
        if pool is None:
            return {"success": False, "error": "AgentPool not available"}
        return pool.exhaust_agent(agent_id, reason=reason)
    
    def respawn_agent(self, agent_id: str) -> Dict:
        """Respawn an exhausted agent."""
        pool = _get_agent_pool()
        if pool is None:
            return {"success": False, "error": "AgentPool not available"}
        return pool.respawn_agent(agent_id)
    
    def get_available_agent(self, tier: str = None) -> Optional[str]:
        """Get an available agent for the given tier."""
        pool = _get_agent_pool()
        if pool is None:
            return None
        return pool.get_available_agent(tier=tier)
    
    def assign_task_to_agent(self, task_id: str, agent_id: str = None, 
                             tier: str = None) -> Dict:
        """Assign a task to an agent (or find best available)."""
        pool = _get_agent_pool()
        if pool is None:
            return {"success": False, "error": "AgentPool not available"}
        
        if agent_id is None and tier:
            agent_id = pool.get_available_agent(tier=tier)
            if agent_id is None:
                return {"success": False, "error": f"No available agent for tier {tier}"}
        
        return pool.assign_task(task_id, agent_id=agent_id)
    
    # =========================================================================
    # TASK INGESTION OPERATIONS (V3.1)
    # =========================================================================
    
    def get_ingestion_engine(self):
        """Get the TaskIngestionEngine instance."""
        return _get_ingestion_engine(self.brain_path)
    
    def ingest_tasks(self, source: str, source_type: str = "auto",
                     session_id: str = None, auto_assign: bool = False,
                     skip_dedup: bool = False, dry_run: bool = False) -> Dict:
        """Ingest tasks from various sources."""
        engine = _get_ingestion_engine(self.brain_path)
        if engine is None:
            return {"success": False, "error": "TaskIngestionEngine not available"}
        
        import os
        if os.path.exists(source):
            result = engine.ingest_from_file(
                source, source_type=source_type, session_id=session_id,
                auto_assign=auto_assign, skip_dedup=skip_dedup, dry_run=dry_run
            )
        else:
            result = engine.ingest_from_text(
                source, source_type=source_type if source_type != "auto" else "manual",
                session_id=session_id, auto_assign=auto_assign,
                skip_dedup=skip_dedup, dry_run=dry_run
            )
        
        return result.to_dict()
    
    def rollback_ingestion(self, batch_id: str, reason: str = None) -> Dict:
        """Rollback an ingestion batch."""
        engine = _get_ingestion_engine(self.brain_path)
        if engine is None:
            return {"success": False, "error": "TaskIngestionEngine not available"}
        return engine.rollback(batch_id, reason)
    
    def get_ingestion_stats(self) -> Dict:
        """Get ingestion statistics."""
        engine = _get_ingestion_engine(self.brain_path)
        if engine is None:
            return {"error": "TaskIngestionEngine not available"}
        return engine.get_ingestion_stats()
    
    # =========================================================================
    # METRICS & MONITORING
    # =========================================================================
    
    def get_pool_metrics(self) -> Dict:
        """Get pool-wide metrics."""
        tasks = self.task_store.get_all_tasks()
        
        return {
            "total_tasks": len(tasks),
            "pending": len([t for t in tasks if t.get("status") in ["PENDING", "READY"]]),
            "in_progress": len([t for t in tasks if t.get("status") == "IN_PROGRESS"]),
            "blocked": len([t for t in tasks if t.get("status") == "BLOCKED"]),
            "done": len([t for t in tasks if t.get("status") == "DONE"]),
            "failed": len([t for t in tasks if t.get("status") == "FAILED"]),
            "with_checkpoints": len([t for t in tasks if t.get("checkpoint")]),
            "with_summaries": len([t for t in tasks if t.get("context_summary")])
        }
    
    def get_dependency_graph(self) -> Dict:
        """Compute dependency graph for all tasks."""
        tasks = self.task_store.get_all_tasks()
        
        # Build forward dependencies (task -> what it depends on)
        forward = {}
        # Build reverse dependencies (task -> what depends on it)
        reverse = {}
        
        for task in tasks:
            task_id = task["id"]
            deps = task.get("blocked_by", []) + task.get("depends_on", [])
            forward[task_id] = deps
            
            for dep in deps:
                if dep not in reverse:
                    reverse[dep] = []
                reverse[dep].append(task_id)
        
        # Compute depths
        depths = {}
        
        def compute_depth(task_id: str, visited: set) -> int:
            if task_id in depths:
                return depths[task_id]
            if task_id in visited:
                return -1  # Cycle detected
            
            visited.add(task_id)
            deps = forward.get(task_id, [])
            
            if not deps:
                depths[task_id] = 0
                return 0
            
            max_dep_depth = max(compute_depth(d, visited) for d in deps)
            depths[task_id] = max_dep_depth + 1 if max_dep_depth >= 0 else -1
            return depths[task_id]
        
        for task in tasks:
            compute_depth(task["id"], set())
        
        return {
            "forward_deps": forward,
            "reverse_deps": reverse,
            "depths": depths,
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }


# Singleton instance
_orchestrator: Optional[NucleusOrchestratorV3] = None


def get_orchestrator() -> NucleusOrchestratorV3:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = NucleusOrchestratorV3()
    return _orchestrator
