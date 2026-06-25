# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:43:52
**Total tests:** 49
**Actions tested:** 7
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 22 | 44.9% | Tool returned a successful response |
| ⚠️ handled | 27 | 55.1% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **49** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 71.4% |
| ⚠️ handled | 2 | 28.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 71.4% |
| ⚠️ handled | 2 | 28.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 7 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 71.4% |
| ⚠️ handled | 2 | 28.6% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 7 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 7 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **7** | **100%** |

## Per-Module Breakdown

### Module: `federation` (7 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `health` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `join` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `leave` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `peers` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `route` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `sync` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |

#### `federation.health`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'health': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `💚 FEDERATION HEALTH
═══════════════════════════════════════

🟢 HEALTHY
[████████████████████] 100%

📊 PARTITION
   Status: NORMAL
   Peers Online: 0/0
   Leader: None

📈 METRICS
   Tasks Routed: 0
   `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.join`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() got an unexpected keyword argument 'id'",
  "expected_params": "(seed_peer: str)",
  "provided_params": [
    "id",
    "que`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.leave`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'leave': register.<locals>._h_leave() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "li`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.peers`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'peers': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "li`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.route`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() got an unexpected keyword argument 'id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "provided_par`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "l`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: brain_test-brain
   Region: default
   Running: ❌

👑 CONSENSUS
   Leader: None
   Is Leader: ❌
   Term: 0

🔗 PEERS (0/`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `federation.sync`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sync': register.<locals>._h_sync() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
    "limi`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ],
  `

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_federation",
  "available_actions": [
    "health",
    "join",
    "leave",
    "peers",
    "route",
    "status",
    "sync"
  ]
}`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**7/7 actions return a useful response when called with empty action + empty params.**
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
