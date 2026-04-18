#!/usr/bin/env python3
"""
Nucleus Basic Usage Example

This example demonstrates how to interact with Nucleus programmatically.
Note: For normal usage, Nucleus runs as an MCP server and you interact
with it through your MCP client (Claude Desktop, Cursor, etc.)

This script is for testing and development purposes.
"""

import os
import json
from pathlib import Path

# Set up a test brain path
TEST_BRAIN = Path("/tmp/nucleus_example")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

# Now import Nucleus
from mcp_server_nucleus import (
    brain_health,
    brain_version,
)

def main():
    print("=" * 60)
    print("NUCLEUS BASIC USAGE EXAMPLE")
    print("=" * 60)
    
    # Example 1: Check health
    print("\n[1] Health Check")
    print("-" * 40)
    # Note: MCP tools return JSON strings
    # In actual MCP usage, the client handles this
    print("brain_health() - Returns system status")
    print("  Status: healthy")
    print("  Version: 0.5.1")
    print("  Tools: 130")
    
    # Example 2: Version info
    print("\n[2] Version Info")
    print("-" * 40)
    print("brain_version() - Returns version details")
    print("  Version: 0.5.1")
    print("  Codename: Sovereign")
    
    # Example 3: Engram usage
    print("\n[3] Engram Ledger (Persistent Memory)")
    print("-" * 40)
    print("brain_write_engram(key, value, context, intensity)")
    print("  Example:")
    print("    key='auth_decision'")
    print("    value='Use JWT for API auth because stateless'")
    print("    context='Architecture'")
    print("    intensity=8")
    print("")
    print("brain_query_engrams(context='Architecture', min_intensity=5)")
    print("  Returns all Architecture engrams with intensity >= 5")
    
    # Example 4: Governance
    print("\n[4] Governance Dashboard")
    print("-" * 40)
    print("brain_governance_status()")
    print("  Returns:")
    print("  - Active policies (Default-Deny, Isolation, Audit)")
    print("  - Engram count")
    print("  - Security configuration")
    
    # Example 5: Depth Tracking
    print("\n[5] Depth Tracker (Rabbit Hole Protection)")
    print("-" * 40)
    print("brain_depth_push(topic='Authentication')")
    print("  → Depth: 1, Topic: Authentication")
    print("")
    print("brain_depth_push(topic='OAuth2')")
    print("  → Depth: 2, Topic: OAuth2")
    print("  ⚠️ Caution: Getting deep!")
    print("")
    print("brain_depth_pop()")
    print("  → Depth: 1, Returned to: Authentication")
    
    # Example 6: Task Management
    print("\n[6] Task Queue")
    print("-" * 40)
    print("brain_add_task(description, priority, skills)")
    print("  Example:")
    print("    description='Implement user authentication'")
    print("    priority=1")
    print("    skills=['python', 'security']")
    print("")
    print("brain_list_tasks(status='pending')")
    print("  Returns all pending tasks")
    
    print("\n" + "=" * 60)
    print("For full documentation, see: docs/")
    print("For MCP client setup, see: docs/QUICK_START.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
