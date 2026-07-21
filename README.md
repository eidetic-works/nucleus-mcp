<!-- mcp-name: io.github.eidetic-works/nucleus -->
# `.brain` — the portable decision log

> The portable decision log your AI tools all read. One MCP server. Any AI tool. Plain files.

[![PyPI version](https://badge.fury.io/py/nucleus-mcp.svg)](https://badge.fury.io/py/nucleus-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-brightgreen)](https://modelcontextprotocol.io)
[![NPM](https://img.shields.io/badge/npm-nucleus--mcp-red)](https://www.npmjs.com/package/nucleus-mcp)
[![nucleus-mcp MCP server](https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp/badges/score.svg)](https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp)

Every AI coding session starts by re-explaining context the last session already knew. `.brain` is a folder in your repo that Claude Code, Cursor, and Codex all read via one MCP server. Decisions, policies, plans — written once, remembered across every session and every tool.

MIT licensed. File-based (plain JSON + markdown). No embeddings. No vendor lock-in.

---

## Also included: nucleus-rabbithole

`nucleus-mcp` ships a second, fully independent tool: **nucleus-rabbithole**,
a rabbit-hole depth tracker for focus-prone developers.

It gives your AI a push/pop depth stack, a context-switch thrash detector,
an open-loop externaliser, and a weekly review — all backed by local SQLite,
no network, no daemon.

```bash
# Already installed with nucleus-mcp — just run:
nucleus-rabbithole
```

Claude Code `.mcp.json` snippet:
```json
{
  "mcpServers": {
    "nucleus-rabbithole": {
      "command": "nucleus-rabbithole",
      "args": []
    }
  }
}
```

Full documentation: [docs/RABBITHOLE.md](docs/RABBITHOLE.md)

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

**Option A — No install (ChatGPT, Claude, Perplexity):**

Add `https://relay.nucleusos.dev/mcp` as a remote MCP server in your platform's connector settings. That's it — your AI now has persistent memory.

**Option B — Local install (Cursor, Windsurf, Claude Desktop):**

```bash
pip install nucleus-mcp
nucleus init --recipe founder
```

Two commands. Nucleus is running. AI outputs are now verified. `nucleus init` writes a local `.mcp.json` for Claude Code — restart Claude Code and you're set. For other clients (Cursor, Windsurf, Claude Desktop), run `nucleus setup` after.

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
- **Cross-vendor delegate** — Hand tasks to other AI vendors (Gemini, Devin/GLM) with automatic permission flags, output capture, and status reporting. Includes `plan_review_loop` — multi-round plan drafting + adversarial review across different model families. ([docs/PLAN_REVIEW_LOOP.md](docs/PLAN_REVIEW_LOOP.md))
- **Archive** — Training pipeline (SFT + DPO), delta tracking, frontier health dashboard.

**Benchmark:** [decision-retention-evals](https://github.com/eidetic-works/decision-retention-evals) — does your AI agent remember why the code is the way it is?

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

One command installs the CLI and auto-configures every MCP client you have —
**Claude Desktop, Claude Code, Cursor, Windsurf, and Antigravity** — backing up
each config file it touches. No hand-editing JSON.

```bash
pip install nucleus-mcp      # or:  uvx nucleus-mcp  ·  pipx install nucleus-mcp
nucleus init                 # seeds .brain/ and writes .mcp.json (Claude Code)
nucleus setup                # (optional) configure Cursor, Windsurf, Claude Desktop
```

Then **restart your AI client**. To verify: your client's tool list now shows
`nucleus_*` tools, or run `nucleus doctor`.

`nucleus init` writes a `<config>.json.bak` backup before editing, and never
touches an existing `nucleus` entry unless you pass `--force`. Already have a
`.brain`? Run `nucleus setup` to (re)configure clients without re-seeding it —
add `--dry-run` to preview the exact changes first.

### Claude Desktop — one-click bundle

A one-click **`nucleus.mcpb`** bundle for Claude Desktop is built via
`bash scripts/build_mcpb.sh` (it will be attached to releases once the release
workflow ships it). Opening the bundle with Claude Desktop uses Claude's
built-in uv runtime to fetch and run `nucleus-mcp` — no Python setup required.

### No install (ChatGPT, Claude.ai, Perplexity)

Add `https://relay.nucleusos.dev/mcp` as a remote MCP server in your platform's
connector settings. Persistent memory, nothing to install.

<details>
<summary>Manual config (fallback)</summary>

If a client isn't auto-detected, `nucleus init` prints a ready-to-paste
`mcpServers` block and copies it to your clipboard, along with each client's
config-file location. The full manual walkthrough lives in
[docs/QUICK_START.md](docs/QUICK_START.md).
</details>

### Path Discovery

Nucleus finds your `.brain` automatically:
1. `NUCLEUS_BRAIN_PATH` environment variable (explicit)
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

See [docs/SECURITY_WHITEPAPER.md](docs/SECURITY_WHITEPAPER.md) for telemetry details.

---

## Contributing

- **Bug?** Open an [Issue](https://github.com/eidetic-works/nucleus-mcp/issues)
- **Feature idea?** Start a [Discussion](https://github.com/eidetic-works/nucleus-mcp/discussions)
- **Code?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Chat?** [Discord](https://discord.gg/RJuBNNJ5MT)

## License

MIT © 2026 | [hello@nucleusos.dev](mailto:hello@nucleusos.dev)

## Privacy

Nucleus is a local-first tool. All engrams, memories, and project state are stored on your machine in `.brain/` — no personal data is sent to any server unless you explicitly configure a remote relay.

**Telemetry:** Anonymous, aggregate usage statistics only (command name, duration, error type, versions, OS). No engram content, no file paths, no prompts, no API keys, no PII — ever. Disable with `nucleus config --no-telemetry` or `NUCLEUS_ANON_TELEMETRY=false`.

**Remote relay (optional):** If you configure a remote relay endpoint, engram metadata is synced to your own relay server. You control the relay — no third-party data sharing.

**Contact:** Privacy questions → [hello@nucleusos.dev](mailto:hello@nucleusos.dev)
