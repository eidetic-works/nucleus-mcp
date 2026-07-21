# Stress Test Posture — How Bug E Was Found

**Date:** 2026-06-26
**Context:** Found 2 CRITICAL production bugs (Federation + audit_log) by reading 17K lines of stress test docs line-by-line, not by looking at summary numbers.

---

## The posture that works

### 1. Don't trust the summary — read the error messages

The stress test summary said "0 crashes, 0 fails, 616 pass, 1246 handled." That looked clean. But "handled" just means the tool returned a structured error — it doesn't tell you **why** the error occurred.

Bug E was hiding in the "handled" bucket. Every `audit_log.query` call returned:
```
"error": "Invalid params for action 'query': got an unexpected keyword argument 'team_id'"
```

That's not "correctly rejected because of missing brain state" — that's "the handler signature doesn't match the dispatch calling convention." But the summary just counted it as "handled" and moved on.

**Rule:** Read the actual error messages in the per-action result previews, not just the pass/handled/fail counts.

### 2. Trace error messages to handler signatures

When you see "got an unexpected keyword argument 'X'", the question is:
- Does the handler accept parameter 'X'?
- If not, why is dispatch passing it?

Bug E was found by asking: "Why does `audit_log.query` fail with 'unexpected keyword argument team_id'?" The answer: the handler was `def _h_query(params):` (takes a single dict) but `async_dispatch` calls `handler(**params)` (unpacks the dict as kwargs). So `_h_query(team_id='default')` fails because the handler doesn't have a `team_id` parameter.

**Rule:** When you see "unexpected keyword argument", check if the handler signature matches the dispatch calling convention.

### 3. Verify the harness is actually doing what it claims

The harness claimed to introspect handler signatures for happy-path params. But the introspection was capturing 0 handlers because of a Python import binding issue (`from ._dispatch import async_dispatch` binds the function directly, so patching the module doesn't affect it).

The harness was silently falling back to generic params for all 266 actions. The results looked reasonable (616 pass) but were less accurate than they could have been.

After fixing the harness, pass jumped from 616 to 883 — a 43% increase. The "reasonable" results were hiding 255 actions that should have passed but were getting wrong params.

**Rule:** Verify that harness features (introspection, mocking, etc.) are actually working. A silent fallback is worse than a loud failure.

### 4. "Handled" is not "correct" — it's "didn't crash"

The stress test classifies results as pass/handled/fail/crash. "Handled" means the tool returned a structured error response. But there are two very different reasons for "handled":

1. **Correct rejection:** The tool validated the input and rejected it for a good reason (e.g., "session ID not found"). This is expected behavior.
2. **Handler bug:** The handler threw an exception that dispatch caught and wrapped as an error (e.g., "unexpected keyword argument"). This is a production bug.

Both show up as "handled" in the summary. You can only tell them apart by reading the error message.

**Rule:** "Handled" is the bucket where bugs hide. Read every error message in the handled bucket.

### 5. The dispatch calling convention is a common bug source

The pattern that caused Bug E (and Bug A — federation) is the same: **handler calling convention mismatch**.

- `async_dispatch` calls `handler(**params)` — unpacks the dict as kwargs
- Some handlers expect `def handler(params):` — take a single dict
- Some handlers are sync lambdas wrapping async impls — coroutines never awaited
- Some handlers return non-JSON-serializable objects

All of these show up as "handled" in the stress test, not as crashes, because dispatch catches the exception and wraps it.

**Rule:** Check every handler against the dispatch calling convention:
1. Does it accept `**params` (kwargs)?
2. If async, is it registered as an `async def` (not a sync lambda)?
3. Does it return a JSON-serializable result?

### 6. Read the full report, not just the README

The README is a 2-minute summary. The full report is 17K lines. The README said "37% happy-path pass rate (expected)" and explained it as "generic params don't match real brain state." That explanation was partially wrong — some of the failures were because of wrong params (harness issue), not missing brain state (expected behavior).

After fixing the harness, the happy-path pass rate jumped to 74%. The README's explanation was masking a harness bug.

**Rule:** The README explains the numbers. The full report shows the evidence. When the explanation doesn't match the evidence, trust the evidence.

---

## How to apply this posture

1. **Run the stress test** — `python3 scripts/stress_test_tools.py`
2. **Read the full report** — not just the summary, the per-action result previews
3. **Look at every "handled" result** — read the error message
4. **Classify each "handled" as:**
   - **Correct rejection** — tool validated input and rejected for good reason (expected)
   - **Handler bug** — handler signature doesn't match dispatch convention (fix needed)
   - **Harness limitation** — test params don't match real brain state (expected)
   - **Test isolation issue** — handler has side effects during testing (mock needed)
5. **Verify harness features work** — check that introspection, mocking, etc. are actually functioning
6. **Fix handler bugs first** — these are production bugs
7. **Fix harness bugs second** — these make the tests less accurate
8. **Regenerate docs** — after any fix, re-run and regenerate

---

## Bugs found with this posture

| Bug | Severity | How found | Fix |
|-----|----------|-----------|-----|
| Federation coroutines never awaited | CRITICAL | fire_without_thinking angle | `ba11f1c8` — async wrappers |
| Non-string action crashes dispatch | HIGH | fire_without_thinking swapped-args | `ba11f1c8` — type-check action |
| audit_log int(limit) crash | MEDIUM | wrong_types angle | `f04a1f64` — try/except |
| audit_log + cost_router sync dispatch | MEDIUM | code review | `f04a1f64` — convert to async_dispatch |
| audit_log + cost_router handler signature | CRITICAL | reading full report error messages | `ddb7c861` — `def _h_x(params)` → `def _h_x(**params)` |
| extract_router_handlers capturing 0 | HARNESS | verifying introspection output | `368d24c1` — patch each module |
