"""
OAuth 2.1 Authentication Provider (Phase 3 Stub)

This module will implement OAuth 2.1 + PoP for HTTP/SSE transports
when Nucleus Cloud is built in Phase 3.

MCP Specification Requirements (RFC9728):
- Implement OAuth 2.0 Protected Resource Metadata
- Expose .well-known/oauth-protected-resource endpoint
- Support authorization server discovery
- Implement Dynamic Client Registration (RFC7591)
- Use DPoP for Proof-of-Possession tokens

Reference Implementation Guide:
- https://modelcontextprotocol.io/specification/draft/basic/authorization
- https://datatracker.ietf.org/doc/html/rfc9728
- https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13

Design Decision: GO with OAuth-Ready Architecture
- Rationale: 80% of users don't need OAuth (STDIO transport)
- Full implementation deferred until Phase 3 (Nucleus Cloud)
- See docs/AUTH_ARCHITECTURE.md for full analysis
"""

from typing import Any, Dict, List, Optional, Tuple

from .base import AuthProvider, AuthToken, AuthResult


class OAuthProvider(AuthProvider):
    """
    OAuth 2.1 + PoP Provider for HTTP/SSE transports.
    
    STATUS: STUB - Full implementation in Phase 3
    
    When implemented, this provider will:
    1. Serve Protected Resource Metadata at /.well-known/oauth-protected-resource
    2. Integrate with authorization servers (Keycloak, Auth0, etc.)
    3. Validate Bearer tokens with DPoP binding
    4. Support scope-based authorization
    5. Implement token introspection for validation
    
    Phase 3 Implementation Checklist:
    [ ] Protected Resource Metadata endpoint
    [ ] Authorization server integration
    [ ] Token validation with introspection
    [ ] DPoP (Demonstrating Proof-of-Possession)
    [ ] Scope enforcement
    [ ] Token refresh handling
    [ ] Audit logging
    """
    
    def __init__(
        self,
        resource_url: Optional[str] = None,
        authorization_servers: Optional[List[str]] = None,
        supported_scopes: Optional[List[str]] = None,
    ):
        """
        Initialize OAuth provider.
        
        Args:
            resource_url: The protected resource URL (e.g., https://nucleus.example.com/mcp)
            authorization_servers: List of authorization server URLs
            supported_scopes: List of supported OAuth scopes
        """
        raise NotImplementedError(
            "OAuthProvider is not yet implemented. "
            "OAuth 2.1 support will be added in Phase 3 (Nucleus Cloud). "
            "Current transport (HTTP/SSE) requires OAuth per MCP spec. "
            "For local development, use STDIO transport with IPCAuthProvider. "
            "See docs/AUTH_ARCHITECTURE.md for implementation roadmap."
        )
    
    @property
    def provider_name(self) -> str:
        return "OAuth 2.1 Provider"
    
    @property
    def transport_type(self) -> str:
        return "http"
    
    def issue_token(
        self,
        scope: str,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> AuthToken:
        """
        OAuth tokens are issued by the authorization server, not the resource server.
        This method would return a reference to request tokens from the auth server.
        """
        raise NotImplementedError("OAuth tokens are issued by authorization server")
    
    def validate_token(
        self,
        token_id: str,
        required_scope: str,
        **kwargs
    ) -> Tuple[AuthResult, str]:
        """
        Validate an OAuth access token.
        
        Implementation will:
        1. Check token signature (if JWT)
        2. Verify DPoP binding
        3. Check expiration
        4. Verify scope
        5. Optionally introspect with auth server
        """
        raise NotImplementedError("OAuth validation not yet implemented")
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke token via authorization server."""
        raise NotImplementedError("OAuth revocation not yet implemented")
    
    def cleanup_expired(self) -> int:
        """OAuth tokens are managed by authorization server."""
        return 0
    
    def get_protected_resource_metadata(self) -> Dict[str, Any]:
        """
        Generate Protected Resource Metadata per RFC9728.
        
        This will be served at /.well-known/oauth-protected-resource
        
        Example response:
        {
            "resource": "https://nucleus.example.com/mcp",
            "authorization_servers": ["https://auth.example.com"],
            "scopes_supported": ["mcp:tools", "mcp:resources", "mcp:prompts"],
            "bearer_methods_supported": ["header"],
            "resource_signing_alg_values_supported": ["RS256", "ES256"]
        }
        """
        raise NotImplementedError("Protected Resource Metadata not yet implemented")


# Phase 3 Implementation Notes:
#
# 1. HTTP Server Setup:
#    - Add /.well-known/oauth-protected-resource endpoint
#    - Return 401 with WWW-Authenticate header for unauthorized requests
#    - Support Bearer token authentication
#
# 2. Authorization Flow:
#    - Client discovers PRM at well-known URL
#    - Client fetches auth server metadata
#    - Client registers dynamically (if DCR supported)
#    - User authorizes via browser
#    - Client exchanges code for tokens
#    - Client includes access token in MCP requests
#
# 3. Token Validation:
#    - Parse Bearer token from Authorization header
#    - Verify JWT signature (if JWT)
#    - Check DPoP proof binding
#    - Verify scope includes required permissions
#    - Check expiration
#    - Optionally introspect with auth server
#
# 4. Integration Options:
#    - Keycloak (self-hosted, enterprise)
#    - Auth0 (managed, quick setup)
#    - AWS Cognito (AWS ecosystem)
#    - Custom authorization server
