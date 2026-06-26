# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T06:33:42
**Total tests:** 441
**Actions tested:** 63
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 116 | 26.3% | Tool returned a successful response |
| ⚠️ handled | 325 | 73.7% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **441** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 13 | 20.6% |
| ⚠️ handled | 50 | 79.4% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 20 | 31.7% |
| ⚠️ handled | 43 | 68.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 63 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 20 | 31.7% |
| ⚠️ handled | 43 | 68.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 63 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### fire_without_thinking

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 63 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 63 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **63** | **100%** |

## Per-Module Breakdown

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
| `relay_skip_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `relay_wait` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `saturation_baselines` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `saturation_check` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `shared_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `shared_read` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `shared_write` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `smoke_test` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start_deploy_poll` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_auto` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_now` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_resolve` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sync_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `test_channel` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'relay_listen': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(recipient, window_s=60, poll_s=5, in_reply_to=N`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_listen': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, window_s=60, poll_s=5, in_r`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_listen': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(recipient, window_s=60, poll_s=5, in_reply_to=None`

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
  "error": "Invalid params for action 'relay_log_event': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(event, side, subject, tags=None, match_reaso`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_log_event': register.<locals>.<lambda>() missing 3 required positional arguments: 'event', 'side', and 'subject'",
  "expected_params": "(event, side, su`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_log_event': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(event, side, subject, tags=None, match_reason='`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_start': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, interval_s=10, session_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_start': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient, interval_s=10, session_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_start': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(recipient, interval_s=10, session_id=None)",
 `

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_status': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params":`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_status': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(recipient)",
  "provided_params": [
    "id",`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params": [`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_stop': register.<locals>.<lambda>() missing 1 required positional argument: 'recipient'",
  "expected_params": "(recipient)",
  "provided_params": [`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_poll_stop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(recipient)",
  "provided_params": [
    "id",
 `

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
  "error": "Invalid params for action 'relay_post': register.<locals>.<lambda>() got an unexpected keyword argument 'message'",
  "expected_params": "(to, subject, body, priority='normal', context=N`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_post': register.<locals>.<lambda>() missing 3 required positional arguments: 'to', 'subject', and 'body'",
  "expected_params": "(to, subject, body, prio`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_post': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(to, subject, body, priority='normal', context=None, `

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
  "error": "Invalid params for action 'relay_skip_review': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(limit=20)",
  "provided_params": [
    "id",
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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'relay_wait': register.<locals>.<lambda>() missing 2 required positional arguments: 'in_reply_to' and 'recipient'",
  "expected_params": "(in_reply_to, recipien`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'relay_wait': register.<locals>.<lambda>() missing 2 required positional arguments: 'in_reply_to' and 'recipient'",
  "expected_params": "(in_reply_to, recipien`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'relay_wait': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(in_reply_to, recipient, timeout_s=60, poll_interval_`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'saturation_baselines': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(surface='main', window_size=100)",
  "prov`

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

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'saturation_check': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(surface='main', window_size=100, threshold_fac`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'shared_list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "keys": [],
  "count": 0
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'shared_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "keys": [],
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

#### `sync.shared_read`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'shared_read': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key)",
  "provided_params": [
    "id"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'shared_read': register.<locals>.<lambda>() missing 1 required positional argument: 'key'",
  "expected_params": "(key)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'shared_read': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key)",
  "provided_params": [
    "id",
    "query"`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'shared_write': register.<locals>.<lambda>() got an unexpected keyword argument 'content'",
  "expected_params": "(key, value, agent_id='')",
  "provided_params`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'shared_write': register.<locals>.<lambda>() missing 2 required positional arguments: 'key' and 'value'",
  "expected_params": "(key, value, agent_id='')",
  "p`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'shared_write': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(key, value, agent_id='')",
  "provided_params": [
`

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
  "error": "Invalid params for action 'smoke_test': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, endpoint='/api/health')",
  "provided_par`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'smoke_test': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, endpoint='/api/health')",
  "provided_par`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'smoke_test': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(url, endpoint='/api/health')",
  "provided_params": `

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'start_deploy_poll': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id, commit_sha=None)",
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'start_deploy_poll': register.<locals>.<lambda>() missing 1 required positional argument: 'service_id'",
  "expected_params": "(service_id, commit_sha=None)",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'start_deploy_poll': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(service_id, commit_sha=None)",
  "provided_pa`

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
  "error": "Invalid params for action 'sync_auto': register.<locals>._sync_auto() missing 1 required positional argument: 'enable'",
  "expected_params": "(enable)",
  "provided_params": []
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
  "error": "Invalid params for action 'sync_auto': register.<locals>._sync_auto() got an unexpected keyword argument 'id'",
  "expected_params": "(enable)",
  "provided_params": [
    "id",
    "que`

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
  "error": "Invalid params for action 'sync_now': register.<locals>._sync_now() got an unexpected keyword argument 'id'",
  "expected_params": "(force=False)",
  "provided_params": [
    "id",
    "`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'sync_resolve': register.<locals>._sync_resolve() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, strategy='last_write_w`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'sync_resolve': register.<locals>._sync_resolve() missing 1 required positional argument: 'file_path'",
  "expected_params": "(file_path, strategy='last_write_w`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sync_resolve': register.<locals>._sync_resolve() got an unexpected keyword argument 'id'",
  "expected_params": "(file_path, strategy='last_write_wins')",
  "p`

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
  "current_agent": "unknown_agent",
  "agent_info": {
    "agent_id": "unknown_agent",
    "environment": "unknown",
    "role": "wo`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "unknown_agent",
  "agent_info": {
    "agent_id": "unknown_agent",
    "environment": "unknown",
    "role": "wo`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sync_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sync_enabled": false,
  "mode": "manual",
  "last_sync": null,
  "current_agent": "unknown_agent",
  "agent_info": {
    "agent_id": "unknown_agent",
    "environment": "unknown",
    "role": "wo`

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
  "error": "Invalid params for action 'test_channel': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(channel_name=None)",
  "provided_params": [
    "i`

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'trigger_agent': register.<locals>.<lambda>() missing 2 required positional arguments: 'agent' and 'task_description'",
  "expected_params": "(agent, task_descr`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'trigger_agent': register.<locals>.<lambda>() missing 2 required positional arguments: 'agent' and 'task_description'",
  "expected_params": "(agent, task_descr`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trigger_agent': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(agent, task_description, context_files=None)",
  `

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

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'write_artifact': register.<locals>.<lambda>() got an unexpected keyword argument 'tags'",
  "expected_params": "(path, content)",
  "provided_params": [
    "c`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'write_artifact': register.<locals>.<lambda>() missing 2 required positional arguments: 'path' and 'content'",
  "expected_params": "(path, content)",
  "provid`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'write_artifact': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path, content)",
  "provided_params": [
    "id"`

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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**63/63 actions return a useful response across 5 confused-LLM scenarios.**
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
