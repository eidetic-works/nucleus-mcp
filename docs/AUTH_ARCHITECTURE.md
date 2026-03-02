# Nucleus Authentication Architecture

> **Decision**: GO with OAuth-Ready Architecture  
> **Date**: 2026-02-24  
> **Status**: Implemented (Phase 1)

## Executive Summary

Nucleus uses a **transport-based authentication model**:

| Transport | Auth Provider | Status |
|-----------|--------------|--------|
| STDIO | IPC Tokens | ✅ Production |
| HTTP/SSE | OAuth 2.1 | 📋 Phase 3 |

## Current Architecture (Phase 1-2)

### Transport: STDIO (JSON-RPC over stdin/stdout)

**Auth Provider**: `IPCAuthProvider`

**Security Model**:
- 30-second TTL tokens
- Single-use consumption
- HMAC-signed for integrity
- Linked to DecisionMade events
- Full audit trail in `.brain/ledger/auth/`

**Why This Works**:
- STDIO is process-bound (only parent process can communicate)
- No network exposure
- Implicit trust boundary at process level
- OAuth would be over-engineering for local IPC

### Module Structure

```
src/mcp_server_nucleus/runtime/auth/
├── __init__.py          # Public exports
├── base.py              # Abstract AuthProvider interface
├── ipc_provider.py      # IPC tokens for STDIO
├── oauth_provider.py    # OAuth 2.1 stub (Phase 3)
└── auth_manager.py      # Transport-based router
```

### Usage

```python
from mcp_server_nucleus.runtime.auth import (
    get_auth_provider,
    AuthTransport,
    require_ipc_token,
)

# Get provider for current transport
provider = get_auth_provider(AuthTransport.STDIO)

# Issue token
token = provider.issue_token(scope="tool_call", decision_id="dec-abc123")

# Validate token
result, error = provider.validate_token(token.token_id, "tool_call")

# Decorator for protected functions
@require_ipc_token("tool_call")
def sensitive_operation(token_id: str, ...):
    ...
```

## Future Architecture (Phase 3 - Nucleus Cloud)

### Transport: HTTP/SSE

**Auth Provider**: `OAuthProvider`

**MCP Specification Requirements**:
1. Implement RFC9728 (Protected Resource Metadata)
2. Expose `/.well-known/oauth-protected-resource`
3. Return 401 with `WWW-Authenticate` for unauthorized requests
4. Support Bearer tokens with DPoP

### Implementation Checklist

```
[ ] Add HTTP/SSE server endpoint
[ ] Implement Protected Resource Metadata
[ ] Integrate with authorization server
[ ] Token validation with introspection
[ ] DPoP (Proof-of-Possession)
[ ] Scope enforcement
[ ] Token refresh handling
[ ] Audit logging integration
```

### Protected Resource Metadata Example

```json
{
  "resource": "https://nucleus.example.com/mcp",
  "authorization_servers": ["https://auth.example.com"],
  "scopes_supported": ["mcp:tools", "mcp:resources", "mcp:prompts"],
  "bearer_methods_supported": ["header"],
  "resource_signing_alg_values_supported": ["RS256", "ES256"]
}
```

### Authorization Flow

```
1. Client connects to Nucleus HTTP endpoint
2. Nucleus returns 401 with PRM location
3. Client fetches Protected Resource Metadata
4. Client discovers authorization server
5. Client registers (DCR) or uses pre-registration
6. User authorizes via browser
7. Client exchanges code for tokens
8. Client includes Bearer token in MCP requests
9. Nucleus validates token and processes request
```

## Design Decision Rationale

### Why Not Full OAuth Now?

1. **80% of users don't need it** - Solo founders, vibe coders use STDIO
2. **MCP spec only requires OAuth for HTTP/SSE** - STDIO is exempt
3. **Phase 3 is months away** - YAGNI principle
4. **Current IPC auth is sufficient** - Addresses all current threats

### Why OAuth-Ready Architecture?

1. **Phase 3 planning** - "Nucleus Cloud" will need OAuth
2. **Clean abstraction** - Transport-agnostic auth interface
3. **Minimal cost** - Just architecture, not full implementation
4. **Industry alignment** - OAuth 2.1 is the 2026 standard

## Threat Model Comparison

| Threat | STDIO + IPC | HTTP + OAuth |
|--------|-------------|--------------|
| Process hijacking | ✅ IPC tokens | ✅ OAuth tokens |
| Network sniffing | N/A (no network) | ✅ TLS + DPoP |
| Token theft | ✅ 30s TTL | ✅ Short-lived + refresh |
| Replay attacks | ✅ Single-use | ✅ DPoP nonce |
| Audit trail | ✅ Decision linkage | ✅ OAuth logs |

## Migration Path

When Phase 3 arrives:

1. Implement `OAuthProvider` fully
2. Add HTTP/SSE server with auth middleware
3. Deploy authorization server (Keycloak/Auth0)
4. Update documentation
5. Both transports coexist (user chooses)

## References

- [MCP Authorization Spec](https://modelcontextprotocol.io/specification/draft/basic/authorization)
- [RFC9728 - Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13)
- [DPoP Spec](https://datatracker.ietf.org/doc/html/rfc9449)
