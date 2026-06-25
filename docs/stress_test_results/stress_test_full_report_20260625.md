# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 1526
**Actions tested:** 218
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 254 | 16.6% | Tool returned a successful response |
| ⚠️ handled | 1146 | 75.1% | Tool returned a graceful error (no crash) |
| 🔶 warn | 126 | 8.3% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **1526** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 43 | 19.7% |
| ⚠️ handled | 175 | 80.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 59 | 27.1% |
| ⚠️ handled | 159 | 72.9% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 1 | 0.5% |
| ⚠️ handled | 217 | 99.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 59 | 27.1% |
| ⚠️ handled | 159 | 72.9% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 218 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 218 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 92 | 42.2% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 126 | 57.8% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **218** | **100%** |

## Per-Module Breakdown

### Module: `audit_log_tool` (4 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `admin_query` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `log_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `query` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `verify` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 4 pass |

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

### Module: `cost_router` (1 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `route` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `cost_router.route`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'route' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'route' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'route' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'route' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace`

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

### Module: `engrams` (39 actions)

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
| `tool` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
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
        "timestamp": "2026-06-25T15:49:07.944378Z",
        "emitter": "nucleus_governance",
        "type": "governance_sovereign_status_gene`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-25T15:49:07.944378Z",
        "emitter": "nucleus_governance",
        "type": "governance_sovereign_status_gene`

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
        "timestamp": "2026-06-25T15:49:07.944378Z",
        "emitter": "nucleus_governance",
        "type": "governance_sovereign_status_gene`

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
    "total_cost_units": 4080.6,
    "total_interactions": 40806,
    "breakdown": {
      "unknown": {
        "cost": 3415.6,
        "count": 34156,
        "tier": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 4080.6,
    "total_interactions": 40806,
    "breakdown": {
      "unknown": {
        "cost": 3415.6,
        "count": 34156,
        "tier": `

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
    "total_cost_units": 4080.6,
    "total_interactions": 40806,
    "breakdown": {
      "unknown": {
        "cost": 3415.6,
        "count": 34156,
        "tier": `

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
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Thursday\n================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Thursday\n================`

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
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [GROWING]\n   Week 26 | Thursday\n================`

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
        "id": "brief_2649",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "brief_2646",
        "context"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "brief_2649",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "brief_2646",
        "context"`

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
        "id": "brief_2649",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "brief_2646",
        "context"`

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
    "decisions": [
      {
        "decision_id": "dec-5fc286f2e1d2",
        "reasoning": "Tool: nucleus_engrams | LLM tool call after critic intervention, turn 2",
 `

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
    "decisions": [
      {
        "decision_id": "dec-5fc286f2e1d2",
        "reasoning": "Tool: nucleus_engrams | LLM tool call after critic intervention, turn 2",
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
  "brain_path": "<BRAIN_PATH>/.brain",
  "uptime_seconds": 17,
  "python_version": "3.14.4"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "<BRAIN_PATH>/.brain",
  "uptime_seconds": 17,
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
  "brain_path": "<BRAIN_PATH>/.brain",
  "uptime_seconds": 17,
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
    "timestamp": "2026-06-25T15:50:58.094453+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 184.1,
    "forma`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-25T15:50:58.661420+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 164.9,
    "forma`

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
    "timestamp": "2026-06-25T15:51:00.147152+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 193.3,
    "forma`

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
      "plist_path": "<HOME>/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "<HOME>/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
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
      "plist_path": "<HOME>/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
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
    "total_executions": 28929,
    "outcomes": {
      "ADD": 7477,
      "UPDATE": 175,
      "NOOP": 869,
      "UNKNOWN": 20391,
      "ERROR": 17
    },
    "by_ev`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 28929,
    "outcomes": {
      "ADD": 7477,
      "UPDATE": 175,
      "NOOP": 869,
      "UNKNOWN": 20391,
      "ERROR": 17
    },
    "by_ev`

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
    "total_executions": 28929,
    "outcomes": {
      "ADD": 7477,
      "UPDATE": 175,
      "NOOP": 869,
      "UNKNOWN": 20391,
      "ERROR": 17
    },
    "by_ev`

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
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 09:21 PM\n==================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 09:21 PM\n==================`

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
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Thursday, June 25, 2026 09:21 PM\n==================`

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
# Generated at 2026-06-25T15:51:04.152704+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-25T15:51:04.159286+00:00

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
# Generated at 2026-06-25T15:51:04.163725+00:00

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
        "key": "v0.6.0_windsurf_check",
        "value": "Verified 8-tool lean tier in real-world Cascade session.",
        "context": "Decis`

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
        "key": "v0.6.0_windsurf_check",
        "value": "Verified 8-tool lean tier in real-world Cascade session.",
        "context": "Decis`

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
    "engrams": [
      {
        "key": "megaplan_v107_first_impression",
        "value": "v1.0.7 \"First Impression\" megaplan completed via Exhaustive Design Thinki`

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
    "engrams": [
      {
        "key": "megaplan_v107_first_impression",
        "value": "v1.0.7 \"First Impression\" megaplan completed via Exhaustive Design Thinki`

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
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 v0.6.0_windsurf_check: Verified 8-tool lean tier in real-world Cascade session.\n`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 v0.6.0_windsurf_check: Verified 8-tool lean tier in real-world Cascade session.\n`

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
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 v0.6.0_windsurf_check: Verified 8-tool lean tier in real-world Cascade session.\n`

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

#### `engrams.tool`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'tool' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace"`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'tool' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'tool' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace"`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'tool' in nucleus_engrams",
  "available_actions": [
    "add",
    "audit_log",
    "billing_summary",
    "compounding_status",
    "context_graph",
    "dsor_get_trace"`

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
  "timestamp": "2026-06-25T15:51:14.831699Z"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T15:51:14.832923Z"
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
  "timestamp": "2026-06-25T15:51:14.833310Z"
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
  "features": [
    {
      "id": "smoke_test_feature",
      "name": "smoke_test_feature",
      "description": "Dry run test feature for smoke testing",
      "product": "nucleus",
      "source":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(product=None, status=None, tag=None)",
  "provided_params"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "features": [
    {
      "id": "smoke_test_feature",
      "name": "smoke_test_feature",
      "description": "Dry run test feature for smoke testing",
      "product": "nucleus",
      "source":`

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
      "command": "/opt/homebrew/opt/python@3.11/bin/python3.11",
      "args": [
        "<HOME>/ai-`

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
      "command": "/opt/homebrew/opt/python@3.11/bin/python3.11",
      "args": [
        "<HOME>/ai-`

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
- *Result preview:* `[
  "smoke_test_feature.md",
  "verification_test_feature.md",
  "qa_swarm_test_feature.md",
  "crisis_detection.md",
  "test_feature.md"
]`

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
- *Result preview:* `[
  "smoke_test_feature.md",
  "verification_test_feature.md",
  "qa_swarm_test_feature.md",
  "crisis_detection.md",
  "test_feature.md"
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

### Module: `federation` (8 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `default` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `health` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `join` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `leave` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `peers` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `route` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `sync` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

#### `federation.default`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'default' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  "hint": "Try: n`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'default' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  "hint": "Try: n`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'default' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  "hint": "Try: n`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'default' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  "hint": "Try: n`

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
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x11da2b940>"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x11da2b940>"`

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
- *Result preview:* `"<coroutine object _brain_federation_leave_impl at 0x11da2b940>"`

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
   ID: brain_.brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/0 on`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_.brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/0 on`

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
   ID: brain_.brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/0 on`

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
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x1148c8c40>"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x1148c8c40>"`

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
- *Result preview:* `"<coroutine object _brain_federation_sync_impl at 0x1148c8c40>"`

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

### Module: `governance` (21 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `GET` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `audit_report` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `auto_fix_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `comply_apply` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `comply_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `comply_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `curl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `delete_file` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `kyc_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `list_directory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `lock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pip_install` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `set_mode` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sovereign_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `strategic` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `trace_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `trace_view` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `unlock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `validate_strategic_plan` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `watch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

#### `governance.GET`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.audit_report`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(report_format='text', since_hours=None, brain_p`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': 'NoneType' object is not subscriptable",
  "expected_params": "(report_format='text', since_hours=None, brain_path=None)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(report_format='text', since_hours=None, brain_path`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': 'NoneType' object is not subscriptable",
  "expected_params": "(report_format='text', since_hours=None, brain_path=None)",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.comply_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

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
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.kyc_review`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "review_id": "KYC-FB808C52",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.053345+00:00",
  "completed_at": "2026-06-25T15:51:15.053378+00:00",
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "review_id": "KYC-7ADC7FAB",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.054532+00:00",
  "completed_at": "2026-06-25T15:51:15.054556+00:00",
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
  "review_id": "KYC-C47AAE33",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.055940+00:00",
  "completed_at": "2026-06-25T15:51:15.055964+00:00",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.sovereign_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

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
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: <BRAIN_PATH>
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: <BRAIN_PATH>
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
📍 Workspace: <BRAIN_PATH>
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.strategic`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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
  "count": 99,
  "traces": [
    {
      "file": "KYC-0247F068.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0247F068",
      "recommendation": "REJECT",
      "risk_score": 175,
      `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_para`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "count": 99,
  "traces": [
    {
      "file": "KYC-0247F068.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0247F068",
      "recommendation": "REJECT",
      "risk_score": 175,
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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
  "review_id": "KYC-74E5C72F",
  "application_id": "APP-003",
  "applicant": "Dmitri Volkov",
  "started_at": "2026-03-03T08:21:57.981452Z",
  "completed_at": "2026-03-03T08:`

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
  "review_id": "KYC-74E5C72F",
  "application_id": "APP-003",
  "applicant": "Dmitri Volkov",
  "started_at": "2026-03-03T08:21:57.981452Z",
  "completed_at": "2026-03-03T08:`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

### Module: `orchestration` (13 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `archive_stale` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `close_commitment` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `commitment_health` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `export` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `list_commitments` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `metrics` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `open_loops` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `patterns` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pr_watch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `satellite` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `scan_commitments` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `weekly_challenge` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

#### `orchestration.add_loop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'add_loop' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'add_loop' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'add_loop' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'add_loop' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.archive_stale`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'archive_stale' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "cre`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'archive_stale' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "cre`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'archive_stale' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "cre`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'archive_stale' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "cre`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.close_commitment`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'close_commitment' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'close_commitment' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'close_commitment' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'close_commitment' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.commitment_health`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'commitment_health' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'commitment_health' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'commitment_health' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'commitment_health' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.export`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'export' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'export' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'export' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
 `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'export' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.list_commitments`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'list_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'list_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'list_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'list_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.metrics`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'metrics' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'metrics' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'metrics' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'metrics' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.open_loops`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'open_loops' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'open_loops' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'open_loops' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'open_loops' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.patterns`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'patterns' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'patterns' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'patterns' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'patterns' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.pr_watch`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'pr_watch' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'pr_watch' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'pr_watch' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'pr_watch' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.satellite`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'satellite' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create"`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'satellite' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'satellite' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create"`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'satellite' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create"`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.scan_commitments`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'scan_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'scan_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'scan_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'scan_commitments' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `orchestration.weekly_challenge`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'weekly_challenge' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'weekly_challenge' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'weekly_challenge' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'weekly_challenge' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

### Module: `relay` (4 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `ack` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `inbox` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `post` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

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

### Module: `sync` (67 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `*` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `/api/health` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `add_channel` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `admin` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `audit_pair` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `check_deploy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `complete_deploy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `evaluate_triggers` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `get_triggers` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `identify_agent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `info` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `list_artifacts` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `list_channels` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `marketplace_alert` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_audit` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_can_call` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_compare` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `marketplace_diff` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_export` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `marketplace_federation_proxy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_federation_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_federation_sync` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_history` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_promote` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_quarantine` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_recommend` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_search` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `marketplace_subscribe` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_subscriptions` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_trends` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `marketplace_unsubscribe` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `marketplace_whoami` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `notify` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pair_fire` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pair_register` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pair_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `pair_stop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `read_artifact` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_ack` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_classify_skip` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_clear` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_event_stats` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_inbox` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_listen` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_log_event` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_poll_start` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_poll_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_poll_stop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_post` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_skip_review` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `relay_wait` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `saturation_baselines` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `saturation_check` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `shared_list` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `shared_read` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `shared_write` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `smoke_test` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `start_deploy_poll` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sync_auto` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sync_now` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sync_resolve` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sync_status` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `test_channel` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `trigger_agent` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `write_artifact` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

#### `sync.*`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action '*' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action '*' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers",`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action '*' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action '*' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_triggers",`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync./api/health`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action '/api/health' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action '/api/health' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action '/api/health' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action '/api/health' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.admin`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'admin' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigge`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'admin' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigge`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'admin' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigge`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'admin' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigge`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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
- *Result preview:* `[
  {
    "id": "trigger-synthesis",
    "event_type": "user_intent",
    "target_agent": "synthesizer",
    "description": "Synthesizer triages incoming user intent."
  },
  {
    "id": "trigger-groo`

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
- *Result preview:* `[
  {
    "id": "trigger-synthesis",
    "event_type": "user_intent",
    "target_agent": "synthesizer",
    "description": "Synthesizer triages incoming user intent."
  },
  {
    "id": "trigger-groo`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.info`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'info' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigger`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'info' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigger`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'info' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigger`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'info' in nucleus_sync",
  "available_actions": [
    "add_channel",
    "audit_pair",
    "check_deploy",
    "complete_deploy",
    "evaluate_triggers",
    "get_trigger`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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
- *Result preview:* `[
  ".DS_Store",
  "dummy.md",
  "research/mcp_debugging_guide.md",
  "research/clinical_advisor_playbook.md",
  "research/user_interview_script.md",
  "research/hardening_patterns_research.md",
  "re`

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
- *Result preview:* `[
  ".DS_Store",
  "dummy.md",
  "research/mcp_debugging_guide.md",
  "research/clinical_advisor_playbook.md",
  "research/user_interview_script.md",
  "research/hardening_patterns_research.md",
  "re`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.marketplace_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "total_registered": 3,
  "by_tier": {
    "unverified": 2,
    "active": 0,
    "trusted": 0,
    "verified": 1
  },
  "inactive_count": 0,
  "top_10_by_reputation": [
    {
      "address": "sonn`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_registered": 3,
  "by_tier": {
    "unverified": 2,
    "active": 0,
    "trusted": 0,
    "verified": 1
  },
  "inactive_count": 0,
  "top_10_by_reputation": [
    {
      "address": "sonn`

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
  "total_registered": 3,
  "by_tier": {
    "unverified": 2,
    "active": 0,
    "trusted": 0,
    "verified": 1
  },
  "inactive_count": 0,
  "top_10_by_reputation": [
    {
      "address": "sonn`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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
  "snapshot": [
    {
      "address": "sonnet-helper-cc-tb@nucleus",
      "display_name": "sonnet_helper_cc_tb",
      "accepts": [
        "spawn_brief"
      ],
      "emits": [
        "spawn_r`

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
  "snapshot": [
    {
      "address": "sonnet-helper-cc-tb@nucleus",
      "display_name": "sonnet_helper_cc_tb",
      "accepts": [
        "spawn_brief"
      ],
      "emits": [
        "spawn_r`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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
  "cards": [
    {
      "address": "multi-cascade@nucleus",
      "display_name": "Multi-Cascade Parallel Execution",
      "description": "Parallel AI execution with CRDT-based atomic claiming. 4+`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_search': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(tags=None, min_tier=None, limit=10)",
  "pro`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "cards": [
    {
      "address": "multi-cascade@nucleus",
      "display_name": "Multi-Cascade Parallel Execution",
      "description": "Parallel AI execution with CRDT-based atomic claiming. 4+`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.marketplace_trends`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "trend": "stable",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": [
    {
      "date": "2026-05-26",
      "total_registered": 3,
      "distribution": {
        "unverified": 66.67,`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "trend": "stable",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": [
    {
      "date": "2026-05-26",
      "total_registered": 3,
      "distribution": {
        "unverified": 66.67,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'marketplace_trends': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(days=30, brain_path=None)",
  "provided_para`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "trend": "stable",
  "days_analyzed": 30,
  "total_changes": 0,
  "snapshots": [
    {
      "date": "2026-05-26",
      "total_registered": 3,
      "distribution": {
        "unverified": 66.67,`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_classify_skip`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_clear`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_event_stats`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_inbox`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_listen`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_log_event`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_poll_start`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_poll_status`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_poll_stop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_post`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_skip_review`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_status`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.relay_wait`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.saturation_baselines`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.saturation_check`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.shared_list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.shared_read`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.shared_write`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.smoke_test`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.start_deploy_poll`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.sync_auto`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.sync_now`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.sync_resolve`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.sync_status`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.test_channel`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.trigger_agent`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

#### `sync.write_artifact`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
  "module": "nucleus_sync"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Rate limit exceeded for nucleus_sync: 200 calls per 60s window. Try again in 59.7s.",
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic`

---

### Module: `tasks` (17 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `claim` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `context_switch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `context_switch_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `context_switch_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `create` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_map` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `depth_pop` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `depth_push` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `depth_set_max` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_show` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `escalate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `get_next` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `import_jsonl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.context_switch_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260625212116"
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
    "session_id": "session-20260625212116"
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
    "session_id": "session-20260625212116"
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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
    "indicator": "[\u2591\u2591\u2591]"
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
    "indicator": "[\u2591\u2591\u2591]"
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591]"
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
    "indicator": "[\u2591\u2591\u2591]"
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
    "indicator": "[\u2591\u2591\u2591]"
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_show`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 3,
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
    "max_safe_depth": 3,
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
    "max_safe_depth": 3,
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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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
      "id": "task-7bdd42ef",
      "description": "v1.0.9 Sovereign Outreach Execution: Post 3 Reddit strikes (secithub, pwnhub, LocalLLaMA) using Comet Striker `

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
      "id": "task-7bdd42ef",
      "description": "v1.0.9 Sovereign Outreach Execution: Post 3 Reddit strikes (secithub, pwnhub, LocalLLaMA) using Comet Striker `

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

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

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

## Cross-Agent Compatibility Details

**126 actions have cross-agent compatibility warnings.**

| Module | Action | Warning |
|--------|--------|---------|
| audit_log_tool | `admin_query` | not async — some MCP clients expect async tools |
| audit_log_tool | `log_event` | not async — some MCP clients expect async tools |
| audit_log_tool | `query` | not async — some MCP clients expect async tools |
| audit_log_tool | `verify` | not async — some MCP clients expect async tools |
| governance | `GET` | not async — some MCP clients expect async tools |
| governance | `audit_report` | not async — some MCP clients expect async tools |
| governance | `auto_fix_loop` | not async — some MCP clients expect async tools |
| governance | `comply_apply` | not async — some MCP clients expect async tools |
| governance | `comply_list` | not async — some MCP clients expect async tools |
| governance | `comply_report` | not async — some MCP clients expect async tools |
| governance | `curl` | not async — some MCP clients expect async tools |
| governance | `delete_file` | not async — some MCP clients expect async tools |
| governance | `kyc_review` | not async — some MCP clients expect async tools |
| governance | `list_directory` | not async — some MCP clients expect async tools |
| governance | `lock` | not async — some MCP clients expect async tools |
| governance | `pip_install` | not async — some MCP clients expect async tools |
| governance | `set_mode` | not async — some MCP clients expect async tools |
| governance | `sovereign_status` | not async — some MCP clients expect async tools |
| governance | `status` | not async — some MCP clients expect async tools |
| governance | `strategic` | not async — some MCP clients expect async tools |
| governance | `trace_list` | not async — some MCP clients expect async tools |
| governance | `trace_view` | not async — some MCP clients expect async tools |
| governance | `unlock` | not async — some MCP clients expect async tools |
| governance | `validate_strategic_plan` | not async — some MCP clients expect async tools |
| governance | `watch` | not async — some MCP clients expect async tools |
| orchestration | `add_loop` | not async — some MCP clients expect async tools |
| orchestration | `archive_stale` | not async — some MCP clients expect async tools |
| orchestration | `close_commitment` | not async — some MCP clients expect async tools |
| orchestration | `commitment_health` | not async — some MCP clients expect async tools |
| orchestration | `export` | not async — some MCP clients expect async tools |
| orchestration | `list_commitments` | not async — some MCP clients expect async tools |
| orchestration | `metrics` | not async — some MCP clients expect async tools |
| orchestration | `open_loops` | not async — some MCP clients expect async tools |
| orchestration | `patterns` | not async — some MCP clients expect async tools |
| orchestration | `pr_watch` | not async — some MCP clients expect async tools |
| orchestration | `satellite` | not async — some MCP clients expect async tools |
| orchestration | `scan_commitments` | not async — some MCP clients expect async tools |
| orchestration | `weekly_challenge` | not async — some MCP clients expect async tools |
| relay | `ack` | not async — some MCP clients expect async tools |
| relay | `inbox` | not async — some MCP clients expect async tools |
| relay | `post` | not async — some MCP clients expect async tools |
| relay | `status` | not async — some MCP clients expect async tools |
| sync | `*` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `/api/health` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `add_channel` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `admin` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `audit_pair` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `check_deploy` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `complete_deploy` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `evaluate_triggers` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `get_triggers` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `identify_agent` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `info` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `list_artifacts` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `list_channels` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_alert` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_audit` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_can_call` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_compare` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_dashboard` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_diff` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_export` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_federation_proxy` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_federation_register` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_federation_sync` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_history` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_promote` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_quarantine` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_recommend` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_search` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_subscribe` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_subscriptions` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_trends` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_unsubscribe` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `marketplace_whoami` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `notify` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `pair_fire` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `pair_register` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `pair_status` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `pair_stop` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `read_artifact` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_ack` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_classify_skip` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_clear` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_event_stats` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_inbox` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_listen` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_log_event` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_poll_start` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_poll_status` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_poll_stop` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_post` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_skip_review` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_status` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `relay_wait` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `saturation_baselines` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `saturation_check` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `shared_list` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `shared_read` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `shared_write` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `smoke_test` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `start_deploy_poll` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `sync_auto` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `sync_now` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `sync_resolve` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `sync_status` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `test_channel` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `trigger_agent` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| sync | `write_artifact` | not async — some MCP clients expect async tools; references "claude" in logic — may not be client-agnostic |
| tasks | `add` | not async — some MCP clients expect async tools |
| tasks | `claim` | not async — some MCP clients expect async tools |
| tasks | `context_switch` | not async — some MCP clients expect async tools |
| tasks | `context_switch_reset` | not async — some MCP clients expect async tools |
| tasks | `context_switch_status` | not async — some MCP clients expect async tools |
| tasks | `create` | not async — some MCP clients expect async tools |
| tasks | `depth_map` | not async — some MCP clients expect async tools |
| tasks | `depth_pop` | not async — some MCP clients expect async tools |
| tasks | `depth_push` | not async — some MCP clients expect async tools |
| tasks | `depth_reset` | not async — some MCP clients expect async tools |
| tasks | `depth_set_max` | not async — some MCP clients expect async tools |
| tasks | `depth_show` | not async — some MCP clients expect async tools |
| tasks | `escalate` | not async — some MCP clients expect async tools |
| tasks | `get_next` | not async — some MCP clients expect async tools |
| tasks | `import_jsonl` | not async — some MCP clients expect async tools |
| tasks | `list` | not async — some MCP clients expect async tools |
| tasks | `update` | not async — some MCP clients expect async tools |

### Warning Categories

| Warning | Count |
|---------|-------|
| not async — some MCP clients expect async tools | 126 |
| references "claude" in logic — may not be client-agnostic | 67 |

## Fire-Without-Thinking (Zero-Config) Details

**218/218 actions return a useful response when called with empty action + empty params.**
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
