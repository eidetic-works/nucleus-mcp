#!/usr/bin/env python3
"""
Task Management Demo

Demonstrates Nucleus's Task Queue - the orchestration layer for agent work.
Supports priorities, skills, claiming, and multi-agent coordination.
"""

import os
from pathlib import Path

# Setup test environment
TEST_BRAIN = Path("/tmp/nucleus_task_demo")
TEST_BRAIN.mkdir(parents=True, exist_ok=True)
(TEST_BRAIN / "ledger").mkdir(exist_ok=True)
os.environ["NUCLEAR_BRAIN_PATH"] = str(TEST_BRAIN)

def main():
    print("=" * 60)
    print("TASK MANAGEMENT DEMO")
    print("=" * 60)
    
    print("""
Nucleus provides a full task queue for orchestrating agent work.
Tasks can be prioritized, assigned skills, claimed by agents, and tracked.

ADDING TASKS
------------
> brain_add_task(
    description="Implement user authentication",
    priority=1,              # 1=highest, 5=lowest
    skills=["python", "security"]
  )

Returns:
{
  "id": "task-abc123",
  "description": "Implement user authentication",
  "priority": 1,
  "status": "pending",
  "skills": ["python", "security"],
  "created_at": "2026-01-26T20:00:00Z"
}

LISTING TASKS
-------------
> brain_list_tasks(status="pending")

Returns all pending tasks sorted by priority.

> brain_list_tasks(skill="python")

Returns tasks requiring Python skills.

CLAIMING TASKS
--------------
> brain_claim_task(task_id="task-abc123", agent_id="agent-1")

Claims a task for an agent. Prevents other agents from working on it.

UPDATING TASKS
--------------
> brain_update_task(
    task_id="task-abc123",
    status="in_progress"
  )

> brain_complete_task(task_id="task-abc123")

PRIORITY LEVELS
---------------
| Level | Meaning              | Use For                    |
|-------|----------------------|----------------------------|
| 1     | Critical             | Blockers, security issues  |
| 2     | High                 | Important features         |
| 3     | Medium (default)     | Normal work                |
| 4     | Low                  | Nice to have               |
| 5     | Backlog              | Future consideration       |

SKILL-BASED ROUTING
-------------------
Tasks can specify required skills:
- ["python", "security"] - Needs both
- ["frontend"] - UI work
- ["research"] - Investigation
- ["devops"] - Infrastructure

Agents declare their skills and get matched to appropriate tasks.

MULTI-AGENT COORDINATION
------------------------
> brain_orchestrate_swarm(
    mission="Build authentication system",
    agents=["coder-1", "reviewer-1", "tester-1"]
  )

Automatically:
1. Decomposes mission into tasks
2. Assigns based on skills
3. Tracks dependencies
4. Reports progress

DASHBOARD
---------
> brain_dashboard()

Returns ASCII visualization:
```
📊 NUCLEUS DASHBOARD
====================

Tasks by Status:
  pending:     12 ████████████
  in_progress:  3 ███
  completed:   45 █████████████████████████████████████████████

Priority Distribution:
  P1 (critical): 2
  P2 (high):     5
  P3 (medium):  10
```

WHY THIS MATTERS
----------------
1. Prevents task conflicts between agents
2. Ensures high-priority work gets done first
3. Matches tasks to agent capabilities
4. Provides visibility into work status
5. Enables autonomous multi-agent workflows
""")

    print("=" * 60)
    print("Try these commands in your MCP client:")
    print("  brain_add_task(description='...', priority=2)")
    print("  brain_list_tasks()")
    print("  brain_claim_task(task_id='...', agent_id='...')")
    print("  brain_dashboard()")
    print("=" * 60)

if __name__ == "__main__":
    main()
