# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T06:05:36
**Total tests:** 266
**Actions tested:** 38
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 100 | 37.6% | Tool returned a successful response |
| ⚠️ handled | 166 | 62.4% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **266** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 20 | 52.6% |
| ⚠️ handled | 18 | 47.4% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 21 | 55.3% |
| ⚠️ handled | 17 | 44.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 38 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **38** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 21 | 55.3% |
| ⚠️ handled | 17 | 44.7% |
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

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

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
        "timestamp": "2026-06-25T18:47:16.577085Z",
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
        "timestamp": "2026-06-25T18:47:16.577085Z",
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
        "timestamp": "2026-06-25T18:47:16.577085Z",
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
    "total_cost_units": 193.8,
    "total_interactions": 1938,
    "breakdown": {
      "unknown": {
        "cost": 96.9,
        "count": 969,
        "tier": 1
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_cost_units": 193.8,
    "total_interactions": 1938,
    "breakdown": {
      "unknown": {
        "cost": 96.9,
        "count": 969,
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
    "total_cost_units": 193.8,
    "total_interactions": 1938,
    "breakdown": {
      "unknown": {
        "cost": 96.9,
        "count": 969,
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
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Friday\n=================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Friday\n=================`

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
    "formatted": "============================================================\n\ud83d\udd04 COMPOUNDING LOOP STATUS [STALLING]\n   Week 26 | Friday\n=================`

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
        "id": "brief_34043",
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
        "id": "brief_34043",
        "context": "Strategy",
        "intensity": 3
      },
      {
        "id": "growth_hook_morning_brief_gen`

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
        "id": "brief_34043",
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
  "timestamp": "2026-06-26T`

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
  "error": "'str' object has no attribute 'name'"
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
  "error": "'str' object has no attribute 'name'"
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
    "timestamp": "2026-06-26T00:34:06.492030+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 2.8,
    "formatt`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "timestamp": "2026-06-26T00:34:06.841998+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 8.8,
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
    "timestamp": "2026-06-26T00:34:08.364130+00:00",
    "triggers": [],
    "trigger_count": 0,
    "should_notify": false,
    "check_duration_ms": 8.3,
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
    "total_executions": 834,
    "outcomes": {
      "ADD": 129,
      "NOOP": 272,
      "UNKNOWN": 260,
      "UPDATE": 173
    },
    "by_event_type": {
      "morn`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "total_executions": 834,
    "outcomes": {
      "ADD": 129,
      "NOOP": 272,
      "UNKNOWN": 260,
      "UPDATE": 173
    },
    "by_event_type": {
      "morn`

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
    "total_executions": 834,
    "outcomes": {
      "ADD": 129,
      "NOOP": 272,
      "UNKNOWN": 260,
      "UPDATE": 173
    },
    "by_event_type": {
      "morn`

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
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 06:04 AM\n====================`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 06:04 AM\n====================`

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
    "brief": "============================================================\n\ud83e\udde0 NUCLEUS MORNING BRIEF\n   Friday, June 26, 2026 06:04 AM\n====================`

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
# Generated at 2026-06-26T00:34:08.411249+00:00

# HELP nucleus_tool_calls_total Total number of tool calls
# TYPE nucleus_tool_calls_total counter

# HELP nucleus_tool_er`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `# Nucleus MCP Server Metrics
# Generated at 2026-06-26T00:34:08.411623+00:00

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
# Generated at 2026-06-26T00:34:08.411959+00:00

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
        "value": "RECURRING PATTERN (86x): Behind pace: github_issues at 0.0% of target",
        "contex`

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
        "value": "RECURRING PATTERN (86x): Behind pace: github_issues at 0.0% of target",
        "contex`

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
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (86x): Behind pace: github_issues at 0.0% o`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (86x): Behind pace: github_issues at 0.0% o`

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
    "context": "=== SESSION START CONTEXT ===\n\n\ud83d\udcdd KEY MEMORIES:\n  \u2022 recurring_38a2326e: RECURRING PATTERN (86x): Behind pace: github_issues at 0.0% o`

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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**38/38 actions return a useful response when called with empty action + empty params.**
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
