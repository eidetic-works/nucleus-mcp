# Deterministic Fix Plan — Nucleus Tool Facade Stress Test

> **STATUS: ALL ISSUES RESOLVED (2026-06-25).** All 126 sync-dispatch actions converted to `async_dispatch`. All "claude" references removed from sync module logic. Harness ROUTER extraction fixed (AST-based, multi-router per module). Sessions + orchestration modules now register correctly. Re-run: 266 actions × 7 angles = 1,862 tests, 0 crashes, 0 fails, 0 warns. This document is retained as a historical record of the fix plan.

**Source:** `mcp-server-nucleus/docs/stress_test_results/stress_test_full_report_20260625.md`
**Date:** 2026-06-25
**Scope:** 218 actions × 7 angles = 1,526 tests (original run; re-run = 266 actions × 7 = 1,862 tests)

## Triage Summary

After reading all 14,559 lines and cross-referencing with source code, the 1,526 test results break down into **4 categories**:

| Category | Count | Real bugs? | Action |
|----------|-------|-----------|--------|
| Sync dispatch (not async) | 126 actions | Yes — cross-agent compat | **Fix: convert to async_dispatch** |
| "claude" references | 67 actions | No — false positive (comments/docstrings only) | **Fix: harness regex, not source** |
| Harness ROUTER extraction bugs | ~3 actions | No — harness regex picks up string literals in lambdas | **Fix: harness regex** |
| "Handled" on happy path | 175 actions | No — generic test params don't match real brain state | **No fix needed** |

**Real bugs to fix: 126 actions using sync dispatch.**

## Root Cause Analysis

### Issue 1: Sync dispatch (126 actions)

**What:** 6 modules use `dispatch()` (sync) instead of `async_dispatch()` (async):
- `audit_log_tool` (4 actions) — uses `make_response_dispatch()`
- `governance` (21 actions) — uses `dispatch()`
- `orchestration` (13 actions) — uses `dispatch()`
- `relay` (4 actions) — uses `dispatch()`
- `sessions` (28 actions) — uses `dispatch()`
- `sync` (67 actions) — uses `dispatch()`
- `tasks` (17 actions) — uses `dispatch()`

**Why it matters:** The MCP protocol expects async tool functions. The outer tool function is `async def`, but it calls the sync `dispatch()` which calls sync handlers. This works today because FastMCP awaits the outer function, but:
1. Strict MCP clients may timeout on long-running sync handlers
2. Async handlers can't be added to these modules without breaking the dispatch
3. Event loop blocking — sync handlers block the event loop

**The fix:** Convert each module from `dispatch()` to `async_dispatch()`. This requires:
- Changing the dispatch call from `dispatch(...)` to `await async_dispatch(...)`
- Making each handler `async def` (or wrapping sync handlers)

### Issue 2: "claude" references (67 actions) — FALSE POSITIVE

**What:** The harness flags any source file containing "claude" in non-comment lines.

**Reality:** All 67 "claude" references in `sync.py` are in:
- Docstrings (describing Claude Code as one of the MCP clients)
- Comments (explaining cross-agent behavior)
- String literals (inbox names like `claude_code_main`)

**Fix:** Improve the harness to skip comments, docstrings, and known inbox names. No source code changes needed.

### Issue 3: Harness ROUTER extraction bugs (~3 actions)

**What:** The regex `['\"]([^'\"]+)['\"]\s*:` picks up string literals inside lambda bodies as action keys.

**Examples:**
- `governance.GET` — picked up from `method="GET"` in a lambda
- `sync.*` — picked up from a wildcard pattern
- `sync./api/health` — picked up from a URL string

**Fix:** Improve the regex to only match top-level dict keys, not string literals inside values. No source code changes needed.

### Issue 4: "Handled" on happy path (175 actions) — NOT A BUG

**What:** 175/218 actions return `handled` (graceful error) on the happy path.

**Reality:** The harness uses generic params (e.g., `{'id': 'test'}`) that don't match real brain state. The tools correctly reject these because:
- The engram ID `'test'` doesn't exist in the brain
- The query `'test'` returns no results
- Required params like `key` and `value` aren't in the generic dict

**Fix:** None needed. This is correct behavior — the tools are validating input properly.

---

## Deterministic Fix Plan

### Phase 1: Convert sync dispatch to async (126 actions, 7 modules)

