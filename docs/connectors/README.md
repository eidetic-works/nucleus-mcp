# Nucleus Ecosystem Connectors

Nucleus MCP integrates with the proprietary plugin/connector ecosystems of
major AI platforms. Each connector lets the platform's AI agent call Nucleus
MCP tools (memory, tasks, relay, governance) directly from its chat interface.

## Available Connectors

| Platform | Status | Protocol | Auth | Doc |
|----------|--------|----------|------|-----|
| Claude (Code/Desktop/Cowork) | Live | MCP (stdio + HTTP) | API key / OAuth | [Claude setup](https://github.com/eidetic-works/nucleus-mcp#install) |
| Claude Connectors Directory | Submitted (in review) | MCP (Streamable HTTP) | OAuth 2.1 | [Submission checklist](./CLAUDE_DIRECTORY_SUBMISSION.md) |
| VS Code / Cursor | Live | MCP (stdio) | None | [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=eidetic-works.nucleus-bridge) |
| Perplexity | Partnership request sent | MCP (Streamable HTTP) | OAuth 2.1 | [Perplexity setup](./PERPLEXITY_CONNECTOR.md) |
| ChatGPT (Developer Mode) | Ready | MCP (Streamable HTTP) | OAuth 2.1 | [ChatGPT setup](./CHATGPT_CONNECTOR.md) |
| ChatGPT (App Catalog) | Submitted (in review) | Apps SDK + MCP | OAuth 2.1 | [Submission checklist](./CHATGPT_APP_SUBMISSION.md) |
| Grok Build Plugin Marketplace | PR #54 open | MCP (Streamable HTTP) | OAuth 2.1 | [PR #54](https://github.com/xai-org/plugin-marketplace/pull/54) |
| Microsoft 365 Copilot | Blocked (needs BD rep) | MCP (Streamable HTTP) | OAuth 2.0 | [Submission prep](./MICROSOFT_365_COPILOT_SUBMISSION.md) |

## MCP Directories (developer-facing)

| Directory | Status | Listing |
|-----------|--------|---------|
| Official MCP Registry | Live (v1.13.3, with remote endpoint) | [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.eidetic-works%2Fnucleus/versions) |
| Glama | Live | [glama.ai/mcp/servers/eidetic-works/nucleus-mcp](https://glama.ai/mcp/servers/eidetic-works/nucleus-mcp) |
| mcp.so | Live | [mcp.so/server/nucleus-mcp](https://mcp.so/server/nucleus-mcp) |
| Smithery | Live (capabilities thin — OAuth scan issue) | [smithery.ai/server/@eidetic-works/nucleus-mcp](https://smithery.ai/server/@eidetic-works/nucleus-mcp) |
| PulseMCP | Pending (auto-ingests from official registry ~7 days) | — |
| awesome-mcp-servers | PR #8552 open | [PR #8552](https://github.com/punkpeye/awesome-mcp-servers/pull/8552) |

## Public Endpoint

All HTTP-based connectors use the same Nucleus MCP endpoint:

```
https://relay.nucleusos.dev/mcp
```

This serves the MCP protocol over Streamable HTTP transport, with optional
OAuth 2.1 for platforms that require it (ChatGPT).

## Architecture

```
                    ┌─────────────────┐
                    │  Nucleus MCP    │
                    │  HTTP Endpoint  │
                    │  /mcp           │
                    └────┬────────────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
    ┌──────▼─────┐ ┌─────▼──────┐ ┌────▼──────┐
    │ Perplexity │ │  ChatGPT   │ │  Claude   │
    │ Connector  │ │ Connector  │ │ Desktop   │
    │ (no auth)  │ │ (OAuth 2.1)│ │ (API key) │
    └────────────┘ └────────────┘ └───────────┘
```

## OAuth 2.1 Server

For ChatGPT and other platforms that require OAuth, Nucleus includes a
self-contained OAuth 2.1 authorization server:

- `/.well-known/oauth-protected-resource` — RFC 9728
- `/.well-known/oauth-authorization-server` — RFC 8414
- `/register` — Dynamic Client Registration (RFC 7591)
- `/authorize` — Consent screen + authorization code
- `/token` — Token issuance + refresh
- `/revoke` — Token revocation (RFC 7009)

Enable with:
```bash
NUCLEUS_OAUTH_ENABLED=true
NUCLEUS_OAUTH_ISSUER=https://your-domain.com
```

## Self-hosting

See `deploy/oci/README.md` for the OCI Always Free deploy runbook, or run
locally with:

```bash
nucleus-mcp-http --host 0.0.0.0 --port 8766
```
