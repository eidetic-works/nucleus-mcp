# Contributing to Nucleus

Thank you for your interest in contributing to Nucleus - The Universal Brain for AI Agents.

## We're Open Source! 🎉

Nucleus is fully open source under the MIT license. We welcome contributions of all kinds:

- ✅ **Bug Reports**: Via GitHub Issues
- ✅ **Feature Requests**: Via GitHub Discussions  
- ✅ **Code Contributions**: Via Pull Requests
- ✅ **Documentation**: Improvements always welcome
- ✅ **Integrations**: Add support for new AI tools

## How to Contribute

### 1. Bug Reports

Found a bug? Please open a GitHub Issue with:

- **Environment**: Python version, OS, MCP client
- **Steps to Reproduce**: Minimal example
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Relevant error messages (sanitize sensitive data)

### 2. Feature Requests

Have an idea? Open a GitHub Discussion with:

- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How would you implement it?
- **Alternatives Considered**: What else did you consider?
- **Use Cases**: Who benefits from this?

### 3. Documentation

Documentation improvements are always welcome:

- Typo fixes
- Clarification of existing docs
- New examples or tutorials
- Translations

Submit a Pull Request to the `docs/` directory.

### 4. Beta Testing

We're looking for beta testers to validate new features:

- Test pre-release versions
- Provide feedback on UX
- Report edge cases
- Suggest improvements

Contact us to join the beta program.

## Code of Conduct

### Be Respectful
- Treat everyone with respect
- No harassment, discrimination, or personal attacks
- Assume good intent

### Be Constructive
- Provide actionable feedback
- Focus on the problem, not the person
- Celebrate successes

### Be Patient
- Maintainers are volunteers
- Response times may vary
- Quality over speed

## Code Contributions

### Good First Issues

Look for issues labeled `good-first-issue` - these are ideal for new contributors:
- Documentation improvements
- Small bug fixes
- Test coverage additions
- New integration examples

### Development Setup

```bash
# Clone the repo
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd mcp-server-nucleus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/`)
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

### PR Review Criteria

- [ ] Tests pass
- [ ] Code follows existing style
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

## Enterprise Inquiries

For enterprise licensing or partnership inquiries:
- Email: partnerships@nucleusos.dev

## Security Vulnerabilities

**Do NOT report security vulnerabilities via public GitHub Issues.**

Instead, email: security@nucleusos.dev

Include:
- Detailed description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes

We follow responsible disclosure and will credit researchers who report valid vulnerabilities.

## License

By contributing to Nucleus, you agree that your contributions will be licensed under the project's license terms.

## Questions?

- **General Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Partnership**: hello@nucleusos.dev
- **Security**: hello@nucleusos.dev

---

*Thank you for helping make Nucleus better!*

*— The Nucleus Team*

---

## Building on the HTTP Transport Layer

Added in v1.9.0 ("Sovereign Network"). This section documents how the HTTP transport layer works, how to extend it, and the invariants you must preserve when contributing to it.

### Architecture overview

```
stdio (existing)
   │
   ├── nucleus-mcp              ← unchanged, always works
   │
HTTP transport (new)
   │
   ├── http_transport/
   │   ├── tenant.py            ← tenant resolution + brain isolation
   │   ├── server.py            ← Option 1: nucleus-mcp-http CLI
   │   └── __init__.py
   │
   ├── src/app.py               ← Option 2: Cloud Run ASGI app
   └── deploy/entrypoint.sh     ← container entrypoint
```

The same `mcp` instance (from `mcp_server_nucleus/__init__.py`) is shared between stdio and HTTP. No tool registration happens twice — `mcp.http_app()` wraps the already-registered tools.

### Deployment modes

Three modes, configured entirely via env vars — no code changes needed:

| Mode | Config | Behavior |
|---|---|---|
| Solo | (none) | Default tenant, no auth required. Backward-compatible. |
| Single-tenant | `NUCLEUS_TENANT_ID=<slug>` | Fixed tenant identity, no token required. |
| Multi-tenant | `NUCLEUS_TENANT_MAP={"token": "tenant_id"}` + `NUCLEUS_REQUIRE_AUTH=true` | Token → tenant mapping, auth enforced. |

### How to add a new HTTP route to app.py

Example — adding a `/metrics` endpoint:

```python
# In src/app.py, add to routes:
async def metrics(request: Request):
    from mcp_server_nucleus.runtime.telemetry_ops import get_metrics
    return JSONResponse(get_metrics())

# Add to Starlette routes:
Route("/metrics", metrics),
```

