# Agent LEGO Discipline — How to Work in Nucleus

> **For any agent (Devin, Claude Code, AGY, Gemini) working in this repo.**
> Read this before taking any action.

## The one rule

**Every action goes through a Nucleus LEGO block. Not raw model. Not raw Devin.**

You are not a developer who happens to have Nucleus tools. You are a Nucleus
operator who happens to be running on a model. The model is the substrate;
the LEGO blocks are the only valid interface to take action.

| Action | LEGO block | NOT this |
|---|---|---|
| Plan | `nucleus_delegate(action="plan_review_loop")` | Drafting a plan inline |
| Execute | `nucleus_delegate(action="dispatch")` | Editing files directly |
| Review | `nucleus_delegate(action="review")` | Reviewing your own work inline |
| Recall | Nucleus engram/memory tools | Searching your own context |
| Decide | Nucleus governance/decision tools | Just deciding |
| Commit | `ship` skill | `git commit` directly |
| Orchestrate | Nucleus orchestration tools | Coordinating manually |
| Call agent | `nucleus_delegate(action="dispatch")` | Talking to AGY/Devin directly |

**Even building LEGO is done with LEGO.**

## Before declaring "no block fits"

You must check the wiki first. Never declare "no LEGO block exists for this"
based on your own memory — always verify against the indexed wiki.

**Not all paths give the same kind of answer.** This is the key distinction:

| Path | ChatGPT-like AI answer? | What you actually get | Speed |
|---|---|---|---|
| **1. Local Devin wiki** | ❌ NO | Static Markdown file. You grep/read it yourself. No AI — you interpret the content. | Instant (filesystem read) |
| **2. DeepWiki MCP** | ✅ YES | `ask_question` returns a full AI-generated answer with code examples, file citations, explanations. Like ChatGPT but grounded in the actual repo. | Instant (1-3s) |
| **3. DeepWiki web** | ⚠️ PARTIAL | Returns rendered documentation pages (HTML). Not Q&A — it's pre-generated docs. The web UI has a chat feature but `webfetch` just gets the page content. | Instant (HTTP fetch) |
| **4. Devin API** | ✅ YES but ASYNC | Creates a real Devin session that can answer anything. But it's not instant — you create a session, poll for completion, then read the output. Like sending a message and waiting for a reply. | Slow (30s-5min) |
| **5. DeepWiki-Open** | ✅ YES (self-hosted) | `/chat/completions/stream` gives streaming AI answers. Same as Path 2 but you control the model and hosting. | Instant once deployed |

**Full reference:** [`DEEPWIKI_PATHS.md`](DEEPWIKI_PATHS.md) — detailed examples,
verified status, decision tree, and when to use each path.

**Current environment status:**

