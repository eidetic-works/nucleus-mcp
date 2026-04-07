# Nucleus Security Whitepaper

**Version:** 1.0  
**Date:** April 2026  
**Status:** Public

---

## Executive Summary

Nucleus is the security-first Agent Control Plane for AI agents using the Model Context Protocol (MCP). Unlike conventional agent memory platforms that treat security as an afterthought, Nucleus was designed from the ground up with defense-in-depth: default-deny policies, cryptographic audit trails, governance modes, a kill switch, and built-in compliance frameworks.

This document describes the security architecture that makes Nucleus suitable for regulated environments where agent actions must be auditable, controllable, and compliant.

---

## 1. Threat Model

Nucleus defends against the following attack vectors:

### 1.1 Prompt Injection
Malicious instructions embedded in context could cause agents to execute unauthorized actions. Nucleus mitigates this through default-deny policies that block tool execution regardless of prompt content.

### 1.2 Credential Leaks
Engram content might inadvertently contain API keys, passwords, or tokens. Nucleus scans engram content for common secret patterns before persistence.

### 1.3 Unauthorized Tool Execution
Without governance, agents can call any available tool. Nucleus enforces tool tiers (`runtime/tool_tiers.py`) — tools are gated by activation level, preventing access to dangerous operations without explicit policy approval.

### 1.4 Context Poisoning
Corrupted or malicious engrams could influence future agent decisions. The cryptographic audit trail (SHA-256 hash chain) makes tampering detectable, and the quarantine system allows removing suspicious engrams from active circulation.

### 1.5 State Tampering
Direct modification of brain files could bypass controls. File locking (`runtime/file_resilience.py`) and atomic writes (`runtime/memory_pipeline.py`) prevent concurrent corruption, while the audit log provides forensic evidence of all mutations.

---

## 2. Governance Modes

Nucleus operates in two governance modes, controlled by the hypervisor (`runtime/hypervisor_ops.py`):

### 2.1 Red Mode (Restricted)
- All destructive operations blocked
- File writes require explicit approval
- External network calls prohibited
- Suited for production environments

### 2.2 Blue Mode (Permissive)
- Full tool access enabled
- Development and testing workflows
- All actions still logged to audit trail
- Default mode for local development

Mode switching is logged to the Decision Stream of Record (DSoR) and can be locked to prevent unauthorized changes.

---

## 3. Kill Switch

The kill switch (`runtime/governance/kill_switch.json`) provides emergency halt capability:

- **Activation**: Single API call or CLI command halts all agent operations
- **Scope**: Affects all tool execution, not just individual agents
- **Persistence**: State survives process restarts
- **Recovery**: Requires explicit manual deactivation
- **Audit**: Activation and deactivation logged with timestamps and reasons

This is critical for regulated environments where human operators must be able to immediately stop AI agent activity.

---

## 4. Cryptographic Audit Trail

Every interaction is recorded with cryptographic integrity:

### 4.1 Event Logging
All tool invocations, state changes, and decisions are appended to `events.jsonl` with:
- Timestamp (ISO 8601)
- Action type and parameters
- Agent identity
- SHA-256 content hash

### 4.2 Decision Stream of Record (DSoR)
The DSoR (`runtime/dsor.py`) maintains a chain of decision records:
- Each decision references its parent decision
- Hash chain makes insertion or deletion detectable
- Trace viewer (`runtime/trace_viewer.py`) enables forensic analysis

### 4.3 Interaction Log
The interaction log (`ledger/interaction_log.jsonl`) records every MCP tool call with token counts, latency, and response hashes for billing and compliance auditing.

---

## 5. Credential Scanning

Engram content is scanned for secret patterns before persistence:

- API keys (AWS, GCP, Azure, generic patterns)
- OAuth tokens and bearer tokens
- Private keys (RSA, ECDSA, Ed25519)
- Database connection strings with embedded passwords
- Generic high-entropy strings

Detection triggers a warning and optional quarantine. This prevents agents from accidentally persisting credentials into long-term memory.

---

## 6. Circuit Breakers

External dependency failures are isolated through circuit breakers (`runtime/circuit_breaker.py`):

- **Per-channel isolation**: Notification channels (Telegram, Slack, Discord) have independent circuit breakers
- **Failure threshold**: After N consecutive failures, the breaker opens
- **Recovery timeout**: Automatic retry after cooldown period
- **Metrics**: Breaker state changes are logged for observability