The existing routes are `/health`, `/ready`, `/identity`, and `/mcp`. Any new route should be stateless with respect to tenant identity — if it needs tenant context, resolve it via `NucleusTenantMiddleware` the same way `/mcp` does.

### How to extend tenant resolution

Tenant resolution lives in `http_transport/tenant.py` → `resolve_tenant()`.

To add a new resolution strategy (e.g. JWT, API key header, database lookup):

```python
def resolve_tenant(request: Request) -> Optional[str]:
    # Add your strategy here — first match wins

    # Example: JWT claim
    token = extract_jwt(request.headers.get("Authorization", ""))
    if token:
        return token.get("nucleus_tenant")

    # ... existing strategies below
```

The contract: return a `tenant_id` string (used as directory name) or `None` if unauthenticated. The caller handles `None` — either rejecting the request (when `NUCLEUS_REQUIRE_AUTH=true`) or falling back to the default tenant.

Resolution priority (current):
1. Bearer token → `NUCLEUS_TENANT_MAP` lookup
2. `X-Nucleus-Tenant-ID` header
3. `NUCLEUS_TENANT_ID` env var
4. Default tenant (solo mode)

New strategies should be inserted above the default fallback and should fail fast (no blocking I/O in the hot path unless cached).

### How to add per-tenant configuration

Each tenant's brain is at `NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain`. To add per-tenant config:

```python
from mcp_server_nucleus.http_transport.tenant import brain_path_for_tenant

brain = brain_path_for_tenant(tenant_id)
config_path = brain / "config" / "nucleus.json"
```

`brain_path_for_tenant()` creates the directory structure if it doesn't exist. All runtime ops read brain path from `os.environ["NUCLEUS_BRAIN_PATH"]`, which `NucleusTenantMiddleware` sets per-request before dispatching to the MCP handler.

### How to add auth providers

`NucleusTenantMiddleware` in `tenant.py` is the right place. Current auth is token→map. To add OAuth, SAML, or API key auth:

1. Add resolution logic to `resolve_tenant()`
2. Add the provider's token validation as a helper function in the same file
3. Keep the fallback chain intact — solo mode (no auth) must always work

Do not add auth logic inside individual tools or runtime ops. Tenant isolation is middleware-only by design.

### Transport: streamable-http vs SSE

- `streamable-http` (default) — MCP spec compliant, bidirectional, recommended for all new clients
- `sse` — legacy, for clients that don't support streamable-http yet

Configure via:
- `NUCLEUS_HTTP_TRANSPORT` — for `nucleus-mcp-http` (Option 1 / local server)
- `NUCLEUS_TRANSPORT` — for `nucleus-mcp-cloud` / `src/app.py` (Option 2 / Cloud Run)

Valid values for both: `streamable-http` or `sse`. Default is `streamable-http`.

### Testing HTTP transport locally

```bash
# Install with HTTP extras
pip install -e ".[full,http]"

# Start local HTTP server
nucleus-mcp-http

# Test MCP initialize
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test multi-tenant
NUCLEUS_TENANT_MAP='{"tok-test":"my-org"}' nucleus-mcp-http &
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Authorization: Bearer tok-test" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '...'
# Response header will contain: X-Nucleus-Tenant: my-org
```

To test the Cloud Run variant locally:

```bash
PORT=8080 nucleus-mcp-cloud

# Health check
curl http://localhost:8080/health

# Identity
curl http://localhost:8080/identity
```

### Design principles to preserve

These invariants apply to all contributions touching the transport layer:

1. **stdio must always work unchanged** — HTTP transport is additive, never breaking. The `nucleus-mcp` entrypoint and all stdio behavior must be regression-free regardless of what HTTP code is added.

2. **Tenant isolation is in the middleware, not in tools** — Tools are tenant-unaware by design. They read `NUCLEUS_BRAIN_PATH` from the environment and nothing else. Tenant context must never leak into tool registration or runtime op logic.

3. **Same mcp instance** — Don't register tools twice or create a second `FastMCP` instance. `mcp.http_app()` wraps the instance that already has all tools registered via the existing `__init__.py` import chain.

4. **Brain path injection via env** — `os.environ["NUCLEUS_BRAIN_PATH"]` is the contract that all runtime ops respect. The middleware sets this before dispatching; tools read it. This is the only cross-cutting mechanism for tenant context.

5. **Solo mode must work with zero config** — No env vars required, no auth, no tenant map. `nucleus-mcp-http` with no configuration must start and serve requests for the default tenant.
