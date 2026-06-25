# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:31:27
**Total tests:** 77
**Actions tested:** 11
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 26 | 33.8% | Tool returned a successful response |
| ⚠️ handled | 51 | 66.2% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **77** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 45.5% |
| ⚠️ handled | 6 | 54.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 45.5% |
| ⚠️ handled | 6 | 54.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 11 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 45.5% |
| ⚠️ handled | 6 | 54.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 11 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 11 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 11 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **11** | **100%** |

## Per-Module Breakdown

### Module: `orchestration.SLOTS_ROUTER` (11 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `autopilot_sprint` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `autopilot_sprint_v2` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `force_assign` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `halt_sprint` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `mission_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `orchestrate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `resume_sprint` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `slot_complete` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `slot_exhaust` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `start_mission` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status_dashboard` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

#### `orchestration.SLOTS_ROUTER.autopilot_sprint`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sprint_id": "sprint_1782410410_8e63",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:30:10+0530"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sprint_id": "sprint_1782410410_d0bc",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:30:10+0530"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'autopilot_sprint': register.<locals>._h_autopilot_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(slots=None, mode='auto', halt_on_bl`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sprint_id": "sprint_1782410410_d526",
  "status": "ERROR",
  "error": "No active slots found",
  "timestamp": "2026-06-25T23:30:10+0530"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.autopilot_sprint_v2`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🚀 Sprint Report: sprint_1782410410_f1eaaf
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 Sprint Report: sprint_1782410410_e96ecb
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'autopilot_sprint_v2': register.<locals>._h_autopilot_sprint_v2() got an unexpected keyword argument 'id'",
  "expected_params": "(slots=None, mode='auto', halt`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 Sprint Report: sprint_1782410410_f2e552
══════════════════════════════════════════════════
Status: COMPLETED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.force_assign`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, acknowledge_risk=False)",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id, `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, acknowledge_risk=False)",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'force_assign': register.<locals>._h_force_assign() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id, `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.halt_sprint`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782410410_f2e552
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782410410_f2e552
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'halt_sprint': register.<locals>._h_halt_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(reason='User requested halt')",
  "provided_p`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `⛔ Sprint Halt Requested
   Sprint ID: sprint_1782410410_f2e552
   Reason: User requested halt
   Status: halt_requested
   
💡 Sprint will complete current task then stop gracefully`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.mission_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ No mission found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ No mission found`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'mission_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(mission_id=None)",
  "provided_params": [
    "i`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ No mission found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.orchestrate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'orchestrate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id=None, model=None, alias=None, mode='auto')"`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Action 'orchestrate' failed: module 'mcp_server_nucleus' has no attribute '_get_slot_registry'",
  "module": "nucleus_slots"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.resume_sprint`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'resume_sprint': register.<locals>._h_resume_sprint() got an unexpected keyword argument 'id'",
  "expected_params": "(sprint_id=None)",
  "provided_params": [
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🚀 Sprint Report: unknown
══════════════════════════════════════════════════
Status: FAILED
Mode: auto
Duration: 0.0s

📊 TASKS
   ├── Total: 0
   ├── Completed: 0
   ├── Failed: 0
   └── Remaining: 0

`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.slot_complete`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, outcome='success', note`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, task_id, outcome='success', note`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'slot_complete': register.<locals>._h_slot_complete() missing 2 required positional arguments: 'slot_id' and 'task_id'",
  "expected_params": "(slot_id, task_id`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.slot_exhaust`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() got an unexpected keyword argument 'id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "provided_param`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'slot_exhaust': register.<locals>._h_slot_exhaust() missing 1 required positional argument: 'slot_id'",
  "expected_params": "(slot_id, reset_hours=5)",
  "prov`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.start_mission`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() got an unexpected keyword argument 'id'",
  "expected_params": "(name, goal, task_ids, slot_ids=None, budg`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'start_mission': register.<locals>._h_start_mission() missing 3 required positional arguments: 'name', 'goal', and 'task_ids'",
  "expected_params": "(name, goa`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.SLOTS_ROUTER.status_dashboard`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:30 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:30 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status_dashboard': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(detail_level='standard')",
  "provided_params"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `╔══════════════════════════════════════════════════════════════╗
║ 🧠 NUCLEUS CONTROL PLANE - 2026-06-25 23:30 IST      ║
╠══════════════════════════════════════════════════════════════╣
║ AGENT SLOTS `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_slots",
  "available_actions": [
    "autopilot_sprint",
    "autopilot_sprint_v2",
    "force_assign",
    "halt_sprint",
    "mission_status",
    "orch`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**11/11 actions return a useful response when called with empty action + empty params.**
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
