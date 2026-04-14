# ADR-001: HTTP Transport Layer and Tenant-Aware Sovereignty Architecture

## Status

Implemented — v1.9.0

## Date

2026-04-14

---

## Context

Nucleus MCP was originally designed around stdio transport. The stdio model is simple and correct for a single developer running a single agent on a single machine: the MCP client spawns the server as a subprocess, communicates over stdin/stdout, and the process dies with the session. No network surface, maximum data locality.

That simplicity becomes a hard ceiling as usage grows. Stdio has three fundamental limitations:

1. **One session at a time.** A stdio server cannot accept a second connection while the first is open. Running Claude Code and Cursor simultaneously against the same Nucleus brain is impossible — each would spawn its own subprocess with its own independent state.

2. **No network presence.** There is no address to give a remote client. Perplexity Computer, CI pipelines, webhook handlers, and agents running on other machines have no way to reach a stdio server. Testing requires physical co-location with the process.

3. **No multi-agent orchestration.** Agents on different machines or in different clouds cannot share a Nucleus brain. The persistent memory model only persists within a single process lifetime on a single host.

The decision was made to add HTTP transport as an additive layer — preserving the existing stdio entrypoint without modification while enabling network-accessible deployments ranging from localhost-only to globally hosted Cloud Run instances.

---

## Decision Drivers

Three axes drove the design:

### 1. Capability spectrum

- Can multiple MCP clients share one brain simultaneously?
- Can the server be tested with standard HTTP tools (curl, CI runners)?
- Can agents on remote machines connect?
- Can the server persist across agent sessions and machine reboots?

### 2. Sovereignty spectrum

**Data sovereignty** — Who controls where brain data lives.
- stdio: maximum. Files never leave the machine.
- HTTP local: high. Still on the local filesystem; exposure is only at the network layer.
- Cloud Run: medium-high. Depends on infrastructure choice. Running on an instance you own (GCP VM, Oracle Compute) is substantially different from managed serverless.

**Governance sovereignty** — Ability to enforce policies on agents that connect.
- stdio: zero. You can only govern agents on the same machine.
- HTTP local: local. You can govern any agent on the same network that you allow to connect.
- Cloud Run: full. Any agent connecting over the internet passes through your endpoint, where you control auth, rate limits, audit logging, and access control.

**Network sovereignty** — Control over the network surface itself.
- stdio: none. There is no network surface.
- HTTP local: controlled. You choose the binding address and port.
- Cloud Run: full. You own the endpoint, TLS termination, routing, and DNS.

The real sovereignty unlock is when Cloud Run runs on infrastructure you fully control — a dedicated GCP VM or Oracle Compute instance, not managed serverless — where Nucleus is sovereign at all three layers simultaneously.

### 3. Solo → enterprise deployment spectrum

The same codebase must serve all of these use cases without forking:

| Deployment | Transport | Notes |
|---|---|---|
| Solo developer | stdio | Fine. HTTP local is a superpower for testing. |
| Founder / small team | HTTP local on LAN, or private Cloud Run | Single-tenant, minimal ops. |
| Enterprise | Cloud Run, per-org Nucleus instances | Multi-tenant isolation, audit trails, SSO. |
| SaaS product | Cloud Run as the product | Hosted Nucleus endpoints sold per workspace. |

---

## Decision

Two HTTP deployment options were built on top of a shared transport foundation. The existing `nucleus-mcp` stdio entrypoint was left entirely unchanged.

### Option 1: `nucleus-mcp-http` (local HTTP server)

A new CLI entrypoint that binds the same `mcp` instance to HTTP on `127.0.0.1` (configurable). This is the recommended first step beyond stdio: the same brain, same tools, now accessible over HTTP to any client on the same machine or LAN.

Use this when:
- You want multiple MCP clients (Claude Code, Cursor, Windsurf) sharing one brain simultaneously.
- You are testing from Perplexity Computer, CI, or any remote HTTP client.
- You want network presence without cloud infrastructure.

### Option 2: `nucleus-mcp-cloud` / `app.py` (Cloud Run ASGI app)

A Starlette-based ASGI application with health and readiness endpoints, composable routing, and tenant-aware middleware. Designed to run as a container in Cloud Run, Fly.io, or any OCI-compatible host.

Use this when:
- You need an always-on endpoint that survives across agent sessions.
- You need multi-tenant isolation (multiple orgs sharing one deployment).
- You are building Nucleus as a hosted SaaS product.

