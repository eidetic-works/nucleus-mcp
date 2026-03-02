"""
Tests for the OAuth-Ready Auth Architecture (v0.6.1)

Tests the abstract interface, IPC provider, and auth manager.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from mcp_server_nucleus.runtime.auth import (
    AuthProvider,
    AuthToken,
    AuthResult,
    IPCAuthProvider,
    IPCToken,
    TokenMeterEntry,
    get_auth_provider,
    AuthTransport,
    require_ipc_token,
)
from mcp_server_nucleus.runtime.auth.auth_manager import (
    register_provider,
    clear_providers,
)


class TestAuthToken:
    """Tests for base AuthToken class."""
    
    def test_token_creation(self):
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(seconds=30)).isoformat()
        
        token = AuthToken(
            token_id="test-123",
            created_at=now.isoformat(),
            expires_at=expires,
            scope="tool_call"
        )
        
        assert token.token_id == "test-123"
        assert token.scope == "tool_call"
        assert not token.is_expired()
    
    def test_token_expired(self):
        now = datetime.now(timezone.utc)
        past = (now - timedelta(seconds=30)).isoformat()
        
        token = AuthToken(
            token_id="test-456",
            created_at=past,
            expires_at=past,
            scope="read"
        )
        
        assert token.is_expired()
    
    def test_token_to_dict(self):
        now = datetime.now(timezone.utc)
        token = AuthToken(
            token_id="test-789",
            created_at=now.isoformat(),
            expires_at=now.isoformat(),
            scope="write",
            metadata={"key": "value"}
        )
        
        d = token.to_dict()
        assert d["token_id"] == "test-789"
        assert d["scope"] == "write"
        assert d["metadata"]["key"] == "value"


class TestIPCAuthProvider:
    """Tests for IPC Auth Provider."""
    
    @pytest.fixture
    def temp_brain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def provider(self, temp_brain):
        return IPCAuthProvider(brain_path=temp_brain)
    
    def test_provider_properties(self, provider):
        assert provider.provider_name == "IPC Auth Provider"
        assert provider.transport_type == "stdio"
    
    def test_issue_token(self, provider):
        token = provider.issue_token(scope="tool_call", decision_id="dec-123")
        
        assert token.token_id.startswith("ipc-")
        assert token.scope == "tool_call"
        assert token.decision_id == "dec-123"
        assert not token.consumed
    
    def test_validate_token_success(self, provider):
        token = provider.issue_token(scope="tool_call")
        is_valid, msg = provider.validate_token(token.token_id, "tool_call")
        
        assert is_valid is True
        assert msg == "Valid"
    
    def test_validate_token_not_found(self, provider):
        is_valid, msg = provider.validate_token("nonexistent", "tool_call")
        
        assert is_valid is False
        assert "not found" in msg.lower()
    
    def test_validate_token_scope_mismatch(self, provider):
        token = provider.issue_token(scope="read")
        is_valid, msg = provider.validate_token(token.token_id, "write")
        
        assert is_valid is False
        assert "scope" in msg.lower()
    
    def test_validate_admin_scope_bypass(self, provider):
        token = provider.issue_token(scope="admin")
        is_valid, msg = provider.validate_token(token.token_id, "write")
        
        assert is_valid is True
    
    def test_consume_token(self, provider):
        token = provider.issue_token(scope="tool_call")
        
        success = provider.consume_token(token.token_id)
        assert success
        
        # Second consumption should fail
        success = provider.consume_token(token.token_id)
        assert not success
    
    def test_validate_consumed_token(self, provider):
        token = provider.issue_token(scope="tool_call")
        provider.consume_token(token.token_id)
        
        is_valid, msg = provider.validate_token(token.token_id, "tool_call")
        assert is_valid is False
        assert "consumed" in msg.lower()
    
    def test_cleanup_expired(self, provider):
        # Issue token with negative TTL (already expired)
        token = provider.issue_token(scope="tool_call", ttl_seconds=-1)
        
        cleaned = provider.cleanup_expired()
        assert cleaned >= 1
    
    def test_metering_summary(self, provider):
        token1 = provider.issue_token(scope="tool_call")
        token2 = provider.issue_token(scope="read")
        
        provider.consume_token(token1.token_id, resource_type="tool_call", units=1.0)
        provider.consume_token(token2.token_id, resource_type="read", units=0.5)
        
        summary = provider.get_metering_summary()
        
        assert summary["total_entries"] == 2
        assert summary["total_units"] == 1.5
        assert "tool_call" in summary["by_scope"]
        assert "read" in summary["by_scope"]


class TestAuthManager:
    """Tests for auth manager routing."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, tmp_path, monkeypatch):
        clear_providers()
        # Set temp brain path for tests
        monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(tmp_path))
        yield
        clear_providers()
    
    def test_get_stdio_provider(self):
        provider = get_auth_provider(AuthTransport.STDIO)
        assert isinstance(provider, IPCAuthProvider)
    
    def test_get_http_provider_returns_jwt(self):
        from mcp_server_nucleus.runtime.auth.jwt_provider import JWTAuthProvider
        provider = get_auth_provider(AuthTransport.HTTP)
        assert isinstance(provider, JWTAuthProvider)
    
    def test_get_sse_provider_returns_jwt(self):
        from mcp_server_nucleus.runtime.auth.jwt_provider import JWTAuthProvider
        provider = get_auth_provider(AuthTransport.SSE)
        assert isinstance(provider, JWTAuthProvider)
    
    def test_register_custom_provider(self):
        class MockProvider(AuthProvider):
            @property
            def provider_name(self): return "Mock"
            @property
            def transport_type(self): return "custom"
            def issue_token(self, scope, ttl_seconds=None, **kwargs): pass
            def validate_token(self, token_id, required_scope, **kwargs): return (AuthResult.SUCCESS, "OK")
            def revoke_token(self, token_id): return True
            def cleanup_expired(self): return 0
        
        mock = MockProvider()
        register_provider("custom", mock)
        
        # Should return our mock
        from mcp_server_nucleus.runtime.auth.auth_manager import _providers
        assert "custom" in _providers


