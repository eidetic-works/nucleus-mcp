# Microsoft 365 Copilot Federated Connector — Submission Prep

> Status: **BLOCKED** — requires (1) Microsoft BD rep engagement, (2) readOnlyHint strategy decision

## Submission Path

Microsoft's federated connector program accepts remote MCP servers for inclusion
in the Microsoft 365 Copilot connectors gallery. Tenant admins approve the
connector, then Microsoft 365 Copilot connects to the MCP server via HTTPS and
surfaces content in Copilot experiences (Copilot app, Researcher agent).

**Official docs:** https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/submit-federated-connector

## Prerequisites (BLOCKERS)

1. **Active engagement with a Microsoft business development representative**
   - This is NOT a self-serve submission. We need a BD contact at Microsoft.
   - Sign-up: Microsoft 365 and Copilot program via Partner Center.

2. **Signed legal agreement** permitting Microsoft to use our MCP server and
   its tools within Microsoft 365 Copilot.

3. **readOnlyHint requirement** — Microsoft only enables tools with
   `readOnlyHint: True`. Our current tool annotations:

| Tool | readOnlyHint | Would be enabled? |
|------|-------------|-------------------|
| nucleus_audit (Audit Log) | True | ✅ Yes |
| nucleus_route (Cost Router) | True | ✅ Yes |
| nucleus_relay_subscribe (Relay Subscription) | True | ✅ Yes |
| nucleus_engrams (Memory & Engrams) | False | ❌ No |
| nucleus_tasks (Task Management) | False | ❌ No |
| nucleus_relay (Relay Messaging) | False | ❌ No |
| nucleus_governance (Governance) | False | ❌ No |
| nucleus_federation (Federation) | False | ❌ No |
| nucleus_sessions (Session Management) | False | ❌ No |
| nucleus_features (Feature Flags) | False | ❌ No |
| nucleus_sync (Cross-Agent Sync) | False | ❌ No |
| nucleus_orchestration (Orchestration) | False | ❌ No |
| nucleus_telemetry (Telemetry) | False | ❌ No |
| nucleus_slots (Slots & Sprints) | False | ❌ No |
| nucleus_infra (Infrastructure) | False | ❌ No |
| nucleus_agents (Agent Spawning) | False | ❌ No |
| nucleus_ccr_arm (CCR Arm) | False | ❌ No |

**Result: Only 3 of 17 tools would be enabled.** This gives a crippled
experience — just audit log viewing, cost routing, and relay subscription.
No memory writing, no task management, no relay messaging.

## Options to Resolve the readOnlyHint Blocker

### Option A: Submit with 3 read-only tools (fastest, degraded experience)
- Submit as-is. Microsoft enables only audit_log, cost_router, relay_subscribe.
- Copilot users can view audit logs, check cost routing, and subscribe to relay
  channels — but can't write memories, create tasks, or post relay messages.
- **Pro:** Fast submission once BD contact is established.
- **Con:** Crippled experience. Users won't see the core value (memory + tasks).

### Option B: Create a read-only MCP endpoint variant (medium effort)
- Stand up a second MCP endpoint (e.g., `relay.nucleusos.dev/mcp-readonly`)
  that exposes only the 3 read-only tools + a new `search_engrams` tool with
  `readOnlyHint: True` (search is read-only even though engram writing isn't).
- Submit the read-only endpoint to Microsoft.
- **Pro:** Better experience — users can at least search memories + view audit.
- **Con:** Still no writing capability. Requires new endpoint + tool split.

### Option C: Petition Microsoft for an exception (slow, uncertain)
- Ask the BD rep to enable write tools despite the readOnlyHint policy.
- Microsoft's policy exists for safety — they don't want Copilot agents
  modifying external state without explicit user consent.
- **Pro:** Full experience if approved.
- **Con:** Unlikely to succeed. The policy is documented as a hard requirement.

### Option D: Wait for Microsoft to expand support (passive)
- Microsoft may expand federated connectors to support write tools in the
  future as the MCP ecosystem matures.
- Monitor the docs page for policy changes.
- **Pro:** No effort required.
- **Con:** Indefinite timeline. May never happen.

**Recommendation: Option B** — create a read-only endpoint variant with
search_engrams (readOnlyHint=True) + audit_log + cost_router + relay_subscribe.
This gives Copilot users a meaningful experience (search memories, view audit
logs, subscribe to relay channels) while we wait for Microsoft to expand
write-tool support.

## Required Submission Artifacts (once blockers resolved)

| Field | Value |
|-------|-------|
| MCP server URL | `https://relay.nucleusos.dev/mcp` (or `/mcp-readonly` for Option B) |
| Connector display name | Nucleus Brain |
| Short description (≤80 chars) | Persistent memory & cross-agent coordination for AI agents |
| Synonyms | memory, engrams, tasks, relay, audit, coordination, brain |
| Logo (color.png) | 192x192 full-color PNG — needs creation |
| Logo (outline.png) | 32x32 white-on-transparent PNG — needs creation |
| OAuth credentials | OAuth reference ID from Microsoft registration (needs setup) |
| Tool list | All tools with readOnlyHint=True + human-readable names |
| Documentation | https://eidetic.works + https://github.com/eidetic-works/nucleus-mcp |
| Privacy policy | https://eidetic.works/privacy |
| Support channel | hello@nucleusos.dev |
| Test credentials | OAuth 2.1 email-only consent (same as Claude Directory submission) |
| Sample prompts | 1. "Search my engrams for decisions about authentication" 2. "Show the last 10 audit log entries" 3. "Check Nucleus system health" |

## Next Steps

1. **Find a Microsoft BD contact** — via Partner Center enrollment or
   Microsoft for Startups program. This is the primary blocker.
2. **Decide on readOnlyHint strategy** (Option A/B/C/D above).
3. **Create logo assets** (192x192 color PNG + 32x32 outline PNG).
4. **Register OAuth credentials** with Microsoft identity platform.
5. **Submit** once BD contact + legal agreement are in place.

## Reference

- Submission docs: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/submit-federated-connector
- OAuth 2.0 setup: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/oauth
- Partner Center: https://partner.microsoft.com/
- Microsoft 365 and Copilot program: via Partner Center > Marketplace offers
