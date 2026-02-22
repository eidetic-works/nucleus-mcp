
import asyncio
import os
import sys
import time
import json
from pathlib import Path

# Add src to path to allow imports
sys.path.append(os.path.abspath("src"))

from mcp_server_nucleus.runtime.orchestrator import SwarmsOrchestrator

async def main():
    brain_path = Path("/Users/lokeshgarg/.gemini/antigravity/brain/b95f3ae4-2e33-4132-a8c3-8ecf4024f5ae")
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain_path)
    
    print(f"🧠 Initializing Swarm Orchestrator at {brain_path}")
    orchestrator = SwarmsOrchestrator(brain_path)
    
    # MISSION: V10 PREMIUM SCALE
    mission_goal = """
    **MISSION: V10 PREMIUM 'CODE RED' SCALE SIMULATION**
    
    Context: You are the AI Architect for 'MegaCorp' (Premium Tier Customer).
    Scenario: A critical security vulnerability has been found in your 100 AWS microservices.
    Objective: Migrate ALL 100 microservices to Google Cloud Run within 24 hours using Nucleus Swarms.
    
    **EXECUTION PLAN (Simulated concurrency):**
    Spawn 25 concurrent ephemeral agents to handle this massive workload.
    
    **AGENTS REQUIRED:**
    1. **Architect:** Design the migration pattern (AWS Lambda -> Cloud Run).
    2. **Strategist:** Plan the rollback strategy if migration fails.
    3. **DevOps:** Generate the Terraform for GCP.
    4. **Researcher:** Verify GCP quota limits for 100 concurrent services.
    5. **Critic:** Analyze the cost implication of this migration ($$$).
    6. **Developer:** Write the Dockerfile templates.
    
    **OUTPUT REQUIREMENT:**
    Produce a 'MONSTER_REPORT_V10.md' that details:
    - **Coordination Costs:** Did the agents step on each other's toes?
    - **Latency:** How much did the 'Brain' slow down under this load?
    - **Value:** justify the $5,000 cost of this 24-hour mission to the CFO.
    """
    
    # We list many agents to simulate load, even if the runtime processes them sequentially/batched
    agents = [
        "architect", "strategist", "devops", "researcher", "critic", "developer",
        "devops", "developer", "critic" # Extra agents for load
    ]
    
    print("🚀 Launching V10 PREMIUM Scalability Mission...")
    print(f"Goal: {mission_goal[:100]}...")
    
    result = await orchestrator.start_mission(
        mission_goal=mission_goal,
        swarm_type="execution",
        agents=agents
    )
    
    mission_id = result["mission_id"]
    print(f"✅ Mission Started: {mission_id}")
    
    # Poll for completion
    print("⏳ Waiting for Swarm to return...")
    while True:
        status = await orchestrator.get_mission_status(mission_id)
        current_state = status.get("status", "unknown")
        step = status.get("step_count", 0)
        
        print(f"   Status: {current_state} (Step {step})")
        
        if current_state in ["completed", "failed", "halted_steps", "halted_budget"]:
            break
            
        time.sleep(2)
        
    print(f"🏁 Mission Finished: {current_state}")
    
    # Read artifacts
    swarm_dir = brain_path / "swarms" / mission_id
    summary_file = swarm_dir / "summary.md"
    
    if summary_file.exists():
        print(f"\n📄 MONSTER REPORT GENERATED ({summary_file}):\n")
        print("-" * 40)
        print(summary_file.read_text())
        print("-" * 40)
    else:
        print("❌ No summary file found.")

if __name__ == "__main__":
    asyncio.run(main())
