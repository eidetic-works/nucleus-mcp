# Nucleus MCP — Marketplace Submission Template

> Single source of truth for all directory/marketplace listings.
> Last verified: 2026-06-23 | Version: 1.13.3 (PyPI) | 17 MCP tools | Hosted endpoint: https://relay.nucleusos.dev/mcp
> Auto-update = listing refreshes when you publish to PyPI/NPM. Manual = needs browser action per release.
>
> **2026-06-23 update:** Official MCP Registry v1.13.3 published with remote endpoint. PR #8552 opened to punkpeye/awesome-mcp-servers (4th attempt — past 3 closed for Glama score C). Perplexity connector confirmed working live; 3 partnership emails sent. Grok Build PR #54 open. Past PRs to 12 other awesome-lists checked — 3 merged, 6 still open, 3 closed.

---

## Standardized Fields

| Field | Value |
|-------|-------|
| **Name** | Nucleus MCP |
| **One-liner** | The MCP server that makes AI outputs more reliable every week. |
| **Short description (SEO)** | Open-source MCP server with persistent memory, execution verification, governance, and compliance for AI agents. Local-first, 17 tools. Hosted endpoint: https://relay.nucleusos.dev/mcp |
| **Version** | 1.13.3 |
| **License** | MIT |
| **GitHub URL** | https://github.com/eidetic-works/nucleus-mcp |
| **PyPI URL** | https://pypi.org/project/nucleus-mcp/ |
| **NPM URL** | https://www.npmjs.com/package/nucleus-mcp |
| **Homepage** | https://nucleusos.dev |
| **Discord** | https://discord.gg/RJuBNNJ5MT |
| **Author** | eidetic-works |
| **Email** | hello@nucleusos.dev |
| **Categories/Tags** | mcp, ai-agents, memory, governance, orchestration, compliance, local-first, model-context-protocol, agent-os, execution-verification |
| **Python version** | >=3.9 |
| **Requires** | No API keys, no cloud accounts. Runs locally. |

### Full Description (2-3 paragraphs)

AI agents hallucinate, break code, and repeat mistakes. Nucleus catches this. It is an open-source MCP server that brings persistent memory, execution verification, governance, and compliance to any AI agent. Every AI output is verified, every correction is recorded, and every mistake trains the system to not repeat it. Locally, on your machine.

The core loop is called Three Frontiers: GROUND verifies execution across 5 tiers (syntax, imports, tests, runtime). ALIGN captures human corrections as structured verdicts. COMPOUND turns the delta between intent and reality into training signal. The result is a reliability flywheel that improves every session. 17 MCP tools cover memory (engrams), sessions, tasks, orchestration, compliance (EU DORA, MAS TRM, SOC2), and a full CLI.

Nucleus is local-first with zero mandatory cloud dependencies. Install with one command (`uvx nucleus-mcp`, `npx nucleus-mcp`, or `pip install nucleus-mcp`), add to any MCP-compatible IDE (Claude Code, Claude Desktop, Cursor, Windsurf, VS Code), and your agent gains persistent memory and governance that survives across sessions.

---

## Install Commands

### One-line per IDE

```
Claude Code:    claude mcp add nucleus -- uvx nucleus-mcp
Cursor:         cursor://anysphere.cursor-deeplink/mcp/install?name=nucleus&config=eyJuYW1lIjoibnVjbGV1cyIsInR5cGUiOiJjb21tYW5kIiwiY29tbWFuZCI6Im5weCIsImFyZ3MiOlsiLXkiLCJudWNsZXVzLW1jcCJdfQ==
Claude Desktop: Download nucleus.mcpb from https://github.com/eidetic-works/nucleus-mcp/releases/latest and double-click
Any IDE:        pip install nucleus-mcp && nucleus init
```

### Runtime install commands

```bash
# uvx (Python — zero install, recommended)
uvx nucleus-mcp

# npx (Node — zero install)
npx -y nucleus-mcp

# pip (traditional)
pip install nucleus-mcp
```

---

## MCP Config JSON

### uvx (Python — zero install)

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "uvx",
      "args": ["nucleus-mcp"],
      "env": { "NUCLEUS_BRAIN_PATH": ".brain" }
    }
  }
}
```

### npx (Node — zero install)

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "npx",
      "args": ["-y", "nucleus-mcp"],
      "env": { "NUCLEUS_BRAIN_PATH": ".brain" }
    }
  }
}
```

### pip (traditional — `pip install nucleus-mcp` first)

