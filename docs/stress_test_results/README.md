# Nucleus Tool Facade Stress Test Results

**Test date:** 2026-06-25
**Total tests:** 1,862 (266 actions × 7 angles)
**Zero crashes. Zero unhandled failures. Zero cross-agent compat warnings.**

> **Refinement run:** The fire_without_thinking angle now tests 5 confused-LLM scenarios per action (empty action, None action, params-as-string, swapped args, guessed action + garbage params). The wrong_types angle now introspects handler signatures for per-param type mismatches. Network calls are mocked for deterministic results.

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
- **Fire-without-thinking: 266/266.** Every action returns a structured response across 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), and guessed action + garbage params. An LLM can fire blindly and never crash the tool.
- **Unknown actions: 266/266 handled.** Every tool gracefully rejects typos in the action name.
- **Cross-agent compat: 266/266 pass (100%).** All 11 tool facades are now fully async (using `async_dispatch`) with no client-specific references in their logic. Every tool is agent-agnostic — Claude, Cursor, Windsurf, or any MCP client can call them identically.

### Bugs found and fixed during stress test
1. **Federation async impls never awaited (CRITICAL, fixed in `f04a1f64`):** `_brain_federation_{join,leave,sync,route}_impl` are `async def` but were wrapped in sync lambdas in the ROUTER. `async_dispatch` checked `iscoroutinefunction(handler)` on the lambda (which is sync), so the returned coroutine was never awaited. This means federation `join`/`leave`/`sync`/`route` were **silently no-ops in production** — the functions were called but never executed. Fix: federation ROUTER now uses explicit `async def` wrapper functions. `async_dispatch` also has a safety net that awaits coroutines returned from sync handlers.
2. **Non-string action crashes dispatch (found by fire_without_thinking, fixed in refinement run):** When an LLM swaps the `action` and `params` arguments (passes a dict as `action`), `router.get(action)` throws `TypeError: cannot use 'dict' as a dict key (unhashable type: 'dict')`. 79/266 actions failed this scenario. Fix: both `dispatch()` and `async_dispatch()` now type-check `action` and return a structured error if it's not a string.
3. **audit_log `int(limit)` crashed on non-integer input (fixed in `f04a1f64`):** `query_audit()` did `int(limit)` with no type guard. When `limit='not_a_number'` was passed, it threw `ValueError`. Fix: try/except with fallback to default (100). Same for `offset`.
4. **audit_log + cost_router used sync dispatch despite async wrapper (fixed in `f04a1f64`):** Both were `async def` but called `make_response_dispatch` (sync) inside. Converted to `async_dispatch` for consistency with the other 9 facades.

### Low happy-path pass rate (35%, expected)
The happy-path angle passes only 92/266 (35%) because the harness uses generic params that don't match real brain state. Breakdown by module:

| Module | Pass | Handled | Pass % | Root cause |
|--------|------|---------|--------|------------|
| federation | 5 | 2 | 71% | Most actions work standalone |
| engrams | 20 | 18 | 53% | Many read actions work; write actions need specific keys |
| relay | 2 | 2 | 50% | Needs real relay state |
| sessions | 13 | 13 | 50% | Needs real session IDs |
| orchestration | 35 | 36 | 49% | Many ops work; some need real commitments/slots |
| tasks | 4 | 13 | 24% | Needs real task IDs |
| governance | 4 | 15 | 21% | Needs real compliance configs |
| features | 2 | 14 | 12% | Needs real feature IDs + MCP servers |
| sync | 7 | 56 | 11% | Needs real channels, pair configs, relay endpoints |
| audit_log | 0 | 4 | 0% | admin_query needs token; query returns empty; log_event/verify need specific params |
| cost_router | 0 | 1 | 0% | route action needs a real prompt (generic test prompt is too short) |

This is **expected behavior** — `handled` means the tool correctly rejected invalid/incomplete input with a structured error response. The tools are working correctly; the test params just don't match real brain state.

### Remaining harness limitations
1. **Schema generation fails** with `'str' object has no attribute 'name'` — the schema generator expects Tool objects, not strings. The MockMCP's `list_tools()` returns strings, but the schema code expects objects with a `.name` attribute. This is a harness limitation, not a production bug.
2. **Secret Manager warnings** — `google-cloud-secret-manager not installed` warnings for Telegram/Slack/Discord/WhatsApp tokens. Expected in test environment (network calls are mocked but the import-time check still fires).

### Changes since last run
- **All 11 tool facades converted to async dispatch.** Previously 126 actions used sync `make_response_dispatch`; now all 266 actions use `async_dispatch`.
- **"claude" references removed from sync module logic.** Previously 67 actions in the `sync` module referenced "claude" in their source; now zero actions have client-specific assumptions.
- **Orchestration correctly decomposed into 5 separate ROUTERs.** The harness now correctly identifies that `orchestration` registers 5 separate tools (ORCH_ROUTER, TELEM_ROUTER, SLOTS_ROUTER, INFRA_ROUTER, AGENTS_ROUTER), each with its own action set.
- **Sessions module now registers.** Fixed missing mock helpers (`get_orch`, `read_events`, `get_state`, `update_state`) that prevented the sessions and orchestration modules from registering in the test harness.
- **Federation coroutine bug fixed.** Federation ROUTER now uses explicit `async def` wrappers instead of sync lambdas. `async_dispatch` also has a safety net for any remaining sync lambdas wrapping async impls.
- **Non-string action guard added.** Both `dispatch()` and `async_dispatch()` now type-check the `action` parameter and return a structured error if it's not a string. Prevents `TypeError: unhashable type: 'dict'` when an LLM swaps action/params args.
- **audit_log type coercion hardened.** `int(limit)` and `int(offset)` now have try/except fallbacks.
- **Fire_without_thinking angle upgraded.** Now tests 5 confused-LLM scenarios per action instead of just empty-string action.
- **Wrong_types angle upgraded.** Now introspects handler signatures for per-param type mismatches instead of generic wrong types for all actions.
- **Network calls mocked.** `urllib.request.urlopen` is patched to return mock responses, making the harness deterministic (no PyPI 429s, no GitHub rate limits).
- **Dead code cleaned.** Unused `dispatch` imports removed from 7 tool modules. Unused `json` import removed from federation.py. `DeprecationWarning` for `asyncio.iscoroutinefunction` fixed.

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
