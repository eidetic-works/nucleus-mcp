
"""
Preemptive Swarms Orchestrator.
The "Muscles" of the Nucleus Daemon.

Strategic Role:
- Manages Agent Swarms (Genesis, Execution).
- Enforces "Bounded Autonomy" (Budget/Time limits).
- Bridges the "Context Factory" (Tools) with the "Daemon" (Loop).
- Future: Triggers "Private Graph Training" (Nucleus-GPT).

Phase 60+ Enterprise Upgrade:
- REAL agent execution (not mock)
- Artifact persistence per mission
- Flywheel logging integration
"""

import asyncio
import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from .locking import get_lock
from .policy import DirectivesLoader, MissionParameters
from .factory import ContextFactory
import os

# ============================================================
# FLYWHEEL LOGGING SETUP (Bug 6 Fix)
# ============================================================
def _setup_flywheel_logger():
    """Configure flywheel.log file handler for all Nucleus components."""
    try:
        brain_path = Path(os.environ.get("NUCLEUS_BRAIN_PATH", "./.brain"))
        log_path = brain_path / "flywheel.log"
        
        # Create handler
        handler = logging.FileHandler(log_path, mode='a')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Add to nucleus logger (and all child loggers)
        nucleus_logger = logging.getLogger("mcp_server_nucleus")
        
        # Avoid duplicate handlers
        if not any(isinstance(h, logging.FileHandler) for h in nucleus_logger.handlers):
            nucleus_logger.addHandler(handler)
            nucleus_logger.setLevel(logging.INFO)
            
    except Exception as e:
        import sys
        sys.stderr.write(f"[Flywheel] Failed to setup logger: {e}\n"); sys.stderr.flush()

# Initialize on module load
_setup_flywheel_logger()

logger = logging.getLogger(__name__)


class PrivateGraphTrainer:
    """
    Interface for Local Fine-Tuning (Path D: Nucleus-GPT).
    Currently a stub, but architecturally placed for Phase 60.
    """
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        
    async def train_on_session(self, session_id: str, content: str):
        """
        Future: Fine-tune local SLM on this session.
        Current: Log intent.
        """
        logger.info(f"🎓 [TRAINER] Would fine-tune on session {session_id}")
        # Append to training dataset
        dataset_path = self.brain_path / "training" / "dataset.jsonl"
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        pass


class SwarmsOrchestrator:
    """
    Enterprise Swarm Orchestrator with REAL agent execution.
    Bug 4, 6, 7 Fix: No longer a mock - spawns actual EphemeralAgents.
    """
    
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.state_file = brain_path / "swarms" / "state.json"
        
        # Dependencies
        self.policy_engine = DirectivesLoader(brain_path)
        self.context_factory = ContextFactory(brain_path)
        self.trainer = PrivateGraphTrainer(brain_path)
        
        self._active_missions = {}
        self._load_state()

    def _load_state(self):
        """Load swarm state with BrainLock"""
        if not self.state_file.exists():
            return

        try:
            self._active_missions = json.loads(self.state_file.read_text())
        except Exception as e:
            logger.error(f"Failed to load swarm state: {e}")

    def _save_state(self):
        """Save swarm state with BrainLock"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with get_lock("swarms", self.brain_path).section():
                self.state_file.write_text(json.dumps(self._active_missions, indent=2))
        except Exception as e:
            logger.error(f"Failed to save swarm state: {e}")

    def _parse_agents_from_goal(self, mission_goal: str) -> List[str]:
        """
        Extract agent names from mission goal text.
        Looks for patterns like: "delegate to 'researcher'" or "Researcher agent"
        """
        # Pattern 1: Explicit delegation syntax
        pattern1 = r"delegate to ['\"]?(\w+)['\"]?"
        matches = re.findall(pattern1, mission_goal.lower())
        
        # Pattern 2: Agent names from known personas
        known_personas = ["researcher", "critic", "developer", "librarian", "synthesizer", "devops", "architect", "strategist"]
        for persona in known_personas:
            if persona in mission_goal.lower():
                if persona not in matches:
                    matches.append(persona)
        
        # Default if none found
        if not matches:
            matches = ["developer"]
            
        return matches

    async def start_mission(
        self, 
        mission_goal: str, 
        swarm_type: str = "genesis",
        agents: List[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new mission with REAL agent execution.
        
        Args:
            mission_goal: High-level goal description
            swarm_type: "genesis" (planning) or "execution"
            agents: List of agent personas to spawn (optional)
        """
        mission_id = f"mission-{int(time.time())}"
        logger.info(f"🚀 Starting Mission {mission_id}: {mission_goal}")
        
        # Parse agents from goal if not provided
        if not agents:
            agents = self._parse_agents_from_goal(mission_goal)
        
        logger.info(f"📋 Mission agents: {agents}")
        
        # 1. Load Policy constraints
        params = self.policy_engine.get_mission_parameters(swarm_type)
        
        # 2. Initialize Mission State
        mission_state = {
            "id": mission_id,
            "goal": mission_goal,
            "type": swarm_type,
            "agents": agents,
            "status": "running",
            "step_count": 0,
            "cost_usd": 0.0,
            "created_at": time.time(),
            "max_steps": params.max_steps,
            "max_budget": params.max_budget_usd,
            "artifacts": []
        }
        
        self._active_missions[mission_id] = mission_state
        self._save_state()
        
        # 3. Spawn Background Execution via Thread (persists beyond MCP call)
        import threading
        
        def run_mission_in_thread():
            """Run the async mission loop in a new thread with its own event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._run_mission_loop(mission_id, mission_state, params, agents)
                )
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_mission_in_thread, daemon=True)
        thread.start()
        logger.info(f"🚀 Mission {mission_id} thread started")
        
        return {"mission_id": mission_id, "status": "started"}


    async def _run_mission_loop(
        self, 
        mission_id: str, 
        state: Dict, 
        params: MissionParameters,
        agents: List[str]
    ):
        """
        The REAL Execution Loop (Bug 4 & 7 Fix).
        Actually spawns EphemeralAgents and collects their output.
        """
        # Lazy imports to avoid circular dependencies
        from .agent import EphemeralAgent
        from .llm_client import DualEngineLLM
        
        try:
            logger.info(f"🔄 Mission {mission_id} loop started with agents: {agents}")
            
            mission_artifacts = []
            
            for i, agent_persona in enumerate(agents):
                # Check Bounds (Safety First)
                if state["step_count"] >= params.max_steps:
                    logger.warning(f"🛑 Mission {mission_id} hit Max Steps ({params.max_steps}). halting.")
                    state["status"] = "halted_steps"
                    break
                    
                if state["cost_usd"] >= params.max_budget_usd:
                    logger.warning(f"💸 Mission {mission_id} hit Budget Limit (${params.max_budget_usd}). halting.")
                    state["status"] = "halted_budget"
                    break
                
                logger.info(f"🤖 Spawning agent {i+1}/{len(agents)}: {agent_persona}")
                
                try:
                    # 1. Create context for this agent
                    context = self.context_factory.create_context_for_persona(
                        persona_name=agent_persona,
                        intent=f"[SWARM {mission_id}] Step {i+1}/{len(agents)}: {state['goal']}",
                        session_id=mission_id
                    )
                    
                    # QUALITY FIX: Inject absolute project path into context
                    project_root = str(self.brain_path.parent)
                    brain_path_str = str(self.brain_path)
                    
                    awareness_injection = f"""
