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

Full documentation: [docs/RABBITHOLE.md](docs/RABBITHOLE.md) — also installed with the package, at `<site-packages>/mcp_server_nucleus/docs/RABBITHOLE.md`.

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

**ALIGN** — One-call corrections. `nucleus review` records a verdict against a prior decision, which becomes a training pair and an event.

**COMPOUND** — Deltas measure the gap between intent and reality. Recurring patterns become strategy. Negative deltas become training signal.

Every tool response shows frontier health:
```
[frontiers: GROUND 42 | ALIGN 12 | COMPOUND 28]
```

---

## Quick Start

**Hosted access is not currently available.** The remote MCP endpoint is
withdrawn pending an access-control review. Use the local install below.

**Local install (Cursor, Windsurf, Claude Desktop):**

```bash
pip install nucleus-mcp
nucleus init --recipe founder
```

Two commands. Nucleus is running. `nucleus init` seeds `.brain/`, writes a project-local `.mcp.json`, and offers to configure every AI client you have installed. Say yes, then restart the client.

`nucleus build` additionally needs a coding-agent CLI on PATH — any one of `claude` (npm i -g @anthropic-ai/claude-code), `devin`, or `agy`, already authenticated (`claude`/`devin`/`agy` login once, separately). Without one, `build` stops at the plan stage. If `build` reports `status='error'` without a clear cause, the vendor CLI's own error (e.g. an expired login) lands in `.brain/relay/cross_vendor/*.json` — check the newest file there.

---

## What It Does

**30 MCP tools** across 16 facades, exposing **210 actions**, plus 19 `brain://`
resources and 8 prompts. Regenerate these with `python3 tools_audit/count_surface.py`
rather than editing them by hand — three hand-maintained copies of this number had
drifted apart before that script existed.

- **GROUND** — Execution verification (5 tiers: diff, syntax, imports, tests, runtime)
- **ALIGN** — Human corrections (verdict + delta + DPO + event in one call)
- **Memory** — Engrams that persist across sessions. Write once, recall forever.
- **Sessions** — Save context, resume later. Session arc shows your last 3 sessions.
- **Tasks** — Priority queue with escalation, HITL gates, and heartbeat monitoring.
- **Governance** — Kill switch, compliance configs (EU DORA, MAS TRM, SOC2), audit trails.
- **Orchestration** — Agent slots, multi-brain sync, task dispatch.
- **Archive** — Training pipeline (SFT + DPO), delta tracking, frontier health dashboard.

