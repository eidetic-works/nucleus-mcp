"""
Comprehensive JWT Authentication Tests (Phase 2)

Tests the JWTAuthProvider including:
- Key generation and persistence
- Token issuance (access + refresh)
- RS256 signature verification
- Scope enforcement
- Token revocation (single + family)
- Refresh token rotation
- Refresh token theft detection
- Protected Resource Metadata (RFC9728)
- Auth manager integration (HTTP/SSE transport routing)
- Metrics and audit logging
- Thread safety basics
- Zero-friction STDIO preservation
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.auth.jwt_provider import (
    JWTAuthProvider,
    JWTToken,
    SCOPES,
    _create_jwt,
    _verify_jwt,
    _b64url_encode,
    _b64url_decode,
)
from mcp_server_nucleus.runtime.auth.base import AuthProvider, AuthToken, AuthResult
from mcp_server_nucleus.runtime.auth.auth_manager import (
    get_auth_provider,
    AuthTransport,
    register_provider,
    clear_providers,
)
from mcp_server_nucleus.runtime.auth.ipc_provider import IPCAuthProvider


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def temp_brain():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def jwt_provider(temp_brain):
    return JWTAuthProvider(brain_path=temp_brain)


@pytest.fixture(autouse=True)
def clean_auth_manager():
    """Reset auth manager state between tests."""
    clear_providers()
    yield
    clear_providers()


# ============================================================
# BASE64URL HELPERS
# ============================================================

class TestBase64UrlHelpers:
    def test_roundtrip(self):
        data = b"hello world"
        encoded = _b64url_encode(data)
        decoded = _b64url_decode(encoded)
        assert decoded == data

    def test_no_padding(self):
        data = b"test"
        encoded = _b64url_encode(data)
        assert "=" not in encoded

    def test_url_safe_characters(self):
        data = bytes(range(256))
        encoded = _b64url_encode(data)
        assert "+" not in encoded
        assert "/" not in encoded


# ============================================================
# KEY MANAGEMENT
# ============================================================

class TestKeyManagement:
    def test_keys_generated_on_init(self, jwt_provider, temp_brain):
        keys_dir = temp_brain / "secrets" / "jwt"
        assert (keys_dir / "private.pem").exists()
        assert (keys_dir / "public.pem").exists()

    def test_private_key_permissions(self, jwt_provider, temp_brain):
        priv_path = temp_brain / "secrets" / "jwt" / "private.pem"
        mode = oct(priv_path.stat().st_mode)[-3:]
        assert mode == "600"

    def test_keys_persist_across_instances(self, temp_brain):
        p1 = JWTAuthProvider(brain_path=temp_brain)
        pub1 = p1.get_public_key_pem()

        p2 = JWTAuthProvider(brain_path=temp_brain)
        pub2 = p2.get_public_key_pem()

        assert pub1 == pub2

    def test_public_key_pem_format(self, jwt_provider):
        pem = jwt_provider.get_public_key_pem()
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")
        assert pem.strip().endswith("-----END PUBLIC KEY-----")


# ============================================================
# TOKEN ISSUANCE
# ============================================================

class TestTokenIssuance:
    def test_issue_basic_token(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        assert isinstance(token, JWTToken)
        assert token.token_id  # jti
        assert token.jwt_string
        assert token.scope == "mcp:tools"
        assert token.refresh_token is not None
        assert token.refresh_family is not None

    def test_issue_token_without_refresh(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", include_refresh=False)
        assert token.refresh_token is None
        assert token.refresh_family is None

    def test_issue_token_with_subject(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", subject="user-123")
        assert token.subject == "user-123"

    def test_issue_token_custom_ttl(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", ttl_seconds=60)
        # Token should be valid
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid

    def test_issue_multi_scope(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools mcp:resources")
        assert token.scope == "mcp:tools mcp:resources"

    def test_jwt_string_has_three_parts(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        parts = token.jwt_string.split(".")
        assert len(parts) == 3

    def test_jwt_header_is_rs256(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        header_b64 = token.jwt_string.split(".")[0]
        header = json.loads(_b64url_decode(header_b64))
        assert header["alg"] == "RS256"
        assert header["typ"] == "JWT"

    def test_jwt_payload_contains_standard_claims(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", subject="test-sub")
        payload_b64 = token.jwt_string.split(".")[1]
        payload = json.loads(_b64url_decode(payload_b64))
        assert payload["iss"] == "nucleus-mcp"
        assert payload["aud"] == "nucleus-mcp-client"
        assert payload["sub"] == "test-sub"
        assert "iat" in payload
        assert "exp" in payload
        assert "nbf" in payload
        assert "jti" in payload
        assert payload["scope"] == "mcp:tools"

    def test_token_to_dict(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", subject="u1")
        d = token.to_dict()
        assert d["subject"] == "u1"
        assert d["has_refresh"] is True
        assert d["revoked"] is False


# ============================================================
# TOKEN VALIDATION
# ============================================================

class TestTokenValidation:
    def test_validate_valid_token(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is True
        assert msg == "Valid"

    def test_validate_expired_token(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", ttl_seconds=-1)
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is False
        assert "expired" in msg.lower()

    def test_validate_wrong_scope(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:resources")
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is False
        assert "scope" in msg.lower()

    def test_validate_admin_scope_bypass(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:admin")
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is True

    def test_validate_multi_scope_subset(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools mcp:resources mcp:prompts")
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is True

    def test_validate_multi_scope_superset_fails(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools mcp:resources")
        assert valid is False

    def test_validate_tampered_payload(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        parts = token.jwt_string.split(".")
        # Tamper with payload
        payload = json.loads(_b64url_decode(parts[1]))
        payload["scope"] = "mcp:admin"
        parts[1] = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        tampered = ".".join(parts)

        valid, msg = jwt_provider.validate_token(tampered, "mcp:admin")
        assert valid is False
        assert "signature" in msg.lower()

    def test_validate_malformed_jwt(self, jwt_provider):
        valid, msg = jwt_provider.validate_token("not.a.jwt", "mcp:tools")
        assert valid is False

    def test_validate_two_part_jwt(self, jwt_provider):
        valid, msg = jwt_provider.validate_token("only.two", "mcp:tools")
        assert valid is False
        assert "malformed" in msg.lower()

    def test_validate_no_scope_required(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        valid, msg = jwt_provider.validate_token(token.jwt_string)
        assert valid is True

    def test_decode_token(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", subject="decode-test")
        valid, payload, msg = jwt_provider.decode_token(token.jwt_string)
        assert valid is True
        assert payload["sub"] == "decode-test"
        assert payload["scope"] == "mcp:tools"


# ============================================================
# TOKEN REVOCATION
# ============================================================

class TestTokenRevocation:
    def test_revoke_by_jti(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        jwt_provider.revoke_token(token.token_id)
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is False
        assert "revoked" in msg.lower()

    def test_revoke_by_jwt_string(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        jwt_provider.revoke_token(token.jwt_string)
        valid, msg = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        assert valid is False
        assert "revoked" in msg.lower()

    def test_revoke_token_returns_true(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        result = jwt_provider.revoke_token(token.token_id)
        assert result is True

    def test_revoke_refresh_family(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        jwt_provider.revoke_refresh_family(token.refresh_family)
        new_token, error = jwt_provider.refresh_access_token(token.refresh_token)
        assert new_token is None
        assert "family revoked" in error.lower()


# ============================================================
# REFRESH TOKEN ROTATION
# ============================================================

class TestRefreshTokenRotation:
    def test_refresh_success(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools", subject="refresh-user")
        new_token, error = jwt_provider.refresh_access_token(token.refresh_token)
        assert error == ""
        assert new_token is not None
        assert new_token.jwt_string != token.jwt_string
        assert new_token.refresh_token is not None
        assert new_token.refresh_token != token.refresh_token

    def test_refresh_preserves_scope(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools mcp:resources")
        new_token, _ = jwt_provider.refresh_access_token(token.refresh_token)
        valid, payload, _ = jwt_provider.decode_token(new_token.jwt_string)
        assert payload["scope"] == "mcp:tools mcp:resources"

    def test_refresh_single_use(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")

        # First refresh succeeds
        new_token, error = jwt_provider.refresh_access_token(token.refresh_token)
        assert new_token is not None

        # Second use of same refresh token triggers theft detection
        stolen, error = jwt_provider.refresh_access_token(token.refresh_token)
        assert stolen is None
        assert "reuse" in error.lower() or "theft" in error.lower()

    def test_refresh_theft_revokes_family(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")

        # Legitimate refresh
        new_token, _ = jwt_provider.refresh_access_token(token.refresh_token)
        assert new_token is not None

        # Attacker reuses old refresh token → family revoked
        _, error = jwt_provider.refresh_access_token(token.refresh_token)
        assert "reuse" in error.lower() or "theft" in error.lower()

        # Even the new refresh token from legitimate refresh is now invalid
        _, error2 = jwt_provider.refresh_access_token(new_token.refresh_token)
        assert "family revoked" in error2.lower()

    def test_refresh_invalid_token(self, jwt_provider):
        new_token, error = jwt_provider.refresh_access_token("invalid-token")
        assert new_token is None
        assert "invalid" in error.lower()

    def test_refresh_expired_token(self, jwt_provider):
        provider = JWTAuthProvider(
            brain_path=jwt_provider._brain_path,
            refresh_ttl=-1,  # Already expired
        )
        token = provider.issue_token(scope="mcp:tools")
        new_token, error = provider.refresh_access_token(token.refresh_token)
        assert new_token is None
        assert "expired" in error.lower()


# ============================================================
# CLEANUP
# ============================================================

class TestCleanup:
    def test_cleanup_expired_refresh_tokens(self, temp_brain):
        provider = JWTAuthProvider(brain_path=temp_brain, refresh_ttl=-1)
        provider.issue_token(scope="mcp:tools")
        provider.issue_token(scope="mcp:tools")
        removed = provider.cleanup_expired()
        assert removed >= 2

    def test_cleanup_keeps_valid_tokens(self, jwt_provider):
        jwt_provider.issue_token(scope="mcp:tools")
        removed = jwt_provider.cleanup_expired()
        assert removed == 0


# ============================================================
# PROTECTED RESOURCE METADATA (RFC9728)
# ============================================================

class TestProtectedResourceMetadata:
    def test_metadata_structure(self, jwt_provider):
        meta = jwt_provider.get_protected_resource_metadata(
            resource_url="https://nucleus.example.com/mcp"
        )
        assert meta["resource"] == "https://nucleus.example.com/mcp"
        assert "authorization_servers" in meta
        assert "scopes_supported" in meta
        assert "bearer_methods_supported" in meta
        assert "RS256" in meta["resource_signing_alg_values_supported"]

    def test_metadata_includes_all_scopes(self, jwt_provider):
        meta = jwt_provider.get_protected_resource_metadata()
        for scope in SCOPES:
            assert scope in meta["scopes_supported"]


# ============================================================
# METRICS
# ============================================================

class TestMetrics:
    def test_initial_metrics(self, jwt_provider):
        metrics = jwt_provider.get_metrics()
        assert metrics["tokens_issued"] == 0
        assert metrics["tokens_validated"] == 0

    def test_metrics_after_operations(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        jwt_provider.validate_token(token.jwt_string, "mcp:tools")
        jwt_provider.validate_token("invalid", "mcp:tools")

        metrics = jwt_provider.get_metrics()
        assert metrics["tokens_issued"] == 1
        assert metrics["tokens_validated"] == 1
        assert metrics["tokens_rejected"] >= 1

    def test_refresh_metrics(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        jwt_provider.refresh_access_token(token.refresh_token)
        metrics = jwt_provider.get_metrics()
        assert metrics["tokens_refreshed"] >= 1
        # 2 issued: original + refreshed
        assert metrics["tokens_issued"] >= 2


# ============================================================
# AUDIT LOG
# ============================================================

class TestAuditLog:
    def test_audit_log_records_events(self, jwt_provider):
        jwt_provider.issue_token(scope="mcp:tools", subject="audit-test")
        log = jwt_provider.get_audit_log()
        assert len(log) >= 1
        assert log[0]["event"] == "issued"
        assert log[0]["subject"] == "audit-test"

    def test_audit_log_empty_initially(self, temp_brain):
        provider = JWTAuthProvider(brain_path=temp_brain)
        log = provider.get_audit_log()
        assert log == []


# ============================================================
# AUTH MANAGER INTEGRATION
# ============================================================

class TestAuthManagerIntegration:
    @pytest.fixture(autouse=True)
    def set_brain_path(self, tmp_path, monkeypatch):
        """Set temp brain path so IPC/JWT providers don't hit real filesystem."""
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        clear_providers()
        yield
        clear_providers()

    def test_http_transport_returns_jwt_provider(self):
        provider = get_auth_provider(AuthTransport.HTTP)
        assert isinstance(provider, JWTAuthProvider)

    def test_sse_transport_returns_jwt_provider(self):
        provider = get_auth_provider(AuthTransport.SSE)
        assert isinstance(provider, JWTAuthProvider)

    def test_stdio_transport_returns_ipc_provider(self):
        provider = get_auth_provider(AuthTransport.STDIO)
        assert isinstance(provider, IPCAuthProvider)

    def test_stdio_not_affected_by_jwt(self):
        """STDIO users should never encounter JWT auth."""
        ipc = get_auth_provider(AuthTransport.STDIO)
        token = ipc.issue_token(scope="tool_call")
        valid, msg = ipc.validate_token(token.token_id, "tool_call")
        assert valid is True

    def test_provider_caching(self):
        p1 = get_auth_provider(AuthTransport.HTTP)
        p2 = get_auth_provider(AuthTransport.HTTP)
        assert p1 is p2


