import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.agent_pool import AgentPool, AgentStatus

def verify_jit_consent():
    print("--- 🛡️ NUCLEUS JIT CONSENT TEST ---")
    
    pool = AgentPool()
    agent_id = "agent_jit"
    pool.spawn_agent(agent_id, "gemini-pro", "RESEARCH")
    
    # 1. Simulate Exhaustion
    print(f"\n[Exhausting Agent]")
    pool.exhaust_agent(agent_id)
    agent = pool.agent_registry[agent_id]
    print(f"Status after exhaustion: {agent.status}")
    
    # 2. Try respawn WITHOUT consent
    print(f"\n[Attempting Respawn without consent]")
    respawn_no_consent = pool.respawn_agent(agent_id)
    print(f"Respawn No-Consent Strategy: {respawn_no_consent.get('strategy')}")
    print(f"Context Cleared: {respawn_no_consent.get('context_cleared')}")
    
    if not respawn_no_consent.get('context_cleared'):
        print("❌ FAILED: Should have cleared context by default.")
        return

    # 3. Simulate Choice: WARM
    print(f"\n[Submitting WARM-START Consent]")
    pool.exhaust_agent(agent_id) # Exhaust again
    pool.submit_consent(agent_id, "warm")
    respawn_warm = pool.respawn_agent(agent_id)
    print(f"Respawn WARM Strategy: {respawn_warm.get('strategy')}")
    print(f"Context Cleared: {respawn_warm.get('context_cleared')}")
    
    if respawn_warm.get('context_cleared'):
        print("❌ FAILED: Should have preserved context for WARM.")
        return

    # 4. Simulate Choice: COLD
    print(f"\n[Submitting COLD-START Consent]")
    pool.exhaust_agent(agent_id) # Exhaust again
    pool.submit_consent(agent_id, "cold")
    respawn_cold = pool.respawn_agent(agent_id)
    print(f"Respawn COLD Strategy: {respawn_cold.get('strategy')}")
    print(f"Context Cleared: {respawn_cold.get('context_cleared')}")
    
    if not respawn_cold.get('context_cleared'):
        print("❌ FAILED: Should have cleared context for COLD.")
        return

    print("\n✅ Verification SUCCESS: JIT Consent Loop is fully functional.")

if __name__ == "__main__":
    verify_jit_consent()