```json
{
  "mcpServers": {
    "nucleus": {
      "command": "nucleus-mcp",
      "env": { "NUCLEUS_BRAIN_PATH": ".brain" }
    }
  }
}
```

### Config file locations

| IDE | Config path |
|-----|-------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| Claude Code | `.mcp.json` in project root |
| Cursor | `~/.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| VS Code | `.vscode/mcp.json` in project |

---

## Key Features (for marketplace bullet lists)

- 17 MCP tools — memory (engrams), sessions, tasks, governance, orchestration, compliance, archive
- Three Frontiers reliability loop: GROUND (5-tier execution verification), ALIGN (human corrections), COMPOUND (training signal from deltas)
- Persistent engram memory that survives across sessions — write once, recall forever
- Compliance in one command: EU DORA, Singapore MAS TRM, US SOC2, with audit report generation
- Full CLI alongside MCP tools — pipe-friendly, auto-detects TTY vs JSON
- Local-first: zero mandatory cloud dependencies, all data stays on your machine
- Works with Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, and any MCP-compatible IDE
- Three install runtimes: uvx, npx, pip — same server, same tools
- Agent-native CLI with structured error envelopes, semantic exit codes, and SKILL.md
- Session management with save/resume, context inheritance, and session arc
- Task queue with priority, escalation, HITL gates, and heartbeat monitoring
- Recipe system for instant persona setup: founder, SRE, ADHD brain
- Kill switch governance with consent management and audit trails
- Multi-agent orchestration with slots, federation, and multi-brain sync
- Anonymous opt-out telemetry with full transparency (TELEMETRY.md)

---

## Screenshots / Assets

### Existing assets in repo

| Asset | Path | Dimensions | Status |
|-------|------|------------|--------|
| Logo (square) | `logo.png` | 1024x1024 PNG RGBA | EXISTS |
| Social preview | `docs/social-preview.png` | 1200x630 PNG RGBA | EXISTS |
| Social preview (HQ) | `docs/social-preview-hq.png` | 2736x1427 PNG RGBA | EXISTS |
| Favicon (SVG) | `website/public/favicon.svg` | SVG | EXISTS |

### Assets needed for submissions

| Asset | Spec | Needed by | Status |
|-------|------|-----------|--------|
| Logo 400x400 PNG | Resize from `logo.png` (1024x1024) | Most directories | DERIVE from existing |
| Logo 200x200 PNG | Resize from `logo.png` | Some directories | DERIVE from existing |
| Logo 128x128 PNG | Resize from `logo.png` | Smithery, Glama | DERIVE from existing |
| Logo 64x64 PNG | Resize from `logo.png` | Favicon variants | DERIVE from existing |
| Social card 1280x640 | Resize from `docs/social-preview-hq.png` | GitHub, directories | DERIVE from existing |
| Social card 1200x628 | Standard OG image | Twitter/LinkedIn shares | DERIVE from social-preview.png |
| Screenshot: tool list | Terminal showing `nucleus status --health` | Marketplace galleries | NEEDS CAPTURE |
| Screenshot: Three Frontiers footer | Tool response showing frontier health line | Marketplace galleries | NEEDS CAPTURE |
| Screenshot: compliance report | `nucleus audit-report --format html` output | Marketplace galleries | NEEDS CAPTURE |
| GIF/video: install-to-first-tool | 30-second demo of install + first engram write | Directories with video support | NEEDS CAPTURE |

**Quick resize command (run once to generate all sizes):**

```bash
cd /path/to/mcp-server-nucleus
mkdir -p docs/assets
sips -z 400 400 logo.png --out docs/assets/logo-400.png
sips -z 200 200 logo.png --out docs/assets/logo-200.png
sips -z 128 128 logo.png --out docs/assets/logo-128.png
sips -z 64 64 logo.png --out docs/assets/logo-64.png
sips -z 640 1280 docs/social-preview-hq.png --out docs/assets/social-1280x640.png
```

---

## Per-Channel Submission Tracker

> **Verified 2026-06-23.** Each entry includes: live URL, auto-update behavior, and what needs manual action per release.
> Past verification was 2026-04-04; changes since then marked with **[2026-06-23]**.

### Tier 1 — Official / High-Authority

| Channel | Live URL | Status | Auto-updates? | Manual action per release |
|---------|----------|--------|---------------|--------------------------|
| **MCP Official Registry** | https://registry.modelcontextprotocol.io/v0.1/servers/io.github.eidetic-works%2Fnucleus/versions | **LIVE — v1.13.3 [2026-06-23]** with remote endpoint `https://relay.nucleusos.dev/mcp`. Past versions: v1.0.4 (Feb 10), v1.8.0 (Apr 4), v1.13.0 (Jun 13), v1.13.1 (Jun 14). | NO — `mcp-publisher publish` CLI | Run `mcp-publisher publish` after each PyPI release. Auth: GitHub OAuth (device code flow). |
| **Anthropic Claude Connectors Directory** | [Submission checklist](../docs/connectors/CLAUDE_DIRECTORY_SUBMISSION.md) | **SUBMITTED — in review [2026-06-22]**. Status check email sent to mcp-review@anthropic.com. | N/A | Awaiting Anthropic reply |
| **ChatGPT App Catalog** | [Submission checklist](../docs/connectors/CHATGPT_APP_SUBMISSION.md) | **SUBMITTED — in review** (submitted prior session). App ID recorded. | N/A | Awaiting OpenAI review |
| **ChatGPT Connector (Developer Mode)** | [Setup guide](../docs/connectors/CHATGPT_CONNECTOR.md) | **READY** — OAuth 2.1 server + domain verification live | N/A | Users paste URL manually |
| **Perplexity Connector** | [Setup guide](../docs/connectors/PERPLEXITY_CONNECTOR.md) | **WORKING — live demo confirmed [2026-06-23]**. Connector pulls 19 engrams, 178 relay messages, full system health. 3 partnership emails sent (partnerships@perplexity.ai ×2 + cold to Dmitry Shevelenko CBO). No submission form exists — BD-led partnership. | N/A | Awaiting Perplexity partnership team reply. Users can paste URL now. |
| **Grok Build Plugin Marketplace** | https://github.com/xai-org/plugin-marketplace/pull/54 | **PR #54 OPEN — CI green [2026-06-22]**. Plugin structure in public repo (`.grok-plugin/plugin.json`, `.mcp.json`, `skills/nucleus-memory/SKILL.md`). | NO — PR-based | Awaiting xAI maintainer merge |
| **Microsoft 365 Copilot** | [Submission prep](../docs/connectors/MICROSOFT_365_COPILOT_SUBMISSION.md) | **READY** — `/mcp-readonly` endpoint built (4 tools, all readOnlyHint=True). Remaining: deploy to VM + apply to Microsoft for Startups for BD rep. | N/A | Deploy endpoint, then apply at https://foundershub.startups.microsoft.com/signup |
| **Claude Desktop .mcpb** | dist/nucleus.mcpb | BUILT (needs GH release upload) | NO | Upload .mcpb to GitHub release |
| **Cline MCP Marketplace** | https://github.com/cline/mcp-marketplace/issues/1236 | **OPEN (issue) [verified 2026-06-23]** | NO | Awaiting maintainer review |