This prevents cascading failures when external APIs are unavailable.

---

## 7. File Locking and Atomic Writes

Concurrent access to brain files is protected:

### 7.1 File Locking
The `runtime/file_resilience.py` module provides cross-platform file locking:
- Advisory locks on POSIX systems
- Timeout-based acquisition to prevent deadlocks
- Graceful fallback with warning when locking is unavailable

### 7.2 Atomic Writes
The memory pipeline (`runtime/memory_pipeline.py`) uses atomic write patterns:
- Write to temporary file first
- Flush and sync to disk
- Atomic rename to target path
- This prevents partial writes from corrupting state

### 7.3 SQLite WAL Mode
Task and session storage uses SQLite in WAL (Write-Ahead Logging) mode for concurrent read/write safety without blocking.

---

## 8. Default-Deny Policy

The default-deny model is enforced at three levels:

### 8.1 Tool Tiers
Tools are organized into tiers (`runtime/tool_tiers.py`):
- **Tier 0 (Launch)**: Governance and engram tools only
- **Tier 1 (Core)**: Task, session, and orchestration tools
- **Tier 2 (Advanced)**: Federation, deployment, and training tools
- **Tier 3 (System)**: Reserved for internal operations

Higher tiers require explicit activation via environment variables or license keys.

### 8.2 Rate Limiting
Tool dispatch includes rate limiting (`tools/_dispatch.py`) to prevent abuse:
- Per-tool rate limits
- Global request budget
- Automatic throttling with informative error messages

### 8.3 Input Validation
All tool parameters are validated before execution. The LLM tool enforcer (`runtime/llm_tool_enforcer.py`) validates that AI-generated tool calls conform to expected schemas.

---

## 9. Compliance Frameworks

Nucleus includes built-in support for regulatory compliance (`runtime/compliance_config.py`):

### 9.1 EU DORA (Digital Operational Resilience Act)
- ICT risk management controls
- Incident reporting templates
- Third-party oversight documentation

### 9.2 SG MAS-TRM (Technology Risk Management)
- Technology risk assessment framework
- Outsourcing and cloud controls
- Business continuity requirements

### 9.3 US SOC 2
- Trust service criteria mapping
- Control activity documentation
- Monitoring and logging requirements

### 9.4 Implementation
Each jurisdiction configuration specifies:
- Required governance mode
- Mandatory audit retention periods
- Data residency constraints
- Specific tool restrictions

Applied via `nucleus comply --jurisdiction <id>` or `nucleus secure --jurisdiction <id>`.

---

## 10. Data Residency

All data remains local by default:

- **No cloud dependency**: Nucleus operates entirely on-premises
- **Brain directory**: All state stored in local `.brain/` directory
- **No telemetry by default**: Anonymous telemetry is opt-in and can be disabled with `nucleus config --no-telemetry`
- **Federation**: Multi-brain coordination uses filesystem paths, not network calls

This architecture satisfies data sovereignty requirements for organizations that cannot send agent data to external servers.

---

## Architecture Summary

```
                    ┌─────────────────────────┐
                    │    MCP Client (IDE)      │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │  Default-Deny Gateway     │
                    │  (Tool Tiers + Rate Limit)│
                    └───────────┬──────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
   ┌────────▼───────┐  ┌───────▼────────┐  ┌──────▼───────┐
   │  Governance     │  │  Audit Trail   │  │  Kill Switch │
   │  (Red/Blue)     │  │  (SHA-256)     │  │  (Emergency) │
   └────────┬───────┘  └───────┬────────┘  └──────────────┘
            │                   │
   ┌────────▼───────┐  ┌───────▼────────┐
   │  Tool Execution │  │  DSoR / Events │
   │  (170+ tools)   │  │  (Immutable)   │
   └────────┬───────┘  └────────────────┘
            │
   ┌────────▼───────┐
   │  .brain/        │
   │  (Local only)   │
   └────────────────┘
```

---

## Contact

- Repository: [github.com/eidetic-works/nucleus-mcp](https://github.com/eidetic-works/nucleus-mcp)
- Issues: [GitHub Issues](https://github.com/eidetic-works/nucleus-mcp/issues)

---

*This document describes the security architecture of Nucleus MCP. For implementation details, refer to the source code in `src/mcp_server_nucleus/runtime/`.*
