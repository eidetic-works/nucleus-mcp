# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T07:23:15
**Total tests:** 49
**Actions tested:** 7
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 31 | 63.3% | Tool returned a successful response |
| ⚠️ handled | 18 | 36.7% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **49** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
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
| ✅ pass | 7 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
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

**What it tests:** 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly

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
| `health` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `join` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `leave` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `peers` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `route` | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `status` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |
| `sync` | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 5 pass |

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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✅ JOINED FEDERATION
   Seed Peer: http://localhost:9999
   Total Peers: 1

💡 Federation engine is now active and syncing`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'join': register.<locals>._h_join() missing 1 required positional argument: 'seed_peer'",
  "expected_params": "(seed_peer: str)",
  "provided_params": []
}`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Failed to join: argument of type 'int' is not a container or iterable`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode.`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `🔗 FEDERATION PEERS
═══════════════════════════════════════

🟢 peer_http://localhost_9999
   Address: http://localhost:9999
   Region: unknown
   Trust: 👤 MEMBER
   Latency: 0.0ms
   Load: 0%
   Capabi`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: test-id
📊 Profile: default

🏆 TARGET
   Brain: brain_test-brain
   Score: 0.630

⏱️ ROUTING TIME
   0.020ms

🔄 ALTERNATIVES
   1. pe`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'route': register.<locals>._h_route() missing 1 required positional argument: 'task_id'",
  "expected_params": "(task_id: str, profile: str = 'default')",
  "pr`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: 12345
📊 Profile: 12345

🏆 TARGET
   Brain: brain_test-brain
   Score: 0.630

⏱️ ROUTING TIME
   0.058ms

🔄 ALTERNATIVES
   1. peer_h`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

🔗 PEERS (1/`

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

🔗 PEERS (1/`

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
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

🔗 PEERS (1/`

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

🔗 PEERS (1/`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

**wrong_types** — ✅ pass
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `❌ Federation engine not running. Use brain_federation_join first.`

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
- *Tests:* 5 confused-LLM scenarios: empty action, None action, params-as-string, swapped args (dict as action), guessed action + garbage params — tests what happens when an LLM fires blindly
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

## Fire-Without-Thinking (Confused-LLM) Details

**7/7 actions return a useful response across 5 confused-LLM scenarios.**
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
