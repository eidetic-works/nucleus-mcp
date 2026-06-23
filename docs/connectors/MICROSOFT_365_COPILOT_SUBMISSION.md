# Microsoft 365 Copilot Federated Connector — Submission Prep

> Status: **READY TO SUBMIT** — read-only endpoint built (`/mcp-readonly`),
> 4 tools all `readOnlyHint=True`. Remaining: (1) deploy endpoint to VM,
> (2) apply to Microsoft for Startups for BD rep, (3) submit connector.

## Submission Path

Microsoft's federated connector program accepts remote MCP servers for inclusion
in the Microsoft 365 Copilot connectors gallery. Tenant admins approve the
connector, then Microsoft 365 Copilot connects to the MCP server via HTTPS and
surfaces content in Copilot experiences (Copilot app, Researcher agent).

**Official docs:** https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/submit-federated-connector

## Prerequisites

1. **Active engagement with a Microsoft business development representative**
   - This is NOT a self-serve submission. We need a BD contact at Microsoft.
   - **Path: Apply to Microsoft for Startups Founders Hub** — self-serve
     application at https://foundershub.startups.microsoft.com/signup
   - Once approved, you get a dedicated Microsoft point of contact (this IS
     the BD rep) + Marketplace readiness + co-sell support + up to $150K Azure credits.
   - No investor referral code needed — there's a "continue without a code" path.
   - Need: registered business name, website, business address.

2. **Signed legal agreement** permitting Microsoft to use our MCP server and
   its tools within Microsoft 365 Copilot. (Handled by BD rep after Founders Hub approval.)

3. **readOnlyHint requirement** — RESOLVED. Built `/mcp-readonly` endpoint
   with exactly 4 read-only tools:

| Tool | readOnlyHint | Description |
|------|-------------|-------------|
| nucleus_search (NEW) | True | Search engrams (memory) by substring |
| nucleus_audit | True | Query/verify tamper-evident audit log |
| nucleus_route | True | Route prompts to optimal model tier |
| nucleus_relay_subscribe | True | Long-poll relay inbox subscription |

All 4 tools have `readOnlyHint: True`. Microsoft will enable all 4.

## Read-Only Endpoint (Option B — BUILT)

**Status:** Code committed and verified locally. Not yet deployed to production.

**Endpoint URL (after deploy):** `https://relay.nucleusos.dev/mcp-readonly/`

**Architecture:**
- `src/mcp_server_nucleus/http_transport/readonly_app.py` — Separate FastMCP
  instance with only read-only tools
- `src/mcp_server_nucleus/http_transport/app.py` — Combined lifespan runs
  both MCP session managers; read-only app mounted at `/mcp-readonly`
- Root endpoint (`/`) advertises both `mcp_endpoint` and `mcp_readonly_endpoint`

**Deploy commands (operator-keyboard — SSH to VM required):**
```bash
REV=05c592d9
git worktree add --detach /tmp/relay_wt_$REV $REV
rsync -az --delete \
  /tmp/relay_wt_$REV/mcp-server-nucleus/src/mcp_server_nucleus/ \
  ubuntu@<vm-ip>:/opt/nucleus/mcp-server-nucleus/src/mcp_server_nucleus/
ssh ubuntu@<vm-ip> "echo $REV > /opt/nucleus/mcp-server-nucleus/.deployed_rev \
  && sudo systemctl restart nucleus-relay \
  && sleep 2 && curl -fsS http://127.0.0.1:8889/health"
git worktree remove /tmp/relay_wt_$REV
# Verify read-only endpoint:
curl -sS -X POST https://relay.nucleusos.dev/mcp-readonly/ \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

**Note:** SSH to the VM (35.226.177.119) times out from the dev machine.
The VM is behind a firewall that only allows Cloudflare-proxied HTTP.
Deploy must be run from a machine with SSH access to the VM.

## Required Submission Artifacts (once BD rep engaged)

| Field | Value |
|-------|-------|
| MCP server URL | `https://relay.nucleusos.dev/mcp-readonly/` |
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

1. **Deploy `/mcp-readonly` to relay.nucleusos.dev** — run deploy commands
   from a machine with SSH access to the VM (see above).
2. **Apply to Microsoft for Startups Founders Hub** —
   https://foundershub.startups.microsoft.com/signup
   This gets you a BD rep + up to $150K Azure credits. Self-serve, no
   investor referral code needed.
3. **Create logo assets** (192x192 color PNG + 32x32 outline PNG).
4. **Register OAuth credentials** with Microsoft identity platform.
5. **Submit connector** once BD rep + legal agreement are in place.

## Reference

- Submission docs: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/submit-federated-connector
- OAuth 2.0 setup: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/oauth
- Microsoft for Startups: https://foundershub.startups.microsoft.com/signup
- Microsoft for Startups overview: https://www.microsoft.com/en-us/startups
- Partner Center: https://partner.microsoft.com/
