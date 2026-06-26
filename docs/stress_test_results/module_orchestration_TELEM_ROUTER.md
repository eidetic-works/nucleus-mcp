# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T12:30:27
**Total tests:** 105
**Actions tested:** 15
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 67 | 63.8% | Tool returned a successful response |
| ⚠️ handled | 38 | 36.2% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **105** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 15 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 11 | 73.3% |
| ⚠️ handled | 4 | 26.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 15 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **15** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 11 | 73.3% |
| ⚠️ handled | 4 | 26.7% |
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

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

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
| `agent_cost_dashboard` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `check_kill_switch` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `check_protocol` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `dispatch_metrics` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `get_handoffs` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `get_llm_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `mark_high_impact` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `pause_notifications` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `rate_limit_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `record_feedback` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `record_interaction` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `request_handoff` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `resume_notifications` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `set_llm_tier` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `value_ratio` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 🛑 Kill Switch Status (MDR_010)

**Action:** continue
**Message:** N/A
**Days Inactive:** 0
`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "compliant": true,
  "warnings": [
    "Protocol definition not found - assuming compliant"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'check_protocol': register.<locals>._h_check_protocol() missing 1 required positional argument: 'agent_id'",
  "expected_params": "(agent_id)",
  "provided_para`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "compliant": true,
  "warnings": [
    "Protocol definition not found - assuming compliant"
  ]
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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
  "total_dispatches": 1008,
  "total_errors": 544,
  "error_rate": 0.5396825396825397,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "total_dispatches": 1009,
  "total_errors": 544,
  "error_rate": 0.5391476709613479,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "total_dispatches": 1010,
  "total_errors": 544,
  "error_rate": 0.5386138613861386,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
      `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "total_dispatches": 1011,
  "total_errors": 544,
  "error_rate": 0.5380811078140455,
  "facades": {
    "nucleus_audit": {
      "calls": 28,
      "errors": 8
    },
    "nucleus_route": {
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
    `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
    `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-1354",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "wrong_type",
      "priority": "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "handoffs": [
    {
      "id": "handoff-1782449004-07db",
      "timestamp": "2026-06-26T10:13:24+0530",
      "from_agent": "current_session",
      "to_agent": "test",
      "priority": 3,
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 🧠 LLM Tier Status

**Current Tier:** auto (standard)
**Vertex Mode:** Disabled

No benchmark data available.
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Marked as high-impact closure. Value ratio updated.`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🛑 Notifications paused. Use brain_resume_notifications() to restart.`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "enabled": false,
  "max_calls": 200,
  "window_seconds": 60,
  "facades": {}
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `Error: '>=' not supported between instances of 'str' and 'int'`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'record_feedback': register.<locals>.<lambda>() missing 2 required positional arguments: 'notification_type' and 'score'",
  "expected_params": "(notification_t`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `Error: '>=' not supported between instances of 'str' and 'int'`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Interaction recorded`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: test
PRIORITY: P3
CONTEXT: test
REQUEST: test
ARTIFACTS: None
━━━━━━━━━━━━━━━━━━
ID: handoff-1782457000-d689
Status: Pending - will appear in target agent's s`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'request_handoff': register.<locals>._h_request_handoff() missing 3 required positional arguments: 'to_agent', 'context', and 'request'",
  "expected_params": "`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `
📬 HANDOFF REQUEST
━━━━━━━━━━━━━━━━━━
TO: wrong_type
PRIORITY: Pnot_a_number
CONTEXT: not_a_dict
REQUEST: wrong_type
ARTIFACTS: w, r, o, n, g, _, t, y, p, e
━━━━━━━━━━━━━━━━━━
ID: handoff-1782457000-7`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ Notifications resumed. Interaction recorded.`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Invalid tier 'test'. Valid tiers: premium, standard, economy, local_paid, local_free`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_llm_tier': register.<locals>._h_set_llm_tier() missing 1 required positional argument: 'tier'",
  "expected_params": "(tier)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Invalid tier 'wrong_type'. Valid tiers: premium, standard, economy, local_paid, local_free`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
**Ratio:** None
**Verdict:** No notifications sent yet
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `## 📊 Value Ratio (MDR_010)

**Notifications Sent:** 0
**High Impact Closures:** 20
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

## Fire-Without-Thinking (Confused-LLM) Details

**15/15 actions return a useful response across 5 confused-LLM scenarios.**
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
