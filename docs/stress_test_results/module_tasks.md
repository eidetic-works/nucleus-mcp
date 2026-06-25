# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 119
**Actions tested:** 17
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 18 | 15.1% | Tool returned a successful response |
| ⚠️ handled | 84 | 70.6% | Tool returned a graceful error (no crash) |
| 🔶 warn | 17 | 14.3% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **119** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 4 | 23.5% |
| ⚠️ handled | 13 | 76.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 41.2% |
| ⚠️ handled | 10 | 58.8% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 17 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 41.2% |
| ⚠️ handled | 10 | 58.8% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 17 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 17 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 17 | 100.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

## Per-Module Breakdown

### Module: `tasks` (17 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `claim` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `context_switch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `context_switch_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `context_switch_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `create` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_map` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `depth_pop` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `depth_push` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_reset` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `depth_set_max` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `depth_show` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `escalate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `get_next` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `import_jsonl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

#### `tasks.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'name'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=N`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=Non`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.claim`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, agent_id)",
  "provided_params": [
    "id",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.context_switch`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(new_context)",
  "provided_params": [
    "id",
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.context_switch_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260625212116"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260625212116"
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch_reset': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260625212116"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.context_switch_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.create`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() got an unexpected keyword argument 'name'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skill`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(description, priority=3, blocked_by=None, required_skills=`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_map`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_map': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "()",
  "provided_params": [
    "level"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_map': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
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
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_pop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_pop': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "()",
  "provided_params": [
    "level"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_pop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
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
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591]"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_push`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "(topic)",
  "provided_params": [
    "level"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(topic)",
  "provided_params": [
    "id",
    "query`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591]"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_reset': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
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
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591]"
  },
  "error": null
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_set_max`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() got an unexpected keyword argument 'level'",
  "expected_params": "(max_depth)",
  "provided_params": [
    "level`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(max_depth)",
  "provided_params": [
    "id",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.depth_show`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 3,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 3,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'depth_show': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
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
    "current_depth": 0,
    "max_safe_depth": 3,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.escalate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, reason)",
  "provided_params": [
    "id",
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.get_next`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() got an unexpected keyword argument 'limit'",
  "expected_params": "(skills)",
  "provided_params": [
    "limit"
  ]`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() got an unexpected keyword argument 'id'",
  "expected_params": "(skills)",
  "provided_params": [
    "id",
    "que`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.import_jsonl`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() got an unexpected keyword argument 'data'",
  "expected_params": "(jsonl_path, clear_existing=False, merge_gtm_met`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() got an unexpected keyword argument 'id'",
  "expected_params": "(jsonl_path, clear_existing=False, merge_gtm_metad`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>._h_list() got an unexpected keyword argument 'limit'",
  "expected_params": "(status=None, priority=None, skill=None, claimed_by=None)`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-7bdd42ef",
      "description": "v1.0.9 Sovereign Outreach Execution: Post 3 Reddit strikes (secithub, pwnhub, LocalLLaMA) using Comet Striker `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>._h_list() got an unexpected keyword argument 'id'",
  "expected_params": "(status=None, priority=None, skill=None, claimed_by=None)",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-7bdd42ef",
      "description": "v1.0.9 Sovereign Outreach Execution: Post 3 Reddit strikes (secithub, pwnhub, LocalLLaMA) using Comet Striker `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `tasks.update`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, updates)",
  "provided_params": [
    "id",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id, updates)",
  "provided_params": [
    "id",
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_tasks",
  "available_actions": [
    "add",
    "claim",
    "context_switch",
    "context_switch_reset",
    "context_switch_status",
    "create",
    `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

## Cross-Agent Compatibility Details

**17 actions have cross-agent compatibility warnings.**

| Module | Action | Warning |
|--------|--------|---------|
| tasks | `add` | not async — some MCP clients expect async tools |
| tasks | `claim` | not async — some MCP clients expect async tools |
| tasks | `context_switch` | not async — some MCP clients expect async tools |
| tasks | `context_switch_reset` | not async — some MCP clients expect async tools |
| tasks | `context_switch_status` | not async — some MCP clients expect async tools |
| tasks | `create` | not async — some MCP clients expect async tools |
| tasks | `depth_map` | not async — some MCP clients expect async tools |
| tasks | `depth_pop` | not async — some MCP clients expect async tools |
| tasks | `depth_push` | not async — some MCP clients expect async tools |
| tasks | `depth_reset` | not async — some MCP clients expect async tools |
| tasks | `depth_set_max` | not async — some MCP clients expect async tools |
| tasks | `depth_show` | not async — some MCP clients expect async tools |
| tasks | `escalate` | not async — some MCP clients expect async tools |
| tasks | `get_next` | not async — some MCP clients expect async tools |
| tasks | `import_jsonl` | not async — some MCP clients expect async tools |
| tasks | `list` | not async — some MCP clients expect async tools |
| tasks | `update` | not async — some MCP clients expect async tools |

### Warning Categories

| Warning | Count |
|---------|-------|
| not async — some MCP clients expect async tools | 17 |

## Fire-Without-Thinking (Zero-Config) Details

**17/17 actions return a useful response when called with empty action + empty params.**
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
