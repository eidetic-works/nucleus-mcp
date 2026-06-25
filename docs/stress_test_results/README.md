# Nucleus Tool Facade Stress Test Results

**Test date:** 2026-06-25
**Total tests:** 1,862 (266 actions × 7 angles)
**Zero crashes. Zero unhandled failures. Zero cross-agent compat warnings.**

## How to read this

### Start here
- **`stress_test_full_report_20260625.md`** — the master report. Contains every action, every angle, every result preview. 17,168 lines. If you only read one file, read this.

### Per-module breakdowns
If you only care about one module, read its individual file:

| Module | File | Actions | What it covers |
|--------|------|---------|----------------|
| engrams | `module_engrams.md` | 38 | Memory, health, DSoR, morning brief, heartbeat, tiers |
| sync | `module_sync.md` | 63 | Marketplace, relay, pair-fire, channels, federation proxy |
| sessions | `module_sessions.md` | 26 | Session management, context switch, depth stack |
| orchestration.AGENTS_ROUTER | `module_orchestration_AGENTS_ROUTER.md` | 20 | Agent registry, identify, role management |
| orchestration.TELEM_ROUTER | `module_orchestration_TELEM_ROUTER.md` | 15 | Telemetry, metrics, dashboards |
| governance | `module_governance.md` | 19 | Sovereign mode, compliance, curl, file ops, KYC |
| tasks | `module_tasks.md` | 17 | Task CRUD, commitments, PR watch, weekly challenge |
| features | `module_features.md` | 16 | MCP marketplace, tool mounting, proofs, thanos snap |
| orchestration.ORCH_ROUTER | `module_orchestration_ORCH_ROUTER.md` | 13 | Commitments, loops, patterns, satellite |
| orchestration.INFRA_ROUTER | `module_orchestration_INFRA_ROUTER.md` | 12 | Infrastructure, deploys, health checks |
| orchestration.SLOTS_ROUTER | `module_orchestration_SLOTS_ROUTER.md` | 11 | Slot management, scheduling |
| federation | `module_federation.md` | 7 | Peer routing, federation sync, join/leave |
| relay | `module_relay.md` | 4 | Inbox, post, ack, status |
| audit_log_tool | `module_audit_log_tool.md` | 4 | Audit query, log event, verify |
| cost_router | `module_cost_router.md` | 1 | Cost routing |

### The 7 test angles

| # | Angle | What it tests | Pass | Handled | Crash |
|---|-------|---------------|------|---------|-------|
| 1 | `happy` | Valid params — the normal call an LLM would make | 95 (36%) | 171 | 0 |
| 2 | `missing_params` | No params provided — tests required-param validation | 122 (46%) | 144 | 0 |
| 3 | `wrong_types` | Wrong param types (int where str expected, etc.) | 2 (1%) | 264 | 0 |
| 4 | `empty_params` | Empty params dict — tests default handling | 122 (46%) | 144 | 0 |
| 5 | `unknown_action` | Action name that doesn't exist — tests typo handling | 0 (0%) | 266 | 0 |
| 6 | `fire_without_thinking` | Empty action + empty params — zero-config call | 0 (0%) | 266 | 0 |
| 7 | `cross_agent_compat` | Static analysis for Claude/Cursor/Windsurf compat | 266 (100%) | 0 | 0 |

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
- **Zero crashes across 1,862 tests.** Bad params, wrong types, empty calls, unknown actions — nothing crashes.
- **Fire-without-thinking: 266/266.** Every action returns a structured response when called with empty action + empty params. An LLM can fire blindly and never crash the tool.
- **Unknown actions: 266/266 handled.** Every tool gracefully rejects typos in the action name.
- **Cross-agent compat: 266/266 pass (100%).** All 11 tool facades are now fully async (using `async_dispatch`) with no client-specific references in their logic. Every tool is agent-agnostic — Claude, Cursor, Windsurf, or any MCP client can call them identically.

### Changes since last run
- **All 11 tool facades converted to async dispatch.** Previously 126 actions used sync `make_response_dispatch`; now all 266 actions use `async_dispatch`.
- **"claude" references removed from sync module logic.** Previously 67 actions in the `sync` module referenced "claude" in their source; now zero actions have client-specific assumptions.
- **Orchestration correctly decomposed into 5 separate ROUTERs.** The harness now correctly identifies that `orchestration` registers 5 separate tools (ORCH_ROUTER, TELEM_ROUTER, SLOTS_ROUTER, INFRA_ROUTER, AGENTS_ROUTER), each with its own action set.
- **Sessions module now registers.** Fixed missing mock helpers (`get_orch`, `read_events`, `get_state`, `update_state`) that prevented the sessions and orchestration modules from registering in the test harness.

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
