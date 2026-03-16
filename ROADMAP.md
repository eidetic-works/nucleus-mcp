# Nucleus Roadmap

**Last Updated:** March 2026
**Current Version:** 1.6.2

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
- **IPC Authentication**: Per-request tokens (CVE-2026-001 remediation)
- **KYC Demo**: 5 automated compliance checks

### Pre-1.0 (January 2026) ✅
- **v0.5–v0.6**: Task engine v3.1, Prometheus metrics, multi-agent protocol, DSoR, 135 MCP tools

---

## In Progress

### v1.7.0 (Q1 2026) 🚧
**Theme: Interactive Intelligence**

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Provider Chat | Done | Gemini, Anthropic, Groq with native tool calling |
| Session Resume | Done | Auto-load chat history on startup |
| Groq Auto-Rotation | Done | Cascade across models on rate limit |
| Security Posture Tool | Planned | Governance scoring with shareable report |
| `nucleus secure` | Planned | One-command security hardening |

---

## Planned

### v1.8.0 (Q2 2026)
**Theme: Federation & Channels**

- **Peer-to-Peer Federation**: Connect multiple Nucleus instances
- **Distributed Engrams**: Share memory across federated nodes
- **Messaging Bridge**: Discord, Slack, Telegram channel integration
- **Cross-Instance Tasks**: Route tasks to specialized nodes

### v1.9.0 (Q3 2026)
**Theme: Enterprise**

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

- **Patch Releases** (1.6.x): As needed for bug fixes
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
