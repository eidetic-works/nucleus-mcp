# Nucleus MCP — Marketplace Submission Template

> Single source of truth for all directory/marketplace listings.
> Last verified: 2026-04-04 | Version: 1.8.0 (PyPI) / 1.8.1 (NPM)
> Auto-update = listing refreshes when you publish to PyPI/NPM. Manual = needs browser action per release.

---

## Standardized Fields

| Field | Value |
|-------|-------|
| **Name** | Nucleus MCP |
| **One-liner** | The MCP server that makes AI outputs more reliable every week. |
| **Short description (SEO)** | Open-source MCP server with persistent memory, execution verification, governance, and compliance for AI agents. Local-first, 114 tools. |
| **Version** | 1.8.0 |
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

The core loop is called Three Frontiers: GROUND verifies execution across 5 tiers (syntax, imports, tests, runtime). ALIGN captures human corrections as structured verdicts. COMPOUND turns the delta between intent and reality into training signal. The result is a reliability flywheel that improves every session. 114 MCP tools across 14 facades cover memory (engrams), sessions, tasks, orchestration, compliance (EU DORA, MAS TRM, SOC2), and a full CLI.

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

- 114 MCP tools across 14 facades — memory, sessions, tasks, governance, orchestration, compliance, archive
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

> **Verified 2026-04-04.** Each entry includes: live URL, auto-update behavior, and what needs manual action per release.

### Tier 1 — Official / High-Authority

| Channel | Live URL | Status | Auto-updates? | Manual action per release |
|---------|----------|--------|---------------|--------------------------|
| **MCP Official Registry** | https://registry.modelcontextprotocol.io | LIVE (NPM v1.8.1) | YES — pulls from NPM | None (auto-syncs on npm publish) |
| **Anthropic MCP Gallery** | https://www.anthropic.com/mcp | NOT STARTED | N/A | Submit via Anthropic contact |
| **Claude Desktop .mcpb** | dist/nucleus.mcpb | BUILT (needs GH release upload) | NO | Upload .mcpb to GitHub release |
| **Cline MCP Marketplace** | https://github.com/cline/mcp-marketplace/issues/1236 | OPEN (issue) | NO | Awaiting maintainer review. #1237 closed as dup. |

### Tier 2 — Major MCP Directories

| Channel | Live URL | Status | Auto-updates? | Manual action per release |
|---------|----------|--------|---------------|--------------------------|
| **Glama** | https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp | LISTED — License A, Quality C, Docker release v1.8.0 | PARTIAL — re-scans repo, but Docker release is manual | Redeploy Dockerfile on Glama admin page. Build step: `uv pip install --system --break-system-packages nucleus-mcp` |
| **Smithery** | https://smithery.ai/servers/eidetic-works/nucleus-mcp | LISTED — stale description, deploymentUrl exists, 0 usage | NO — CLI publish required | `npx @smithery/cli mcp publish` (broken for Python stdio servers on CLI v4+, description stuck) |
| **Cursor Directory** | https://cursor.directory (search "Nucleus MCP") | LISTED — confirmed in browser, has "Add to Cursor" button. Stale description updated 2026-04-04. | PARTIAL — reads .mcp.json from repo | Edit via cursor.directory plugin edit page if description changes |
| **MCP Hub** | https://github.com/MCP-Club/mcphub/issues/13 | OPEN (issue) | NO | Awaiting maintainer |
| **PulseMCP** | https://pulsemcp.com | NOT LISTED — curl finds nothing, Cloudflare blocks. Check browser. | UNKNOWN | Submit via web form or email hello@pulsemcp.com |
| **MCPServers.org** | https://mcpservers.org/servers > "Nucleus MCP" | LISTED — shows PyPI 1.8.0, MIT, MCP Compatible, npm badges, Three Frontiers README | YES — auto-scrapes from GitHub/PyPI | None |
| **Docker MCP Registry** | https://github.com/docker/mcp-registry/pull/2298 | OPEN (PR) | NO | Awaiting maintainer review |
| **MCPMarket** | https://mcpmarket.com (search "Nucleus") | LISTED — confirmed in browser 2026-04-04, auto-indexed. Returns 403 to curl. | YES — scrapes GitHub | None (auto-updates from repo) |
| **MCP.Directory** | https://mcp.directory | SUBMITTED 2026-04-04, NOT YET LISTED (24hr review) | UNKNOWN | Check back after review |
| **FindMCPServers** | https://findmcpservers.com | SUBMITTED 2026-04-04, NOT YET LISTED | UNKNOWN | Awaiting review |

