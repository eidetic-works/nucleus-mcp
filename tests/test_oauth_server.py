"""Tests for the OAuth 2.1 authorization server (http_transport/oauth_server.py).

Covers:
  - Dynamic Client Registration (DCR)
  - Authorization code flow (create → consume → issue token)
  - Token validation
  - Refresh token flow
  - Token revocation
  - Well-known metadata endpoints
  - Bearer token integration with tenant middleware
"""
import os
import time
import json
import pytest
from starlette.testclient import TestClient


@pytest.fixture
def oauth_env(monkeypatch):
    """Enable OAuth with test issuer."""
    monkeypatch.setenv("NUCLEUS_OAUTH_ENABLED", "true")
    monkeypatch.setenv("NUCLEUS_OAUTH_ISSUER", "https://test.nucleusos.dev")
    monkeypatch.setenv("NUCLEUS_OAUTH_STORE_PATH", "")  # in-memory only
    # Reset the singleton store
    import mcp_server_nucleus.http_transport.oauth_server as mod
    mod._store = None
    yield
    mod._store = None


@pytest.fixture
def store(oauth_env):
    from mcp_server_nucleus.http_transport.oauth_server import _get_store
    return _get_store()


class TestDynamicClientRegistration:
    """RFC 7591 — Dynamic Client Registration."""

    def test_register_client(self, store):
        client = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
            scopes="mcp:tools mcp:relay",
        )
        assert client["client_id"].startswith("nucleus_")
        assert len(client["client_secret"]) >= 32
        assert client["client_name"] == "test-app"
        assert "mcp:tools" in client["scope"]
        assert "mcp:relay" in client["scope"]

    def test_get_client(self, store):
        client = store.register_client(client_name="test-get")
        retrieved = store.get_client(client["client_id"])
        assert retrieved is not None
        assert retrieved["client_id"] == client["client_id"]

    def test_get_nonexistent_client(self, store):
        assert store.get_client("nucleus_nonexistent") is None


class TestAuthorizationCodeFlow:
    """Authorization code grant flow."""

    def test_create_and_consume_code(self, store):
        client = store.register_client(client_name="test-code")
        code = store.create_code(
            client["client_id"], "mcp:tools", "http://localhost:3000/callback"
        )
        assert len(code) > 20

        entry = store.consume_code(code)
        assert entry is not None
        assert entry["client_id"] == client["client_id"]
        assert entry["scope"] == "mcp:tools"

    def test_consume_expired_code(self, store):
        client = store.register_client(client_name="test-expired")
        code = store.create_code(
            client["client_id"], "mcp:tools", "http://localhost:3000/callback"
        )
        # Manually expire the code
        store.codes[code]["expires"] = int(time.time()) - 1
        entry = store.consume_code(code)
        assert entry is None

    def test_consume_already_consumed_code(self, store):
        client = store.register_client(client_name="test-double")
        code = store.create_code(
            client["client_id"], "mcp:tools", "http://localhost:3000/callback"
        )
        entry1 = store.consume_code(code)
        entry2 = store.consume_code(code)
        assert entry1 is not None
        assert entry2 is None  # code is single-use


class TestTokenIssuance:
    """Access token issuance and validation."""

    def test_issue_and_validate_token(self, store):
        client = store.register_client(client_name="test-token")
        access, refresh, expires_in = store.issue_token(client["client_id"], "mcp:tools")

        assert access.startswith("nucleus_at_")
        assert refresh.startswith("nucleus_rt_")
        assert expires_in == 3600  # default 1 hour

        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        result = validate_bearer(access)
        assert result is not None
        assert result["client_id"] == client["client_id"]
        assert result["scope"] == "mcp:tools"

    def test_validate_invalid_token(self, store):
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        assert validate_bearer("nucleus_at_invalid") is None
        assert validate_bearer("not_an_oauth_token") is None

    def test_refresh_token(self, store):
        client = store.register_client(client_name="test-refresh")
        access, refresh, _ = store.issue_token(client["client_id"], "mcp:tools")

        # Refresh should issue new tokens
        new_access, new_refresh, _ = store.refresh_token(refresh)
        assert new_access != access
        assert new_refresh != refresh

        # Old access token should be revoked
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        assert validate_bearer(access) is None
        assert validate_bearer(new_access) is not None

    def test_refresh_invalid_token(self, store):
        result = store.refresh_token("nucleus_rt_invalid")
        assert result is None

    def test_revoke_access_token(self, store):
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        client = store.register_client(client_name="test-revoke")
        access, refresh, _ = store.issue_token(client["client_id"], "mcp:tools")

        assert store.revoke_token(access) is True
        assert validate_bearer(access) is None

    def test_revoke_refresh_token(self, store):
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        client = store.register_client(client_name="test-revoke-rt")
        access, refresh, _ = store.issue_token(client["client_id"], "mcp:tools")

        assert store.revoke_token(refresh) is True
        assert validate_bearer(access) is None  # access also revoked

    def test_revoke_unknown_token(self, store):
        assert store.revoke_token("unknown_token") is False


