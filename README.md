# 🧠 Nucleus — Sovereign Agent OS

> ⚠️ **official repository** → **[nucleus-mcp](https://github.com/eidetic-works/nucleus-mcp)**

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-54%20passing-brightgreen)]()

> **The sovereign, local-first Agent Operating System** — persistent memory, governance, compliance, and audit trails for any AI agent.

> [!CAUTION]
> **After the [OpenClaw security crisis](https://www.youtube.com/watch?v=ceEUO_i7aW4) (1.5M API keys leaked, sleeper agents in skills), agent security is no longer optional.**
> Nucleus is built security-first: hypervisor controls, resource locking, compliance governance, and full audit trails — all 100% local.

---

## 🎯 The Problem

AI agents are powerful, but **ungoverned**:
- **No memory** — every session starts from zero
- **No audit trail** — no one knows why the agent did what it did
- **No compliance** — regulators can't approve what they can't trace
- **No sovereignty** — your data flows through someone else's cloud

**For regulated industries (BFSI, healthcare, legal), this is a dealbreaker.**

---

## ✨ The Solution: Sovereign Agent OS

Nucleus gives every AI agent a **persistent brain** with **built-in governance**:

```
┌─────────────────────────────────────────────────┐
│  🧠 Nucleus — Sovereign Agent OS                │
│                                                 │
│  ┌─ Memory ──┐  ┌─ Governance ┐  ┌─ DSoR ────┐ │
│  │ Engrams   │  │ HITL        │  │ Decision  │ │
│  │ Sessions  │  │ Kill Switch │  │ Trail     │ │
│  │ Context   │  │ Compliance  │  │ Audit     │ │
│  └───────────┘  └─────────────┘  └───────────┘ │
│                                                 │
│  100% Local  •  Zero Cloud  •  Full Audit Trail │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (2 Minutes)

### Install
```bash
pip install nucleus-mcp
nucleus-init
```

### Try It
```bash
# See your sovereignty posture
nucleus sovereign

# Run a KYC compliance demo (15-minute BFSI demo)
nucleus kyc demo

# Apply EU DORA compliance
nucleus comply --jurisdiction eu-dora

# Generate audit-ready report
nucleus audit-report --format html -o report.html

# Browse decision trails
nucleus trace list
```

### Configure (Claude Desktop / Cursor / Windsurf)

Add to your MCP config:
```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "nucleus_mcp"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/.brain"
      }
    }
  }
}
```

---

## 🏛️ Why Nucleus for Regulated Industries

### Jurisdiction-Aware Compliance

One command to configure for any regulatory framework:

```bash
nucleus comply --jurisdiction eu-dora       # EU DORA (7yr retention, kill switch)
nucleus comply --jurisdiction sg-mas-trm    # Singapore MAS TRM (5yr, strictest HITL)
nucleus comply --jurisdiction us-soc2       # US SOC2 (1yr retention)
nucleus comply --report                     # Check compliance status
```

| Jurisdiction | Region | Retention | HITL Ops | Kill Switch |
|--------------|--------|-----------|----------|-------------|
| `eu-dora` | EU | 7 years | 5 types | ✅ Required |
| `sg-mas-trm` | Singapore | 5 years | 5 types | ✅ Required |
| `us-soc2` | US/Global | 1 year | 3 types | ⚪ Optional |
| `global-default` | Global | 90 days | 2 types | ⚪ Optional |

### KYC Compliance Demo

Built-in demo workflow showing how Nucleus governs a KYC document review:

```bash
nucleus kyc review APP-001  # Low risk → ✅ APPROVE
nucleus kyc review APP-002  # Medium risk → ⚠️ ESCALATE (PEP match)
nucleus kyc review APP-003  # High risk → ❌ REJECT (sanctions)
nucleus kyc demo            # Run all 3 in sequence
```

Each review generates:
- 5 automated checks (sanctions, PEP, document validity, risk factors, source of funds)
- Full decision trail stored as DSoR (Decision System of Record) trace
- HITL approval request for risky applications
- Sovereignty guarantee: all processing is local

### Audit Reports

Generate audit-ready reports for regulators:

```bash
nucleus audit-report                              # Terminal text
nucleus audit-report --format json                # JSON for APIs
nucleus audit-report --format html -o report.html # HTML for compliance officers
```

### Sovereignty Status

See your full sovereignty posture:

```bash
nucleus sovereign
```

Shows: sovereignty score (0-100), memory health, governance posture, DSoR integrity, data residency guarantee.

---

## 🛠 Full Feature Set

### Core — Persistent Agent Memory
| Feature | Command | Description |
|---------|---------|-------------|
| **Engrams** | `nucleus_engrams` | Persistent knowledge that survives sessions |
| **Sessions** | `nucleus_sessions` | Save and resume work context |
| **Morning Brief** | `nucleus morning-brief` | Daily compounding intelligence brief |
| **End of Day** | `nucleus end-of-day` | Capture learnings as engrams |

### Governance — Agent Controls
| Feature | Command | Description |
|---------|---------|-------------|
| **Compliance** | `nucleus comply` | Jurisdiction-aware configuration |
| **Audit Reports** | `nucleus audit-report` | Audit-ready compliance reports |
| **KYC Demo** | `nucleus kyc` | Pre-built compliance demo workflow |
| **DSoR Traces** | `nucleus trace` | Browse decision trails |
| **Sovereignty** | `nucleus sovereign` | Full sovereignty posture report |
| **HITL** | Built-in | Human-in-the-loop approval gates |
| **Kill Switch** | Built-in | Emergency halt for agent operations |
| **Hypervisor** | `nucleus_governance` | File locking, security, mode control |

### Orchestration — Multi-Agent Coordination
| Feature | Command | Description |
|---------|---------|-------------|
| **Tasks** | `nucleus_tasks` | Track work across agents |
| **Sync** | `nucleus_sync` | Multi-agent brain synchronization |
| **Slots** | `nucleus_slots` | Agent orchestration with sprint mode |
| **Federation** | `nucleus_federation` | Multi-brain coordination |

---

## ⚡ Comparison

| | OpenClaw | Claude Code | **Nucleus** |
|---|----------|-------------|-------------|
| **Security** | ❌ Key leaks, sleeper agents | ⚠️ Cloud-managed | ✅ Hypervisor + audit trail |
| **Compliance** | ❌ None | ❌ None | ✅ DORA, MAS TRM, SOC2 |
| **Audit Trail** | ❌ | ⚠️ Basic logs | ✅ Full DSoR + HTML reports |
| **HITL** | ❌ | ⚠️ Limited | ✅ Jurisdiction-configurable |
| **Cross-Platform** | ❌ | ❌ | ✅ Any MCP client |
| **Local-First** | ⚠️ Some cloud | ⚠️ Some cloud | ✅ 100% local |
| **Open Source** | ✅ MIT | ❌ Closed | ✅ MIT |

---

## 🐳 Deployment

### Docker (per jurisdiction)
```bash
# EU DORA deployment
docker compose -f deploy/docker-compose.eu-dora.yml up -d

