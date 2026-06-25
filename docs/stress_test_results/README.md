# Nucleus Tool Facade Stress Test Results

**Test date:** 2026-06-25
**Total tests:** 1,526 (218 actions × 7 angles)
**Zero crashes. Zero unhandled failures.**

## How to read this

### Start here
- **`stress_test_full_report_20260625.md`** — the master report. Contains every action, every angle, every result preview. 14,559 lines. If you only read one file, read this.

### Per-module breakdowns
If you only care about one module, read its individual file:

| Module | File | Actions | What it covers |
|--------|------|---------|----------------|
| engrams | `module_engrams.md` | 39 | Memory, health, DSoR, morning brief, heartbeat, tiers |
| sync | `module_sync.md` | 67 | Marketplace, relay, pair-fire, channels, federation proxy |
| sessions | `module_sessions.md` | 28 | Session management, context switch, depth stack |
| governance | `module_governance.md` | 21 | Sovereign mode, compliance, curl, file ops, KYC |
| tasks | `module_tasks.md` | 17 | Task CRUD, commitments, PR watch, weekly challenge |
| features | `module_features.md` | 16 | MCP marketplace, tool mounting, proofs, thanos snap |
| orchestration | `module_orchestration.md` | 13 | Commitments, loops, patterns, satellite |
| federation | `module_federation.md` | 8 | Peer routing, federation sync, join/leave |
| relay | `module_relay.md` | 4 | Inbox, post, ack, status |
| audit_log_tool | `module_audit_log_tool.md` | 4 | Audit query, log event, verify |
| cost_router | `module_cost_router.md` | 1 | Cost routing |

### The 7 test angles

| # | Angle | What it tests | Pass | Handled | Crash |
|---|-------|---------------|------|---------|-------|
| 1 | `happy` | Valid params — the normal call an LLM would make | 43 (20%) | 175 | 0 |
| 2 | `missing_params` | No params provided — tests required-param validation | 59 (27%) | 159 | 0 |
| 3 | `wrong_types` | Wrong param types (int where str expected, etc.) | 1 (0%) | 217 | 0 |
| 4 | `empty_params` | Empty params dict — tests default handling | 59 (27%) | 159 | 0 |
| 5 | `unknown_action` | Action name that doesn't exist — tests typo handling | 0 (0%) | 218 | 0 |
| 6 | `fire_without_thinking` | Empty action + empty params — zero-config call | 0 (0%) | 218 | 0 |
| 7 | `cross_agent_compat` | Static analysis for Claude/Cursor/Windsurf compat | 92 (42%) | 0 | 0 |

### Status meanings

| Status | Emoji | Meaning |
|--------|-------|---------|
| `pass` | ✅ | Tool returned a successful response |
| `handled` | ⚠️ | Tool returned a graceful error (no crash) |
| `warn` | 🔶 | Cross-agent compat warning (static analysis) |
| `fail` | ❌ | Tool failed without structured response |
| `crash` | 💥 | Unhandled exception (KeyError, AttributeError, etc.) |

## Key findings

### The good
- **Zero crashes across 1,526 tests.** Bad params, wrong types, empty calls, unknown actions — nothing crashes.
- **Fire-without-thinking: 218/218.** Every action returns a structured response when called with empty action + empty params. An LLM can fire blindly and never crash the tool.
- **Unknown actions: 218/218 handled.** Every tool gracefully rejects typos in the action name.

### The issues
- **Cross-agent compat: 126/218 warnings.** Two root causes:
  1. **126 actions use sync dispatch** — `audit_log_tool`, `governance`, `orchestration`, `relay`, and `sync` modules use `make_response_dispatch` (sync) instead of `async_dispatch`. The tool functions are async, but inner handlers are sync. Strict MCP clients may have issues.
  2. **67 actions reference "claude" in logic** — All `sync` module actions reference "claude" in their source code, meaning the sync module has client-specific assumptions, not fully agent-agnostic.

## How to reproduce

```bash
# Run the stress test
python3 scripts/stress_test_tools.py

# Generate this documentation
python3 scripts/generate_stress_test_docs.py
```

The harness uses a MockMCP object that captures all tool registrations without starting a real MCP server. Each tool function is called directly with test params. Results are classified as pass/handled/warn/fail/crash.

## Limitations

1. **Happy path params are generic.** Some actions need specific brain state (e.g., a real engram ID) to succeed. The test uses generic params, so `handled` may mean "correctly rejected because the ID doesn't exist" rather than "broken."
2. **Cross-agent compat is static analysis.** The harness checks function signatures, docstrings, and source code — it does not actually test against Claude, Cursor, or Windsurf MCP clients.
3. **No real MCP server.** The MockMCP captures registrations but doesn't test the full MCP protocol (JSON-RPC, schema generation, transport).
