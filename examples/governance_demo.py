#!/usr/bin/env python3
"""
Governance Demo

Demonstrates Nucleus's Governance Moat - the security features that make
Nucleus an Agent CONTROL Plane rather than just an Agent Context file.
"""

import os
from pathlib import Path

# Setup test environment
TEST_BRAIN = Path("/tmp/nucleus_governance_demo")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

def main():
    print("=" * 60)
    print("GOVERNANCE MOAT DEMO")
    print("=" * 60)
    
    print("""
The Governance Moat is what separates Nucleus from static context files
like CLAUDE.md or .cursorrules. It provides ACTIVE CONTROL, not just context.

THE THREE PILLARS
-----------------

1. DEFAULT-DENY SECURITY
   - Every mounted MCP server starts with NO permissions
   - Explicit approval required for each capability
   - No silent execution - you always know what's happening
   
2. ISOLATION BOUNDARIES
   - Tools cannot see each other's state
   - No access to full chat history
   - Tokens stored in Host, never passed to agents
   
3. IMMUTABLE AUDIT TRAIL
   - Every interaction logged with SHA-256 hash
   - Hash chain makes tampering detectable
   - Full decision trail: Who/Why/When

GOVERNANCE DASHBOARD
--------------------
> brain_governance_status()

Returns:
{
  "policies": {
    "default_deny": true,
    "isolation_boundaries": true,
    "immutable_audit": true
  },
  "engram_count": 42,
  "audit_entries": 1337,
  "security_level": "SOVEREIGN"
}

AUDIT TRAIL
-----------
> brain_audit_log(limit=10)

Returns last 10 interactions:
[
  {
    "timestamp": "2026-01-26T20:00:00Z",
    "action": "tool_call",
    "tool": "brain_write_engram",
    "params_hash": "sha256:abc123...",
    "result_hash": "sha256:def456...",
    "prev_hash": "sha256:789xyz..."
  },
  ...
]

CONTEXT VS. CONTROL
-------------------

| Aspect       | CLAUDE.md          | Nucleus                    |
|--------------|--------------------|-----------------------------|
| Type         | Static text file   | Active runtime              |
| Enforcement  | Honor system       | Default-deny policies       |
| Memory       | Session-bound      | Persistent (Engram Ledger)  |
| Audit        | None               | SHA-256 hash chain          |
| Security     | Prompt injection   | Isolation boundaries        |
| State        | Read-only          | Dynamic, stateful           |

CLAUDE.md says "please don't do bad things."
Nucleus ENFORCES that bad things cannot happen.

WHY THIS MATTERS
----------------
1. Compliance - Auditable trail for enterprise
2. Safety - Agents can't exceed their boundaries
3. Trust - Verify agent actions cryptographically
4. Control - You're always in command

THE SOVEREIGNTY PLEDGE
----------------------
"Your agents, your rules, your data.
 Nucleus enforces YOUR policies, not ours.
 No phoning home. No hidden telemetry.
 Sovereignty is not a feature - it's the foundation."
""")

    print("=" * 60)
    print("Try these commands in your MCP client:")
    print("  brain_governance_status()")
    print("  brain_audit_log(limit=20)")
    print("  brain_health()")
    print("=" * 60)

if __name__ == "__main__":
    main()
