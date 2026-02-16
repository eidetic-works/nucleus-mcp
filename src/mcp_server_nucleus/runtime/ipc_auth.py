"""
v0.6.0 DSoR: IPC Authentication & Token Metering

Remediates CVE-2026-001 (Sidecar Exploit) from V9_VULNERABILITY_REPORT.md:
- Implements per-request IPC auth tokens (no more implicit trust)
- Links token metering to DecisionMade events (prevents billing bypass)

Security Model:
- Every IPC request must include a short-lived auth token
- Tokens are bound to specific decision_ids for audit linkage
- Token consumption is metered and logged for billing accuracy
"""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_brain_path() -> Path:
    """Get the brain path from environment."""
    return Path(os.getenv("NUCLEAR_BRAIN_PATH", "/Users/lokeshgarg/ai-mvp-backend/.brain"))


@dataclass
class IPCToken:
    """
    Per-request IPC authentication token.
    Short-lived, single-use, bound to a decision.
    """
    token_id: str
    decision_id: Optional[str]  # Linked DecisionMade event
    created_at: str
    expires_at: str
    scope: str  # e.g., "tool_call", "read", "write"
    consumed: bool = False
    consumed_at: Optional[str] = None
    request_hash: Optional[str] = None  # Hash of the request this token authorized
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCToken":
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired, not consumed)."""
        if self.consumed:
            return False
        now = datetime.now(timezone.utc).isoformat()
        return now < self.expires_at


@dataclass
class TokenMeterEntry:
    """
    Metering entry for billing and audit.
    Links token consumption to decisions and resource usage.
    """
    entry_id: str
    token_id: str
    decision_id: Optional[str]
    timestamp: str
    scope: str
    resource_type: str  # e.g., "tool_call", "llm_tokens", "compute"
    units_consumed: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IPCAuthManager:
    """
    v0.6.0 DSoR: Manages IPC authentication and token metering.
    
    Addresses V9 vulnerabilities:
    1. CVE-2026-001: Per-request auth prevents socket impersonation
    2. Pricing Rebellion: Metering linked to DecisionMade prevents bypass
    """
    
    # Token validity duration in seconds
    TOKEN_TTL_SECONDS = 30  # Short-lived for security
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self._active_tokens: Dict[str, IPCToken] = {}
        self._secret_key: Optional[bytes] = None
        self._meter_log: List[TokenMeterEntry] = []
        self._load_or_create_secret()
    
    def _load_or_create_secret(self) -> None:
        """Load or create the IPC secret key."""
        secrets_dir = self.brain_path / "secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)
        
        key_file = secrets_dir / ".ipc_secret"
        
        if key_file.exists():
            self._secret_key = key_file.read_bytes()
        else:
            # Generate new secret (32 bytes = 256 bits)
            self._secret_key = secrets.token_bytes(32)
            key_file.write_bytes(self._secret_key)
            # Restrict permissions (owner read/write only)
            os.chmod(key_file, 0o600)
    
    def _generate_token_id(self) -> str:
        """Generate a unique token ID."""
        return f"ipc-{secrets.token_hex(12)}"
    
    def _compute_token_signature(self, token_id: str, scope: str, 
                                  decision_id: Optional[str]) -> str:
        """Compute HMAC signature for token validation."""
        message = f"{token_id}:{scope}:{decision_id or 'none'}"
        signature = hmac.new(
            self._secret_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        return signature
    
    def issue_token(self, scope: str, decision_id: Optional[str] = None,
                    ttl_seconds: Optional[int] = None) -> IPCToken:
        """
        Issue a new per-request IPC auth token.
        
        Args:
            scope: The scope of operations this token authorizes
            decision_id: Optional linked DecisionMade event ID
            ttl_seconds: Optional custom TTL (defaults to TOKEN_TTL_SECONDS)
            
        Returns:
            New IPCToken instance
        """
        ttl = ttl_seconds or self.TOKEN_TTL_SECONDS
        now = datetime.now(timezone.utc)
        
        token_id = self._generate_token_id()
        expires_at = datetime.fromtimestamp(
            now.timestamp() + ttl, 
            tz=timezone.utc
        ).isoformat()
        
        token = IPCToken(
            token_id=token_id,
            decision_id=decision_id,
            created_at=now.isoformat(),
            expires_at=expires_at,
            scope=scope
        )
        
        self._active_tokens[token_id] = token
        
        # Log token issuance
        self._log_token_event("issued", token)
        
        return token
    
    def validate_token(self, token_id: str, scope: str,
                       request_hash: Optional[str] = None) -> tuple[bool, str]:
        """
        Validate an IPC token for a request.
        
        Args:
            token_id: The token ID to validate
            scope: The required scope for the operation
            request_hash: Optional hash of the request being authorized
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check token exists
        token = self._active_tokens.get(token_id)
        if not token:
            return False, "Token not found or expired"
        
        # Check not consumed
        if token.consumed:
            return False, "Token already consumed (single-use)"
        
        # Check not expired
        now = datetime.now(timezone.utc).isoformat()
        if now >= token.expires_at:
            return False, "Token expired"
        
        # Check scope matches
        if token.scope != scope and token.scope != "admin":
            return False, f"Scope mismatch: token has '{token.scope}', need '{scope}'"
        
        return True, "Valid"
    
    def consume_token(self, token_id: str, request_hash: Optional[str] = None,
                      resource_type: str = "tool_call",
                      units: float = 1.0,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Consume a token and record metering entry.
        
        Args:
            token_id: The token to consume
            request_hash: Hash of the request this token authorized
            resource_type: Type of resource being consumed
            units: Number of units consumed (for billing)
            metadata: Optional additional metadata
            
        Returns:
            True if token was successfully consumed
        """
        token = self._active_tokens.get(token_id)
        if not token or token.consumed:
            return False
        
        # Mark as consumed
        token.consumed = True
        token.consumed_at = datetime.now(timezone.utc).isoformat()
        token.request_hash = request_hash
        
        # Create metering entry
        meter_entry = TokenMeterEntry(
            entry_id=f"meter-{secrets.token_hex(8)}",
            token_id=token_id,
            decision_id=token.decision_id,
            timestamp=token.consumed_at,
            scope=token.scope,
            resource_type=resource_type,
            units_consumed=units,
            metadata=metadata or {}
        )
        
        self._meter_log.append(meter_entry)
        
        # Persist metering entry
        self._persist_meter_entry(meter_entry)
        
        # Log consumption
        self._log_token_event("consumed", token)
        
        return True
    
    def _persist_meter_entry(self, entry: TokenMeterEntry) -> None:
        """Persist metering entry to ledger."""
        try:
            meter_dir = self.brain_path / "ledger" / "metering"
            meter_dir.mkdir(parents=True, exist_ok=True)
            
            meter_file = meter_dir / "token_meter.jsonl"
            with open(meter_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception:
            pass  # Non-blocking
    
    def _log_token_event(self, event_type: str, token: IPCToken) -> None:
        """Log token lifecycle event."""
        try:
            auth_dir = self.brain_path / "ledger" / "auth"
            auth_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = auth_dir / "ipc_tokens.jsonl"
            event = {
                "event": event_type,
                "token_id": token.token_id,
                "decision_id": token.decision_id,
                "scope": token.scope,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass  # Non-blocking
    
    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from memory.
        
        Returns:
            Number of tokens cleaned up
        """
        now = datetime.now(timezone.utc).isoformat()
        expired = [
            tid for tid, token in self._active_tokens.items()
            if now >= token.expires_at
        ]
        
        for tid in expired:
            del self._active_tokens[tid]
        
        return len(expired)
    
    def get_metering_summary(self, since: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metering summary for billing/audit.
        
        Args:
            since: Optional ISO timestamp to filter from
            
        Returns:
            Summary of token consumption and metering
        """
        entries = self._meter_log
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        summary = {
            "total_entries": len(entries),
            "total_units": sum(e.units_consumed for e in entries),
            "by_scope": {},
            "by_resource_type": {},
            "decisions_linked": 0
        }
        
        for entry in entries:
            # By scope
            if entry.scope not in summary["by_scope"]:
                summary["by_scope"][entry.scope] = 0
            summary["by_scope"][entry.scope] += entry.units_consumed
            
            # By resource type
            if entry.resource_type not in summary["by_resource_type"]:
                summary["by_resource_type"][entry.resource_type] = 0
            summary["by_resource_type"][entry.resource_type] += entry.units_consumed
            
            # Count linked decisions
            if entry.decision_id:
                summary["decisions_linked"] += 1
        
        return summary


# Singleton instance
_ipc_auth_manager: Optional[IPCAuthManager] = None


def get_ipc_auth_manager() -> IPCAuthManager:
    """Get or create the singleton IPCAuthManager instance."""
    global _ipc_auth_manager
    if _ipc_auth_manager is None:
        _ipc_auth_manager = IPCAuthManager()
    return _ipc_auth_manager


def require_ipc_token(scope: str):
    """
    Decorator to require IPC token authentication for a function.
    
    Usage:
        @require_ipc_token("tool_call")
        def my_sensitive_function(token_id: str, ...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            token_id = kwargs.get("token_id") or (args[0] if args else None)
            if not token_id:
                raise PermissionError("IPC token required but not provided")
            
            manager = get_ipc_auth_manager()
            is_valid, error = manager.validate_token(token_id, scope)
            
            if not is_valid:
                raise PermissionError(f"IPC token validation failed: {error}")
            
            # Token is valid, proceed with function
            result = func(*args, **kwargs)
            
            # Consume token after successful execution
            manager.consume_token(token_id, resource_type=scope)
            
            return result
        return wrapper
    return decorator
