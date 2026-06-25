# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T23:16:16
**Total tests:** 84
**Actions tested:** 12
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 37 | 44.0% | Tool returned a successful response |
| ⚠️ handled | 47 | 56.0% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **84** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 58.3% |
| ⚠️ handled | 5 | 41.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 9 | 75.0% |
| ⚠️ handled | 3 | 25.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 12 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 9 | 75.0% |
| ⚠️ handled | 3 | 25.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 12 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 12 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 12 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **12** | **100%** |

## Per-Module Breakdown

### Module: `orchestration.INFRA_ROUTER` (12 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `capture_metrics` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `file_changes` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `gcloud_services` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `gcloud_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `growth_pulse` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_services` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `manage_strategy` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `optimize_workflow` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `scan_marketing_log` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `status_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `synthesize_strategy` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `update_roadmap` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `orchestration.INFRA_ROUTER.capture_metrics`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:29.851116+00:00"
  },
  "pypi": {
    "error": `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:30.728479+00:00"
  },
  "pypi": {
    "error": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'capture_metrics': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(write_engram=True)",
  "provided_params": [
   `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "github": {
    "stars": 3,
    "forks": 3,
    "open_issues": 0,
    "watchers": 1,
    "source": "github_api",
    "fetched_at": "2026-06-25T17:45:31.738232+00:00"
  },
  "pypi": {
    "last_mon`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.file_changes`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'file_changes': register.<locals>._h_file_changes() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "q`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{"status": "degraded", "event_count": 0, "events": []}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.gcloud_services`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'gcloud_services': register.<locals>._h_gcloud_services() got an unexpected keyword argument 'id'",
  "expected_params": "(project=None, region='us-central1')",`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "success": false,
  "data": null,
  "error": "API [run.googleapis.com] not enabled on project [gentlequest-prod]. Would you \nlike to enable and retry (this will take a few minutes)? (y/N)?  \nERR`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.gcloud_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'gcloud_status': register.<locals>._h_gcloud_status() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "gcloud_available": true,
  "gcloud_path": "/opt/homebrew/bin/gcloud",
  "project": "gentlequest-prod",
  "account": "operator@example.com"
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.growth_pulse`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-25T17:45:40.359908+00:00",
  "sections": {
    "brief": {
      "engram_count": 52,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-25T17:45:41.311657+00:00",
  "sections": {
    "brief": {
      "engram_count": 57,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'growth_pulse': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(write_engrams=True)",
  "provided_params": [
    "`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "pipeline": "growth_pulse",
  "timestamp": "2026-06-25T17:45:42.363186+00:00",
  "sections": {
    "brief": {
      "engram_count": 62,
      "task_count": 0,
      "recommendation": "BOOTSTRAP"
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.list_services`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_services': register.<locals>._h_list_services() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_services': register.<locals>._h_list_services() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "mock": true,
  "message": "Render API Key not found or call failed. Showing MOCK data.",
  "error_detail": null,
  "items": [
    {
      "service": {
        "id": "srv-mock-1",
        "name": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.manage_strategy`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() got an unexpected keyword argument 'id'",
  "expected_params": "(action, content=None)",
  "provided_p`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'manage_strategy': register.<locals>._h_manage_strategy() missing 1 required positional argument: 'action'",
  "expected_params": "(action, content=None)",
  "p`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.optimize_workflow`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'optimize_workflow': register.<locals>._h_optimize_workflow() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "i`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.scan_marketing_log`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'scan_marketing_log': register.<locals>._h_scan_marketing_log() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'scan_marketing_log': register.<locals>._h_scan_marketing_log() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "healthy",
  "failure_count": 0,
  "failures": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.status_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'status_report': register.<locals>._h_status_report() got an unexpected keyword argument 'id'",
  "expected_params": "(focus='roadmap')",
  "provided_params": [`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.synthesize_strategy`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'synthesize_strategy': register.<locals>._h_synthesize_strategy() got an unexpected keyword argument 'id'",
  "expected_params": "(focus_topic=None)",
  "provid`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `❌ Failed: GEMINI_API_KEY not found in environment`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `orchestration.INFRA_ROUTER.update_roadmap`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() got an unexpected keyword argument 'id'",
  "expected_params": "(action, item=None)",
  "provided_params`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() missing 1 required positional argument: 'action'",
  "expected_params": "(action, item=None)",
  "provid`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() got an unexpected keyword argument 'id'",
  "expected_params": "(action, item=None)",
  "provided_params`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'update_roadmap': register.<locals>._h_update_roadmap() missing 1 required positional argument: 'action'",
  "expected_params": "(action, item=None)",
  "provid`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pul`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_infra",
  "available_actions": [
    "capture_metrics",
    "file_changes",
    "gcloud_services",
    "gcloud_status",
    "growth_pulse",
    "list_serv`

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**12/12 actions return a useful response when called with empty action + empty params.**
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
