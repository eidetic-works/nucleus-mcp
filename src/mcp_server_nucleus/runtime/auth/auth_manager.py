"""
Auth Manager - Transport-Based Auth Router

Routes authentication requests to the appropriate provider
based on the transport type being used.

Transport Mapping:
- stdio -> IPCAuthProvider (current, production)
- http  -> OAuthProvider (Phase 3)
- sse   -> OAuthProvider (Phase 3)
"""

from enum import Enum
from typing import Optional

from .base import AuthProvider
from .ipc_provider import IPCAuthProvider
from .jwt_provider import JWTAuthProvider


class AuthTransport(Enum):
    """Supported transport types."""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


# Provider registry
_providers: dict = {}


def get_auth_provider(transport: AuthTransport = AuthTransport.STDIO) -> AuthProvider:
    """
    Get the appropriate auth provider for the given transport.
    
    Args:
        transport: The transport type (stdio, http, sse)
        
    Returns:
        AuthProvider instance for the transport
        
    Raises:
        NotImplementedError: If OAuth provider requested but not yet implemented
    """
    transport_key = transport.value if isinstance(transport, AuthTransport) else transport
    
    if transport_key in _providers:
        return _providers[transport_key]
    
    if transport_key == "stdio":
        provider = IPCAuthProvider()
        _providers[transport_key] = provider
        return provider
    
    elif transport_key in ("http", "sse"):
        # Phase 2: JWT authentication for HTTP/SSE transports
        provider = JWTAuthProvider()
        _providers[transport_key] = provider
        return provider
    
    else:
        raise ValueError(f"Unknown transport type: {transport_key}")


def register_provider(transport: str, provider: AuthProvider) -> None:
    """
    Register a custom auth provider for a transport.
    
    Useful for testing or custom implementations.
    
    Args:
        transport: Transport type string
        provider: AuthProvider instance
    """
    _providers[transport] = provider


def clear_providers() -> None:
    """Clear all registered providers. Useful for testing."""
    _providers.clear()