### Tier 2 — Major MCP Directories

| Channel | Live URL | Status | Auto-updates? | Manual action per release |
|---------|----------|--------|---------------|--------------------------|
| **Glama** | https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp | **LISTED [verified 2026-06-23]** — Scores: Quality A, Coherence A, **Maintenance C** (CI was failing — now FIXED [2026-06-23], awaiting Glama re-scan). Badge: AAC. | PARTIAL — re-scans repo | Wait for Glama re-scan (24-48h) → maintenance score should improve → unblocks punkpeye PR |
| **Smithery** | https://smithery.ai/server/@eidetic-works/nucleus-mcp | **LISTED [re-published 2026-06-23]** — "No capabilities found" (scan hits OAuth metadata wall). Connector works fine despite thin listing. | NO — CLI publish | `smithery mcp publish "https://relay.nucleusos.dev/mcp" -n @eidetic-works/nucleus-mcp` |
| **mcp.so** | https://mcp.so/server/nucleus-mcp | **LISTED [verified 2026-06-23]** — shows config JSON, "Try in Playground" button. | YES — auto-indexed | None |
| **Cursor Directory** | https://cursor.directory (search "Nucleus MCP") | LISTED — confirmed in browser 2026-04-04, has "Add to Cursor" button | PARTIAL — reads .mcp.json from repo | Edit via cursor.directory plugin edit page if description changes |
| **MCP Hub** | https://github.com/MCP-Club/mcphub/issues/13 | OPEN (issue) | NO | Awaiting maintainer |
| **PulseMCP** | https://pulsemcp.com | **EMAIL SENT to hello@pulsemcp.com [2026-06-23]**. PulseMCP auto-ingests from Official MCP Registry daily, processes weekly (~7 days). | YES — auto-ingests from official registry | None — will auto-list within 7 days of registry publish |
| **MCPServers.org** | https://mcpservers.org | LISTED (2026-04-04) — auto-scraped | YES — auto-scrapes from GitHub/PyPI | None |
| **Docker MCP Registry** | https://github.com/docker/mcp-registry/pull/2298 | **OPEN (PR) [verified 2026-06-23]** | NO | Awaiting maintainer review |
| **MCPMarket** | https://mcpmarket.com (search "Nucleus") | LISTED (2026-04-04) — auto-indexed | YES — scrapes GitHub | None |
| **MCP.Directory** | https://mcp.directory | SUBMITTED 2026-04-04 — status unknown (site live, search returns nothing for "nucleus") | UNKNOWN | Check in browser |
| **FindMCPServers** | https://findmcpservers.com | SUBMITTED 2026-04-04 — status unknown (site live, search returns nothing for "nucleus") | UNKNOWN | Check in browser |
| **mcpserver.dev** | https://mcpserver.dev | SUBMITTED 2026-04-04 — status unknown (site live) | UNKNOWN | Check in browser |
| **mcpserverhub.com** | https://mcpserverhub.com | SUBMITTED 2026-04-04 via Tally.so — status unknown (site live) | UNKNOWN | Check in browser |

