# Engram v1 Specification

> **Version:** 1.0  
> **Status:** Draft  
> **Last Updated:** 2026-05-05  
> **Related:** Relay Ops (relay_ops.py), MCP Server (tools/engrams.py)

---

## 1. What an engram is

An engram is a key/value memory unit that stores contextual information across AI sessions. It is the primitive building block of Nucleus's decision log system.

### Core attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `key` | string | Unique identifier for the engram |
| `value` | string | The stored information (markdown, plain text, or structured data) |
| `context` | enum | Categorizes the engram's semantic domain |
| `intensity` | integer (1-10) | Indicates importance/weight for compounding operations |
| `created_at` | ISO8601 | Timestamp of engram creation |
| `session_id` | string | Origin session for audit trail |
| `provider` | string (optional) | AI provider that created the engram (audit-only) |

### Context enum

The `context` field MUST be one of these values:

- **`Feature`** — Product feature implementations, flags, capabilities
- **`Architecture`** — System design decisions, patterns, structural choices
- **`Brand`** — Positioning, messaging, public-facing decisions
- **`Strategy`** — Strategic bets, market positioning, go/no-go calls
- **`Decision`** — Operational decisions, gate approvals, commit messages

### Lifecycle

Engrams follow a three-stage lifecycle:

1. **Write** — Created via `nucleus_engrams.write_engram()` or relay convergence
2. **Query** — Retrieved via `nucleus_engrams.query_engrams()` with semantic search
3. **Compound** — Intensified or merged via weekly consolidation or fusion reactor

### Intensity semantics

| Range | Meaning | Typical Use |
|-------|--------|-------------|
| 1-3 | Low | Temporary notes, debug info, ephemeral context |
| 4-7 | Medium | Design decisions, feature flags, strategic bets |
| 8-10 | High | Architectural invariants, brand pillars, irreversible decisions |

---

## 2. Wire format (JSON schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Engram v1",
  "type": "object",
  "required": ["key", "value", "context", "intensity", "created_at", "session_id"],
  "properties": {
    "key": {
      "type": "string",
      "pattern": "^[a-z0-9_\\-]{1,100}$",
      "description": "Unique identifier, lowercase alphanumeric with underscores/hyphens"
    },
    "value": {
      "type": "string",
      "maxLength": 10000,
      "description": "The stored information (markdown, plain text, or structured data)"
    },
    "context": {
      "type": "string",
      "enum": ["Feature", "Architecture", "Brand", "Strategy", "Decision"],
      "description": "Semantic domain categorization"
    },
    "intensity": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "description": "Importance weight for compounding operations"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO8601 timestamp of creation"
    },
    "session_id": {
      "type": "string",
      "pattern": "^[a-z0-9_\\-]{1,50}$",
      "description": "Origin session identifier for audit trail"
    },
    "provider": {
      "type": "string",
      "pattern": "^[a-z0-9_\\-]{1,50}$",
      "description": "AI provider that created the engram (audit-only, never used for routing)"
    }
  },
  "additionalProperties": false
}
```

### Example engram

```json
{
  "key": "relay_context_convergence_signal",
  "value": "relay_listen returns is_convergence: true when context.convergence is set. This triggers automatic Decision-context engram write.",
  "context": "Feature",
  "intensity": 7,
  "created_at": "2026-05-04T18:00:00Z",
  "session_id": "worker_a",
  "provider": "claude"
}
```

---

## 3. Relay integration

The relay system integrates with engrams via the `context` field in relay messages.

### relay_listen context mapping

The `relay_listen` function in `relay_ops.py` returns a `context` field (line 2076) that maps directly to engram context:

```python
# relay_ops.py line 2076
"context": data.get("context", {})
```

When a relay message contains `context: {"phase": "2", "plan": "wedge_dot_brain"}`, this context is available in the relay summary. However, this is **not** automatically written as an engram. Automatic engram writes occur only on convergence signals.

### is_convergence triggering Decision engrams

The `is_convergence` flag (relay_ops.py line 2077) triggers automatic Decision-context engram writes:

```python
# relay_ops.py line 2077
"is_convergence": bool(data.get("context", {}).get("convergence"))
```

When a relay message contains `context: {"convergence": true}`, the agent workflow writes a Decision-context engram:

```json
{
  "key": "plan_convergence_wedge_dot_brain_2026_05_05",
  "value": "Tandem relay workflow update complete: relay_ops.py context/is_convergence fields added, agent.md and principal.md workflows updated with ack/verification/deviation/context-based convergence",
  "context": "Decision",
  "intensity": 8,
  "created_at": "2026-05-05T00:55:12Z",
  "session_id": "worker_a"
}
```

### Mapping rules

| Relay context field | Engram context | Trigger condition |
|---------------------|----------------|-------------------|
| `context.convergence === true` | `Decision` | Automatic write on convergence signal |
| `context.phase`, `context.plan`, etc. | No automatic mapping | Manual write only |
| Relay body content | Any context | Manual write via `nucleus_engrams.write_engram` |

---

## 4. Query contract

The `/brain query` endpoint provides semantic search over engrams.

### Request

```bash
nucleus_engrams query_engrams
  query: "why did we add is_convergence flag"
  context: "Feature"  # optional filter
  min_intensity: 5    # optional filter
