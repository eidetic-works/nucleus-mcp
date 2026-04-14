# HTTP Transport

stdio connects one agent on one machine. HTTP connects any agent, anywhere.

Three things HTTP transport unlocks:

- **Test from anything** — curl, CI pipelines, Perplexity Computer, remote clients
- **Shared brain** — multiple agents on the same machine hit one Nucleus instance simultaneously
- **Cloud deployment** — always-on, accessible from any agent you control

---

## Option 1 — Local server

```bash
pip install "nucleus-mcp[http]"
nucleus-mcp-http
```

Server starts at `http://127.0.0.1:8766/mcp` (streamable-http transport).

**Verify it's working:**

```bash
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

**Common options:**

```bash
nucleus-mcp-http --port 9000        # custom port
nucleus-mcp-http --transport sse    # SSE transport instead of streamable-http
nucleus-mcp-http --host 0.0.0.0    # bind to all interfaces (team LAN)
```

---

## Option 2 — Container / Cloud Run

```bash
docker build -t nucleus-mcp .
```

**Solo — single user:**

```bash
docker run -p 8080:8080 \
  -e NUCLEUS_TENANT_ID=myorg \
  -v ./brain:/app/.brain \
  nucleus-mcp http
```

**Multi-tenant — team or SaaS:**

```bash
docker run -p 8080:8080 \
  -e NUCLEUS_BRAIN_ROOT=/app/tenants \
  -e NUCLEUS_TENANT_MAP='{"tok_abc":"acme","tok_xyz":"globex"}' \
  -e NUCLEUS_REQUIRE_AUTH=true \
  -v ./tenants:/app/tenants \
  nucleus-mcp http
```

**Endpoints:**

| Path | Method | Purpose |
|------|--------|---------|
| `/` | GET | Identity card (version, mode, transport) |
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/mcp` | POST | MCP endpoint (streamable-http) |
| `/sse` | GET/POST | MCP endpoint when `NUCLEUS_TRANSPORT=sse` |

---

## Tenant modes

### Solo (default)

No configuration needed. All requests use the `default` tenant.

Brain location: `~/.nucleus/tenants/default/.brain`

### Single-tenant

All requests map to one named tenant. Suitable for a Cloud Run deployment serving one org.

```bash
NUCLEUS_TENANT_ID=acme
```

### Multi-tenant

Token → tenant mapping. Each tenant gets a fully isolated brain.

```bash
NUCLEUS_TENANT_MAP='{"tok_abc":"acme","tok_xyz":"globex"}'
NUCLEUS_REQUIRE_AUTH=true
```

Clients authenticate via `Authorization: Bearer <token>`.

**Tenant resolution order:**

1. `Authorization: Bearer <token>` → lookup in `NUCLEUS_TENANT_MAP`
2. `X-Nucleus-Tenant-ID` header
3. `NUCLEUS_TENANT_ID` env var
4. `default` fallback

Each tenant's brain is stored at: `NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain`

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUCLEUS_HTTP_HOST` | `127.0.0.1` | Bind host (Option 1) |
| `NUCLEUS_HTTP_PORT` | `8766` | Bind port (Option 1) |
| `NUCLEUS_HTTP_TRANSPORT` | `streamable-http` | Transport for Option 1: `streamable-http` or `sse` |
| `NUCLEUS_TRANSPORT` | `streamable-http` | Transport for container deployments |
| `NUCLEUS_BRAIN_ROOT` | `~/.nucleus/tenants` | Root directory for per-tenant brain dirs |
| `NUCLEUS_TENANT_ID` | _(none)_ | Static tenant slug |
| `NUCLEUS_TENANT_MAP` | _(none)_ | JSON object mapping tokens to tenant IDs |
| `NUCLEUS_REQUIRE_AUTH` | `false` | Reject requests without a valid bearer token |
| `PORT` | `8080` | Container port (injected by Cloud Run) |
| `NUCLEUS_LOG_LEVEL` | `WARNING` | Log verbosity |

---

## Connecting MCP clients

**Clients that support streamable-http** (Claude Desktop, Cursor, Windsurf — recent versions):

```json
{
  "mcpServers": {
    "nucleus-http": {
      "url": "http://localhost:8766/mcp"
    }
  }
}
```

**Clients that only support SSE:**

```bash
nucleus-mcp-http --transport sse
```

Then point your client at the SSE URL (typically `http://localhost:8766/sse`).

**With auth (multi-tenant):**

```json
{
  "mcpServers": {
    "nucleus-http": {
      "url": "https://your-nucleus-host/mcp",
      "headers": {
        "Authorization": "Bearer tok_abc"
      }
    }
  }
}
```

---

## Data sovereignty

| Deployment | Data | Governance | Network |
|------------|------|------------|---------|
| stdio | Your machine | Your machine | Your machine |
| HTTP local | Your machine | Your machine | Your machine |
| Cloud Run — your own GCP/Oracle instance | Your infra | Your infra | Your infra |
| Cloud Run — managed serverless | Provider infra | You control | Provider infra |

stdio is maximum sovereignty — nothing leaves the machine. HTTP local adds testability without giving anything up. Deploying to your own GCP or Oracle Cloud instance preserves full sovereignty at all three layers.

Managed serverless (Cloud Run, Fly.io, etc.) is a valid choice when you need zero-ops infrastructure — you retain governance sovereignty over which agents can connect and what they can do, but take on an infrastructure dependency. If full sovereignty matters, run on a VM you own.