### Tier 3 — GitHub PR-based Directories

| Channel (stars) | PR | Status [verified 2026-06-23] | Auto-updates? |
|-----------------|-----|--------|---------------|
| **punkpeye/awesome-mcp-servers** (84K) | #1887, #4102, #4104 (all CLOSED), **#8552 (OPEN [2026-06-23])** | 3 past PRs closed — require Glama A scores for quality AND maintenance. We have AAC (C for maintenance). New PR #8552 will likely be closed too unless CI is fixed. | NO |
| **appcypher/awesome-mcp-servers** | fork branches exist (add-nucleus-mcp, add-nucleus-mcp-server, add-nucleus-v3) | WRONG UPSTREAM — appcypher is a separate repo, not the canonical one. Fork has stale entry ("114 tools"). Skip. | NO |
| **e2b-dev/awesome-ai-agents** (13K) | #671 | **OPEN** — awaiting review | NO |
| **lobehub/lobe-chat-plugins** | #85 | **OPEN** — Sourcery bot commented | NO |
| **yzfly/Awesome-MCP-ZH** (6.7K) | #144 | **CLOSED** | NO |
| **YuzeHao2023/Awesome-MCP-Servers** (1K) | #157 | **OPEN** — awaiting review | NO |
| **rohitg00/awesome-devops-mcp-servers** (970) | #142 | **MERGED** ✅ | NO |
| **MobinX/awesome-mcp-list** (881) | #180 | **OPEN** — awaiting review | NO |
| **TensorBlock/awesome-mcp-servers** (599) | #315 | **MERGED** ✅ | NO |
| **apappascs/mcp-servers-hub** (315) | #18 | **OPEN** — Gemini bot reviewed | NO |
| **PipedreamHQ/awesome-mcp-servers** (260) | #61 | **OPEN** — awaiting review | NO |
| **AlexMili/Awesome-MCP** (138) | #81 | **MERGED** ✅ | NO |

**Summary: 3 merged, 6 open, 3 closed (punkpeye ×3), 1 closed (yzfly)**

### Tier 4 — Package Registries

| Channel | Live URL | Version [2026-06-23] | Auto-updates? |
|---------|----------|---------|---------------|
| **PyPI** | https://pypi.org/project/nucleus-mcp/ | v1.13.3 | NO — manual `python -m build && twine upload` |
| **NPM** | https://www.npmjs.com/package/nucleus-mcp | **DOES NOT EXIST** — npm package was never published. server.json npm entry removed [2026-06-23]. | N/A |
| **GitHub Releases** | https://github.com/eidetic-works/nucleus-mcp/releases | v1.13.3 | NO — manual `gh release create` |
| **Homebrew** | https://github.com/eidetic-works/homebrew-nucleus | v1.13.3 | NO — manual formula update |

### Tier 5 — IDE Marketplaces

| Channel | Status | Notes |
|---------|--------|-------|
| **VS Code Marketplace** | LIVE | `eidetic-works.nucleus-bridge` extension published |
| Open VSX, Cursor Marketplace, JetBrains, Windsurf | NOT STARTED | Require extension wrappers. Future work. |

