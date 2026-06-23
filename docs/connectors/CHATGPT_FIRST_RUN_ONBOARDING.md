# ChatGPT Connector — First-Run User Journey (2-Minute Value)

> **Status: DRAFT — under fleet review.** Companion to
> `CHATGPT_APP_SUBMISSION.md` (reviewer journey) and
> `CHATGPT_CONNECTOR.md` (setup). This doc covers the **real user** journey:
> a fresh ChatGPT user with an **empty brain** who needs to get value in
> 2 minutes, plus the post-approval production flow.
>
> **Credential posture:** No API keys, OAuth client secrets, or operator
> credentials are committed in this doc or the submission materials. The
> connector ships with env-var contract only; secrets are injected at deploy
> time by the operator lane (per AGENTS.md spend-class rule).

## The gap this doc addresses

The submission checklist's 5 test cases are **reviewer-optimized** — they
assume a pre-seeded demo brain (17 engrams + 7 tasks). A real user starts
with **zero memories, zero tasks, no peer agents**. Test Cases 2, 4, and 5
return empty or meaningless results for them. The 2-minute value loop for
a real user is different from the reviewer loop.

## The 2-minute value loop

### 0:00–0:15 — Install

1. User clicks **Add to ChatGPT** in the app catalog
2. OAuth consent screen → clicks **Allow**
3. Connector shows **Connected**

No account creation, no 2FA, no setup wizard. The OAuth flow is the entire
onboarding.

### 0:15–0:45 — First memory write (the core hook)

**User prompt:**
> Remember that I prefer concise answers with bullet points, and save this to my Nucleus memory.

**Tool triggered:** `nucleus_engrams` with `action="write_engram"`

**Expected output:** Confirmation that a new engram was written, with a
generated engram ID. The model renders this as a short confirmation:
"Saved to your Nucleus memory. Engram ID: eng_abc123."

**Why this lands in 30 seconds:** This is the thing ChatGPT **cannot do
natively** — persist a preference across conversations. The user just
taught ChatGPT something it will remember next time. That's the product
pitch in one action.

### 0:45–1:00 — Confirm persistence (prove it works)

**User prompt:**
> What do you remember about my preferences?

**Tool triggered:** `nucleus_engrams` with `action="search_engrams"`

**Expected output:** Surfaces the just-written preference alongside any
other engrams (none yet, so just the one). The model renders:
"From your Nucleus memory: you prefer concise answers with bullet points."

**Why this matters:** This proves the write landed and is queryable. Without
this step, the user has no evidence the memory persisted — the confirmation
in step 2 could be a lie. Recall is the proof.

### 1:00–1:30 — First task (second core workflow)

**User prompt:**
> Create a task titled "Review Q3 roadmap" with high priority and add it to my Nucleus task list.

**Tool triggered:** `nucleus_tasks` with `action="add"`

**Expected output:** Task object with generated ID, status `open`, priority
`high`. Model confirms: "Created task task_def456 in your Nucleus task list."

### 1:30–1:45 — Task recall (prove tracking)

**User prompt:**
> Show me my open tasks.

**Tool triggered:** `nucleus_tasks` with `action="list"`

**Expected output:** The just-created task. Model renders the list.

### 1:45–2:00 — The cross-session promise (the aha moment teaser)

This is not a tool call — it's the **framing** the model should deliver at
the end of the first-run sequence:

> "This memory and task list persist across all your future ChatGPT
> conversations. Start a new chat and ask me 'what do you know about my
> preferences?' — I'll remember."

The aha moment is **next session**, not this one. But the promise has to be
planted in the first 2 minutes or the user never comes back to test it.

## What does NOT deliver value in 2 minutes for a solo user

| Feature | Why it fails on first run | When it lands |
|---------|---------------------------|---------------|
| Search for prior decisions (Test Case 2) | Empty brain, returns nothing | After days of usage |
| Relay to peer agent (Test Case 4) | Solo user has no peer agent fleet | Multi-agent power users only |
| Governance status (Test Case 5) | Empty/default state, meaningless to new user | Advanced users, not first-run |
| Federation | No peer brains configured | Enterprise / multi-tenant |
| Sovereign LLM | Advanced feature, requires local Ollama | Power users with local infra |

These are **power-user surfaces**, not first-run hooks. They belong in a
"what else can Nucleus do?" doc, not the 2-minute onboarding.

## The empty-brain problem

A fresh user's first interaction with `search_engrams` returns nothing.
This is correct behavior (the brain is empty) but feels broken if the user
tries search before writing anything. Two mitigations:

### Mitigation 1 (docs-only, no code change): Ordering

The onboarding sequence above **writes before it searches**. The user never
hits an empty search result during the 2-minute loop. The first search
happens after the first write, so it returns the just-written engram.

