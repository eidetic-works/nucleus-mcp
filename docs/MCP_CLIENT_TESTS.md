# Nucleus V2 - MCP Client Test Suite

> **Purpose:** Manual test cases for stress testing and cold testing Nucleus V2 in Claude Desktop and Windsurf.

---

## ⚠️ Safety First!

> [!CAUTION]
> **CLI vs. Client Configuration:**
> Your Terminal does **NOT** share configuration with Claude Desktop. 
> - If you run `nucleus-init` in your terminal without flags, it will try to initialize the **current directory**.
> - If you are in your project root, this targets your **PRODUCTION BRAIN**.
> 
> **Always use explicit paths for testing:**
> `nucleus-init init /tmp/cold-start-test/.brain`

## Cold Start Tests

### Test 1: Fresh Brain Initialization (Windsurf → Claude)

**1. Windsurf (Terminal):**
Initialize the brain filesystem structure first.
```bash
# SAFETY: Must use explicit args for temp brain
rm -rf /tmp/cold-start-test/.brain  # Ensure clean slate
nucleus-init init /tmp/cold-start-test/.brain
```

**2. Claude Desktop (Prompt):**
"Check the status of the new brain"
*(Claude cannot run nucleus-init itself, but it can read the brain once created)*

**Expected:**
- Windsurf: Creates folder structure
- Claude: `brain_get_state` returns initialized state
- `state.json` has empty `current_sprint.tasks`
- `events.jsonl` is empty or minimal

### Test 2: First Task Creation
**Prompt:** "Add a new task: 'Test cold start functionality' with priority 1 and skill 'testing'"
**Expected:**
- Task created with unique ID
- Status = PENDING
- `task_created` event emitted

### Test 3: State Recovery After Restart
**Setup:** Restart Claude Desktop / Windsurf
**Prompt:** "Get the current brain state"
**Expected:**
- All previously created tasks persist
- No data loss
- Events still readable

---

## Stress Tests

### Test 4: Rapid Task Creation (10 tasks)
**Prompt:** 
```
Create 10 tasks rapidly:
1. "Stress test task 1" priority 1
2. "Stress test task 2" priority 2
3. "Stress test task 3" priority 3
...continue to 10
```
**Expected:**
- All 10 tasks created with unique IDs
- No duplicates
- All events emitted

### Test 5: Concurrent Claim Simulation
**Prompt (in two sessions):**
- Session A: "Claim task 'Stress test task 1' as agent-A"
- Session B: "Claim task 'Stress test task 1' as agent-B"
**Expected:**
- First claim succeeds
- Second claim fails with "already claimed" error
- No race condition

### Test 6: Full Workflow Stress
**Prompt:**
```
For each of 5 pending tasks:
1. Claim it
2. Update status to IN_PROGRESS
3. Mark as DONE
Report the results.
```
**Expected:**
- All 5 tasks processed
- Status transitions correct
- Events emitted for each action

### Test 7: Escalation Cascade
**Prompt:**
```
Create 3 tasks, claim them, then escalate all with reason "Testing escalation flood"
```
**Expected:**
- All 3 escalated
- `escalation_reason` set
- `claimed_by` cleared

---

## Edge Case Tests

### Test 8: Invalid Task Reference
**Prompt:** "Claim task 'nonexistent-task-id'"
**Expected:**
- Error: "Task not found"
- No state corruption

### Test 9: Invalid Dependency
**Prompt:** "Create a task blocked by 'fake-dependency-123'"
**Expected:**
- Error: "Referential integrity violation"
- Task NOT created

### Test 10: Empty Skills Match
**Prompt:** "Get next task for skills: ['nonexistent-skill-xyz']"
**Expected:**
- Returns null/no task
- No error

### Test 11: Priority Ordering Verification
**Prompt:**
```
List all pending tasks and verify they are ordered by priority (1 = highest first)
```
**Expected:**
- Priority 1 tasks before priority 2, etc.

### Test 12: Large Payload Test
**Prompt:** "Create a task with a very long description (500+ characters)"
**Expected:**
- Task created successfully
- Description preserved
- No truncation

---

## Recovery Tests

### Test 13: Corrupted State Recovery
**Setup:** Manually corrupt `state.json` (invalid JSON)
**Prompt:** "Get brain state"
**Expected:**
- Graceful error handling
- Clear error message
- No crash

### Test 14: Missing Events File
**Setup:** Delete `events.jsonl`
**Prompt:** "Read recent events"
**Expected:**
- Empty list or recreated file
- No crash

### Test 15: Disk Full Simulation
**Setup:** Fill disk or set read-only
**Prompt:** "Create a new task"
**Expected:**
- Error message about write failure
- No partial writes

---

## Performance Tests

### Test 16: Large Task List Query
**Setup:** Create 100+ tasks
**Prompt:** "List all tasks"
**Expected:**
- Response within 2 seconds
- All tasks returned

### Test 17: Event Log Pagination
**Setup:** Generate 1000+ events
**Prompt:** "Read last 50 events"
**Expected:**
- Only 50 events returned
- Most recent first

---

## Verification Checklist

| Test | Claude | Windsurf | Pass/Fail |
|:-----|:------:|:--------:|:---------:|
| 1. Fresh Brain Init | ☐ | ☐ | |
| 2. First Task Creation | ☐ | ☐ | |
| 3. State Recovery | ☐ | ☐ | |
| 4. Rapid Creation (10) | ☐ | ☐ | |
| 5. Concurrent Claim | ☐ | ☐ | |
| 6. Full Workflow Stress | ☐ | ☐ | |
| 7. Escalation Cascade | ☐ | ☐ | |
| 8. Invalid Reference | ☐ | ☐ | |
| 9. Invalid Dependency | ☐ | ☐ | |
| 10. Empty Skills | ☐ | ☐ | |
| 11. Priority Ordering | ☐ | ☐ | |
| 12. Large Payload | ☐ | ☐ | |
| 13. Corrupted State | ☐ | ☐ | |
| 14. Missing Events | ☐ | ☐ | |
| 15. Disk Full | ☐ | ☐ | |
| 16. Large List Query | ☐ | ☐ | |
| 17. Event Pagination | ☐ | ☐ | |

---

## Quick Run Commands

### Run All Cold Tests
```
Copy prompts 1-3 into Claude/Windsurf sequentially
```

### Run All Stress Tests
```
Copy prompts 4-7 into Claude/Windsurf sequentially
```

### Automated CLI Stress Test

> [!WARNING]
> This script runs directly against the path defined in `NUCLEAR_BRAIN_PATH`.
> **Double-check the path** before running to avoid filling your production brain with junk data.

```bash
cd mcp-server-nucleus
# ⚠️  VERIFY THIS PATH IS CORRECT (e.g. /tmp/...) ⚠️
NUCLEAR_BRAIN_PATH=/tmp/cold-start-test/.brain python3.11 -c "
from mcp_server_nucleus import _add_task, _list_tasks, _claim_task
import time
import os

print(f'Running against: {os.environ.get(\"NUCLEAR_BRAIN_PATH\")}')
start = time.time()
for i in range(50):
    _add_task(f'Stress test {i}', priority=i%5+1)
print(f'Created 50 tasks in {time.time()-start:.2f}s')
print(f'Total tasks: {len(_list_tasks())}')
"
```
