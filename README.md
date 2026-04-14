<!-- mcp-name: io.github.eidetic-works/nucleus -->
# Nucleus

> The MCP server that makes AI outputs more reliable every week.

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![NPM](https://img.shields.io/badge/npm-nucleus--mcp-red)](https://www.npmjs.com/package/nucleus-mcp)
[![nucleus-mcp MCP server](https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp/badges/score.svg)](https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp)
[![SafeSkill 30/100](https://img.shields.io/badge/SafeSkill-30%2F100_Blocked-red)](https://safeskill.dev/scan/eidetic-works-nucleus-mcp)

AI agents hallucinate, break code, and repeat mistakes. Nucleus catches this. Every AI output is verified, every correction is recorded, and every mistake trains the system to not repeat it. Locally, on your machine.

---

## Three Frontiers

The core loop that makes AI reliability compound over time:

```
  GROUND              ALIGN               COMPOUND
  ──────              ─────               ────────
  Machine verifies    Human corrects      System learns

  AI writes code  →  You fix a mistake →  Delta recorded
  GROUND checks   →  Verdict stored    →  DPO pair created
  Receipt logged  →  Event emitted     →  Training data grows
       │                   │                    │
       └───────────────────┴────────────────────┘
                    Reliability improves
```

**GROUND** — 5-tier execution verification. Syntax, imports, tests, runtime. Goes outside the formal system to check the AI's work.

**ALIGN** — One-call corrections. `nucleus_align(action="correct", params={context, correction})`. Each correction automatically records a verdict, creates a training pair, and emits an event.

**COMPOUND** — Deltas measure the gap between intent and reality. Recurring patterns become strategy. Negative deltas become training signal.

Every tool response shows frontier health:
```
[frontiers: GROUND 42 | ALIGN 12 | COMPOUND 28]
```

---

## Quick Start

```bash
pip install nucleus-mcp
nucleus init --recipe founder
```

Two commands. Nucleus is running. AI outputs are now verified.

---

## What It Does

**114 MCP tools** across 13 facades:

- **GROUND** — Execution verification (5 tiers: diff, syntax, imports, tests, runtime)
- **ALIGN** — Human corrections (verdict + delta + DPO + event in one call)
- **Memory** — Engrams that persist across sessions. Write once, recall forever.
- **Sessions** — Save context, resume later. Session arc shows your last 3 sessions.
- **Tasks** — Priority queue with escalation, HITL gates, and heartbeat monitoring.
- **Governance** — Kill switch, compliance configs (EU DORA, MAS TRM, SOC2), audit trails.
- **Orchestration** — Agent slots, multi-brain sync, task dispatch.
- **Archive** — Training pipeline (SFT + DPO), delta tracking, frontier health dashboard.

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
| 13 tools, 10 resources, 3 prompts | Yes | Yes |
| Persistent memory | Yes | Yes |
| Governance & HITL | Yes | Yes |
| Audit trails (DSoR) | Yes | Yes |
| **Signed audit reports** | - | Ed25519 |
| **Compliance exports** | Score only | Full PDF/HTML |
| **Priority issues** | - | Yes |

---

## Install

### One-Click

| IDE | Install |
|-----|---------|
| Cursor | [Add to Cursor](cursor://mcp/install?name=Nucleus%20MCP&config=eyJjb21tYW5kIjogIm5weCIsICJhcmdzIjogWyIteSIsICJudWNsZXVzLW1jcCJdfQ==) |
| Claude Code | `npx -y nucleus-mcp` |
| Any IDE | `pip install nucleus-mcp` |

### pip / npx

```bash
pip install nucleus-mcp
```

Or use npx (zero Python setup required):

```bash
npx -y nucleus-mcp
```

## Configure Your MCP Client

### Claude Desktop / Cursor / Windsurf

Add to your MCP config (`claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "npx",
      "args": ["-y", "nucleus-mcp"]
    }
  }
}
```

<details>
<summary>Alternative: use pip install directly</summary>

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "python3",
      "args": ["-m", "mcp_server_nucleus"],
      "env": {
        "NUCLEAR_BRAIN_PATH": "/path/to/your/project/.brain"
      }
    }
  }
}
```
</details>

### Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "npx",
      "args": ["-y", "nucleus-mcp"]
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