| Path | Status | For this repo (private)? | For public repos? |
|---|---|---|---|
| 1. Local Devin wiki | ✅ LIVE | ✅ YES (updated today) | ✅ YES (if you've opened it) |
| 2. DeepWiki MCP | ✅ LIVE | ❌ NO (private repo) | ✅ YES |
| 3. DeepWiki web | ✅ LIVE | ❌ NO (private repo) | ✅ YES |
| 4. Devin API | ✅ LIVE | ✅ YES (async) | ✅ YES |
| 5. DeepWiki-Open | ❌ NOT DEPLOYED | ❌ Not deployed | ❌ Not deployed |

**For this repo (mcp-server-nucleus, private):**
- **Quick search:** Path 1 ✅ (local wiki — grep it, read it yourself)
- **Deep AI answer:** Path 4 ✅ (Devin API — create session, wait, get answer)
- **Instant AI answer:** ❌ Not available (Path 2 can't index private repos, Path 5 not deployed)

**Real-world evaluation (tested with the same question on all paths):**
- Path 1: 0.03s, raw grep matches — fast but high-effort, you interpret
- Path 2: ~2s, 800-word AI answer with citations — gold standard for public repos
- Path 3: ~3s, pre-generated docs — good for browsing, bad for Q&A
- Path 4: ~3min, 1221-char grounded answer with exact file names — best for private repos
- Path 5: not deployed

**Full evaluation with sample outputs:** [`DEEPWIKI_PATHS.md`](DEEPWIKI_PATHS.md) § "Real-world evaluation"

**Recommended workflow for this repo:**
```
1. Quick check → Path 1 (grep local wiki, 0.03s)
   ├── Found it? → Done
   └── Need deeper? → continue
2. Deep question → Path 4 (Devin API, ~3min)
   └── Grounded answer from actual private code
3. Public repo question → Path 2 (DeepWiki MCP, ~2s)
   └── Instant AI answer with citations
```

### Path 1 — Local Devin wiki (fastest, no AI)

Static Markdown file. You grep/read it yourself. No AI — you interpret the content.

```bash
# Find the wiki for this repo
ls ~/.local/share/devin/cli/wiki/*/meta.json | xargs -I{} grep -l "mcp-server-nucleus" {}

# Search it
grep -i "deploy\|test\|ship\|commit" ~/.local/share/devin/cli/wiki/*/wiki.md
```

Auto-updates every Devin CLI session. Only works for repos you've opened with Devin CLI.

### Path 2 — DeepWiki MCP (public repos, instant AI answers)

ChatGPT-like AI answer — instant, grounded in the actual repo code. Free, no auth.

```python
mcp_call_tool("deepwiki", "ask_question", {
    "repoName": "langchain-ai/langchain",
    "question": "What is the main entry point for creating an agent?"
})
# → Full AI answer with code examples and file citations
```

Public repos only. Private repos return "Repository not found."

### Path 3 — DeepWiki web (public repos, pre-generated docs)

Rendered documentation pages (HTML). Not Q&A — pre-generated docs you read yourself.

```bash
webfetch("https://deepwiki.com/facebook/react")
```

Same scope as Path 2 (public repos only). Use when you want to browse docs without asking a specific question.

### Path 4 — Devin API (private repos, async AI answers)

ChatGPT-like AI answer but ASYNC — create a session, wait (30s-5min), read the output. Works for private repos.

```bash
source .env  # loads DEVIN_ORG_KEY
curl -X POST "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions" \
  -H "Authorization: Bearer $DEVIN_ORG_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What tools exist for deploying in this repo?"}'
# → {"session_id": "...", "status": "new"} (poll for completion)
```

Credentials in `.env` (gitignored). `DEVIN_ORG_KEY` (cog_ prefix, v3 API) preferred over `DEVIN_API_KEY` (apk_user_ prefix, legacy).

**Session lifecycle:** Sessions stay open (`waiting_for_user`) after answering — they do NOT auto-complete. Reuse the same session_id for follow-up questions about the same repo (faster, less ACU cost). Create a new session only for different repos or unrelated topics. See [`DEEPWIKI_PATHS.md`](DEEPWIKI_PATHS.md) § "Session lifecycle and reuse" for the full pattern.

### Path 5 — DeepWiki-Open self-hosted (full control, AI answers on your terms)

Same ChatGPT-like answers as Path 2, but you control the model and hosting. Not currently deployed.

```bash
# Would run at localhost:8001 if deployed
curl -X POST "http://localhost:8001/chat/completions/stream" \
  -d '{"repo_url": "...", "messages": [{"role": "user", "content": "What tools exist for deploying?"}]}'
```

Setup: clone [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open), configure model provider, run FastAPI server.

### Which path to use — decision tree

```
Need to query repo knowledge?
│
├── What kind of answer do you need?
│   ├── Quick keyword search (no AI) → Path 1 (local wiki)
│   ├── ChatGPT-like AI answer (instant)
│   │   ├── Public repo → Path 2 (DeepWiki MCP)
│   │   └── Private repo → Path 5 (if deployed)
│   ├── ChatGPT-like AI answer (async OK) → Path 4 (Devin API)
│   └── Browse pre-generated docs → Path 3 (DeepWiki web)
│
└── Which repo?
    ├── Repo you've worked in with Devin CLI → Path 1 available
    ├── Public GitHub repo → Paths 2, 3 available
    ├── Private repo you have access to → Path 4 available
    └── Need full control / air-gapped → Path 5 (if deployed)
```

## The LEGO block inventory

Nucleus has 22+ tool facades, each exposing multiple actions. The full list
lives in the wiki, but the most commonly needed blocks:

| Block | Tool | Action | Input | Output |
|---|---|---|---|---|
| Plan | `nucleus_delegate` | `plan_review_loop` | prompt | approved plan (the plans directory ) |
| Execute | `nucleus_delegate` | `dispatch` | vendor + prompt + artifact_ref | changed files + result |
| Review | `nucleus_delegate` | `review` | pasted code/diff | verdict (SOUND/RISKY/BUGGY) |
| List vendors | `nucleus_delegate` | `list` | — | vendors + models + actions |
| Ship | `ship` skill | — | — | commit + push + PR |
| Tasks | `nucleus_tasks` | various | — | task queue management |
| Relay | `nucleus_relay` | various | — | cross-agent messaging |
| Engrams | `nucleus_engrams` | various | — | memory recall |
| Governance | `nucleus_governance` | various | — | decision recording |
| Sessions | `nucleus_sessions` | various | — | session management |
| Features | `nucleus_features` | various | — | feature flags |
| Sync | `nucleus_sync` | various | — | cross-repo sync |

## The handshake principle

LEGO blocks compose by shared format conventions, not by naming each other.

```
Block A writes → the plans directory <id>/final_plan.md  (Markdown with - [ ] checkboxes)
Block B reads  → the plans directory *.md  (latest, auto-discovered)

Neither block names the other. The format is the contract.
```

A block conforms to a spec. It does not know who produced its input or who
consumes its output. This is what makes them LEGO — they snap together by
shape, not by wiring.

## Secret hygiene

- **Never** hardcode tokens in source files, prompts, or command-line arguments
- **Always** load from `.env` (gitignored) or environment variables
- **Never** commit `.env` to git (it's in `.gitignore` — verify if unsure)
- **Never** paste tokens in chat, relay messages, or engrams
- The `.env` file contains all API keys — load it at session start

## Quick reference for agents

```bash
# 1. Load environment (do this first)
source .env

# 2. Find the local wiki for this repo
ls ~/.local/share/devin/cli/wiki/*/meta.json | xargs -I{} grep -l "mcp-server-nucleus" {}

# 3. Search the wiki for a capability before declaring "no block fits"
grep -i "<capability>" ~/.local/share/devin/cli/wiki/*/wiki.md

# 4. Check what MCP tools are available
# (via your MCP client — list_tools on the nucleus server)

# 5. Check what skills are available
ls ~/.claude/skills/*/SKILL.md

# 6. Check what scripts exist
ls scripts/*.sh
```
