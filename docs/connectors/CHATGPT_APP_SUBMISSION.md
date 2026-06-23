# ChatGPT App Catalog Submission Checklist

This doc tracks the full submission process for getting Nucleus MCP into
the ChatGPT App Catalog (one-click install for all ChatGPT users).

## Status: SUBMITTED — in OpenAI review queue (2026-06-21)

> All operator-keyboard items complete. App submitted to OpenAI App Catalog.
> Token verified live on relay. Awaiting Case ID + screenshot/video URLs for
> archival (see "Artifacts needed from operator" below).

### Code-side (DONE)

| Item | Status | Evidence |
|------|--------|----------|
| Public MCP endpoint | DONE | `https://relay.nucleusos.dev/mcp` (live, v1.13.3) |
| OAuth 2.1 server | LIVE | `NUCLEUS_OAUTH_ENABLED=true` on relay; DCR→authorize→token→MCP verified end-to-end |
| Authorize POST form-body fix | DONE | `oauth_server.py` — POST reads hidden fields from form body, not just query params (regression test in `test_oauth_server.py`) |
| Tool annotations (all 17 tools) | DONE | `readOnlyHint` / `destructiveHint` / `openWorldHint` on every `@mcp.tool()` |
| `/.well-known/openai-apps` endpoint | LIVE | Returns verification token `egEDZ80H...` — HTTP 200 verified 2026-06-21 |
| `/.well-known/oauth-protected-resource` | LIVE | RFC 9728 metadata — returns 200 with correct issuer |
| `/.well-known/oauth-authorization-server` | LIVE | RFC 8414 metadata — returns 200 with correct issuer |
| Streamable HTTP transport | DONE | `NUCLEUS_TRANSPORT=streamable-http` (default) |
| Tests | DONE | `tests/test_chatgpt_app_catalog.py` — 12/12 pass; `test_oauth_server.py` — 18/18 pass |
| Privacy policy URL | EXISTS | `https://eidetic.works/privacy` |
| Terms of service URL | EXISTS | `https://eidetic.works/terms` |
| Demo data seeded | DONE | 17 engrams + 7 tasks in "oauth" tenant brain; reviewer simulation verified all 5 test prompts |
| Welcome engram seeding | DONE | `tenant.py:_seed_welcome_engram` — new tenant brains get an onboarding engram on first creation (commit 51ae2f3d) |
| Per-tenant isolation | DONE | `tests/test_tenant_welcome_seeding.py` — 7/7 pass; cross-tenant leak fix in `tenant.py` middleware (NUCLEUS_BRAIN_PATH + NUCLEAR_BRAIN_PATH both set) |

### Operator-keyboard items (ALL DONE)

#### 1. Verify OpenAI Organization — DONE (2026-06-21)

- Operator completed org verification at platform.openai.com → Settings → Organization → General
- Approved as a business
- No further action on this item

#### 2. Set verification token on OCI — DONE (2026-06-21)

- `NUCLEUS_OPENAI_APPS_TOKEN` set on relay
- Verified: `curl https://relay.nucleusos.dev/.well-known/openai-apps` returns token (HTTP 200)
- Domain verification passes on OpenAI's side

#### 3. Demo account — DONE

Demo account uses the OAuth consent flow (no username/password). Reviewer
clicks "Add to ChatGPT" → "Allow" on the consent screen. The "oauth" tenant
brain is pre-seeded with 17 engrams + 7 tasks. Reviewer simulation verified
all 5 test prompts return meaningful data.

#### 4. Record demo video — DONE (2026-06-21)

- Operator recorded demo video covering web + mobile use cases
- Walk-through: memory write → task creation → relay message → governance check
- Uploaded to YouTube: `https://www.youtube.com/watch?v=D1B6m_F-h80`
- Recorded in OpenAI submission JSON (field: `demo_recording_url`)

#### 5. Screenshots — N/A (2026-06-21)

- Screenshots not uploaded (`screenshots: None` in submission JSON)
- Demo video covers the UI walkthrough — screenshots optional per OpenAI form
- No action needed unless OpenAI requests them during review

### Artifacts recorded (2026-06-21)

Source: `~/Downloads/nucleus-sovereign-agent-os-1-0-0.json` (OpenAI app
submission export, downloaded by operator after form completion).