### What was built

| File | Role |
|---|---|
| `src/mcp_server_nucleus/http_transport/tenant.py` | Tenant resolution and brain isolation middleware |
| `src/mcp_server_nucleus/http_transport/server.py` | Option 1 entrypoint (`nucleus-mcp-http` CLI) |
| `src/mcp_server_nucleus/http_transport/__init__.py` | Package exports |
| `src/app.py` | Option 2 Cloud Run ASGI app (rewritten from Flask stub) |
| `deploy/entrypoint.sh` | Container entrypoint supporting `sovereign`, `http`, and `cli` modes |
| `pyproject.toml` | New scripts `nucleus-mcp-http`, `nucleus-mcp-cloud`; new `[http]` dependency group |
| `Dockerfile` | Installs `[full,http]` extras, exposes port 8080, updated `HEALTHCHECK` |

---

## Transport Spectrum

| Dimension | stdio | HTTP local | Cloud Run |
|---|---|---|---|
| **Clients** | 1 | Many (same machine or LAN) | Unlimited (internet) |
| **Persistence** | Session lifetime | Process lifetime | Always-on |
| **Testable via curl** | No | Yes | Yes |
| **CI pipelines** | No | Yes (localhost) | Yes (public URL) |
| **Remote agents** | No | No (LAN only) | Yes |
| **Data sovereignty** | Maximum | High | Medium-high |
| **Governance sovereignty** | Zero | Local network | Full |
| **Network sovereignty** | None | Controlled | Full |
| **Ops complexity** | None | Low | Medium |
| **Infrastructure required** | None | None | Container host |
| **Recommended for** | Solo dev | Dev/test, small teams | Enterprise, SaaS |

---

## Tenant Architecture

### The core question

Should each user or org get their own Nucleus process, or should Nucleus be a shared control plane with per-tenant namespacing?

**Answer: support both via tenant-aware middleware.** The same binary can run as:

- **Solo** — no configuration, all requests resolve to the `"default"` tenant.
- **Team** — `NUCLEUS_TENANT_MAP` maps bearer tokens to tenant IDs; each team member gets their own isolated brain.
- **Multi-tenant SaaS** — `NUCLEUS_BRAIN_ROOT` with per-tenant subdirectories; arbitrary numbers of tenants, no per-tenant process needed.

### Tenant resolution order

`NucleusTenantMiddleware` resolves the tenant for every HTTP request. First match wins:

1. `Authorization: Bearer <token>` — token is looked up in `NUCLEUS_TENANT_MAP` (JSON env var mapping `{token: tenant_id}`). If found, the mapped `tenant_id` is used.
2. `X-Nucleus-Tenant-ID` header — used directly as the tenant ID. Suitable for internal service-to-service calls where the caller is trusted.
3. `NUCLEUS_TENANT_ID` environment variable — static single-tenant fallback. Useful for dedicated per-org deployments where the tenant is fixed at deploy time.
4. `"default"` — the unconditional solo fallback.

### Brain isolation

Each tenant gets a fully isolated brain directory:

```
NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain/
```

The middleware sets `os.environ["NUCLEUS_BRAIN_PATH"]` to the resolved tenant brain path before passing the request to the MCP app. The MCP tools read `NUCLEUS_BRAIN_PATH` at call time, so they transparently operate on the correct brain without any modification to tool logic.

No tenant can read or write another tenant's brain. This isolation is enforced in the middleware layer, not in individual tools. Adding a new tool does not require any tenant-awareness logic in the tool itself — isolation is automatic.

### Caveats

- `os.environ` mutation is process-global. This is safe under uvicorn's default single-threaded async model (one request runs to completion before the next begins in a single worker). It is **not safe** for multi-process or true concurrent deployments. See the Risks section below.
- `X-Nucleus-Tenant-ID` bypasses token authentication. Never expose it on a public endpoint without adding an authentication layer in front.

---

## Consequences

### Positive

- **Zero regression on stdio.** The `nucleus-mcp` entrypoint is untouched. Any existing stdio-based workflow continues to work identically.
- **Additive complexity.** HTTP transport is a new code path, not a modification of existing paths. Contributors not working on transport do not need to understand it.
- **Testability.** Any MCP interaction can now be exercised with `curl` or from a CI pipeline. No agent harness required.
- **Composability.** The fastmcp `mcp.http_app()` returns a standard Starlette ASGI app. It composes cleanly with any ASGI middleware, router, or host.
- **Multi-client brain sharing.** Multiple MCP clients on the same machine can share a single Nucleus instance simultaneously, which is impossible with stdio.
- **Path to SaaS.** The tenant middleware enables multi-tenant deployments without forking the codebase.