### Tier 6 — Web Form Directories

| # | Directory | Submit URL | Status [2026-06-23] | Notes |
|---|-----------|-----------|---------------------|-------|
| 1 | mcpserver.dev | https://mcpserver.dev | SUBMITTED 2026-04-04 — site live, listing unverified | Check in browser |
| 2 | mcpserverhub.com | https://mcpserverhub.com/submit | SUBMITTED 2026-04-04 — site live, listing unverified | Check in browser |
| 3 | allmcpservers.com | https://allmcpservers.com | SUBMIT FAILED — spinner hangs, broken reCAPTCHA | Skip — site broken |
| 4 | mcpdrops.com | https://mcpdrops.com/submit | NOT SUBMITTED | Requires login/account first |
| 5 | mcpserverfinder.com | info@mcpserverfinder.com | NOT SUBMITTED | Email-only submission |

**DEAD — skip these:**
- ~~mcpserve.com~~ — Netlify 404, site dead
- ~~mcp-server-directory.com~~ — Shows "0 MCP Servers, 0 MCP Clients" — empty/dead
- ~~mcpserverdirectory.org~~ — DNS timeout
- ~~mcpservers.net~~ — Connection refused / SSL error
- ~~mcp-servers-hub.net~~ — Connection refused / SSL error
- ~~aiagentslist.com/submit~~ — 404 on submit path
- ~~mcpregistry.online~~ — Read-only, no submit form
- ~~allmcpservers.com~~ — Submit form broken (spinner hangs, reCAPTCHA error)

### Tier 7 — AI/Developer Tool Directories (NOT STARTED)

Product Hunt, AlternativeTo, There's An AI For That, Future Tools, AI Tool Guru, Portkey.ai — save for coordinated launch.

### Tier 8 — Community / Social (NOT STARTED)

Hacker News, Reddit (r/MCP, r/ClaudeAI, r/LocalLLaMA), Dev.to, Hashnode — save for coordinated launch.

---

## Blockers, Unknowns & Manual Checks

> Things that need attention, are stuck, or can't be verified from CLI. Check these periodically.
> **Last reviewed: 2026-06-23.**

### BLOCKED (needs action to unblock)

| Channel | Blocker | What to do |
|---------|---------|------------|
| **punkpeye/awesome-mcp-servers** (84K stars) | Requires Glama A scores for quality AND maintenance. We have AAC (C for maintenance). 3 past PRs closed; PR #8552 will likely be closed too. | **CI FIXED [2026-06-23]** — ruff ignore list expanded (F403/F405/F821/E731/E401/F811), test job handles missing tests/ dir, separate public CI workflow (ci-public.yml). All 8 CI jobs now pass on public repo. Waiting for Glama re-scan to update maintenance score from C → A/B. |
| **Microsoft 365 Copilot** | ~~readOnlyHint strategy~~ RESOLVED — `/mcp-readonly` endpoint built (4 tools, all readOnlyHint=True). Remaining blocker: deploy to VM + apply to Microsoft for Startups for BD rep. | Deploy endpoint, then apply at https://foundershub.startups.microsoft.com/signup |
| **Perplexity official gallery** | No submission form — BD-led partnership. 3 emails sent, no reply yet. | Wait for reply from partnerships@perplexity.ai or Dmitry Shevelenko. Users can paste URL now (connector works). |
| **Claude Desktop .mcpb** | Built but not uploaded to GitHub release. | Upload dist/nucleus.mcpb as asset on next `gh release create`. |

### RESOLVED [2026-06-23]

| Channel | Was | Now |
|---------|-----|-----|
| **MCP Official Registry** | Published without remote endpoint, invalid npm package entry | v1.13.3 published WITH remote endpoint, npm entry removed |
| **PulseMCP** | Not listed, no submission path known | Email sent to hello@pulsemcp.com; auto-ingests from official registry within 7 days |
| **Glama Quality Score** | Was C (2.0-2.8/5.0) for TDQS | Now A (4.7/5.0) — tool descriptions improved. Maintenance is now the C score. |
| **Smithery** | CLI broken for Python stdio | Re-published via `smithery mcp publish` — listing refreshed, capabilities still thin (OAuth scan issue, cosmetic) |
| **NPM package** | Listed in server.json but never published | Removed from server.json — was causing registry validation failures |

