# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 469
**Actions tested:** 67
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 24 | 5.1% | Tool returned a successful response |
| ⚠️ handled | 378 | 80.6% | Tool returned a graceful error (no crash) |
| 🔶 warn | 67 | 14.3% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **469** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 4 | 6.0% |
| ⚠️ handled | 63 | 94.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 10 | 14.9% |
| ⚠️ handled | 57 | 85.1% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 67 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 10 | 14.9% |
| ⚠️ handled | 57 | 85.1% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 67 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 67 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 67 | 100.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **67** | **100%** |

## Per-Module Breakdown

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

## Cross-Agent Compatibility Details

**67 actions have cross-agent compatibility warnings.**

| Module | Action | Warning |
|--------|--------|---------|
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

### Warning Categories

| Warning | Count |
|---------|-------|
| not async — some MCP clients expect async tools | 67 |
| references "claude" in logic — may not be client-agnostic | 67 |

## Fire-Without-Thinking (Zero-Config) Details

**67/67 actions return a useful response when called with empty action + empty params.**
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
