# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T10:17:51
**Total tests:** 266
**Actions tested:** 38
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 161 | 60.5% | Tool returned a successful response |
| ⚠️ handled | 105 | 39.5% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **266** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 37 | 97.4% |
| ⚠️ handled | 1 | 2.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 29 | 76.3% |
| ⚠️ handled | 9 | 23.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 28 | 73.7% |
| ⚠️ handled | 10 | 26.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 29 | 76.3% |
| ⚠️ handled | 9 | 23.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 38 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### fire_without_thinking

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 38 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 38 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

## Per-Module Breakdown

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
| `list_decisions` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_snapshots` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `list_tools` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `metering_summary` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
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
        "timestamp": "2026-06-26T04:42:26.175838Z",
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
        "timestamp": "2026-06-26T04:42:26.175838Z",
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
  "timestamp": "2026-06-26T04:42:26.185643Z"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "entries": [
      {
        "timestamp": "2026-06-26T04:42:26.175838Z",
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
    "total_cost_units": 6.6,
    "total_interactions": 66,
    "breakdown": {
      "unknown": {
        "cost": 3.3,
        "count": 33,
        "tier": 1
      },
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 6.6,
    "total_interactions": 66,
    "breakdown": {
      "unknown": {
        "cost": 3.3,
        "count": 33,
        "tier": 1
      },
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
    "total_cost_units": 6.6,
    "total_interactions": 66,
    "breakdown": {
      "unknown": {
        "cost": 3.3,
        "count": 33,
        "tier": 1
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

#### `engrams.compounding_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [DECAYING]\n   Week 26 | Friday\n=================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [DECAYING]\n   Week 26 | Friday\n=================`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [DECAYING]\n   Week 26 | Friday\n=================`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [DECAYING]\n   Week 26 | Friday\n=================`

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
        "id": "growth_hook_morning_brief_generated_48946",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "growth_hook_morning_brief_generated_48946",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": `

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
        "id": "growth_hook_morning_brief_generated_48946",
        "context": "Strategy",
        "intensity": 5
      },
      {
        "id": `

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
  "timestamp": "2026-06-26T04:42:26.275107Z"
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
  "timestamp": "2026-06-26T04:42:26.275866Z"
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
    "decisions": [],
    "count": 0,
    "message": "No decisions found. DSoR ledger is empty."
  },
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-26T`

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
  "timestamp": "2026-06-26T`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "An internal error occurred. Error ID: 68211b45",
  "error_code": null,
  "timestamp": "2026-06-26T04:42:26.279074Z"
}`

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
  "timestamp": "2026-06-26T`

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
        "status": "READY",
        "total": 0
      },
      "snapshots":`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "READY",
        "total": 0
      },
      "snapshots":`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "READY",
        "total": 0
      },
      "snapshots":`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "version": "0.6.0",
    "feature": "DSoR",
    "components": {
      "decision_ledger": {
        "status": "READY",
        "total": 0
      },
      "snapshots":`

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
        "id": "growth_hook_morning_brief_ge`

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
    "node_count": 10
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
    "timestamp": "2026-06-26T10:12:26.332711",
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
  "uptime_seconds": 4,
  "python_version": "3.14.4"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 4,
  "python_version": "3.14.4"
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 4,
  "python_version": "3.14.4"
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "healthy",
  "version": "1.2.1",
  "tools_registered": "unknown",
  "brain_path": "/tmp/test-brain",
  "uptime_seconds": 4,
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
    "timestamp": "2026-06-26T04:42:31.325759+00:00",
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
    "timestamp": "2026-06-26T04:42:31.699350+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 15.3,
    "format`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T04:42:33.074070+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 0.3,
    "formatt`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T04:42:33.576173+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 2.7,
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "installed": true,
    "platform": {
      "platform": "macOS",
      "plist_path": "/home/operator/Library/LaunchAgents/dev.nucleusos.heartbeat.plist",
      "`

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
    "total_executions": 19,
    "outcomes": {
      "ADD": 4,
      "NOOP": 9,
      "UNKNOWN": 6
    },
    "by_event_type": {
      "morning_brief_generated": {
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 19,
    "outcomes": {
      "ADD": 4,
      "NOOP": 9,
      "UNKNOWN": 6
    },
    "by_event_type": {
      "morning_brief_generated": {
    `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 19,
    "outcomes": {
      "ADD": 4,
      "NOOP": 9,
      "UNKNOWN": 6
    },
    "by_event_type": {
      "morning_brief_generated": {
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 19,
    "outcomes": {
      "ADD": 4,
      "NOOP": 9,
      "UNKNOWN": 6
    },
    "by_event_type": {
      "morning_brief_generated": {
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

#### `engrams.ipc_tokens`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [],
    "count": 0
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [],
    "count": 0
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [],
    "count": 0
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "tokens": [],
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

#### `engrams.list_decisions`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
    "count": 0
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
    "count": 0
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
    "count": 0
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "decisions": [],
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
    "total_entries": 0,
    "total_units": 0
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 0,
    "total_units": 0
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 0,
    "total_units": 0
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "total_entries": 0,
    "total_units": 0
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

#### `engrams.morning_brief`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 10:12 AM\n====================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 10:12 AM\n====================`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 10:12 AM\n====================`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 10:12 AM\n====================`

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
# Generated at 2026-06-26T04:42:33.855515+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-26T04:42:33.902985+00:00

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
# Generated at 2026-06-26T04:42:33.927193+00:00

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
    "timestamp": "2026-06-26T10:12:34.067901",
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
    "timestamp": "2026-06-26T10:12:34.087982",
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
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 sre_diagnosis_2026062`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 sre_diagnosis_2026062`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 sre_diagnosis_2026062`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 blockers_2026-06-26: w; r; o; n; g; _; t; y; p; e\n  \u2022 sre_diagnosis_2026062`

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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**38/38 actions return a useful response across 5 confused-LLM scenarios.**
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
