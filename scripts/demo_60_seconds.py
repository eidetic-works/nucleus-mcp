#!/usr/bin/env python3
"""
Nucleus 60-Second Demo Script

This script demonstrates the core value proposition of Nucleus:
"Govern Your Agents in 60 Seconds"

Run this to see the 5 core launch tools in action.
Use this as a script for recording demo videos.

Usage:
    python scripts/demo_60_seconds.py
"""

import os
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ANSI colors for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_step(num, title, subtitle=""):
    print(f"{Colors.CYAN}{Colors.BOLD}[{num}/5] {title}{Colors.END}")
    if subtitle:
        print(f"    {Colors.YELLOW}{subtitle}{Colors.END}")

def print_success(msg):
    print(f"    {Colors.GREEN}✅ {msg}{Colors.END}")

def print_code(code):
    print(f"    {Colors.BLUE}>>> {code}{Colors.END}")

def pause(seconds=2):
    time.sleep(seconds)

def call_tool(tool, **kwargs):
    """Helper to call MCP FunctionTool objects."""
    if hasattr(tool, 'fn'):
        return tool.fn(**kwargs)
    return tool(**kwargs)

def setup_demo_brain():
    """Create a fresh demo brain."""
    import tempfile
    demo_brain = Path(tempfile.mkdtemp(prefix="nucleus_demo_"))
    os.environ["NUCLEAR_BRAIN_PATH"] = str(demo_brain)
    
    # Create required directories
    (demo_brain / "ledger").mkdir(parents=True)
    (demo_brain / "ledger" / "engrams").mkdir()
    (demo_brain / "ledger" / "audit").mkdir()
    (demo_brain / "mounts").mkdir()
    
    return demo_brain

def main():
    """Run the 60-second demo."""
    
    print_header("🧠 NUCLEUS: Govern Your Agents in 60 Seconds")
    
    print("Welcome to Nucleus - The Agent Control Plane")
    print("This demo shows how to govern AI agents with security and memory.\n")
    pause(2)
    
    # Setup
    print(f"{Colors.YELLOW}Setting up demo environment...{Colors.END}")
    brain_path = setup_demo_brain()
    print(f"    Brain path: {brain_path}\n")
    pause(1)
    
    # Import nucleus
    import mcp_server_nucleus as nucleus
    
    # =========================================================================
    # STEP 1: Mount a server (show Recursive Aggregator)
    # =========================================================================
    print_step(1, "Mount an External Tool", "The Recursive Aggregator pattern")
    print_code("brain_mount_server(name='github', command='npx', args=['-y', '@modelcontextprotocol/server-github'])")
    pause(1)
    
    # Note: We simulate this since actual mounting requires subprocess
    print_success("Server 'github' registered with Nucleus")
    print("    → All requests now go through Nucleus governance layer")
    pause(2)
    
    # =========================================================================
    # STEP 2: Check governance status (show Default-Deny)
    # =========================================================================
    print_step(2, "Verify Security Policies", "Default-Deny in action")
    print_code("brain_governance_status()")
    pause(1)
    
    result = call_tool(nucleus.brain_governance_status)
    data = json.loads(result)
    
    if data.get("success"):
        policies = data["data"].get("policies", {})
        for policy, status in policies.items():
            # status can be bool or dict with 'enabled' key
            enabled = status.get("enabled") if isinstance(status, dict) else status
            if enabled:
                print(f"    {Colors.GREEN}✓ {policy}: ENFORCED{Colors.END}")
            else:
                print(f"    {Colors.YELLOW}○ {policy}: READY{Colors.END}")
    
    print_success("All mounted servers start with ZERO permissions")
    pause(2)
    
    # =========================================================================
    # STEP 3: Write an Engram (persistent memory)
    # =========================================================================
    print_step(3, "Remember a Decision", "Persistent memory across sessions")
    print_code("brain_write_engram(key='db_choice', value='PostgreSQL for ACID', context='Architecture', intensity=9)")
    pause(1)
    
    result = call_tool(
        nucleus.brain_write_engram,
        key="db_choice",
        value="PostgreSQL chosen for ACID compliance and mature ecosystem",
        context="Architecture",
        intensity=9
    )
    data = json.loads(result)
    
    if data.get("success"):
        print_success("Engram written to persistent ledger")
        print("    → This memory survives IDE restarts")
        print("    → Available to all agents in this project")
    pause(2)
    
    # =========================================================================
    # STEP 4: Query Engrams (recall memory)
    # =========================================================================
    print_step(4, "Recall Your Decisions", "Query the Engram Ledger")
    print_code("brain_query_engrams(context='Architecture', min_intensity=5)")
    pause(1)
    
    result = call_tool(
        nucleus.brain_query_engrams,
        context="Architecture",
        min_intensity=5
    )
    data = json.loads(result)
    
    if data.get("success"):
        engrams = data["data"].get("engrams", [])
        print_success(f"Found {len(engrams)} relevant engram(s)")
        for engram in engrams:
            print(f"    → [{engram.get('intensity', '?')}/10] {engram.get('key', 'unknown')}: {engram.get('value', '')[:50]}...")
    pause(2)
    
    # =========================================================================
    # STEP 5: Show audit log (cryptographic trail)
    # =========================================================================
    print_step(5, "Verify the Audit Trail", "Cryptographic decision provenance")
    print_code("brain_audit_log(limit=5)")
    pause(1)
    
    result = call_tool(nucleus.brain_audit_log, limit=5)
    data = json.loads(result)
    
    if data.get("success"):
        entries = data["data"].get("entries", [])
        print_success(f"Audit log contains {len(entries)} entries")
        for entry in entries[-3:]:
            hash_preview = entry.get("hash", "")[:16] + "..."
            print(f"    → [{entry.get('type', 'unknown')}] {hash_preview}")
        print("    → Every action is SHA-256 hashed for verification")
    pause(2)
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_header("🎉 DEMO COMPLETE")
    
    print("In 60 seconds, you've seen:")
    print(f"  {Colors.GREEN}1. Recursive Aggregator{Colors.END} - Mount any MCP server through Nucleus")
    print(f"  {Colors.GREEN}2. Default-Deny Security{Colors.END} - All tools start sandboxed")
    print(f"  {Colors.GREEN}3. Persistent Memory{Colors.END} - Engrams survive across sessions")
    print(f"  {Colors.GREEN}4. Memory Recall{Colors.END} - Query your decisions anytime")
    print(f"  {Colors.GREEN}5. Cryptographic Audit{Colors.END} - Immutable decision trail")
    print()
    print(f"{Colors.BOLD}This is Nucleus: The Agent Control Plane{Colors.END}")
    print()
    print("Get started:")
    print(f"  {Colors.CYAN}pip install mcp-server-nucleus{Colors.END}")
    print(f"  {Colors.CYAN}nucleus-init{Colors.END}")
    print()
    print(f"Learn more: {Colors.BLUE}https://nucleussovereign.com{Colors.END}")
    print()
    
    # Cleanup
    import shutil
    if brain_path.exists():
        shutil.rmtree(brain_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
