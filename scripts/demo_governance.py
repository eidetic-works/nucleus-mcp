#!/usr/bin/env python3
"""
Governance Demo Script for Nucleus Sovereign OS

Run this to demonstrate the Agent Control Plane features:
- Engram Ledger (persistent memory)
- Audit Trail (cryptographic logging)
- Governance Status dashboard

Usage:
    PYTHONPATH=src python3 scripts/demo_governance.py
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
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  🏛️  {title}")
    print("=" * 60 + "\n")


def print_result(result: str):
    """Pretty print a JSON result."""
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        print(result)


def demo_engram_ledger():
    """Demonstrate the Engram Ledger functionality."""
    from mcp_server_nucleus import _brain_write_engram_impl, _brain_query_engrams_impl
    
    print_header("ENGRAM LEDGER DEMO")
    
    print("📝 Writing critical decision engram (intensity=10)...")
    result = _brain_write_engram_impl(
        key="no_openai",
        value="Budget constraint: Use Gemini API only, never OpenAI",
        context="Decision",
        intensity=10
    )
    print_result(result)
    
    time.sleep(0.5)
    
    print("\n📝 Writing architectural decision (intensity=8)...")
    result = _brain_write_engram_impl(
        key="db_choice",
        value="PostgreSQL for production, SQLite for local dev",
        context="Architecture",
        intensity=8
    )
    print_result(result)
    
    time.sleep(0.5)
    
    print("\n📝 Writing brand decision (intensity=6)...")
    result = _brain_write_engram_impl(
        key="color_scheme",
        value="Purple primary (#7C3AED) with pink accent",
        context="Brand",
        intensity=6
    )
    print_result(result)
    
    print("\n" + "-" * 40)
    print("🔍 Querying all engrams (sorted by intensity)...")
    result = _brain_query_engrams_impl(context=None, min_intensity=1)
    print_result(result)
    
    print("\n" + "-" * 40)
    print("🔍 Querying critical engrams only (intensity >= 8)...")
    result = _brain_query_engrams_impl(context=None, min_intensity=8)
    print_result(result)


def demo_audit_trail():
    """Demonstrate the cryptographic audit trail."""
    from mcp_server_nucleus import _brain_audit_log_impl
    
    print_header("AUDIT TRAIL DEMO")
    
    print("🔐 The Immutable Why-Trace")
    print("Every interaction is SHA-256 hashed for integrity verification.\n")
    
    result = _brain_audit_log_impl(limit=5)
    print_result(result)
    
    print("\n💡 Each hash proves: WHO did WHAT, WHEN, and WHY.")
    print("   This is cryptographic accountability for agent decisions.")


def demo_governance_status():
    """Demonstrate the governance dashboard."""
    from mcp_server_nucleus import _brain_governance_status_impl
    
    print_header("GOVERNANCE STATUS DEMO")
    
    print("🛡️  The Governance Moat\n")
    
    result = _brain_governance_status_impl()
    print_result(result)
    
    print("\n📋 Policy Enforcement:")
    print("   ✅ Default-Deny: All tools start with NO access")
    print("   ✅ Isolation: Tools can't see each other")
    print("   ✅ Audit: Every decision is logged")


def cleanup():
    """Clean up demo brain directory."""
    import shutil
    if DEMO_BRAIN.exists():
        shutil.rmtree(DEMO_BRAIN)


def main():
    """Run the full governance demo."""
    print("\n" + "🧠" * 30)
    print("\n   NUCLEUS SOVEREIGN OS - GOVERNANCE DEMO")
    print("   The Agent Control Plane")
    print("\n" + "🧠" * 30)
    
    # Clean up any previous demo
    cleanup()
    
    # Create fresh demo brain
    DEMO_BRAIN.mkdir(parents=True, exist_ok=True)
    (DEMO_BRAIN / "ledger").mkdir(exist_ok=True)
    (DEMO_BRAIN / "engrams").mkdir(exist_ok=True)
    
    try:
        # Run demos
        demo_engram_ledger()
        demo_audit_trail()
        demo_governance_status()
        
        print_header("DEMO COMPLETE")
        print("🎯 Key Takeaways:")
        print("   1. Engrams persist decisions across sessions")
        print("   2. Audit trail provides cryptographic proof")
        print("   3. Governance policies are always enforced")
        print("\n📦 Install: pip install nucleus-mcp")
        print("🔗 GitHub: github.com/eidetic-works/nucleus-mcp")
        print()
        
    finally:
        # Cleanup
        cleanup()


if __name__ == "__main__":
    main()
