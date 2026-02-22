# Governance Policies: The Nucleus Security Model

**Version:** 1.0.0  
**Status:** CANONICAL  
**Category:** Agent Control Plane / Security

---

## Executive Summary

Nucleus implements three governance policies that distinguish it from raw MCP server connections. These policies form the **Governance Moat**—the security layer that makes the MCP ecosystem trustworthy for autonomous agents.

---

## Policy 1: Default-Deny

### Principle
> All tools start with **zero** network and filesystem access. Trust is explicitly granted, never assumed.

### Implementation

```
┌─────────────────────────────────────────────────────┐
│                    NUCLEUS HOST                      │
│  ┌─────────────────────────────────────────────┐    │
│  │           PERMISSION BOUNDARY               │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │    │
│  │  │ Tool A  │  │ Tool B  │  │ Tool C  │     │    │
│  │  │ ❌ Net  │  │ ❌ Net  │  │ ❌ Net  │     │    │
│  │  │ ❌ FS   │  │ ❌ FS   │  │ ❌ FS   │     │    │
│  │  └─────────┘  └─────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  User grants explicit permission:                    │
│  > "Allow Tool A to read ~/.config/api_keys.json"   │
│                                                      │
│  ┌─────────┐                                        │
│  │ Tool A  │ ✅ FS (scoped to ~/.config/)          │
│  │ ❌ Net  │                                        │
│  └─────────┘                                        │
└─────────────────────────────────────────────────────┘
```

### Contrast with Raw MCP

| Aspect | Raw MCP Server | Nucleus (Default-Deny) |
|--------|----------------|------------------------|
| Network access | Always on | Explicitly granted |
| Filesystem access | Always on | Scoped & approved |
| API token exposure | In prompts | Host-isolated |
| Approval workflow | None | Human-in-the-loop |

---

## Policy 2: Isolation Boundaries

### Principle
> Tools cannot see each other or the full chat history. Nucleus mediates all context exchange.

### Implementation

```
┌─────────────────────────────────────────────────────┐
│                   NUCLEUS HOST                       │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Tool A    │  │   Tool B    │  │   Tool C    │ │
│  │             │  │             │  │             │ │
│  │ View: Own   │  │ View: Own   │  │ View: Own   │ │
│  │ context     │  │ context     │  │ context     │ │
│  │ only        │  │ only        │  │ only        │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │        │
│         └────────────────┼────────────────┘        │
│                          │                         │
│                   ┌──────▼──────┐                  │
│                   │   NUCLEUS   │                  │
│                   │   MEDIATOR  │                  │
│                   │             │                  │
│                   │ Full View:  │                  │
│                   │ All context │                  │
│                   │ All history │                  │
│                   └─────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### What Tools CANNOT See
- Other tools' inputs/outputs
- Full chat history
- User's API tokens
- System prompt content
- Other tools' error logs

### What Tools CAN See
- Their own input parameters
- Nucleus-injected context (Engrams)
- Their own execution history (if opted in)

---

## Policy 3: Immutable Audit

### Principle
> Every decision is SHA-256 hashed and logged locally. The audit trail proves who did what, when, and why.

### Implementation

```
┌─────────────────────────────────────────────────────┐
│                  INTERACTION LOG                     │
│            .brain/ledger/interaction_log.jsonl       │
│                                                      │
│  {"timestamp": "2026-01-26T11:30:00Z",              │
│   "emitter": "brain_add_task",                       │
│   "type": "task_created",                            │
│   "hash": "a1b2c3d4e5f6...",                        │
│   "alg": "sha256"}                                   │
│                                                      │
│  {"timestamp": "2026-01-26T11:31:00Z",              │
│   "emitter": "brain_claim_task",                     │
│   "type": "task_claimed",                            │
│   "hash": "f6e5d4c3b2a1...",                        │
│   "alg": "sha256"}                                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Audit Properties

| Property | Description |
|----------|-------------|
| **Immutable** | Append-only ledger, no deletions |
| **Cryptographic** | SHA-256 hash of each interaction |
| **Local** | Stored in `.brain/`, never transmitted |
| **Verifiable** | Any entry can be independently verified |
| **Queryable** | `brain_audit_log()` MCP tool for retrieval |

### Verification Flow

```python
# Verify any interaction hash
import hashlib
import json

entry = {"type": "task_created", "emitter": "brain_add_task", "data": {...}}
payload = json.dumps(entry, sort_keys=True)
expected_hash = hashlib.sha256(payload.encode()).hexdigest()

# Compare with logged hash
assert stored_hash == expected_hash
```

---

## The Governance Moat

These three policies combine to create a **Governance Moat**—a security layer that:

1. **Prevents unauthorized access** (Default-Deny)
2. **Limits blast radius** (Isolation Boundaries)
3. **Enables accountability** (Immutable Audit)

### Why This Matters for Autonomous Agents

| Without Governance | With Governance |
|-------------------|-----------------|
| Agent can read any file | Agent requests permission first |
| Tool failure cascades | Failures are isolated |
| "Who deleted that file?" | Audit trail shows exactly who/when |
| Trust is assumed | Trust is earned and verified |

---

## MCP Tools for Governance

| Tool | Purpose |
|------|---------|
| `brain_audit_log(limit)` | View recent interaction hashes |
| `brain_check_protocol(agent_id)` | Verify agent compliance with MoU |
| `brain_health()` | System health including security status |

---

## Configuration

### Environment Variables

```bash
# Enable V9 Security features (interaction logging)
export NUCLEUS_V9_SECURITY=true

# Set brain path (where audit logs are stored)
export NUCLEAR_BRAIN_PATH=/path/to/.brain
```

### Audit Log Location

```
.brain/
├── ledger/
│   ├── events.jsonl          # Decision events
│   ├── interaction_log.jsonl # Cryptographic audit trail
│   └── tasks.json            # Task state
```

---

## Related Documents

- [RECURSIVE_AGGREGATOR.md](./architecture/RECURSIVE_AGGREGATOR.md) - Technical architecture
- [CONTROL_PLANE_POSITIONING.md](./v10_strategy/CONTROL_PLANE_POSITIONING.md) - Market positioning
- [ENGRAM_SPECIFICATION.md](./ENGRAM_SPECIFICATION.md) - Memory model (coming soon)

---

*Part of the Nucleus Sovereign OS (N-SOS) documentation.*  
*Generated: January 26, 2026*
