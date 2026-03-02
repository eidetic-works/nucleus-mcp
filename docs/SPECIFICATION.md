# Nucleus V2 Specification: Agent-Native Task Orchestration

> **"A brain that remembers your intent so you don't have to."**

*Generated after 14 exhaustive thinking passes. This is the definitive specification for Nucleus task orchestration.*

---

## 1. Executive Summary

### What Is Nucleus?

Nucleus is the **Agent Control Plane**—a persistent, declarative task orchestrator that transforms chatbots into governed, auditable co-workers.

### The Problem

| Without Nucleus | With Nucleus |
| :--- | :--- |
| Re-explain project status every session | Agent already knows the sprint status |
| Agents don't coordinate | Shared state enables handoffs |
| Context lost on restart | Persistent memory survives crashes |
| Manual task assignment | Priority-based pull system |

### The Formula

```
Nucleus = Persistent State + Priority Queue + Skill Routing + Claim Protocol + Human Escalation
```

---

## 2. First Principles

### Why Not Copy Human Workflows?

Human Agile (Scrum) was designed for:
- Limited memory → Daily standups
- Social needs → Retrospectives  
- Fatigue → Sprints
- Verbal brains → Meetings

AI agents have NONE of these constraints:
- **Perfect memory** (if written to disk)
- **No ego** (no recognition needed)
- **No fatigue** (24/7 operation)
- **Telepathy** (read same file = instant sync)

### The Agent-Native Model

| Human Paradigm | Agent Paradigm |
| :--- | :--- |
| Push (manager assigns) | **Pull** (agent claims) |
| Fixed sprints | **Dynamic re-prioritization** |
| Daily standups | **Continuous event stream** |
| Role-based routing | **Skill-based routing** |
| Subjective review | **Verifiable postconditions** |

### The Core Insight

```
Agents = Pure Functions (State → State')
Tasks = State Transitions (Pre → Post)
Dependencies = Data Pipes (Output → Input)
Orchestration = Reconciliation Loop (Desired ↔ Actual)
```

---

## 3. The Four Enemies

Nucleus fights against:

| Enemy | Manifestation | Solution |
| :--- | :--- | :--- |
| **Entropy** | Chaos without coordination | Priority queue |
| **Amnesia** | Context lost between sessions | Persistent state |
| **Friction** | Overhead slows progress | Minimal schema |
| **Drift** | Goals diverge from intent | Goal hierarchy |

---

## 4. The Five Principles

### 1. Legibility
Human can read `state.json` and fully understand system state.

### 2. Reversibility
No action causes permanent damage. Everything is mutable.

### 3. Graceful Degradation
Any component can fail and system still works (manual fallback).

### 4. Trust
Every component must be trustworthy or explicitly flag uncertainty.

### 5. Simplicity
Ship fast, evolve later. Complexity is the enemy.

---

## 5. Task Schema (V1)

```json
{
  "id": "uuid",
  "description": "string",
  "status": "PENDING | READY | IN_PROGRESS | BLOCKED | DONE | FAILED | ESCALATED",
  "priority": 1,
  "blocked_by": ["task-id"],
  "required_skills": ["skill"],
  "claimed_by": "agent-id | null",
  "source": "user | synthesizer",
  "escalation_reason": "string | null",
  "created_at": "ISO",
  "updated_at": "ISO"
}
```

### Field Definitions

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Unique identifier |
| `description` | string | What needs to be done |
| `status` | enum | Current state in lifecycle |
| `priority` | 1-5 | 1 = highest, 5 = lowest |
| `blocked_by` | [task-id] | Hard dependencies (DAG) |
| `required_skills` | [skill] | For routing to capable agents |
| `claimed_by` | agent-id \| null | Prevents race conditions |
| `source` | enum | "user" = priority override |
| `escalation_reason` | string \| null | Why human help needed |
| `created_at` | ISO timestamp | For audit |
| `updated_at` | ISO timestamp | For observability |

### Status State Machine

```
PENDING → READY → IN_PROGRESS → DONE
    ↓         ↓           ↓
 BLOCKED   BLOCKED      FAILED
                          ↓
                      ESCALATED
```

---

## 6. Tools (V1)

### 6.1 `brain_list_tasks`

**Purpose:** Query tasks by filter criteria.

**Parameters:**
```json
{
  "status": "optional, filter by status",
  "priority": "optional, filter by priority",
  "skill": "optional, filter by required skill",
  "claimed_by": "optional, filter by claimant"
}
```

**Returns:** Array of matching tasks.

---

### 6.2 `brain_get_next_task`

**Purpose:** Get the highest-priority unblocked task for given skills.

**Parameters:**
```json
{
  "skills": ["skill1", "skill2"]
}
```

**Logic:**
1. Filter by skill match
2. Exclude BLOCKED, DONE, FAILED, ESCALATED
3. Exclude already claimed
4. Sort by priority (ascending, 1 = highest)
5. Return top result

**Returns:** Single task or null.

---

### 6.3 `brain_claim_task`

