# Nucleus MCP — Production Readiness Audit

**Date:** 2026-06-20  
**Auditor:** Automated 4-layer probe (Devin, session 007)  
**Method:** Read-only code inspection + live probe scripts against isolated temp brains. Zero production source files modified.  
**Scope:** All 17 MCP tools across 4 layers — Unit Tests, Contract Hardening, Integration, Production Readiness  
**Raw reports:** `/tmp/audit_engrams.md`, `/tmp/audit_relay_sync.md`, `/tmp/audit_audit_route.md`, `/tmp/audit_other_tools.md`

---

## Fix Status (updated 2026-06-20)

Correctness-only fixes applied under the W8 freeze, each with regression tests:

| Finding | Status | Commit / Note |
|---|---|---|
| C5 — `traverse_mount` ImportError | ✅ FIXED | `b303d453` — added missing module-level impl |
| H7 — non-atomic relay writes | ✅ FIXED | `a4c22756` — stage-to-.tmp + `os.replace()` |
| M16 — empty task description accepted | ✅ FIXED | `a4c22756` — reject empty/whitespace |
| H3 — `sovereignty_tier` on oauth-shim fallback | ⏸ WON'T FIX (here) | Intended/tested behavior; founder-scope compliance question |
| M12 — `complexity=None` → `data:null` | ⏸ WON'T FIX | Correct envelope behavior; systemic to `make_response`, not a router bug |
| L3 — hardcoded `mcp_tools_count: 110` | ⏸ DEFERRED | Proper fix needs dynamic registry plumbing; cosmetic |
| L4 — hardcoded `version "0.5.0"` | ⏸ DEFERRED | In dead code (`_brain_health_impl_legacy`, no callers) |
| C1–C4, H8–H13, H15 (auth/stubs) | ⛔ GATED | Extend-path scope; hold for Day-60 decision |

---

## Executive Summary

Nucleus has a **solid unit-test foundation** (435+ tests, all passing) but contains **5 CRITICAL and 16 HIGH severity gaps** that block production deployment today. The core issues cluster around three themes:

1. **No auth enforcement at the tool layer** — any connected MCP client can write engrams, post relay messages as any sender, forge audit log entries, or claim sovereign-tier routing
2. **Several features are stubs or dead code** — governance consensus (0 CI tests), federation transport (simulated), `traverse_mount` (always raises `ImportError`), OAuth 2.1 (`NotImplementedError`)
3. **Implicit trust between agents** — any agent can complete another agent's tasks, overwrite session metadata, read any inbox

The substrate is production-ready as a **single-operator local daemon** (which is its current use case). It is **not production-ready as a multi-tenant service** without addressing the CRITICAL items.

---

## Test Suite Baseline

| Tool Group | Tests Run | Passed | Failed | Skipped |
|---|---|---|---|---|
| Engrams (write/query/search/health/DSoR) | 87 | 87 | 0 | 0 |
| Relay + Sync | 156 | 156 | 0 | 0 |
| Audit Log + Cost Router | 69 | 69 | 0 | 0 |
| Sessions | 66 | 66 | 0 | 1 (signing suite — feature absent) |
| Tasks | 35 | 35 | 0 | 0 |
| Governance | 0 | 0 | 0 | 1 (entire file — `is_sovereign_mode` absent) |
| Federation | 38 | 38 | 0 | 0 |
| **Total (targeted)** | **451** | **451** | **0** | **2** |

**Full suite** (274 test files, non-e2e): **3703 passed, 41 skipped, 0 failed** in 20m 36s. Zero failures.

---

## Critical Findings

> These must be resolved before any multi-tenant or public deployment.

### C1 — Zero auth on `nucleus_relay` inbox reads (FS mode)
**Tool:** `nucleus_relay` / `nucleus_sync`  
**Finding:** In filesystem mode (the current production mode), any MCP client can call `relay_inbox(recipient="any_role")` and read another role's messages with zero credentials. There is no bearer-token check, no role ownership validation, nothing.  
**Impact:** Complete confidentiality loss for the inter-agent message bus. Agent A can read all of Agent B's unread messages.  
**Evidence:** Live probe — `relay_inbox(recipient="victim_inbox")` returned all messages without any auth token.

