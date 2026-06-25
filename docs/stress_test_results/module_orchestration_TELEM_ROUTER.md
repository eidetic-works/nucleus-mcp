# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:31:27
**Total tests:** 105
**Actions tested:** 15
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 44 | 41.9% | Tool returned a successful response |
| ⚠️ handled | 61 | 58.1% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **105** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 9 | 60.0% |
| ⚠️ handled | 6 | 40.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 10 | 66.7% |
| ⚠️ handled | 5 | 33.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 15 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 10 | 66.7% |
| ⚠️ handled | 5 | 33.3% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 15 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 15 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 15 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

## Per-Module Breakdown

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
  "total_dispatches": 720,
  "total_errors": 486,
  "error_rate": 0.675,
  "facades": {
    "nucleus_audit": {
      "calls": 20,
      "errors": 20
    },
    "nucleus_route": {
      "calls": 5,
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_dispatches": 721,
  "total_errors": 486,
  "error_rate": 0.6740638002773925,
  "facades": {
    "nucleus_audit": {
      "calls": 20,
      "errors": 20
    },
    "nucleus_route": {
      `

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
  "total_dispatches": 723,
  "total_errors": 487,
  "error_rate": 0.673582295988935,
  "facades": {
    "nucleus_audit": {
      "calls": 20,
      "errors": 20
    },
    "nucleus_route": {
      "`

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
    "nucleus_audit": 20,
    "nucleus_route": 5,
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_fe`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "enabled": true,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {
    "nucleus_audit": 20,
    "nucleus_route": 5,
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_fe`

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
    "nucleus_audit": 20,
    "nucleus_route": 5,
    "nucleus_engrams": 190,
    "nucleus_features": 80,
    "nucleus_fe`

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
**High Impact Closures:** 12
**Ratio:** None
**Verdict:** No notifications sent yet
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 12
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
**High Impact Closures:** 12
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

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**15/15 actions return a useful response when called with empty action + empty params.**
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
