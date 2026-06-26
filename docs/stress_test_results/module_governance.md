# Nucleus Tool Facade Stress Test — Full Report

**Generated:** 2026-06-26T06:05:36
**Total tests:** 133
**Actions tested:** 19
**Angles per action:** 7

## Executive Summary

| Status | Count | Percentage | Meaning |
|--------|-------|-----------|---------|
| ✅ pass | 39 | 29.3% | Tool returned a successful response |
| ⚠️ handled | 94 | 70.7% | Tool returned a graceful error (no crash) |
| 🔶 warn | 0 | 0.0% | Cross-agent compat warning (static analysis) |
| ❌ fail | 0 | 0.0% | Tool failed without structured response |
| 💥 crash | 0 | 0.0% | Unhandled exception (KeyError, AttributeError, etc.) |
| **Total** | **133** | **100%** | |

## Results by Angle

### happy

**What it tests:** Valid params provided — the "normal" call an LLM would make

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 4 | 21.1% |
| ⚠️ handled | 15 | 78.9% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### missing_params

**What it tests:** No params provided at all (empty dict {}) — tests required-param validation

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 8 | 42.1% |
| ⚠️ handled | 11 | 57.9% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### wrong_types

**What it tests:** Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 19 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### empty_params

**What it tests:** Empty params dict {} — same as missing_params, tests default handling

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 8 | 42.1% |
| ⚠️ handled | 11 | 57.9% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### unknown_action

**What it tests:** Action name that does not exist in this tool's ROUTER — tests error handling for typos

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 19 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### fire_without_thinking

**What it tests:** Empty action string + empty params — zero-config call, tests what happens when an LLM just fires blindly

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 0 | 0.0% |
| ⚠️ handled | 19 | 100.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

### cross_agent_compat

**What it tests:** Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients

| Status | Count | % |
|--------|-------|---|
| ✅ pass | 19 | 100.0% |
| ⚠️ handled | 0 | 0.0% |
| 🔶 warn | 0 | 0.0% |
| ❌ fail | 0 | 0.0% |
| 💥 crash | 0 | 0.0% |
| **Total** | **19** | **100%** |

## Per-Module Breakdown

### Module: `governance` (19 actions)

| Action | happy | missing | wrong_types | empty | unknown | fire_blank | compat | Overall |
|--------|-------|---------|-------------|-------|---------|------------|--------|---------|
| `audit_report` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `auto_fix_loop` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `comply_apply` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `comply_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `comply_report` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `curl` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `delete_file` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `kyc_review` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `list_directory` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `lock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `pip_install` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `set_mode` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `sovereign_status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `status` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 4 pass |
| `trace_list` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `trace_view` | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ 3 pass |
| `unlock` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `validate_strategic_plan` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |
| `watch` | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ 1 pass |

#### `governance.audit_report`

**happy** — ⚠️ handled
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'limit'",
  "expected_params": "(report_format='text', since_hours=None, brain_p`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T00:34:09.321833+00:00\n  Jurisdiction: N`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'audit_report': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(report_format='text', since_hours=None, brain_path`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "formatted": "======================================================================\n  NUCLEUS AGENT OS \u2014 AUDIT TRAIL REPORT\n  Generated: 2026-06-26T00:34:09.330940+00:00\n  Jurisdiction: N`

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.comply_report`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

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
  "status": "non_compliant",
  "checks": {
    "jurisdiction": {
      "status": "not_configured"
    },
    "audit_logs": {
      "status": "present",
      "audit_files": 0,
      "event_files": 1`

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.kyc_review`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "review_id": "KYC-0D51AC50",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T00:34:09.339048+00:00",
  "completed_at": "2026-06-26T00:34:09.339064+00:00",
 `

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "review_id": "KYC-E6736B5F",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T00:34:09.339506+00:00",
  "completed_at": "2026-06-26T00:34:09.339519+00:00",
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
  "review_id": "KYC-B8022C1A",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-26T00:34:09.339930+00:00",
  "completed_at": "2026-06-26T00:34:09.339939+00:00",
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.sovereign_status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `{
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `{
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

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
  "sovereignty_score": 55,
  "formatted": "\n  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\`

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

#### `governance.status`

**happy** — ✅ pass
- *Tests:* Valid params provided — the "normal" call an LLM would make
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
👁️  Watchdog: Inactive
🔒 Protected Paths: 0
🎨 Injector: Ready`

**missing_params** — ✅ pass
- *Tests:* No params provided at all (empty dict {}) — tests required-param validation
- *Result preview:* `🛡️  NUCLEUS HYPERVISOR v0.8.0 (God Mode)
📍 Workspace: /private/tmp
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
📍 Workspace: /private/tmp
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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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
  "count": 33,
  "traces": [
    {
      "file": "KYC-0D51AC50.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0D51AC50",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

**wrong_types** — ⚠️ handled
- *Tests:* Params with wrong types (int where str expected, str where int expected, etc.) — tests type coercion
- *Result preview:* `{
  "error": "Invalid params for action 'trace_list': register.<locals>.<lambda>() got an unexpected keyword argument 'id'",
  "expected_params": "(trace_type=None, brain_path=None)",
  "provided_para`

**empty_params** — ✅ pass
- *Tests:* Empty params dict {} — same as missing_params, tests default handling
- *Result preview:* `{
  "count": 33,
  "traces": [
    {
      "file": "KYC-0D51AC50.json",
      "type": "KYC_REVIEW",
      "review_id": "KYC-0D51AC50",
      "recommendation": "APPROVE",
      "risk_score": 0,
      "`

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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
  "review_id": "KYC-ADFD6FFD",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T18:13:17.378178+00:00",
  "completed_at": "2026-06-25T1`

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
  "review_id": "KYC-ADFD6FFD",
  "application_id": "APP-001",
  "applicant": "John Smith",
  "started_at": "2026-06-25T18:13:17.378178+00:00",
  "completed_at": "2026-06-25T1`

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

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

**cross_agent_compat** — ✅ pass
- *Tests:* Static analysis of tool function signature, description, async-ness, and client-specific references — tests compatibility across Claude/Cursor/Windsurf/ChatGPT MCP clients
- *No error, no result preview*

---

## Cross-Agent Compatibility Details

## Fire-Without-Thinking (Zero-Config) Details

**19/19 actions return a useful response when called with empty action + empty params.**
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