**Benchmark:** decision-retention-evals — does your AI agent remember why the code is the way it is? (ask on [Discord](https://discord.gg/RJuBNNJ5MT) for the current mirror)

---

## Nucleus Pro

Everything above is free (MIT). Nucleus Pro adds verifiable governance:

```bash
nucleus trial                              # 14-day free trial
nucleus compliance-check                   # Score your AI governance
nucleus audit-report --format html -o report.html   # Audit report
```

**$19/month** or **$149/year** — [nucleusos.dev/pricing](https://nucleusos.dev/pricing)

| | Free | Pro |
|---|---|---|
| 30 tools, 19 resources, 8 prompts | Yes | Yes |
| Persistent memory | Yes | Yes |
| Governance & HITL | Yes | Yes |
| Audit trails (DSoR) | Yes | Yes |
| **Signed audit reports** | - | not yet shipped |
| **Compliance exports** | Score only | Full PDF/HTML |
| **Priority issues** | - | Yes |

---

## Install

```bash
pip install nucleus-mcp      # or:  uvx nucleus-mcp  ·  pipx install nucleus-mcp
nucleus init                 # seeds .brain/, then offers to configure your AI clients
```

Requires Python ≥3.10; on 3.14 some dependencies (e.g. `watchdog`) build from
source — 3.11–3.13 install wheels cleanly. `init` writes whichever `nucleus`
binary it resolves first on PATH into the config it generates — with a stale
global install alongside a venv, `pipx`/`uvx` or `which nucleus` keeps the right
one.

`nucleus init` always does three things: seeds `.brain/`, writes a project-local
`.mcp.json` that Claude Code reads in that folder, and runs a memory write-and-recall
self-test so you can see it working before you trust it.

In an interactive terminal it then asks whether to configure your other AI clients.
Answer yes and it writes the `nucleus` entry into every one it finds installed —
**Claude Desktop, Claude Code, Cursor, Windsurf, Antigravity, Devin** — backing up
each file it touches. It tells you how many it configured, and says so plainly when
that number is zero rather than leaving you to wonder.

Run with `--no-wizard`, or in a script where there is no terminal to ask, and it
seeds the brain and the project-local config only. Use `nucleus setup` for the
client configuration in that case.

Then **restart your AI client**. To verify: your client's tool list now shows
`nucleus_*` tools, or run `nucleus doctor`.

An existing `nucleus` entry is never touched unless you pass `--force`. For most
clients a `<config>.json.bak` copy is written before the edit. Claude Code's
`~/.claude.json` is handled differently and deliberately: nucleus writes a temp
file and swaps it in atomically, so a failed write leaves the original exactly as
it was, and no `.bak` is left lying beside it. A client that is installed but has
never had an MCP config gets one created; a client you do not have is left alone
entirely, and `~/.claude.json` is never invented if it is missing.
Already have a `.brain`? Run `nucleus setup` to configure clients without
re-seeding it, with `--dry-run` to preview the exact changes first.

### Claude Desktop — one-click bundle

A one-click **`nucleus.mcpb`** bundle for Claude Desktop is built via
`bash scripts/build_mcpb.sh` (it will be attached to releases once the release
workflow ships it). Opening the bundle with Claude Desktop uses Claude's
built-in uv runtime to fetch and run `nucleus-mcp` — no Python setup required.

### Hosted / no-install access

Currently unavailable. The remote MCP endpoint is withdrawn pending an
access-control review; use a local install.

<details>
<summary>Manual config (fallback)</summary>

If a client isn't auto-detected, run `nucleus setup --dry-run` to print every
location nucleus looks in and the exact `mcpServers` block it would write, then
paste that block into your client's config yourself. `nucleus setup --create`
writes a Claude Code config even when nothing is detected. The full manual
walkthrough lives in [docs/QUICK_START.md](docs/QUICK_START.md), which ships with the package at `<site-packages>/mcp_server_nucleus/docs/QUICK_START.md`.
</details>

### Path Discovery

Nucleus finds your `.brain` automatically:
1. `NUCLEUS_BRAIN_PATH` environment variable (explicit)
2. Walk up from CWD looking for `.brain/` directory
3. Fall back to `$HOME/.nucleus/brain`

This lookup order applies to the running server. `nucleus init` instead seeds
`.brain/` in the directory you run it in (or the `path` argument) — set
`NUCLEUS_BRAIN_PATH` afterwards if you want the server to find a brain placed
somewhere else.

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

- **Bug?** Email [hello@nucleusos.dev](mailto:hello@nucleusos.dev) or report it on [Discord](https://discord.gg/RJuBNNJ5MT)
- **Feature idea?** Bring it to [Discord](https://discord.gg/RJuBNNJ5MT)
- **Code?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Chat?** [Discord](https://discord.gg/RJuBNNJ5MT)

## License

MIT © 2026 | [hello@nucleusos.dev](mailto:hello@nucleusos.dev)


## Companion repositories (optional)

Some deployments keep companion scripts in a repo next to this one. Point nucleus at them with
either:

```bash
export NUCLEUS_SIBLING_REPOS="$HOME/repo-a:$HOME/repo-b"     # os.pathsep-separated
# or, one path per line:
printf '%s\n' "$HOME/repo-a" "$HOME/repo-b" > ~/.config/nucleus/siblings
```

With neither set, nucleus searches only its own repo — no assumptions are made about the host.
A job whose script cannot be found fails with an error naming every location tried.

## Privacy

**Where your memories live depends on which Quick Start option you chose.**

**Option B — local install.** Nucleus is local-first. Engrams, memories and
project state are written to `.brain/` on your machine. Nothing is sent anywhere
unless you configure a relay yourself.

**Option A — no install (`relay.nucleusos.dev`).** This is a **hosted service we
operate**. Your engrams are stored on our servers, not on your machine, and what
is stored is the **full content** of each memory — the `value` field, not just a
key or a timestamp — along with its context label, intensity, version and
timestamps. There is no local `.brain/` in this mode; the relay is the brain.

We keep tenants separated and reachable only with your own bearer token. But
"local-first" does not describe Option A, and it would be wrong to let the word
cover it: if you would not put something on a server we run, do not put it in a
memory while connected this way. Use Option B for that.

An earlier version of this section described only the local case, and understated
what a relay receives. It has been corrected.

**Telemetry:** Anonymous, aggregate usage statistics only (command name, duration, error type, versions, OS). No engram content, no file paths, no prompts, no API keys, no PII — ever. Disable with `nucleus config --no-telemetry` or `NUCLEUS_ANON_TELEMETRY=false`. This is separate from, and unaffected by, which option above you chose.

**Self-hosted relay (optional, Option B):** If you point Nucleus at a relay
endpoint you run, full engram content is synced there — same record shape as
above. That server is yours.

**Contact:** Privacy questions → [hello@nucleusos.dev](mailto:hello@nucleusos.dev)
