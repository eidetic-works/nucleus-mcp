# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 112
**Actions tested:** 16
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 28 | 25.0% | Tool returned a successful response |
| ⚠️ handled | 84 | 75.0% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **112** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 2 | 12.5% |
| ⚠️ handled | 14 | 87.5% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 31.2% |
| ⚠️ handled | 11 | 68.8% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 16 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 5 | 31.2% |
| ⚠️ handled | 11 | 68.8% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 16 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 16 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 16 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **16** | **100%** |

## Per-Module Breakdown

### Module: `features` (16 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `add` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `discover_tools` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `generate_proof` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `get_proof` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `invoke_tool` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_mounted` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `list_proofs` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `mount_server` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `search` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `thanos_snap` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `traverse_mount` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `unmount_server` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `update` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `validate` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `features.add`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 6 required positional arguments: 'product', 'description', 'source', 'version', 'how_to_test', and 'expected_result'",`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 7 required positional arguments: 'product', 'name', 'description', 'source', 'version', 'how_to_test', and 'expected_r`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() got an unexpected keyword argument 'id'",
  "expected_params": "(product, name, description, source, version, how_to_test, exp`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'add': register.<locals>._h_add() missing 7 required positional arguments: 'product', 'name', 'description', 'source', 'version', 'how_to_test', and 'expected_r`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.discover_tools`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T15:51:14.831699Z"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T15:51:14.832923Z"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'discover_tools': register.<locals>._h_discover() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id=None)",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": {},
  "error": null,
  "error_code": null,
  "timestamp": "2026-06-25T15:51:14.833310Z"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.generate_proof`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, thinking=None, deployed_url=None`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'generate_proof': register.<locals>._h_gen_proof() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, thinking=None, depl`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.get`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "id",
    "query",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.get_proof`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "limit"
 `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id)",
  "provided_params": [
    "id",
    "q`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'get_proof': register.<locals>.<lambda>() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.invoke_tool`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id, tool_name, arguments={})",
  "provided_`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'invoke_tool': register.<locals>._h_invoke() missing 2 required positional arguments: 'server_id' and 'tool_name'",
  "expected_params": "(server_id, tool_name,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(product=None, status=None, tag=None)",
  "provided_para`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "features": [
    {
      "id": "smoke_test_feature",
      "name": "smoke_test_feature",
      "description": "Dry run test feature for smoke testing",
      "product": "nucleus",
      "source":`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(product=None, status=None, tag=None)",
  "provided_params"`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "features": [
    {
      "id": "smoke_test_feature",
      "name": "smoke_test_feature",
      "description": "Dry run test feature for smoke testing",
      "product": "nucleus",
      "source":`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list_mounted`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_mounted': register.<locals>._h_list_mounted() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.11/bin/python3.11",
      "args": [
        "<HOME>/ai-`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_mounted': register.<locals>._h_list_mounted() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "q`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": true,
  "data": [
    {
      "id": "stripe",
      "transport": "stdio",
      "command": "/opt/homebrew/opt/python@3.11/bin/python3.11",
      "args": [
        "<HOME>/ai-`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.list_proofs`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_proofs': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `[
  "smoke_test_feature.md",
  "verification_test_feature.md",
  "qa_swarm_test_feature.md",
  "crisis_detection.md",
  "test_feature.md"
]`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_proofs': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `[
  "smoke_test_feature.md",
  "verification_test_feature.md",
  "qa_swarm_test_feature.md",
  "crisis_detection.md",
  "test_feature.md"
]`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.mount_server`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
  `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() got an unexpected keyword argument 'id'",
  "expected_params": "(name, command, args=[])",
  "provided_params": [
 `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'mount_server': register.<locals>._h_mount() missing 2 required positional arguments: 'name' and 'command'",
  "expected_params": "(name, command, args=[])",
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.search`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(query)",
  "provided_params": [
    "query",
    "lim`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(query)",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'search': register.<locals>.<lambda>() missing 1 required positional argument: 'query'",
  "expected_params": "(query)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.thanos_snap`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'thanos_snap': register.<locals>._h_thanos() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `✨ Thanos Snap Sequence:
Stripe: Connected ✅
Postgres: Connected ✅
Search: Connected ✅`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.traverse_mount`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() got an unexpected keyword argument 'id'",
  "expected_params": "(root_mount_id)",
  "provided_params": [
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'traverse_mount': register.<locals>._h_traverse() missing 1 required positional argument: 'root_mount_id'",
  "expected_params": "(root_mount_id)",
  "provided_`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.unmount_server`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() got an unexpected keyword argument 'id'",
  "expected_params": "(server_id)",
  "provided_params": [
    "id",
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'unmount_server': register.<locals>._h_unmount() missing 1 required positional argument: 'server_id'",
  "expected_params": "(server_id)",
  "provided_params": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.update`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, status=None, description=None, version=None`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, status=None, description=None,`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, status=None, description=None, version=None`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update': register.<locals>._h_update() missing 1 required positional argument: 'feature_id'",
  "expected_params": "(feature_id, status=None, description=None,`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `features.validate`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(feature_id, result)",
  "provided_params": [
    "id",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'validate': register.<locals>.<lambda>() missing 2 required positional arguments: 'feature_id' and 'result'",
  "expected_params": "(feature_id, result)",
  "pr`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_features",
  "available_actions": [
    "add",
    "discover_tools",
    "generate_proof",
    "get",
    "get_proof",
    "invoke_tool",
    "list",
    `

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**16/16 actions return a useful response when called with empty action + empty params.**
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
