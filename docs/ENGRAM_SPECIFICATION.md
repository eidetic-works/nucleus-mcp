# Engram Specification: The Cognitive Memory Model

**Version:** 1.0.0  
**Status:** CANONICAL  
**Category:** Agent Control Plane / Memory

---

## Executive Summary

Engrams are the atomic units of contextual memory in Nucleus. Unlike generic "memory" systems, Engrams encode **strategic context** with intensity levels, zoom-based categorization, and optional cryptographic signatures for sovereignty.

---

## 1. Data Model

### Engram Schema

```python
class Engram:
    key: str           # Unique identifier (e.g., "auth_architecture")
    value: str         # The remembered content
    context: str       # Zoom level category (Feature, Architecture, Brand)
    intensity: int     # 1-10 priority scale (how much should the agent care?)
    timestamp: str     # ISO 8601 creation time
    signature: str     # Optional: Cryptographic signature for sovereignty
```

### JSON Representation

```json
{
  "key": "flask_session_decision",
  "value": "Using Flask-Session with Redis backend for stateless scaling",
  "context": "Architecture",
  "intensity": 8,
  "timestamp": "2026-01-26T10:30:00Z",
  "signature": null
}
```

---

## 2. Context Categories (Zoom Levels)

Engrams are organized by strategic "zoom level" to enable efficient retrieval:

| Context | Description | Example |
|---------|-------------|---------|
| **Feature** | Specific implementation details | "Mood tracker uses fl_chart for visualization" |
| **Architecture** | System design decisions | "Flask backend + Flutter frontend" |
| **Brand** | Marketing and positioning | "Category: Agent Control Plane" |
| **Strategy** | High-level business decisions | "Target universities before enterprise" |
| **Decision** | Recorded choices with reasoning | "Chose Redis over Memcached for persistence" |

---

## 3. Intensity Scale

The intensity level (1-10) indicates how much attention the agent should give to this Engram:

| Intensity | Meaning | Agent Behavior |
|-----------|---------|----------------|
| **10** | Critical | Always include in context |
| **8-9** | High | Include when relevant domain |
| **5-7** | Medium | Include if space permits |
| **3-4** | Low | Include only if specifically queried |
| **1-2** | Archive | Rarely surface, historical reference |

### Intensity Guidelines

```
10: "NEVER use OpenAI API - budget constraint"
 8: "All new features need unit tests"
 5: "Prefer Tailwind over raw CSS"
 3: "Old logo was blue, changed to purple in v2"
 1: "Considered MongoDB in 2024, rejected"
```

---

## 4. Storage Format

### Ledger Location

```
.brain/
├── engrams/
│   └── ledger.jsonl    # Append-only Engram storage
```

### JSONL Format

Each line is a complete Engram:

```jsonl
{"key": "api_auth", "value": "JWT tokens with 24h expiry", "context": "Architecture", "intensity": 7, "timestamp": "2026-01-20T08:00:00Z", "signature": null}
{"key": "color_scheme", "value": "Purple primary (#7C3AED)", "context": "Brand", "intensity": 5, "timestamp": "2026-01-21T14:30:00Z", "signature": null}
{"key": "no_openai", "value": "Do not use OpenAI - Gemini only", "context": "Decision", "intensity": 10, "timestamp": "2026-01-22T09:15:00Z", "signature": null}
```

---

## 5. Query Patterns

### Query by Context

```python
from memoir.engram import EngramLedger
from pathlib import Path

ledger = EngramLedger(Path(".brain"))

# Get all Architecture engrams
arch_engrams = ledger.query_context("Architecture")

# Sorted by intensity (highest first)
for e in arch_engrams:
    print(f"[{e.intensity}] {e.key}: {e.value}")
```

### Query All

```python
# Get complete memory
all_engrams = ledger.query_all()
print(f"Total engrams: {len(all_engrams)}")
```

### Keyword Search (via context matching)

```python
# Searches key, value, and context fields
results = ledger.query_context("JWT")
```

---

## 6. Write Patterns

### Creating an Engram

```python
from memoir.engram import Engram, EngramLedger
from pathlib import Path

ledger = EngramLedger(Path(".brain"))

# Create high-intensity architectural decision
engram = Engram(
    key="database_choice",
    value="PostgreSQL for production, SQLite for local dev",
    context="Architecture",
    intensity=8
)

ledger.write_engram(engram)
```

### Intensity Guidelines for Writing

| When to use... | Intensity |
|----------------|-----------|
| Breaking constraint (never do X) | 10 |
| Architectural decision | 7-9 |
| Implementation preference | 5-6 |
| Historical note | 2-4 |
| Trivial detail | 1 |

---

## 7. Cryptographic Sovereignty (Future)

### Planned Features (v0.6.0+)

1. **Signing**: Each Engram can be cryptographically signed by the owner
2. **Verification**: Agents can verify Engram authenticity before trusting
3. **Export**: Signed Engrams can be safely exported/shared

### Signature Schema (Planned)

```json
{
  "key": "critical_decision",
  "value": "...",
  "context": "Strategy",
  "intensity": 10,
  "timestamp": "2026-01-26T10:30:00Z",
  "signature": {
    "algorithm": "ed25519",
    "public_key": "...",
    "signature": "..."
  }
}
```

---

## 8. Integration with MCP Tools

### Related Tools

| Tool | Purpose |
|------|---------|
| `brain_save_session()` | Saves session context including Engrams |
| `brain_resume_session()` | Restores Engrams from saved session |
| `brain_search_memory()` | Searches across all memory sources |

### Future Tool (Planned)

```python
@mcp.tool()
def brain_write_engram(key: str, value: str, context: str, intensity: int = 5) -> str:
    """Write a new Engram to the cognitive memory ledger."""
    # Implementation
```

---

## 9. Best Practices

### DO

- ✅ Use high intensity (8-10) for constraints and critical decisions
- ✅ Use descriptive keys (e.g., "auth_jwt_expiry" not "auth1")
- ✅ Include reasoning in value (e.g., "X because Y")
- ✅ Use consistent context categories

### DON'T

- ❌ Store secrets or API keys in Engrams
- ❌ Use intensity 10 for everything (defeats the purpose)
- ❌ Create duplicate keys (update existing instead)
- ❌ Store large binary data

---

## 10. Comparison with Other Memory Systems

| Feature | CLAUDE.md | Engram Ledger |
|---------|-----------|---------------|
| **Structure** | Freeform text | Typed schema |
| **Queryable** | No (full read) | Yes (by context, key) |
| **Priority** | None | Intensity (1-10) |
| **Append-only** | Manual edit | Automatic ledger |
| **Verifiable** | No | Cryptographic (future) |

---

## Related Documents

- [GOVERNANCE_POLICIES.md](./GOVERNANCE_POLICIES.md) - Security model
- [RECURSIVE_AGGREGATOR.md](./architecture/RECURSIVE_AGGREGATOR.md) - Architecture
- [memoir/engram.py](../memoir/engram.py) - Implementation

---

*Part of the Nucleus Sovereign OS (N-SOS) documentation.*  
*Generated: January 26, 2026*
