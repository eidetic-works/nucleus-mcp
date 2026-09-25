"""Tests for Clerk integration in the OAuth server.

Covers:
  - Clerk JWT verification (verify_clerk_jwt + extract_email)
  - /authorize redirect to Clerk when enabled
  - /auth/clerk/callback successful flow (JWT → auth code → redirect)
  - /auth/clerk/callback error cases (missing JWT, invalid JWT, unverified email)
  - Backward compat: Clerk disabled → existing consent screen still works
  - Full Clerk flow: callback → token exchange → tenant_id in token
"""
import json
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import parse_qs, urlparse

from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
def clerk_env(oauth_env, monkeypatch):
    """Enable Clerk integration."""
    monkeypatch.setenv("NUCLEUS_CLERK_ENABLED", "true")
    monkeypatch.setenv("NUCLEUS_CLERK_ISSUER", "https://test-app.clerk.accounts.dev")
    monkeypatch.setenv("NUCLEUS_CLERK_JWKS_URL", "https://test-app.clerk.accounts.dev/.well-known/jwks.json")
    # Clear JWKS cache
    import mcp_server_nucleus.http_transport.clerk_auth as clerk_mod
    clerk_mod._clear_jwks_cache()
    yield
    clerk_mod._clear_jwks_cache()


@pytest.fixture
def store(oauth_env):
    from mcp_server_nucleus.http_transport.oauth_server import _get_store
    return _get_store()


# ---------------------------------------------------------------------------
# Helpers: generate a real RS256 JWT for testing
# ---------------------------------------------------------------------------