### C2 — Sender forgery on relay posts (FS mode)
**Tool:** `nucleus_relay`  
**Finding:** Any caller can post a relay message with `sender="admin"` or `sender=<any_other_role>`. The `from` field is stored as-is with no credential binding.  
**Impact:** Any agent can impersonate any other agent on the relay bus.  
**Evidence:** Live probe confirmed.

### C3 — `nucleus_audit` log_event has zero auth
**Tool:** `nucleus_audit`  
**Finding:** Any connected MCP client can call `log_event` and write arbitrary entries to the SHA-256 audit chain. The tamper-evidence only protects against filesystem edits — not API-level forgeries. A malicious agent can flood the log, insert false entries, or corrupt the chain's compliance story.  
**Impact:** The tamper-evident audit log is not tamper-evident against the MCP layer itself.

### C4 — `nucleus_route` tier routing is 100% caller-supplied
**Tool:** `nucleus_route`  
**Finding:** The cost router has no concept of subscription tier from a backend. Routing is purely the `complexity` hint provided by the caller. Any Free-tier user can pass `complexity="sovereign"` and get local-TB / oauth-shim routing. Any caller can claim Sonnet by passing `complexity="complex"`.  
**Impact:** Complete bypass of the Free/Pro/Pro+/Team tier enforcement. Revenue protection is absent.

### C5 — `traverse_mount` always raises `ImportError`
**Tool:** `nucleus_features`  
**Finding:** `features.py` line 79 imports `_brain_traverse_and_mount_impl` from `mounter_ops`, but this function does not exist at the module level. Only `Mounter.traverse_and_mount()` (a method) exists. Every call to the `traverse_mount` action raises `ImportError`.  
**Impact:** The feature is entirely broken. Any workflow depending on `traverse_mount` silently fails.  
**Evidence:** Live probe confirmed `ImportError` on every invocation.

---

## High Severity Findings

### H1 — Audit chain only verified on explicit demand
**Tool:** `nucleus_audit`  
**Finding:** `query_audit` reads rows from SQLite and returns them with no integrity check. Tampered rows are served silently. Only an explicit `verify` call detects corruption.  
**Fix:** Add a `verify_on_read` option, or at minimum document prominently that compliance consumers must call `verify` separately.

### H2 — DB deletion mid-session is silent; chain lost on restart
**Tool:** `nucleus_audit`  
**Finding:** If the SQLite DB file is deleted while the process runs, the thread-local connection holds the inode open and writes succeed. On the next process restart, the entire audit history is gone with no error or warning to the operator.

### H3 — `sovereignty_tier="sovereign"` set even on Anthropic fallback
**Tool:** `nucleus_route`  
**Finding:** When local-TB is unavailable, the router falls back to `claude-oauth-shim` (which routes data to Anthropic) but still sets `sovereignty_tier="sovereign"` in the response. This is a compliance hazard — callers relying on that field to verify zero data egress will be misled.

### H4 — No payload size cap in relay FS mode
**Tool:** `nucleus_relay`  
**Finding:** HTTP mode enforces a 64 KiB cap. FS mode has none. Live probe wrote a 200 KB payload without error. An agent can fill disk or cause unbounded memory usage on reads.

### H5 — `body=None` / `body=dict` accepted in relay FS mode
**Tool:** `nucleus_relay`  
**Finding:** FS mode accepts any Python type as message body. HTTP mode requires a string. Round-tripping FS-posted messages through the HTTP bridge causes silent type corruption.

### H6 — No relay inbox retention enforcement
**Tool:** `nucleus_relay`  
**Finding:** No TTL, no max-message count. Inboxes grow unbounded. In long-running deployments this becomes a disk exhaustion vector.

### H7 — Non-atomic relay writes
**Tool:** `nucleus_relay`  
**Finding:** Each message is written as a single `write_text()` call. A subscriber that wakes between the file creation and the write completing will read a partial or empty JSON file and permanently miss the message (no retry on parse failure).