### Negative / Trade-offs

- **Ops surface.** HTTP transport requires a running process (or container). It does not self-start; someone must manage the process lifecycle.
- **Auth is not built-in.** The bearer token lookup in `NUCLEUS_TENANT_MAP` provides tenant resolution, not cryptographic authentication. For production deployments, a proper auth layer (API gateway, mTLS, OAuth) must be added in front.
- **`os.environ` mutation.** The per-request brain path injection via `os.environ` is a known anti-pattern for concurrent environments. It works correctly today under uvicorn's async model but will require refactoring if Nucleus moves to multi-process workers or a thread-per-request model.
- **Dependency footprint.** The `[http]` extras add Starlette, uvicorn, and httpx. These are not installed by default for stdio-only users.

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `os.environ` mutation causes brain path bleed between requests in a multi-process deployment | Medium | Critical (data corruption) | Document the limitation clearly; add a `NUCLEUS_WARN_MULTIPROCESS` check that logs a warning if `WEB_CONCURRENCY > 1` and the environ-mutation strategy is active |
| `X-Nucleus-Tenant-ID` header abused to access arbitrary tenants | High (if exposed publicly) | Critical | Document that this header requires a trusted network or authentication layer upstream; consider making it opt-in via `NUCLEUS_TRUST_TENANT_HEADER` |
| Bearer token secrets in `NUCLEUS_TENANT_MAP` leaked via env var | Medium | High | Use a secrets manager (GCP Secret Manager, Vault) to inject the env var at runtime rather than baking it into the container image |
| HTTP port exposed unintentionally on a public interface | Low | High | Default binding is `127.0.0.1`; public binding requires explicit `HOST=0.0.0.0` configuration |

---

## Implementation Notes

### fastmcp ASGI integration

`fastmcp` exposes `mcp.http_app(transport="streamable-http")` which returns a Starlette `Route`-mountable ASGI callable backed by the same `mcp` instance as the stdio entrypoint. This is the correct integration point — it avoids duplicating tool registration and keeps the two transports in sync automatically.

The transport parameter defaults to `"streamable-http"` (MCP spec compliant). Set `NUCLEUS_TRANSPORT=sse` to use the legacy SSE transport for clients that have not yet adopted streamable-http.

### Middleware wrapping

`NucleusTenantMiddleware` is a Starlette `BaseHTTPMiddleware` subclass. It runs before the fastmcp ASGI app on every request, resolves the tenant, mutates `os.environ["NUCLEUS_BRAIN_PATH"]`, adds the `X-Nucleus-Tenant-ID` response header, and then calls `await call_next(request)`.

The response header is set unconditionally so callers can always verify which tenant brain was used — useful for debugging and for asserting correct routing in integration tests.

### Cloud Run app composition

`src/app.py` uses `starlette.routing.Mount` and `starlette.routing.Route` to compose:

- `GET /health` — liveness probe (returns `{"status": "ok"}`)
- `GET /ready` — readiness probe (returns `{"status": "ready"}` once the MCP app is initialized)
- `/` and `/mcp` — the tenant-wrapped fastmcp ASGI app

This structure means Cloud Run health checks work without going through the MCP protocol, which avoids spurious MCP errors in infrastructure logs.

### Container entrypoint modes

`deploy/entrypoint.sh` accepts a `MODE` environment variable:

- `sovereign` — runs stdio (default, no network exposure)
- `http` — runs `nucleus-mcp-http` (local HTTP)
- `cli` — drops to a shell for debugging

This means the same Docker image can be used for all three deployment styles without rebuilding.

### Verified behavior (sandbox)

The following were verified in a sandbox environment:

- MCP `initialize` over streamable-http returns HTTP 200 with correct `serverInfo`.
- `X-Nucleus-Tenant` response header is present on every response.
- Bearer token `acme-token` → `acme` brain directory created and used.
- Bearer token `globex-token` → `globex` brain directory created and used.
- No token → `default` brain directory used.
- All three brain directories are created and isolated — no cross-tenant bleed observed.

---

## How to Build On This

### Adding new routes to `app.py`

