# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T12:30:27
**Total tests:** 1862
**Actions tested:** 266
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 950 | 51.0% | Tool returned a successful response |
| ⚠️ handled | 912 | 49.0% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **1862** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 215 | 80.8% |
| ⚠️ handled | 51 | 19.2% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 142 | 53.4% |
| ⚠️ handled | 124 | 46.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 185 | 69.5% |
| ⚠️ handled | 81 | 30.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 142 | 53.4% |
| ⚠️ handled | 124 | 46.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 266 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### fire_without_thinking

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 266 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 266 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

## Per-Module Breakdown

### Module: `audit_log_tool` (4 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `admin_query` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `log_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `query` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `verify` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `audit_log_tool.admin_query`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "admin_query: invalid or missing admin_token"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "admin_query: invalid or missing admin_token"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "admin_query: invalid or missing admin_token"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "admin_query: invalid or missing admin_token"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ],
  "hint": "Try: nucleus_audit(actio`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.log_event`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "log_event requires: event_type, actor, resource, outcome"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "log_event requires: event_type, actor, resource, outcome"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "log_event requires: event_type, actor, resource, outcome"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "log_event requires: event_type, actor, resource, outcome"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ],
  "hint": "Try: nucleus_audit(actio`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.query`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "count": 0,
    "records": []
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "count": 0,
    "records": []
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "count": 0,
    "records": []
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "count": 0,
    "records": []
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ],
  "hint": "Try: nucleus_audit(actio`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.verify`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "chain_ok": true,
    "broken_at_id": null
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "chain_ok": true,
    "broken_at_id": null
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "chain_ok": true,
    "broken_at_id": null
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "chain_ok": true,
    "broken_at_id": null
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ],
  "hint": "Try: nucleus_audit(actio`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_audit",
  "available_actions": [
    "admin_query",
    "log_event",
    "query",
    "verify"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `cost_router` (1 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `route` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `cost_router.route`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "provider": "anthropic",
    "model": "claude-haiku-3-5",
    "complexity": "routine",
    "sovereignty_tier": "standard",
    "estimated_input_tokens": 1,
    "ex`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "provider": "anthropic",
    "model": "claude-haiku-3-5",
    "complexity": "routine",
    "sovereignty_tier": "standard",
    "estimated_input_tokens": 1,
    "ex`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "provider": "anthropic",
    "model": "claude-haiku-3-5",
    "complexity": "routine",
    "sovereignty_tier": "standard",
    "estimated_input_tokens": 1,
    "ex`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "provider": "anthropic",
    "model": "claude-haiku-3-5",
    "complexity": "routine",
    "sovereignty_tier": "standard",
    "estimated_input_tokens": 1,
    "ex`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_route",
  "available_actions": [
    "route"
  ],
  "hint": "Try: nucleus_route(action='route', params={...})"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_route",
  "available_actions": [
    "route"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `engrams` (38 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `audit_log` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `billing_summary` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `compounding_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `context_graph` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `dsor_get_trace` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `dsor_query_decisions` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `dsor_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `end_of_day` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `engram_neighbors` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `export_schema` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `federation_dsor` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `fusion_reactor` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `governance_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `health` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `heartbeat_check` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `heartbeat_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `hook_metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `ipc_tokens` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_decisions` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_snapshots` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_tools` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `metering_summary` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `morning_brief` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `performance_metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `prometheus_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pulse_and_polish` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `query_engrams` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `render_graph` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `routing_decisions` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `search` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `search_engrams` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `self_healing_sre` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `session_inject` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `tier_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `version` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `weekly_consolidate` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `write_engram` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |

#### `engrams.add`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "key": "test-key",
    "value": "test-value",
    "context": "Decision",
    "intensity": 5,
    "adun": {
      "added": 0,
      "updated": 0,
      "deleted": 0`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision', intensit`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid context: expected str, got int`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision', intensit`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.audit_log`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-26T06:56:14.876946Z",
        "emitter": "brain_write_engram",
        "type": "engram_written",
        "hash":`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-26T06:56:14.876946Z",
        "emitter": "brain_write_engram",
        "type": "engram_written",
        "hash":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error reading audit log: '>' not supported between instances of 'int' and 'str'",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:14.882094Z"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-26T06:56:14.876946Z",
        "emitter": "brain_write_engram",
        "type": "engram_written",
        "hash":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.billing_summary`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 181.2,
    "total_interactions": 1812,
    "breakdown": {
      "unknown": {
        "cost": 90.2,
        "count": 902,
        "tier": 1
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 181.2,
    "total_interactions": 1812,
    "breakdown": {
      "unknown": {
        "cost": 90.2,
        "count": 902,
        "tier": 1
    `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'billing_summary': unsupported type for timedelta hours component: str",
  "expected_params": "(since_hours=None, group_by='tool')",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 181.2,
    "total_interactions": 1812,
    "breakdown": {
      "unknown": {
        "cost": 90.2,
        "count": 902,
        "tier": 1
    `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.compounding_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Friday\n==================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Friday\n==================`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Friday\n==================`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Friday\n==================`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.context_graph`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "brief_56975",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "growth_hook_morning_brief_gen`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "brief_56975",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "growth_hook_morning_brief_gen`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_graph': '>=' not supported between instances of 'int' and 'str'",
  "expected_params": "(include_edges=True, min_intensity=1)",
  "provided_params": [
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "brief_56975",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "growth_hook_morning_brief_gen`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.dsor_get_trace`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Decision ID test-id not found in ledger.",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:15.749392Z"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_get_trace': register.<locals>.<lambda>() missing 1 required positional argument: 'decision_id'",
  "expected_params": "(decision_id)",
  "provided_params"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Decision ID 12345 not found in ledger.",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:15.749577Z"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_get_trace': register.<locals>.<lambda>() missing 1 required positional argument: 'decision_id'",
  "expected_params": "(decision_id)",
  "provided_params"`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.dsor_query_decisions`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "limit must be a number, got str",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:15.750401Z"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.dsor_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "ACTIVE",
        "total": 16
      },
      "snapshots`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "ACTIVE",
        "total": 16
      },
      "snapshots`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "ACTIVE",
        "total": 16
      },
      "snapshots`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "ACTIVE",
        "total": 16
      },
      "snapshots`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.end_of_day`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "day": "Friday",
    "week": 26,
    "engrams_written": 1,
    "details": [
      {
        "key": "daily_summary_2026-06-26",
        "result`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': register.<locals>.<lambda>() missing 1 required positional argument: 'summary'",
  "expected_params": "(summary, key_decisions=None, blockers=None`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': object of type 'int' has no len()",
  "expected_params": "(summary, key_decisions=None, blockers=None)",
  "provided_params": [
    "summary",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': register.<locals>.<lambda>() missing 1 required positional argument: 'summary'",
  "expected_params": "(summary, key_decisions=None, blockers=None`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.engram_neighbors`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "target": {
      "id": "test-key",
      "context": "Decision",
      "intensity": 5
    },
    "neighbors": [
      {
        "id": "daily_summary_2026-06-26",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'engram_neighbors': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key, max_depth=1)",
  "provided_params":`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "Engram 'wrong_type' not found in graph",
    "node_count": 122
  },
  "error": null
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'engram_neighbors': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key, max_depth=1)",
  "provided_params":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.export_schema`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "openapi": "3.0.0",
  "info": {
    "title": "mock-mcp API",
    "version": "0.5.0",
    "description": "Auto-generated schema for Nucleus MCP Tools, Prompts, and Resources"
  },
  "paths": {
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "openapi": "3.0.0",
  "info": {
    "title": "mock-mcp API",
    "version": "0.5.0",
    "description": "Auto-generated schema for Nucleus MCP Tools, Prompts, and Resources"
  },
  "paths": {
    `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "openapi": "3.0.0",
  "info": {
    "title": "mock-mcp API",
    "version": "0.5.0",
    "description": "Auto-generated schema for Nucleus MCP Tools, Prompts, and Resources"
  },
  "paths": {
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "openapi": "3.0.0",
  "info": {
    "title": "mock-mcp API",
    "version": "0.5.0",
    "description": "Auto-generated schema for Nucleus MCP Tools, Prompts, and Resources"
  },
  "paths": {
    `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.federation_dsor`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "event_counts": {
      "peer_joined": 0,
      "peer_left": 0,
      "peer_suspect": 0,
      "leader_elected": 0,
      "task_routed": 0,
      "state_synced": 0`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "event_counts": {
      "peer_joined": 0,
      "peer_left": 0,
      "peer_suspect": 0,
      "leader_elected": 0,
      "task_routed": 0,
      "state_synced": 0`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "event_counts": {
      "peer_joined": 0,
      "peer_left": 0,
      "peer_suspect": 0,
      "leader_elected": 0,
      "task_routed": 0,
      "state_synced": 0`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "event_counts": {
      "peer_joined": 0,
      "peer_left": 0,
      "peer_suspect": 0,
      "leader_elected": 0,
      "task_routed": 0,
      "state_synced": 0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.fusion_reactor`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "pipeline": "fusion_reactor",
    "version": "1.0.0",
    "timestamp": "2026-06-26T12:26:15.938725",
    "observation": "test",
    "sections": {
      "capture": `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': register.<locals>.<lambda>() missing 1 required positional argument: 'observation'",
  "expected_params": "(observation, context='Decision', i`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': can only concatenate str (not \"int\") to str",
  "expected_params": "(observation, context='Decision', intensity=6, write_engrams=True)",
  "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': register.<locals>.<lambda>() missing 1 required positional argument: 'observation'",
  "expected_params": "(observation, context='Decision', i`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.governance_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "policies": {
      "default_deny": true,
      "isolation_boundaries": true,
      "immutable_audit": false,
      "cryptographic_hashing": false
    },
    "stat`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "policies": {
      "default_deny": true,
      "isolation_boundaries": true,
      "immutable_audit": false,
      "cryptographic_hashing": false
    },
    "stat`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "policies": {
      "default_deny": true,
      "isolation_boundaries": true,
      "immutable_audit": false,
      "cryptographic_hashing": false
    },
    "stat`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "policies": {
      "default_deny": true,
      "isolation_boundaries": true,
      "immutable_audit": false,
      "cryptographic_hashing": false
    },
    "stat`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.health`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 2,
  "python_version": "3.14.4"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 2,
  "python_version": "3.14.4"
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 2,
  "python_version": "3.14.4"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 2,
  "python_version": "3.14.4"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.heartbeat_check`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T06:56:18.387641+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 2.6,
    "formatt`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T06:56:18.729778+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 6.6,
    "formatt`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T06:56:20.116267+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 0.1,
    "formatt`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T06:56:20.491194+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 7.1,
    "formatt`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.heartbeat_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "~/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "installed": true`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "~/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "installed": true`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "~/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "installed": true`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "~/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "installed": true`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.hook_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 703,
    "outcomes": {
      "ADD": 72,
      "NOOP": 204,
      "UNKNOWN": 290,
      "UPDATE": 137
    },
    "by_event_type": {
      "morni`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 703,
    "outcomes": {
      "ADD": 72,
      "NOOP": 204,
      "UNKNOWN": 290,
      "UPDATE": 137
    },
    "by_event_type": {
      "morni`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 703,
    "outcomes": {
      "ADD": 72,
      "NOOP": 204,
      "UNKNOWN": 290,
      "UPDATE": 137
    },
    "by_event_type": {
      "morni`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 703,
    "outcomes": {
      "ADD": 72,
      "NOOP": 204,
      "UNKNOWN": 290,
      "UPDATE": 137
    },
    "by_event_type": {
      "morni`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.ipc_tokens`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [
      {
        "token_id": "ipc-c263ab3d0bf96983242ddd3a",
        "events": [
          {
            "event": "issued",
            "token_id": "ipc`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [
      {
        "token_id": "ipc-c263ab3d0bf96983242ddd3a",
        "events": [
          {
            "event": "issued",
            "token_id": "ipc`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [
      {
        "token_id": "ipc-c263ab3d0bf96983242ddd3a",
        "events": [
          {
            "event": "issued",
            "token_id": "ipc`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [
      {
        "token_id": "ipc-c263ab3d0bf96983242ddd3a",
        "events": [
          {
            "event": "issued",
            "token_id": "ipc`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.list_decisions`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: bad operand type for unary -: 'str'"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [
      {
        "decision_id": "dec-319af3817f72",
        "intent": "Route task 12345 to brain_test-brain",
        "reasoning": "Composite score=0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.list_snapshots`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "snapshots": [],
    "count": 0
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "snapshots": [],
    "count": 0
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "snapshots": [],
    "count": 0
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "snapshots": [],
    "count": 0
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.list_tools`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "tier": "ADVANCED",
    "tier_level": 2,
    "total_tools": 21,
    "tools": [
      "nucleus_agents",
      "nucleus_audit",
      "nucleus_ccr_arm",
      "nucle`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "tier": "ADVANCED",
    "tier_level": 2,
    "total_tools": 21,
    "tools": [
      "nucleus_agents",
      "nucleus_audit",
      "nucleus_ccr_arm",
      "nucle`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "tier": "ADVANCED",
    "tier_level": 2,
    "total_tools": 0,
    "tools": []
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "tier": "ADVANCED",
    "tier_level": 2,
    "total_tools": 21,
    "tools": [
      "nucleus_agents",
      "nucleus_audit",
      "nucleus_ccr_arm",
      "nucle`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.metering_summary`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 4,
    "total_units": 4.0,
    "by_scope": {
      "federation_join": 4.0
    },
    "by_resource_type": {
      "federation_join": 4.0
    },
   `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 4,
    "total_units": 4.0,
    "by_scope": {
      "federation_join": 4.0
    },
    "by_resource_type": {
      "federation_join": 4.0
    },
   `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported type for timedelta hours component: str"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 4,
    "total_units": 4.0,
    "by_scope": {
      "federation_join": 4.0
    },
    "by_resource_type": {
      "federation_join": 4.0
    },
   `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.morning_brief`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 12:26 PM\n====================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 12:26 PM\n====================`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 12:26 PM\n====================`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 12:26 PM\n====================`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.performance_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "No metrics collected. Set NUCLEUS_PROFILING=true."
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "No metrics collected. Set NUCLEUS_PROFILING=true."
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "No metrics collected. Set NUCLEUS_PROFILING=true."
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "No metrics collected. Set NUCLEUS_PROFILING=true."
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.prometheus_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-26T06:56:20.564069+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-26T06:56:20.564543+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "format must be str, got int"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-26T06:56:20.564928+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.pulse_and_polish`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "steps": [
      {
        "name": "pulse",
        "status": "skipped",
        "reason": "cannot import name 'capture_pulse' from 'mcp_server_nucleus.runtime.pul`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "steps": [
      {
        "name": "pulse",
        "status": "skipped",
        "reason": "cannot import name 'capture_pulse' from 'mcp_server_nucleus.runtime.pul`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "steps": [
      {
        "name": "pulse",
        "status": "skipped",
        "reason": "cannot import name 'capture_pulse' from 'mcp_server_nucleus.runtime.pul`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "steps": [
      {
        "name": "pulse",
        "status": "skipped",
        "reason": "cannot import name 'capture_pulse' from 'mcp_server_nucleus.runtime.pul`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.query_engrams`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "blockers_2026-06-26",
        "value": "w; r; o; n; g; _; t; y; p; e",
        "context": "Decision",
        "intensity": 9,
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "blockers_2026-06-26",
        "value": "w; r; o; n; g; _; t; y; p; e",
        "context": "Decision",
        "intensity": 9,
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid min_intensity: expected number, got str`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "blockers_2026-06-26",
        "value": "w; r; o; n; g; _; t; y; p; e",
        "context": "Decision",
        "intensity": 9,
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.render_graph`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "ascii": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "ascii": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'render_graph': '>=' not supported between instances of 'int' and 'str'",
  "expected_params": "(max_nodes=30, min_intensity=1)",
  "provided_params": [
    "ma`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "ascii": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.routing_decisions`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_decisions": 0,
    "decisions": []
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_decisions": 0,
    "decisions": []
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: bad operand type for unary -: 'str'"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_decisions": 0,
    "decisions": []
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.search`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "sre_diagnosis_20260626_1012",
        "value": "SRE Diagnosis 2026-06-26 10:12: symptom='test' severity=CRITICAL findings=2 ac`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",
  "prov`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid query: expected str, got int`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",
  "prov`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.search_engrams`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "sre_diagnosis_20260626_1012",
        "value": "SRE Diagnosis 2026-06-26 10:12: symptom='test' severity=CRITICAL findings=2 ac`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search_engrams': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid query: expected str, got int`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'search_engrams': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.self_healing_sre`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "pipeline": "self_healing_sre",
    "version": "1.0.0",
    "timestamp": "2026-06-26T12:26:20.623348",
    "symptom": "test",
    "sections": {
      "search": {
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'self_healing_sre': register.<locals>.<lambda>() missing 1 required positional argument: 'symptom'",
  "expected_params": "(symptom, write_engram=True)",
  "pro`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "pipeline": "self_healing_sre",
    "version": "1.0.0",
    "timestamp": "2026-06-26T12:26:20.624682",
    "symptom": "wrong_type",
    "sections": {
      "search`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'self_healing_sre': register.<locals>.<lambda>() missing 1 required positional argument: 'symptom'",
  "expected_params": "(symptom, write_engram=True)",
  "pro`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.session_inject`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 recurring_3adaa98b: R`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 recurring_3adaa98b: R`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 recurring_3adaa98b: R`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 recurring_3adaa98b: R`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.tier_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "current_tier": "ADVANCED",
    "tier_level": 2,
    "tier_breakdown": {
      "tier_0": 2,
      "tier_1": 5,
      "tier_2": 5
    },
   `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "current_tier": "ADVANCED",
    "tier_level": 2,
    "tier_breakdown": {
      "tier_0": 2,
      "tier_1": 5,
      "tier_2": 5
    },
   `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "current_tier": "ADVANCED",
    "tier_level": 2,
    "tier_breakdown": {
      "tier_0": 2,
      "tier_1": 5,
      "tier_2": 5
    },
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "current_tier": "ADVANCED",
    "tier_level": 2,
    "tier_breakdown": {
      "tier_0": 2,
      "tier_1": 5,
      "tier_2": 5
    },
   `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.version`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: 1.2.1
   Python: 3.14.4
   Platform: Darwin 25.5.0

🔧 CAPABILITIES
   MCP Tools: 110+
   Architecture: Trinity (Or`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: 1.2.1
   Python: 3.14.4
   Platform: Darwin 25.5.0

🔧 CAPABILITIES
   MCP Tools: 110+
   Architecture: Trinity (Or`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: 1.2.1
   Python: 3.14.4
   Platform: Darwin 25.5.0

🔧 CAPABILITIES
   MCP Tools: 110+
   Architecture: Trinity (Or`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🧠 NUCLEUS VERSION INFO
═══════════════════════════════════════

📦 VERSION
   Nucleus: 1.2.1
   Python: 3.14.4
   Platform: Darwin 25.5.0

🔧 CAPABILITIES
   MCP Tools: 110+
   Architecture: Trinity (Or`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.weekly_consolidate`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "week": 26,
    "dry_run": true,
    "actions": [
      {
        "action": "garbage_collect_tasks",
        "archived": 0,
        "kept": 0
      },
      {
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "week": 26,
    "dry_run": true,
    "actions": [
      {
        "action": "garbage_collect_tasks",
        "archived": 0,
        "kept": 0
      },
      {
    `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "week": 26,
    "dry_run": "not_a_bool",
    "actions": [
      {
        "action": "garbage_collect_tasks",
        "archived": 0,
        "kept": 0
      },
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "week": 26,
    "dry_run": true,
    "actions": [
      {
        "action": "garbage_collect_tasks",
        "archived": 0,
        "kept": 0
      },
      {
    `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

#### `engrams.write_engram`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "key": "test-key",
    "value": "test-value",
    "context": "Decision",
    "intensity": 5,
    "adun": {
      "added": 0,
      "updated": 0,
      "deleted": 0`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'write_engram': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision',`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid context: expected str, got int`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'write_engram': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision',`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

### Module: `features` (16 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `discover_tools` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `generate_proof` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `get` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_proof` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `invoke_tool` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_mounted` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_proofs` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `mount_server` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `search` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `thanos_snap` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `traverse_mount` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `unmount_server` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `validate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `features.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Feature 'test' already exists"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 7 required positional arguments: 'product', 'name', 'description', 'source', 'version', 'how_to_test', and 'expected_r`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Feature 'wrong_type' already exists"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 7 required positional arguments: 'product', 'name', 'description', 'source', 'version', 'how_to_test', and 'expected_r`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.discover_tools`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.762814Z"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.762881Z"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Server wrong_type not found",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.762933Z"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.762977Z"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.generate_proof`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"success": true, "message": "Proof generated for test-id", "path": "/tmp/test-brain/features/proofs/test-id.md"}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error generating proof: 'int' object has no attribute 'upper'`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.get`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Feature 'test-id' not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Feature '12345' not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.get_proof`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `# Proof: test-id

> Generated: 2026-06-26 12:26:21

## Thinking
None

## Deployed URL
None

## Files Changed
None

## Rollback Plan
- **Risk Level:** LOW
- **Estimated Time:** 15 minutes
- **Strategy:`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Proof for 12345 not found.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.invoke_tool`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"success": false, "error": "Server test not found"}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"success": false, "error": "Server wrong_type not found"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "features": [
    {
      "id": "test",
      "name": "test",
      "description": "test",
      "product": "test",
      "source": "test",
      "version": "test",
      "status": "development",
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "features": [
    {
      "id": "test",
      "name": "test",
      "description": "test",
      "product": "test",
      "source": "test",
      "version": "test",
      "status": "development",
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "features": [],
  "total": 0
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "features": [
    {
      "id": "test",
      "name": "test",
      "description": "test",
      "product": "test",
      "source": "test",
      "version": "test",
      "status": "development",
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list_mounted`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.14/bin/python3.14",
      "args": [
        "~/ai-mvp-backend/scri`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.14/bin/python3.14",
      "args": [
        "~/ai-mvp-backend/scri`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.14/bin/python3.14",
      "args": [
        "~/ai-mvp-backend/scri`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.14/bin/python3.14",
      "args": [
        "~/ai-mvp-backend/scri`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list_proofs`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `[
  "test-id.md"
]`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[
  "test-id.md"
]`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `[
  "test-id.md"
]`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `[
  "test-id.md"
]`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.mount_server`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: Connection closed`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=None)",
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: 1 validation error for StdioServerParameters
args
  Input should be a valid list [type=list_type, input_value='wrong_type', input_type=str]
    For further information visit https://errors.pyda`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=None)",
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.search`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "features": [
    {
      "id": "test",
      "name": "test",
      "description": "test",
      "product": "test",
      "source": "test",
      "version": "test",
      "status": "development",
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "query must be str, got int"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.thanos_snap`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.traverse_mount`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Root mount 'test' not found",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.786298Z"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Root mount 'wrong_type' not found",
  "error_code": null,
  "timestamp": "2026-06-26T06:56:21.786419Z"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.unmount_server`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Unmounted test`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Unmounted wrong_type`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.update`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "No updates provided"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, status=None, description=None,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Feature '12345' not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, status=None, description=None,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.validate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Result must be 'passed' or 'failed'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Result must be 'passed' or 'failed'"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `federation` (7 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `health` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `join` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `leave` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `peers` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `route` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `sync` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `federation.health`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.join`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ JOINED FEDERATION
   Seed Peer: http://localhost:9999
   Total Peers: 1

💡 Federation engine is now active and syncing`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Failed to join: argument of type 'int' is not a container or iterable`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.leave`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.peers`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.route`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: test-id
📊 Profile: default

🏆 TARGET
   Brain: brain_test-brain
   Score: 0.630

⏱️ ROUTING TIME
   0.020ms

🔄 ALTERNATIVES
   1. pe`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: 12345
📊 Profile: 12345

🏆 TARGET
   Brain: brain_test-brain
   Score: 0.630

⏱️ ROUTING TIME
   0.028ms

🔄 ALTERNATIVES
   1. peer_h`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (1/`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (1/`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (1/`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (1/`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.sync`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `governance` (19 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `audit_report` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `auto_fix_loop` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `comply_apply` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `comply_list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `comply_report` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `curl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `delete_file` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `kyc_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_directory` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `lock` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `pip_install` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `set_mode` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `sovereign_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `trace_list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `trace_view` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `unlock` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `validate_strategic_plan` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `watch` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |

#### `governance.audit_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T06:56:23.579052+00:00\n  Jurisdiction: N`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T06:56:23.590928+00:00\n  Jurisdiction: N`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T06:56:23.595177+00:00\n  Jurisdiction: N`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T06:56:23.595516+00:00\n  Jurisdiction: N`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.auto_fix_loop`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "failure",
  "message": "Failed to fix after 3 attempts.",
  "last_output": "\n",
  "logs": [
    "[12:26:23] Starting Fixer Loop for test",
    "[12:26:23] Running verification: test",
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "failure",
  "message": "Failed to fix after 3 attempts.",
  "last_output": "Verification failed to run: [Errno 2] No such file or directory: 'wrong_type'",
  "logs": [
    "[12:26:23] S`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.comply_apply`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown jurisdiction: test",
  "available": "eu-dora, sg-mas-trm, us-soc2, global-default"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown jurisdiction: wrong_type",
  "available": "eu-dora, sg-mas-trm, us-soc2, global-default"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.comply_list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.comply_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "missing"
    },
    "hitl_policy": {
      "status": "no`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.curl`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"success": false, "error": "\ud83d\udea8 Egress Firewall Blocked: Domain not in ALLOWED_DOMAINS. URL: test"}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": [
    "met`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"success": false, "error": "\ud83d\udea8 Egress Firewall Blocked: Domain not in ALLOWED_DOMAINS. URL: wrong_type"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.delete_file`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ BLOCKED: Path 'test' resolves outside workspace root. Delete denied.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path, confirm=False)",
  "provided_params": `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ BLOCKED: Path 'wrong_type' resolves outside workspace root. Delete denied.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path, confirm=False)",
  "provided_params": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.kyc_review`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "review_id": "KYC-906C1BF7",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T06:56:23.661055+00:00",
  "completed_at": "2026-06-26T06:56:23.661075+00:00",
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "review_id": "KYC-785E3304",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T06:56:23.661552+00:00",
  "completed_at": "2026-06-26T06:56:23.661564+00:00",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown application: 12345",
  "available": [
    "APP-001",
    "APP-002",
    "APP-003"
  ]
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "review_id": "KYC-BC719D70",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T06:56:23.662249+00:00",
  "completed_at": "2026-06-26T06:56:23.662259+00:00",
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.list_directory`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ BLOCKED: Path 'test' resolves outside workspace root. Listing denied.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ BLOCKED: Path 'wrong_type' resolves outside workspace root. Listing denied.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.lock`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🔒 LOCKED: test (Immutable flag set)`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🔒 LOCKED: wrong_type (Immutable flag set)`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.pip_install`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"success": false, "error": "error: externally-managed-environment\n\n\u00d7 This environment is externally managed\n\u2570\u2500> To install Python packages system-wide, try brew install\n    xyz, wh`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"success": false, "error": "error: externally-managed-environment\n\n\u00d7 This environment is externally managed\n\u2570\u2500> To install Python packages system-wide, try brew install\n    xyz, wh`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.set_mode`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Invalid mode. Use 'red', 'blue', or 'reset'.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid mode. Use 'red', 'blue', or 'reset'.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.sovereign_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "sovereignty_score": 35,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.trace_list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "count": 15,
  "traces": [
    {
      "file": "KYC-0661F9EE.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0661F9EE",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "count": 15,
  "traces": [
    {
      "file": "KYC-0661F9EE.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0661F9EE",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "count": 0,
  "traces": [],
  "status": "no_dsor_directory"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "count": 15,
  "traces": [
    {
      "file": "KYC-0661F9EE.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0661F9EE",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.trace_view`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"error": "Trace not found: test"}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-0661F9EE",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T06:49:16.369874+00:00",
  "completed_at": "2026-06-26T0`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "Trace not found: 12345"}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-0661F9EE",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T06:49:16.369874+00:00",
  "completed_at": "2026-06-26T0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.unlock`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ UNLOCK DENIED: IPC token_id required for Tier 3 operation.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ UNLOCK DENIED: IPC token_id required for Tier 3 operation.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.validate_strategic_plan`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"valid": false, "mode": "strategic", "error": "PROTOCOL VIOLATION: Strategic mode PLAN must reference at least one Big Bang insight [BB##] from docs/reports/nucleus_bigbang_30d.md.", "hint": "Add a '`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"valid": false, "error": "mode must be str, got int"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.watch`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ BLOCKED: Path 'test' resolves outside workspace root. Watch denied.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ BLOCKED: Path 'wrong_type' resolves outside workspace root. Watch denied.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `orchestration.AGENTS_ROUTER` (20 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `apply_critique` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `critique_code` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `fix_code` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `get_alerts` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `handoff_task` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `ingest_tasks` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `ingestion_stats` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_dashboard_snapshots` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_pending_consents` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `orchestrate_swarm` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `read_memory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `register_session` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `respond_to_consent` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `rollback_ingestion` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `search_memory` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `session_briefing` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `set_alert_threshold` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `snapshot_dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `spawn_agent` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |

#### `orchestration.AGENTS_ROUTER.apply_critique`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"error": "Failed: Expecting value: line 1 column 1 (char 0)"}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'apply_critique': register.<locals>._h_apply_critique() missing 1 required positional argument: 'review_path'",
  "expected_params": "(review_path)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "Error: File not found: wrong_type"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'apply_critique': register.<locals>._h_apply_critique() missing 1 required positional argument: 'review_path'",
  "expected_params": "(review_path)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.critique_code`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"error": "Path 'test' resolves outside workspace root. Access denied."}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'critique_code': register.<locals>._h_critique_code() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, context='General R`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "Path 'wrong_type' resolves outside workspace root. Access denied."}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'critique_code': register.<locals>._h_critique_code() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, context='General R`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 12:26:24
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 12:26:24
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Dashboard error: 'int' object has no attribute 'lower'`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 12:26:24
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.fix_code`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"status": "error", "message": "Path 'test' resolves outside workspace root. Access denied."}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'fix_code': register.<locals>._h_fix_code() missing 2 required positional arguments: 'file_path' and 'issues_context'",
  "expected_params": "(file_path, issues`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"status": "error", "message": "Path 'wrong_type' resolves outside workspace root. Access denied."}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'fix_code': register.<locals>._h_fix_code() missing 2 required positional arguments: 'file_path' and 'issues_context'",
  "expected_params": "(file_path, issues`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.get_alerts`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ No active alerts - all systems healthy`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ No active alerts - all systems healthy`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ No active alerts - all systems healthy`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ No active alerts - all systems healthy`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.handoff_task`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Task handed off to shared queue. ID: task-2ef133f6`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() missing 1 required positional argument: 'task_description'",
  "expected_params": "(task_description, target`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Task handed off for session wrong_ty. ID: task-4f8e5f32`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() missing 1 required positional argument: 'task_description'",
  "expected_params": "(task_description, target`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.ingest_tasks`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Ingestion error: [Errno 21] Is a directory: 'test'`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_tasks': register.<locals>._h_ingest_tasks() missing 1 required positional argument: 'source'",
  "expected_params": "(source, source_type='auto', sessio`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Ingestion error: [Errno 21] Is a directory: 'wrong_type'`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_tasks': register.<locals>._h_ingest_tasks() missing 1 required positional argument: 'source'",
  "expected_params": "(source, source_type='auto', sessio`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.ingestion_stats`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `📊 **Ingestion Statistics**
========================================
   Total ingested: 0
   Total skipped: 0
   Total failed: 0
   Batches: 0
   Dedup cache: 0`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `📊 **Ingestion Statistics**
========================================
   Total ingested: 0
   Total skipped: 0
   Total failed: 0
   Batches: 0
   Dedup cache: 0`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `📊 **Ingestion Statistics**
========================================
   Total ingested: 0
   Total skipped: 0
   Total failed: 0
   Batches: 0
   Dedup cache: 0`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `📊 **Ingestion Statistics**
========================================
   Total ingested: 0
   Total skipped: 0
   Total failed: 0
   Batches: 0
   Dedup cache: 0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.list_dashboard_snapshots`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782456563_ed22f3: Snapshot 2026-06-26T06:49:23Z (2026-06-26T06:49:23Z)
   snap_1782456563_8cf09d: wrong_type (2026-06-26T06:49:2`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782456563_ed22f3: Snapshot 2026-06-26T06:49:23Z (2026-06-26T06:49:23Z)
   snap_1782456563_8cf09d: wrong_type (2026-06-26T06:49:2`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ List snapshots error: slice indices must be integers or None or have an __index__ method`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782456563_ed22f3: Snapshot 2026-06-26T06:49:23Z (2026-06-26T06:49:23Z)
   snap_1782456563_8cf09d: wrong_type (2026-06-26T06:49:2`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.list_pending_consents`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.orchestrate_swarm`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Swarm failed: 'NoneType' object has no attribute 'start_mission'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate_swarm': register.<locals>._h_orchestrate_swarm() missing 1 required positional argument: 'mission'",
  "expected_params": "(mission, agents=None)",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Swarm failed: 'NoneType' object has no attribute 'start_mission'"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate_swarm': register.<locals>._h_orchestrate_swarm() missing 1 required positional argument: 'mission'",
  "expected_params": "(mission, agents=None)",`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.read_memory`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid category. Allowed: ['context', 'patterns', 'learnings', 'decisions']"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'read_memory': register.<locals>.<lambda>() missing 1 required positional argument: 'category'",
  "expected_params": "(category)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid category. Allowed: ['context', 'patterns', 'learnings', 'decisions']"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'read_memory': register.<locals>.<lambda>() missing 1 required positional argument: 'category'",
  "expected_params": "(category)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.register_session`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Registered session test... focused on: test`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'register_session': register.<locals>._h_register_session() missing 2 required positional arguments: 'conversation_id' and 'focus_area'",
  "expected_params": "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Action 'register_session' failed: Invalid tier 'wrong_type'; must be one of ['haiku', 'opus', 'sonnet']",
  "module": "nucleus_agents"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'register_session': register.<locals>._h_register_session() missing 2 required positional arguments: 'conversation_id' and 'focus_area'",
  "expected_params": "`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.respond_to_consent`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"success": true, "agent_id": "test", "choice": "COLD", "message": "Consent recorded."}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'respond_to_consent': register.<locals>.<lambda>() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id, choice='cold')",
  "pro`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"success": true, "agent_id": "wrong_type", "choice": "12345", "message": "Consent recorded."}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'respond_to_consent': register.<locals>.<lambda>() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id, choice='cold')",
  "pro`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.rollback_ingestion`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Rollback failed: Batch test not found`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'rollback_ingestion': register.<locals>._h_rollback_ingestion() missing 1 required positional argument: 'batch_id'",
  "expected_params": "(batch_id, reason=Non`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Rollback failed: Batch wrong_type not found`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'rollback_ingestion': register.<locals>._h_rollback_ingestion() missing 1 required positional argument: 'batch_id'",
  "expected_params": "(batch_id, reason=Non`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.search_memory`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "query": "test",
  "count": 0,
  "results": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search_memory': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "query must be str, got int"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'search_memory': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.session_briefing`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (1)
- `test`: test

### 📌 Pending (27)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (1)
- `test`: test

### 📌 Pending (27)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (1)
- `test`: test

### 📌 Pending (27)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (1)
- `test`: test

### 📌 Pending (27)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.set_alert_threshold`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Threshold Set
   Metric: test
   Level: 5
   Value: test-value`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_alert_threshold': register.<locals>._h_set_alert_threshold() missing 3 required positional arguments: 'metric', 'level', and 'value'",
  "expected_params":`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Threshold Set
   Metric: wrong_type
   Level: not_a_number
   Value: wrong_type`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'set_alert_threshold': register.<locals>._h_set_alert_threshold() missing 3 required positional arguments: 'metric', 'level', and 'value'",
  "expected_params":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.snapshot_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782456987_916e89
   Name: Snapshot 2026-06-26T06:56:27Z
   Timestamp: 2026-06-26T06:56:27Z
   
💡 To compare: brain_compare_dashboards('snap_1782456987_916e89', 'other_s`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782456987_5064cc
   Name: Snapshot 2026-06-26T06:56:27Z
   Timestamp: 2026-06-26T06:56:27Z
   
💡 To compare: brain_compare_dashboards('snap_1782456987_5064cc', 'other_s`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782456987_ed861a
   Name: wrong_type
   Timestamp: 2026-06-26T06:56:27Z
   
💡 To compare: brain_compare_dashboards('snap_1782456987_ed861a', 'other_snapshot_id')`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782456987_14e82a
   Name: Snapshot 2026-06-26T06:56:27Z
   Timestamp: 2026-06-26T06:56:27Z
   
💡 To compare: brain_compare_dashboards('snap_1782456987_14e82a', 'other_s`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.AGENTS_ROUTER.spawn_agent`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `⚠️ HITL GATE: spawn_agent requires confirm=true.
Intent: test
Persona: default
Re-call with confirm=true to proceed. Agent spawning consumes compute resources.`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'spawn_agent': register.<locals>._h_spawn_agent() missing 1 required positional argument: 'intent'",
  "expected_params": "(intent, execute_now=True, persona=No`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `⚠️ HITL GATE: spawn_agent requires confirm=true.
Intent: wrong_type
Persona: wrong_type
Re-call with confirm=true to proceed. Agent spawning consumes compute resources.`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'spawn_agent': register.<locals>._h_spawn_agent() missing 1 required positional argument: 'intent'",
  "expected_params": "(intent, execute_now=True, persona=No`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "ha`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_agents",
  "available_actions": [
    "apply_critique",
    "critique_code",
    "dashboard",
    "fix_code",
    "get_alerts",
    "handoff_task",
    "i`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `orchestration.INFRA_ROUTER` (12 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `capture_metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `file_changes` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `gcloud_services` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `gcloud_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `growth_pulse` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_services` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `manage_strategy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `optimize_workflow` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `scan_marketing_log` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `status_report` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `synthesize_strategy` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `update_roadmap` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `orchestration.INFRA_ROUTER.capture_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "github": {
    "stars": 0,
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "source": "github_api",
    "fetched_at": "2026-06-26T06:56:27.211365+00:00"
  },
  "pypi": {
    "last_mon`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "github": {
    "stars": 0,
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "source": "github_api",
    "fetched_at": "2026-06-26T06:56:27.250783+00:00"
  },
  "pypi": {
    "last_mon`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "github": {
    "stars": 0,
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "source": "github_api",
    "fetched_at": "2026-06-26T06:56:27.271609+00:00"
  },
  "pypi": {
    "last_mon`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "github": {
    "stars": 0,
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "source": "github_api",
    "fetched_at": "2026-06-26T06:56:27.288400+00:00"
  },
  "pypi": {
    "last_mon`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.file_changes`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.gcloud_services`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "sequence item 7: expected str instance, int found"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.gcloud_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.growth_pulse`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-26T06:56:35.760664+00:00",
  "sections": {
    "brief": {
      "engram_count": 128,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-26T06:56:35.787161+00:00",
  "sections": {
    "brief": {
      "engram_count": 133,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-26T06:56:35.812644+00:00",
  "sections": {
    "brief": {
      "engram_count": 133,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-26T06:56:35.838215+00:00",
  "sections": {
    "brief": {
      "engram_count": 133,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.list_services`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.manage_strategy`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action: test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action: wrong_type"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.optimize_workflow`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.scan_marketing_log`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.status_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.synthesize_strategy`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.update_roadmap`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action: test. Use 'read', 'add', or 'complete'."
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() missing 1 required positional argument: 'action'",
  "expected_params": "(action, item=None)",
  "provid`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action: wrong_type. Use 'read', 'add', or 'complete'."
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() missing 1 required positional argument: 'action'",
  "expected_params": "(action, item=None)",
  "provid`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `orchestration.ORCH_ROUTER` (13 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add_loop` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `archive_stale` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `close_commitment` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `commitment_health` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `export` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_commitments` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `open_loops` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `patterns` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `pr_watch` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `satellite` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `scan_commitments` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `weekly_challenge` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `orchestration.ORCH_ROUTER.add_loop`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Loop created!

**ID:** `comm_20260626_122635_8`
**Type:** task
**Description:** test
**Priority:** 3
**Suggested:** schedule - Needs focused time`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add_loop': register.<locals>._h_add_loop() missing 1 required positional argument: 'description'",
  "expected_params": "(description, loop_type='task', priori`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Loop created!

**ID:** `comm_20260626_122635_9`
**Type:** 12345
**Description:** wrong_type
**Priority:** not_a_number
**Suggested:** schedule - Needs focused time`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add_loop': register.<locals>._h_add_loop() missing 1 required positional argument: 'description'",
  "expected_params": "(description, loop_type='task', priori`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.archive_stale`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Archive complete. Archived 0 stale items.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Archive complete. Archived 0 stale items.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Archive complete. Archived 0 stale items.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Archive complete. Archived 0 stale items.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.close_commitment`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: Commitment test not found`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'close_commitment': register.<locals>._h_close_commitment() missing 2 required positional arguments: 'commitment_id' and 'method'",
  "expected_params": "(commi`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: Commitment wrong_type not found`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'close_commitment': register.<locals>._h_close_commitment() missing 2 required positional arguments: 'commitment_id' and 'method'",
  "expected_params": "(commi`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.commitment_health`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 🎯 Commitment Health

**Open loops:** 8
- 🟢 Green: 8
- 🟡 Yellow: 0
- 🔴 Red: 0

**By type:** task: 4, 12345: 4

**Mental load:** 🟢 LOW
**Advice:** Looking good, maintain momentum

**Last scan:** 2026`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 🎯 Commitment Health

**Open loops:** 8
- 🟢 Green: 8
- 🟡 Yellow: 0
- 🔴 Red: 0

**By type:** task: 4, 12345: 4

**Mental load:** 🟢 LOW
**Advice:** Looking good, maintain momentum

**Last scan:** 2026`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 🎯 Commitment Health

**Open loops:** 8
- 🟢 Green: 8
- 🟡 Yellow: 0
- 🔴 Red: 0

**By type:** task: 4, 12345: 4

**Mental load:** 🟢 LOW
**Advice:** Looking good, maintain momentum

**Last scan:** 2026`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 🎯 Commitment Health

**Open loops:** 8
- 🟢 Green: 8
- 🟡 Yellow: 0
- 🔴 Red: 0

**By type:** task: 4, 12345: 4

**Mental load:** 🟢 LOW
**Advice:** Looking good, maintain momentum

**Last scan:** 2026`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.export`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Exported 112 files to brain_export_20260626_122635.zip`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Exported 112 files to brain_export_20260626_122636.zip`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Exported 112 files to brain_export_20260626_122636.zip`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Exported 112 files to brain_export_20260626_122637.zip`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.list_commitments`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `**Open Commitments (10 total)**

🟢 **test**
   Age: 0 days | Suggested: schedule
   Reason: Needs focused time
   ID: `comm_20260626_101319_0`

🟢 **wrong_type**
   Age: 0 days | Suggested: schedule
  `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `**Open Commitments (10 total)**

🟢 **test**
   Age: 0 days | Suggested: schedule
   Reason: Needs focused time
   ID: `comm_20260626_101319_0`

🟢 **wrong_type**
   Age: 0 days | Suggested: schedule
  `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ No open commitments!`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `**Open Commitments (10 total)**

🟢 **test**
   Age: 0 days | Suggested: schedule
   Reason: Needs focused time
   ID: `comm_20260626_101319_0`

🟢 **wrong_type**
   Age: 0 days | Suggested: schedule
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 📊 Coordination Metrics (Last 7 Days)

**🚀 Velocity:** 0 items closed
**⏱️ Speed:** 0 days avg

**📈 Closure Rates by Type:**
(No closed items yet)

**🧠 Current Load:**
- Total Open: 8
- Red Tier: 0
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📊 Coordination Metrics (Last 7 Days)

**🚀 Velocity:** 0 items closed
**⏱️ Speed:** 0 days avg

**📈 Closure Rates by Type:**
(No closed items yet)

**🧠 Current Load:**
- Total Open: 8
- Red Tier: 0
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 📊 Coordination Metrics (Last 7 Days)

**🚀 Velocity:** 0 items closed
**⏱️ Speed:** 0 days avg

**📈 Closure Rates by Type:**
(No closed items yet)

**🧠 Current Load:**
- Total Open: 8
- Red Tier: 0
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📊 Coordination Metrics (Last 7 Days)

**🚀 Velocity:** 0 items closed
**⏱️ Speed:** 0 days avg

**📈 Closure Rates by Type:**
(No closed items yet)

**🧠 Current Load:**
- Total Open: 8
- Red Tier: 0
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.open_loops`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: 'int' object has no attribute 'upper'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: 'int' object has no attribute 'upper'`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ No open loops! Guilt-free operation.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: 'int' object has no attribute 'upper'`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.patterns`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `No patterns learned yet.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `No patterns learned yet.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `No patterns learned yet.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `No patterns learned yet.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.pr_watch`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "stale_count": 0,
  "by_classification": {},
  "relays_emitted": [],
  "dry_run": false
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "stale_count": 0,
  "by_classification": {},
  "relays_emitted": [],
  "dry_run": false
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "stale_count": 0,
  "by_classification": {},
  "relays_emitted": [],
  "dry_run": "not_a_bool"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "stale_count": 0,
  "by_classification": {},
  "relays_emitted": [],
  "dry_run": false
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.satellite`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.scan_commitments`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Scan complete. Found 0 new items.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Scan complete. Found 0 new items.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Scan complete. Found 0 new items.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Scan complete. Found 0 new items.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.ORCH_ROUTER.weekly_challenge`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `No active challenge. Run `nucleus_orchestration(action='weekly_challenge', params={'action': 'list'})` to pick one!`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `No active challenge. Run `nucleus_orchestration(action='weekly_challenge', params={'action': 'list'})` to pick one!`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `No active challenge. Run `nucleus_orchestration(action='weekly_challenge', params={'action': 'list'})` to pick one!`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `No active challenge. Run `nucleus_orchestration(action='weekly_challenge', params={'action': 'list'})` to pick one!`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "exp`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_orchestration",
  "available_actions": [
    "add_loop",
    "archive_stale",
    "close_commitment",
    "commitment_health",
    "export",
    "list_com`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `orchestration.SLOTS_ROUTER` (11 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `autopilot_sprint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `autopilot_sprint_v2` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `force_assign` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `halt_sprint` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `mission_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `orchestrate` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `resume_sprint` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `slot_complete` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `slot_exhaust` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `start_mission` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `status_dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `orchestration.SLOTS_ROUTER.autopilot_sprint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sprint_id": "sprint_1782457000_01b7",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-26T12:26:40+0530"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sprint_id": "sprint_1782457000_3aae",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-26T12:26:40+0530"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "sprint_id": "sprint_1782457000_2631",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-26T12:26:40+0530"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sprint_id": "sprint_1782457000_aaed",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-26T12:26:40+0530"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.autopilot_sprint_v2`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🚀 Sprint Report: sprint_1782457000_2a4fb7
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 Sprint Report: sprint_1782457000_b232c2
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Sprint error: 'int' object has no attribute 'lower'`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 Sprint Report: sprint_1782457000_9662df
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.force_assign`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"error": "Slot test not found"}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id, `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{"error": "Slot wrong_type not found"}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id, `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.halt_sprint`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782457000_9662df
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782457000_9662df
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782457000_9662df
   Reason: 12345
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782457000_9662df
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.mission_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ No mission found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ No mission found`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ No mission found`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ No mission found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.orchestrate`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": "auto"
  },
  "slot": null,
  "protocol_status": {
    "compliant": true,
    "violations": [],
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": "auto"
  },
  "slot": null,
  "protocol_status": {
    "compliant": true,
    "violations": [],
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": 12345
  },
  "slot": null,
  "protocol_status": {
    "compliant": true,
    "violations": [],
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": "auto"
  },
  "slot": null,
  "protocol_status": {
    "compliant": true,
    "violations": [],
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.resume_sprint`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🚀 Sprint Report: wrong_type
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.slot_complete`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: Slot test not found

Next Task:
{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": "auto"
  },
  "slot": null,
  "protocol_status": {
    "c`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: Slot wrong_type not found

Next Task:
{
  "meta": {
    "timestamp": "2026-06-26T12:26:40+0530",
    "protocol_version": "2.0.0",
    "mode": "auto"
  },
  "slot": null,
  "protocol_status": {
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.slot_exhaust`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: Slot test not found`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': unsupported operand type(s) for +: 'float' and 'str'",
  "expected_params": "(slot_id, reset_hours=5)",
  "provided_params": [
    "slot_id",
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.start_mission`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Mission Started
   ID: mission_1782457000_9f86d0
   Name: test
   Goal: test
   Tasks: 4
   Budget: $10.00
   Time Limit: 4.0h
   
💡 Use brain_mission_status() to track progress`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Mission error: Unknown format code 'f' for object of type 'str'`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.status_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Dashboard error: '<' not supported between instances of 'str' and 'int'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Dashboard error: '<' not supported between instances of 'str' and 'int'`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Dashboard error: '<' not supported between instances of 'str' and 'int'`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Dashboard error: '<' not supported between instances of 'str' and 'int'`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `orchestration.TELEM_ROUTER` (15 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `agent_cost_dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `check_kill_switch` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `check_protocol` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `dispatch_metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `get_handoffs` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `get_llm_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `mark_high_impact` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `pause_notifications` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `rate_limit_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `record_feedback` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `record_interaction` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `request_handoff` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `resume_notifications` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `set_llm_tier` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `value_ratio` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `orchestration.TELEM_ROUTER.agent_cost_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "spawn_limiter": {
    "total_allowed": 0,
    "total_limited": 0,
    "tokens_available": 10.0,
    "capacity": 10.0,
    "fill_rate": 2.0,
    "spawns_by_persona": {}
  },
  "cost_summary": {
  `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "spawn_limiter": {
    "total_allowed": 0,
    "total_limited": 0,
    "tokens_available": 10.0,
    "capacity": 10.0,
    "fill_rate": 2.0,
    "spawns_by_persona": {}
  },
  "cost_summary": {
  `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "spawn_limiter": {
    "total_allowed": 0,
    "total_limited": 0,
    "tokens_available": 10.0,
    "capacity": 10.0,
    "fill_rate": 2.0,
    "spawns_by_persona": {}
  },
  "cost_summary": {
  `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "spawn_limiter": {
    "total_allowed": 0,
    "total_limited": 0,
    "tokens_available": 10.0,
    "capacity": 10.0,
    "fill_rate": 2.0,
    "spawns_by_persona": {}
  },
  "cost_summary": {
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.check_kill_switch`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 🛑 Kill Switch Status (MDR_010)

**Action:** continue
**Message:** N/A
**Days Inactive:** 0
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 🛑 Kill Switch Status (MDR_010)

**Action:** continue
**Message:** N/A
**Days Inactive:** 0
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 🛑 Kill Switch Status (MDR_010)

**Action:** continue
**Message:** N/A
**Days Inactive:** 0
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 🛑 Kill Switch Status (MDR_010)

**Action:** continue
**Message:** N/A
**Days Inactive:** 0
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.check_protocol`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "compliant": true,
  "warnings": [
    "Protocol definition not found - assuming compliant"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id)",
  "provided_para`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "compliant": true,
  "warnings": [
    "Protocol definition not found - assuming compliant"
  ]
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id)",
  "provided_para`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.dispatch_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "total_dispatches": 1008,
  "total_errors": 544,
  "error_rate": 0.5396825396825397,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_dispatches": 1009,
  "total_errors": 544,
  "error_rate": 0.5391476709613479,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "total_dispatches": 1010,
  "total_errors": 544,
  "error_rate": 0.5386138613861386,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_dispatches": 1011,
  "total_errors": 544,
  "error_rate": 0.5380811078140455,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.get_handoffs`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
    `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-1354",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "wrong_type",
      "priority": "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
    `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.get_llm_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.mark_high_impact`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Marked as high-impact closure. Value ratio updated.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Marked as high-impact closure. Value ratio updated.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Marked as high-impact closure. Value ratio updated.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Marked as high-impact closure. Value ratio updated.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.pause_notifications`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🛑 Notifications paused. Use brain_resume_notifications() to restart.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🛑 Notifications paused. Use brain_resume_notifications() to restart.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🛑 Notifications paused. Use brain_resume_notifications() to restart.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🛑 Notifications paused. Use brain_resume_notifications() to restart.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.rate_limit_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.record_feedback`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: '>=' not supported between instances of 'str' and 'int'`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() missing 2 required positional arguments: 'notification_type' and 'score'",
  "expected_params": "(notification_t`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: '>=' not supported between instances of 'str' and 'int'`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() missing 2 required positional arguments: 'notification_type' and 'score'",
  "expected_params": "(notification_t`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.record_interaction`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Interaction recorded`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Interaction recorded`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Interaction recorded`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Interaction recorded`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.request_handoff`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: test
PRIORITY: P3
CONTEXT: test
REQUEST: test
ARTIFACTS: None
━━━━━━━━━━━━━━━━━━
ID: handoff-1782457000-d689
Status: Pending - will appear in target agent's s`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() missing 3 required positional arguments: 'to_agent', 'context', and 'request'",
  "expected_params": "`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: wrong_type
PRIORITY: Pnot_a_number
CONTEXT: not_a_dict
REQUEST: wrong_type
ARTIFACTS: w, r, o, n, g, _, t, y, p, e
━━━━━━━━━━━━━━━━━━
ID: handoff-1782457000-7`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() missing 3 required positional arguments: 'to_agent', 'context', and 'request'",
  "expected_params": "`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.resume_notifications`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ Notifications resumed. Interaction recorded.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Notifications resumed. Interaction recorded.`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Notifications resumed. Interaction recorded.`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Notifications resumed. Interaction recorded.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.set_llm_tier`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Invalid tier 'test'. Valid tiers: premium, standard, economy, local_paid, local_free`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() missing 1 required positional argument: 'tier'",
  "expected_params": "(tier)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid tier 'wrong_type'. Valid tiers: premium, standard, economy, local_paid, local_free`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() missing 1 required positional argument: 'tier'",
  "expected_params": "(tier)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.TELEM_ROUTER.value_ratio`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_telemetry",
  "available_actions": [
    "agent_cost_dashboard",
    "check_kill_switch",
    "check_protocol",
    "dispatch_metrics",
    "get_handoffs"`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

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
  "error": "Action 'ack' failed: No bearer for role='wrong_type'. Expected per-role file at ~/.tb/relay/<role>_bearer (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucleus_relay"
}`

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
  "error": "Action 'inbox' failed: No bearer for role='wrong_type'. Expected per-role file at ~/.tb/relay/<role>_bearer (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucleus_relay"
}`

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
  "error": "Action 'post' failed: No bearer for role='wrong_type'. Expected per-role file at ~/.tb/relay/<role>_bearer (mode 600) or NUCLEUS_RELAY_BEARER env.",
  "module": "nucleus_relay"
}`

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

### Module: `sessions` (26 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `archive_resolved` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `check_recent` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `conversation_stats` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `current` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `detect_splits` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `emit_event` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `end` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `garbage_collect` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `get_state` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `handoff_summary` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `heartbeat` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `ingest_conversations` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_agents` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_conversations` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `propose_merges` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `read_events` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `register` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `resume` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `resume_checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `save` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `search_conversations` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `start` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `unregister` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `update_state` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |

#### `sessions.archive_resolved`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "files_moved": 0,
    "files_skipped": 0,
    "archive_path": "/tmp/test-brain/archive/resolved",
    "moved_files": [],
    "skipped_files": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "files_moved": 0,
    "files_skipped": 0,
    "archive_path": "/tmp/test-brain/archive/resolved",
    "moved_files": [],
    "skipped_files": `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "files_moved": 0,
    "files_skipped": 0,
    "archive_path": "/tmp/test-brain/archive/resolved",
    "moved_files": [],
    "skipped_files": `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "files_moved": 0,
    "files_skipped": 0,
    "archive_path": "/tmp/test-brain/archive/resolved",
    "moved_files": [],
    "skipped_files": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.check_recent`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.checkpoint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Checkpoint failed: Task test-id not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, step=None, progress_percent=None,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Checkpoint failed: Task 12345 not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, step=None, progress_percent=None,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.conversation_stats`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_sessions_raw": 721,
    "total_sessions_ingested": 721,
    "total_turns": 7535,
    "total_preferences": 81,
    "total_reasoning_chains": 0,
    "corpus_s`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_sessions_raw": 721,
    "total_sessions_ingested": 721,
    "total_turns": 7535,
    "total_preferences": 81,
    "total_reasoning_chains": 0,
    "corpus_s`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "total_sessions_raw": 721,
    "total_sessions_ingested": 721,
    "total_turns": 7535,
    "total_preferences": 81,
    "total_reasoning_chains": 0,
    "corpus_s`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_sessions_raw": 721,
    "total_sessions_ingested": 721,
    "total_turns": 7535,
    "total_preferences": 81,
    "total_reasoning_chains": 0,
    "corpus_s`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.current`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": true,
    "session_id": "not_a_dict_20260626_121940",
    "message": "Resumable session found."
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.detect_splits`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "splits": []
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "splits": []
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "splits": []
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "splits": []
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.emit_event`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "event_id": null
  },
  "error": null
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'emit_event': register.<locals>._h_emit() missing 3 required positional arguments: 'event_type', 'emitter', and 'data'",
  "expected_params": "(event_type, emit`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "event_id": null
  },
  "error": null
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'emit_event': register.<locals>._h_emit() missing 3 required positional arguments: 'event_type', 'emitter', and 'data'",
  "expected_params": "(event_type, emit`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.end`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "test",
    "activity": {
      "total_events": 1090,
      "tasks_completed": 30,
      "tasks_claimed": 0,
      "tasks_created":`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "Session ended (neutral): 30 tasks done, 19 tasks created, 1097 total events",
    "activity": {
      "total_events": 1097,
      `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "summary must be str, got int"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "Session ended (neutral): 30 tasks done, 19 tasks created, 1103 total events",
    "activity": {
      "total_events": 1103,
      `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.garbage_collect`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "archived": 0,
    "kept": 0,
    "message": "No tasks.json found"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "archived": 0,
    "kept": 0,
    "message": "No tasks.json found"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "archived": 0,
    "kept": 0,
    "message": "No tasks.json found"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "archived": 0,
    "kept": 0,
    "message": "No tasks.json found"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.get_state`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.handoff_summary`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Summary generation failed: Task test-id not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_summary': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'summary'",
  "expected_params": "(task_id, summary, key_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Summary generation failed: Task 12345 not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_summary': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'summary'",
  "expected_params": "(task_id, summary, key_`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.heartbeat`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "session test not registered"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat': register.<locals>._h_heartbeat() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params": [`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "session wrong_type not registered"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat': register.<locals>._h_heartbeat() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params": [`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.ingest_conversations`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions_processed": 0,
    "turns_created": 0,
    "preferences_found": 0,
    "chains_extracted": 0,
    "errors": [],
    "duration_ms": 239
  },
  "error": nu`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions_processed": 0,
    "turns_created": 0,
    "preferences_found": 0,
    "chains_extracted": 0,
    "errors": [],
    "duration_ms": 183
  },
  "error": nu`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_conversations': '>=' not supported between instances of 'int' and 'str'",
  "expected_params": "(mode='incremental', session_id='', limit=0, dry_run=Fal`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions_processed": 0,
    "turns_created": 0,
    "preferences_found": 0,
    "chains_extracted": 0,
    "errors": [],
    "duration_ms": 193
  },
  "error": nu`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "test_20260626_121940",
        "context": "test",
        "created_at": "2026-06-26T12:19:40+0530"
      },
      {
        "i`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "test_20260626_121940",
        "context": "test",
        "created_at": "2026-06-26T12:19:40+0530"
      },
      {
        "i`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "test_20260626_121940",
        "context": "test",
        "created_at": "2026-06-26T12:19:40+0530"
      },
      {
        "i`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "test_20260626_121940",
        "context": "test",
        "created_at": "2026-06-26T12:19:40+0530"
      },
      {
        "i`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list_agents`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "agents": []
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "agents": []
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "agents": []
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "agents": []
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.list_conversations`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "conversations": [
      {
        "session_id": "2d4213a6-d67",
        "full_id": "2d4213a6-d677-4d46-9265-bcc8b6560217",
        "mtime": "2026-06-22T15:30:12.9`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "conversations": [
      {
        "session_id": "2d4213a6-d67",
        "full_id": "2d4213a6-d677-4d46-9265-bcc8b6560217",
        "mtime": "2026-06-22T15:30:12.9`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "conversations": [],
    "error": "limit must be number, got str"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "conversations": [
      {
        "session_id": "2d4213a6-d67",
        "full_id": "2d4213a6-d677-4d46-9265-bcc8b6560217",
        "mtime": "2026-06-22T15:30:12.9`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.propose_merges`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-26  \n> **Status:** Awaiting human rev`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-26  \n> **Status:** Awaiting human rev`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-26  \n> **Status:** Awaiting human rev`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-26  \n> **Status:** Awaiting human rev`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.read_events`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "events": []
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "events": []
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "events": []
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "events": []
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.register`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "session_id": "test",
    "agent": "test",
    "role": "test",
    "worktree_path": null,
    "pid": 23366,
    "registered_at": "2026-06-26T06:56:41.982433Z",
   `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'register': register.<locals>._h_register() missing 4 required positional arguments: 'session_id', 'agent', 'role', and 'provider'",
  "expected_params": "(sess`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "heartbeat_interval_s must be a number, got str"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'register': register.<locals>._h_register() missing 4 required positional arguments: 'session_id', 'agent', 'role', and 'provider'",
  "expected_params": "(sess`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.resume`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "No active session found"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "No active session found"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "Session 'wrong_type' not found"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "No active session found"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.resume_checkpoint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Resume failed: Task test-id not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'resume_checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id)",
  "provided_params": []
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "\u274c Resume failed: Task 12345 not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'resume_checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id)",
  "provided_params": []
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.save`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "session_id": "test_20260626_122641",
    "context": "test",
    "message": "Session saved. Resume later with: nucleus sessions resume"
  },
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'save': register.<locals>._h_save() missing 1 required positional argument: 'context'",
  "expected_params": "(context, active_task=None, pending_decisions=None`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "session_id": "not_a_dict_20260626_122641",
    "context": "not_a_dict",
    "message": "Session saved. Resume later with: nucleus sessions re`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'save': register.<locals>._h_save() missing 1 required positional argument: 'context'",
  "expected_params": "(context, active_task=None, pending_decisions=None`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.search_conversations`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "results": [],
    "total_matches": 0,
    "query": "test"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "results": [],
    "total_matches": 0,
    "query": ""
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "results": [],
    "total_matches": 0,
    "error": "query must be str, got int"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "results": [],
    "total_matches": 0,
    "query": ""
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.start`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.unregister`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "session_id": "test",
    "removed": true
  },
  "error": null
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unregister': register.<locals>._h_unregister() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params":`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "session_id": "wrong_type",
    "removed": false
  },
  "error": null
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'unregister': register.<locals>._h_unregister() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sessions.update_state`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": null
  },
  "error": null
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update_state': register.<locals>.<lambda>() missing 1 required positional argument: 'updates'",
  "expected_params": "(updates)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "message": null
  },
  "error": null
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update_state': register.<locals>.<lambda>() missing 1 required positional argument: 'updates'",
  "expected_params": "(updates)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "curren`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sessions",
  "available_actions": [
    "archive_resolved",
    "check_recent",
    "checkpoint",
    "conversation_stats",
    "current",
    "detect_spl`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `sync` (63 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add_channel` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `audit_pair` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `check_deploy` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `complete_deploy` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `evaluate_triggers` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `get_triggers` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `identify_agent` | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `list_artifacts` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_channels` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `marketplace_alert` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_audit` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `marketplace_can_call` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_compare` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `marketplace_diff` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_export` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `marketplace_federation_proxy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_federation_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_federation_sync` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_history` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_promote` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_quarantine` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_recommend` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `marketplace_search` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `marketplace_subscribe` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_subscriptions` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `marketplace_trends` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `marketplace_unsubscribe` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_whoami` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `notify` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `pair_fire` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pair_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pair_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pair_stop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `read_artifact` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `relay_ack` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_classify_skip` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_clear` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_event_stats` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `relay_inbox` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_listen` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `relay_log_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_poll_start` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `relay_poll_status` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `relay_poll_stop` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `relay_post` | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `relay_skip_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `relay_wait` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `saturation_baselines` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `saturation_check` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `shared_list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `shared_read` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `shared_write` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `smoke_test` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start_deploy_poll` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `sync_auto` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_now` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_resolve` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `sync_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `test_channel` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `trigger_agent` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `write_artifact` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |

#### `sync.add_channel`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown channel type: file"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add_channel': register.<locals>.<lambda>() missing 1 required positional argument: 'channel_type'",
  "expected_params": "(channel_type, **kwargs)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown channel type: wrong_type"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add_channel': register.<locals>.<lambda>() missing 1 required positional argument: 'channel_type'",
  "expected_params": "(channel_type, **kwargs)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.audit_pair`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": true,
  "data": {
    "window_hours": 24.0,
    "events_in_window": 0,
    "malformed_lines_skipped": 30,
    "pair_rollup": [],
    "utilization": []
  }
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "ok": true,
  "data": {
    "window_hours": 24.0,
    "events_in_window": 0,
    "malformed_lines_skipped": 30,
    "pair_rollup": [],
    "utilization": []
  }
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Action 'audit_pair' failed: could not convert string to float: 'wrong_type'",
  "module": "nucleus_sync"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "ok": true,
  "data": {
    "window_hours": 24.0,
    "events_in_window": 0,
    "malformed_lines_skipped": 30,
    "pair_rollup": [],
    "utilization": []
  }
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.check_deploy`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "poll_id": "poll-1782456762-068bacd4",
  "service_id": "test",
  "commit_sha": null,
  "status": "polling",
  "elapsed_minutes": 4.0,
  "message": "Polling for 4.0 minutes. Use mcp_render_list_dep`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'check_deploy': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id)",
  "provided_params": []`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "poll_id": "poll-1782456762-47c13bcd",
  "service_id": "wrong_type",
  "commit_sha": "wrong_type",
  "status": "polling",
  "elapsed_minutes": 4.0,
  "message": "Polling for 4.0 minutes. Use mcp_r`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'check_deploy': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id)",
  "provided_params": []`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.complete_deploy`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "deploy_success",
  "message": "\u2705 Deploy complete! URL: None",
  "deploy_url": null,
  "smoke_test": null,
  "service_id": "test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'complete_deploy': register.<locals>.<lambda>() missing 2 required positional arguments: 'service_id' and 'success'",
  "expected_params": "(service_id, success`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "deploy_success_smoke_failed",
  "message": "\u26a0\ufe0f Deploy succeeded but smoke test failed: None",
  "deploy_url": "wrong_type",
  "smoke_test": {
    "passed": false,
    "error":`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'complete_deploy': register.<locals>.<lambda>() missing 2 required positional arguments: 'service_id' and 'success'",
  "expected_params": "(service_id, success`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.evaluate_triggers`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `[]`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'evaluate_triggers': register.<locals>.<lambda>() missing 2 required positional arguments: 'event_type' and 'emitter'",
  "expected_params": "(event_type, emitt`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `[]`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'evaluate_triggers': register.<locals>.<lambda>() missing 2 required positional arguments: 'event_type' and 'emitter'",
  "expected_params": "(event_type, emitt`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.get_triggers`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `[]`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[]`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `[]`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `[]`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.identify_agent`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "identify_agent requires either {agent_id, environment} or {role, provider, session_id} per ADR-0005 \u00a7D1."
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "identify_agent requires either {agent_id, environment} or {role, provider, session_id} per ADR-0005 \u00a7D1."
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "agent_id": "wrong_type",
  "environment": 12345,
  "role": 12345,
  "provider": "wrong_type",
  "session_id": "wrong_type",
  "registered_at": "2026-06-26T12:26:42.191612",
  "pid": 23366,
  "sto`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "identify_agent requires either {agent_id, environment} or {role, provider, session_id} per ADR-0005 \u00a7D1."
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.list_artifacts`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `[
  "test"
]`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[
  "test"
]`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `[]`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `[
  "test"
]`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.list_channels`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "channels": []
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "channels": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "channels": []
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "channels": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_alert`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "subscribed": true,
  "subscriber": "test",
  "target": "test",
  "event_types": [
    "tier_changed",
    "quarantined"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_alert': register.<locals>.<lambda>() missing 2 required positional arguments: 'subscriber' and 'target'",
  "expected_params": "(subscriber, target`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "subscribed": true,
  "subscriber": "wrong_type",
  "target": "wrong_type",
  "event_types": "wrong_type"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_alert': register.<locals>.<lambda>() missing 2 required positional arguments: 'subscriber' and 'target'",
  "expected_params": "(subscriber, target`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_audit`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "actions": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "actions": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "actions": [],
  "total": 0,
  "offset": "not_a_number",
  "limit": "not_a_number"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "actions": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_can_call`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "allowed": false,
  "caller": "test",
  "target": "test",
  "reason": "unregistered_caller"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_can_call': register.<locals>.<lambda>() missing 2 required positional arguments: 'caller' and 'target'",
  "expected_params": "(caller, target)",
 `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "allowed": false,
  "caller": "wrong_type",
  "target": "wrong_type",
  "reason": "unregistered_caller"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_can_call': register.<locals>.<lambda>() missing 2 required positional arguments: 'caller' and 'target'",
  "expected_params": "(caller, target)",
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_compare`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "address 'test' not registered"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_compare': register.<locals>.<lambda>() missing 2 required positional arguments: 'a' and 'b'",
  "expected_params": "(a, b)",
  "provided_params": [`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "address 'wrong_type' not registered"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_compare': register.<locals>.<lambda>() missing 2 required positional arguments: 'a' and 'b'",
  "expected_params": "(a, b)",
  "provided_params": [`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "total_registered": 0,
  "by_tier": {
    "unverified": 0,
    "active": 0,
    "trusted": 0,
    "verified": 0
  },
  "inactive_count": 0,
  "top_10_by_reputation": [],
  "tier_flips_recorded": 0`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_registered": 0,
  "by_tier": {
    "unverified": 0,
    "active": 0,
    "trusted": 0,
    "verified": 0
  },
  "inactive_count": 0,
  "top_10_by_reputation": [],
  "tier_flips_recorded": 0`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "total_registered": 0,
  "by_tier": {
    "unverified": 0,
    "active": 0,
    "trusted": 0,
    "verified": 0
  },
  "inactive_count": 0,
  "top_10_by_reputation": [],
  "tier_flips_recorded": 0`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_registered": 0,
  "by_tier": {
    "unverified": 0,
    "active": 0,
    "trusted": 0,
    "verified": 0
  },
  "inactive_count": 0,
  "top_10_by_reputation": [],
  "tier_flips_recorded": 0`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_diff`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "snapshot_a parse error: Expecting value: line 1 column 1 (char 0)"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_diff': register.<locals>.<lambda>() missing 2 required positional arguments: 'snapshot_a' and 'snapshot_b'",
  "expected_params": "(snapshot_a, sna`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "snapshot_a parse error: Expecting value: line 1 column 1 (char 0)"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_diff': register.<locals>.<lambda>() missing 2 required positional arguments: 'snapshot_a' and 'snapshot_b'",
  "expected_params": "(snapshot_a, sna`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_export`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "snapshot": [],
  "total": 0
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "snapshot": [],
  "total": 0
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "snapshot": [],
  "total": 0
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "snapshot": [],
  "total": 0
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_federation_proxy`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": "Unknown peer 'test'. Known peers: ['peer_http://localhost_9999']"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_proxy': register.<locals>.<lambda>() missing 2 required positional arguments: 'target_brain' and 'action'",
  "expected_params": "(targe`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": "Unknown peer 'wrong_type'. Known peers: ['peer_http://localhost_9999']"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_proxy': register.<locals>.<lambda>() missing 2 required positional arguments: 'target_brain' and 'action'",
  "expected_params": "(targe`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_federation_register`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": "Invalid address format: test. Must match '^[a-z0-9\\-]+@nucleus$'."
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_register': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, capabilities`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": "Invalid address format: wrong_type. Must match '^[a-z0-9\\-]+@nucleus$'."
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_register': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, capabilities`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_federation_sync`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": "Federation engine not running. Use federation join first."
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "ok": false,
  "error": "Federation engine not running. Use federation join first."
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": "Federation engine not running. Use federation join first."
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "ok": false,
  "error": "Federation engine not running. Use federation join first."
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_history`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "address 'test' not registered"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_history': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, limit=20)",
  "provided_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "address 'wrong_type' not registered"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_history': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, limit=20)",
  "provided_`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_promote`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "reason": "caller_not_verified",
  "detail": "'admin' must be VERIFIED tier to promote"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_promote': register.<locals>.<lambda>() missing 2 required positional arguments: 'address' and 'new_tier'",
  "expected_params": "(address, new_tier`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "reason": "caller_not_verified",
  "detail": "'12345' must be VERIFIED tier to promote"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_promote': register.<locals>.<lambda>() missing 2 required positional arguments: 'address' and 'new_tier'",
  "expected_params": "(address, new_tier`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_quarantine`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "reason": "caller_not_verified",
  "detail": "'admin' must be VERIFIED tier to quarantine"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_quarantine': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, caller='admin', reaso`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "reason": "caller_not_verified",
  "detail": "'12345' must be VERIFIED tier to quarantine"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_quarantine': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, caller='admin', reaso`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_recommend`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "recommendations": [],
  "task": "test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': register.<locals>.<lambda>() missing 1 required positional argument: 'task'",
  "expected_params": "(task, top_k=5)",
  "provided_param`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': slice indices must be integers or None or have an __index__ method",
  "expected_params": "(task, top_k=5)",
  "provided_params": [
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': register.<locals>.<lambda>() missing 1 required positional argument: 'task'",
  "expected_params": "(task, top_k=5)",
  "provided_param`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_search`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "cards": [],
  "count": 0
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "cards": [],
  "count": 0
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown min_tier 'wrong_type'. Valid: Unverified, Active, Trusted, Verified"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "cards": [],
  "count": 0
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_subscribe`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "subscribed": true,
  "subscriber": "test",
  "target": "*",
  "event_types": [
    "tier_changed",
    "quarantined"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*', even`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "subscribed": true,
  "subscriber": "wrong_type",
  "target": 12345,
  "event_types": [
    "tier_changed",
    "quarantined"
  ]
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*', even`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_subscriptions`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "subscriptions": [
    {
      "subscriber": "test",
      "target": "*",
      "event_types": [
        "tier_changed",
        "quarantined"
      ],
      "created_at": "2026-06-26T06:56:42.202`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "subscriptions": [
    {
      "subscriber": "test",
      "target": "*",
      "event_types": [
        "tier_changed",
        "quarantined"
      ],
      "created_at": "2026-06-26T06:56:42.202`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "subscriptions": [
    {
      "subscriber": "wrong_type",
      "target": 12345,
      "event_types": [
        "tier_changed",
        "quarantined"
      ],
      "created_at": "2026-06-26T06:5`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "subscriptions": [
    {
      "subscriber": "test",
      "target": "*",
      "event_types": [
        "tier_changed",
        "quarantined"
      ],
      "created_at": "2026-06-26T06:56:42.202`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_trends`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "trend": "insufficient_data",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": []
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "trend": "insufficient_data",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_trends': unsupported type for timedelta days component: str",
  "expected_params": "(days=30, brain_path=None)",
  "provided_params": [
    "days",`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "trend": "insufficient_data",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_unsubscribe`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "removed": 1,
  "subscriber": "test",
  "target": "*"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_unsubscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*')",
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "removed": 1,
  "subscriber": "wrong_type",
  "target": 12345
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_unsubscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*')",
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.marketplace_whoami`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "registered": false,
  "reason": "CC_SESSION_ROLE not set and no role param"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "registered": false,
  "reason": "CC_SESSION_ROLE not set and no role param"
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "registered": false,
  "address": "wrong-type@nucleus"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "registered": false,
  "reason": "CC_SESSION_ROLE not set and no role param"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.notify`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sent": {},
  "channels_reached": 0
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'notify': register.<locals>.<lambda>() missing 2 required positional arguments: 'title' and 'message'",
  "expected_params": "(title, message, level='info')",
 `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "sent": {},
  "channels_reached": 0
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'notify': register.<locals>.<lambda>() missing 2 required positional arguments: 'title' and 'message'",
  "expected_params": "(title, message, level='info')",
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.pair_fire`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'test'"
  }
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pair_fire': register.<locals>.<lambda>() missing 2 required positional arguments: 'lane' and 'brief'",
  "expected_params": "(lane, brief, model='sonnet', subj`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'wrong_type'"
  }
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'pair_fire': register.<locals>.<lambda>() missing 2 required positional arguments: 'lane' and 'brief'",
  "expected_params": "(lane, brief, model='sonnet', subj`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.pair_register`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'test'"
  }
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pair_register': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane, charter_path=None)",
  "provided_par`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'wrong_type'"
  }
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'pair_register': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane, charter_path=None)",
  "provided_par`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.pair_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": true,
  "data": {
    "pairs": [
      {
        "lane": "peer",
        "running": false,
        "pid": null,
        "session_id": null,
        "queue_depth": 0,
        "latest_heartbea`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "ok": true,
  "data": {
    "pairs": [
      {
        "lane": "peer",
        "running": false,
        "pid": null,
        "session_id": null,
        "queue_depth": 0,
        "latest_heartbea`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "unknown lane 'wrong_type'"
  }
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "ok": true,
  "data": {
    "pairs": [
      {
        "lane": "peer",
        "running": false,
        "pid": null,
        "session_id": null,
        "queue_depth": 0,
        "latest_heartbea`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.pair_stop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'test'"
  }
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pair_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "ok": false,
  "error": {
    "code": "INVALID_LANE",
    "message": "v0.1 supports lane=peer|main only; got 'wrong_type'"
  }
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'pair_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.read_artifact`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `test`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'read_artifact': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: File not found: wrong_type`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'read_artifact': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_ack`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "acknowledged": false,
  "message_id": "test",
  "error": "Message not found in claude_code_main inbox"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_ack': register.<locals>.<lambda>() missing 1 required positional argument: 'message_id'",
  "expected_params": "(message_id, recipient=None, session_id=N`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "acknowledged": false,
  "message_id": "wrong_type",
  "error": "Message not found in wrong_type inbox"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_ack': register.<locals>.<lambda>() missing 1 required positional argument: 'message_id'",
  "expected_params": "(message_id, recipient=None, session_id=N`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_classify_skip`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "classified": false,
  "error": "classification must be one of {'rightly_skipped', 'should_have_fired'}"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_classify_skip': register.<locals>.<lambda>() missing 3 required positional arguments: 'ts', 'subject', and 'classification'",
  "expected_params": "(ts, `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "classified": false,
  "error": "classification must be one of {'rightly_skipped', 'should_have_fired'}"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_classify_skip': register.<locals>.<lambda>() missing 3 required positional arguments: 'ts', 'subject', and 'classification'",
  "expected_params": "(ts, `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_clear`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "deleted": 0,
  "errors": 0,
  "older_than_hours": 168
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "deleted": 0,
  "errors": 0,
  "older_than_hours": 168
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_clear': unsupported operand type(s) for -: 'float' and 'str'",
  "expected_params": "(recipient=None, older_than_hours=168)",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "deleted": 0,
  "errors": 0,
  "older_than_hours": 168
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_event_stats`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "total_fires": 0,
  "total_skips": 0,
  "total_attempts": 0,
  "override_count": 0,
  "override_rate": 0.0,
  "skip_rate": 0.0
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_fires": 0,
  "total_skips": 0,
  "total_attempts": 0,
  "override_count": 0,
  "override_rate": 0.0,
  "skip_rate": 0.0
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "total_fires": 0,
  "total_skips": 0,
  "total_attempts": 0,
  "override_count": 0,
  "override_rate": 0.0,
  "skip_rate": 0.0
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_fires": 0,
  "total_skips": 0,
  "total_attempts": 0,
  "override_count": 0,
  "override_rate": 0.0,
  "skip_rate": 0.0
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_inbox`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "recipient": "claude_code_main",
  "messages": [],
  "count": 0,
  "unread_only": true,
  "session_id": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "recipient": "claude_code_main",
  "messages": [],
  "count": 0,
  "unread_only": true,
  "session_id": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_inbox': '>=' not supported between instances of 'int' and 'str'",
  "expected_params": "(unread_only=True, limit=20, recipient=None, session_id=None)",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "recipient": "claude_code_main",
  "messages": [],
  "count": 0,
  "unread_only": true,
  "session_id": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_listen`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "found": false,
  "call_again": true,
  "waited_s": 59,
  "recipient": "test",
  "known_ids": [],
  "next_attempt": 2,
  "next_poll_s": 10,
  "hint": "No new relay in 60s. Call relay_listen again `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_listen': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, window_s=60, poll_s=5, in_r`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "found": false,
  "call_again": true,
  "waited_s": 59,
  "recipient": "wrong_type",
  "known_ids": [
    "t",
    "o",
    "n",
    "p",
    "g",
    "w",
    "e",
    "y",
    "_",
    "r"
  ],
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_listen': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, window_s=60, poll_s=5, in_r`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_log_event`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "logged": false,
  "error": "event must be one of {'fire', 'skip'}"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_log_event': register.<locals>.<lambda>() missing 3 required positional arguments: 'event', 'side', and 'subject'",
  "expected_params": "(event, side, su`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "logged": false,
  "error": "event must be one of {'fire', 'skip'}"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_log_event': register.<locals>.<lambda>() missing 3 required positional arguments: 'event', 'side', and 'subject'",
  "expected_params": "(event, side, su`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_poll_start`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "started",
  "recipient": "test",
  "interval_s": 10,
  "session_id": null,
  "signal_file": "/tmp/test-brain/relay/test/POLL_SIGNAL.json"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_start': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, interval_s=10, session_`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "started",
  "recipient": "wrong_type",
  "interval_s": 10,
  "session_id": "wrong_type",
  "signal_file": "/tmp/test-brain/relay/wrong_type/POLL_SIGNAL.json"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_start': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, interval_s=10, session_`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_poll_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "running": true,
  "recipient": "test",
  "interval_s": 10,
  "checked_at": "2026-06-26T06:58:42.816472Z",
  "pending": [],
  "pending_count": 0
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_status': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params":`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "running": true,
  "recipient": "wrong_type",
  "interval_s": 10,
  "checked_at": "2026-06-26T06:58:42.818358Z",
  "pending": [
    {
      "relay_id": "relay_20260626_044516_4a270bee",
      "sub`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_status': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_poll_stop`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "stopped",
  "recipient": "test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params": [`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "stopped",
  "recipient": "wrong_type"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params": [`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_post`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Action 'relay_post' failed: relay_post: sender is required. Pass sender= explicitly (e.g. 'coordinator', 'worker', 'cowork', 'primary', 'secondary'). Set NUCLEUS_RELAY_INFER_SENDER=1 to `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_post': register.<locals>.<lambda>() missing 3 required positional arguments: 'to', 'subject', and 'body'",
  "expected_params": "(to, subject, body, prio`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "sent": true,
  "message_id": "relay_20260626_065842_7eb2cc04",
  "from": "wrong_type",
  "to": "wrong_type",
  "subject": "wrong_type",
  "priority": 12345,
  "path": "relay/wrong_type/20260626_0`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_post': register.<locals>.<lambda>() missing 3 required positional arguments: 'to', 'subject', and 'body'",
  "expected_params": "(to, subject, body, prio`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_skip_review`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "total_skips": 0,
  "total_classified": 0,
  "unclassified_count": 0,
  "unclassified": []
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_skips": 0,
  "total_classified": 0,
  "unclassified_count": 0,
  "unclassified": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_skip_review': slice indices must be integers or None or have an __index__ method",
  "expected_params": "(limit=20)",
  "provided_params": [
    "limit"
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_skips": 0,
  "total_classified": 0,
  "unclassified_count": 0,
  "unclassified": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "current_session_type": "claude_code_main",
  "mailboxes": {
    "claude_code": {
      "total": 0,
      "unread": 0,
      "latest_message_at": null
    },
    "claude_code_main": {
      "total`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "current_session_type": "claude_code_main",
  "mailboxes": {
    "claude_code": {
      "total": 0,
      "unread": 0,
      "latest_message_at": null
    },
    "claude_code_main": {
      "total`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "current_session_type": "claude_code_main",
  "mailboxes": {
    "claude_code": {
      "total": 0,
      "unread": 0,
      "latest_message_at": null
    },
    "claude_code_main": {
      "total`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "current_session_type": "claude_code_main",
  "mailboxes": {
    "claude_code": {
      "total": 0,
      "unread": 0,
      "latest_message_at": null
    },
    "claude_code_main": {
      "total`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.relay_wait`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "found": false,
  "timed_out": true,
  "waited_s": 59
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_wait': register.<locals>.<lambda>() missing 2 required positional arguments: 'in_reply_to' and 'recipient'",
  "expected_params": "(in_reply_to, recipien`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "found": true,
  "relay_id": "relay_20260626_044516_4a270bee",
  "subject": "wrong_type",
  "from": "wrong_type",
  "waited_s": 0
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'relay_wait': register.<locals>.<lambda>() missing 2 required positional arguments: 'in_reply_to' and 'recipient'",
  "expected_params": "(in_reply_to, recipien`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.saturation_baselines`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "surface": "main",
  "window_size": 100,
  "turn_count": 0,
  "tokens_baseline_median": null,
  "tokens_p95": null,
  "latency_baseline_median_s": null,
  "latency_p95_s": null,
  "data_present": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "surface": "main",
  "window_size": 100,
  "turn_count": 0,
  "tokens_baseline_median": null,
  "tokens_p95": null,
  "latency_baseline_median_s": null,
  "latency_p95_s": null,
  "data_present": `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "surface": 12345,
  "window_size": "not_a_number",
  "turn_count": 0,
  "tokens_baseline_median": null,
  "tokens_p95": null,
  "latency_baseline_median_s": null,
  "latency_p95_s": null,
  "data_`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "surface": "main",
  "window_size": 100,
  "turn_count": 0,
  "tokens_baseline_median": null,
  "tokens_p95": null,
  "latency_baseline_median_s": null,
  "latency_p95_s": null,
  "data_present": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.saturation_check`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "surface": "main",
  "saturated": false,
  "threshold_factor": 2.0,
  "baselines": {
    "surface": "main",
    "window_size": 100,
    "turn_count": 0,
    "tokens_baseline_median": null,
    "to`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "surface": "main",
  "saturated": false,
  "threshold_factor": 2.0,
  "baselines": {
    "surface": "main",
    "window_size": 100,
    "turn_count": 0,
    "tokens_baseline_median": null,
    "to`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "surface": 12345,
  "saturated": false,
  "threshold_factor": "wrong_type",
  "baselines": {
    "surface": 12345,
    "window_size": "not_a_number",
    "turn_count": 0,
    "tokens_baseline_medi`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "surface": "main",
  "saturated": false,
  "threshold_factor": 2.0,
  "baselines": {
    "surface": "main",
    "window_size": 100,
    "turn_count": 0,
    "tokens_baseline_median": null,
    "to`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.shared_list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "keys": [
    {
      "key": "test-key",
      "agent_id": "test",
      "updated_at": "2026-06-26T06:52:42.039324Z"
    },
    {
      "key": "wrong_type",
      "agent_id": 12345,
      "updated`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "keys": [
    {
      "key": "test-key",
      "agent_id": "test",
      "updated_at": "2026-06-26T06:52:42.039324Z"
    },
    {
      "key": "wrong_type",
      "agent_id": 12345,
      "updated`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "keys": [
    {
      "key": "test-key",
      "agent_id": "test",
      "updated_at": "2026-06-26T06:52:42.039324Z"
    },
    {
      "key": "wrong_type",
      "agent_id": 12345,
      "updated`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "keys": [
    {
      "key": "test-key",
      "agent_id": "test",
      "updated_at": "2026-06-26T06:52:42.039324Z"
    },
    {
      "key": "wrong_type",
      "agent_id": 12345,
      "updated`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.shared_read`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "found": true,
  "key": "test-key",
  "value": "test-value",
  "agent_id": "test",
  "updated_at": "2026-06-26T06:52:42.039324Z"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'shared_read': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "found": true,
  "key": "wrong_type",
  "value": "wrong_type",
  "agent_id": 12345,
  "updated_at": "2026-06-26T06:52:42.040401Z"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'shared_read': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.shared_write`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "written": true,
  "key": "test-key",
  "value": "test-value",
  "agent_id": "test",
  "updated_at": "2026-06-26T06:59:43.251410Z"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'shared_write': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, agent_id='')",
  "p`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "written": true,
  "key": "wrong_type",
  "value": "wrong_type",
  "agent_id": 12345,
  "updated_at": "2026-06-26T06:59:43.252570Z"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'shared_write': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, agent_id='')",
  "p`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.smoke_test`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "passed": false,
  "error": "Invalid URL: no host in 'test'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'smoke_test': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, endpoint='/api/health')",
  "provided_par`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "passed": false,
  "error": "Invalid URL: no host in 'wrong_type'"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'smoke_test': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, endpoint='/api/health')",
  "provided_par`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.start_deploy_poll`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "poll_id": "poll-1782457183-d7f363e8",
  "service_id": "test",
  "commit_sha": null,
  "status": "polling_started",
  "message": "Deploy monitoring started. Use brain_check_deploy('test') to check`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'start_deploy_poll': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id, commit_sha=None)",
 `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "poll_id": "poll-1782457183-acd253d9",
  "service_id": "wrong_type",
  "commit_sha": "wrong_type",
  "status": "polling_started",
  "message": "Deploy monitoring started. Use brain_check_deploy('w`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'start_deploy_poll': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id, commit_sha=None)",
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.sync_auto`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Add sync.enabled: true to .brain/config/nucleus.yaml"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'sync_auto': register.<locals>._sync_auto() missing 1 required positional argument: 'enable'",
  "expected_params": "(enable)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Add sync.enabled: true to .brain/config/nucleus.yaml"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'sync_auto': register.<locals>._sync_auto() missing 1 required positional argument: 'enable'",
  "expected_params": "(enable)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.sync_now`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Sync not enabled",
  "hint": "Create .brain/config/nucleus.yaml with sync.enabled: true"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.sync_resolve`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "error",
  "message": "No active conflict."
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'sync_resolve': register.<locals>._sync_resolve() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, strategy='last_write_w`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "error",
  "message": "No active conflict."
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'sync_resolve': register.<locals>._sync_resolve() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, strategy='last_write_w`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.sync_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "wrong_type",
  "agent_info": {
    "agent_id": "wrong_type",
    "environment": 12345,
    "role": 12345,
    "p`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "wrong_type",
  "agent_info": {
    "agent_id": "wrong_type",
    "environment": 12345,
    "role": 12345,
    "p`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "wrong_type",
  "agent_info": {
    "agent_id": "wrong_type",
    "environment": 12345,
    "role": 12345,
    "p`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "wrong_type",
  "agent_info": {
    "agent_id": "wrong_type",
    "environment": 12345,
    "role": 12345,
    "p`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.test_channel`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "results": {}
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "results": {}
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Channel 'wrong_type' not found"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "results": {}
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.trigger_agent`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Triggered test with event evt-1782457183-89cf3a30`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'trigger_agent': register.<locals>.<lambda>() missing 2 required positional arguments: 'agent' and 'task_description'",
  "expected_params": "(agent, task_descr`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Triggered wrong_type with event evt-1782457183-dcc55fd7`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'trigger_agent': register.<locals>.<lambda>() missing 2 required positional arguments: 'agent' and 'task_description'",
  "expected_params": "(agent, task_descr`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `sync.write_artifact`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Successfully wrote to test`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'write_artifact': register.<locals>.<lambda>() missing 2 required positional arguments: 'path' and 'content'",
  "expected_params": "(path, content)",
  "provid`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error writing artifact: data must be str, not int`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'write_artifact': register.<locals>.<lambda>() missing 2 required positional arguments: 'path' and 'content'",
  "expected_params": "(path, content)",
  "provid`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers"`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `tasks` (17 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `claim` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `context_switch` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `context_switch_reset` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `context_switch_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `create` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `depth_map` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_pop` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_push` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_reset` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_set_max` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_show` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `escalate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_next` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `import_jsonl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `tasks.add`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-9bdd41b9",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "DAG violation: task cannot block itself"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.claim`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.context_switch`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_context": "test",
    "switch_count": 1,
    "max_switches": 5,
    "was_switch": true,
    "recent_contexts": [
      "test"
    ],
    "warning": null,
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_context": "wrong_type",
    "switch_count": 2,
    "max_switches": 5,
    "was_switch": true,
    "recent_contexts": [
      "test",
      "wrong_type"
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.context_switch_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626122943"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626122943"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626122943"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626122943"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.context_switch_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.create`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-dfe130b0",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "DAG violation: task cannot block itself"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_map`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_pop`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_push`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 1,
    "max_safe_depth": 5,
    "topic": "test",
    "breadcrumbs": "test",
    "warning": null,
    "warning_level": "safe",
    "indicator": "[\`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 2,
    "max_safe_depth": 5,
    "topic": "wrong_type",
    "breadcrumbs": "test \u2192 wrong_type",
    "warning": null,
    "warning_level": "saf`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_set_max`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "'<' not supported between instances of 'str' and 'int'"
  },
  "error": null
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "'<' not supported between instances of 'str' and 'int'"
  },
  "error": null
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_show`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.escalate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "error": "Task not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.get_next`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-de8a692d",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-de8a692d",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.import_jsonl`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "File not found: test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "File not found: wrong_type"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
  `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
  `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": [],
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.update`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**266/266 actions return a useful response across 5 confused-LLM scenarios.**
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