# Or use the one-command deployment script
./deploy/deploy.sh eu-dora
```

### Local
```bash
pip install nucleus-mcp
nucleus init
nucleus comply --jurisdiction eu-dora
nucleus sovereign  # Verify
```

---

## 📦 v1.3.0 — What's New

- **Compliance Configuration** — 4 regulatory jurisdictions with governance policies
- **Audit Reports** — Text, JSON, and HTML output for compliance officers
- **KYC Demo Workflow** — 3 demo applications with 5 automated checks
- **Sovereignty Status** — Posture report with A/B/C/D grading
- **DSoR Trace Viewer** — Browse and inspect decision trails
- **Deployment Kit** — Dockerfile, docker-compose per jurisdiction, deploy script
- **54 new tests** — All passing

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## 🤝 Community & Contributing

- **🐛 Found a bug?** Open an [Issue](https://github.com/eidetic-works/nucleus-mcp/issues)
- **💡 Feature idea?** Start a [Discussion](https://github.com/eidetic-works/mcp-server-nucleus/discussions)
- **🔧 Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **💬 Join Discord** — [Join the Nucleus Development Server](https://discord.gg/RJuBNNJ5MT)

## 📜 License

MIT © 2026 Nucleus Team | [hello@nucleusos.dev](mailto:hello@nucleusos.dev)

---

**Built for the AI-native enterprise.** Star us if Nucleus gives your agents a brain — and a conscience. ⭐
