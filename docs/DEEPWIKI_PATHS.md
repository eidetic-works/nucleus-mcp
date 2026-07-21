# DeepWiki — 5 Paths to Query Repo Knowledge

> **For any agent that needs to understand a codebase.**
> DeepWiki indexes GitHub repos and lets you ask AI-powered questions about
> them. This doc covers all 5 access paths, what kind of answer each gives,
> which ones are live in this environment, and when to use each.

## What DeepWiki does

DeepWiki indexes a GitHub repo's code, generates documentation, and lets
you ask questions like "What tools exist for deploying?" or "How does the
authentication system work?" — getting AI-powered, context-grounded answers
that cite specific files and line numbers.

It's the **first place to look** before declaring "no LEGO block fits this
operation." Always query the wiki first.

## Not all paths give the same kind of answer

This is the key distinction. Some paths give you a ChatGPT-like AI answer
(instant, interactive, grounded in the actual code). Others give you raw
content that you have to read and interpret yourself.

| Path | ChatGPT-like AI answer? | What you actually get | Speed |
|---|---|---|---|
| **1. Local Devin wiki** | ❌ NO | Static Markdown file. You grep/read it yourself. No AI — you interpret the content. | Instant (filesystem read) |
| **2. DeepWiki MCP** | ✅ YES | `ask_question` returns a full AI-generated answer with code examples, file citations, explanations. Like ChatGPT but grounded in the actual repo. | Instant (1-3s) |
| **3. DeepWiki web** | ⚠️ PARTIAL | Returns rendered documentation pages (HTML). Not Q&A — it's pre-generated docs. The web UI has a chat feature but `webfetch` just gets the page content. | Instant (HTTP fetch) |
| **4. Devin API** | ✅ YES but ASYNC | Creates a real Devin session that can answer anything. But it's not instant — you create a session, poll for completion, then read the output. Like sending a message and waiting for a reply. | Slow (30s-5min) |
| **5. DeepWiki-Open** | ✅ YES (self-hosted) | `/chat/completions/stream` gives streaming AI answers. Same as Path 2 but you control the model and hosting. | Instant once deployed |

## The 5 paths — detailed

### Path 1 — Local Devin wiki (fastest, no AI)

The Devin CLI auto-generates a wiki for every repo you open. It's a single
Markdown file (~10K lines) saved locally.

**What you get:** A static Markdown file. No AI, no Q&A. You grep it, read
it, and interpret the content yourself. Think of it as a pre-generated
encyclopedia of the codebase — comprehensive but not interactive.

**Location:**
```
~/.local/share/devin/cli/wiki/<repo_hash>/wiki.md
```

**Find the wiki for a repo:**
```bash
for dir in ~/.local/share/devin/cli/wiki/*/; do
  echo "=== $(cat "$dir/meta.json" | grep repo_identifier) ==="
  echo "  wiki: $dir/wiki.md"
  echo "  modified: $(stat -f '%Sm' "$dir/wiki.md" 2>/dev/null)"
done
```

**Search it:**
```bash
grep -i "deploy\|test\|ship\|commit" ~/.local/share/devin/cli/wiki/*/wiki.md
```

**Or use a subagent** (recommended for thorough search — the wiki is large):
```
run_subagent(
  title="Search wiki for <capability>",
  profile="subagent_explore",
  task="Read ~/.local/share/devin/cli/wiki/<hash>/wiki.md and find
        all blocks that handle <capability>."
)
```

**Refresh cadence:** Auto-updates during every Devin CLI session in the repo.
No manual refresh command. If you ran a session today, it's fresh.

**Scope:** Only repos you've previously opened with Devin CLI.

**Status in this environment:** ✅ LIVE — 4 repos indexed:
- `mcp-server-nucleus` (updated Jul 20 19:28)
- `bespoq` (updated Jul 20 18:58)
- *(2 other repos redacted — check `~/.local/share/devin/cli/wiki/*/meta.json` for full list)*

**Example of what you get:**
```bash
$ grep "deploy" ~/.local/share/devin/cli/wiki/270ae.../wiki.md
line 4521: The deploy script handles package installation via uv tool install...
line 8932: Deployment operations are managed by the deployment_ops module...
```
You read those lines and figure out what they mean. No AI interpretation.

