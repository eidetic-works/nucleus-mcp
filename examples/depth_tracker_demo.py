#!/usr/bin/env python3
"""
Depth Tracker Demo

Demonstrates Nucleus's Depth Tracker - protection against "rabbit holes."
Helps agents maintain focus and avoid getting lost in nested sub-problems.
"""

import os
from pathlib import Path

# Setup test environment
TEST_BRAIN = Path("/tmp/nucleus_depth_demo")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

def main():
    print("=" * 60)
    print("DEPTH TRACKER DEMO")
    print("=" * 60)
    
    print("""
The Depth Tracker prevents agents from going down "rabbit holes" -
getting lost in nested sub-problems and losing sight of the main goal.

HOW IT WORKS
------------
- Track current depth level (0 = root)
- Push when diving into a sub-topic
- Pop when returning to parent topic
- Warnings at configurable max depth
- Visual breadcrumb trail

EXAMPLE SESSION
---------------

Agent starts at root (depth 0):
> brain_depth_show()
  Depth: 0 (Root)
  Breadcrumbs: []

Agent explores "Authentication":
> brain_depth_push(topic="Authentication")
  Depth: 1
  Breadcrumbs: ["Authentication"]

Agent goes deeper into "OAuth2":
> brain_depth_push(topic="OAuth2")
  Depth: 2
  Breadcrumbs: ["Authentication", "OAuth2"]

Agent goes even deeper:
> brain_depth_push(topic="Token Refresh")
  Depth: 3
  Breadcrumbs: ["Authentication", "OAuth2", "Token Refresh"]
  ⚠️ CAUTION: Approaching max depth (5)

Agent realizes they're too deep:
> brain_depth_pop()
  Depth: 2
  Returned to: OAuth2

Reset to start fresh:
> brain_depth_reset()
  Depth: 0
  All topics cleared

DEPTH LEVELS
------------
| Level | Status   | Meaning                    |
|-------|----------|----------------------------|
| 0     | Root     | Starting point             |
| 1-2   | Safe     | Normal exploration         |
| 3     | Caution  | Getting deep               |
| 4     | Warning  | Consider returning         |
| 5+    | Critical | Definitely too deep        |

CONFIGURING MAX DEPTH
---------------------
> brain_depth_set_max(new_max=3)
  Max depth set to 3
  (Stricter for focused tasks)

> brain_depth_set_max(new_max=10)
  Max depth set to 10
  (More lenient for research)

DEPTH MAP (Visualization)
-------------------------
> brain_depth_map()

  🧠 DEPTH MAP
  ============
  
  [0] Root
   └─[1] Authentication
      └─[2] OAuth2
         └─[3] Token Refresh ← YOU ARE HERE

WHY THIS MATTERS
----------------
1. Prevents scope creep during complex tasks
2. Helps agents maintain focus
3. Creates navigable breadcrumb trail
4. Alerts when exploration is too deep
5. Enables quick "zoom out" to regain perspective

BEST PRACTICES
--------------
1. Push when starting a sub-task
2. Pop when sub-task is complete
3. Reset when starting a new main task
4. Set lower max_depth for focused work
5. Check depth_show() when feeling lost
""")

    print("=" * 60)
    print("Try these commands in your MCP client:")
    print("  brain_depth_push(topic='...')")
    print("  brain_depth_pop()")
    print("  brain_depth_show()")
    print("  brain_depth_reset()")
    print("  brain_depth_set_max(new_max=5)")
    print("  brain_depth_map()")
    print("=" * 60)

if __name__ == "__main__":
    main()