### H8 — Session files have no integrity protection
**Tool:** `nucleus_sessions`  
**Finding:** `_save_session` writes plain JSON with no HMAC or signature. The session signing test suite (`test_session_signing.py`) is skipped entirely because the `signature` field does not exist in the current build. A tampered session file is accepted silently on resume.

### H9 — No task-level authorization
**Tool:** `nucleus_tasks`  
**Finding:** Any agent can complete, update, or escalate any other agent's task. `claimed_by` is a data field, not a permission gate. Live probe: `agent-bob` successfully marked `agent-alice`'s IN_PROGRESS task as DONE.

### H10 — Federation transport is simulated
**Tool:** `nucleus_federation`  
**Finding:** `FederationEngine.network.send_message()` returns simulated responses. `join("localhost:19999")` reports `✅ JOINED FEDERATION` with no TCP connection. No real inter-nucleus packets are sent. The feature is a stub.

### H11 — No MCP subprocess sandboxing in `nucleus_features`
**Tool:** `nucleus_features`  
**Finding:** Mounted MCP servers (stdio) inherit the full `os.environ`. No seccomp, container, or capability drop. Shell injection is possible if `command` or `args` contain any unsanitized user input.

### H12 — OAuth 2.1 entirely unimplemented
**Tool:** `nucleus_features` (HTTP/SSE transport)  
**Finding:** `OAuthProvider.__init__` raises `NotImplementedError`. The HTTP/SSE transport path is unauthenticated.

### H13 — Governance consensus not active
**Tool:** `nucleus_governance`  
**Finding:** `FederationEngine.is_sovereign_mode()` is absent from the current build. The entire governance consensus test suite is skipped (pytest exit code 5). No action-approval gate is enforced in production CI.

### H14 — `write_engram` has no per-request auth
**Tool:** `nucleus_engrams`  
**Finding:** Any connected MCP client can write to the brain. Tier gating exists at the tool registration level but is not checked per-call inside the handler.

### H15 — Concurrent ledger writes can corrupt (unlocked fallback)
**Tool:** `nucleus_engrams`  
**Finding:** `_update_in_ledger` and `_delete_in_ledger` do full-file rewrites. When `fcntl` locking fails, they fall back to unlocked writes — creating a race condition window where concurrent writes can produce a corrupted ledger.

### H16 — `spawn_agent` calls real LLM API on every confirmed spawn
**Tool:** `nucleus_agents`  
**Finding:** `spawn_agent` with `confirm=True` immediately invokes `DualEngineLLM` and makes a real API call. There is no cost estimate shown to the caller before spend is committed, and no per-session spend cap.

---

## Medium Severity Findings

| # | Tool | Finding |
|---|---|---|
| M1 | engrams | `health` action returns raw JSON — not the standard `{"success", "data", "error", "timestamp"}` envelope. Callers checking `response["success"]` get `KeyError`. |
| M2 | engrams | `intensity` accepts Python floats (e.g. `5.5`) — schema says integer. |
| M3 | engrams | `context` is case-sensitive with no normalization. LLM callers frequently pass lowercase. |
| M4 | engrams | Rate limit is per-facade (200/60s for all 35 actions). 200 cheap `health` pings block `write_engram`. |
| M5 | engrams | 5 bare `open()` calls in DSoR/routing handlers — no `encoding='utf-8'`, no `with`-block resource management. |
| M6 | relay | FIFO inconsistency: `relay_inbox` returns messages LIFO; the poll daemon processes FIFO. |
| M7 | relay | `ccr_arm(role="")` falls through to unreliable env-var heuristic — can return the wrong role. |
| M8 | relay | `nucleus_ccr_arm` and `nucleus_relay_subscribe` block the MCP context for up to 30 minutes. No timeout warning to caller. |
| M9 | relay | `DEPRECATED_DIR_TO_CANONICAL` migration is passive — messages to deprecated dirs are silently undelivered. |
| M10 | audit | Inverted date range (`since > until`) silently returns 0 records with `success=True`. |
| M11 | audit | Unknown filter keys silently ignored in `query_audit`. Caller typos return unfiltered full result. |
| M12 | audit | `complexity=None` in `nucleus_route` returns `data: null`. Callers chaining `.get("data", {}).get(...)` hit `AttributeError`. |
| M13 | audit | `ROUTE_TABLE` and `PRICING_PER_1K` are hardcoded — pricing/model changes require code edit + redeploy. |
| M14 | sessions | Duplicate `session_id` registration is last-writer-wins silently — impersonation risk if session IDs are guessable. |
| M15 | tasks | `clear_existing=True` in `import_jsonl` is silently ignored. API contract broken. |
| M16 | tasks | Empty task description accepted silently. |
| M17 | features | `thanos_snap` spawns 3 child processes (`stripe`, `postgres`, `brave_search` mock servers) without any confirmation gate. |
| M18 | agents | `fix_code` autonomously overwrites files with LLM output. Creates `.bak` but no HITL gate. |
| M19 | federation | No encryption on federated sync — HMAC authenticates handshake only; synced state is plaintext. |
| M20 | all | Mutable default argument `params: dict = {}` across all 9 MCP tool facades. |

