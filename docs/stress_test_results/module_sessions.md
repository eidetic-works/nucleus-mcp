# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:43:52
**Total tests:** 182
**Actions tested:** 26
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 71 | 39.0% | Tool returned a successful response |
| ⚠️ handled | 111 | 61.0% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **182** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 13 | 50.0% |
| ⚠️ handled | 13 | 50.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 16 | 61.5% |
| ⚠️ handled | 10 | 38.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 26 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 16 | 61.5% |
| ⚠️ handled | 10 | 38.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 26 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 26 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 26 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **26** | **100%** |

## Per-Module Breakdown

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
    "summary": "Session ended (neutral): 27 tasks done, 1 tasks created, 829 total events",
    "activity": {
      "total_events": 829,
      "ta`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "success": true,
    "summary": "Session ended (neutral): 27 tasks done, 1 tasks created, 836 total events",
    "activity": {
      "total_events": 836,
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
    "summary": "Session ended (neutral): 27 tasks done, 1 tasks created, 842 total events",
    "activity": {
      "total_events": 842,
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
    "duration_ms": 234
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
    "duration_ms": 205
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
    "duration_ms": 180
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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**26/26 actions return a useful response when called with empty action + empty params.**
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