| Artifact | Value |
|----------|-------|
| App ID | `asdk_app_v_6a37bbb65f648191a844acc11c98f09b` |
| Status | `REVIEW` (in OpenAI review queue) |
| Callback ID | `Xx64pqEiX4SP` |
| Display name | Nucleus Sovereign Agent OS |
| Developer | Eidetic Works |
| Version | 1.0.0 |
| MCP URL | `https://relay.nucleusos.dev/mcp` |
| Demo video | `https://www.youtube.com/watch?v=D1B6m_F-h80` |
| Screenshots | None (not uploaded — demo video covers the UI walkthrough) |
| Entity type | business |
| Intended audience | all_ages |

**Submission record CLOSED.** The app is in OpenAI's review queue. Monitoring
for review status changes is passive — OpenAI emails on approval/rejection.
The App ID (`asdk_app_v_6a37bbb65f648191a844acc11c98f09b`) is the tracking
identifier; quote it in any correspondence with OpenAI support.

#### 6. App submission form

Go to **platform.openai.com → Apps → Submit app**:

| Field | Value |
|-------|-------|
| App name | Nucleus Sovereign Agent OS |
| MCP Server URL | `https://relay.nucleusos.dev/mcp` |
| Auth mode | OAuth 2.1 |
| Client ID | (from DCR at `https://relay.nucleusos.dev/register`) |
| Privacy policy URL | `https://eidetic.works/privacy` |
| Terms of service URL | `https://eidetic.works/terms` |
| Company | Eidetic Works |
| Description | Persistent memory, task management, and multi-agent relay for AI assistants. Nucleus gives ChatGPT a sovereign brain — write engrams, track tasks, coordinate with other AI agents, and govern decisions. |
| Demo account | (from step 3) |
| Screenshots | (from step 5) |
| Demo video URL | (from step 4) |
| Test prompts | See below |

### Test credentials

No username/password required. The reviewer clicks **Add to ChatGPT** → is
redirected to the Nucleus OAuth consent screen → clicks **Allow** → is dropped
into a pre-seeded demo tenant (`oauth`) brain containing 17 engrams + 7 tasks
of realistic founder-decision data (architecture decisions, strategy notes,
brand positioning, feature flags). No account creation, no 2FA, no setup.

### Test cases (5)

#### Test Case 1 — Write a memory engram

**Scenario**
User wants ChatGPT to remember a personal preference so it persists across
future conversations (the core "sovereign memory" use case).

**User prompt**
> Remember that I prefer concise answers with bullet points, and save this to my Nucleus memory.

**Tool triggered**
`nucleus_engrams` with `action="write_engram"` (and `action="search_engrams"` on a follow-up
turn to confirm the write landed). Aliases `action="add"` and `action="search"` are also accepted.

**Expected output**
The tool returns a confirmation that a new engram was written to the brain
ledger (with a generated engram ID). On the next turn, asking
"check my Nucleus memory for my preferences" triggers `nucleus_engrams`
`action="search_engrams"` and surfaces the just-written preference alongside the
pre-seeded demo engrams. Output is structured JSON the model renders as a
short confirmation + the recalled preference.

---

#### Test Case 2 — Search memory for a prior decision

**Scenario**
User asks ChatGPT to recall a strategic decision recorded earlier. This
validates that the seeded demo brain is queryable and returns meaningful
results (not empty).

**User prompt**
> Search my Nucleus memory for any decisions about the marketing budget.