Add a `Route` or `Mount` to the `routes` list in `src/app.py`. Routes are matched in order, so add specific routes before the catch-all MCP mount. Example:

```python
Route("/metrics", endpoint=metrics_handler),
```

Health and readiness routes follow the same pattern — a plain async function that returns a `JSONResponse`.

### Adding new tenant resolution strategies

Edit `NucleusTenantMiddleware.resolve_tenant()` in `src/mcp_server_nucleus/http_transport/tenant.py`. The method receives the full `Request` object and returns a `str` tenant ID. Add new resolution logic before the `"default"` fallback. Resolution is sequential — return early as soon as a valid tenant is found.

Example: resolving from a JWT claim in the Authorization header rather than a static token map would be added here, replacing or augmenting the current bearer token lookup.

### Adding authentication providers

Authentication belongs in front of `NucleusTenantMiddleware`, not inside it. Options:

- **ASGI middleware layer**: Add an auth middleware (e.g., `starlette-authlib`, a custom `BaseHTTPMiddleware`) before `NucleusTenantMiddleware` in the middleware stack. Reject unauthenticated requests with HTTP 401 before tenant resolution runs.
- **API gateway**: Deploy Cloud Run behind GCP API Gateway or Kong. The gateway handles OAuth/API key validation; Nucleus receives only pre-authenticated requests with a trusted `X-Nucleus-Tenant-ID` header.
- **mTLS**: For service-to-service deployments, configure Cloud Run to require client certificates. Tenant identity can be derived from the certificate subject.

### Building per-tenant configuration

`NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain/` is the isolation boundary. Per-tenant configuration can be stored as files inside this directory. The middleware already resolves the path — tools can read `os.environ["NUCLEUS_BRAIN_PATH"]` and load a `config.json` from that directory to get tenant-specific settings (model preferences, rate limits, allowed tool sets, etc.).

### Moving away from `os.environ` mutation

The correct long-term fix for the `os.environ` concurrency issue is to thread the brain path through a context variable (`contextvars.ContextVar`) rather than a process-global env var. The middleware sets the context var; tools read it. This is safe under any concurrency model. The refactor is straightforward but requires updating every tool that reads `NUCLEUS_BRAIN_PATH` — plan it as a single atomic PR.

### Adding per-tenant audit logging

Audit logging should be added in `NucleusTenantMiddleware`, after `call_next(request)` returns. At that point you have the tenant ID, the request path and method, the response status, and the elapsed time. Emit a structured log line (JSON) for every MCP call. Ship logs to Cloud Logging, Datadog, or a SIEM via the container's stdout.

---

## Alternatives Considered

### A — Separate MCP instances per transport

Run two independent fastmcp instances, one for stdio and one for HTTP, each with their own tool registrations.

**Rejected.** Tool registration would have to be duplicated or abstracted into a shared module, creating a maintenance burden and risk of drift between transports. Using `mcp.http_app()` on the same instance gives HTTP for free.

### B — Flask instead of Starlette for the Cloud Run app

The original `src/app.py` was a Flask stub. Flask is synchronous and does not compose cleanly with ASGI middleware or async MCP tool handlers.

**Rejected.** Starlette is the natural host for a fastmcp ASGI app. It adds no meaningful complexity over Flask for this use case and eliminates the async/sync impedance mismatch.

### C — A shared multi-tenant brain with namespaced keys

Instead of per-tenant filesystem directories, use a single brain with tenant-prefixed keys (e.g., `acme::memory::foo`).

**Rejected.** Filesystem isolation is simpler, auditable (you can `ls` a tenant's brain), and requires no changes to tool logic. Namespaced keys require every tool to be aware of tenancy, leak tenant IDs into tool internals, and make it harder to migrate a tenant to their own instance later.

### D — Hardcode single-tenant HTTP (no tenant middleware)

Ship a simple HTTP server with no multi-tenant support; add tenancy later if needed.

**Rejected.** Adding tenancy after the fact requires breaking changes to the API surface and data layout. The middleware approach adds negligible complexity now and makes the solo case equally simple (no config = default tenant).

### E — Use a dedicated MCP gateway (e.g., a reverse proxy with MCP-awareness)

Route all transport concerns to an external component; keep Nucleus as stdio-only.

**Rejected.** This increases operational complexity substantially for no benefit at the current scale. Nucleus owning its transport layer keeps the deployment self-contained and gives contributors a single repository to reason about.