def _generate_test_jwk():
    """Generate a test RSA key pair as JWK for signing test JWTs."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import base64

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Get public numbers for JWK
    numbers = public_key.public_numbers()

    def _int_to_b64url(n: int) -> str:
        byte_len = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "kid": "test-key-1",
        "use": "sig",
        "alg": "RS256",
        "n": _int_to_b64url(numbers.n),
        "e": _int_to_b64url(numbers.e),
    }

    return private_key, jwk


def _make_clerk_jwt(private_key, email="alice@example.com", verified=True,
                    issuer="https://test-app.clerk.accounts.dev",
                    expired=False, sub="user_abc123"):
    """Create a signed Clerk session JWT for testing."""
    import jwt as pyjwt

    now = int(time.time())
    payload = {
        "iss": issuer,
        "sub": sub,
        "iat": now,
        "nbf": now - 10,
        "exp": now - 1 if expired else now + 3600,
        "email": email,
        "email_verified": verified,
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-1"})


def _mock_jwks_fetch(jwk):
    """Patch _fetch_jwks to return our test JWK."""
    return patch(
        "mcp_server_nucleus.http_transport.clerk_auth._fetch_jwks",
        return_value={"keys": [jwk], "fetched_at": time.time()},
    )


# ---------------------------------------------------------------------------
# Tests: Clerk JWT verification
# ---------------------------------------------------------------------------

class TestClerkJwtVerification:

    def test_verify_valid_jwt(self, clerk_env):
        from mcp_server_nucleus.http_transport.clerk_auth import verify_clerk_jwt
        private_key, jwk = _generate_test_jwk()
        token = _make_clerk_jwt(private_key)

        with _mock_jwks_fetch(jwk):
            claims = verify_clerk_jwt(token)

        assert claims is not None
        assert claims["sub"] == "user_abc123"
        assert claims["email"] == "alice@example.com"

    def test_verify_expired_jwt(self, clerk_env):
        from mcp_server_nucleus.http_transport.clerk_auth import verify_clerk_jwt
        private_key, jwk = _generate_test_jwk()
        token = _make_clerk_jwt(private_key, expired=True)

        with _mock_jwks_fetch(jwk):
            claims = verify_clerk_jwt(token)

        assert claims is None

    def test_verify_wrong_issuer(self, clerk_env):
        from mcp_server_nucleus.http_transport.clerk_auth import verify_clerk_jwt
        private_key, jwk = _generate_test_jwk()
        token = _make_clerk_jwt(private_key, issuer="https://wrong.clerk.accounts.dev")

        with _mock_jwks_fetch(jwk):
            claims = verify_clerk_jwt(token)

        assert claims is None

    def test_verify_tampered_jwt(self, clerk_env):
        from mcp_server_nucleus.http_transport.clerk_auth import verify_clerk_jwt
        private_key, jwk = _generate_test_jwk()
        token = _make_clerk_jwt(private_key)
        # Tamper with the payload
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1][:-2] + "xx" + "." + parts[2]

        with _mock_jwks_fetch(jwk):
            claims = verify_clerk_jwt(tampered)

        assert claims is None

    def test_verify_when_clerk_disabled(self, oauth_env):
        """Clerk not enabled — verify_clerk_jwt returns None."""
        from mcp_server_nucleus.http_transport.clerk_auth import verify_clerk_jwt
        private_key, jwk = _generate_test_jwk()
        token = _make_clerk_jwt(private_key)

        with _mock_jwks_fetch(jwk):
            claims = verify_clerk_jwt(token)

        assert claims is None  # Clerk disabled


class TestExtractEmail:

    def test_extract_verified_email(self):
        from mcp_server_nucleus.http_transport.clerk_auth import extract_email
        claims = {"email": "Alice@Example.COM", "email_verified": True}
        assert extract_email(claims) == "alice@example.com"

    def test_extract_unverified_email_rejected(self):
        from mcp_server_nucleus.http_transport.clerk_auth import extract_email
        claims = {"email": "alice@example.com", "email_verified": False}
        assert extract_email(claims) is None

    def test_extract_email_missing_verified_flag(self):
        from mcp_server_nucleus.http_transport.clerk_auth import extract_email
        claims = {"email": "alice@example.com"}
        assert extract_email(claims) is None  # conservative — treat as unverified

    def test_extract_email_address_legacy_claim(self):
        from mcp_server_nucleus.http_transport.clerk_auth import extract_email
        claims = {"email_address": "alice@example.com", "email_verified": True}
        assert extract_email(claims) == "alice@example.com"

    def test_extract_no_email(self):
        from mcp_server_nucleus.http_transport.clerk_auth import extract_email
        claims = {"sub": "user_123", "email_verified": True}
        assert extract_email(claims) is None


# ---------------------------------------------------------------------------
# Tests: /authorize redirect to Clerk
# ---------------------------------------------------------------------------

class TestAuthorizeClerkRedirect:

    def test_authorize_redirects_to_clerk(self, clerk_env, store):
        """When Clerk is enabled, GET /authorize redirects to Clerk sign-in."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        client_rec = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
        )

        with TestClient(app, follow_redirects=False) as c:
            resp = c.get("/authorize", params={
                "client_id": client_rec["client_id"],
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:tools",
                "state": "xyz123",
            })

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "test-app.clerk.accounts.dev/sign-in" in location
        assert "redirect_url=" in location
        # The redirect_url should contain our callback path
        from urllib.parse import unquote
        assert "/auth/clerk/callback" in unquote(location)

    def test_authorize_shows_consent_when_clerk_disabled(self, oauth_env, store):
        """When Clerk is disabled, GET /authorize shows the consent screen."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        client_rec = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
        )

        with TestClient(app) as c:
            resp = c.get("/authorize", params={
                "client_id": client_rec["client_id"],
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:tools",
                "state": "xyz123",
            })

        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Authorize" in resp.text
        # AU-2: the consent screen no longer offers a free-text email field by
        # default. Typing an address there minted a bearer token bound to that
        # address's brain with zero verification, so anyone could claim anyone.
        # The field is now behind NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL; the
        # default deployment serves one shared brain and says so.
        assert "user_email" not in resp.text
        assert "single shared Brain" in resp.text


# ---------------------------------------------------------------------------
# Tests: /auth/clerk/callback
# ---------------------------------------------------------------------------

class TestClerkCallback:

    def test_callback_success(self, clerk_env, store):
        """Valid Clerk JWT → auth code issued → redirect to MCP client."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        jwt_token = _make_clerk_jwt(private_key, email="alice@example.com")

        client_rec = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
        )

        with _mock_jwks_fetch(jwk):
            with TestClient(app, follow_redirects=False) as c:
                resp = c.get("/auth/clerk/callback", params={
                    "__clerk_db_jwt": jwt_token,
                    "client_id": client_rec["client_id"],
                    "redirect_uri": "http://localhost:3000/callback",
                    "scope": "mcp:tools",
                    "state": "xyz123",
                })

        assert resp.status_code == 302
        location = resp.headers["location"]
        assert location.startswith("http://localhost:3000/callback?")
        params = parse_qs(urlparse(location).query)
        assert "code" in params
        assert params["state"] == ["xyz123"]

        # Verify the code was created with the correct tenant_id
        code = params["code"][0]
        entry = store.consume_code(code)
        assert entry is not None
        assert entry["client_id"] == client_rec["client_id"]
        # tenant_id should be SHA-256(alice@example.com)[:16]
        import hashlib
        expected_tenant = f"tenant_{hashlib.sha256(b'alice@example.com').hexdigest()[:16]}"
        assert entry["tenant_id"] == expected_tenant

    def test_callback_missing_jwt(self, clerk_env, store):
        """No JWT in callback → 401."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        client_rec = store.register_client(client_name="test-app")

        with TestClient(app) as c:
            resp = c.get("/auth/clerk/callback", params={
                "client_id": client_rec["client_id"],
                "redirect_uri": "",
                "scope": "mcp:tools",
                "state": "xyz123",
            })

        assert resp.status_code == 401

    def test_callback_invalid_jwt(self, clerk_env, store):
        """Invalid JWT → 401."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        # Use a different key to sign — won't match JWKS
        from cryptography.hazmat.primitives.asymmetric import rsa
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        import jwt as pyjwt
        now = int(time.time())
        bad_token = pyjwt.encode(
            {"iss": "https://test-app.clerk.accounts.dev", "sub": "x",
             "iat": now, "exp": now + 3600, "email": "a@b.com", "email_verified": True},
            other_key, algorithm="RS256", headers={"kid": "test-key-1"},
        )

        client_rec = store.register_client(client_name="test-app")

        with _mock_jwks_fetch(jwk):
            with TestClient(app) as c:
                resp = c.get("/auth/clerk/callback", params={
                    "__clerk_db_jwt": bad_token,
                    "client_id": client_rec["client_id"],
                    "scope": "mcp:tools",
                    "state": "xyz123",
                })

        assert resp.status_code == 401

    def test_callback_unverified_email(self, clerk_env, store):
        """JWT with unverified email → 401."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        jwt_token = _make_clerk_jwt(private_key, email="alice@example.com", verified=False)

        client_rec = store.register_client(client_name="test-app")

        with _mock_jwks_fetch(jwk):
            with TestClient(app) as c:
                resp = c.get("/auth/clerk/callback", params={
                    "__clerk_db_jwt": jwt_token,
                    "client_id": client_rec["client_id"],
                    "scope": "mcp:tools",
                    "state": "xyz123",
                })

        assert resp.status_code == 401

    def test_callback_unknown_client(self, clerk_env, store):
        """Valid JWT but unknown client_id → 400."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        jwt_token = _make_clerk_jwt(private_key)

        with _mock_jwks_fetch(jwk):
            with TestClient(app) as c:
                resp = c.get("/auth/clerk/callback", params={
                    "__clerk_db_jwt": jwt_token,
                    "client_id": "nucleus_nonexistent",
                    "scope": "mcp:tools",
                    "state": "xyz123",
                })

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Full flow — Clerk callback → token exchange → tenant_id in token
# ---------------------------------------------------------------------------

