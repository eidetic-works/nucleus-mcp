# 🧠 Nucleus — Sovereign Agent OS

> ⚠️ **official repository** → **[nucleus-mcp](https://github.com/eidetic-works/nucleus-mcp)**

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-263%20passing-brightgreen)]() [![Release](https://img.shields.io/badge/Release-v1.6.2-blue)]() [![NPM](https://img.shields.io/badge/npm-v1.4.1-red)](https://www.npmjs.com/package/nucleus-mcp)

> **The sovereign, local-first Agent Operating System** — persistent memory, governance, compliance, and audit trails for any AI agent.

🌐 [**Website**](https://nucleusos.dev) • 🏦 [**Live KYC Demo**](https://nucleusos.dev/kyc-demo.html) • 🛠 [**170+ Tool Catalog**](https://hud.nucleusos.dev) • 💬 [**Discord**](https://discord.gg/RJuBNNJ5MT)

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
nucleus self-setup
```

### Adaptive Path Discovery
Nucleus automatically locates your `.brain` by following this hierarchy:
1. `NUCLEUS_BRAIN_PATH` environment variable.
2. Climbing parent directories from CWD to find an existing `.brain`.
3. Defaulting to `$HOME/.nucleus/brain`.

### Try It
```bash
# One-command security hardening + posture report
nucleus secure

# Interactive AI chat (Gemini, Anthropic, Groq — hot-switchable)
nucleus chat

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

# System Health & Lock Recovery
nucleus status --health
nucleus status --cleanup-lock
```

### 🆘 Session Recovery (Universal)

If your IDE session freezes due to bloated conversation files:

```bash
# One-shot automatic recovery
nucleus recover auto <conversation-id>

# Or step-by-step:
nucleus recover detect                      # Find bloated conversations
nucleus recover extract <conversation-id>   # Extract context
nucleus recover bootstrap <conversation-id> # Create fresh session
nucleus recover rewrite <old-id> <new-id>   # Update test paths
```

**Works across any IDE** (Windsurf, Cursor, Antigravity) and CLI. Zero configuration required.

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

## 🗝️ Agent CLI — v1.6.2



Nucleus speaks **MCP + CLI + SDK**. Every command auto-detects TTY (table) vs pipe (JSON).

```bash
# Memory
nucleus engram search "compliance"                    # Table in terminal, JSONL when piped
nucleus engram write my_key "important insight" --context Strategy --intensity 8
nucleus engram query --context Decision --limit 10

# Tasks
nucleus task list --status READY --format json        # Force JSON output
nucleus task add "Ship v1.4.0 CLI" --priority 1
nucleus task update task-abc123 --status DONE

# Sessions
nucleus session save "Working on CLI implementation"
nucleus session resume                                # Most recent session

# Growth
nucleus growth pulse                                  # GitHub stars + PyPI + compound
nucleus growth status                                 # Metrics without side effects

# Outbound I/O
nucleus outbound check reddit r/ClaudeAI              # Idempotency gate
nucleus outbound record reddit r/ClaudeAI --permalink https://reddit.com/abc
nucleus outbound plan                                 # What's ready vs posted

# Pipe-friendly (Unix composable)
nucleus engram search "test" | jq '.key'
nucleus task list --format tsv | cut -f1,3
```

**Global flags:** `--format json|table|tsv` • `--brain-path /path/to/.brain` • `--version`

---

## �🥞 The Layered Open-Core Model
Nucleus is designed for progressive adoption. You can start local and scale up to full institutional compliance seamlessly.

1. **Layer 1: Sovereign Core (OSS):** 100% local, persistent engrams, session state, and essential file governance.
2. **Layer 2: CLI-First Tooling:** `morning-brief`, `end-of-day`, and the `dogfood` tracker for compounding intelligence.
3. **Layer 3: Deployment Kit:** 1-command jurisdiction deployments (`nucleus deploy --jurisdiction eu-dora`).
4. **Layer 4: Institutional Compliance:** DSoR Trace Viewer, Audit Report HTML exports (DORA/MAS TRM), and strict HITL gates.

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
| **Secure** | `nucleus secure` | One-command hardening + security certificate |
| **HITL** | Built-in | Human-in-the-loop approval gates |
| **Kill Switch** | Built-in | Emergency halt for agent operations |
| **Hypervisor** | `nucleus_governance` | File locking, security, mode control |

### Interactive — AI Chat
| Feature | Command | Description |
|---------|---------|-------------|
| **Chat** | `nucleus chat` | Multi-provider terminal AI (Gemini/Anthropic/Groq) |
| **Multi-Turn** | Built-in | Native conversation history with session resume |
| **Tool Calling** | Built-in | Native function calling + `<execute>` tag fallback |
| **Dual-Agent** | `/dual <provider>` | Primary generates, reviewer critiques |

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

## 🔭 Anonymous Telemetry

Nucleus collects **anonymous, aggregate usage statistics** to improve the product. No personal data, no engram content, no org docs — ever.

> ⚠️ **Note:** Anonymous telemetry powers the autonomous incident brain engine (`telemetry.nucleusos.dev`). Disabling it may degrade or disable autonomy features like policy adaptation, crash-loop detection, and rollout health scoring. Only opt out if you have a fully local telemetry stack.

**Opt out in 1 command:**
```bash
nucleus config --no-telemetry
# or via env:    NUCLEUS_ANON_TELEMETRY=false
# or in config:  telemetry.anonymous.enabled: false
```

**What's collected:** command name, duration, error type, Nucleus/Python version, OS platform.  
**What's NEVER collected:** engram content, file paths, prompts, API keys, any PII.

See [TELEMETRY.md](TELEMETRY.md) for full details.

---

## 📦 v1.6.2 — Interactive Intelligence
- **Multi-Provider Chat** — `nucleus chat` with Gemini, Anthropic, Groq (hot-switchable via `/provider`)
- **Native Tool Calling** — Anthropic `tool_use` API + Groq OpenAI function calling
- **Model-Aware Gating** — 70b+ models use native tools; 8b models use `<execute>` tags
- **Groq Auto-Rotation** — Cascades across models on rate limit (70b → scout → qwen → 8b)
- **Session Resume** — Chat history auto-loads from disk on startup
- **`nucleus secure`** — One-command security hardening + posture report with certificate
- **263 tests passing** — Routing fuzzer, session resume, tool pattern detection

## 📦 v1.6.0 — The Autonomous Incident Brain
- Automated Incident Response, Adaptive Policy Engine, Reliability Policy Surface
- Full-Stack Health Monitoring with crash-loop defense
- Safe Rollouts & Auto-Rollback with health-gated releases

## 📦 v1.5.0 — The Sovereign Kernel
- **Adaptive Path Discovery** — Zero-conf brain location (Env > CWD > Home)
- **Universal Shell Integration** — Integrated bash/zsh completions via `self-setup`
- **Federation Level 1** — Automated local peer discovery via IPC
- **DSoR Self-Healing** — Automated reconciliation of orphaned decisions in audit logs
- **CLI Sovereignty** — Unified routing, Python-native bootstrap, and health monitoring
- **80+ tests** — All passing (including stale lock recovery and recursion guards)

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
