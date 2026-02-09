"""
Basic Usage Example for Nucleus MCP

This example demonstrates how to use Nucleus MCP programmatically.
Typically, you'd use it via an MCP client like Claude Desktop or Cursor,
but this shows the underlying API.
"""

import os
import tempfile
from pathlib import Path

# Set up a temporary brain for this example
with tempfile.TemporaryDirectory() as tmpdir:
    os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
    
    # Import after setting env var
    from mcp_server_nucleus import (
        brain_write_engram,
        brain_query_engrams,
        brain_get_state,
        brain_set_state,
        brain_identify_agent,
        brain_sync_now,
        brain_health,
    )
    
    print("🧠 Nucleus MCP - Basic Usage Example")
    print("=" * 50)
    
    # 1. Check health
    print("\n1. Checking brain health...")
    health = brain_health()
    print(health)
    
    # 2. Identify as an agent
    print("\n2. Registering as an agent...")
    agent = brain_identify_agent("example_agent", "python_script")
    print(agent)
    
    # 3. Store some knowledge
    print("\n3. Storing knowledge (engrams)...")
    engram1 = brain_write_engram(
        content="We decided to use PostgreSQL for the user database",
        category="decision",
        tags=["database", "architecture"]
    )
    print(engram1)
    
    engram2 = brain_write_engram(
        content="The API should use REST with JSON responses",
        category="decision",
        tags=["api", "architecture"]
    )
    print(engram2)
    
    # 4. Query knowledge
    print("\n4. Querying knowledge...")
    results = brain_query_engrams(query="database")
    print(results)
    
    # 5. Set some state
    print("\n5. Setting project state...")
    state = brain_set_state("current_sprint", "MVP Genesis")
    print(state)
    
    state = brain_set_state("team_size", "1")
    print(state)
    
    # 6. Get state
    print("\n6. Getting current state...")
    current_state = brain_get_state()
    print(current_state)
    
    # 7. Sync
    print("\n7. Syncing brain...")
    sync = brain_sync_now()
    print(sync)
    
    print("\n" + "=" * 50)
    print("✅ Example complete!")
    print(f"Brain location: {tmpdir}")
    print("\nIn real usage, other AI tools (Claude, Cursor, Windsurf)")
    print("would be able to access this same brain and share context.")