**Purpose:** Atomically claim a task to prevent races.

**Parameters:**
```json
{
  "task_id": "uuid",
  "agent_id": "thread-id"
}
```

**Logic:**
1. Check task exists and is READY
2. Check not already claimed
3. Set `claimed_by` and `status` to IN_PROGRESS
4. Update `updated_at`

**Returns:** Success or failure with reason.

---

### 6.4 `brain_update_task`

**Purpose:** Modify task fields.

**Parameters:**
```json
{
  "task_id": "uuid",
  "updates": {
    "status": "optional",
    "priority": "optional",
    "description": "optional"
  }
}
```

**Returns:** Updated task.

---

### 6.5 `brain_add_task`

**Purpose:** Create a new task.

**Parameters:**
```json
{
  "description": "required",
  "priority": "optional, default 3",
  "blocked_by": "optional",
  "required_skills": "optional",
  "source": "optional, default synthesizer"
}
```

**Logic:**
1. Generate UUID
2. Set status to PENDING (or BLOCKED if blocked_by is set)
3. Set timestamps

**Returns:** Created task.

---

### 6.6 `brain_escalate`

**Purpose:** Request human help when agent is stuck.

**Parameters:**
```json
{
  "task_id": "uuid",
  "reason": "string describing why help is needed"
}
```

**Logic:**
1. Set status to ESCALATED
2. Set escalation_reason
3. Unclaim task (claimed_by = null)

**Returns:** Success.

---

## 7. Safety Properties (Invariants)

These must ALWAYS hold:

| Property | Meaning |
| :--- | :--- |
| Single Status | A task has exactly ONE status at any time |
| Mutual Exclusion | A claimed task cannot be double-claimed |
| Consistency | A BLOCKED task cannot be IN_PROGRESS |
| DAG Property | No circular dependencies |
| Referential Integrity | `blocked_by` references must exist |

---

## 8. Liveness Properties

These must EVENTUALLY happen:

| Property | Meaning |
| :--- | :--- |
| Progress | Every PENDING task eventually becomes READY or BLOCKED |
| Completion | Every IN_PROGRESS task eventually becomes DONE, FAILED, or ESCALATED |
| Termination | Queue eventually empties if no new tasks |

---

## 9. Evolution Roadmap

### V1: Coordination (Current Scope)
- Priority queue
- Skill routing
- Dependency DAG
- Claim locking
- Human escalation

### V2: Intelligence
- Postcondition verification
- Trust levels (graduated autonomy)
- Cost tracking (token budgets)
- Learning (outcome patterns)
- Timeout bounds

### V3: Autonomy
- Reconciliation loop (desired ↔ actual)
- Auto-decomposition
- Exploration budget
- Self-improvement
- Predictive tasking

---

## 10. Comparison to Alternatives

### Why Not Jira?
Jira is designed for humans (rich UI, comments, attachments).
Nucleus is designed for agents (structured JSON, atomic tools).

### Why Not LangGraph?
LangGraph state is in-memory (dies on crash).
Nucleus state is on disk (survives restarts).

### Why Not mcp-server-memory?
Memory MCP stores **facts** ("Lokesh likes Python").
Nucleus stores **process** ("Sprint 2 is 50% done, Architect is blocked").

### Competitive Matrix

| Feature | **Nucleus** | mcp-memory | MemGPT | Zep AI |
| :--- | :---: | :---: | :---: | :---: |
| Remembers Facts | ✅ | ✅ | ✅ | ✅ |
| Remembers Tasks/Sprint | ✅ | ❌ | ❌ | ❌ |
| Role Management | ✅ | ❌ | ❌ | ❌ |
| Multi-Agent Sync | ✅ | ❌ | ❌ | ❌ |
| Local-First | ✅ | ✅ | ⚠️ | ❌ |
| MCP Native | ✅ | ✅ | ❌ | ❌ |

---

## 11. Success Criteria

| Metric | Target |
| :--- | :--- |
| Daily use | 2 weeks without abandonment |
| Tasks completed | At least 10 through system |
| User sentiment | "This actually helps" |

## 12. Failure Criteria

| Signal | Meaning |
| :--- | :--- |
| Abandoned after 1 day | Too much friction |
| More overhead than savings | Over-engineered |
| Debug time > Use time | System is the problem |

---

## 13. Anti-Patterns (Never Do)

1. Never execute without human visibility path
2. Never delete data permanently
3. Never ignore a human override
4. Never claim more certainty than warranted
5. Never block human intervention

---

## 14. Implementation Timeline

| Step | Estimate |
| :--- | :--- |
| Schema update | 10 minutes |
| 6 MCP tools | 1-2 days |
| Tests | 1 day |
| Documentation | 1 day |
| **Total** | **4-5 days** |

---

## 15. The Ultimate Test

> "I said what I wanted. It happened. I trust it."

When Nucleus works perfectly, you don't notice it exists.
Intent flows into reality. Silence.

---

*Specification complete. 14 thinking passes. Ready for implementation.*
