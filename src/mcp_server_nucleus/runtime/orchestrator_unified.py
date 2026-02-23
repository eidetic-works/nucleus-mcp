"""
Unified Nucleus Orchestrator (v0.5.0)
=====================================
Converges SwarmsOrchestrator (V2) with NucleusOrchestratorV3 (V3).

Single entry point for:
- Mission/Swarm Management (Ephemeral Agent execution).
- Task/Queue Management (CRDT Store + Scheduler).
- System-wide persistence and state synchronization.

Strategic Role:
- The "Brain" and "Muscles" of the Nucleus Daemon.
- MDR_010 Compliant: High availability and reliability.
"""

import json
import time
import os
import logging
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

# V3 Core Components
from .crdt_task_store import CRDTTaskStore
from .task_scheduler import TaskScheduler
# V2 Logic Components
from .locking import get_lock
from .policy import DirectivesLoader, MissionParameters
from .factory import ContextFactory

logger = logging.getLogger("nucleus.orchestrator")

class UnifiedOrchestrator:
    """
    The Single Source of Truth for Nucleus Orchestration.
    Integrates mission execution with task management.
    """

    _task_counter = 0

    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or Path(os.getenv("NUCLEAR_BRAIN_PATH", "./.brain"))
        self.replica_id = f"nucleus_{int(time.time())}"
        
        # 1. Initialize Task Core (V3)
        self.task_store = CRDTTaskStore(replica_id=self.replica_id)
        self.scheduler = TaskScheduler(max_agents=1000)
        
        # 2. Initialize Mission Logic (V2)
        self.policy_engine = DirectivesLoader(self.brain_path)
        self.context_factory = ContextFactory(self.brain_path)
        
        # 3. State Management
        self._active_missions = {}
        self.swarms_state_file = self.brain_path / "swarms" / "state.json"
        
        # Load existing datasets
        self._load_all_state()

    def _load_all_state(self):
        """Unified state loader."""
        # Load Tasks (CRDT logic handles merge)
        tasks_path = self.brain_path / "ledger" / "tasks.json"
        if tasks_path.exists():
            try:
                with open(tasks_path) as f:
                    data = json.load(f)
                
                # V3.1+ format is {"tasks": [...]}
                # Older format might be just a list [...]
                tasks_list = data["tasks"] if isinstance(data, dict) and "tasks" in data else data
                
                if not isinstance(tasks_list, list):
                     tasks_list = []
                     
                for task in tasks_list:
                    self.task_store.add_task(task)
            except Exception as e:
                logger.warning(f"Failed to load tasks during unification: {e}")

        # Load Swarms
        if self.swarms_state_file.exists():
            try:
                self._active_missions = json.loads(self.swarms_state_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load swarm state: {e}")

    def _save_all_state(self):
        """Unified state saver."""
        # Save Tasks
        tasks_path = self.brain_path / "ledger" / "tasks.json"
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            crdt_tasks = self.task_store.get_all_tasks()
            output = {
                "tasks": crdt_tasks,
                "metadata": {
                    "version": "0.5.0",
                    "last_synced": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if 'timezone' in globals() else time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }
            with open(tasks_path, "w") as f:
                json.dump(output, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

        # Save Swarms
        self.swarms_state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with get_lock("swarms", self.brain_path).section():
                self.swarms_state_file.write_text(json.dumps(self._active_missions, indent=2))
        except Exception as e:
            logger.error(f"Failed to save swarm state: {e}")

    # =========================================================================
    # TASK OPERATIONS (Brains)
    # =========================================================================

    def add_task(self, description: str, priority: int = 3, 
                 tier: str = "T2_CODE", blocked_by: List[str] = None,
                 source: str = "user", required_skills: List[str] = None) -> Dict:
        UnifiedOrchestrator._task_counter += 1
        task_id = f"task_{int(time.time() * 1000)}_{UnifiedOrchestrator._task_counter}"
        task = {
            "id": task_id,
            "description": description,
            "status": "PENDING",
            "tier": tier,
            "priority": priority,
            "blocked_by": blocked_by or [],
            "required_skills": required_skills or [],
            "source": source,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "checkpoint": None,
            "context_summary": None
        }
        self.task_store.add_task(task)
        self._save_all_state()
        return {"success": True, "task": task}

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.task_store.get_task(task_id)

    def update_task(self, task_id: str, updates: Dict) -> Dict:
        task = self.task_store.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        for key, value in updates.items():
            if key != "id":
                task[key] = value
        self.task_store.update_task(task_id, task)
        self._save_all_state()
        return {"success": True, "task": task}

    def get_next_task(self, skills: List[str] = None) -> Optional[Dict]:
        tasks = self.task_store.get_all_tasks()
        available = [t for t in tasks if t.get("status") in ["PENDING", "READY"]]
        if not available: return None
        available.sort(key=lambda x: x.get("priority", 3))
        return available[0]

    # =========================================================================
    # V3.1 CHECKPOINT & HANDOFF OPERATIONS
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
        self._save_all_state()
        return {"success": True, "checkpoint": task["checkpoint"]}

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
        self._save_all_state()
        return {"success": True, "context_summary": task["context_summary"]}

    # =========================================================================
    # V3 TASK LIFECYCLE (claim, complete, query)
    # =========================================================================

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
            return {"success": False, "error": f"Task already claimed by {task['claimed_by']}"}

        task["claimed_by"] = agent_id
        task["status"] = "IN_PROGRESS"
        task["claimed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        self.task_store.update_task(task_id, task)
        self._save_all_state()
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
        self._save_all_state()
        return {"success": True, "task": task}

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
        forward = {}
        reverse = {}

        for task in tasks:
            task_id = task["id"]
            deps = task.get("blocked_by", []) + task.get("depends_on", [])
            forward[task_id] = deps
            for dep in deps:
                if dep not in reverse:
                    reverse[dep] = []
                reverse[dep].append(task_id)

        depths = {}

        def compute_depth(tid: str, visited: set) -> int:
            if tid in depths:
                return depths[tid]
            if tid in visited:
                return -1
            visited.add(tid)
            deps = forward.get(tid, [])
            if not deps:
                depths[tid] = 0
                return 0
            max_dep_depth = max(compute_depth(d, visited) for d in deps)
            depths[tid] = max_dep_depth + 1 if max_dep_depth >= 0 else -1
            return depths[tid]

        for task in tasks:
            compute_depth(task["id"], set())

        return {
            "forward_deps": forward,
            "reverse_deps": reverse,
            "depths": depths,
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }

    def get_agent_pool(self):
        """Get the AgentPool instance (lazy import)."""
        try:
            from .agent_pool import _get_agent_pool
            return _get_agent_pool()
        except ImportError:
            return None

    def get_ingestion_stats(self) -> Dict:
        """Get ingestion statistics."""
        try:
            from .task_ingestion import _get_ingestion_engine
            engine = _get_ingestion_engine(self.brain_path)
            if engine is None:
                return {"error": "TaskIngestionEngine not available"}
            return engine.get_ingestion_stats()
        except ImportError:
            return {"error": "TaskIngestionEngine not available"}

    # =========================================================================
    # MISSION OPERATIONS (Muscles)
    # =========================================================================

    async def start_mission(self, goal: str, swarm_type: str = "genesis", 
                            agents: List[str] = None) -> Dict:
        mission_id = f"mission-{int(time.time())}"
        logger.info(f"🚀 [UNIFIED] Starting Mission {mission_id}")
        
        if not agents:
            agents = self._parse_agents_from_goal(goal)
            
        params = self.policy_engine.get_mission_parameters(swarm_type)
        
        mission_state = {
            "id": mission_id,
            "goal": goal,
            "type": swarm_type,
            "agents": agents,
            "status": "running",
            "step_count": 0,
            "created_at": time.time(),
            "artifacts": []
        }
        
        self._active_missions[mission_id] = mission_state
        self._save_all_state()
        
        # Background execution
        threading.Thread(target=lambda: self._run_mission_background(mission_id, mission_state, params), daemon=True).start()
        
        return {"mission_id": mission_id, "status": "started"}

    def _parse_agents_from_goal(self, goal: str) -> List[str]:
        known = ["researcher", "critic", "developer", "architect"]
        matches = [p for p in known if p in goal.lower()]
        return matches if matches else ["developer"]

    def _run_mission_background(self, mission_id: str, state: Dict, params: MissionParameters):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_mission_loop(mission_id, state, params))
        except Exception as e:
            logger.error(f"Mission {mission_id} thread-loop crashed: {e}")
        finally:
            loop.close()

    async def _run_mission_loop(self, mission_id: str, state: Dict, params: MissionParameters):
        from .agent import EphemeralAgent
        from .llm_client import DualEngineLLM
        
        logger.info(f"🔄 [UNIFIED] Loop started for {mission_id}")
        mission_artifacts = []
        
        for i, persona in enumerate(state["agents"]):
            if state["step_count"] >= params.max_steps: break
            
            logger.info(f"🤖 Step {i+1}: Spawning {persona}")
            context = self.context_factory.create_context_for_persona(
                persona_name=persona,
                intent=f"[MISSION {mission_id}] {state['goal']}",
                session_id=mission_id
            )
            
            model = DualEngineLLM(job_type=context.get('job_type', 'ORCHESTRATION'))
            agent = EphemeralAgent(context, model)
            result = await agent.run()
            
            artifact = {"agent": persona, "step": i+1, "result": result[:5000]}
            mission_artifacts.append(artifact)
            state["artifacts"].append(artifact)
            state["step_count"] += 1
            
            self._save_all_state()
            
        self._save_mission_artifacts_to_disk(mission_id, mission_artifacts, state['goal'])
        state["status"] = "completed"
        self._save_all_state()

    def _save_mission_artifacts_to_disk(self, mission_id: str, artifacts: List[Dict], goal: str):
        mission_dir = self.brain_path / "swarms" / mission_id
        mission_dir.mkdir(parents=True, exist_ok=True)
        summary = f"# Mission {mission_id}\n\nGoal: {goal}\n\n"
        for a in artifacts:
            summary += f"## {a['agent']} (Step {a['step']})\n{a['result']}\n\n---\n\n"
        (mission_dir / "summary.md").write_text(summary)
        (mission_dir / "artifacts.json").write_text(json.dumps(artifacts, indent=2))

    def get_mission_status(self, mission_id: str) -> Optional[Dict]:
        return self._active_missions.get(mission_id)

# Singleton management
_orchestrator = None

def get_orchestrator() -> UnifiedOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UnifiedOrchestrator()
    return _orchestrator
