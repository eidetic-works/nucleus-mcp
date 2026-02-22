"""
Swarm Orchestration Entry Point.
Phase 60+ Enterprise Upgrade: Now uses SwarmsOrchestrator for real auto-execution.

This module is the bridge between the MCP tool (brain_orchestrate_swarm)
and the SwarmsOrchestrator class that handles actual agent spawning.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

# Configure logger
logger = logging.getLogger("nucleus.swarm")


def get_brain_path() -> Path:
    """Get the brain path from environment variable."""
    # Try NUCLEUS_BRAIN_PATH first (correct name), then NUCLEAR_BRAIN_PATH (legacy)
    brain_path = os.environ.get("NUCLEUS_BRAIN_PATH") or os.environ.get("NUCLEAR_BRAIN_PATH")
    if brain_path and Path(brain_path).exists():
        return Path(brain_path)
    
    # Fallback: search for .brain directory
    cwd = Path.cwd()
    if (cwd / ".brain").exists():
        return cwd / ".brain"
    for parent in cwd.parents:
        if (parent / ".brain").exists():
            return parent / ".brain"
    
    # Ultimate fallback
    return Path("/Users/nucleus-os/ai-mvp-backend/.brain")


def _orchestrate_swarm(mission: str, agents: List[str] = None) -> Dict:
    """
    Orchestrate a swarm of agents to complete a complex mission.
    
    Phase 60+ UPGRADE: Now uses SwarmsOrchestrator for REAL auto-execution.
    Agents are spawned automatically in sequence - no manual intervention needed.
    
    Args:
        mission: High-level goal description
        agents: List of agent personas to recruit (default: ["developer", "critic"])
        
    Returns:
        Dict with mission_id, status, and instructions for checking results
    """
    try:
        from .orchestrator import SwarmsOrchestrator
        
        brain_path = get_brain_path()
        logger.info(f"🐝 Initializing swarm for mission: {mission}")
        
        # Create orchestrator
        orchestrator = SwarmsOrchestrator(brain_path)
        
        # Prepare agents list
        agent_list = agents or ["developer", "critic"]
        
        # Apply nest_asyncio for running async in sync context
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            logger.warning("nest_asyncio not available, async may fail in some contexts")
        
        # Run the async mission
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use run_until_complete
                result = loop.run_until_complete(orchestrator.start_mission(
                    mission_goal=mission,
                    swarm_type="execution",
                    agents=agent_list
                ))
            else:
                # No loop running, use asyncio.run
                result = asyncio.run(orchestrator.start_mission(
                    mission_goal=mission,
                    swarm_type="execution",
                    agents=agent_list
                ))
        except RuntimeError as async_error:
            # Fallback: create new loop
            logger.warning(f"Async issue: {async_error}, creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(orchestrator.start_mission(
                    mission_goal=mission,
                    swarm_type="execution",
                    agents=agent_list
                ))
            finally:
                loop.close()
        
        mission_id = result.get("mission_id", "unknown")
        status = result.get("status", "unknown")
        
        logger.info(f"✅ Swarm {mission_id} initiated with agents: {agent_list}")
        
        return {
            "success": True,
            "mission_id": mission_id,
            "status": status,
            "agents": agent_list,
            "message": f"Swarm {mission_id} started with agents {agent_list}. Agents are executing in background.",
            "check_results": f".brain/swarms/{mission_id}/summary.md",
            "check_state": ".brain/swarms/state.json"
        }
        
    except Exception as e:
        logger.error(f"❌ Swarm orchestration failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "message": f"Swarm failed to start: {e}"
        }


def _get_swarm_status(mission_id: str) -> Dict:
    """
    Check the status of a running swarm.
    
    Args:
        mission_id: The mission ID returned from _orchestrate_swarm
        
    Returns:
        Current mission state and any artifacts produced
    """
    try:
        from .orchestrator import SwarmsOrchestrator
        
        brain_path = get_brain_path()
        orchestrator = SwarmsOrchestrator(brain_path)
        
        # Check state file
        state = orchestrator._active_missions.get(mission_id)
        if not state:
            return {
                "success": False,
                "error": f"Mission {mission_id} not found"
            }
        
        # Check for artifacts
        mission_dir = brain_path / "swarms" / mission_id
        artifacts = []
        if mission_dir.exists():
            for f in mission_dir.iterdir():
                artifacts.append(str(f.name))
        
        return {
            "success": True,
            "mission_id": mission_id,
            "status": state.get("status", "unknown"),
            "step_count": state.get("step_count", 0),
            "cost_usd": state.get("cost_usd", 0),
            "artifacts": artifacts
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
