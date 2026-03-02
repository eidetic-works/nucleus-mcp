"""
Nucleus Authentication Module (v1.1.1)

Multi-Transport Auth Architecture:
- STDIO transport: IPC tokens (production-ready)
- HTTP/SSE transport: JWT RS256 (Phase 2 - production-ready)
- OAuth 2.1 + PoP: Stubs for Phase 3 (Nucleus Cloud)

Design Decision: GO with OAuth-Ready Architecture
- See docs/AUTH_ARCHITECTURE.md for full rationale
"""

from .base import AuthProvider, AuthToken, AuthResult
from .ipc_provider import (
    IPCAuthProvider,
    IPCToken,
    TokenMeterEntry,
    get_ipc_auth_manager,
    require_ipc_token,
)
from .jwt_provider import JWTAuthProvider, JWTToken, SCOPES as JWT_SCOPES
from .auth_manager import get_auth_provider, AuthTransport, register_provider, clear_providers

__all__ = [
    # Base interfaces
    "AuthProvider",
    "AuthToken", 
    "AuthResult",
    # IPC Auth (STDIO transport)
    "IPCAuthProvider",
    "IPCToken",
    "TokenMeterEntry",
    "get_ipc_auth_manager",
    "require_ipc_token",
    # JWT Auth (HTTP/SSE transport)
    "JWTAuthProvider",
    "JWTToken",
    "JWT_SCOPES",
    # Auth Manager
    "get_auth_provider",
    "AuthTransport",
    "register_provider",
    "clear_providers",
]
