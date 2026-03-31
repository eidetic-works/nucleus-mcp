# Nucleus

> A personal AI operating system — persistent memory, governance, and coordination for AI agents.

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![NPM](https://img.shields.io/badge/npm-nucleus--mcp-red)](https://www.npmjs.com/package/nucleus-mcp)

Nucleus is an MCP server that gives AI agents a persistent brain. Sessions survive restarts, decisions leave audit trails, and governance rules enforce boundaries — all running locally on your machine.

This is a solo founder project. Built because I needed it, open-sourced because others might too.

---

## Quick Start

```bash
pip install nucleus-mcp
nucleus init --recipe founder
nucleus morning-brief
```

Three commands. You now have a persistent brain with memory, governance, and a daily workflow.

Other recipes: `nucleus recipe list` (SRE, ADHD, and more).

---

## What It Does

```
┌──────────────────────────────────────────────────────┐
│  Nucleus                                             │
│                                                      │
│  ┌─ Memory ──────┐  ┌─ Governance ──┐  ┌─ Audit ──┐ │
│  │ Engrams       │  │ HITL gates    │  │ Decision │ │
│  │ Sessions      │  │ Kill switch   │  │ trails   │ │
│  │ Commitments   │  │ Compliance    │  │ Reports  │ │
│  │ Heartbeat     │  │ Resource lock │  │ Traces   │ │
│  └───────────────┘  └──────────────┘  └──────────┘ │
│                                                      │
│  ┌─ Coordination ┐  ┌─ CLI ────────┐               │
│  │ Task queue    │  │ Engram CRUD  │               │
│  │ Agent slots   │  │ Session mgmt │               │
│  │ Multi-brain   │  │ Chat (multi- │               │
│  │ sync          │  │  provider)   │               │
│  └───────────────┘  └──────────────┘               │
│                                                      │
│  100% local  ·  Zero cloud dependency  ·  MIT        │
└──────────────────────────────────────────────────────┘
```

### Key Features

- **Engrams** — Persistent knowledge that survives across sessions. Write once, recall forever.
- **Session persistence** — Save work context, resume later. No more "where was I?"
- **Commitment tracking** — Open loops tracked with age tiers (green/yellow/red) and health scores.
- **Heartbeat** — Proactive check-ins that catch stale blockers, velocity drops, and idle sessions.
- **Multi-agent coordination** — Task queues, agent slots, and brain sync for multi-agent setups.
- **Governance** — HITL approval gates, kill switch, resource locking, compliance configuration.
- **Decision trails** — Every agent decision logged with reasoning. Full audit trail.
- **170+ MCP tools** — Organized into facade tools for memory, governance, orchestration, sessions, and more.

---

## Nucleus Pro

Everything above is free (MIT). Nucleus Pro adds verifiable governance:

```bash
nucleus trial                              # 14-day free trial
nucleus compliance-check                   # Score your AI governance
nucleus audit-report --signed -o report.html  # Cryptographically signed report
```

**$19/month** or **$149/year** — [nucleusos.dev/pricing](https://nucleusos.dev/pricing)

| | Free | Pro |
|---|---|---|
| 170+ MCP tools | Yes | Yes |
| Persistent memory | Yes | Yes |
| Governance & HITL | Yes | Yes |
| Audit trails (DSoR) | Yes | Yes |
| **Signed audit reports** | - | Ed25519 |
| **Compliance exports** | Score only | Full PDF/HTML |
| **Priority issues** | - | Yes |

---

## Configure Your MCP Client

### Claude Desktop / Cursor / Windsurf

Add to your MCP config (`claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "nucleus_mcp"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"
      }
    }
  }
}
```

### Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "nucleus_mcp"],
      "env": {
        "NUCLEAR_BRAIN_PATH": ".brain"
      }
    }
  }
}
```

### Path Discovery

Nucleus finds your `.brain` automatically:
1. `NUCLEAR_BRAIN_PATH` environment variable (explicit)
2. Walk up from CWD looking for `.brain/` directory
3. Fall back to `$HOME/.nucleus/brain`

---

## CLI

Nucleus has a full CLI alongside the MCP tools. Auto-detects TTY (table output) vs pipe (JSON).

```bash
# Memory
nucleus engram write my_key "insight here" --context Decision --intensity 7
nucleus engram search "compliance"
nucleus engram query --context Strategy --limit 10

# Tasks
nucleus task list --status READY
nucleus task add "Ship the feature" --priority 1

# Sessions
nucleus session save "Working on auth refactor"
nucleus session resume

# Health
nucleus status --health
nucleus sovereign

# Compliance
nucleus comply --jurisdiction eu-dora
nucleus audit-report --format html -o report.html

# Chat (multi-provider: Gemini, Anthropic, Groq)
nucleus chat
```

Pipe-friendly:
```bash
nucleus engram search "test" | jq '.key'
nucleus task list --format tsv | cut -f1,3
```

---

## Compliance

One-command configuration for regulatory frameworks:

```bash
nucleus comply --jurisdiction eu-dora       # EU DORA
nucleus comply --jurisdiction sg-mas-trm    # Singapore MAS TRM
nucleus comply --jurisdiction us-soc2       # US SOC2
```

| Jurisdiction | Retention | HITL Ops | Kill Switch |
|--------------|-----------|----------|-------------|
| `eu-dora` | 7 years | 5 types | Required |
| `sg-mas-trm` | 5 years | 5 types | Required |
| `us-soc2` | 1 year | 3 types | Optional |
| `global-default` | 90 days | 2 types | Optional |

---

## Telemetry

Nucleus collects anonymous, aggregate usage statistics (command name, duration, error type, versions, OS). No engram content, no file paths, no prompts, no API keys, no PII — ever.

```bash
nucleus config --no-telemetry
# or: NUCLEUS_ANON_TELEMETRY=false
```

See [TELEMETRY.md](TELEMETRY.md) for details.

---

## Contributing

- **Bug?** Open an [Issue](https://github.com/eidetic-works/nucleus-mcp/issues)
- **Feature idea?** Start a [Discussion](https://github.com/eidetic-works/nucleus-mcp/discussions)
- **Code?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Chat?** [Discord](https://discord.gg/RJuBNNJ5MT)

## License

MIT © 2026 | [hello@nucleusos.dev](mailto:hello@nucleusos.dev)
