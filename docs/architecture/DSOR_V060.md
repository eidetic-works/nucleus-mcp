# v0.6.0 DSoR: Decision System of Record

**Status:** IMPLEMENTED  
**Date:** January 30, 2026  
**Author:** Titan/Opus Handover Protocol

---

## Overview

DSoR (Decision System of Record) transforms Nucleus from "ad-hoc execution" to "decision provenance." Every agent action is now cryptographically anchored to a decision trail.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT EXECUTION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Agent   │───▶│ DecisionMade │───▶│  IPC Token   │          │
│  │  Intent  │    │    Event     │    │   Issued     │          │
│  └──────────┘    └──────────────┘    └──────────────┘          │
│                         │                    │                   │
│                         ▼                    ▼                   │
│               ┌──────────────┐    ┌──────────────┐              │
│               │   Decision   │    │    Token     │              │
│               │   Ledger     │    │  Validated   │              │
│               │  (JSONL)     │    │ & Consumed   │              │
│               └──────────────┘    └──────────────┘              │
│                                          │                       │
│                                          ▼                       │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Tool   │◀───│   Execute    │◀───│   Metering   │          │
│  │  Result  │    │     Tool     │    │    Entry     │          │
│  └──────────┘    └──────────────┘    └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. DecisionMade Events (`agent.py`)

Every tool execution is preceded by a `DecisionMade` event:

```python
decision = DecisionMade(
    decision_id="dec-abc123def456",
    reasoning="Tool: brain_add_task | LLM requested from turn 2",
    context_hash="14702942c34c69d6",  # SHA-256 of world-state
    confidence=0.9
)
```

**Fields:**
- `decision_id`: Unique identifier (uuid-based)
- `reasoning`: Why this decision was made
- `context_hash`: Hash of world-state at decision time
- `confidence`: 0.0-1.0 confidence score
- `timestamp`: ISO-8601 timestamp

### 2. Context Manager (`context_manager.py`)

Provides stateless hashing of world-state:

```python
from mcp_server_nucleus.runtime.context_manager import get_context_manager

cm = get_context_manager()
snapshot = cm.take_snapshot()
# snapshot.state_hash = "14702942c34c69d6"
# snapshot.component_hashes = {"ledger": "...", "slots": "...", "mounts": "..."}
```

**Capabilities:**
- `compute_world_state_hash()`: Hash current state
- `take_snapshot()`: Create immutable snapshot
- `verify_state_integrity()`: Compare before/after
- `persist_snapshot()`: Save for audit

### 3. IPC Auth (`ipc_auth.py`)

Per-request authentication tokens (remediates CVE-2026-001):

```python
from mcp_server_nucleus.runtime.ipc_auth import get_ipc_auth_manager

manager = get_ipc_auth_manager()
token = manager.issue_token(scope="tool_call", decision_id="dec-123")
# Token is single-use, 30-second TTL
```

**Security Properties:**
- Short-lived (30s TTL)
- Single-use (consumed on validation)
- Linked to decisions (audit trail)
- HMAC-signed (tamper-proof)

### 4. Token Metering

Every token consumption creates a metering entry:

```json
{
  "entry_id": "meter-abc123",
  "token_id": "ipc-def456",
  "decision_id": "dec-789xyz",
  "timestamp": "2026-01-30T08:00:00Z",
  "scope": "tool_call",
  "resource_type": "tool_call",
  "units_consumed": 1.0
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `brain_list_decisions` | List recent DecisionMade events |
| `brain_list_snapshots` | List context snapshots |
| `brain_metering_summary` | Get billing/audit summary |
| `brain_ipc_tokens` | List IPC tokens |
| `brain_dsor_status` | Comprehensive DSoR status |

## V9 Vulnerabilities Addressed

### CVE-2026-001: Sidecar Exploit

**Before:** IPC socket trusted any connection after initial auth.
**After:** Per-request tokens required. Single-use. 30s TTL.

### Pricing Rebellion

**Before:** Usage metering could be bypassed by forking CLI.
**After:** Token metering linked to DecisionMade events. No decision = no execution.

## File Locations

```
.brain/
├── ledger/
│   ├── decisions/
│   │   └── decisions.jsonl     # DecisionMade events
│   ├── snapshots/
│   │   └── snap-000001.json    # Context snapshots
│   ├── metering/
│   │   └── token_meter.jsonl   # Billing entries
│   └── auth/
│       └── ipc_tokens.jsonl    # Token lifecycle events
└── secrets/
    └── .ipc_secret             # HMAC key (chmod 600)
```

## Usage Example

```python
# Agent execution now automatically:
# 1. Takes "before" snapshot
# 2. Emits DecisionMade before each tool call
# 3. Issues IPC token linked to decision
# 4. Validates and consumes token
# 5. Records metering entry
# 6. Takes "after" snapshot
# 7. Verifies state integrity
```

## Testing

```bash
# Run DSoR-specific tests
PYTHONPATH=src python -m unittest tests.test_dsor_v060 -v

# Expected: 16/16 tests pass
```

## Migration Notes

- **Backward Compatible**: Existing agents work without changes
- **Opt-in Security**: IPC auth is non-blocking (graceful degradation)
- **No Schema Changes**: Uses append-only JSONL ledgers

---

*v0.6.0 DSoR: From ad-hoc execution to decision provenance.*
