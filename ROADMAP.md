# Nucleus Roadmap

**Last Updated:** April 2026
**Current Version:** 1.8.8

---

## Vision

Nucleus is the **Sovereign Agent Operating System** — the governance, memory, and orchestration layer that makes autonomous AI agents safe, auditable, and controllable. In a world where agent frameworks ship fast and break trust, Nucleus is the governed alternative.

---

## Released

### v1.6.x (March 2026) ✅
**Theme: Telemetry & Observability**

- **Smart Telemetry Drain**: Automated Upstash Redis → Local OTel pipeline with Docker lifecycle management
- **Anonymous Telemetry**: Opt-out OpenTelemetry with fire-and-forget spans (never blocks user workflow)
- **`nucleus config`**: Toggle telemetry, set endpoints, view configuration
- **First-User Detection**: Alert on first external user with platform filtering

### v1.5.0 (March 2026) ✅
**Theme: The Sovereign Kernel**

- **Adaptive Path Discovery**: Dynamic brain location with priority hierarchy
- **Federation Engine Level 1**: Local IPC peer discovery with exclusive file locking
- **Universal Shell Integration**: Bash/zsh autocompletion via `nucleus self-setup`
- **DSoR Self-Healing**: Automated reconciliation of orphaned audit decisions
- **CLI Sovereignty**: Health checks, sovereignty score, stale lock cleanup

### v1.4.1 (March 2026) ✅
**Theme: Agent-Native**

- **Gemini CLI Integration**: Wrapper script, 16/16 test suite, production-ready
- **Agent-Native CLI**: Structured error envelopes, semantic exit codes, machine-parseable output
- **Audit Score**: 6/16 → 11/16 on "8 Rules for Agent-Callable CLIs" checklist

### v1.0–v1.3 (February 2026) ✅
**Theme: Core Platform**

- **Engram Ledger**: Persistent memory with intensity scoring and ADUN protocol
- **Task Orchestration**: Priority-based queue with DAG dependencies, atomic claiming, escalation
- **Decision System of Record (DSoR)**: SHA-256 audit trail, context hashing, before/after snapshots
- **Hypervisor**: Default-deny governance, file locking, kill switch, watchdog
- **Compliance**: 4 jurisdictions (EU-DORA, SG-MAS-TRM, US-SOC2, Global)
- **12 Facade Tools**: ~170 actions consolidated into clean MCP interface
- **IPC Authentication**: Per-request tokens (NUC-SEC-001 remediation)
- **KYC Demo**: 5 automated compliance checks

### Pre-1.0 (January 2026) ✅
- **v0.5–v0.6**: Task engine v3.1, Prometheus metrics, multi-agent protocol, DSoR, 135 MCP tools

---

### v1.7.0 (March 2026) ✅
**Theme: Interactive Intelligence**

- **Multi-Provider Chat**: Gemini, Anthropic, Groq with native tool calling
- **Session Resume**: Auto-load chat history on startup
- **Groq Auto-Rotation**: Cascade across models on rate limit

### v1.8.x (April 2026) ✅
**Theme: Compounding Substrate**

- **Phases 1-7 Shipped**: 7 arteries, deltas, Three Frontiers (GROUND/ALIGN/COMPOUND), business events, convergence, runtime wiring, ALIGN tool, ambient health
- **Zero-Sanitization Auto-Sync**: Post-commit hook triggers git archive → public repo. No sed patches, no AST surgery.
- **12 Facade Tools**: ~170 actions consolidated into clean MCP interface
- **287+ tests**, 0 regressions across all phases

---

## In Progress

### v1.9.0 (Q2 2026) 🚧
**Theme: Substrate Visibility & Federation**

| Feature | Status | Description |
|---------|--------|-------------|
| cold_start enrichment | Done | Session arc + compounding pulse in brain card |
| brain://cycle resource | Done | Weekly cycle state in IDE sidebar |
| brain://arc resource | Done | Session continuity in IDE sidebar |
| Security Posture Tool | Planned | Governance scoring with shareable report |
| `nucleus secure` | Planned | One-command security hardening |
| Peer-to-Peer Federation | Planned | Connect multiple Nucleus instances |

---

## Planned

### v2.0.0 (Q3 2026)
**Theme: Enterprise & Scale**

- **RBAC**: Role-based access control for teams
- **SSO Integration**: SAML/OIDC authentication
- **Audit Export**: Cryptographically signed compliance reports
- **SLA Monitoring**: Uptime and latency guarantees

### v2.0.0 (Q4 2026)
**Theme: Production Scale**

- **Rust Core**: Performance-critical paths in Rust
- **Horizontal Sharding**: Multi-brain fleet management
- **Formal Verification**: Proven security properties
- **Certification**: SOC2 / ISO 27001 readiness

---

## Research Track

These are exploratory items not committed to a release:

- **Autonomous Goal Decomposition**: Agents set their own sub-goals
- **Learned Policies**: ML-based policy recommendations
- **Natural Language Policies**: "Never access files outside /project"
- **Hardware Security Module**: HSM-backed key management

---

## How to Influence the Roadmap

1. **Feature Requests**: Open a GitHub Discussion
2. **Bug Reports**: Open a GitHub Issue
3. **Beta Testing**: Join our beta program
4. **Enterprise Needs**: Contact partnerships@nucleusos.dev

---

## Release Cadence

- **Patch Releases** (1.8.x): As needed for bug fixes
- **Minor Releases** (1.x.0): Monthly feature releases
- **Major Releases** (x.0.0): Quarterly milestone releases

---

## Deprecation Policy

- Features deprecated in version N are removed in version N+2
- Security fixes backported for 2 minor versions
- Breaking changes announced 1 minor version in advance

---

*Roadmap subject to change based on community feedback and strategic priorities.*

*— The Nucleus Team*
# test pre-commit