---

### Path 2 — DeepWiki MCP server (public repos, instant AI answers)

A free, remote, no-authentication-required MCP server for **public** GitHub
repos. Already configured in `~/.config/devin/config.json`.

**What you get:** A full ChatGPT-like AI answer — instant, interactive,
grounded in the actual repo code. The answer includes code examples, file
citations, and explanations. Like ChatGPT but it has actually read the repo.

**Server URL:** `https://mcp.deepwiki.com/mcp` (Streamable HTTP)

**Three tools:**

| Tool | What it does | AI answer? |
|---|---|---|
| `ask_question` | Ask any question, get AI-powered answer with file citations | ✅ YES |
| `read_wiki_structure` | Get a list of documentation topics for a repo | ❌ No (topic list) |
| `read_wiki_contents` | View full documentation about a repo | ❌ No (raw docs) |

**Usage:**
```python
# Ask a question about any public repo — get a ChatGPT-like answer
mcp_call_tool("deepwiki", "ask_question", {
    "repoName": "langchain-ai/langchain",
    "question": "What is the main entry point for creating an agent?"
})
# → Returns: "The main entry point is create_agent() in
#   libs/langchain_v1/langchain/agents/factory.py. It constructs
#   an executable agent graph from a model, tools, and middleware...
#   [code example] [file citations]"

# Get topic list (not AI — just a structured outline)
mcp_call_tool("deepwiki", "read_wiki_structure", {
    "repoName": "anthropics/claude-code"
})

# Read full wiki contents (not AI — raw documentation)
mcp_call_tool("deepwiki", "read_wiki_contents", {
    "repoName": "facebook/react"
})
```

**Scope:** Public GitHub repos only. Private repos return "Repository not
found." For private repos, use Path 1 (local wiki) or Path 4 (Devin API).

**Status in this environment:** ✅ LIVE — tested with `langchain-ai/langchain`:

> **Question asked:** "What is the main entry point for creating an agent?"
>
> **Answer received:** "The main entry point is the `create_agent` function,
> located in `libs/langchain_v1/langchain/agents/factory.py`. This function
> is also exposed directly through the `langchain.agents` package. It
> constructs an executable agent graph from a model, tools, and middleware..."
> (with full code example and file citations)

**Limitation:** The repo must be indexed by DeepWiki. Most popular public
repos are already indexed. Obscure repos may not be.

---

### Path 3 — DeepWiki web (public repos, pre-generated docs)

Browse DeepWiki directly via web. No MCP needed — works with any HTTP client.

**What you get:** Rendered documentation pages (HTML). NOT Q&A — it's
pre-generated docs that you read like a wiki. The DeepWiki web UI does have
a chat feature, but `webfetch`/`curl` only fetches the static page content,
not the interactive chat.

**Usage:**
```bash
# Read a repo's wiki page — get rendered documentation (not AI Q&A)
curl -s "https://deepwiki.com/owner/repo" | head -100

# Or use the webfetch tool (renders to readable text)
webfetch("https://deepwiki.com/facebook/react")
```

**Scope:** Same as Path 2 — public repos only. The web interface renders the
same content the MCP server returns, just in HTML.

**Status in this environment:** ✅ LIVE — `curl` returned HTTP 200 for
`deepwiki.com/langchain-ai/langchain`.

**When to use instead of Path 2:** When you don't have MCP access, want to
browse visually, or need to read pre-generated docs without asking a
specific question. Path 2 (MCP `ask_question`) is better for targeted Q&A.

**Example of what you get:**
```bash
$ webfetch("https://deepwiki.com/langchain-ai/langchain")
# → Returns: rendered HTML page with documentation sections like
#   "Agent System", "Agent Creation and Middleware Architecture", etc.
#   You read the docs yourself — no AI interpretation.
```

---

### Path 4 — Devin API (private repos, async AI answers)

When the local wiki is stale and DeepWiki can't index the repo (private),
use the Devin API to create a session that analyzes the repo.

