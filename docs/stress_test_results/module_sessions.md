# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 196
**Actions tested:** 28
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 28 | 14.3% | Tool returned a successful response |
| ⚠️ handled | 168 | 85.7% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **196** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 28 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 28 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **28** | **100%** |

## Per-Module Breakdown

### Module: `sessions` (28 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `archive_resolved` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `check_recent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `conversation_stats` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `current` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `detect_splits` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `emit_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `end` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `events` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `garbage_collect` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_state` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `handoff_summary` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `heartbeat` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `ingest_conversations` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_agents` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_conversations` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `propose_merges` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `read_events` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `recent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume_checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `save` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search_conversations` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `unregister` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `update_state` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `sessions.archive_resolved`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.check_recent`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.checkpoint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.conversation_stats`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.current`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.detect_splits`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.emit_event`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.end`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.events`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.garbage_collect`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.get_state`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.handoff_summary`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.heartbeat`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.ingest_conversations`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list_agents`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list_conversations`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.propose_merges`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.read_events`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.recent`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.register`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.resume`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.resume_checkpoint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.save`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.search_conversations`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.start`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.8s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.unregister`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.update_state`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_engrams: 200 calls per 60s window. Try again in 23.7s.",
  "module": "nucleus_engrams"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace",`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**28/28 actions return a useful response when called with empty action + empty params.**
**0 actions fail or crash.**

This tests the 'fire without thinking' pattern — an LLM that just calls `nucleus_engrams('', {})`
without knowing what action to use or what params to pass. Every action should return a
structured response (even if it's an error), not crash.

## Methodology

### Test Harness

The stress test harness (`scripts/stress_test_tools.py`) uses a MockMCP object that captures
all tool registrations without starting a real MCP server. Each tool function is called
directly with the test params, and the result is classified as:

- **pass** — Tool returned a successful response (JSON with `success: true`)
- **handled** — Tool returned a graceful error (JSON with `success: false` or `error: ...`)
- **warn** — Static analysis warning (cross-agent compat check)
- **fail** — Tool failed without a structured response
- **crash** — Unhandled exception (KeyError, AttributeError, TypeError, IndexError)

### Test Angles

**happy**
- Valid params provided — the "normal" call an LLM would make

**missing_params**
- No params provided at all (empty dict {}) — tests required-param validation

**wrong_types**
- Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

**empty_params**
- Empty params dict {} — same as missing_params, tests default handling

**unknown_action**
- Action name that does not exist in this tool's ROUTER — tests error handling for typos

**fire_without_thinking**
- Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

**cross_agent_compat**
- Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

### Test Params

For the 'happy path' angle, the harness uses a dictionary of default params based on
common action names (e.g., `query` → `{'query': 'test', 'limit': 5}`). Actions that
require specific params (like an `id` that exists in the brain) will return 'handled'
instead of 'pass' because the test params don't match real data.

### Limitations

1. **Happy path params are generic.** Some actions need specific brain state (e.g., a real
   engram ID) to succeed. The test uses generic params, so 'handled' may mean 'correctly
   rejected because the ID doesn't exist' rather than 'broken.'
2. **Cross-agent compat is static analysis.** The harness checks function signatures,
   docstrings, and source code — it does not actually test against Claude, Cursor, or
   Windsurf MCP clients.
3. **No real MCP server.** The MockMCP captures registrations but doesn't test the full
   MCP protocol (JSON-RPC, schema generation, transport).