class TestClerkFullFlow:

    def test_clerk_callback_to_token_exchange(self, clerk_env, store):
        """Full flow: Clerk JWT → auth code → token exchange → tenant_id in token."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        jwt_token = _make_clerk_jwt(private_key, email="bob@example.com")

        client_rec = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
        )

        # Step 1: Clerk callback → get auth code
        with _mock_jwks_fetch(jwk):
            with TestClient(app, follow_redirects=False) as c:
                resp = c.get("/auth/clerk/callback", params={
                    "__clerk_db_jwt": jwt_token,
                    "client_id": client_rec["client_id"],
                    "redirect_uri": "http://localhost:3000/callback",
                    "scope": "mcp:tools",
                    "state": "abc",
                })

        assert resp.status_code == 302
        params = parse_qs(urlparse(resp.headers["location"]).query)
        code = params["code"][0]

        # Step 2: Token exchange
        with TestClient(app) as c:
            resp = c.post("/token", data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_rec["client_id"],
                "client_secret": client_rec["client_secret"],
                "redirect_uri": "http://localhost:3000/callback",
            })

        assert resp.status_code == 200
        token_data = resp.json()
        assert token_data["token_type"] == "Bearer"
        assert token_data["access_token"].startswith("nucleus_at_")
        assert "refresh_token" in token_data

        # Step 3: Verify tenant_id is embedded in the token
        access_token = token_data["access_token"]
        token_entry = store.validate_token(access_token)
        assert token_entry is not None
        import hashlib
        expected_tenant = f"tenant_{hashlib.sha256(b'bob@example.com').hexdigest()[:16]}"
        assert token_entry["tenant_id"] == expected_tenant

    def test_two_users_get_different_tenants(self, clerk_env, store):
        """Alice and Bob go through Clerk → different tenant_ids."""
        from mcp_server_nucleus.http_transport.oauth_server import oauth_routes
        from starlette.applications import Starlette
        app = Starlette(routes=oauth_routes)

        private_key, jwk = _generate_test_jwk()
        client_rec = store.register_client(
            client_name="test-app",
            redirect_uris=["http://localhost:3000/callback"],
        )

        tenants = {}
        for email in ["alice@example.com", "bob@example.com"]:
            jwt_token = _make_clerk_jwt(private_key, email=email)

            with _mock_jwks_fetch(jwk):
                with TestClient(app, follow_redirects=False) as c:
                    resp = c.get("/auth/clerk/callback", params={
                        "__clerk_db_jwt": jwt_token,
                        "client_id": client_rec["client_id"],
                        "redirect_uri": "http://localhost:3000/callback",
                        "scope": "mcp:tools",
                        "state": "x",
                    })

            assert resp.status_code == 302
            code = parse_qs(urlparse(resp.headers["location"]).query)["code"][0]

            with TestClient(app) as c:
                resp = c.post("/token", data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_rec["client_id"],
                    "client_secret": client_rec["client_secret"],
                    "redirect_uri": "http://localhost:3000/callback",
                })

            access_token = resp.json()["access_token"]
            token_entry = store.validate_token(access_token)
            tenants[email] = token_entry["tenant_id"]

        # Different emails → different tenants
        assert tenants["alice@example.com"] != tenants["bob@example.com"]

        # Same email → same tenant (deterministic)
        import hashlib
        expected = f"tenant_{hashlib.sha256(b'alice@example.com').hexdigest()[:16]}"
        assert tenants["alice@example.com"] == expected
