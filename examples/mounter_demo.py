#!/usr/bin/env python3
"""
Recursive Mounter Demo

Demonstrates Nucleus's Recursive Mounter - the ability to mount and orchestrate
external MCP servers as children under the Nucleus control plane.
"""

import os
from pathlib import Path

# Setup test environment
TEST_BRAIN = Path("/tmp/nucleus_mounter_demo")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

def main():
    print("=" * 60)
    print("RECURSIVE MOUNTER DEMO")
    print("=" * 60)
    
    print("""
The Recursive Mounter allows Nucleus to mount external MCP servers
as "children" under its governance umbrella. This is the foundation
of the "Recursive Aggregator" architecture.

MOUNTING A SERVER
-----------------
> brain_mount_server(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  )

Returns:
{
  "id": "mnt-abc123",
  "name": "filesystem",
  "status": "mounted",
  "tools_available": 5
}

LISTING MOUNTED SERVERS
-----------------------
> brain_list_mounted()

Returns:
[
  {
    "id": "mnt-abc123",
    "name": "filesystem",
    "status": "active",
    "mounted_at": "2026-01-26T20:00:00Z"
  },
  {
    "id": "mnt-def456",
    "name": "github",
    "status": "active",
    "mounted_at": "2026-01-26T20:05:00Z"
  }
]

DISCOVERING TOOLS
-----------------
> brain_discover_mounted_tools(server_id="mnt-abc123")

Returns tools available from the mounted server:
{
  "server": "filesystem",
  "tools": [
    {"name": "read_file", "description": "..."},
    {"name": "write_file", "description": "..."},
    {"name": "list_directory", "description": "..."}
  ]
}

UNMOUNTING A SERVER
-------------------
> brain_unmount_server(server_id="mnt-abc123")

Cleanly disconnects the server and removes it from the registry.

ARCHITECTURE
------------

┌─────────────────────────────────────────────────────────────┐
│                    NUCLEUS (Host Layer)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Governance Policies                      │    │
│  │  (Default-Deny, Isolation, Audit)                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│     ┌─────────┐     ┌─────────┐     ┌─────────┐            │
│     │ Child 1 │     │ Child 2 │     │ Child 3 │            │
│     │ (FS)    │     │ (GitHub)│     │ (Custom)│            │
│     └─────────┘     └─────────┘     └─────────┘            │
└─────────────────────────────────────────────────────────────┘

PERSISTENCE
-----------
Mounts are persisted to `.brain/ledger/mounts.json` and
automatically restored on Nucleus restart.

GOVERNANCE INTEGRATION
----------------------
All calls to mounted servers go through Nucleus's governance:
1. Policy check (default-deny)
2. Audit logging
3. Isolation enforcement
4. Result validation

The mounted server CANNOT bypass these controls.

COMMON USE CASES
----------------
1. Mount filesystem server for file operations
2. Mount GitHub server for repo management
3. Mount database server for data access
4. Mount custom servers for specialized tools

WHY THIS MATTERS
----------------
1. Unified governance across all MCP servers
2. Single audit trail for all tool calls
3. Consistent security policies
4. Simplified agent configuration
5. Foundation for multi-server orchestration
""")

    print("=" * 60)
    print("Try these commands in your MCP client:")
    print("  brain_mount_server(name='...', command='...', args=[...])")
    print("  brain_list_mounted()")
    print("  brain_discover_mounted_tools(server_id='...')")
    print("  brain_unmount_server(server_id='...')")
    print("=" * 60)

if __name__ == "__main__":
    main()
