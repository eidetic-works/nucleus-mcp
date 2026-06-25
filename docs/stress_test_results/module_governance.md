# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-25T21:25:45
**Total tests:** 147
**Actions tested:** 21
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 18 | 12.2% | Tool returned a successful response |
| ⚠️ handled | 108 | 73.5% | Tool returned a graceful error (no crash) |
| 🔶 warn | 21 | 14.3% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **147** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 4 | 19.0% |
| ⚠️ handled | 17 | 81.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 33.3% |
| ⚠️ handled | 14 | 66.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 21 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 7 | 33.3% |
| ⚠️ handled | 14 | 66.7% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 21 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 21 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 21 | 100.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **21** | **100%** |

## Per-Module Breakdown

### Module: `governance` (21 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `GET` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `audit_report` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `auto_fix_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `comply_apply` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `comply_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `comply_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `curl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `delete_file` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `kyc_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `list_directory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `lock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `pip_install` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `set_mode` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `sovereign_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 3 pass |
| `strategic` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `trace_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `trace_view` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔶 | ✅ 2 pass |
| `unlock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `validate_strategic_plan` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |
| `watch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔶 | 🔶 1 warn |

#### `governance.GET`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'GET' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.audit_report`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(report_format='text', since_hours=None, brain_p`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': 'NoneType' object is not subscriptable",
  "expected_params": "(report_format='text', since_hours=None, brain_path=None)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(report_format='text', since_hours=None, brain_path`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': 'NoneType' object is not subscriptable",
  "expected_params": "(report_format='text', since_hours=None, brain_path=None)",
  "provided_params": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.auto_fix_loop`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(file_path, verification_command)",
  "provided_pa`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'auto_fix_loop': register.<locals>.<lambda>() missing 2 required positional arguments: 'file_path' and 'verification_command'",
  "expected_params": "(file_path`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.comply_apply`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(jurisdiction, brain_path=None)",
  "provided_param`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'comply_apply': register.<locals>.<lambda>() missing 1 required positional argument: 'jurisdiction'",
  "expected_params": "(jurisdiction, brain_path=None)",
  `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.comply_list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'comply_list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "()",
  "provided_params": [
    "limit"
  ]
}`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "()",
  "provided_params": [
    "id",
    "query",
 `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "eu-dora": "EU DORA (Digital Operational Resilience Act)",
  "sg-mas-trm": "Singapore MAS TRM (Technology Risk Management)",
  "us-soc2": "SOC2 Type II",
  "global-default": "Global Default (Best `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.comply_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'comply_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(brain_path=None)",
  "provided_params": [
    "id`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "status": "compliant",
  "checks": {
    "jurisdiction": {
      "status": "configured",
      "id": "eu-dora",
      "name": "EU DORA (Digital Operational Resilience Act)",
      "applied_at": "2`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.curl`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(url, method='GET')",
  "provided_params": [
    "id",
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'curl': register.<locals>.<lambda>() missing 1 required positional argument: 'url'",
  "expected_params": "(url, method='GET')",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.delete_file`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path, confirm=False)",
  "provided_params": [
    "`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path, confirm=False)",
  "provided_params": `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path, confirm=False)",
  "provided_params": [
    "`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'delete_file': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path, confirm=False)",
  "provided_params": `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.kyc_review`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "review_id": "KYC-FB808C52",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.053345+00:00",
  "completed_at": "2026-06-25T15:51:15.053378+00:00",
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "review_id": "KYC-7ADC7FAB",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.054532+00:00",
  "completed_at": "2026-06-25T15:51:15.054556+00:00",
 `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'kyc_review': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(application_id='APP-001', brain_path=None)",
  "prov`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "review_id": "KYC-C47AAE33",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T15:51:15.055940+00:00",
  "completed_at": "2026-06-25T15:51:15.055964+00:00",
 `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.list_directory`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(path)",
  "provided_params": [
    "limit"
  `

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "qu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'list_directory': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.lock`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
    `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'lock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.pip_install`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(package)",
  "provided_params": [
    "id",
    "qu`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'pip_install': register.<locals>.<lambda>() missing 1 required positional argument: 'package'",
  "expected_params": "(package)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.set_mode`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(mode)",
  "provided_params": [
    "id",
    "query",
`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'set_mode': register.<locals>.<lambda>() missing 1 required positional argument: 'mode'",
  "expected_params": "(mode)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.sovereign_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'sovereign_status': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(brain_path=None)",
  "provided_params": [
    `

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "sovereignty_score": 100,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: <BRAIN_PATH>
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: <BRAIN_PATH>
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

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
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: <BRAIN_PATH>
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.strategic`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Unknown action 'strategic' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.trace_list`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_p`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "count": 99,
  "traces": [
    {
      "file": "KYC-0247F068.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0247F068",
      "recommendation": "REJECT",
      "risk_score": 175,
      `

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_para`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "count": 99,
  "traces": [
    {
      "file": "KYC-0247F068.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0247F068",
      "recommendation": "REJECT",
      "risk_score": 175,
      `

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.trace_view`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'trace_view': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_id='', brain_path=None)",
  "provided_params":`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-74E5C72F",
  "application_id": "APP-003",
  "applicant": "Dmitri Volkov",
  "started_at": "2026-03-03T08:21:57.981452Z",
  "completed_at": "2026-03-03T08:`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_view': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_id='', brain_path=None)",
  "provided_params":`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "type": "KYC_REVIEW",
  "review_id": "KYC-74E5C72F",
  "application_id": "APP-003",
  "applicant": "Dmitri Volkov",
  "started_at": "2026-03-03T08:21:57.981452Z",
  "completed_at": "2026-03-03T08:`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.unlock`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
  `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'unlock': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.validate_strategic_plan`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(plan_text, mode='strategic')",
  "provi`

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'validate_strategic_plan': register.<locals>.<lambda>() missing 1 required positional argument: 'plan_text'",
  "expected_params": "(plan_text, mode='strategic'`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

#### `governance.watch`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**missing_params** — ⚠️ handled
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(path)",
  "provided_params": [
    "id",
    "query",
   `

**empty_params** — ⚠️ handled
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "error": "Invalid params for action 'watch': register.<locals>.<lambda>() missing 1 required positional argument: 'path'",
  "expected_params": "(path)",
  "provided_params": []
}`

**unknown_action** — ⚠️ handled
- *Tests:* Action name that does not exist in this tool's ROUTER — tests error handling for typos
- *Result preview:* `{
  "error": "Unknown action '__nonexistent_action__' in nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_repor`

**fire_without_thinking** — ⚠️ handled
- *Tests:* Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly
- *Result preview:* `{
  "error": "No action specified for nucleus_governance",
  "available_actions": [
    "audit_report",
    "auto_fix_loop",
    "comply_apply",
    "comply_list",
    "comply_report",
    "curl",
   `

**cross_agent_compat** — 🔶 warn
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *Error:* `not async — some MCP clients expect async tools`

---

## Cross-Agent Compatibility Details

**21 actions have cross-agent compatibility warnings.**

| Module | Action | Warning |
|--------|--------|---------|
| governance | `GET` | not async — some MCP clients expect async tools |
| governance | `audit_report` | not async — some MCP clients expect async tools |
| governance | `auto_fix_loop` | not async — some MCP clients expect async tools |
| governance | `comply_apply` | not async — some MCP clients expect async tools |
| governance | `comply_list` | not async — some MCP clients expect async tools |
| governance | `comply_report` | not async — some MCP clients expect async tools |
| governance | `curl` | not async — some MCP clients expect async tools |
| governance | `delete_file` | not async — some MCP clients expect async tools |
| governance | `kyc_review` | not async — some MCP clients expect async tools |
| governance | `list_directory` | not async — some MCP clients expect async tools |
| governance | `lock` | not async — some MCP clients expect async tools |
| governance | `pip_install` | not async — some MCP clients expect async tools |
| governance | `set_mode` | not async — some MCP clients expect async tools |
| governance | `sovereign_status` | not async — some MCP clients expect async tools |
| governance | `status` | not async — some MCP clients expect async tools |
| governance | `strategic` | not async — some MCP clients expect async tools |
| governance | `trace_list` | not async — some MCP clients expect async tools |
| governance | `trace_view` | not async — some MCP clients expect async tools |
| governance | `unlock` | not async — some MCP clients expect async tools |
| governance | `validate_strategic_plan` | not async — some MCP clients expect async tools |
| governance | `watch` | not async — some MCP clients expect async tools |

### Warning Categories

| Warning | Count |
|---------|-------|
| not async — some MCP clients expect async tools | 21 |

## Fire-Without-Thinking (Zero-Config) Details

**21/21 actions return a useful response when called with empty action + empty params.**
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