# ============================================================
# PROVIDER INTERFACE COMPLIANCE
# ============================================================

class TestProviderInterface:
    def test_implements_auth_provider(self, jwt_provider):
        assert isinstance(jwt_provider, AuthProvider)

    def test_provider_name(self, jwt_provider):
        assert jwt_provider.provider_name == "JWT Auth Provider"

    def test_transport_type(self, jwt_provider):
        assert jwt_provider.transport_type == "http"


# ============================================================
# THREAD SAFETY
# ============================================================

class TestThreadSafety:
    def test_concurrent_token_issuance(self, jwt_provider):
        tokens = []
        errors = []

        def issue():
            try:
                t = jwt_provider.issue_token(scope="mcp:tools")
                tokens.append(t)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=issue) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tokens) == 20
        # All tokens should have unique jti
        jtis = {t.token_id for t in tokens}
        assert len(jtis) == 20

    def test_concurrent_validation(self, jwt_provider):
        token = jwt_provider.issue_token(scope="mcp:tools")
        results = []

        def validate():
            valid, _ = jwt_provider.validate_token(token.jwt_string, "mcp:tools")
            results.append(valid)

        threads = [threading.Thread(target=validate) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)


# ============================================================
# CROSS-PROVIDER ISOLATION
# ============================================================

class TestCrossProviderIsolation:
    def test_jwt_token_invalid_on_ipc(self, jwt_provider, temp_brain):
        ipc = IPCAuthProvider(brain_path=temp_brain)
        jwt_token = jwt_provider.issue_token(scope="mcp:tools")

        # JWT string should not validate on IPC provider
        valid, msg = ipc.validate_token(jwt_token.jwt_string, "mcp:tools")
        assert valid is False

    def test_ipc_token_invalid_on_jwt(self, jwt_provider, temp_brain):
        ipc = IPCAuthProvider(brain_path=temp_brain)
        ipc_token = ipc.issue_token(scope="tool_call")

        # IPC token ID should not validate on JWT provider
        valid, msg = jwt_provider.validate_token(ipc_token.token_id, "tool_call")
        assert valid is False
