# Microsoft 365 Copilot Federated Connector — Submission

> Status: **SUBMITTED 2026-06-23** — Federated Copilot Connector submission
> form (8 pages, 32 fields) completed and submitted via
> https://aka.ms/FccSubmissionForm. Awaiting Microsoft review.
>
> Remaining: (1) deploy endpoint to VM (operator-keyboard),
> (2) apply to Microsoft for Startups for BD rep (Microsoft may route
> submission to Founders Hub if no BD rep is named),
> (3) deploy 32x32 outline logo to eidetic.works.

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

## Required Submission Artifacts (SUBMITTED 2026-06-23)

| Field | Value |
|-------|-------|
| MCP server URL | `https://relay.nucleusos.dev/mcp-readonly/` |
| Connector display name | Nucleus Brain |
| Short description (≤80 chars) | Persistent memory & cross-agent coordination for AI agents |
| Synonyms | memory, engrams, tasks, relay, audit, coordination, brain, nucleus |
| Logo (color.png) | 192x192 — https://eidetic.works/icon-192.png (live) |
| Logo (outline.png) | 32x32 white-on-transparent — https://eidetic.works/icon-32-outline.png (created locally, needs deploy) |
| Auth type | No auth needed (read-only endpoint) |
| Tool list | nucleus_search (Search Engrams), nucleus_audit (Audit Log Query), nucleus_route (Model Cost Router), nucleus_relay_subscribe (Relay Inbox Subscription) |
| Documentation | https://github.com/eidetic-works/nucleus-mcp |
| Privacy policy | https://eidetic.works/privacy-policy |
| Support channel | hello@nucleusos.dev |
| Test credentials | N/A — no auth required |
| Sample prompts | 4 prompts: search engrams, audit log, system health, relay subscription |
| GA date | 2026-06-23 |
| Category | Developer Tools |
| Capabilities | Read Only (all 4 tools readOnlyHint=True) |
| Third-party access | Third-party AI model integration (nucleus_route routes to LLM APIs) |
| Data handling | Server only accesses data explicitly requested by user; HTTPS/TLS encrypted |
| Health data | No |
| BD rep | "N/A — seeking BD rep via Microsoft for Startups Founders Hub" |

## Submission Confirmation

- **Form URL:** https://aka.ms/FccSubmissionForm
- **Submitted:** 2026-06-23
- **Confirmation:** "Your response was submitted." (Microsoft Forms)
- **Screenshot:** `microsoft-fcc-submission-confirmation.png` (this directory)
- **Update contact:** submit-fcc@microsoft.com (for updates to existing submissions)

## Next Steps

1. **Deploy `/mcp-readonly` to relay.nucleusos.dev** — run deploy commands
   from a machine with SSH access to the VM (see above). Microsoft will
   verify the endpoint during review.
2. **Apply to Microsoft for Startups Founders Hub** —
   https://foundershub.startups.microsoft.com/signup
   This gets you a BD rep + up to $150K Azure credits. Self-serve, no
   investor referral code needed. Update the submission with the BD rep
   email via submit-fcc@microsoft.com once assigned.
3. **Deploy 32x32 outline logo** to eidetic.works (file created at
   `landing/public/icon-32-outline.png`, needs landing page redeploy).
4. **Monitor hello@nucleusos.dev inbox** for Microsoft review emails —
   use `scripts/zoho_mail_reader.py --search microsoft` to check.

## Reference

- Submission docs: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/submit-federated-connector
- OAuth 2.0 setup: https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/oauth
- Microsoft for Startups: https://foundershub.startups.microsoft.com/signup
- Microsoft for Startups overview: https://www.microsoft.com/en-us/startups
- Partner Center: https://partner.microsoft.com/