**What you get:** A real Devin session that can answer anything — full
ChatGPT-like AI answer, but ASYNC. You create a session, wait for it to
complete (30s-5min), then read the output. Like sending a message to a
colleague and waiting for their reply. The session can clone the repo,
read files, run commands, and give a grounded answer.

**Credentials** in `.env` (gitignored):
```bash
source .env

# DEVIN_ORG_KEY     — cog_ prefix, v3 API, service user identity (PREFERRED)
# DEVIN_API_KEY     — apk_user_ prefix, v1/v2 legacy API, human identity
```

**Create a session to ask about a repo:**
```bash
curl -X POST "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions" \
  -H "Authorization: Bearer $DEVIN_ORG_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze mcp-server-nucleus and list all MCP tool actions for deploying and shipping"}'
```

**Response (instant — session created, not yet answered):**
```json
{
  "session_id": "e0b42eae745c46ebba67b340f21770d0",
  "url": "https://app.devin.ai/sessions/e0b42eae745c46ebba67b340f21770d0",
  "status": "new"
}
```

**Poll for completion (the answer comes back async):**
```bash
curl -X GET "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $DEVIN_ORG_KEY"
# → {"status": "completed", "output": "The deployment tools are..."}
```

**Key distinction:**
- `DEVIN_ORG_KEY` (cog_ prefix) → v3 API, org-scoped, service user. **Preferred.**
- `DEVIN_API_KEY` (apk_user_ prefix) → v1/v2 legacy API. Works during deprecation.

**Scope:** Any repo you have access to (public or private). The session runs
with your credentials and can clone/read private repos.

**Status in this environment:** ✅ LIVE — tested auth, created session
(session_id=e0b42eae...), org_id confirmed (org-58693df8b1f24331982224d7cd9bbf41).

**When to use:**
- Private repos not indexed by DeepWiki (Paths 2-3)
- Local wiki is stale (repo hasn't been touched in weeks)
- Cross-repo queries (analyze multiple repos in one session)
- Programmatic session creation for automated workflows
- When you need a deep, reasoned answer (not just keyword search)

**Example of what you get:**
```
You: POST /sessions {"prompt": "What tools exist for deploying?"}
API: {"session_id": "e0b42eae...", "status": "new"}
  ↓ (wait 30s-5min — the session reads the repo, reasons about it)
You: GET /sessions/e0b42eae...
API: {"status": "completed", "output": "The deployment tools are:
      nucleus_infra (MCP tool facade), one_click_release.sh (script),
      sync_public_repo.sh (script)... [details] [file paths]"}
```

---

### Path 5 — DeepWiki-Open self-hosted (full control, AI answers on your terms)

For private repos where you need full control over wiki generation and
Q&A, you can self-host [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open).

**What you get:** Same ChatGPT-like AI answers as Path 2, but you control
the model provider (Google, OpenAI, OpenRouter, Azure, Ollama), the hosting,
and the caching. The `/chat/completions/stream` endpoint gives streaming AI
answers grounded in the repo code.

**REST endpoints (self-hosted FastAPI server):**

| Endpoint | Method | What it does | AI answer? |
|---|---|---|---|
| `/wiki/generate` | POST | Generate wiki from repo URL (supports private repos with `access_token`) | ❌ No (generates wiki) |
| `/chat/completions/stream` | POST | Stream AI answers about a repo | ✅ YES (streaming) |
| `/wiki/{project_id}` | GET | Get generated wiki by project ID | ❌ No (raw wiki) |
| `/wiki/projects` | GET | List all processed projects | ❌ No (list) |
| `/api/wiki_cache` | GET/POST/DELETE | Manage wiki cache | ❌ No (cache ops) |
| `/export/wiki` | POST | Export wiki as Markdown or JSON | ❌ No (export) |

**Example (generate wiki for a private repo):**
```bash
curl -X POST "http://localhost:8001/wiki/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/eidetic-works/mcp-server-nucleus",
    "access_token": "ghp_your_github_token",
    "model_provider": "google",
    "model_name": "gemini-2.0-flash"
  }'
```

**Example (ask a question — get AI answer):**
```bash
curl -X POST "http://localhost:8001/chat/completions/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/eidetic-works/mcp-server-nucleus",
    "messages": [{"role": "user", "content": "What tools exist for deploying?"}]
  }'
# → Streaming AI response: "The deployment tools are... [grounded in repo code]"
```

**Setup:**
```bash
git clone https://github.com/AsyncFuncAI/deepwiki-open
cd deepwiki-open
pip install -r requirements.txt
# Configure model provider (Google, OpenAI, OpenRouter, Azure, or Ollama)
uvicorn api.api:app --host 0.0.0.0 --port 8001
```

**Status in this environment:** ❌ NOT DEPLOYED — would need to be set up.

**When to use:**
- Private repos where you need full control over wiki generation
- Air-gapped environments where external API calls aren't allowed
- When you want to cache wikis locally for repeated queries
- When you want to choose the model provider (Google, OpenAI, Ollama, etc.)
- When Path 2 (DeepWiki MCP) can't index your private repo and Path 4 (Devin
  API) is too slow/async for your needs

