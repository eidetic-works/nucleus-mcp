# Nucleus Roadmap

**Last Updated:** January 30, 2026  
**Current Version:** 0.6.0

---

## Vision

Nucleus aims to be the **definitive Agent Control Plane** - the governance layer that makes autonomous AI agents safe, auditable, and controllable.

---

## Released

### v0.6.0 (January 2026) ✅
**Theme: Decision Provenance**

- **Decision System of Record (DSoR)**: Full audit trail for agent decisions
  - `DecisionMade` events emitted before every tool execution
  - Context hashing with SHA-256 for state verification
  - Before/after snapshots for agent lifecycle verification
- **IPC Authentication**: Per-request tokens (CVE-2026-001 remediation)
- **Token Metering**: Billing-ready consumption tracking
- **Context Manager**: World-state hashing and drift detection
- **5 New MCP Tools**: DSoR inspection and audit
- **135 MCP Tools**: Total tool count
- **64 Unit Tests**: Including 16 DSoR-specific tests

### v0.5.1 (January 2026) ✅
- **Engram Ledger**: Persistent memory with intensity scoring
- **Governance Dashboard**: `brain_governance_status()` 
- **Cryptographic Audit**: SHA-256 hashed interaction log
- **Recursive Mounter**: Mount/unmount external MCP servers
- **130 MCP Tools**: Comprehensive agent orchestration
- **48 Unit Tests**: Full test coverage

### v0.5.0 (January 2026) ✅
- **V3.1 Task Engine**: Slot pooling, tier routing
- **Prometheus Metrics**: Observability endpoints
- **Performance Profiling**: Latency tracking
- **Multi-Agent Protocol**: MoU enforcement

---

## In Progress

### v0.6.1 (Q1 2026) 🚧
**Theme: Scalability & Protection**

| Feature | Status | Description |
|---------|--------|-------------|
| Tool Router Pattern | Proposed | Group 135+ tools into logical pools |
| Cython Shield | Proposed | Binary protection for core algorithms |
| Policy DSL | Planned | Declarative security policies |
| WebSocket Transport | Planned | Real-time MCP communication |

---

## Planned

### v0.7.0 (Q2 2026)
**Theme: Federation**

- **Peer-to-Peer Federation**: Connect multiple Nucleus instances
- **Distributed Engrams**: Share memory across federated nodes
- **Cross-Instance Tasks**: Route tasks to specialized nodes
- **Federation Dashboard**: Monitor peer health

### v0.8.0 (Q3 2026)
**Theme: Enterprise**

- **RBAC**: Role-based access control for teams
- **SSO Integration**: SAML/OIDC authentication
- **Audit Export**: Compliance-ready audit logs
- **SLA Monitoring**: Uptime and latency guarantees

### v1.0.0 (Q4 2026)
**Theme: Production Ready**

- **Rust Core**: Performance-critical paths in Rust
- **Formal Verification**: Proven security properties
- **Enterprise Support**: SLA-backed support tiers
- **Certification**: SOC2 / ISO 27001 readiness

---

## Research Track

These are exploratory items not committed to a release:

- **Autonomous Goal Decomposition**: Agents set their own sub-goals
- **Learned Policies**: ML-based policy recommendations
- **Natural Language Policies**: "Never access files outside /project"
- **Blockchain Audit**: Immutable external audit trail
- **Hardware Security Module**: HSM-backed key management

---

## How to Influence the Roadmap

1. **Feature Requests**: Open a GitHub Discussion
2. **Bug Reports**: Open a GitHub Issue
3. **Beta Testing**: Join our beta program
4. **Enterprise Needs**: Contact partnerships@nucleusos.dev

---

## Release Cadence

- **Patch Releases** (0.5.x): As needed for bug fixes
- **Minor Releases** (0.x.0): Monthly feature releases
- **Major Releases** (x.0.0): Quarterly milestone releases

---

## Deprecation Policy

- Features deprecated in version N are removed in version N+2
- Security fixes backported for 2 minor versions
- Breaking changes announced 1 minor version in advance

---

*Roadmap subject to change based on community feedback and strategic priorities.*

*— The Nucleus Team*
