"""
Abstract Auth Provider Interface

This module defines the contract that all auth providers must implement.
Enables transport-agnostic authentication for Nucleus.

Transport Types:
- STDIO: Uses IPC tokens (IPCAuthProvider)
- HTTP/SSE: Uses OAuth 2.1 (OAuthProvider - Phase 3)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AuthResult(Enum):
    """Result of authentication attempt."""
    SUCCESS = "success"
    INVALID_TOKEN = "invalid_token"
    EXPIRED = "expired"
    SCOPE_MISMATCH = "scope_mismatch"
    CONSUMED = "already_consumed"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"


@dataclass
class AuthToken:
    """
    Base authentication token.
    All auth providers must produce tokens conforming to this interface.
    """
    token_id: str
    created_at: str
    expires_at: str
    scope: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        now = datetime.now(timezone.utc).isoformat()
        return now >= self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize token to dictionary."""
        return {
            "token_id": self.token_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "metadata": self.metadata,
        }


class AuthProvider(ABC):
    """
    Abstract base class for authentication providers.
    
    Implementations:
    - IPCAuthProvider: For STDIO transport (local agent-to-agent)
    - OAuthProvider: For HTTP/SSE transport (Phase 3 - Nucleus Cloud)
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass
    
    @property
    @abstractmethod
    def transport_type(self) -> str:
        """Transport type this provider handles (stdio, http, sse)."""
        pass
    
    @abstractmethod
    def issue_token(
        self,
        scope: str,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> AuthToken:
        """
        Issue a new authentication token.
        
        Args:
            scope: Authorization scope for the token
            ttl_seconds: Time-to-live in seconds
            **kwargs: Provider-specific parameters
            
        Returns:
            New AuthToken instance
        """
        pass
    
    @abstractmethod
    def validate_token(
        self,
        token_id: str,
        required_scope: str = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Validate an authentication token.
        
        Args:
            token_id: Token to validate
            required_scope: Scope required for the operation
            **kwargs: Provider-specific parameters (e.g., 'scope' for backward compat)
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        pass
    
    @abstractmethod
    def revoke_token(self, token_id: str) -> bool:
        """
        Revoke/consume a token.
        
        Args:
            token_id: Token to revoke
            
        Returns:
            True if successfully revoked
        """
        pass
    
    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        pass
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit log entries.
        
        Args:
            limit: Maximum entries to return
            
        Returns:
            List of audit log entries
        """
        return []  # Default: no audit log
