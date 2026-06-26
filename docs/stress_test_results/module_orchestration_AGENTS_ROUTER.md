# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T08:59:30
**Total tests:** 140
**Actions tested:** 20
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 64 | 45.7% | Tool returned a successful response |
| ⚠️ handled | 76 | 54.3% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **140** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 16 | 80.0% |
| ⚠️ handled | 4 | 20.0% |
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
| ✅ pass | 14 | 70.0% |
| ⚠️ handled | 6 | 30.0% |
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

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

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
- *Result preview:* `{"error": "Failed: Expecting value: line 1 column 1 (char 0)"}`

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
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 08:56:44
════════════════════════════════════════════════════════════

📊 AGENT POOL HEALTH
────────────────────────────────────────
   ├── Active: 0/0 
   ├── Idle:`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 08:56:44
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
- *Result preview:* `🚀 NOP Status Dashboard - 2026-06-26 08:56:44
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
- *Result preview:* `✅ Task handed off to shared queue. ID: task-2a0f2bf2`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'handoff_task': register.<locals>._h_handoff_task() missing 1 required positional argument: 'task_description'",
  "expected_params": "(task_description, target`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Task handed off for session wrong_ty. ID: task-6325e76f`

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
   snap_1782444170_deebf5: Snapshot 2026-06-26T03:22:50Z (2026-06-26T03:22:50Z)
   snap_1782444170_aa68ca: wrong_type (2026-06-26T03:22:5`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782444170_deebf5: Snapshot 2026-06-26T03:22:50Z (2026-06-26T03:22:50Z)
   snap_1782444170_aa68ca: wrong_type (2026-06-26T03:22:5`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ List snapshots error: slice indices must be integers or None or have an __index__ method`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `📸 Dashboard Snapshots
========================================
   snap_1782444170_deebf5: Snapshot 2026-06-26T03:22:50Z (2026-06-26T03:22:50Z)
   snap_1782444170_aa68ca: wrong_type (2026-06-26T03:22:5`

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

### 👥 Active Sessions (3)
- `test`: test
- `null`: None
- `wrong_ty`: wrong_type

### 📌 Pending (79)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (3)
- `test`: test
- `null`: None
- `wrong_ty`: wrong_type

### 📌 Pending (79)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (3)
- `test`: test
- `null`: None
- `wrong_ty`: wrong_type

### 📌 Pending (79)
- 🟡 test
- 🟡 @wrong_ty: wrong_type
- 🟡 test
- 🟡 test
- 🟡 test`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📋 Session Briefing

### 👥 Active Sessions (3)
- `test`: test
- `null`: None
- `wrong_ty`: wrong_type

### 📌 Pending (79)
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
   ID: snap_1782444411_7c8e2d
   Name: Snapshot 2026-06-26T03:26:51Z
   Timestamp: 2026-06-26T03:26:51Z
   
💡 To compare: brain_compare_dashboards('snap_1782444411_7c8e2d', 'other_s`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782444411_442e6a
   Name: Snapshot 2026-06-26T03:26:51Z
   Timestamp: 2026-06-26T03:26:51Z
   
💡 To compare: brain_compare_dashboards('snap_1782444411_442e6a', 'other_s`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782444411_3d8257
   Name: wrong_type
   Timestamp: 2026-06-26T03:26:51Z
   
💡 To compare: brain_compare_dashboards('snap_1782444411_3d8257', 'other_snapshot_id')`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ Snapshot Created
   ID: snap_1782444411_09a0fd
   Name: Snapshot 2026-06-26T03:26:51Z
   Timestamp: 2026-06-26T03:26:51Z
   
💡 To compare: brain_compare_dashboards('snap_1782444411_09a0fd', 'other_s`

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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**20/20 actions return a useful response across 5 confused-LLM scenarios.**
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
