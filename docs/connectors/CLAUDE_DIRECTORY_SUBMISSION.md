# Claude Connectors Directory Submission Checklist

This doc tracks the full submission process for getting Nucleus MCP into
Anthropic's Connectors Directory (one-click install for all Claude users
across Claude.ai, Desktop, Mobile, Code, and Cowork).

## Status: SUBMITTED — in Anthropic review queue (2026-06-22)

> All 6 pages of the MCP Directory Submission Form completed and submitted
> via the public Google Form (https://clau.de/mcp-directory-submission).
> Anthropic does not guarantee acceptance or individual response due to
> volume. One placeholder to update if accepted: Server Logo SVG URL.

---

### Code-side (DONE)

| Item | Status | Evidence |
|------|--------|----------|
| Public MCP endpoint | DONE | `https://relay.nucleusos.dev/mcp` (live, v3.4.2) |
| OAuth 2.1 server | LIVE | `NUCLEUS_OAUTH_ENABLED=true` on relay; DCR→authorize→token→MCP verified end-to-end |
| Tool annotations (all 17 tools) | DONE | `readOnlyHint` / `destructiveHint` / `openWorldHint` on every `@mcp.tool()` |
| Tool titles (all 17 tools) | DONE | `title=` on every `@mcp.tool()` — verified 17/17 live on relay (commit 9db3a91f) |
| `/.well-known/oauth-protected-resource` | LIVE | RFC 9728 metadata — returns 200 with correct issuer |
| `/.well-known/oauth-authorization-server` | LIVE | RFC 8414 metadata — returns 200 with correct issuer |
| Streamable HTTP transport | DONE | `NUCLEUS_TRANSPORT=streamable-http` (default) |
| Privacy policy URL | EXISTS | `https://eidetic.works/privacy` |
| Terms of service URL | EXISTS | `https://eidetic.works/terms` |
| Public documentation | EXISTS | `https://github.com/eidetic-works/nucleus-mcp` + `https://eidetic.works` |
| Per-tenant isolation | DONE | Cross-tenant leak fix in `tenant.py` middleware; welcome engram seeding on new tenant creation |
| Demo data seeded | DONE | 17 engrams + 7 tasks in "oauth" tenant brain (same as ChatGPT submission) |

### Known risk: action-dispatcher pattern

Our 17 tools use a facade pattern: `nucleus_engrams(action="write_engram", params={...})`.
Each tool handles 20-30 different actions, mixing reads and writes. Claude's review
criteria says "Do not ship a catch-all `api_request` tool with a `method` parameter.
Split into a read-only tool and one or more write tools."

Our tools are NOT HTTP proxies with a `method` parameter — they're semantic action
dispatchers. But the spirit of the rule may apply. **Decision: submit as-is and learn
from the reviewer response.** If rejected, we'll split tools based on specific feedback
rather than guessing.

---

### Submission artifacts (pre-filled for operator)

Fill these into the Claude submission portal:

#### Server connection

| Field | Value |
|-------|-------|
| Server URL | `https://relay.nucleusos.dev/mcp` |
| Transport | Streamable HTTP |
| Same URL for all users? | Yes |

#### Listing

| Field | Value | Limit |
|-------|-------|-------|
| Server name | `Nucleus Brain` | 100 chars |
| Tagline | `Persistent memory & cross-agent coordination for AI` | 55 chars |
| Description | (see below) | 2000 chars |
| Categories | `Productivity`, `Developer Tools`, `Knowledge Management` | 1-5 categories |
| Documentation URL | `https://github.com/eidetic-works/nucleus-mcp` | — |
| Privacy policy URL | `https://eidetic.works/privacy` | — |
| Support contact | `hello@nucleusos.dev` | — |
| URL slug | `nucleus-brain` | permanent once published |

#### Description (2000 chars max)

```
Nucleus Brain gives your AI assistant persistent memory, task management, and cross-agent coordination. Write memories (engrams) that survive across sessions, search and recall past decisions, track tasks with depth scoring, and relay messages between AI agents working on the same project.

Key capabilities:
- Memory: Write, query, and search engrams (persistent memory entries) with context tagging and intensity scoring
- Tasks: Create, update, and track tasks with priority, skill, and claim management
- Relay: Send messages between AI agents (Claude, ChatGPT, Perplexity, custom agents) via a filesystem-or-HTTP relay substrate
- Governance: Verify system state, run auto-fix loops, and maintain tamper-evident audit logs
- Federation: Coordinate across multiple Nucleus brain instances
- Cost routing: Route prompts to optimal model tiers (Haiku/Sonnet/local) for cost efficiency

Each tool exposes multiple actions via an `action` parameter — see tool descriptions for the full action list. OAuth 2.1 authentication with per-tenant brain isolation. Self-hosted or use the hosted endpoint at relay.nucleusos.dev.
```

#### Use cases

```
Primary use cases:
1. Persistent memory across conversations — write decisions, architecture notes, and context that survives session boundaries
2. Multi-agent coordination — relay messages between Claude, ChatGPT, and other AI tools working on the same project
3. Task tracking with depth scoring — manage multi-step work and track progress across sessions
4. Audit and compliance — tamper-evident SHA-256 chained audit log for sensitive operations

What users need before connecting:
- No account required for the hosted endpoint (anonymous mode available)
- OAuth 2.1 flow handles authentication automatically (email-only consent, no password)
- For self-hosting: install nucleus-mcp via pip and run nucleus-mcp-http

Reads data: yes (engram queries, task lists, audit logs, health checks)
Writes data: yes (engram writes, task creation, relay messages, audit events)
```

#### Company

| Field | Value |
|-------|-------|
| Company name | `Eidetic Works` |
| Website | `https://eidetic.works` |

#### Test credentials

```
The connector uses OAuth 2.1 with email-only consent (no password).
Reviewer flow:
1. Click "Add to Claude" → consent screen appears
2. Enter any email address → click "Allow"
3. A tenant brain is auto-created with 17 seeded engrams + 7 tasks
4. All 17 tools are immediately callable

Test prompts for reviewers:
- "Search my engrams for decisions" (nucleus_engrams action=search_engrams)
- "What tasks are in my brain?" (nucleus_tasks action=list)
- "Write a memory: key=test, value=hello" (nucleus_engrams action=write_engram)
- "Show system health" (nucleus_engrams action=health)
- "List recent relay messages" (nucleus_relay action=read)
```

---

### Operator-keyboard items

#### 1. Submit through Claude.ai admin portal (if on Team/Enterprise)

**Link:** https://claude.ai (→ Settings → Admin → Connectors → Submit)

**Steps:**
1. Log in to Claude.ai with an organization Owner account (Team or Enterprise plan)
2. Go to **Admin Settings** → **Connectors** → **Submission portal**
3. Enter the server URL: `https://relay.nucleusos.dev/mcp`
4. The portal will auto-sync tools from the server
5. Fill in the listing details from the artifacts above (name, tagline, description, categories, URLs)
6. Paste the use cases and company info
7. Provide test credentials (email-only OAuth flow)
8. Submit for review

#### 2. OR submit via public form (if NOT on Team/Enterprise)

**Link:** https://claude.com/docs/connectors/building/submission (→ "MCP directory submission form")

**Steps:**
1. Open the submission form
2. Fill in the same artifacts as above
3. Submit

#### 3. Check submission status

After submitting, track status at the submissions dashboard in Claude.ai admin settings.
Email `connectors@anthropic.com` for escalations.

---

### What happens after submission

1. **Review queue:** Anthropic reviewers test every tool and run a policy compliance scan
2. **Review time:** Varies with queue volume
3. **Possible outcomes:**
   - **Accepted** — listed in the Connectors Directory, available across all Claude products
   - **Rejected with feedback** — we fix issues and resubmit
   - **Rejected for action-dispatcher pattern** — we split tools into read/write pairs or individual tools based on specific feedback
4. **After publication:** Dashboard shows server health and usage metrics