### Tier 3 — GitHub PR-based Directories

| Channel (stars) | PR | Status | Auto-updates? |
|-----------------|-----|--------|---------------|
| **punkpeye/awesome-mcp-servers** (84K) | #4104, #4102, #1887 | ALL CLOSED — requires Glama AAA score | NO — re-submit after AAA |
| **appcypher/awesome-mcp-servers** | [compare URL](https://github.com/appcypher/awesome-mcp-servers/compare/main...eidetic-works:awesome-mcp-servers:add-nucleus-mcp-server?expand=1) | PR CREATED (2026-04-04) | NO |
| **e2b-dev/awesome-ai-agents** (13K) | #671 | OPEN — awaiting review | NO |
| **lobehub/lobe-chat-plugins** | #85 | OPEN — Sourcery bot commented | NO |
| **yzfly/Awesome-MCP-ZH** (6.7K) | #144 | OPEN — awaiting review | NO |
| **YuzeHao2023/Awesome-MCP-Servers** (1K) | #157 | OPEN — awaiting review | NO |
| **rohitg00/awesome-devops-mcp-servers** (970) | #142 | OPEN — CodeRabbit bot reviewed | NO |
| **MobinX/awesome-mcp-list** (881) | #180 | OPEN — awaiting review | NO |
| **TensorBlock/awesome-mcp-servers** (599) | #315 | OPEN — awaiting review | NO |
| **apappascs/mcp-servers-hub** (315) | #18 | OPEN — Gemini bot reviewed | NO |
| **PipedreamHQ/awesome-mcp-servers** (260) | #61 | OPEN — awaiting review | NO |
| **AlexMili/Awesome-MCP** (138) | #81 | OPEN — awaiting review | NO |
| **MCP.so** | chatmcp/mcpso#1 comment | NOT LISTED — comment didn't trigger indexing, search returns nothing | NO — needs re-submission or auto-index |

### Tier 4 — Package Registries

| Channel | Live URL | Version | Auto-updates? |
|---------|----------|---------|---------------|
| **PyPI** | https://pypi.org/project/nucleus-mcp/ | v1.8.0 | NO — manual `python -m build && twine upload` |
| **NPM** | https://www.npmjs.com/package/nucleus-mcp | v1.8.1 | NO — manual `cd npm-wrapper && npm publish` |
| **GitHub Releases** | https://github.com/eidetic-works/nucleus-mcp/releases | v1.8.0 | NO — manual `gh release create` |
| **Homebrew** | https://github.com/eidetic-works/homebrew-nucleus | v1.8.0 | NO — manual formula update |

### Tier 5 — IDE Marketplaces (NOT STARTED)

VS Code Marketplace, Open VSX, Cursor Marketplace, JetBrains, Windsurf — all require extension wrappers. Future work.

### Tier 6 — Web Form Directories

| # | Directory | Submit URL | Status (2026-04-04) | Notes |
|---|-----------|-----------|---------------------|-------|
| 1 | mcpserver.dev | https://mcpserver.dev | SUBMITTED 2026-04-04 | Awaiting review |
| 2 | mcpserverhub.com | https://mcpserverhub.com/submit | SUBMITTED 2026-04-04 | Tally.so form, awaiting review |
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

### BLOCKED (needs action to unblock)

| Channel | Blocker | What to do |
|---------|---------|------------|
| **punkpeye/awesome-mcp-servers** (84K stars) | Requires Glama AAA score. All 3 PRs (#1887, #4102, #4104) auto-closed. | Fix TDQS (tool descriptions) → publish to PyPI → redeploy Glama Docker → wait for re-score → re-submit PR |
| **Glama Quality Score** | Tool TDQS scores are C (2.0-2.8/5.0) due to generic inputSchema. glama.json still showing "missing or invalid" as of 2026-04-04. | TDQS fix written in stdio_server.py (enum actions, rich descriptions). Needs PyPI publish + Glama redeploy. glama.json is in public repo — may need Glama re-scan time. |
| **Smithery description** | CLI v4+ broken for Python stdio servers — can't republish to update stale description ("Agent control plane..."). | Wait for Smithery CLI fix, or contact Smithery support. Low priority. |
| **Claude Desktop .mcpb** | Built but not uploaded to GitHub release. | Upload dist/nucleus.mcpb as asset on next `gh release create`. |

### UNSURE / NEEDS MANUAL CHECK IN BROWSER

| Channel | Why unsure | How to check |
|---------|-----------|--------------|
| **PulseMCP** | Cloudflare blocks CLI. Was listed before but curl finds nothing now. | Open https://pulsemcp.com in browser, search "nucleus". If not listed, submit via form or email hello@pulsemcp.com. |
| **MCP.so** | Comment on chatmcp/mcpso#1 didn't trigger indexing. Search returns nothing. | Open https://mcp.so in browser, search "nucleus". May need re-submission. |
| **MCP.Directory** | Submitted 2026-04-04 with 24hr review. Not listed yet. | Check https://mcp.directory after 24hrs. If still missing, resubmit. |
| **FindMCPServers** | Submitted 2026-04-04. Not listed yet. | Check https://findmcpservers.com after a few days. |
| **mcpserver.dev** | Submitted 2026-04-04. Not listed yet. | Check https://mcpserver.dev after a few days. |
| **mcpserverhub.com** | Submitted 2026-04-04 via Tally.so. Not listed yet. | Check https://mcpserverhub.com after a few days. |
| **Cursor Directory** | Listed (confirmed in browser) but curl can't find it (SPA). Description was stale, updated 2026-04-04. | Open https://cursor.directory, search "Nucleus MCP" to verify update took effect. |
| **MCPMarket** | Listed (confirmed in browser) but returns 403 to curl. Can't verify auto-update. | Open https://mcpmarket.com, search "Nucleus" to verify description is current. |

### STALE DESCRIPTIONS (needs update after messaging changes)

| Channel | Current description | Should be |
|---------|-------------------|-----------|
| **Glama** | "unified memory layer that synchronizes context..." (old) | Should refresh from updated README on next scan |
| **Smithery** | "Agent control plane that runs on your computer." | Can't update — CLI broken for Python servers |
| **Cursor Directory** | Updated 2026-04-04 | Verify update took effect in browser |

---

## Release Checklist (what to update per version)

### Always (automated or one-command)
1. `pip install` + `twine upload` → PyPI auto-updates
2. `cd npm-wrapper && npm publish` → NPM auto-updates → MCP Registry auto-syncs
3. `gh release create` → GitHub Releases
4. MCPMarket auto-re-scrapes from GitHub

### Manual per major release
1. **Glama** — Redeploy on admin/dockerfile page (build step: `uv pip install --system --break-system-packages nucleus-mcp`)
2. **Homebrew** — Update formula in eidetic-works/homebrew-nucleus
3. **Cursor Directory** — Edit plugin page if description changed
4. **Awesome lists** — Only if merged PRs need version bump (usually not)

### Never (one-time submissions)
- All Tier 3 GitHub PRs (once merged, they stay)
- All Tier 6 web form directories (once listed, they stay)
- Cline marketplace issue
- Docker MCP Registry PR

---

## Submission Copy

### Short (under 280 chars)
Nucleus MCP -- open-source MCP server with 114 tools for persistent memory, execution verification, and compliance. Local-first. Works with Claude, Cursor, VS Code. One command: uvx nucleus-mcp https://github.com/eidetic-works/nucleus-mcp

### Forum intro (1 paragraph)
Nucleus is an open-source MCP server that makes AI agents more reliable over time. It provides 114 tools for persistent memory (engrams), 5-tier execution verification (GROUND), human correction capture (ALIGN), and automatic training signal generation (COMPOUND). It includes compliance configs for EU DORA, Singapore MAS TRM, and SOC2. Everything runs locally with zero cloud dependencies. Install with `uvx nucleus-mcp` and add to Claude Code, Cursor, or any MCP-compatible IDE.

### Tags
Primary: `mcp`, `model-context-protocol`, `ai-agents`, `ai-tools`
Secondary: `memory`, `governance`, `compliance`, `orchestration`, `local-first`

### Competitive positioning
- Alternative to: Context7, MemoryMesh, basic MCP memory servers
- Differentiators: execution verification (GROUND), compliance frameworks, 114 tools (not just memory), training signal generation, full CLI
- Not competing with: LangChain, CrewAI, AutoGen (agent frameworks; Nucleus is agent infrastructure)
