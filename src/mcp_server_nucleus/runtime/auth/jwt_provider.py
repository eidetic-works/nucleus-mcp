"""
JWT Authentication Provider (Phase 2)

Implements AuthProvider for HTTP/SSE transports using RS256 JWTs.
Designed for "Nucleus Cloud" readiness while maintaining zero-friction
for local STDIO users (who never touch this code path).

Security Model:
- RS256 asymmetric signing (private key stays on server)
- Short-lived access tokens (15min default)
- Refresh token rotation with family tracking
- Scope-based authorization (mcp:tools, mcp:resources, mcp:prompts, admin)
- Token revocation via deny-list
- DPoP stub for Phase 3 Proof-of-Possession

MCP Specification Alignment (RFC9728):
- Protected Resource Metadata generation
- Bearer token validation
- Scope enforcement per MCP operation type

Author: Nucleus Team
"""

import base64
import hashlib
import json
import os
import secrets
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from .base import AuthProvider, AuthToken, AuthResult


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_ACCESS_TTL = int(os.environ.get("NUCLEUS_JWT_ACCESS_TTL", "900"))  # 15 min
DEFAULT_REFRESH_TTL = int(os.environ.get("NUCLEUS_JWT_REFRESH_TTL", "86400"))  # 24h
JWT_ISSUER = os.environ.get("NUCLEUS_JWT_ISSUER", "nucleus-mcp")
JWT_AUDIENCE = os.environ.get("NUCLEUS_JWT_AUDIENCE", "nucleus-mcp-client")

# Supported scopes
SCOPES = {
    "mcp:tools": "Execute MCP tools",
    "mcp:resources": "Read MCP resources",
    "mcp:prompts": "Access MCP prompts",
    "mcp:admin": "Administrative operations",
}


# ============================================================
# HELPERS: Minimal JWT (no PyJWT dependency)
# ============================================================

def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64url decode with padding restoration."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _json_b64(obj: dict) -> str:
    """JSON-encode then base64url-encode."""
    return _b64url_encode(json.dumps(obj, separators=(",", ":")).encode("utf-8"))


def _create_jwt(payload: dict, private_key) -> str:
    """Create an RS256-signed JWT from payload dict."""
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = _json_b64(header)
    payload_b64 = _json_b64(payload)

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _verify_jwt(token: str, public_key) -> Tuple[bool, dict, str]:
    """
    Verify an RS256 JWT and return (valid, payload, error_msg).

    Returns:
        Tuple of (is_valid, decoded_payload_or_empty, error_message)
    """
    parts = token.split(".")
    if len(parts) != 3:
        return False, {}, "Malformed JWT: expected 3 parts"

    header_b64, payload_b64, sig_b64 = parts

    # Verify header
    try:
        header = json.loads(_b64url_decode(header_b64))
    except Exception:
        return False, {}, "Invalid JWT header"

    if header.get("alg") != "RS256":
        return False, {}, f"Unsupported algorithm: {header.get('alg')}"

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        signature = _b64url_decode(sig_b64)
        public_key.verify(
            signature,
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception:
        return False, {}, "Invalid JWT signature"

    # Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return False, {}, "Invalid JWT payload"

    # Check expiration
    now = int(time.time())
    if payload.get("exp", 0) < now:
        return False, payload, "Token expired"

    # Check not-before
    if payload.get("nbf", 0) > now:
        return False, payload, "Token not yet valid"

    return True, payload, ""


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class JWTToken(AuthToken):
    """JWT-specific token with refresh and family tracking."""
    jwt_string: str = ""
    refresh_token: Optional[str] = None
    refresh_family: Optional[str] = None
    subject: Optional[str] = None
    revoked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "subject": self.subject,
            "refresh_family": self.refresh_family,
            "has_refresh": self.refresh_token is not None,
            "revoked": self.revoked,
        })
        return base