### Mitigation 2 (recommended feature, post-freeze): Seed onboarding engram

On first OAuth consent, seed one engram into the new user's brain:

```json
{
  "id": "eng_onboarding_welcome",
  "tags": ["onboarding", "system"],
  "content": "Welcome to Nucleus. This is your sovereign memory — I persist across all your ChatGPT conversations. Ask me to remember anything: preferences, decisions, project context, contacts. Then start a new chat and ask me what I know about you.",
  "context": "Onboarding",
  "intensity": 0.3
}
```

This means the user's first `search_engrams` call (even before they write
anything) returns a meaningful result explaining what Nucleus is and what to
do next. It converts the empty-brain moment from "feels broken" to
"self-explaining."

**Status:** Not implemented. Flagged as a post-freeze feature recommendation.
Requires a first-run hook in the OAuth consent flow (`/authorize` POST
handler) that detects a new tenant and seeds the welcome engram. ~20 LOC.

## Suggested first-run prompts (for the app catalog listing)

If the ChatGPT app catalog listing has a "try these prompts" section, these
are the 2-minute-loop prompts — not the reviewer test cases:

1. **"Remember that I prefer concise answers with bullet points, and save this to my Nucleus memory."**
2. **"What do you remember about my preferences?"**
3. **"Create a task titled 'Review Q3 roadmap' with high priority."**
4. **"Show me my open tasks."**

These work on an empty brain. The reviewer test cases (Test Cases 1–5 in
`CHATGPT_APP_SUBMISSION.md`) require the pre-seeded demo brain and should
stay in the submission materials, not the user-facing listing.

## Negative first-run cases (what NOT to suggest)

These prompts look reasonable but produce empty or confusing results on a
fresh brain:

- **"Search my memory for any decisions about the marketing budget."**
  → Empty brain returns nothing. Frustrating first experience.
- **"Send a relay message to my peer agent."**
  → Solo user has no peer agent. The post succeeds but lands in an inbox
  nobody reads.
- **"Show me the governance status of my session."**
  → Returns default/empty state. Meaningless to a new user.

## Post-approval production flow (how users actually use it once approved)

This section answers the question: **assume the connector passes OpenAI
review and goes live in the ChatGPT app catalog — what does a real user's
end-to-end experience look like?**

### The deployment shape (what we ship, no creds baked in)

The connector is a **remote MCP server** exposed at a public HTTPS endpoint.
No credentials are committed to the repo. The deploy-time contract is:

| Variable | Purpose | Set by |
|----------|---------|--------|
| `OPENAI_OAUTH_CLIENT_ID` | ChatGPT app catalog OAuth client | operator lane at deploy |
| `OPENAI_OAUTH_CLIENT_SECRET` | OAuth client secret | operator lane (secret manager, never in repo) |
| `NUCLEUS_BRAIN_PATH` | Per-tenant brain root | auto-derived from OAuth `sub` claim |
| `NUCLEUS_RELAY_URL` | Relay endpoint (optional, for peer-agent features) | operator lane |
| `NUCLEUS_RELAY_BEARER` | Per-role relay token | operator lane (secret manager) |

The OAuth flow is the **only** user-facing auth surface. The user never
sees or handles any of the above — they click "Add to ChatGPT", approve,
and the connector is live in their chat.

### The live user journey (post-approval, production)

#### Step 1 — Discovery (in ChatGPT app catalog)