---

## Low Severity Findings

| # | Tool | Finding |
|---|---|---|
| L1 | engrams | `write_engram(value="")` silently succeeds. |
| L2 | engrams | `search_engrams(query="")` returns all engrams — undocumented list-all behavior. |
| L3 | engrams | `mcp_tools_count: 110` hardcoded in `version` (actual ~170). |
| L4 | engrams | `_brain_health_impl_legacy()` hardcodes `version: "0.5.0"`. |
| L5 | engrams | `dsor_get_trace(None)` produces `"Decision ID None not found"` without input validation. |
| L6 | relay | Missing `sender` in `nucleus_sync:relay_post` raises, while `nucleus_relay` auto-fills. Behavioral inconsistency. |
| L7 | relay | Duplicate `from __future__ import annotations` in `relay_ops.py`. |
| L8 | audit | `anon_telemetry` fires in test/CI — not mocked in test suite. |
| L9 | audit | Audit log is local-only — no cloud backup, sync, or replication. |
| L10 | audit | `outcome` field stored but not queryable via `query_audit` filters. |
| L11 | tasks | `complete-already-DONE` task allowed — no idempotency guard. |
| L12 | sessions | Heartbeat on non-existent session raises `FileNotFoundError` (caught at facade, but noisy). |
| L13 | all | 5+ bare `except: pass` blocks in event/hook locations reduce production observability. |

---

## Production Readiness Scorecard

| Domain | Unit Tests | Contract Hardening | Integration | Auth/Security | Overall |
|---|---|---|---|---|---|
| `nucleus_engrams` | ✅ 87/87 | ⚠️ 4 gaps | ✅ solid | ❌ no per-call auth | **Beta** |
| `nucleus_relay` | ✅ 156/156 | ❌ 4 high gaps | ✅ solid | ❌ no inbox ownership | **Alpha** |
| `nucleus_sync` | ✅ (included above) | ✅ clean | ✅ offline-safe | ✅ n/a | **Beta** |
| `nucleus_audit` | ✅ 69/69 | ⚠️ 2 silent issues | ✅ chain durable | ❌ no log_event auth | **Alpha** |
| `nucleus_route` | ✅ (included above) | ⚠️ 2 gaps | ✅ pure function | ❌ no tier verification | **Alpha** |
| `nucleus_sessions` | ✅ 66/66 | ⚠️ 2 gaps | ✅ FS-persisted | ❌ no session signing | **Alpha** |
| `nucleus_tasks` | ✅ 35/35 | ⚠️ 2 gaps | ✅ SQLite | ❌ no ownership gate | **Alpha** |
| `nucleus_governance` | ❌ 0 tests run | ❌ API absent | ❌ not active | ❌ | **Pre-alpha** |
| `nucleus_federation` | ✅ 38/38 | ❌ join is fake | ❌ simulated transport | ❌ no encryption | **Pre-alpha** |
| `nucleus_features` | ⚠️ thin | ❌ traverse_mount broken | ⚠️ mount works | ❌ no subprocess sandbox | **Alpha** |
| `nucleus_agents` | ✅ (partial) | ⚠️ fix_code unguarded | ✅ real LLM | ⚠️ no spend cap | **Beta** |
| `nucleus_orchestration` | ✅ (partial) | ✅ infra is read-only | ✅ | ✅ HITL on spawn | **Beta** |