@dataclass
class RefreshRecord:
    """Tracks a refresh token for rotation detection."""
    family_id: str
    token_hash: str
    subject: str
    scope: str
    issued_at: float
    expires_at: float
    used: bool = False
    revoked: bool = False


# ============================================================
# JWT AUTH PROVIDER
# ============================================================

class JWTAuthProvider(AuthProvider):
    """
    JWT Authentication Provider for HTTP/SSE transports.

    Features:
    - RS256 asymmetric signing (auto-generates keypair on first use)
    - Access tokens (short-lived, 15min default)
    - Refresh tokens with rotation + family tracking
    - Scope enforcement
    - Token deny-list for revocation
    - Audit logging
    - Thread-safe operations
    """

    def __init__(
        self,
        brain_path: Optional[Path] = None,
        access_ttl: int = DEFAULT_ACCESS_TTL,
        refresh_ttl: int = DEFAULT_REFRESH_TTL,
        issuer: str = JWT_ISSUER,
        audience: str = JWT_AUDIENCE,
    ):
        self._brain_path = brain_path or Path(
            os.getenv("NUCLEAR_BRAIN_PATH", ".brain")
        )
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer
        self._audience = audience

        self._lock = threading.Lock()

        # Key material
        self._private_key = None
        self._public_key = None

        # Token state
        self._deny_list: set = set()  # revoked token jti values
        self._refresh_records: Dict[str, RefreshRecord] = {}  # hash -> record
        self._revoked_families: set = set()  # entire family revocations

        # Metrics
        self._metrics = {
            "tokens_issued": 0,
            "tokens_validated": 0,
            "tokens_rejected": 0,
            "tokens_refreshed": 0,
            "tokens_revoked": 0,
        }

        # Initialize keys
        self._load_or_create_keys()

    @property
    def provider_name(self) -> str:
        return "JWT Auth Provider"

    @property
    def transport_type(self) -> str:
        return "http"

    # ============================================================
    # KEY MANAGEMENT
    # ============================================================

    def _keys_dir(self) -> Path:
        d = self._brain_path / "secrets" / "jwt"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load_or_create_keys(self) -> None:
        """Load existing RSA keypair or generate a new one."""
        priv_path = self._keys_dir() / "private.pem"
        pub_path = self._keys_dir() / "public.pem"

        if priv_path.exists() and pub_path.exists():
            self._private_key = serialization.load_pem_private_key(
                priv_path.read_bytes(), password=None
            )
            self._public_key = serialization.load_pem_public_key(
                pub_path.read_bytes()
            )
        else:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            self._public_key = self._private_key.public_key()

            priv_pem = self._private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            pub_pem = self._public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            priv_path.write_bytes(priv_pem)
            os.chmod(priv_path, 0o600)
            pub_path.write_bytes(pub_pem)

    def get_public_key_pem(self) -> str:
        """Return PEM-encoded public key for external verification."""
        return self._public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

    # ============================================================
    # TOKEN ISSUANCE
    # ============================================================

    def issue_token(
        self,
        scope: str,
        ttl_seconds: Optional[int] = None,
        subject: Optional[str] = None,
        include_refresh: bool = True,
        **kwargs,
    ) -> JWTToken:
        """
        Issue a JWT access token (and optionally a refresh token).

        Args:
            scope: Space-separated scope string (e.g. "mcp:tools mcp:resources")
            ttl_seconds: Override default access TTL
            subject: User/client identifier
            include_refresh: Whether to include a refresh token
        """
        now = int(time.time())
        jti = secrets.token_hex(16)
        access_ttl = ttl_seconds or self._access_ttl

        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": subject or "anonymous",
            "iat": now,
            "nbf": now,
            "exp": now + access_ttl,
            "jti": jti,
            "scope": scope,
        }

        jwt_string = _create_jwt(payload, self._private_key)

        # Create refresh token if requested
        refresh_token = None
        refresh_family = None
        if include_refresh:
            refresh_family = secrets.token_hex(8)
            refresh_token = secrets.token_urlsafe(48)
            refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            with self._lock:
                self._refresh_records[refresh_hash] = RefreshRecord(
                    family_id=refresh_family,
                    token_hash=refresh_hash,
                    subject=subject or "anonymous",
                    scope=scope,
                    issued_at=now,
                    expires_at=now + self._refresh_ttl,
                )

        token = JWTToken(
            token_id=jti,
            created_at=datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            expires_at=datetime.fromtimestamp(now + access_ttl, tz=timezone.utc).isoformat(),
            scope=scope,
            jwt_string=jwt_string,
            refresh_token=refresh_token,
            refresh_family=refresh_family,
            subject=subject,
        )

        with self._lock:
            self._metrics["tokens_issued"] += 1

        self._log_event("issued", jti, subject or "anonymous", scope)
        return token

    # ============================================================
    # TOKEN VALIDATION
    # ============================================================

    def validate_token(
        self,
        token_id: str,
        required_scope: str = None,
        **kwargs,
    ) -> Tuple[bool, str]:
        """
        Validate a JWT access token.

        The token_id parameter here is the raw JWT string (not the jti).
        This follows the MCP pattern where the Bearer token is passed in.

        Returns:
            Tuple of (is_valid, error_message)
        """
        jwt_string = token_id  # In HTTP context, this is the Bearer token

        valid, payload, error = _verify_jwt(jwt_string, self._public_key)
        if not valid:
            with self._lock:
                self._metrics["tokens_rejected"] += 1
            return False, error

        # Check deny-list
        jti = payload.get("jti", "")
        with self._lock:
            if jti in self._deny_list:
                self._metrics["tokens_rejected"] += 1
                return False, "Token has been revoked"

        # Check scope
        if required_scope:
            token_scopes = set(payload.get("scope", "").split())
            required_scopes = set(required_scope.split())
            if "mcp:admin" not in token_scopes and not required_scopes.issubset(token_scopes):
                with self._lock:
                    self._metrics["tokens_rejected"] += 1
                return False, f"Insufficient scope: need {required_scope}, have {payload.get('scope')}"

        # Check issuer/audience
        if payload.get("iss") != self._issuer:
            return False, f"Invalid issuer: {payload.get('iss')}"
        if payload.get("aud") != self._audience:
            return False, f"Invalid audience: {payload.get('aud')}"

        with self._lock:
            self._metrics["tokens_validated"] += 1

        return True, "Valid"

    def decode_token(self, jwt_string: str) -> Tuple[bool, dict, str]:
        """
        Decode and validate a JWT, returning the full payload.

        Returns:
            Tuple of (is_valid, payload_dict, error_message)
        """
        valid, payload, error = _verify_jwt(jwt_string, self._public_key)
        if not valid:
            return False, {}, error

        jti = payload.get("jti", "")
        with self._lock:
            if jti in self._deny_list:
                return False, {}, "Token has been revoked"

        return True, payload, ""

    # ============================================================
    # TOKEN REFRESH
    # ============================================================

    def refresh_access_token(
        self, refresh_token: str
    ) -> Tuple[Optional[JWTToken], str]:
        """
        Exchange a refresh token for a new access+refresh token pair.

        Implements refresh token rotation:
        - Each refresh token is single-use
        - If a used refresh token is presented, the entire family is revoked
          (detects token theft)

        Returns:
            Tuple of (new_token_or_None, error_message)
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        with self._lock:
            record = self._refresh_records.get(token_hash)

            if not record:
                return None, "Invalid refresh token"

            # Check family revocation
            if record.family_id in self._revoked_families:
                return None, "Refresh token family revoked (possible theft detected)"

            # Check expiration
            if record.expires_at < time.time():
                return None, "Refresh token expired"

            # Check revocation
            if record.revoked:
                return None, "Refresh token revoked"

            # Detect reuse (rotation violation = possible theft)
            if record.used:
                self._revoked_families.add(record.family_id)
                self._metrics["tokens_revoked"] += 1
                return None, "Refresh token reuse detected — family revoked (possible theft)"

            # Mark as used
            record.used = True

        # Issue new token pair with same family
        new_token = self.issue_token(
            scope=record.scope,
            subject=record.subject,
            include_refresh=True,
        )

        # Link new refresh to same family
        if new_token.refresh_token:
            new_hash = hashlib.sha256(new_token.refresh_token.encode()).hexdigest()
            with self._lock:
                if new_hash in self._refresh_records:
                    self._refresh_records[new_hash].family_id = record.family_id
                new_token.refresh_family = record.family_id
                self._metrics["tokens_refreshed"] += 1

        self._log_event("refreshed", new_token.token_id, record.subject, record.scope)
        return new_token, ""

    # ============================================================
    # TOKEN REVOCATION
    # ============================================================

    def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a token by its jti or JWT string.

        If a JWT string is provided, extract the jti and revoke it.
        """
        jti = token_id

        # Try to extract jti from JWT string
        if "." in token_id:
            try:
                parts = token_id.split(".")
                payload = json.loads(_b64url_decode(parts[1]))
                jti = payload.get("jti", token_id)
            except Exception:
                pass

        with self._lock:
            self._deny_list.add(jti)
            self._metrics["tokens_revoked"] += 1

        self._log_event("revoked", jti, "system", "")
        return True

    def revoke_refresh_family(self, family_id: str) -> bool:
        """Revoke an entire refresh token family."""
        with self._lock:
            self._revoked_families.add(family_id)
        return True

    # ============================================================
    # CLEANUP
    # ============================================================

    def cleanup_expired(self) -> int:
        """Clean up expired refresh records."""
        now = time.time()
        removed = 0

        with self._lock:
            expired_hashes = [
                h for h, r in self._refresh_records.items()
                if r.expires_at < now
            ]
            for h in expired_hashes:
                del self._refresh_records[h]
                removed += 1

        return removed

    # ============================================================
    # PROTECTED RESOURCE METADATA (RFC9728)
    # ============================================================

    def get_protected_resource_metadata(
        self,
        resource_url: str = "https://localhost/mcp",
        authorization_servers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Protected Resource Metadata per RFC9728.

        This will be served at /.well-known/oauth-protected-resource
        """
        return {
            "resource": resource_url,
            "authorization_servers": authorization_servers or [f"{resource_url}/auth"],
            "scopes_supported": list(SCOPES.keys()),
            "bearer_methods_supported": ["header"],
            "resource_signing_alg_values_supported": ["RS256"],
            "resource_documentation": "https://nucleusos.dev/docs/auth",
        }

    # ============================================================
    # METRICS & AUDIT
    # ============================================================

    def get_metrics(self) -> Dict[str, Any]:
        """Get JWT auth metrics."""
        with self._lock:
            return {
                **self._metrics,
                "active_refresh_tokens": len(self._refresh_records),
                "deny_list_size": len(self._deny_list),
                "revoked_families": len(self._revoked_families),
            }

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent JWT auth events."""
        try:
            log_file = self._brain_path / "ledger" / "auth" / "jwt_events.jsonl"
            if not log_file.exists():
                return []
            entries = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            return entries[-limit:]
        except Exception:
            return []

    def _log_event(self, event_type: str, jti: str, subject: str, scope: str) -> None:
        """Log JWT lifecycle event to audit ledger."""
        try:
            auth_dir = self._brain_path / "ledger" / "auth"
            auth_dir.mkdir(parents=True, exist_ok=True)
            log_file = auth_dir / "jwt_events.jsonl"
            event = {
                "event": event_type,
                "jti": jti,
                "subject": subject,
                "scope": scope,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass
