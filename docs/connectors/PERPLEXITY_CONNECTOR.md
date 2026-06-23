# Perplexity Connector — Nucleus MCP

Connect Perplexity to your Nucleus Brain for persistent memory, task
orchestration, and cross-agent relay across all your AI tools.

## Prerequisites

- **Perplexity Pro, Max, or Enterprise** plan (custom MCP connectors are
  not available on Free)
- Custom connector feature enabled in Settings (shipped 2026-03-13)
- A Nucleus Brain endpoint (self-hosted or `https://relay.nucleusos.dev/mcp`)

## Setup — Perplexity UI

1. Navigate to **https://www.perplexity.ai/computer/connectors** (or log in
   → profile → All settings → Connectors)
2. Click **+ Custom connector** in the top-right corner
3. Fill in:

| Field | Value |
|-------|-------|
| Name | `Nucleus Brain` |
| MCP server URL | `https://relay.nucleusos.dev/mcp` |
| Transport | Streamable HTTP (default) |
| Auth | OAuth 2.0 (select OAuth, Client ID auto-generated) |

4. Tick **"I understand custom connectors can introduce risks"**
5. Click **Add**
6. Click the connector in the search result. A browser window opens for
   OAuth consent → enter your email → click **Allow**. A tenant brain is
   auto-created with seeded demo data.
7. On the prompt page, enable the Nucleus Brain connector to allow Perplexity
   to call the MCP server.

8. (Recommended) Paste the following into the **Custom instructions** field
   of any Space where you want Nucleus active:

```
You have access to Nucleus Brain tools for persistent memory and task
orchestration. Use nucleus_relay to send messages to other AI agents
(Claude Code, Cowork, Antigravity). Use nucleus_engrams to persist
important decisions. Use nucleus_tasks to track multi-step work across
sessions. Prefer Nucleus tools over repeating context in the conversation.
```

## Available tools

Once connected, Perplexity can call 17 Nucleus MCP tools:

| Tool | Human-readable name | Capability |
|------|-------------------|------------|
| nucleus_engrams | Memory & Engrams | Write/search/recall persistent memories |
| nucleus_tasks | Task Management | Create, update, list tasks with depth scoring |
| nucleus_relay | Relay Messaging | Cross-agent messaging (Claude Code, Cowork, etc.) |
| nucleus_audit | Audit Log | Tamper-evident audit trail |
| nucleus_governance | Governance | Ground verification, alignment correction |
| nucleus_federation | Federation | Cross-brain federation |
| nucleus_sessions | Session Management | Session lifecycle |
| nucleus_features | Feature Flags | Feature flag management |
| nucleus_sync | Cross-Agent Sync | Multi-agent state synchronization |
| nucleus_orchestration | Orchestration | Workflow orchestration |
| nucleus_telemetry | Telemetry | System metrics |
| nucleus_slots | Slots & Sprints | Sprint/slot management |
| nucleus_infra | Infrastructure | Infrastructure management |
| nucleus_agents | Agent Spawning | Spawn sub-agents |
| nucleus_route | Cost Router | Cost-aware model routing |
| nucleus_ccr_arm | CCR Arm | CCR subscription arming |
| nucleus_relay_subscribe | Relay Subscription | Subscribe to relay channels |

Full tool list is auto-discovered by Perplexity on connect.

## Auth

The public endpoint at `relay.nucleusos.dev/mcp` uses OAuth 2.1 with
email-only consent (no password). On first connection, Perplexity opens
a browser window for OAuth authorization.

For self-hosted deployments with auth:

1. Set `NUCLEUS_REQUIRE_AUTH=true` on your Nucleus HTTP server
2. Generate a bearer token: `python scripts/gen_relay_token.py perplexity`
3. In Perplexity connector settings, select **API Key** auth and
   paste the token

## Self-hosted alternative

If you run Nucleus MCP HTTP locally:

```bash
nucleus-mcp-http --host 0.0.0.0 --port 8766
```

Then use `http://<your-host>:8766/mcp` as the Server URL in Perplexity.
Note: Perplexity requires HTTPS for remote connectors. For local development,
use a tunnel like `ngrok http 8766` or `cloudflared tunnel`.

For cloud deployment (Cloud Run, Fly.io, OCI):

```bash
nucleus-mcp-cloud
```

See `deploy/oci/README.md` for the OCI Always Free deploy runbook.

## Sample prompts

Once connected, try these in Perplexity:

1. **"Search my engrams for decisions about authentication architecture"**
   → calls `nucleus_engrams` with `action=search_engrams`

2. **"What tasks are in my brain? Show high priority items."**
   → calls `nucleus_tasks` with `action=list`

3. **"Write a memory: key=perplexity-test, value=hello from Perplexity"**
   → calls `nucleus_engrams` with `action=write_engram`

4. **"Show the last 10 audit log entries"**
   → calls `nucleus_audit` with `action=recent`

5. **"Check Nucleus system health"**
   → calls `nucleus_engrams` with `action=health`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connector shows "Failed to connect" | Verify the URL is reachable: `curl -sS https://relay.nucleusos.dev/health` returns 200 |
| Tools not appearing | Ensure Perplexity plan supports custom connectors (Pro+); try removing and re-adding the connector |
| OAuth window doesn't open | Check popup blocker; try in an incognito window |
| "Missing session ID" error | This is normal — Perplexity handles session management internally; the error appears only on raw curl probes without the initialize handshake |
| 406 Not Acceptable | The endpoint requires `Accept: text/event-stream` — Perplexity sends this automatically; raw curl probes need `-H "Accept: text/event-stream"` |

## Official gallery listing — IN REVIEW

We have submitted a partnership request to Perplexity (email to
`partnerships@perplexity.ai` on June 22, 2026) to be listed in the official
App Connectors gallery at `perplexity.ai/enterprise/app-connectors`.

**Status:** Awaiting response from Perplexity partnerships team.

If approved, Nucleus Brain will be discoverable in the connector gallery
without requiring manual URL entry. Until then, users can add it as a
custom remote connector using the setup steps above.

## References

- [Perplexity Custom MCP Connectors](https://docs.perplexity.ai/)
- [Perplexity App Connectors gallery](https://www.perplexity.ai/enterprise/app-connectors)
- [Perplexity Partnerships](mailto:partnerships@perplexity.ai)
- [Nucleus MCP on PyPI](https://pypi.org/project/nucleus-mcp/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Nucleus Brain homepage](https://eidetic.works)