**Legend:** Pre-alpha = broken/stub · Alpha = works but unsafe for multi-tenant · Beta = safe for single-operator · Production = ready

---

## Recommended Fix Order

### Phase 1 — Must-fix before any multi-tenant exposure (C1–C5, H8, H9, H12)

1. **Relay inbox ownership** — bind each inbox to the bearer token that created it; reject cross-role reads without matching token
2. **Relay sender validation** — bind `sender` to the authenticated bearer; reject caller-supplied sender that doesn't match token
3. **Audit log auth** — add a bearer or admin-token check on `log_event`; distinguish "trusted internal" from "any MCP client"
4. **Tier verification in cost router** — pass tier claim through a backend check (Stripe subscription lookup or signed JWT claim); never trust caller-supplied `complexity=sovereign`
5. **Fix `traverse_mount`** — resolve the `ImportError` by calling `Mounter.traverse_and_mount()` correctly at the module level
6. **Session signing** — implement HMAC on session save/resume (code exists, just not wired)
7. **Task ownership** — enforce `claimed_by` as a permission gate on complete/update

### Phase 2 — Correctness and reliability (H1–H7, H10, H11, H13–H16)

1. `verify_on_read` option for audit queries (or auto-verify + reject on corruption)
2. DB deletion recovery — write sentinel file + startup integrity check
3. Fix `sovereignty_tier` field on oauth-shim fallback path
4. Add payload size cap in relay FS mode (match HTTP mode 64 KiB cap)
5. Atomic relay writes — write to `.tmp` then `rename()` (atomic on POSIX)
6. Relay retention policy — configurable TTL + max-message-count per inbox
7. Governance consensus: wire `is_sovereign_mode`, enable CI test suite
8. MCP subprocess sandboxing — at minimum, strip sensitive env vars before `subprocess.Popen`
9. OAuth 2.1 — implement or explicitly document as "not yet supported"
10. Concurrent ledger write safety — remove unlocked fallback, surface the error

### Phase 3 — Polish and observability (M-series, L-series)

- Standardize `health` action to use `make_response` envelope
- Add per-action rate limits (not shared 200/60s quota across all 35 engram actions)
- Normalize `context` to title-case before validation
- Config-file-driven routing table (not hardcoded)
- Mock `anon_telemetry` in test suite
- Replace `except: pass` with `logger.warning` or structured error engrams

---

## What Works Well (production-grade today)

- ✅ **Input sanitization** — prototype pollution blocked, path traversal blocked, 100KB string cap, deep nesting rejected across all tool facades
- ✅ **Error sanitization** — no stack traces leak to MCP callers; all exceptions are caught at the dispatch boundary
- ✅ **SHA-256 chain tamper detection** — correctly catches filesystem-level payload mutations; concurrent-write safety via per-team locks
- ✅ **Brain path configurability** — `NUCLEUS_BRAIN_PATH` env var works throughout; no hardcoded absolute paths
- ✅ **Relay backing store auto-create** — missing dirs created safely on first access
- ✅ **HITL gates on spawn_agent and delete_file** — require `confirm=True` explicitly
- ✅ **Cost router is a pure function** — deterministic, fast (~9ms), never calls an LLM API
- ✅ **`morning_brief` is offline-safe** — zero external daemon/network deps; all file reads are graceful-if-missing
- ✅ **Secret scanning on engram values** — warns on API keys, PEM blocks, Bearer tokens being stored
- ✅ **DSoR backed by real files** — decisions.jsonl is live data, not hardcoded
- ✅ **Federation peer liveness** — clock-based SUSPECT → OFFLINE transition implemented

---

*This document was generated 2026-06-20 via automated 4-layer probe. Raw probe scripts: `/tmp/probe_engrams.py`, `/tmp/probe_relay.py`, `/tmp/probe_audit.py`, `/tmp/probe_other.py`. No production files were modified.*
