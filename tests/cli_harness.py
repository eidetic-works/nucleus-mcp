#!/usr/bin/env python3
"""
Nucleus CLI Test Harness (v0.5.0)
================================
Quick local testing without full MCP setup.
AG-011: God Mode view of the brain.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus import get_orch

async def run_harness():
    print("=== 🧠 Nucleus CLI Harness ===")
    
    # 1. Check Health (Standardized Response)
    print("\n[1] Tool: brain_health()")
    from mcp_server_nucleus import _brain_health_impl
    health = _brain_health_impl()
    print(health)
    
    # 2. Check Orchestrator
    print("\n[2] Orchestrator Verification")
    orch = get_orch()
    print(f"Orchestrator Type: {type(orch)}")
    print(f"Replica ID: {orch.replica_id}")
    
    # 3. List Tasks
    print("\n[3] Tool: brain_list_tasks()")
    from mcp_server_nucleus import _list_tasks_impl
    tasks = _list_tasks_impl()
    print(tasks)
    
    # 4. Mission Test (Dry Run Simulation)
    print("\n[4] Swarm Mission Start (Simulated)")
    # We won't actually trigger it if we're worried about costs/limits here,
    # but we can verify the method exists.
    if hasattr(orch, 'start_mission'):
        print("✅ UnifiedOrchestrator has start_mission")
    
    print("\n=== Harness Complete ===")

if __name__ == "__main__":
    if "NUCLEAR_BRAIN_PATH" not in os.environ:
        # Default to the local project brain if not set
        os.environ["NUCLEAR_BRAIN_PATH"] = "/Users/lokeshgarg/ai-mvp-backend/.brain"
    
    asyncio.run(run_harness())
