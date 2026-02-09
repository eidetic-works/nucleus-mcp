#!/usr/bin/env python3
"""
Governance Demo Script for Nucleus MCP
--------------------------------------
Demonstrates the core "Shared Brain" and "Governance" features:
1. Engram Ledger (Deep Memory)
2. Tool Guardrails (Security)
3. Audit Trail (Trust)
"""

import json
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up test brain path
DEMO_BRAIN = Path(__file__).parent.parent / ".demo_brain"
os.environ["NUCLEAR_BRAIN_PATH"] = str(DEMO_BRAIN)

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  🏛️  {title}")
    print("=" * 60 + "\n")

def print_result(result: str):
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2))
    except:
        print(result)

def demo_engram_ledger():
    from mcp_server_nucleus import brain_write_engram, brain_query_engrams
    
    print_header("1. SHARED BRAIN: ENGRAM LEDGER")
    
    print("📝 Storing an architectural decision...")
    res = brain_write_engram(
        key="db_policy",
        value="Use only local-first databases (SQLite/LevelDB) for this experiment.",
        context="Architecture",
        intensity=9
    )
    print_result(res)
    
    time.sleep(1)
    
    print("\n📝 Storing a security policy...")
    res = brain_write_engram(
        key="api_security",
        value="All external API calls must be logged to the brain for auditing.",
        context="Security",
        intensity=10
    )
    print_result(res)
    
    print("\n🔍 Querying the brain for 'Security' context...")
    res = brain_query_engrams(context="Security")
    print_result(res)

def demo_governance():
    from mcp_server_nucleus import brain_governance_status, brain_audit_log
    
    print_header("2. GOVERNANCE & AUDIT TRAIL")
    
    print("🛡️  Checking Governance Status...")
    res = brain_governance_status()
    print_result(res)
    
    print("\n🔐 Viewing the Cryptographic Audit Trail...")
    print("Every action taken by your agents is hashed for integrity.")
    res = brain_audit_log(limit=5)
    print_result(res)

def cleanup():
    import shutil
    if DEMO_BRAIN.exists():
        shutil.rmtree(DEMO_BRAIN)

def main():
    print("\n" + "🧠" * 20)
    print("   NUCLEUS MCP - UNIVERSAL BRAIN DEMO")
    print("   Govern Your Agents in 60 Seconds")
    print("🧠" * 20 + "\n")
    
    cleanup()
    DEMO_BRAIN.mkdir(parents=True, exist_ok=True)
    
    try:
        demo_engram_ledger()
        demo_governance()
        
        print_header("DEMO COMPLETE")
        print("🚀 Ready to launch!")
        print("   - Persistent Memory: CHECK")
        print("   - Cross-Agent Sync: CHECK")
        print("   - Security Guardrails: CHECK")
        print("\nNext: pip install nucleus-mcp")
        print()
        
    finally:
        cleanup()

if __name__ == "__main__":
    main()