User opens ChatGPT → Settings → Connectors → searches "Nucleus" or
"Nucleus memory" → sees the listing with:
- One-line value prop: "Persistent memory across all your ChatGPT conversations."
- The 4 suggested first-run prompts from this doc (see "Suggested first-run
  prompts" section above).
- An **Add to ChatGPT** button.

#### Step 2 — Install (OAuth consent, ~15 seconds)

1. User clicks **Add to ChatGPT**.
2. ChatGPT redirects to our OAuth consent screen (hosted at our public
   endpoint, served by the connector's `/authorize` route).
3. User sees: "Nucleus wants to access your ChatGPT account to provide
   persistent memory. Allow?" → clicks **Allow**.
4. ChatGPT redirects back, connector exchanges the auth code for a token,
   creates a fresh per-tenant brain directory keyed by the OAuth `sub`
   claim (or seeds the welcome engram per Mitigation 2 above if that
   post-freeze feature has shipped).
5. User lands back in ChatGPT with Nucleus tools now available.

**No account creation, no email, no password.** The OAuth flow is the
entire onboarding. This is the single biggest friction-reducer vs. a
traditional SaaS signup.

#### Step 3 — First conversation (the 2-minute value loop)

The user's first chat after install is the 2-minute loop documented in the
"## The 2-minute value loop" section above. The model has the Nucleus
tools loaded; the user writes a memory, recalls it, creates a task, lists
it, and gets the cross-session promise.

#### Step 4 — Subsequent conversations (the retention loop)

This is where the product actually sticks. The user starts a **new** chat
(the next day, next week) and:

1. **Asks a recall question:** "What do you remember about my preferences?"
   → `search_engrams` surfaces everything they've written across all prior
   chats. This is the aha moment — ChatGPT now "knows" them.
2. **Adds new context:** "Remember that I'm working on a Q3 launch and the
   key stakeholder is Sarah." → `engram_write` persists it.
3. **Manages tasks:** "What's on my task list?" → `task_list` returns open
   items from prior sessions.
4. **Optionally uses advanced features** (power-user surfaces, not
   first-run):
   - Relay to peer agents (requires fleet setup — most users never touch this)
   - Governance status (advanced)
   - Federation (enterprise / multi-tenant)

The retention loop is: **write in any chat → recall in any other chat →
the brain compounds.** Every conversation makes the next one smarter.

#### Step 5 — Disconnect (if user wants to stop)

User opens Settings → Connectors → Nucleus → **Remove**. The connector's
OAuth token is revoked; the per-tenant brain directory is preserved
(operator-side, not user-visible) per the data-retention policy documented
in the submission. The user can re-add later and their memories are still
there (unless they explicitly request deletion via the support contact in
the listing).

### What the user never sees (operator-side only)

These are **not user-facing** — they're the operator lane's deploy
responsibilities, listed here only so reviewers understand the full shape:

- The public HTTPS endpoint (Cloudflare-fronted, OCI-backed per the
  current HYBRID v3 topology in ADR-0035).
- The OAuth client registration in the ChatGPT developer portal (operator
  creates this once, at submission time — the client ID/secret are the
  only deploy-time secrets).
- Per-tenant brain isolation (each OAuth `sub` gets its own brain root;
  no cross-tenant data leakage — this is the load-bearing privacy
  invariant and must be test-pinned before going live).
- Relay substrate (optional — only wired if the user's plan includes
  peer-agent features; solo users never touch it).

### Failure modes the user might hit (and what they see)

| Failure | User experience | Operator-side cause |
|---------|-----------------|---------------------|
| Endpoint down | "Nucleus is unavailable right now." | OCI instance offline / Cloudflare tunnel broken |
| OAuth misconfigured | "Couldn't connect — try again or contact support." | Client ID/secret mismatch, redirect URI wrong |
| Brain DB corruption | "Memory recall failed." | SQLite store needs recovery (cc-tb's daemon diagnosis covers this) |
| Rate limit | Slower responses, no error shown | Anthropic API quota (not our surface) |
| Relay unreachable (peer features) | Peer-agent features silently no-op | `NUCLEUS_RELAY_URL` unset or bearer invalid — solo users unaffected |

### What needs to be true BEFORE going live (operator-keyboard gate)

These are the deploy-time prerequisites, all **operator-keyboard** (not
AI-lane) per AGENTS.md spend-class rule:

1. **OAuth client registered** in ChatGPT developer portal — operator
   creates the app, gets client ID + secret, configures redirect URI to
   our public endpoint.
2. **Public endpoint live** — Cloudflare tunnel + OCI backend verified
   healthy (the existing `relay.nucleusos.dev` topology is the template;
   the connector endpoint would be a sibling like `mcp.nucleusos.dev`).
3. **Per-tenant isolation test-pinned** — a regression test proving two
   different OAuth `sub` claims get two different brain roots with zero
   cross-read. This is the load-bearing privacy gate.
4. **Welcome engram seeding** (if Mitigation 2 has shipped) — first-OAuth
   hook seeds the welcome engram so empty-brain search returns something
   meaningful.
5. **Support contact live** — the listing's support URL (Stripe-verified
   `eidetic.works/support`) must resolve and be monitored.

Items 1–2 are spend-class (create cloud resources / register external app)
→ `[FOUNDER-AUTH-NEEDED]` per AGENTS.md. Items 3–5 are code/docs lane and
can ship without founder-auth.

## Cross-references

- `CHATGPT_APP_SUBMISSION.md` — reviewer journey (pre-seeded brain, 5 test cases)
- `CHATGPT_CONNECTOR.md` — setup + OAuth flow + tool list
- `docs/ops/EVENING_2026-06-21_OPERATOR_CARD.md` — pending operator-keyboard items for submission
- `docs/adr/0035-omba-hybrid-v3-azure-postgres-oci-r2.md` — HYBRID v3 topology (deploy shape)
- `AGENTS.md` § "Founder-auth on spend-class commands" — OAuth client registration is spend-class
