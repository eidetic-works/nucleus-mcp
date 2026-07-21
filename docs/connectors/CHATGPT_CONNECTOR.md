# ChatGPT Connector — Nucleus MCP

Connect ChatGPT to your Nucleus Brain for persistent memory, task
orchestration, and cross-agent relay across all your AI tools.

## Prerequisites

- **ChatGPT Plus, Pro, Team, Enterprise, or Education** account
- **Developer Mode** enabled (Settings → Apps → Advanced settings →
  Developer mode)
- A Nucleus Brain endpoint with OAuth 2.1 enabled

## Setup — ChatGPT Developer Mode

### Step 1 — Enable Developer Mode

1. Open **ChatGPT** (web or desktop)
2. Click your profile picture → **Settings**
3. Go to **Apps** → **Advanced settings**
4. Toggle **Developer mode** on
5. Accept the warning about custom connectors

### Step 2 — Add Nucleus as a Custom Connector

1. In **Settings** → **Connectors**, click **Add custom connector**
2. Enter the Nucleus MCP server URL:

```
https://relay.nucleusos.dev/mcp
```

3. ChatGPT will discover the OAuth 2.1 endpoints automatically via
   `/.well-known/oauth-protected-resource` and
   `/.well-known/oauth-authorization-server`
4. You'll be redirected to the Nucleus consent screen — click **Allow**
5. ChatGPT will exchange the authorization code for an access token
6. The connector should show **Connected** with 100+ tools

### Step 3 — Use Nucleus in ChatGPT

1. Start a new conversation
2. Switch to **Developer mode** from the Plus menu
3. Select the **Nucleus Brain** app
4. ChatGPT can now call Nucleus MCP tools:

   - "Use Nucleus to save this decision to memory"
   - "Create a task in Nucleus for tracking this project"
   - "Relay this summary to Claude Code via Nucleus"

## Available tools

Once connected, ChatGPT can call 100+ Nucleus MCP tools including:

- **Memory**: `engram_write`, `engram_search`, `engram_recall`
- **Tasks**: `task_create`, `task_update`, `task_list`
- **Relay**: `nucleus_sync` (cross-agent messaging to Claude Code, Cowork, Perplexity)
- **Governance**: `ground_verify`, `align_correct`, `compound_learn`
- **Sovereign**: `local_llm_generate` (zero-data-egress inference)

Full tool list is auto-discovered by ChatGPT on connect.

## OAuth 2.1 flow (for developers)

Nucleus implements the full MCP authorization spec:

```
ChatGPT                    Nucleus Auth Server              Nucleus MCP
  │                              │                              │
  │ 1. POST /mcp (no auth)       │                              │
  │─────────────────────────────────────────────────────────────>│
  │ 2. 401 + WWW-Authenticate    │                              │
  │<─────────────────────────────────────────────────────────────│
  │ 3. GET /.well-known/oauth-protected-resource                 │
  │─────────────────────────────>│                              │
  │ 4. PRM (auth server URL)     │                              │
  │<─────────────────────────────│                              │
  │ 5. GET /.well-known/oauth-authorization-server              │
  │─────────────────────────────>│                              │
  │ 6. AS metadata (endpoints)   │                              │
  │<─────────────────────────────│                              │
  │ 7. POST /register (DCR)      │                              │
  │─────────────────────────────>│                              │
  │ 8. client_id + secret        │                              │
  │<─────────────────────────────│                              │
  │ 9. GET /authorize (browser)  │                              │
  │─────────────────────────────>│                              │
  │ 10. Consent screen           │                              │
  │<─────────────────────────────│                              │
  │ 11. POST /authorize (allow)  │                              │
  │─────────────────────────────>│                              │
  │ 12. Redirect with code       │                              │
  │<─────────────────────────────│                              │
  │ 13. POST /token (code)       │                              │
  │─────────────────────────────>│                              │
  │ 14. access_token + refresh   │                              │
  │<─────────────────────────────│                              │
  │ 15. POST /mcp (Bearer)       │                              │
  │─────────────────────────────────────────────────────────────>│
  │ 16. MCP response             │                              │
  │<─────────────────────────────────────────────────────────────│
```

## Self-hosted deployment

To enable OAuth on your own Nucleus HTTP server:

```bash
# Set these env vars on your nucleus-mcp-cloud process
NUCLEUS_OAUTH_ENABLED=true
NUCLEUS_OAUTH_ISSUER=https://your-domain.com
NUCLEUS_OAUTH_STORE_PATH=/path/to/oauth_store.json
```

The OAuth endpoints are served at:
- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-authorization-server`
- `/register` (Dynamic Client Registration)
- `/authorize` (consent screen)
- `/token` (token issuance + refresh)
- `/revoke` (token revocation)

## Scopes

| Scope | Description |
|-------|-------------|
| `mcp:tools` | Call Nucleus MCP tools (default) |
| `mcp:resources` | Read Nucleus MCP resources |
| `mcp:prompts` | Use Nucleus MCP prompts |
| `mcp:relay` | Send and receive cross-agent relay messages |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No OAuth metadata found" | Verify `NUCLEUS_OAUTH_ENABLED=true` is set on the server; check `curl https://relay.nucleusos.dev/.well-known/oauth-protected-resource` returns JSON |
| Consent screen doesn't load | Check browser console for CORS errors; ensure `NUCLEUS_OAUTH_ISSUER` matches the public URL |
| "invalid_client" on token exchange | DCR may have failed; try removing the connector and re-adding it |
| Token expired | ChatGPT auto-refreshes; if it fails, remove and re-add the connector |
| Tools not appearing | Ensure Developer Mode is on; select the Nucleus app in the conversation |

## ChatGPT Apps SDK (catalog distribution)

For distribution to ALL ChatGPT users (not just Developer Mode users),
the ChatGPT Apps SDK path is being built. This will publish Nucleus to
the ChatGPT app catalog with a one-click install. See Phase 3 in the
connector roadmap.

## References

- [ChatGPT Developer Mode & MCP Apps](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta)
- [MCP Authorization Spec](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [RFC 9728 — Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- [RFC 8414 — Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)
- [RFC 7591 — Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591)
- [Nucleus MCP on PyPI](https://pypi.org/project/nucleus-mcp/)
