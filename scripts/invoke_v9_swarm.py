
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
    
    mission_goal = """
    **MISSION: V9 POST-LAUNCH REALITY CHECK (BREAK THE SYSTEM)**
    
    Context: We just launched Nucleus V8 ("The Trinity Strategy").
    - Architecture: Open CLI + Closed Rust Sidecar Daemon.
    - Security: Kernel-locked secrets, Zero-Knowledge Cloud.
    - Economics: Usage-based ($20/mo + overages), 30% Marketplace take.
    
    Your Goal: Be the Adversary. Simulate the first 90 days. Find the catastrophic failures we missed.
    
    **REQUIRED OUTPUTS (Detailed & Separate):**
    
    1.  **The 'Sidecar' Exploit (CVE-2026-001):** 
        - Attack the IPC (Unix Domain Socket) between CLI and Daemon. 
        - How does a malicious VS Code extension hijack the authenticated session?
        
    2.  **The 'Pricing' Rebellion:**
        - How do users "Game" the Active Agent count to pay $0 while using 100% compute?
        - Who forks the CLI to bypass the billing heartbeat?
        
    3.  **The 'Marketplace' Poisoning:**
        - How does a "Verified" plugin introduce a sleeper vulnerability that survives WASM sandboxing?
        
    4.  **The 'Trust' Leak:**
        - What critical data did we forget to mirror to Markdown? (The one thing they can't see).
        
    Synthesize these findings into a 'V9_VULNERABILITY_REPORT.md'.
    """
    
    agents = ["critic", "devops", "strategist", "architect"]
    
    print("🚀 Launching Swarm Mission...")
    print(f"Goal: {mission_goal[:100]}...")
    
    # We call _run_mission_loop directly to block and see output, 
    # OR we use start_mission and poll. 
    # Using start_mission is 'safer' as it mimics real usage.
    
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
        print(f"\n📄 REPORT GENERATED ({summary_file}):\n")
        print("-" * 40)
        print(summary_file.read_text())
        print("-" * 40)
    else:
        print("❌ No summary file found.")

if __name__ == "__main__":
    asyncio.run(main())
