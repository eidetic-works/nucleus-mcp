# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T06:05:36
**Total tests:** 140
**Actions tested:** 20
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 39 | 27.9% | Tool returned a successful response |
| ⚠️ handled | 101 | 72.1% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **140** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 25.0% |
| ⚠️ handled | 15 | 75.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 35.0% |
| ⚠️ handled | 13 | 65.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 20 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 35.0% |
| ⚠️ handled | 13 | 65.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 20 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 20 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 20 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **20** | **100%** |

## Per-Module Breakdown

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
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 06:04:09
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 06:04:09
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
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 06:04:09
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
   snap_1782413222_d044cc: Snapshot 2026-06-25T18:47:02Z (2026-06-25T18:47:02Z)
   snap_1782413222_64af5c: Snapshot 2026-06-25T18:47:02Z `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782413222_d044cc: Snapshot 2026-06-25T18:47:02Z (2026-06-25T18:47:02Z)
   snap_1782413222_64af5c: Snapshot 2026-06-25T18:47:02Z `

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
   snap_1782413222_d044cc: Snapshot 2026-06-25T18:47:02Z (2026-06-25T18:47:02Z)
   snap_1782413222_64af5c: Snapshot 2026-06-25T18:47:02Z `

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
   ID: snap_1782434053_c3aaf0
   Name: Snapshot 2026-06-26T00:34:13Z
   Timestamp: 2026-06-26T00:34:13Z
   
💡 To compare: brain_compare_dashboards('snap_1782434053_c3aaf0', 'other_s`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782434053_351c2f
   Name: Snapshot 2026-06-26T00:34:13Z
   Timestamp: 2026-06-26T00:34:13Z
   
💡 To compare: brain_compare_dashboards('snap_1782434053_351c2f', 'other_s`

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
   ID: snap_1782434053_764915
   Name: Snapshot 2026-06-26T00:34:13Z
   Timestamp: 2026-06-26T00:34:13Z
   
💡 To compare: brain_compare_dashboards('snap_1782434053_764915', 'other_s`

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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**20/20 actions return a useful response when called with empty action + empty params.**
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