**Tool triggered**
`nucleus_engrams` with `action="search_engrams"`, query terms matching the seeded
`five_k_marketing` engram ("Marketing budget: $5,000 total. Must be surgical
— Reddit r/ClaudeAI, Hacker News, Dev.to. No paid ads. Value-first content
only."). Alias `action="search"` is also accepted.

**Expected output**
The tool returns 1+ matching engrams from the demo brain, including the
$5,000 marketing-budget decision with its context tag ("Strategy") and
intensity score. The model renders this as a natural-language summary of
the prior decision, citing that it came from Nucleus memory.

---

#### Test Case 3 — Create a task

**Scenario**
User wants ChatGPT to create a tracked task in their Nucleus task list, the
second core workflow after memory.

**User prompt**
> Create a task titled "Review Q3 roadmap" with high priority and add it to my Nucleus task list.

**Tool triggered**
`nucleus_tasks` with `action="add"`. Alias `action="create"` is also accepted.

**Expected output**
The tool returns a task object with a generated task ID, status `open`,
priority `high`, and the provided title. A follow-up prompt ("show me my
open tasks") triggers `nucleus_tasks` `action="list"` and surfaces the
newly created task alongside the 7 pre-seeded demo tasks. The model
confirms the task was created and shows the updated list.

---

#### Test Case 4 — Send a relay message to a peer agent

**Scenario**
User wants to send a message to another AI agent in their fleet via the
Nucleus relay substrate (the multi-agent coordination use case).

**User prompt**
> Send a relay message to my peer agent asking it to review PR #123.

**Tool triggered**
`nucleus_relay` with `action="post"`, `to="peer"` (or `to="claude_code_peer"`),
and a message body containing the PR review request. `recipient` is accepted
as an alias for `to`.

**Expected output**
The tool returns a `posted=true` confirmation with a generated relay
message ID and timestamp. The message lands in the `claude_code_peer`
inbox on the relay server. (The reviewer will not see the peer agent
reply in real time, but the post-confirmation proves the relay path is
live.) The model confirms the message was sent and shows the message ID.

---

#### Test Case 5 — Check governance / session status

**Scenario**
User wants to see the governance state of their current Nucleus session —
active policies, agent identity, session health. This validates the
governance + session introspection surface.

**User prompt**
> Show me the governance status of my current Nucleus session.

**Tool triggered**
`nucleus_governance` with `action="status"` (and optionally
`nucleus_sessions` with `action="check_recent"`). Alias `action="current"` is also accepted.

**Expected output**
The tool returns a governance status object: active policies, session ID,
agent identity (the OAuth reviewer session), and any active
circuit-breakers or kill-switches. The model renders this as a short
status report confirming the session is governed and healthy.

---

### Negative test cases (3)

#### Negative Test Case 1

**Scenario**
The user wants to search the live web for current news or real-time
information. Nucleus searches the user's private local brain ledger
(past memories, decisions, notes) — not the internet. Triggering here
would return irrelevant or empty results and mislead the user into
thinking Nucleus performed a web search.

**User prompt**
> Search the web for the latest news about OpenAI's GPT-5 release.

---

#### Negative Test Case 2

**Scenario**
The user wants to schedule a calendar event or send an email. Nucleus
does not manage calendars, send emails, or book meetings. The word
"send" might superficially suggest the `nucleus_relay` tool, but relay
messages are inter-agent JSON payloads on the Nucleus relay server —
not email or calendar operations. Triggering here would confuse the
user with a relay confirmation for something that was supposed to be a
calendar invite.

**User prompt**
> Schedule a meeting with Alex for next Tuesday at 2pm and send him a calendar invite.

---

#### Negative Test Case 3

**Scenario**
The user wants code generated and written to their local filesystem.
Nucleus is a memory / task / relay / governance layer — not a code
interpreter or file editor. While `nucleus_infra` can *track* file
changes as engrams, it does not write or execute code. Triggering here
would return an infra-tracking record when the user expected a working
Python script on their desktop.

**User prompt**
> Write a Python script that scrapes a website and save it to my desktop as scraper.py.

---

## Tool annotation reference

| Tool | readOnly | destructive | openWorld | Rationale |
|------|----------|-------------|-----------|-----------|
| nucleus_engrams | false | false | false | Writes engrams (additive), local brain |
| nucleus_tasks | false | false | false | Creates/updates tasks, local state |
| nucleus_sync | false | false | false | Agent identity + deploy mgmt, local |
| nucleus_relay_subscribe | true | false | false | Long-poll read subscription |
| nucleus_ccr_arm | false | false | false | Arms watcher, local state change |
| nucleus_relay | false | false | true | Posts messages to external agents |
| nucleus_governance | false | true | false | Can revoke/approve/kill, local |
| nucleus_sessions | false | false | false | Session state, local |
| nucleus_federation | false | false | true | Multi-brain coordination, external |
| nucleus_features | false | false | false | Feature tracking, local |
| nucleus_orchestration | false | false | false | Commitments/loops, local |
| nucleus_telemetry | false | false | false | Telemetry/PEFS, local |
| nucleus_slots | false | false | false | Sprint/mission mgmt, local |
| nucleus_infra | false | true | true | File changes + cloud ops, external+destructive |
| nucleus_agents | false | false | true | Spawns external agents |
| nucleus_route | true | false | false | Routing decision is read-only |
| nucleus_audit | true | false | false | Append-only audit log, read-only queries |

## Tool justifications (for OpenAI "Tool justification" field)

**Architectural note (applies to all 14 multiplexer tools below):** Nucleus uses a
deliberate **facade/dispatcher pattern** — one MCP tool exposes many actions via an
`action: str` + `params: dict` signature, routed through an internal `ROUTER` map to
typed handler functions. Each action's required/optional fields are documented in the
tool's docstring (visible to the model via `list_tools`). We chose this pattern over
one-tool-per-action to stay under MCP's practical tool-count ceiling (18 facades →
171 actions vs. 171 separate tools, which would overflow most clients' tool-selection
context). The `params: dict` shape is a known limitation — a follow-up PR will add
JSON-schema `oneOf` discriminated-union input schemas per action so the structure is
machine-enforced, not just docstring-documented. The three annotations per tool are
set conservatively at the facade level: if ANY action in the multiplexer can mutate
state, `readOnlyHint=false`; if ANY action can destroy data, `destructiveHint=true`;
if ANY action reaches external systems, `openWorldHint=true`. Justifications below
are written **per annotation value** as the form requires.

### nucleus_governance
**Read Only: False** — The `delete_file`, `lock`, `unlock`, `set_mode`, `comply_apply`,
and `pip_install` actions all mutate filesystem state, hypervisor flags, compliance
config, or installed packages. At least 6 of 18 actions write state, so the facade is
not read-only.

**Open World: False** — All actions operate on local brain/hypervisor state. The
`curl` and `pip_install` actions are proxied through an in-process air-gapped egress
gate (not open internet); no action reaches arbitrary external endpoints.

**Destructive: True** — The `delete_file` action removes files from disk, and
`lock`/`unlock` toggle `chflags uchg` (immutable flag). These are irreversible
destructive operations on the local filesystem.

### nucleus_features
**Read Only: False** — `mount_server`, `invoke_tool`, and `generate_proof` mutate
feature registry state and append to proof ledgers.

**Open World: False** — Feature registry and proof ledgers are local to the brain;
no action reaches external systems.

**Destructive: False** — All writes are additive (proofs append, mounts register).
No action deletes or irreversibly destroys data.

### nucleus_sessions
**Read Only: False** — `create`, `checkpoint`, and `envelope` write session state to
the local brain.

**Open World: False** — Session state is local brain; no external system is reached.

**Destructive: False** — Sessions are append-only; no delete action exists in the
multiplexer.

### nucleus_tasks
**Read Only: False** — `create`, `update`, `complete`, and `assign_skills` mutate
task state in the local brain.

**Open World: False** — Task store is local brain; no external system is reached.

**Destructive: False** — `complete` marks a task done (soft-state); no action
hard-deletes task records.

### nucleus_sync
**Read Only: False** — `identify_agent` writes identity state; `heartbeat` updates
last-seen timestamps. Both mutate local registry state.

**Open World: False** — Identity registry is local; no external system is reached.

**Destructive: False** — No action destroys identity records. Writes are additive
or update-in-place.

### nucleus_orchestration
**Read Only: False** — `weekly_challenge` and `patterns` write commitment/loop state
to the local brain.

**Open World: False** — Orchestration state is local; no external system is reached.

**Destructive: False** — Commitments and loops are append-only; no action destroys
prior state.

### nucleus_telemetry
**Read Only: False** — `record_event` writes telemetry records to the local store.

**Open World: False** — Telemetry store is local brain; no external system is
reached.

**Destructive: False** — Telemetry is append-only; no action deletes or overwrites
prior records.

### nucleus_slots
**Read Only: False** — `allocate`, `start_mission`, and `autopilot_sprint_v2` mutate
slot/mission state in the local brain.

**Open World: False** — Slot registry is local; no external system is reached.

**Destructive: False** — `release` is soft-state (marks slot free); no action
hard-deletes slot records.

### nucleus_infra
**Read Only: False** — `manage_strategy`, `update_roadmap`, and `file_write` mutate
strategy state, roadmap documents, and filesystem content.

**Open World: True** — Cloud ops actions reach external cloud providers (OCI, Azure)
to provision/modify infrastructure resources.

**Destructive: True** — `file_write` can overwrite existing files, and strategy
actions can clobber prior strategy documents. These are irreversible destructive
operations.

### nucleus_agents
**Read Only: False** — `spawn`, `confirm`, `tier_set`, and `role` assign mutate the
agent registry in the local brain.

**Open World: True** — `spawn` launches external agent processes (subprocess or
remote agent surfaces); the facade reaches systems outside the local brain.

**Destructive: False** — No action hard-deletes agent records. Writes are additive
or update-in-place.

### nucleus_federation
**Read Only: False** — `register` and `sync` write federation peer state to the
local brain.

**Open World: True** — `route` and `discover` reach external peer brains across the
network to dispatch tasks or enumerate peers.

**Destructive: False** — No action destroys peer registrations. Writes are additive.

### nucleus_engrams
**Read Only: False** — `write_engram` appends memory records to the local brain
store.

**Open World: False** — Engram store is local brain; no external system is reached.

**Destructive: False** — Engrams are append-only; no action deletes or overwrites
prior memory records.

### nucleus_relay
**Read Only: False** — `post` and `ack` mutate relay state (posting messages,
marking read) in both local and remote inboxes.

**Open World: True** — `post` delivers messages to external agent inboxes across
surfaces (other AI agents, cloud sessions, OCI relay server). The facade reaches
systems outside the local brain.

**Destructive: False** — Messages are append-only; no action deletes or overwrites
prior relay messages.

### nucleus_audit
**Read Only: True** — Every action (`query`, `admin_query`, `export`, `tail`) is a
read/query. The audit log is append-only and this tool exposes no write surface.

**Open World: False** — Audit log is local brain; no external system is reached.

**Destructive: False** — Follows from read-only: no write surface means no
destructive capability.

### nucleus_relay_subscribe
**Read Only: True** — The tool opens a long-poll subscription that reads relay
messages from the local inbox directory. No action writes, posts, or mutates any
state — it only blocks until a new message arrives or the timeout elapses, then
returns the unread payload.

**Open World: False** — Subscription reads from the local `.brain/relay/<bucket>/`
filesystem path. No external system is reached; the long-poll is over local files,
not a network socket.

**Destructive: False** — Read-only by construction; no write surface exists, so no
destructive capability. (Note: messages are marked read by a separate `ack` action
on `nucleus_relay`, not by this subscription tool.)

### nucleus_ccr_arm
**Read Only: False** — Arming the CCR watcher writes a sentinel file
(`$HOME/.claude/ccr_w0_state/<role>.subscribed`) and spawns a background `Monitor`
process. Both are local state mutations — the facade is not read-only.

**Open World: False** — All side effects are local: a filesystem touch on the
operator's machine and a local background process spawn. No external system is
reached. (The downstream Telegram push that the daemon may fire is owned by the
W1 launchd daemon, not by this tool's action surface.)

**Destructive: False** — The sentinel file is additive (touch/create), the Monitor
process is reversible (killable), and no action deletes or overwrites prior state.
No irreversible destructive operation exists in the multiplexer.

### nucleus_route
**Read Only: True** — The tool returns a routing decision (which agent/surface
should handle a given task) computed from local brain state — agent registry,
skill index, federation peer table. It is a pure query: input task descriptor in,
routing recommendation out, zero state mutation.

**Open World: False** — Routing decision is computed entirely from local brain
state. The tool does not dispatch the task (that is `nucleus_agents.spawn` or
`nucleus_federation.route`); it only returns the recommended target. No external
system is reached.

**Destructive: False** — Follows from read-only: a pure decision query with no
write surface has no destructive capability.

---

## After submission

- OpenAI sends a Case ID confirmation email
- Review takes days to weeks
- Common rejection causes: missing annotations (we have them), demo account
  doesn't work, privacy policy insufficient, tool descriptions inaccurate
- If rejected, fix and resubmit with the same Case ID reference

## CSP (Content Security Policy)

If Nucleus app uses any widget UI (not currently planned for v1), CSP must
allow the exact domains fetched from. For the MCP-only submission (no widget),
CSP is not required — the MCP server itself is the entire app surface.