**Approach:** For each module, change `dispatch()` to `async_dispatch()` and make handlers async.

**Key insight:** The `async_dispatch()` function already exists in `_dispatch.py` and handles both sync and async handlers — it awaits coroutines if the handler returns one, otherwise treats the result as sync. So we only need to:

1. Change the dispatch call from `dispatch(...)` to `await async_dispatch(...)`
2. The handlers themselves can stay sync — `async_dispatch` handles both

**Per-module changes:**

#### 1.1 `audit_log_tool.py` (4 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/audit_log_tool.py`
- **Change:** Replace `make_response_dispatch(...)` with `await async_dispatch(...)`
- **Lines:** ~179
- **Risk:** Low — `async_dispatch` has the same error handling

#### 1.2 `governance.py` (21 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/governance.py`
- **Change:** Replace `dispatch(action, params, ROUTER, "nucleus_governance")` with `await async_dispatch(action, params, ROUTER, "nucleus_governance")`
- **Lines:** ~356
- **Risk:** Low

#### 1.3 `orchestration.py` (13 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/orchestration.py`
- **Change:** Replace 4 `dispatch(...)` calls with `await async_dispatch(...)`
- **Lines:** ~384, ~508, ~643, ~851
- **Risk:** Low

#### 1.4 `relay.py` (4 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/relay.py`
- **Change:** Replace `dispatch(action, params, ROUTER, "nucleus_relay")` with `await async_dispatch(...)`
- **Lines:** ~224
- **Risk:** Low

#### 1.5 `sessions.py` (28 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/sessions.py`
- **Change:** Replace `dispatch(action, params, ROUTER, "nucleus_sessions")` with `await async_dispatch(...)`
- **Lines:** ~177
- **Risk:** Low

#### 1.6 `sync.py` (67 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/sync.py`
- **Change:** Replace `dispatch(action, params, ROUTER, "nucleus_sync")` with `await async_dispatch(...)`
- **Lines:** ~392
- **Risk:** Low

#### 1.7 `tasks.py` (17 actions)
- **File:** `mcp-server-nucleus/src/mcp_server_nucleus/tools/tasks.py`
- **Change:** Replace `dispatch(action, params, ROUTER, "nucleus_tasks")` with `await async_dispatch(...)`
- **Lines:** ~105
- **Risk:** Low

### Phase 2: Fix harness false positives (no source changes)

#### 2.1 Fix ROUTER extraction regex
- **File:** `scripts/stress_test_tools.py`
- **Change:** Only match top-level dict keys, not string literals inside lambda values
- **Approach:** Parse the ROUTER dict with `ast.literal_eval` instead of regex

#### 2.2 Fix "claude" reference detection
- **File:** `scripts/stress_test_tools.py`
- **Change:** Skip comments, docstrings, and known inbox names (`claude_code_main`, `claude_code_peer`)
- **Approach:** Strip comments and docstrings before searching for "claude"

### Phase 3: Re-run stress test and verify

1. Run `python3 scripts/stress_test_tools.py`
2. Run `python3 scripts/generate_stress_test_docs.py`
3. Verify: 0 crashes, 0 fails, 0 cross-agent compat warnings
4. Commit updated reports

---

## Execution Order

| Step | What | Files | Est. changes | Risk |
|------|------|-------|-------------|------|
| 1 | Convert `audit_log_tool` to async | 1 file, ~5 lines | Low |
| 2 | Convert `governance` to async | 1 file, ~3 lines | Low |
| 3 | Convert `orchestration` to async | 1 file, ~8 lines | Low |
| 4 | Convert `relay` to async | 1 file, ~3 lines | Low |
| 5 | Convert `sessions` to async | 1 file, ~3 lines | Low |
| 6 | Convert `sync` to async | 1 file, ~3 lines | Low |
| 7 | Convert `tasks` to async | 1 file, ~3 lines | Low |
| 8 | Fix harness ROUTER extraction | 1 file, ~20 lines | Low |
| 9 | Fix harness "claude" detection | 1 file, ~10 lines | Low |
| 10 | Re-run stress test | — | — |
| 11 | Regenerate docs | — | — |
| 12 | Commit | — | — |

**Total source changes:** ~28 lines across 7 tool files
**Total harness changes:** ~30 lines in 1 file
**Expected result:** 0 crashes, 0 fails, 0 cross-agent compat warnings
