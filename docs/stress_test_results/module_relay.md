# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T07:23:15
**Total tests:** 28
**Actions tested:** 4
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 11 | 39.3% | Tool returned a successful response |
| ⚠️ handled | 17 | 60.7% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **28** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 2 | 50.0% |
| ⚠️ handled | 2 | 50.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 2 | 50.0% |
| ⚠️ handled | 2 | 50.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 1 | 25.0% |
| ⚠️ handled | 3 | 75.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 2 | 50.0% |
| ⚠️ handled | 2 | 50.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 4 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### fire_without_thinking

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 4 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 4 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **4** | **100%** |

## Per-Module Breakdown

### Module: `relay` (4 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `ack` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `inbox` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `post` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `relay.ack`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "acked": 0,
  "failed": 0,
  "error": "fs_mode_caller_should_route_to_relay_ops"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "acked": 0,
  "failed": 0,
  "error": "fs_mode_caller_should_route_to_relay_ops"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Action 'ack' failed: No bearer for role='wrong_type'. Expected per-role file at /home/operator/.tb/relay_token_wrong_type (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucleu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "acked": 0,
  "failed": 0,
  "error": "fs_mode_caller_should_route_to_relay_ops"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ],
  "hint": "Try: nucleus_relay(action='ack', para`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `relay.inbox`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "messages": [],
  "role": "main",
  "has_more": false,
  "rate_limited": false,
  "transport_error": false
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "messages": [],
  "role": "main",
  "has_more": false,
  "rate_limited": false,
  "transport_error": false
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Action 'inbox' failed: No bearer for role='wrong_type'. Expected per-role file at /home/operator/.tb/relay_token_wrong_type (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucl`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "messages": [],
  "role": "main",
  "has_more": false,
  "rate_limited": false,
  "transport_error": false
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ],
  "hint": "Try: nucleus_relay(action='ack', para`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `relay.post`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sent": false,
  "error": "missing_to_field"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sent": false,
  "error": "missing_to_field"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Action 'post' failed: No bearer for role='wrong_type'. Expected per-role file at /home/operator/.tb/relay_token_wrong_type (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucle`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sent": false,
  "error": "missing_to_field"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ],
  "hint": "Try: nucleus_relay(action='ack', para`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `relay.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "is_http_mode": false,
  "relay_url_set": false,
  "bearer_set": false,
  "canonical_role": "main",
  "resolved_inbox_dir": "claude_code_main"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "is_http_mode": false,
  "relay_url_set": false,
  "bearer_set": false,
  "canonical_role": "main",
  "resolved_inbox_dir": "claude_code_main"
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "is_http_mode": false,
  "relay_url_set": false,
  "bearer_set": false,
  "canonical_role": "wrong_type",
  "resolved_inbox_dir": "wrong_type"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "is_http_mode": false,
  "relay_url_set": false,
  "bearer_set": false,
  "canonical_role": "main",
  "resolved_inbox_dir": "claude_code_main"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ],
  "hint": "Try: nucleus_relay(action='ack', para`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_relay",
  "available_actions": [
    "ack",
    "inbox",
    "post",
    "status"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**4/4 actions return a useful response across 5 confused-LLM scenarios.**
**0 actions fail or crash.**

This tests 5 scenarios an LLM might produce when confused:
1. **empty_action** — `('', {})` — LLM sends empty string
2. **none_action** — `(None, {})` — LLM forgot to fill the action param
3. **params_as_string** — `(action, 'just a prompt string')` — LLM passed a string instead of dict
4. **swapped_args** — `(params_dict, action_string)` — LLM put params in the action slot
5. **guessed_action** — `(action, {'random_garbage': True})` — LLM guessed an action but passed garbage

Every action should return a structured response (even if it's an error), not crash.

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
- 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

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