---

## Decision tree

```
Need to query repo knowledge?
│
├── What kind of answer do you need?
│   ├── Quick keyword search (no AI needed)
│   │   └── Path 1 (local wiki) — grep the file, read it yourself
│   │
│   ├── ChatGPT-like AI answer (instant)
│   │   ├── Public repo → Path 2 (DeepWiki MCP ask_question)
│   │   └── Private repo → Path 5 (self-hosted, if deployed)
│   │
│   ├── ChatGPT-like AI answer (async OK)
│   │   └── Path 4 (Devin API — create session, poll, get answer)
│   │
│   └── Browse pre-generated docs (no AI)
│       └── Path 3 (DeepWiki web — webfetch the page)
│
└── Which repo?
    ├── Repo you've worked in with Devin CLI → Path 1 available
    ├── Public GitHub repo → Paths 2, 3 available
    ├── Private repo you have access to → Path 4 available
    └── Need full control / air-gapped → Path 5 (if deployed)
```

## Current environment status

| Path | Status | Answer type | For this repo (private)? | For public repos? |
|---|---|---|---|---|
| 1. Local Devin wiki | ✅ LIVE | Static file (no AI) | ✅ YES (updated today) | ✅ YES (if you've opened it) |
| 2. DeepWiki MCP | ✅ LIVE | Instant AI answer | ❌ NO (private repo) | ✅ YES |
| 3. DeepWiki web | ✅ LIVE | Pre-generated docs (no AI) | ❌ NO (private repo) | ✅ YES |
| 4. Devin API | ✅ LIVE | Async AI answer (30s-5min) | ✅ YES | ✅ YES |
| 5. DeepWiki-Open | ❌ NOT DEPLOYED | Instant AI answer (self-hosted) | ❌ Not deployed | ❌ Not deployed |

**For this repo (mcp-server-nucleus, private):**
- **Quick search:** Path 1 ✅ (local wiki — grep it, read it yourself)
- **Deep AI answer:** Path 4 ✅ (Devin API — create session, wait, get answer)
- **Instant AI answer:** ❌ Not available (Path 2 can't index private repos, Path 5 not deployed)
- Paths 2, 3 ❌ (repo is private, DeepWiki can't index it)
- Path 5 ❌ (not deployed)

## Which path to use — quick reference

| I want to... | Use this path |
|---|---|
| Quick keyword search in a repo I've worked in | **Path 1** (grep local wiki) |
| Ask a question about a public repo and get an instant AI answer | **Path 2** (DeepWiki MCP `ask_question`) |
| Browse documentation pages for a public repo | **Path 3** (DeepWiki web) |
| Ask a question about a private repo (async OK) | **Path 4** (Devin API) |
| Ask a question about a private repo (instant, self-hosted) | **Path 5** (DeepWiki-Open — needs setup) |
| Ask a question about ANY repo with full control over the model | **Path 5** (DeepWiki-Open — needs setup) |
| Search across multiple repos | **Path 4** (Devin API — one session can analyze multiple) |

## Real-world evaluation — same question, all 5 paths

To evaluate which path is best, I asked the same question via each available
path and compared the results.

**Question asked:** "What tools exist for shipping, committing, and deploying code?"

### Path 1 — Local wiki grep

```
Time: 0.03s
Effort: Manual (you interpret the results)
Answer: 20 grep matches — raw lines from the wiki file
```

Sample output:
```
282: | Infrastructure | scripts/, deploy/ | CI/CD, deployment manifests...
591: Security Gates: sync_public_repo.sh uses git archive to filter...
1104: scripts/release.sh
1258: nucleus_infra: Interface for file changes, gcloud, Render deployments...
1773: scripts/deploy_airgapped_agent.sh
```

**What I got:** Raw lines. I had to read them and figure out what they mean.
No synthesis, no "here are the 5 tools that do X." Just keyword matches.

**Verdict:** Fast but high-effort. Good for "does the wiki mention X?" but
bad for "what are all the tools that do X?" You have to do the synthesis
yourself.

---

### Path 2 — DeepWiki MCP (ask_question on langchain-ai/langchain)

```
Time: ~2s
Effort: Zero (full AI answer)
Answer: 800-word structured response with code examples and file citations
```

Sample output:
> "The LangChain repository utilizes several tools and scripts for shipping,
> committing, and deploying code, primarily through GitHub Actions workflows
> and local development tools.
>
> ## Committing Code
> The repository enforces a Conventional Commits specification... enforced
> by the `pr_lint.yml` GitHub Actions workflow...
>
> ## Shipping and Deploying Code
> The deployment process is managed through a secure, multi-stage release
> pipeline defined in the `_release.yml` GitHub Actions workflow...
>
> 1. Version bump PR...
> 2. Merge the PR...
> 3. Trigger the release workflow...
> 4. Automated release handling: build, release notes, pre-release checks,
>    TestPyPI publish, PyPI publish, GitHub release tagging..."

**What I got:** A full, structured, ChatGPT-like answer. It categorized the
tools (committing vs shipping vs deploying), explained the workflow, cited
specific files (`_release.yml`, `pr_lint.yml`, `.pre-commit-config.yaml`),
and even noted limitations ("no information about external deployment
platforms").

**Verdict:** Best for public repos. Instant, comprehensive, zero effort.
The gold standard.

---

### Path 3 — DeepWiki web (webfetch on langchain-ai/langchain)

```
Time: ~3s
Effort: Medium (you read pre-generated docs)
Answer: Rendered HTML documentation page (~2000 words)
```

Sample output:
> "## Development and Release
>
> ### Package Structure and Build System
> Each LangChain package uses a pyproject.toml file following PEP 621...
>
> ### Release Process and Workflows
> The release pipeline is a secure, multi-stage process that separates the
> build phase from the publishing phase...
>
> ### Versioning and Dependency Management
> LangChain maintains version strings in both pyproject.toml and package
> source files..."

**What I got:** Pre-generated documentation. Comprehensive but NOT answering
my specific question — it's the repo's documentation page about development,
not a targeted answer about "what tools ship/commit/deploy." I had to read
through it to find the relevant parts.

**Verdict:** Good for browsing docs, bad for targeted Q&A. Path 2 is strictly
better for questions. Path 3 is better when you want to read the full
documentation of a topic without a specific question.

---

### Path 4 — Devin API (session on mcp-server-nucleus, private repo)

```
Time: ~3min to first answer (async, polling)
Effort: Low (create session, poll, read messages)
Answer: 1221-char structured list with exact file names
```

Sample output:
> "In mcp-server-nucleus, ship/commit/deploy surfaces:
>
> **MCP tool actions** (the source tree ):
> - nucleus_sync — deploy actions: start_deploy_poll, check_deploy,
>   complete_deploy, smoke_test
> - nucleus_orchestration — scan_commitments, list_commitments,
>   close_commitment, commitment_health
> - No git-commit / push / ship / release actions are exposed as MCP tools.
>
> **Scripts** (scripts/):
> - Deploy: deploy.sh, deploy_agent.py, deploy_dashboard.sh,
>   deploy_production.sh, deploy_swarm.sh, quick_deploy.sh...
> - Release: one_click_release.sh, package_release.py, release_android_aab.sh...
> - Ship: relay_pr_ship.py, tb_ship_gate.py
> - Root-level: deploy_gentlequest.sh, deploy_ios.sh..."

**What I got:** A grounded, specific answer about THIS private repo. It
actually read the repo, listed exact file names, distinguished between MCP
tool actions and scripts, and noted the gap ("No git-commit/push/ship/release
actions are exposed as MCP tools"). This is something Path 2 (DeepWiki MCP)
cannot do because the repo is private.

**Cost:** acus_consumed: 0.0 (not yet billed — session still open,
status_detail: waiting_for_user). The session stays open for follow-up
questions, which is a feature, not a bug.

**Caveat:** The session is async and stays open. It's not a one-shot Q&A —
it's a full Devin session that expects interaction. You create it, poll for
the answer, and the session remains available for follow-ups. This is
different from Path 2 (instant, stateless Q&A).

**Verdict:** Best for private repos. Slow but worth it — the answer is
grounded in the actual private code, not generic. The async nature is a
feature for multi-turn investigation but a drawback for quick lookups.

### Path 4 — Session lifecycle and reuse

The Devin API is NOT a one-shot Q&A like Path 2. It's a full Devin session
with a lifecycle. Understanding this is critical for using it efficiently.

**Session lifecycle:**

```
POST /sessions       → {"status": "new"}           (session created)
  ↓ (Devin reads the repo, reasons about the question)
GET /sessions/{id}   → {"status": "running", "status_detail": "waiting_for_user"}
  ↓ (read the answer from /messages)
  ↓ (session stays open — does NOT auto-complete)
  ↓
  ├── Reuse: send a follow-up question to the SAME session
  │   POST /sessions/{id}/messages {"message": "What about test tools?"}
  │   → Devin answers using the SAME repo context it already loaded
  │   → Faster than creating a new session (context is cached)
  │
  └── Or: let it sit (session stays open, no cost until you interact)
```

**Key behaviors observed in testing:**

| Behavior | What happens |
|---|---|
| After answer | Session stays `running` + `waiting_for_user` — does NOT auto-complete |
| ACU cost | `acus_consumed: 0.0` while waiting — no cost for idle sessions |
| Follow-up question | Send to the SAME session_id — Devin reuses loaded context |
| New question (different topic) | Create a NEW session — fresh context, costs ACUs |
| Session URL | `https://app.devin.ai/sessions/{session_id}` — human-viewable |

**Two patterns for using Path 4:**

**Pattern A — One session per question (simple, more ACUs):**
```bash
# Each question = new session
SESSION_1=$(create_session "What tools exist for deploying?")
# → poll → read answer → session stays open (ignore it)

SESSION_2=$(create_session "What tools exist for testing?")
# → poll → read answer → session stays open (ignore it)
```
- Pro: Simple, no state to track
- Con: Each session re-loads the repo context (slower, more ACUs)

**Pattern B — Reuse session for related questions (efficient, less ACUs):**
```bash
# First question = new session
SESSION=$(create_session "What tools exist for deploying?")
# → poll → read answer

# Follow-up = reuse same session
send_message $SESSION "What about test tools?"
# → poll → read answer (Devin already has the repo context loaded)

send_message $SESSION "And what about commit/ship tools?"
# → poll → read answer (same context)
```
- Pro: Faster follow-ups, less ACU cost (context already loaded)
- Con: Must track session_id, session context can drift over many questions

**When to use which pattern:**

| Situation | Pattern |
|---|---|
| One-off question | A (new session, read answer, done) |
| Investigating one repo, multiple related questions | B (reuse session) |
| Questions about different repos | A (each session is scoped to one repo) |
| Questions about different topics in same repo | B (reuse — context is same repo) |

**API calls for session reuse:**
```bash
# Send a follow-up message to an existing session
curl -X POST "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $DEVIN_ORG_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "What about test tools? Same format — just a list."}'

# Read the new answer
curl -s "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $DEVIN_ORG_KEY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('items', []):
    if m.get('source') == 'devin' and len(m.get('message','')) > 50:
        print(m['message'])
"
```

**Test session from this evaluation:**
- session_id: `8d5c98fe3b344ed68df5154ae05d54cc`
- URL: `https://app.devin.ai/sessions/8d5c98fe3b344ed68df5154ae05d54cc`
- Status: `running` / `waiting_for_user` (still open for follow-ups)
- Context loaded: mcp-server-nucleus repo (ship/commit/deploy tools)
- Can be reused for follow-up questions about this repo

---

### Path 5 — DeepWiki-Open (not deployed)

```
Time: N/A (not running)
Answer: N/A
```

**Verdict:** Cannot evaluate. Would theoretically give Path 2-quality answers
for private repos (instant, self-hosted). Would need setup.

---

## Evaluation summary

| Dimension | Path 1 (local wiki) | Path 2 (DeepWiki MCP) | Path 3 (DeepWiki web) | Path 4 (Devin API) | Path 5 (self-hosted) |
|---|---|---|---|---|---|
| **Speed** | ⚡ 0.03s | ⚡ ~2s | ⚡ ~3s | 🐢 ~3min | ⚡ (if deployed) |
| **Answer type** | Raw grep matches | Full AI answer | Pre-generated docs | Full AI answer | Full AI answer |
| **Effort** | High (you interpret) | Zero (instant) | Medium (you read) | Low (poll + read) | Zero (if deployed) |
| **Public repos** | ✅ (if opened before) | ✅ | ✅ | ✅ | ✅ |
| **Private repos** | ✅ (if opened before) | ❌ | ❌ | ✅ | ✅ (with token) |
| **Specificity** | Keyword matches | Grounded + cited | General docs | Grounded + exact files | Grounded + cited |
| **Interaction** | One-shot grep | One-shot Q&A | One-shot fetch | Multi-turn session | One-shot Q&A |
| **Cost** | Free | Free | Free | ACU-based | Free (self-hosted) |
| **Best for** | Quick "does X exist?" | Public repo Q&A | Browsing docs | Private repo deep dive | Private repo instant Q&A |

## Which path is BEST?

### Overall winner: Path 2 (DeepWiki MCP) — for public repos

Instant, free, comprehensive AI answers with file citations. The gold
standard. If the repo is public and indexed by DeepWiki, always use Path 2.

### Best for private repos: Path 4 (Devin API) — with caveats

It's the only path that gives AI answers for private repos. It's slow (3min+)
and async, but the answer quality is excellent — grounded in the actual code,
with exact file names and structural analysis. The multi-turn nature is a
bonus for investigation but overkill for quick lookups.

### Best for quick searches: Path 1 (local wiki) — when you know what you're looking for

0.03 seconds. No AI, but if you just need "does the wiki mention deploy?"
this is the fastest path. Use it as a first pass before escalating to Path 4.

### Best for browsing: Path 3 (DeepWiki web) — when you want to read docs

Not Q&A, but good for reading a repo's documentation without a specific
question. Path 2 is strictly better if you have a question.

### Path 5 would be the private-repo winner — if deployed

Self-hosted DeepWiki would give Path 2-quality instant AI answers for
private repos. It would beat Path 4 on speed (instant vs 3min) but lose on
depth (Path 4's full Devin session can investigate deeper). Currently not
deployed, so Path 4 is the only option for private repos.

## Recommended workflow for this repo (mcp-server-nucleus, private)

```
1. Quick check → Path 1 (grep local wiki, 0.03s)
   ├── Found what I need? → Done
   └── Need deeper analysis? → continue

2. Deep question → Path 4 (Devin API, ~3min)
   ├── Create session with specific question
   ├── Poll for answer
   └── Session stays open for follow-ups

3. Public repo question → Path 2 (DeepWiki MCP, ~2s)
   └── Instant AI answer with citations
```

## See also

- [`AGENT_LEGO_DISCIPLINE.md`](AGENT_LEGO_DISCIPLINE.md) — the full LEGO
  discipline guide (when to use which block, the one rule, secret hygiene)
- [`PLAN_REVIEW_LOOP.md`](PLAN_REVIEW_LOOP.md) — the plan review loop block
  that was built using this very discipline
- [DeepWiki](https://deepwiki.com) — the public DeepWiki service
- [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open) — self-hostable version
- [Devin API docs](https://docs.devin.ai/api-reference/authentication) — auth + endpoints
