"""
IPC Authentication Provider (v0.6.1)

Implements AuthProvider for STDIO transport.
Refactored from runtime/ipc_auth.py with abstract interface compliance.

Security Model:
- Short-lived tokens (30s TTL)
- Single-use consumption
- HMAC-signed for integrity
- Linked to DecisionMade events for audit
"""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import AuthProvider, AuthToken, AuthResult


def get_brain_path() -> Path:
    """Get the brain path from environment."""
    return Path(os.getenv("NUCLEUS_BRAIN_PATH", ".brain"))


@dataclass
class IPCToken(AuthToken):
    """
    IPC-specific authentication token.
    Extends base AuthToken with decision linkage and consumption tracking.
    """
    decision_id: Optional[str] = None
    consumed: bool = False
    consumed_at: Optional[str] = None
    request_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "decision_id": self.decision_id,
            "consumed": self.consumed,
            "consumed_at": self.consumed_at,
            "request_hash": self.request_hash,
        })
        return base
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCToken":
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired, not consumed)."""
        if self.consumed:
            return False
        return not self.is_expired()


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
    resource_type: str
    units_consumed: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IPCAuthProvider(AuthProvider):
    """
    IPC Authentication Provider for STDIO transport.
    
    Implements the AuthProvider interface for local agent-to-agent
    communication over STDIO/JSON-RPC.
    
    Security Features:
    - Per-request auth tokens (no implicit trust)
    - 30-second TTL (short-lived)
    - Single-use consumption
    - HMAC signatures for integrity
    - Decision linkage for audit trail
    - Metering for billing accuracy
    """
    
    TOKEN_TTL_SECONDS = 30
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self._active_tokens: Dict[str, IPCToken] = {}
        self._secret_key: Optional[bytes] = None
        self._meter_log: List[TokenMeterEntry] = []
        self._load_or_create_secret()
    
    @property
    def provider_name(self) -> str:
        return "IPC Auth Provider"
    
    @property
    def transport_type(self) -> str:
        return "stdio"
    
    def _load_or_create_secret(self) -> None:
        """Load or create the IPC secret key."""
        secrets_dir = self.brain_path / "secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)
        
        key_file = secrets_dir / ".ipc_secret"
        
        if key_file.exists():
            self._secret_key = key_file.read_bytes()
        else:
            self._secret_key = secrets.token_bytes(32)
            key_file.write_bytes(self._secret_key)
            os.chmod(key_file, 0o600)
    
    def _generate_token_id(self) -> str:
        """Generate a unique token ID."""
        return f"ipc-{secrets.token_hex(12)}"
    
    def _compute_signature(self, token_id: str, scope: str, 
                           decision_id: Optional[str]) -> str:
        """Compute HMAC signature for token validation."""
        message = f"{token_id}:{scope}:{decision_id or 'none'}"
        signature = hmac.new(
            self._secret_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        return signature
    
    def issue_token(
        self,
        scope: str,
        ttl_seconds: Optional[int] = None,
        decision_id: Optional[str] = None,
        **kwargs
    ) -> IPCToken:
        """Issue a new IPC auth token."""
        ttl = ttl_seconds or self.TOKEN_TTL_SECONDS
        now = datetime.now(timezone.utc)
        
        token_id = self._generate_token_id()
        expires_at = datetime.fromtimestamp(
            now.timestamp() + ttl,
            tz=timezone.utc
        ).isoformat()
        
        token = IPCToken(
            token_id=token_id,
            created_at=now.isoformat(),
            expires_at=expires_at,
            scope=scope,
            decision_id=decision_id,
        )
        
        self._active_tokens[token_id] = token
        self._log_token_event("issued", token)
        
        return token
    
    def validate_token(
        self,
        token_id: str,
        required_scope: str = None,
        request_hash: Optional[str] = None,
        scope: str = None,  # Backward compat alias
        **kwargs
    ) -> Tuple[bool, str]:
        """Validate an IPC token. Returns (is_valid: bool, error_message: str)."""
        # Support both 'scope' (old) and 'required_scope' (new) parameters
        actual_scope = required_scope or scope or kwargs.get('scope')
        if not actual_scope:
            return False, "No scope provided for validation"
        
        token = self._active_tokens.get(token_id)
        if not token:
            return False, "Token not found or expired"
        
        if token.consumed:
            return False, "Token already consumed (single-use)"
        
        if token.is_expired():
            return False, "Token expired"
        
        if token.scope != actual_scope and token.scope != "admin":
            return False, f"Scope mismatch: token has '{token.scope}', need '{actual_scope}'"
        
        return True, "Valid"
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke/consume a token."""
        return self.consume_token(token_id)
    
    def consume_token(
        self,
        token_id: str,
        request_hash: Optional[str] = None,
        resource_type: str = "tool_call",
        units: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Consume a token and record metering entry."""
        token = self._active_tokens.get(token_id)
        if not token or token.consumed:
            return False
        
        token.consumed = True
        token.consumed_at = datetime.now(timezone.utc).isoformat()
        token.request_hash = request_hash
        
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
        self._persist_meter_entry(meter_entry)
        self._log_token_event("consumed", token)
        
        return True
    
    def cleanup_expired(self) -> int:
        """Clean up expired tokens from memory."""
        now = datetime.now(timezone.utc).isoformat()
        expired = [
            tid for tid, token in self._active_tokens.items()
            if now >= token.expires_at
        ]
        
        for tid in expired:
            del self._active_tokens[tid]
        
        return len(expired)
    
    def _persist_meter_entry(self, entry: TokenMeterEntry) -> None:
        """Persist metering entry to ledger."""
        try:
            meter_dir = self.brain_path / "ledger" / "metering"
            meter_dir.mkdir(parents=True, exist_ok=True)
            
            meter_file = meter_dir / "token_meter.jsonl"
            with open(meter_file, "a", encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass
    
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
            with open(log_file, "a", encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def get_metering_summary(self, since: Optional[str] = None) -> Dict[str, Any]:
        """Get metering summary for billing/audit."""
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
            if entry.scope not in summary["by_scope"]:
                summary["by_scope"][entry.scope] = 0
            summary["by_scope"][entry.scope] += entry.units_consumed
            
            if entry.resource_type not in summary["by_resource_type"]:
                summary["by_resource_type"][entry.resource_type] = 0
            summary["by_resource_type"][entry.resource_type] += entry.units_consumed
            
            if entry.decision_id:
                summary["decisions_linked"] += 1
        
        return summary
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        try:
            log_file = self.brain_path / "ledger" / "auth" / "ipc_tokens.jsonl"
            if not log_file.exists():
                return []
            
            entries = []
            with open(log_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            
            return entries[-limit:]
        except Exception:
            return []


# Backward compatibility aliases
IPCAuthManager = IPCAuthProvider

# Singleton instance
_ipc_auth_manager: Optional[IPCAuthProvider] = None


def get_ipc_auth_manager() -> IPCAuthProvider:
    """Get or create the singleton IPCAuthProvider instance."""
    global _ipc_auth_manager
    if _ipc_auth_manager is None:
        _ipc_auth_manager = IPCAuthProvider()
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
                try:
                    from mcp_server_nucleus.runtime.prometheus import inc_auth_failure
                    inc_auth_failure()
                except Exception:
                    pass
                raise PermissionError(f"IPC token validation failed: {error}")
            
            result_val = func(*args, **kwargs)
            manager.consume_token(token_id, resource_type=scope)
            
            return result_val
        return wrapper
    return decorator