# WORLD AWARENESS
Current Project Root: {project_root}
Nucleus Brain Path: {brain_path_str}
Active Swarm Mission: {mission_id}
Mission Artifacts: {brain_path_str}/swarms/{mission_id}/

CRITICAL: When using files or tools, always search within the Project Root first.
"""
                    context["system_prompt"] = awareness_injection + context["system_prompt"]
                    
                    # 2. Get LLM with correct tier routing
                    # DualEngineLLM takes job_type in constructor and IS the model (has generate_content)
                    job_type = context.get('job_type', 'ORCHESTRATION')
                    model = DualEngineLLM(job_type=job_type)
                    
                    logger.info(f"📡 Agent {agent_persona} using job_type={job_type}, tier={model.tier}")
                    
                    # 3. Spawn and run agent (DualEngineLLM has generate_content method)
                    agent = EphemeralAgent(context, model)
                    result = await agent.run()
                    
                    # 4. Record results
                    artifact = {
                        "agent": agent_persona,
                        "step": i + 1,
                        "job_type": job_type,
                        "result": result[:3000]  # Truncate for storage
                    }
                    mission_artifacts.append(artifact)
                    state["artifacts"].append(artifact)
                    
                    logger.info(f"✅ Agent {agent_persona} completed step {i+1}")
                    
                except Exception as agent_error:
                    logger.error(f"💥 Agent {agent_persona} failed: {agent_error}")
                    mission_artifacts.append({
                        "agent": agent_persona,
                        "step": i + 1,
                        "error": str(agent_error)
                    })
                
                state["step_count"] += 1
                state["cost_usd"] += 0.05  # Estimated cost per agent
                
                # Save checkpoint after each agent
                self._active_missions[mission_id] = state
                self._save_state()
            
            # 5. Persist artifacts to disk (Bug 4 fix)
            self._save_mission_artifacts(mission_id, mission_artifacts, state['goal'])
            
            # 6. Mark completed
            if state["status"] == "running":
                state["status"] = "completed"
                logger.info(f"✅ Mission {mission_id} Completed with {len(mission_artifacts)} agent outputs.")
            
            # 7. Trigger Training (The "Sovereign Loop")
            await self.trainer.train_on_session(mission_id, json.dumps(mission_artifacts))
            
            # Final save
            self._active_missions[mission_id] = state
            self._save_state()
                
        except Exception as e:
            logger.error(f"💥 Mission {mission_id} Failed: {e}")
            state["status"] = "failed"
            state["error"] = str(e)
            self._save_state()

    def _save_mission_artifacts(self, mission_id: str, artifacts: List[Dict], goal: str):
        """
        Save mission artifacts to .brain/swarms/{mission_id}/summary.md
        Bug 4 Fix: Ensures artifacts persist to disk.
        """
        try:
            mission_dir = self.brain_path / "swarms" / mission_id
            mission_dir.mkdir(parents=True, exist_ok=True)
            
            # Save summary markdown
            summary_file = mission_dir / "summary.md"
            summary_content = f"""# Mission: {mission_id}

**Goal:** {goal}
**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Agents Executed:** {len(artifacts)}

---

"""
            for artifact in artifacts:
                agent = artifact.get('agent', 'unknown')
                step = artifact.get('step', 0)
                result = artifact.get('result', artifact.get('error', 'No output'))
                job_type = artifact.get('job_type', 'unknown')
                
                summary_content += f"""## Step {step}: {agent.title()} ({job_type})

```
{result}
```

---

"""
            
            summary_file.write_text(summary_content)
            logger.info(f"📄 Saved mission artifacts to {mission_dir}")
            
            # Also save raw JSON
            raw_file = mission_dir / "artifacts.json"
            raw_file.write_text(json.dumps(artifacts, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save mission artifacts: {e}")
            
    async def get_mission_status(self, mission_id: str) -> Optional[Dict]:
        return self._active_missions.get(mission_id)
