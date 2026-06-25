# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:16:16
**Total tests:** 1862
**Actions tested:** 266
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 607 | 32.6% | Tool returned a successful response |
| ⚠️ handled | 1255 | 67.4% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **1862** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 95 | 35.7% |
| ⚠️ handled | 171 | 64.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 122 | 45.9% |
| ⚠️ handled | 144 | 54.1% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 2 | 0.8% |
| ⚠️ handled | 264 | 99.2% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **266** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 122 | 45.9% |
| ⚠️ handled | 144 | 54.1% |
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

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

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
| `query` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `verify` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

#### `audit_log_tool.admin_query`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{'success': False, 'data': None, 'error': 'admin_query: invalid or missing admin_token'}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{'success': False, 'data': None, 'error': 'admin_query: invalid or missing admin_token'}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{'success': False, 'data': None, 'error': 'admin_query: invalid or missing admin_token'}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{'success': False, 'data': None, 'error': 'admin_query: invalid or missing admin_token'}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action '__nonexistent_action__'. Valid: log_event | query | admin_query | verify"}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action ''. Valid: log_event | query | admin_query | verify"}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.log_event`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{'success': False, 'data': None, 'error': 'log_event requires: event_type, actor, resource, outcome'}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{'success': False, 'data': None, 'error': 'log_event requires: event_type, actor, resource, outcome'}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{'success': False, 'data': None, 'error': 'log_event requires: event_type, actor, resource, outcome'}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{'success': False, 'data': None, 'error': 'log_event requires: event_type, actor, resource, outcome'}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action '__nonexistent_action__'. Valid: log_event | query | admin_query | verify"}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action ''. Valid: log_event | query | admin_query | verify"}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.query`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{'success': True, 'data': {'count': 0, 'records': []}, 'error': None}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{'success': True, 'data': {'count': 0, 'records': []}, 'error': None}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{'success': False, 'data': None, 'error': "invalid literal for int() with base 10: 'not_a_number'"}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{'success': True, 'data': {'count': 0, 'records': []}, 'error': None}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action '__nonexistent_action__'. Valid: log_event | query | admin_query | verify"}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action ''. Valid: log_event | query | admin_query | verify"}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `audit_log_tool.verify`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{'success': True, 'data': {'chain_ok': True, 'broken_at_id': None}, 'error': None}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{'success': True, 'data': {'chain_ok': True, 'broken_at_id': None}, 'error': None}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{'success': True, 'data': {'chain_ok': True, 'broken_at_id': None}, 'error': None}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{'success': True, 'data': {'chain_ok': True, 'broken_at_id': None}, 'error': None}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action '__nonexistent_action__'. Valid: log_event | query | admin_query | verify"}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action ''. Valid: log_event | query | admin_query | verify"}`

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
- *Result preview:* `{'success': True, 'data': {'provider': 'anthropic', 'model': 'claude-haiku-3-5', 'complexity': 'routine', 'sovereignty_tier': 'standard', 'estimated_input_tokens': 1, 'expected_input_cost_usd': 8e-07,`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{'success': True, 'data': {'provider': 'anthropic', 'model': 'claude-haiku-3-5', 'complexity': 'routine', 'sovereignty_tier': 'standard', 'estimated_input_tokens': 1, 'expected_input_cost_usd': 8e-07,`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{'success': True, 'data': {'provider': 'anthropic', 'model': 'claude-haiku-3-5', 'complexity': 'routine', 'sovereignty_tier': 'standard', 'estimated_input_tokens': 1, 'expected_input_cost_usd': 8e-07,`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{'success': True, 'data': {'provider': 'anthropic', 'model': 'claude-haiku-3-5', 'complexity': 'routine', 'sovereignty_tier': 'standard', 'estimated_input_tokens': 1, 'expected_input_cost_usd': 8e-07,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action '__nonexistent_action__'. Valid: route"}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{'success': False, 'data': None, 'error': "Unknown action ''. Valid: route"}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

### Module: `engrams` (38 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `audit_log` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `billing_summary` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `compounding_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `context_graph` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `dsor_get_trace` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `dsor_query_decisions` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `dsor_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `end_of_day` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `engram_neighbors` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `export_schema` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `federation_dsor` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `fusion_reactor` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `governance_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `health` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `heartbeat_check` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `heartbeat_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `hook_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `ipc_tokens` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_decisions` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_snapshots` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_tools` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `metering_summary` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `morning_brief` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `performance_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `prometheus_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pulse_and_polish` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `query_engrams` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `render_graph` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `routing_decisions` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `search_engrams` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `self_healing_sre` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `session_inject` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `tier_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `version` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `weekly_consolidate` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `write_engram` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `engrams.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>.<lambda>() got an unexpected keyword argument 'name'",
  "expected_params": "(key, value, context='Decision', intensity=5)",
  "provide`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision', intensit`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key, value, context='Decision', intensity=5)",
  "provided_`

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

#### `engrams.audit_log`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-25T17:45:13.568681Z",
        "emitter": "brain",
        "type": "session_started",
        "hash": "ef84ee3d70`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-25T17:45:13.568681Z",
        "emitter": "brain",
        "type": "session_started",
        "hash": "ef84ee3d70`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'audit_log': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=20)",
  "provided_params": [
    "id",
    "que`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-25T17:45:13.568681Z",
        "emitter": "brain",
        "type": "session_started",
        "hash": "ef84ee3d70`

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

#### `engrams.billing_summary`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 32.6,
    "total_interactions": 326,
    "breakdown": {
      "unknown": {
        "cost": 16.3,
        "count": 163,
        "tier": 1
      `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 32.6,
    "total_interactions": 326,
    "breakdown": {
      "unknown": {
        "cost": 16.3,
        "count": 163,
        "tier": 1
      `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'billing_summary': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(since_hours=None, group_by='tool')",
  "provide`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 32.6,
    "total_interactions": 326,
    "breakdown": {
      "unknown": {
        "cost": 16.3,
        "count": 163,
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

#### `engrams.compounding_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Thursday\n===============`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Thursday\n===============`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'compounding_status': register.<locals>._h_compounding_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Thursday\n===============`

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

#### `engrams.context_graph`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "growth_hook_morning_brief_generated_9519",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "growth_hook_morning_brief_generated_9519",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_graph': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(include_edges=True, min_intensity=1)",
  "provide`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "growth_hook_morning_brief_generated_9519",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": "`

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

#### `engrams.dsor_get_trace`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_get_trace': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(decision_id)",
  "provided_params": [
    "li`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_get_trace': register.<locals>.<lambda>() missing 1 required positional argument: 'decision_id'",
  "expected_params": "(decision_id)",
  "provided_params"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_get_trace': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(decision_id)",
  "provided_params": [
    "id",
`

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

#### `engrams.dsor_query_decisions`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_query_decisions': register.<locals>.<lambda>() got an unexpected keyword argument 'query'",
  "expected_params": "(limit=50)",
  "provided_params": [
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
    "count": 0,
    "message": "No decisions found. DSoR ledger is empty."
  },
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_query_decisions': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=50)",
  "provided_params": [
    "id`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
    "count": 0,
    "message": "No decisions found. DSoR ledger is empty."
  },
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T`

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

#### `engrams.dsor_status`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'dsor_status': register.<locals>._h_dsor_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "que`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.end_of_day`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': register.<locals>.<lambda>() missing 1 required positional argument: 'summary'",
  "expected_params": "(summary, key_decisions=None, blockers=None`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': register.<locals>.<lambda>() missing 1 required positional argument: 'summary'",
  "expected_params": "(summary, key_decisions=None, blockers=None`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'end_of_day': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(summary, key_decisions=None, blockers=None)",
  "pro`

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

#### `engrams.engram_neighbors`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'engram_neighbors': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key, max_depth=1)",
  "provided_params":`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'engram_neighbors': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key, max_depth=1)",
  "provided_params":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'engram_neighbors': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key, max_depth=1)",
  "provided_params": [
   `

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

#### `engrams.export_schema`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'export_schema': register.<locals>._h_export_schema() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "'MockMCP' object has no attribute 'list_tools'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'export_schema': register.<locals>._h_export_schema() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "'MockMCP' object has no attribute 'list_tools'"
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

#### `engrams.federation_dsor`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'federation_dsor': register.<locals>._h_fed_dsor() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "qu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.fusion_reactor`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': register.<locals>.<lambda>() missing 1 required positional argument: 'observation'",
  "expected_params": "(observation, context='Decision', i`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': register.<locals>.<lambda>() missing 1 required positional argument: 'observation'",
  "expected_params": "(observation, context='Decision', i`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'fusion_reactor': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(observation, context='Decision', intensity=6, wr`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'governance_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "que`

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

#### `engrams.health`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 1,
  "python_version": "3.14.4"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 1,
  "python_version": "3.14.4"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'health': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 1,
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

#### `engrams.heartbeat_check`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-25T17:45:22.035127+00:00",
    "triggers": [
      {
        "signal": "VELOCITY_DROP",
        "recent_writes": 0,
        "window_hours": 4`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-25T17:45:22.370456+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 1.5,
    "formatt`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat_check': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(notify=False, brain_path=None)",
  "provided_pa`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-25T17:45:23.763686+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 2.3,
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

#### `engrams.heartbeat_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "/home/operator/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "/home/operator/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(brain_path=None)",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "/home/operator/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "`

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

#### `engrams.hook_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 148,
    "outcomes": {
      "ADD": 26,
      "NOOP": 39,
      "UNKNOWN": 63,
      "UPDATE": 20
    },
    "by_event_type": {
      "morning_`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 148,
    "outcomes": {
      "ADD": 26,
      "NOOP": 39,
      "UNKNOWN": 63,
      "UPDATE": 20
    },
    "by_event_type": {
      "morning_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'hook_metrics': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 148,
    "outcomes": {
      "ADD": 26,
      "NOOP": 39,
      "UNKNOWN": 63,
      "UPDATE": 20
    },
    "by_event_type": {
      "morning_`

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

#### `engrams.ipc_tokens`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'ipc_tokens': register.<locals>._h_ipc_tokens() got an unexpected keyword argument 'id'",
  "expected_params": "(active_only=True)",
  "provided_params": [
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.list_decisions`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_decisions': register.<locals>._h_list_decisions() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=20)",
  "provided_params": [
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.list_snapshots`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_snapshots': register.<locals>._h_ledger_snapshots() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=10)",
  "provided_params": [
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.list_tools`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_tools': register.<locals>._h_list_tools() got an unexpected keyword argument 'limit'",
  "expected_params": "(category=None)",
  "provided_params": [
    `

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_tools': register.<locals>._h_list_tools() got an unexpected keyword argument 'id'",
  "expected_params": "(category=None)",
  "provided_params": [
    "id`

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

#### `engrams.metering_summary`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'metering_summary': register.<locals>._h_metering() got an unexpected keyword argument 'id'",
  "expected_params": "(since_hours=24)",
  "provided_params": [
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.morning_brief`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 11:15 PM\n==================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 11:15 PM\n==================`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'morning_brief': register.<locals>._h_morning_brief() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 11:15 PM\n==================`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'performance_metrics': register.<locals>._h_perf_metrics() got an unexpected keyword argument 'id'",
  "expected_params": "(export_to_file=False)",
  "provided_`

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

#### `engrams.prometheus_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-25T17:45:23.784897+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-25T17:45:23.785284+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'prometheus_metrics': register.<locals>._h_prom_metrics() got an unexpected keyword argument 'id'",
  "expected_params": "(format='prometheus')",
  "provided_pa`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-25T17:45:23.785659+00:00

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pulse_and_polish': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(write_engram=True)",
  "provided_params": [
  `

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

#### `engrams.query_engrams`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'query_engrams': register.<locals>.<lambda>() got an unexpected keyword argument 'query'",
  "expected_params": "(context=None, min_intensity=1, limit=50)",
  "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "recurring_38a2326e",
        "value": "RECURRING PATTERN (7x): Behind pace: github_issues at 0.0% of target",
        "context`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'query_engrams': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(context=None, min_intensity=1, limit=50)",
  "pro`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [
      {
        "key": "recurring_38a2326e",
        "value": "RECURRING PATTERN (7x): Behind pace: github_issues at 0.0% of target",
        "context`

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
  "error": "Invalid params for action 'render_graph': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(max_nodes=30, min_intensity=1)",
  "provided_param`

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

#### `engrams.routing_decisions`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'routing_decisions': register.<locals>._h_routing_decisions() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=20)",
  "provided_params": `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Error: unsupported operand type(s) for /: 'str' and 'str'"
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

#### `engrams.search`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [],
    "count": 0,
    "total_matching": 0,
    "truncated": false,
    "limit": 5,
    "query": "test",
    "case_sensitive": false,
    "sources": [
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",
  "prov`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query, case_sensitive=False, limit=50)",
  "provided_par`

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

#### `engrams.search_engrams`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "engrams": [],
    "count": 0,
    "total_matching": 0,
    "truncated": false,
    "limit": 5,
    "query": "test",
    "case_sensitive": false,
    "sources": [
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search_engrams': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query, case_sensitive=False, limit=50)",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'search_engrams': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query, case_sensitive=False, limit=50)",
  "prov`

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

#### `engrams.self_healing_sre`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'self_healing_sre': register.<locals>.<lambda>() missing 1 required positional argument: 'symptom'",
  "expected_params": "(symptom, write_engram=True)",
  "pro`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'self_healing_sre': register.<locals>.<lambda>() missing 1 required positional argument: 'symptom'",
  "expected_params": "(symptom, write_engram=True)",
  "pro`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'self_healing_sre': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(symptom, write_engram=True)",
  "provided_para`

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

#### `engrams.session_inject`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (7x): Behind pace: github_issues at 0.0% of`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (7x): Behind pace: github_issues at 0.0% of`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'session_inject': register.<locals>._h_session_inject() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
  `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (7x): Behind pace: github_issues at 0.0% of`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'tier_status': register.<locals>._h_tier_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "que`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'version': register.<locals>._h_version() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
   `

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'weekly_consolidate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(dry_run=True)",
  "provided_params": [
    "`

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

#### `engrams.write_engram`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'write_engram': register.<locals>.<lambda>() got an unexpected keyword argument 'content'. Did you mean 'context'?",
  "expected_params": "(key, value, context=`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'write_engram': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, context='Decision',`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'write_engram': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key, value, context='Decision', intensity=5)",
  "`

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

### Module: `features` (16 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `discover_tools` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `generate_proof` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_proof` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `invoke_tool` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_mounted` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_proofs` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `mount_server` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `thanos_snap` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `traverse_mount` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `unmount_server` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `validate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `features.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 6 required positional arguments: 'product', 'description', 'source', 'version', 'how_to_test', and 'expected_result'",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 7 required positional arguments: 'product', 'name', 'description', 'source', 'version', 'how_to_test', and 'expected_r`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(product, name, description, source, version, how_to_test, exp`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "timestamp": "2026-06-25T17:45:24.633402Z"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T17:45:24.633457Z"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'discover_tools': register.<locals>._h_discover() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id=None)",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T17:45:24.633550Z"
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, thinking=None, deployed_url=None`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "limit"
  ]
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
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "id",
    "query",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "limit"
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id, tool_name, arguments={})",
  "provided_`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(product=None, status=None, tag=None)",
  "provided_para`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "features": [],
  "total": 0
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(product=None, status=None, tag=None)",
  "provided_params"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "features": [],
  "total": 0
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_mounted': register.<locals>._h_list_mounted() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
 `

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
        "/home/operator/ai-`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_mounted': register.<locals>._h_list_mounted() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "q`

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
        "/home/operator/ai-`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_proofs': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[]`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_proofs': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `[]`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
  `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() got an unexpected keyword argument 'id'",
  "expected_params": "(name, command, args=[])",
  "provided_params": [
 `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(query)",
  "provided_params": [
    "query",
    "lim`

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
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query)",
  "provided_params": [
    "id",
    "query",
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'thanos_snap': register.<locals>._h_thanos() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() got an unexpected keyword argument 'id'",
  "expected_params": "(root_mount_id)",
  "provided_params": [
    "`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id)",
  "provided_params": [
    "id",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, status=None, description=None, version=None`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, status=None, description=None,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, status=None, description=None, version=None`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, result)",
  "provided_params": [
    "id",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `health` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `join` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `leave` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `peers` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `route` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `sync` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'health': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>.<lambda>() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>.<lambda>() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(seed_peer)",
  "provided_params": [
    "id",
    "query",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>.<lambda>() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer)",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x10cefb350>"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x10cefb350>"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'leave': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "li`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x10cefb350>"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'peers': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "li`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, profile='default')",
  "provided_param`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, profile='default')",
  "provided_param`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, profile='default')",
  "provided_params": [
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, profile='default')",
  "provided_param`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

🔗 PEERS (0/`

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

🔗 PEERS (0/`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

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

🔗 PEERS (0/`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x10d2a2740>"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x10d2a2740>"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sync': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "lim`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x10d2a2740>"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `audit_report` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `auto_fix_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `comply_apply` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `comply_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `comply_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `curl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `delete_file` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `kyc_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_directory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `lock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pip_install` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `set_mode` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sovereign_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `trace_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `trace_view` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `unlock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `validate_strategic_plan` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `watch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `governance.audit_report`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(report_format='text', since_hours=None, brain_p`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-25T17:45:24.646937+00:00\n  Jurisdiction: N`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(report_format='text', since_hours=None, brain_path`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-25T17:45:24.650341+00:00\n  Jurisdiction: N`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(file_path, verification_command)",
  "provided_pa`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(jurisdiction, brain_path=None)",
  "provided_param`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'comply_list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(brain_path=None)",
  "provided_params": [
    "id`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(url, method='GET')",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path, confirm=False)",
  "provided_params": [
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path, confirm=False)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path, confirm=False)",
  "provided_params": [
    "`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "review_id": "KYC-441C33D2",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T17:45:24.654975+00:00",
  "completed_at": "2026-06-25T17:45:24.654989+00:00",
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "review_id": "KYC-D262F8A2",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T17:45:24.655427+00:00",
  "completed_at": "2026-06-25T17:45:24.655439+00:00",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'kyc_review': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(application_id='APP-001', brain_path=None)",
  "prov`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "review_id": "KYC-D6097431",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T17:45:24.655892+00:00",
  "completed_at": "2026-06-25T17:45:24.655901+00:00",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(path)",
  "provided_params": [
    "limit"
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(package)",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(mode)",
  "provided_params": [
    "id",
    "query",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sovereign_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(brain_path=None)",
  "provided_params": [
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_p`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "count": 12,
  "traces": [
    {
      "file": "KYC-11934284.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-11934284",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_para`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "count": 12,
  "traces": [
    {
      "file": "KYC-11934284.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-11934284",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'trace_view': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_id='', brain_path=None)",
  "provided_params":`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-11934284",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T17:43:44.808150+00:00",
  "completed_at": "2026-06-25T1`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_view': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_id='', brain_path=None)",
  "provided_params":`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-11934284",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T17:43:44.808150+00:00",
  "completed_at": "2026-06-25T1`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(plan_text, mode='strategic')",
  "provi`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `fix_code` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_alerts` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `handoff_task` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `ingest_tasks` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `ingestion_stats` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_dashboard_snapshots` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_pending_consents` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `orchestrate_swarm` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `read_memory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `register_session` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `respond_to_consent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `rollback_ingestion` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search_memory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `session_briefing` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `set_alert_threshold` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `snapshot_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `spawn_agent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `orchestration.AGENTS_ROUTER.apply_critique`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'apply_critique': register.<locals>._h_apply_critique() missing 1 required positional argument: 'review_path'",
  "expected_params": "(review_path)",
  "provide`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'apply_critique': register.<locals>._h_apply_critique() missing 1 required positional argument: 'review_path'",
  "expected_params": "(review_path)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'apply_critique': register.<locals>._h_apply_critique() got an unexpected keyword argument 'id'",
  "expected_params": "(review_path)",
  "provided_params": [
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'critique_code': register.<locals>._h_critique_code() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, context='General R`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'critique_code': register.<locals>._h_critique_code() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, context='General R`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'critique_code': register.<locals>._h_critique_code() got an unexpected keyword argument 'id'",
  "expected_params": "(file_path, context='General Review')",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-25 23:15:24
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-25 23:15:24
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'dashboard': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(detail_level='standard', format='ascii', include_aler`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-25 23:15:24
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'fix_code': register.<locals>._h_fix_code() missing 2 required positional arguments: 'file_path' and 'issues_context'",
  "expected_params": "(file_path, issues`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'fix_code': register.<locals>._h_fix_code() missing 2 required positional arguments: 'file_path' and 'issues_context'",
  "expected_params": "(file_path, issues`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'fix_code': register.<locals>._h_fix_code() got an unexpected keyword argument 'id'",
  "expected_params": "(file_path, issues_context)",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_alerts': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ No active alerts - all systems healthy`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_alerts': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() missing 1 required positional argument: 'task_description'",
  "expected_params": "(task_description, target`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() missing 1 required positional argument: 'task_description'",
  "expected_params": "(task_description, target`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() got an unexpected keyword argument 'id'",
  "expected_params": "(task_description, target_session_id=None, p`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_tasks': register.<locals>._h_ingest_tasks() missing 1 required positional argument: 'source'",
  "expected_params": "(source, source_type='auto', sessio`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_tasks': register.<locals>._h_ingest_tasks() missing 1 required positional argument: 'source'",
  "expected_params": "(source, source_type='auto', sessio`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_tasks': register.<locals>._h_ingest_tasks() got an unexpected keyword argument 'id'",
  "expected_params": "(source, source_type='auto', session_id=None`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'ingestion_stats': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
   snap_1782409487_d8d38e: Snapshot 2026-06-25T17:44:47Z (2026-06-25T17:44:47Z)
   snap_1782409487_59a257: Snapshot 2026-06-25T17:44:47Z `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782409487_d8d38e: Snapshot 2026-06-25T17:44:47Z (2026-06-25T17:44:47Z)
   snap_1782409487_59a257: Snapshot 2026-06-25T17:44:47Z `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_dashboard_snapshots': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=10)",
  "provided_params": [
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782409487_d8d38e: Snapshot 2026-06-25T17:44:47Z (2026-06-25T17:44:47Z)
   snap_1782409487_59a257: Snapshot 2026-06-25T17:44:47Z `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_pending_consents': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{"pending": [], "message": "Use nucleus_agents(action='respond_to_consent', params={agent_id, choice}) to authorize respawns."}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_pending_consents': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'orchestrate_swarm': register.<locals>._h_orchestrate_swarm() missing 1 required positional argument: 'mission'",
  "expected_params": "(mission, agents=None)",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate_swarm': register.<locals>._h_orchestrate_swarm() missing 1 required positional argument: 'mission'",
  "expected_params": "(mission, agents=None)",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate_swarm': register.<locals>._h_orchestrate_swarm() got an unexpected keyword argument 'id'",
  "expected_params": "(mission, agents=None)",
  "provid`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'read_memory': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(category)",
  "provided_params": [
    "id"
  ]
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
  "error": "Invalid params for action 'read_memory': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(category)",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'register_session': register.<locals>._h_register_session() missing 2 required positional arguments: 'conversation_id' and 'focus_area'",
  "expected_params": "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'register_session': register.<locals>._h_register_session() missing 2 required positional arguments: 'conversation_id' and 'focus_area'",
  "expected_params": "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'register_session': register.<locals>._h_register_session() got an unexpected keyword argument 'id'",
  "expected_params": "(conversation_id, focus_area, role=N`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'respond_to_consent': register.<locals>.<lambda>() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id, choice='cold')",
  "pro`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'respond_to_consent': register.<locals>.<lambda>() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id, choice='cold')",
  "pro`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'respond_to_consent': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(agent_id, choice='cold')",
  "provided_param`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'rollback_ingestion': register.<locals>._h_rollback_ingestion() missing 1 required positional argument: 'batch_id'",
  "expected_params": "(batch_id, reason=Non`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'rollback_ingestion': register.<locals>._h_rollback_ingestion() missing 1 required positional argument: 'batch_id'",
  "expected_params": "(batch_id, reason=Non`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'rollback_ingestion': register.<locals>._h_rollback_ingestion() got an unexpected keyword argument 'id'",
  "expected_params": "(batch_id, reason=None)",
  "pro`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'search_memory': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(query)",
  "provided_params": [
    "query",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search_memory': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'search_memory': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query)",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

### 📌 Pending (1)
- ⚪ [heartbeat][velocity_drop] Velocity dropped — 0 writes in 48`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📋 Session Briefing

### 📌 Pending (1)
- ⚪ [heartbeat][velocity_drop] Velocity dropped — 0 writes in 48`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'session_briefing': register.<locals>._h_session_briefing() got an unexpected keyword argument 'id'",
  "expected_params": "(conversation_id=None)",
  "provided`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📋 Session Briefing

### 📌 Pending (1)
- ⚪ [heartbeat][velocity_drop] Velocity dropped — 0 writes in 48`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'set_alert_threshold': register.<locals>._h_set_alert_threshold() missing 3 required positional arguments: 'metric', 'level', and 'value'",
  "expected_params":`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_alert_threshold': register.<locals>._h_set_alert_threshold() missing 3 required positional arguments: 'metric', 'level', and 'value'",
  "expected_params":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'set_alert_threshold': register.<locals>._h_set_alert_threshold() got an unexpected keyword argument 'id'",
  "expected_params": "(metric, level, value)",
  "pr`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
   ID: snap_1782409529_b870f3
   Name: Snapshot 2026-06-25T17:45:29Z
   Timestamp: 2026-06-25T17:45:29Z
   
💡 To compare: brain_compare_dashboards('snap_1782409529_b870f3', 'other_s`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782409529_ca91e2
   Name: Snapshot 2026-06-25T17:45:29Z
   Timestamp: 2026-06-25T17:45:29Z
   
💡 To compare: brain_compare_dashboards('snap_1782409529_ca91e2', 'other_s`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'snapshot_dashboard': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(name=None)",
  "provided_params": [
    "id"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782409529_dda720
   Name: Snapshot 2026-06-25T17:45:29Z
   Timestamp: 2026-06-25T17:45:29Z
   
💡 To compare: brain_compare_dashboards('snap_1782409529_dda720', 'other_s`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'spawn_agent': register.<locals>._h_spawn_agent() missing 1 required positional argument: 'intent'",
  "expected_params": "(intent, execute_now=True, persona=No`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'spawn_agent': register.<locals>._h_spawn_agent() missing 1 required positional argument: 'intent'",
  "expected_params": "(intent, execute_now=True, persona=No`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'spawn_agent': register.<locals>._h_spawn_agent() got an unexpected keyword argument 'id'",
  "expected_params": "(intent, execute_now=True, persona=None, confi`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `capture_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `file_changes` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `gcloud_services` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `gcloud_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `growth_pulse` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_services` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `manage_strategy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `optimize_workflow` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `scan_marketing_log` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `status_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `synthesize_strategy` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `update_roadmap` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `orchestration.INFRA_ROUTER.capture_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:29.851116+00:00"
  },
  "pypi": {
    "error": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:30.728479+00:00"
  },
  "pypi": {
    "error": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'capture_metrics': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(write_engram=True)",
  "provided_params": [
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:31.738232+00:00"
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'file_changes': register.<locals>._h_file_changes() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'gcloud_services': register.<locals>._h_gcloud_services() got an unexpected keyword argument 'id'",
  "expected_params": "(project=None, region='us-central1')",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'gcloud_status': register.<locals>._h_gcloud_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "timestamp": "2026-06-25T17:45:40.359908+00:00",
  "sections": {
    "brief": {
      "engram_count": 52,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-25T17:45:41.311657+00:00",
  "sections": {
    "brief": {
      "engram_count": 57,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'growth_pulse': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(write_engrams=True)",
  "provided_params": [
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-25T17:45:42.363186+00:00",
  "sections": {
    "brief": {
      "engram_count": 62,
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_services': register.<locals>._h_list_services() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_services': register.<locals>._h_list_services() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() got an unexpected keyword argument 'id'",
  "expected_params": "(action, content=None)",
  "provided_p`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'optimize_workflow': register.<locals>._h_optimize_workflow() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "i`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'scan_marketing_log': register.<locals>._h_scan_marketing_log() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'scan_marketing_log': register.<locals>._h_scan_marketing_log() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status_report': register.<locals>._h_status_report() got an unexpected keyword argument 'id'",
  "expected_params": "(focus='roadmap')",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'synthesize_strategy': register.<locals>._h_synthesize_strategy() got an unexpected keyword argument 'id'",
  "expected_params": "(focus_topic=None)",
  "provid`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() got an unexpected keyword argument 'id'",
  "expected_params": "(action, item=None)",
  "provided_params`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() missing 1 required positional argument: 'action'",
  "expected_params": "(action, item=None)",
  "provid`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() got an unexpected keyword argument 'id'",
  "expected_params": "(action, item=None)",
  "provided_params`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `add_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `archive_stale` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `close_commitment` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `commitment_health` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `export` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_commitments` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `open_loops` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `patterns` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pr_watch` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `satellite` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `scan_commitments` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `weekly_challenge` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

#### `orchestration.ORCH_ROUTER.add_loop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add_loop': register.<locals>._h_add_loop() got an unexpected keyword argument 'name'",
  "expected_params": "(description, loop_type='task', priority=3)",
  "p`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add_loop': register.<locals>._h_add_loop() missing 1 required positional argument: 'description'",
  "expected_params": "(description, loop_type='task', priori`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add_loop': register.<locals>._h_add_loop() got an unexpected keyword argument 'id'",
  "expected_params": "(description, loop_type='task', priority=3)",
  "pro`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'archive_stale': register.<locals>._h_archive_stale() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'close_commitment': register.<locals>._h_close_commitment() missing 2 required positional arguments: 'commitment_id' and 'method'",
  "expected_params": "(commi`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'close_commitment': register.<locals>._h_close_commitment() missing 2 required positional arguments: 'commitment_id' and 'method'",
  "expected_params": "(commi`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'close_commitment': register.<locals>._h_close_commitment() got an unexpected keyword argument 'id'",
  "expected_params": "(commitment_id, method)",
  "provide`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'commitment_health': register.<locals>._h_commitment_health() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "i`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'export': register.<locals>._h_export() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'export': register.<locals>._h_export() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_commitments': register.<locals>._h_list_commitments() got an unexpected keyword argument 'limit'",
  "expected_params": "(tier=None)",
  "provided_params"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_commitments': register.<locals>._h_list_commitments() got an unexpected keyword argument 'id'",
  "expected_params": "(tier=None)",
  "provided_params": [`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'metrics': register.<locals>._h_metrics() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'open_loops': register.<locals>._h_open_loops() got an unexpected keyword argument 'id'",
  "expected_params": "(type_filter=None, tier_filter=None)",
  "provid`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'patterns': register.<locals>._h_patterns() got an unexpected keyword argument 'id'",
  "expected_params": "(action='list')",
  "provided_params": [
    "id",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pr_watch': register.<locals>._h_pr_watch() got an unexpected keyword argument 'id'",
  "expected_params": "(threshold_days=None, dry_run=False)",
  "provided_p`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'satellite': register.<locals>._h_satellite() got an unexpected keyword argument 'id'",
  "expected_params": "(detail_level='standard')",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'scan_commitments': register.<locals>._h_scan_commitments() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'weekly_challenge': register.<locals>._h_weekly_challenge() got an unexpected keyword argument 'id'",
  "expected_params": "(action='get', challenge_id=None)",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `Error: unsupported operand type(s) for /: 'str' and 'str'`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `autopilot_sprint_v2` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `force_assign` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `halt_sprint` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `mission_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `orchestrate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume_sprint` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `slot_complete` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `slot_exhaust` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start_mission` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

#### `orchestration.SLOTS_ROUTER.autopilot_sprint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sprint_id": "sprint_1782409544_8b6e",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:15:44+0530"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sprint_id": "sprint_1782409544_6e6c",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:15:44+0530"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'autopilot_sprint': register.<locals>._h_autopilot_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(slots=None, mode='auto', halt_on_bl`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sprint_id": "sprint_1782409544_1c58",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:15:44+0530"
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `🚀 Sprint Report: sprint_1782409544_8bfbb2
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
- *Result preview:* `🚀 Sprint Report: sprint_1782409544_ef7287
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'autopilot_sprint_v2': register.<locals>._h_autopilot_sprint_v2() got an unexpected keyword argument 'id'",
  "expected_params": "(slots=None, mode='auto', halt`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 Sprint Report: sprint_1782409544_1bd658
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, acknowledge_risk=False)",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id, `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, acknowledge_risk=False)",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
   Sprint ID: sprint_1782409544_1bd658
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782409544_1bd658
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'halt_sprint': register.<locals>._h_halt_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(reason='User requested halt')",
  "provided_p`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782409544_1bd658
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'mission_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(mission_id=None)",
  "provided_params": [
    "i`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id=None, model=None, alias=None, mode='auto')"`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'resume_sprint': register.<locals>._h_resume_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(sprint_id=None)",
  "provided_params": [
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, outcome='success', note`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, outcome='success', note`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "provided_param`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() got an unexpected keyword argument 'id'",
  "expected_params": "(name, goal, task_ids, slot_ids=None, budg`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:15 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:15 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status_dashboard': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(detail_level='standard')",
  "provided_params"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:15 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `agent_cost_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `check_kill_switch` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `check_protocol` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `dispatch_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `get_handoffs` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `get_llm_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `mark_high_impact` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pause_notifications` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `rate_limit_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `record_feedback` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `record_interaction` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `request_handoff` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume_notifications` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `set_llm_tier` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `value_ratio` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'agent_cost_dashboard': register.<locals>._h_agent_cost_dashboard() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'check_kill_switch': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "que`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id)",
  "provided_para`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id)",
  "provided_para`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() got an unexpected keyword argument 'id'",
  "expected_params": "(agent_id)",
  "provided_params": [
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "total_dispatches": 695,
  "total_errors": 461,
  "error_rate": 0.6633093525179856,
  "facades": {
    "nucleus_engrams": {
      "calls": 190,
      "errors": 105
    },
    "nucleus_features": {`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_dispatches": 696,
  "total_errors": 461,
  "error_rate": 0.6623563218390804,
  "facades": {
    "nucleus_engrams": {
      "calls": 190,
      "errors": 105
    },
    "nucleus_features": {`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'dispatch_metrics': register.<locals>._h_dispatch_metrics() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_dispatches": 698,
  "total_errors": 462,
  "error_rate": 0.66189111747851,
  "facades": {
    "nucleus_engrams": {
      "calls": 190,
      "errors": 105
    },
    "nucleus_features": {
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_handoffs': register.<locals>._h_get_handoffs() got an unexpected keyword argument 'limit'",
  "expected_params": "(agent_id=None)",
  "provided_params": [
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{"handoffs": [], "message": "No handoffs found"}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_handoffs': register.<locals>._h_get_handoffs() got an unexpected keyword argument 'id'",
  "expected_params": "(agent_id=None)",
  "provided_params": [
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{"handoffs": [], "message": "No handoffs found"}`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_llm_status': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "()",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_llm_status': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "()",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_llm_status': register.<locals>._h_get_llm_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_llm_status': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "()",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'mark_high_impact': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "quer`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pause_notifications': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "enabled": true,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_federation": 35,
    "nucleus_governance": 95,
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "enabled": true,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_federation": 35,
    "nucleus_governance": 95,
    `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'rate_limit_status': register.<locals>._h_rate_limit_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "i`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "enabled": true,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_federation": 35,
    "nucleus_governance": 95,
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() missing 2 required positional arguments: 'notification_type' and 'score'",
  "expected_params": "(notification_t`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() missing 2 required positional arguments: 'notification_type' and 'score'",
  "expected_params": "(notification_t`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(notification_type, score)",
  "provided_params"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'record_interaction': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() missing 3 required positional arguments: 'to_agent', 'context', and 'request'",
  "expected_params": "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() missing 3 required positional arguments: 'to_agent', 'context', and 'request'",
  "expected_params": "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() got an unexpected keyword argument 'id'",
  "expected_params": "(to_agent, context, request, priority=`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'resume_notifications': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() missing 1 required positional argument: 'tier'",
  "expected_params": "(tier)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() missing 1 required positional argument: 'tier'",
  "expected_params": "(tier)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() got an unexpected keyword argument 'id'",
  "expected_params": "(tier)",
  "provided_params": [
    "id",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
**High Impact Closures:** 6
**Ratio:** None
**Verdict:** No notifications sent yet
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 6
**Ratio:** None
**Verdict:** No notifications sent yet
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'value_ratio': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 6
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

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
  "error": "Invalid params for action 'ack': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(message_ids=None, role=None)",
  "provided_params": [
    "`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'inbox': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(role=None, unread_only=True, limit=50)",
  "provided_para`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'post': register.<locals>.<lambda>() got an unexpected keyword argument 'message'",
  "expected_params": "(to=None, subject='', body=None, sender=None, priority`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sent": false,
  "error": "missing_to_field"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'post': register.<locals>.<lambda>() got an unexpected keyword argument 'query'",
  "expected_params": "(to=None, subject='', body=None, sender=None, priority='`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(role=None)",
  "provided_params": [
    "id",
    "query`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `archive_resolved` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `check_recent` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `conversation_stats` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `current` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `detect_splits` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `emit_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `end` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `garbage_collect` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `get_state` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `handoff_summary` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `heartbeat` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `ingest_conversations` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_agents` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_conversations` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `propose_merges` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `read_events` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `resume_checkpoint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `save` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search_conversations` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `start` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `unregister` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `update_state` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'archive_resolved': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "quer`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "exists": false
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": false
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'check_recent': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": false
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, step=None, progress_percent=None,`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id, step=None, progress_percent=None,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'checkpoint': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, step=None, progress_percent=None, context=N`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'conversation_stats': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "exists": false
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": false
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'current': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "exists": false
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'detect_splits': register.<locals>._h_detect_splits() got an unexpected keyword argument 'id'",
  "expected_params": "(worktree_path=None)",
  "provided_params"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'emit_event': register.<locals>._h_emit() missing 3 required positional arguments: 'event_type', 'emitter', and 'data'",
  "expected_params": "(event_type, emit`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'emit_event': register.<locals>._h_emit() missing 3 required positional arguments: 'event_type', 'emitter', and 'data'",
  "expected_params": "(event_type, emit`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'emit_event': register.<locals>._h_emit() got an unexpected keyword argument 'id'",
  "expected_params": "(event_type, emitter, data, description='')",
  "provi`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "summary": "Session ended (neutral): 12 tasks done, 1 tasks created, 250 total events",
    "activity": {
      "total_events": 250,
      "ta`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "Session ended (neutral): 12 tasks done, 1 tasks created, 256 total events",
    "activity": {
      "total_events": 256,
      "ta`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'end': register.<locals>._h_end() got an unexpected keyword argument 'id'",
  "expected_params": "(summary='', learnings='', mood='neutral')",
  "provided_param`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "Session ended (neutral): 12 tasks done, 1 tasks created, 261 total events",
    "activity": {
      "total_events": 261,
      "ta`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'garbage_collect': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(max_age_hours=72, dry_run=False)",
  "provided_`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_state': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(path=None)",
  "provided_params": [
    "limit"
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_state': make_helpers.<locals>.<lambda>() takes 0 positional arguments but 1 was given",
  "expected_params": "(path=None)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_state': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path=None)",
  "provided_params": [
    "id",
    "qu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_state': make_helpers.<locals>.<lambda>() takes 0 positional arguments but 1 was given",
  "expected_params": "(path=None)",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'handoff_summary': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'summary'",
  "expected_params": "(task_id, summary, key_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_summary': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'summary'",
  "expected_params": "(task_id, summary, key_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_summary': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, summary, key_decisions=None, handoff_n`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'heartbeat': register.<locals>._h_heartbeat() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params": [`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat': register.<locals>._h_heartbeat() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params": [`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'heartbeat': register.<locals>._h_heartbeat() got an unexpected keyword argument 'id'",
  "expected_params": "(session_id)",
  "provided_params": [
    "id",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "duration_ms": 275
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
    "duration_ms": 221
  },
  "error": nu`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'ingest_conversations': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(mode='incremental', session_id='', limit=0`

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
    "duration_ms": 202
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [],
    "total": 0
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "lim`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "sessions": [],
    "total": 0
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_agents': register.<locals>._h_list_agents() got an unexpected keyword argument 'limit'",
  "expected_params": "(worktree_path=None, role=None, alive_only=`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "agents": []
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_agents': register.<locals>._h_list_agents() got an unexpected keyword argument 'id'",
  "expected_params": "(worktree_path=None, role=None, alive_only=Tru`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_conversations': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=50, offset=0, sort='recent')",
  "prov`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-25  \n> **Status:** Awaiting human rev`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-25  \n> **Status:** Awaiting human rev`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'propose_merges': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "total_proposals": 0,
    "proposal_text": "# Brain Consolidation Proposals\n\n> **Generated:** 2026-06-25  \n> **Status:** Awaiting human rev`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'read_events': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=10)",
  "provided_params": [
    "id"
  ]
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'read_events': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=10)",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'register': register.<locals>._h_register() missing 4 required positional arguments: 'session_id', 'agent', 'role', and 'provider'",
  "expected_params": "(sess`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'register': register.<locals>._h_register() missing 4 required positional arguments: 'session_id', 'agent', 'role', and 'provider'",
  "expected_params": "(sess`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'register': register.<locals>._h_register() got an unexpected keyword argument 'id'. Did you mean 'pid'?",
  "expected_params": "(session_id, agent, role, provi`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'resume': register.<locals>._h_resume() got an unexpected keyword argument 'id'",
  "expected_params": "(session_id=None)",
  "provided_params": [
    "id",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'resume_checkpoint': register.<locals>.<lambda>() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id)",
  "provided_params": []
`

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
  "error": "Invalid params for action 'resume_checkpoint': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id)",
  "provided_params": [
    "id",
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'save': register.<locals>._h_save() missing 1 required positional argument: 'context'",
  "expected_params": "(context, active_task=None, pending_decisions=None`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'save': register.<locals>._h_save() missing 1 required positional argument: 'context'",
  "expected_params": "(context, active_task=None, pending_decisions=None`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'save': register.<locals>._h_save() got an unexpected keyword argument 'id'",
  "expected_params": "(context, active_task=None, pending_decisions=None, breadcru`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "results": [
      {
        "turn_id": "turn-42490dea55f6",
        "timestamp": "2026-06-25T17:45:05.961790+00:00",
        "intent": "Is this the final nudge fr`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'search_conversations': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query='', limit=20, session_id='', date_fr`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'start': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "li`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'unregister': register.<locals>._h_unregister() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params":`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unregister': register.<locals>._h_unregister() missing 1 required positional argument: 'session_id'",
  "expected_params": "(session_id)",
  "provided_params":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'unregister': register.<locals>._h_unregister() got an unexpected keyword argument 'id'",
  "expected_params": "(session_id)",
  "provided_params": [
    "id",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'update_state': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(updates)",
  "provided_params": [
    "id",
    "n`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update_state': register.<locals>.<lambda>() missing 1 required positional argument: 'updates'",
  "expected_params": "(updates)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update_state': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(updates)",
  "provided_params": [
    "id",
    "q`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `audit_pair` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `check_deploy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `complete_deploy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `evaluate_triggers` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_triggers` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `identify_agent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list_artifacts` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_channels` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_alert` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_audit` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_can_call` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_compare` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `marketplace_diff` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_export` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_federation_proxy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_federation_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_federation_sync` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_history` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_promote` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_quarantine` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_recommend` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_search` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `marketplace_subscribe` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_subscriptions` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_trends` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `marketplace_unsubscribe` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `marketplace_whoami` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `notify` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pair_fire` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pair_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pair_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `pair_stop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `read_artifact` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_ack` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_classify_skip` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_clear` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_event_stats` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_inbox` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_listen` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_log_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_poll_start` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_poll_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_poll_stop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_post` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_skip_review` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `relay_wait` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `saturation_baselines` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `saturation_check` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `shared_list` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `shared_read` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `shared_write` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `smoke_test` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start_deploy_poll` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_auto` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_now` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_resolve` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `test_channel` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `trigger_agent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `write_artifact` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `sync.add_channel`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add_channel': register.<locals>.<lambda>() missing 1 required positional argument: 'channel_type'",
  "expected_params": "(channel_type, **kwargs)",
  "provide`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add_channel': register.<locals>.<lambda>() missing 1 required positional argument: 'channel_type'",
  "expected_params": "(channel_type, **kwargs)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add_channel': register.<locals>.<lambda>() missing 1 required positional argument: 'channel_type'",
  "expected_params": "(channel_type, **kwargs)",
  "provide`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'audit_pair': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(window_hours=24.0)",
  "provided_params": [
    "`

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
  "error": "Invalid params for action 'audit_pair': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(window_hours=24.0)",
  "provided_params": [
    "id"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'check_deploy': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id)",
  "provided_params": []`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'check_deploy': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id)",
  "provided_params": []`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'check_deploy': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(service_id)",
  "provided_params": [
    "id",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'complete_deploy': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(service_id, success, deploy_url=None, error=Non`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'complete_deploy': register.<locals>.<lambda>() missing 2 required positional arguments: 'service_id' and 'success'",
  "expected_params": "(service_id, success`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'complete_deploy': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(service_id, success, deploy_url=None, error=Non`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'evaluate_triggers': register.<locals>.<lambda>() missing 2 required positional arguments: 'event_type' and 'emitter'",
  "expected_params": "(event_type, emitt`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'evaluate_triggers': register.<locals>.<lambda>() missing 2 required positional arguments: 'event_type' and 'emitter'",
  "expected_params": "(event_type, emitt`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'evaluate_triggers': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(event_type, emitter)",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_triggers': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[]`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_triggers': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'identify_agent': register.<locals>._identify_agent() got an unexpected keyword argument 'id'",
  "expected_params": "(agent_id=None, environment='unknown', rol`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_artifacts': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(folder=None)",
  "provided_params": [
    "li`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[]`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_artifacts': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(folder=None)",
  "provided_params": [
    "id",
`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_channels': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "channels": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_channels': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_alert': register.<locals>.<lambda>() missing 2 required positional arguments: 'subscriber' and 'target'",
  "expected_params": "(subscriber, target`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_alert': register.<locals>.<lambda>() missing 2 required positional arguments: 'subscriber' and 'target'",
  "expected_params": "(subscriber, target`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_alert': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(subscriber, target, event_types=None)",
  "pr`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_audit': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(caller=None, target=None, action_type=None, since_timestamp=Non`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_audit': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(caller=None, target=None, action_type=None, since_timestamp=Non`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_audit': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(caller=None, target=None, action_type=None, s`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_audit': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(caller=None, target=None, action_type=None, since_timestamp=Non`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_can_call': register.<locals>.<lambda>() missing 2 required positional arguments: 'caller' and 'target'",
  "expected_params": "(caller, target)",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_can_call': register.<locals>.<lambda>() missing 2 required positional arguments: 'caller' and 'target'",
  "expected_params": "(caller, target)",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_can_call': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(caller, target)",
  "provided_params": [
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_compare': register.<locals>.<lambda>() missing 2 required positional arguments: 'a' and 'b'",
  "expected_params": "(a, b)",
  "provided_params": [`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_compare': register.<locals>.<lambda>() missing 2 required positional arguments: 'a' and 'b'",
  "expected_params": "(a, b)",
  "provided_params": [`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_compare': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(a, b)",
  "provided_params": [
    "id",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_dashboard': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_diff': register.<locals>.<lambda>() missing 2 required positional arguments: 'snapshot_a' and 'snapshot_b'",
  "expected_params": "(snapshot_a, sna`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_diff': register.<locals>.<lambda>() missing 2 required positional arguments: 'snapshot_a' and 'snapshot_b'",
  "expected_params": "(snapshot_a, sna`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_diff': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(snapshot_a, snapshot_b)",
  "provided_params":`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_export': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "snapshot": [],
  "total": 0
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_export': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "qu`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_federation_proxy': register.<locals>.<lambda>() missing 2 required positional arguments: 'target_brain' and 'action'",
  "expected_params": "(targe`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_proxy': register.<locals>.<lambda>() missing 2 required positional arguments: 'target_brain' and 'action'",
  "expected_params": "(targe`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_proxy': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(target_brain, action, payload=None`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_federation_register': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, capabilities`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_register': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, capabilities`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_federation_register': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(address, capabilities=None, dis`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_federation_sync': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_history': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, limit=20)",
  "provided_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_history': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, limit=20)",
  "provided_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_history': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(address, limit=20)",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_promote': register.<locals>.<lambda>() missing 2 required positional arguments: 'address' and 'new_tier'",
  "expected_params": "(address, new_tier`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_promote': register.<locals>.<lambda>() missing 2 required positional arguments: 'address' and 'new_tier'",
  "expected_params": "(address, new_tier`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_promote': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(address, new_tier, caller='admin')",
  "pro`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_quarantine': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, caller='admin', reaso`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_quarantine': register.<locals>.<lambda>() missing 1 required positional argument: 'address'",
  "expected_params": "(address, caller='admin', reaso`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_quarantine': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(address, caller='admin', reason='')",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': register.<locals>.<lambda>() missing 1 required positional argument: 'task'",
  "expected_params": "(task, top_k=5)",
  "provided_param`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': register.<locals>.<lambda>() missing 1 required positional argument: 'task'",
  "expected_params": "(task, top_k=5)",
  "provided_param`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_recommend': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_search': register.<locals>.<lambda>() got an unexpected keyword argument 'query'",
  "expected_params": "(tags=None, min_tier=None, limit=10)",
  "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "cards": [],
  "count": 0
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_search': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(tags=None, min_tier=None, limit=10)",
  "pro`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*', even`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*', even`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscribe': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(subscriber, target='*', event_types=None)`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscriptions': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(subscriber=None)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscriptions': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(subscriber=None)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscriptions': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(subscriber=None)",
  "provided_params`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_subscriptions': unsupported operand type(s) for /: 'str' and 'str'",
  "expected_params": "(subscriber=None)",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'marketplace_trends': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(days=30, brain_path=None)",
  "provided_para`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_unsubscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*')",
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_unsubscribe': register.<locals>.<lambda>() missing 1 required positional argument: 'subscriber'",
  "expected_params": "(subscriber, target='*')",
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_unsubscribe': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(subscriber, target='*')",
  "provided_p`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_whoami': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(role=None)",
  "provided_params": [
    "id"`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'notify': register.<locals>.<lambda>() missing 2 required positional arguments: 'title' and 'message'",
  "expected_params": "(title, message, level='info')",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'notify': register.<locals>.<lambda>() missing 2 required positional arguments: 'title' and 'message'",
  "expected_params": "(title, message, level='info')",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'notify': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(title, message, level='info')",
  "provided_params": [
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'pair_fire': register.<locals>.<lambda>() missing 2 required positional arguments: 'lane' and 'brief'",
  "expected_params": "(lane, brief, model='sonnet', subj`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pair_fire': register.<locals>.<lambda>() missing 2 required positional arguments: 'lane' and 'brief'",
  "expected_params": "(lane, brief, model='sonnet', subj`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pair_fire': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(lane, brief, model='sonnet', subject=None, parent_ses`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'pair_register': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane, charter_path=None)",
  "provided_par`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pair_register': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane, charter_path=None)",
  "provided_par`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pair_register': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(lane, charter_path=None)",
  "provided_params": [`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'pair_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(lane=None)",
  "provided_params": [
    "id",
    "`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'pair_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'lane'",
  "expected_params": "(lane)",
  "provided_params": []
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
  "error": "Invalid params for action 'pair_stop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(lane)",
  "provided_params": [
    "id",
    "query",`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'read_artifact': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'read_artifact': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'read_artifact': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "que`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'relay_ack': register.<locals>.<lambda>() missing 1 required positional argument: 'message_id'",
  "expected_params": "(message_id, recipient=None, session_id=N`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_ack': register.<locals>.<lambda>() missing 1 required positional argument: 'message_id'",
  "expected_params": "(message_id, recipient=None, session_id=N`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_ack': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(message_id, recipient=None, session_id=None)",
  "pro`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'relay_classify_skip': register.<locals>.<lambda>() missing 3 required positional arguments: 'ts', 'subject', and 'classification'",
  "expected_params": "(ts, `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_classify_skip': register.<locals>.<lambda>() missing 3 required positional arguments: 'ts', 'subject', and 'classification'",
  "expected_params": "(ts, `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_classify_skip': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(ts, subject, classification, note=None)",
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'relay_clear': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(recipient=None, older_than_hours=168)",
  "provided`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_event_stats': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "que`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'relay_inbox': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(unread_only=True, limit=20, recipient=None, session`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.6s.",
  "module": "nucleus_sync"
}`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `claim` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `context_switch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `context_switch_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `context_switch_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `create` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `depth_map` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_pop` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_push` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `depth_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `depth_set_max` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `depth_show` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `escalate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_next` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `import_jsonl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `tasks.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'name'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=N`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=Non`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, agent_id)",
  "provided_params": [
    "id",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(new_context)",
  "provided_params": [
    "id",
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
    "session_id": "session-20260625231547"
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
    "session_id": "session-20260625231547"
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch_reset': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260625231547"
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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() got an unexpected keyword argument 'name'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skill`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_map': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "()",
  "provided_params": [
    "level"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_map': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_pop': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "()",
  "provided_params": [
    "level"
  ]
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_pop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "(topic)",
  "provided_params": [
    "level"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(topic)",
  "provided_params": [
    "id",
    "query`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_reset': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "(max_depth)",
  "provided_params": [
    "level`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(max_depth)",
  "provided_params": [
    "id",
   `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_show': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, reason)",
  "provided_params": [
    "id",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() got an unexpected keyword argument 'limit'",
  "expected_params": "(skills)",
  "provided_params": [
    "limit"
  ]`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() got an unexpected keyword argument 'id'",
  "expected_params": "(skills)",
  "provided_params": [
    "id",
    "que`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() got an unexpected keyword argument 'data'",
  "expected_params": "(jsonl_path, clear_existing=False, merge_gtm_met`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() got an unexpected keyword argument 'id'",
  "expected_params": "(jsonl_path, clear_existing=False, merge_gtm_metad`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>._h_list() got an unexpected keyword argument 'limit'",
  "expected_params": "(status=None, priority=None, skill=None, claimed_by=None)`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-10140ad6",
      "description": "[heartbeat][velocity_drop] Velocity dropped \u2014 0 writes in 48h.",
      "status": "PENDING",
      "priori`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>._h_list() got an unexpected keyword argument 'id'",
  "expected_params": "(status=None, priority=None, skill=None, claimed_by=None)",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-10140ad6",
      "description": "[heartbeat][velocity_drop] Velocity dropped \u2014 0 writes in 48h.",
      "status": "PENDING",
      "priori`

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, updates)",
  "provided_params": [
    "id",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, updates)",
  "provided_params": [
    "id",
  `

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
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
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

## Fire-Without-Thinking (Zero-Config) Details

**266/266 actions return a useful response when called with empty action + empty params.**
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