```

### Response format

```json
{
  "answer": "The is_convergence flag was added to relay_ops.py to enable context-based convergence signaling instead of brittle subject parsing.",
  "source": "relay_context_convergence_signal",
  "confidence": 0.92,
  "engram_key": "relay_context_convergence_signal",
  "context": "Feature",
  "intensity": 7
}
```

### Fallback response

When no engram matches the query:

```json
{
  "answer": null,
  "source": "no_match",
  "confidence": 0,
  "engram_key": null
}
```

### Performance targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| p50 latency | <200ms | 50th percentile query time |
| p95 latency | <500ms | 95th percentile query time |
| p99 latency | <1s | 99th percentile query time |
| Throughput | >100 QPS | Queries per second on 1000 engrams |

### Query algorithm (v1)

Engram v1 uses simple keyword matching with context filtering:

1. Tokenize query into keywords
2. Filter engrams by `context` if specified
3. Filter engrams by `intensity >= min_intensity` if specified
4. Score engrams by keyword overlap (Jaccard similarity)
5. Return highest-scoring engram if score > threshold (0.3)
6. Return fallback if no engram exceeds threshold

**Note:** v2 will upgrade to vector similarity search (embeddings) for semantic understanding.

---

## 5. Cross-vendor neutrality clause

The engram wire format is designed to be vendor-neutral. Any MCP-compliant client should be able to read and write engrams without provider-specific logic.

### Provider field is audit-only

The `provider` field exists solely for audit trails. It MUST NOT be used for:

- Routing decisions
- Query filtering
- Priority ranking
- Feature gating

Example: A Claude Code session writes `provider: "claude"`, a Cursor session writes `provider: "cursor"`. Both should be able to query the same engrams and receive identical results.

### No provider-specific fields

The wire format does NOT include provider-specific fields such as:

- `claude_version` or `cursor_version`
- `model_name` or `model_id`
- `temperature` or other inference parameters
- Provider-specific metadata

If provider-specific information is needed, it MUST be encoded in the `value` field as structured data, not as top-level fields.

### MCP compliance

The engram schema is compatible with the MCP standard:

- JSON schema validation
- UTF-8 encoding
- ISO8601 timestamps
- No binary data
- No vendor-specific types

Any MCP client (Claude Code, Cursor, Windsurf, Codex) can:

1. Read engrams via `nucleus_engrams.query_engrams()`
2. Write engrams via `nucleus_engrams.write_engram()`
3. Parse the JSON schema
4. Validate against the schema

---

## 6. Versioning

### v0 — Ad-hoc (pre-specification)

- No schema enforcement
- Direct calls to `nucleus_engrams.write_engram()`
- Inconsistent field naming across sessions
- No relay integration
- No convergence signaling

**Status:** Deprecated. Migration path: v0 engrams are readable but new writes must conform to v1 schema.

### v1 — Schema-enforced (this specification)

- JSON schema validation on all writes
- Relay integration via `context` field
- Automatic Decision engram writes on convergence
- Cross-vendor neutrality enforced
- Query contract with performance targets
- Context enum with 5 values

**Status:** Current. All new engrams must conform to this spec.

### v2 — Vector similarity (future)

- Embeddings for semantic search
- Cross-session compounding via fusion reactor
- Automatic engram clustering
- Similarity-based query ranking
- Time-decay for low-intensity engrams

**Migration path:** v1 engrams will be automatically re-indexed with embeddings during v2 rollout. No manual migration required.

### Version detection

Engrams include a `version` field in the ledger file (not in the wire format):

```json
{
  "version": "1.0",
  "engrams": [
    { /* engram v1 wire format */ }
  ]
}
```

The MCP server reads the ledger version and applies appropriate validation logic.

---

## Appendix A: Error codes

| Code | Message | Cause |
|------|---------|-------|
| `E001` | Invalid context enum | `context` not in [Feature, Architecture, Brand, Strategy, Decision] |
| `E002` | Intensity out of range | `intensity` not in [1, 10] |
| `E003` | Key already exists | Engram with same `key` already exists in ledger |
| `E004` | Schema validation failed | JSON schema validation error (see details) |
| `E005` | Missing required field | One of the required fields is missing |

---

## Appendix B: Migration from v0 to v1

### Automated migration script

```bash
nucleus migrate-engrams --from v0 --to v1
```

The migration script:

1. Reads all v0 engrams from the ledger
2. Validates against v1 schema
3. Adds missing fields with defaults:
   - `provider`: `"unknown"` if missing
   - `context`: `"Feature"` if missing (default)
   - `intensity`: `5` if missing (default)
4. Writes v1 ledger
5. Archives v0 ledger to `.brain/ledger/engrams_v0_backup.json`

### Manual migration

If automated migration fails:

1. Export v0 engrams to JSON
2. Manually fix schema violations
3. Import via `nucleus_engrams.write_engram()` with v1 schema validation

---

## Appendix C: Implementation checklist

For MCP server implementation:

- [ ] JSON schema validation on `write_engram()`
- [ ] Context enum enforcement
- [ ] Intensity range validation (1-10)
- [ ] Key uniqueness check
- [ ] Relay context field exposure (relay_ops.py:2076)
- [ ] is_convergence flag (relay_ops.py:2077)
- [ ] Automatic Decision engram write on convergence
- [ ] Query contract implementation
- [ ] Fallback response on no match
- [ ] Performance monitoring (latency metrics)
- [ ] v0 → v1 migration script
- [ ] Schema documentation in MCP tool description

For client implementation:

- [ ] JSON schema validation on writes
- [ ] Context enum selection UI
- [ ] Intensity slider (1-10)
- [ ] Query interface with context/intensity filters
- [ ] Error handling for E001-E005
- [ ] Fallback UI for `answer: null`
