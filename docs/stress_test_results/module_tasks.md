# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T10:17:51
**Total tests:** 119
**Actions tested:** 17
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 55 | 46.2% | Tool returned a successful response |
| ⚠️ handled | 64 | 53.8% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **119** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 13 | 76.5% |
| ⚠️ handled | 4 | 23.5% |
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
| ✅ pass | 11 | 64.7% |
| ⚠️ handled | 6 | 35.3% |
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

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

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
| ✅ pass | 17 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **17** | **100%** |

## Per-Module Breakdown

### Module: `tasks` (17 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `claim` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `context_switch` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `context_switch_reset` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `context_switch_status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `create` | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 2 pass |
| `depth_map` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_pop` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_push` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_reset` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `depth_set_max` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `depth_show` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `escalate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_next` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `import_jsonl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `tasks.add`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-bbb85f1f",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, requi`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "DAG violation: task cannot block itself"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.claim`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'claim': register.<locals>._h_claim() missing 2 required positional arguments: 'task_id' and 'agent_id'",
  "expected_params": "(task_id, agent_id)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.context_switch`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_context": "test",
    "switch_count": 1,
    "max_switches": 5,
    "was_switch": true,
    "recent_contexts": [
      "test"
    ],
    "warning": null,
`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'context_switch': register.<locals>.<lambda>() missing 1 required positional argument: 'new_context'",
  "expected_params": "(new_context)",
  "provided_params"`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_context": "wrong_type",
    "switch_count": 2,
    "max_switches": 5,
    "was_switch": true,
    "recent_contexts": [
      "test",
      "wrong_type"
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.context_switch_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626101621"
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
    "session_id": "session-20260626101621"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626101621"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "message": "\u2705 Context switch counter reset. Fresh start!",
    "switch_count": 0,
    "session_id": "session-20260626101621"
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "status": "\ud83d\udfe2 FOCUSED",
    "switch_count": 0,
    "max_switches": 5,
    "unique_contexts": 0,
    "recent_contexts": [],
    "session_id": "session-202`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.create`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-ab9a2953",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'create': register.<locals>._h_add() missing 1 required positional argument: 'description'",
  "expected_params": "(description, priority=3, blocked_by=None, re`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "DAG violation: task cannot block itself"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_map`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "mermaid": "```mermaid\ngraph TD\n    ROOT((\ud83c\udfe0 START))\n    style ROOT fill:#ccffcc,stroke:#0a0\n```",
    "message": "You're at the root level. No explo`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_pop`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "Already at root level (depth 0). Nothing to pop.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_push`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 1,
    "max_safe_depth": 5,
    "topic": "test",
    "breadcrumbs": "test",
    "warning": null,
    "warning_level": "safe",
    "indicator": "[\`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_push': register.<locals>.<lambda>() missing 1 required positional argument: 'topic'",
  "expected_params": "(topic)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 2,
    "max_safe_depth": 5,
    "topic": "wrong_type",
    "breadcrumbs": "test \u2192 wrong_type",
    "warning": null,
    "warning_level": "saf`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_reset`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
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
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
  },
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "message": "\u2705 Depth reset to root level.",
    "indicator": "[\u2591\u2591\u2591\u2591\u2591]"
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_set_max`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "'<' not supported between instances of 'str' and 'int'"
  },
  "error": null
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'depth_set_max': register.<locals>.<lambda>() missing 1 required positional argument: 'max_depth'",
  "expected_params": "(max_depth)",
  "provided_params": []
`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "error": "'<' not supported between instances of 'str' and 'int'"
  },
  "error": null
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.depth_show`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
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
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
    "status": "\ud83d\udfe2 SAFE",
    "breadcrumbs": "(root)",
    "tree": "(At root level)",
    "indicator": "[\u25`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {
    "current_depth": 0,
    "max_safe_depth": 5,
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.escalate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'escalate': register.<locals>.<lambda>() missing 2 required positional arguments: 'task_id' and 'reason'",
  "expected_params": "(task_id, reason)",
  "provided`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "error": "Task not found"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.get_next`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-de8a692d",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_next': register.<locals>._h_get_next() missing 1 required positional argument: 'skills'",
  "expected_params": "(skills)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": {
    "id": "task-de8a692d",
    "description": "test",
    "status": "PENDING",
    "priority": 3,
    "blocked_by": [],
    "required_skills": [],
    "claimed_by": nu`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.import_jsonl`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "File not found: test"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'import_jsonl': register.<locals>._h_import() missing 1 required positional argument: 'jsonl_path'",
  "expected_params": "(jsonl_path, clear_existing=False, me`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "File not found: wrong_type"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.list`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
  `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
  `

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": true,
  "data": [],
  "error": null
}`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "task-de8a692d",
      "description": "test",
      "status": "PENDING",
      "priority": 3,
      "blocked_by": [],
      "required_skills": [],
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `tasks.update`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 2 required positional arguments: 'task_id' and 'updates'",
  "expected_params": "(task_id, updates)",
  "provide`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "Task not found"
}`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Confused-LLM) Details

**17/17 actions return a useful response across 5 confused-LLM scenarios.**
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