class TestIPCToken:
    """Tests for IPC-specific token features."""
    
    def test_ipc_token_extends_auth_token(self):
        now = datetime.now(timezone.utc)
        token = IPCToken(
            token_id="ipc-test",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=30)).isoformat(),
            scope="tool_call",
            decision_id="dec-abc"
        )
        
        assert isinstance(token, AuthToken)
        assert token.decision_id == "dec-abc"
    
    def test_ipc_token_is_valid(self):
        now = datetime.now(timezone.utc)
        token = IPCToken(
            token_id="ipc-test",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=30)).isoformat(),
            scope="tool_call"
        )
        
        assert token.is_valid()
        
        # Consume it
        token.consumed = True
        assert not token.is_valid()
    
    def test_ipc_token_to_dict(self):
        now = datetime.now(timezone.utc)
        token = IPCToken(
            token_id="ipc-test",
            created_at=now.isoformat(),
            expires_at=now.isoformat(),
            scope="tool_call",
            decision_id="dec-123",
            consumed=True,
            consumed_at=now.isoformat(),
            request_hash="abc123"
        )
        
        d = token.to_dict()
        assert d["decision_id"] == "dec-123"
        assert d["consumed"] is True
        assert d["request_hash"] == "abc123"


class TestRequireIPCTokenDecorator:
    """Tests for the require_ipc_token decorator."""
    
    @pytest.fixture
    def temp_brain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_decorator_allows_valid_token(self, temp_brain, monkeypatch):
        # Patch the singleton to use our temp brain
        from mcp_server_nucleus.runtime.auth import ipc_provider
        provider = IPCAuthProvider(brain_path=temp_brain)
        monkeypatch.setattr(ipc_provider, "_ipc_auth_manager", provider)
        
        token = provider.issue_token(scope="test_scope")
        
        @require_ipc_token("test_scope")
        def protected_func(token_id):
            return "success"
        
        result = protected_func(token_id=token.token_id)
        assert result == "success"
    
    def test_decorator_rejects_missing_token(self):
        @require_ipc_token("test_scope")
        def protected_func():
            return "success"
        
        with pytest.raises(PermissionError) as exc_info:
            protected_func()
        
        assert "required but not provided" in str(exc_info.value)