class TestWellKnownEndpoints:
    """RFC 9728 + RFC 8414 metadata endpoints."""

    def test_protected_resource_metadata(self, oauth_env):
        from mcp_server_nucleus.http_transport.oauth_server import protected_resource_metadata
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/.well-known/oauth-protected-resource",
            "headers": [],
            "query_string": b"",
            "root_path": "",
            "client": ("127.0.0.1", 8000),
            "server": ("test.nucleusos.dev", 443),
            "scheme": "https",
        }

        request = Request(scope)
        import asyncio

        async def run():
            return await protected_resource_metadata(request)

        response = asyncio.run(run())
        assert response.status_code == 200
        body = json.loads(response.body)
        assert "resource" in body
        assert "authorization_servers" in body
        assert "mcp:tools" in body["scopes_supported"]
        assert "header" in body["bearer_methods_supported"]


class TestTenantMiddlewareOAuthIntegration:
    """OAuth token validation via tenant middleware."""

    def test_oauth_token_resolves_tenant(self, oauth_env, monkeypatch):
        monkeypatch.setenv("NUCLEUS_TENANT_ID", "test-tenant")
        from mcp_server_nucleus.http_transport.tenant import _validate_oauth_token
        from mcp_server_nucleus.http_transport.oauth_server import _get_store

        store = _get_store()
        client = store.register_client(client_name="test-middleware")
        access, _, _ = store.issue_token(client["client_id"], "mcp:tools")

        tenant = _validate_oauth_token(access)
        assert tenant == "test-tenant"

    def test_non_oauth_token_returns_none(self, oauth_env):
        from mcp_server_nucleus.http_transport.tenant import _validate_oauth_token
        assert _validate_oauth_token("some-random-token") is None

    def test_invalid_oauth_token_returns_none(self, oauth_env):
        from mcp_server_nucleus.http_transport.tenant import _validate_oauth_token
        assert _validate_oauth_token("nucleus_at_invalid") is None

    def test_per_user_tenant_routing(self, oauth_env):
        """Tokens issued with a tenant_id route to that tenant's brain."""
        from mcp_server_nucleus.http_transport.tenant import _validate_oauth_token
        from mcp_server_nucleus.http_transport.oauth_server import _get_store, _derive_tenant_id_from_email

        store = _get_store()
        client = store.register_client(client_name="test-per-user")

        email = "alice@example.com"
        tenant_id = _derive_tenant_id_from_email(email)
        access, _, _ = store.issue_token(client["client_id"], "mcp:tools", tenant_id=tenant_id)

        resolved = _validate_oauth_token(access)
        assert resolved == tenant_id
        assert resolved.startswith("tenant_")

    def test_per_user_tenant_routing_deterministic(self, oauth_env):
        """Same email always derives the same tenant_id."""
        from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email

        t1 = _derive_tenant_id_from_email("bob@example.com")
        t2 = _derive_tenant_id_from_email("bob@example.com")
        t3 = _derive_tenant_id_from_email("BOB@example.com")  # case-insensitive
        assert t1 == t2 == t3

    def test_per_user_tenant_routing_different_users_isolated(self, oauth_env):
        """Different emails → different tenant_ids → different brains."""
        from mcp_server_nucleus.http_transport.oauth_server import _derive_tenant_id_from_email

        alice = _derive_tenant_id_from_email("alice@example.com")
        bob = _derive_tenant_id_from_email("bob@example.com")
        assert alice != bob

    def test_legacy_token_without_tenant_id_falls_back(self, oauth_env, monkeypatch):
        """Tokens issued without tenant_id fall back to static NUCLEUS_TENANT_ID."""
        monkeypatch.setenv("NUCLEUS_TENANT_ID", "legacy-tenant")
        from mcp_server_nucleus.http_transport.tenant import _validate_oauth_token
        from mcp_server_nucleus.http_transport.oauth_server import _get_store

        store = _get_store()
        client = store.register_client(client_name="test-legacy")
        # Issue token WITHOUT tenant_id (legacy path)
        access, _, _ = store.issue_token(client["client_id"], "mcp:tools")

        resolved = _validate_oauth_token(access)
        assert resolved == "legacy-tenant"


class TestAuthorizeFormBodyPost:
    """Regression test: authorize POST must read client_id from form body,
    not just query params. The HTML consent form sends hidden fields as
    form body, and the form action may not preserve query params."""

    def test_authorize_post_with_form_body_only(self, oauth_env):
        from mcp_server_nucleus.http_transport.oauth_server import authorize, _get_store
        from starlette.requests import Request
        import asyncio

        store = _get_store()
        client = store.register_client(
            client_name="test-form-post",
            redirect_uris=["https://chatgpt.com/callback"],
        )

        # Simulate a POST with form body only (no query params)
        # This is what happens when the consent form submits
        form_data = "action=allow&client_id={}&redirect_uri=https%3A%2F%2Fchatgpt.com%2Fcallback&scope=mcp%3Atools&state=teststate".format(
            client["client_id"]
        )
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/authorize",
            "headers": [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(form_data)).encode()),
            ],
            "query_string": b"",  # No query params — form body only
            "root_path": "",
            "client": ("127.0.0.1", 8000),
            "server": ("relay.nucleusos.dev", 443),
            "scheme": "https",
        }

        async def receive():
            return {"type": "http.request", "body": form_data.encode(), "more_body": False}

        request = Request(scope, receive=receive)

        async def run():
            return await authorize(request)

        response = asyncio.run(run())
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "code=" in location
        assert "state=teststate" in location