### UNSURE / NEEDS MANUAL CHECK IN BROWSER

| Channel | Why unsure | How to check |
|---------|-----------|--------------|
| **MCP.Directory** | Submitted 2026-04-04, site live but search returns nothing for "nucleus" | Open https://mcp.directory in browser, search "nucleus" |
| **FindMCPServers** | Submitted 2026-04-04, site live but search returns nothing for "nucleus" | Open https://findmcpservers.com in browser, search "nucleus" |
| **mcpserver.dev** | Submitted 2026-04-04, site live | Open https://mcpserver.dev in browser, search "nucleus" |
| **mcpserverhub.com** | Submitted 2026-04-04 via Tally.so, site live | Open https://mcpserverhub.com in browser, search "nucleus" |
| **Cursor Directory** | Listed (confirmed 2026-04-04) but curl can't find it (SPA) | Open https://cursor.directory, search "Nucleus MCP" |
| **MCPMarket** | Listed (confirmed 2026-04-04) but returns 403 to curl | Open https://mcpmarket.com, search "Nucleus" |
| **MCPServers.org** | Listed (2026-04-04), auto-scraped | Open https://mcpservers.org, search "Nucleus" |

### STALE DESCRIPTIONS (needs update after messaging changes)

| Channel | Current description | Should be |
|---------|-------------------|-----------|
| **Glama** | "unified memory layer that synchronizes context..." (old, from ~v1.8) | Should refresh from updated README on next scan |
| **Smithery** | "Agent control plane that runs on your computer." | Re-published [2026-06-23] but capabilities thin — may need server-card.json at `/.well-known/mcp/server-card.json` |
| **mcp.so** | "Sovereign Agent Control Plane. Local-first memory, governance, and audit trails..." | Reasonably current |

---

## Release Checklist (what to update per version)

### Always (automated or one-command)
1. `pip install` + `twine upload` → PyPI auto-updates
2. `gh release create` → GitHub Releases
3. MCPMarket auto-re-scrapes from GitHub
4. MCPServers.org auto-scrapes from GitHub/PyPI
5. mcp.so auto-indexes from GitHub

### Manual per major release
1. **MCP Official Registry** — `mcp-publisher publish` (GitHub OAuth device code flow)
2. **Homebrew** — Update formula in eidetic-works/homebrew-nucleus
3. **Cursor Directory** — Edit plugin page if description changed
4. **Glama** — Re-scan triggered by repo changes; check score page after release
5. **Smithery** — `smithery mcp publish "https://relay.nucleusos.dev/mcp" -n @eidetic-works/nucleus-mcp`
6. **Awesome lists** — Only if merged PRs need version bump (usually not)

### Never (one-time submissions)
- All Tier 3 GitHub PRs (once merged, they stay)
- All Tier 6 web form directories (once listed, they stay)
- Cline marketplace issue
- Docker MCP Registry PR

### NPM — DEFUNCT
~~`cd npm-wrapper && npm publish` → NPM auto-updates → MCP Registry auto-syncs~~
NPM package was never published. server.json npm entry removed 2026-06-23.
Do NOT re-add npm package reference unless an actual npm package is published.

---

## Submission Copy

### Short (under 280 chars)
Nucleus MCP -- open-source MCP server with 17 tools for persistent memory, execution verification, and compliance. Local-first. Works with Claude, Cursor, VS Code. One command: uvx nucleus-mcp https://github.com/eidetic-works/nucleus-mcp

### Forum intro (1 paragraph)
Nucleus is an open-source MCP server that makes AI agents more reliable over time. It provides 17 tools for persistent memory (engrams), 5-tier execution verification (GROUND), human correction capture (ALIGN), and automatic training signal generation (COMPOUND). It includes compliance configs for EU DORA, Singapore MAS TRM, and SOC2. Everything runs locally with zero cloud dependencies. Install with `uvx nucleus-mcp` and add to Claude Code, Cursor, or any MCP-compatible IDE.

### Tags
Primary: `mcp`, `model-context-protocol`, `ai-agents`, `ai-tools`
Secondary: `memory`, `governance`, `compliance`, `orchestration`, `local-first`

### Competitive positioning
- Alternative to: Context7, MemoryMesh, basic MCP memory servers
- Differentiators: execution verification (GROUND), compliance frameworks, 17 tools (not just memory), training signal generation, full CLI
- Not competing with: LangChain, CrewAI, AutoGen (agent frameworks; Nucleus is agent infrastructure)
