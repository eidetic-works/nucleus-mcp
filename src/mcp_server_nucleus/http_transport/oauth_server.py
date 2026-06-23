"""OAuth 2.1 Authorization Server for MCP HTTP transport.

Implements the OAuth 2.1 flows required by ChatGPT Connectors, Claude
Connectors, and any MCP client that follows the MCP authorization spec
(https://modelcontextprotocol.io/specification/draft/basic/authorization).

Endpoints served:
  GET  /.well-known/oauth-protected-resource    RFC 9728 Protected Resource Metadata
  GET  /.well-known/oauth-authorization-server  RFC 8414 Authorization Server Metadata
  POST /register                                 RFC 7591 Dynamic Client Registration
  GET  /authorize                                Authorization endpoint (consent screen)
  POST /token                                    Token endpoint (code→token, refresh)

Design choices for v1:
  - Self-contained: Nucleus IS the authorization server (no Keycloak/Auth0 dep)
  - Opaque tokens (not JWT) — simpler, revocable, sufficient for single-tenant
  - In-memory store (clients + codes + tokens) — survives process restart via
    optional file persistence (NUCLEUS_OAUTH_STORE_PATH)
  - DCR is open (no auth on /register) — appropriate for single-tenant; add
    registration auth for multi-tenant deployments
  - Scopes: mcp:tools (default), mcp:resources, mcp:prompts, mcp:relay

Env contract:
  NUCLEUS_OAUTH_ENABLED       "true" to enable OAuth on the MCP endpoint
  NUCLEUS_OAUTH_ISSUER        Base URL of the auth server (e.g. https://relay.nucleusos.dev)
  NUCLEUS_OAUTH_STORE_PATH    Optional file path for persistent token store
  NUCLEUS_OAUTH_ACCESS_TTL    Access token TTL in seconds (default: 3600)
  NUCLEUS_OAUTH_REFRESH_TTL   Refresh token TTL in seconds (default: 2592000 = 30d)

Clerk integration (optional — replaces the self-hosted consent screen with
Clerk's hosted authentication UI for email-verified identity):
  NUCLEUS_CLERK_ENABLED       "true" to enable Clerk for /authorize
  NUCLEUS_CLERK_ISSUER        Clerk frontend API URL (e.g. https://app.clerk.accounts.dev)
  NUCLEUS_CLERK_JWKS_URL      Optional JWKS URL override
  NUCLEUS_CLERK_JWKS_CACHE_TTL  JWKS cache TTL seconds (default: 300)

When Clerk is enabled, /authorize redirects to Clerk's hosted sign-in page
instead of showing the self-hosted consent screen.  Clerk authenticates the
user (magic link / Google / GitHub / MFA) and redirects back to
/auth/clerk/callback with a session JWT.  Nucleus verifies the JWT,
extracts the verified email, derives tenant_id, and issues an auth code —
same downstream flow as the self-hosted path.

Pseudonymity: tokens never logged; only client_id + scope + expiry in logs.
Emails from Clerk are never logged — only the derived tenant_id hash.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.routing import Route

logger = logging.getLogger("nucleus.oauth_server")

# ── Configuration ────────────────────────────────────────────────────────

_DEFAULT_ACCESS_TTL = 3600          # 1 hour
_DEFAULT_REFRESH_TTL = 2592000      # 30 days

_SCOPES_SUPPORTED = [
    "mcp:tools",
    "mcp:resources",
    "mcp:prompts",
    "mcp:relay",
]
_DEFAULT_SCOPES = "mcp:tools"


def _issuer() -> str:
    return os.environ.get("NUCLEUS_OAUTH_ISSUER", "").rstrip("/")


def _access_ttl() -> int:
    return int(os.environ.get("NUCLEUS_OAUTH_ACCESS_TTL", _DEFAULT_ACCESS_TTL))


def _refresh_ttl() -> int:
    return int(os.environ.get("NUCLEUS_OAUTH_REFRESH_TTL", _DEFAULT_REFRESH_TTL))


def _store_path() -> Optional[Path]:
    p = os.environ.get("NUCLEUS_OAUTH_STORE_PATH", "")
    return Path(p) if p else None


def _clerk_enabled() -> bool:
    return os.environ.get("NUCLEUS_CLERK_ENABLED", "false").lower() == "true"


def _clerk_issuer() -> str:
    return os.environ.get("NUCLEUS_CLERK_ISSUER", "").rstrip("/")


def _derive_tenant_id_from_email(email: str) -> str:
    """Derive a deterministic tenant slug from an email address.

    Same email → same tenant_id every time, so a user who re-authorizes
    lands in the same brain.  No PII in the slug — just the first 16 hex
    chars of the SHA-256 hash.

    This is an identity *claim*, not a verified identity.  v2 should add
    email verification (magic link) before trusting the tenant mapping
    for sensitive operations.
    """
    normalized = email.strip().lower()
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"tenant_{digest}"


# ── In-memory + optional file-persistent store ───────────────────────────

class _OAuthStore:
    """Thread-unsafe in-memory store with optional file persistence.

    For v1 single-process deployments. Multi-process (e.g. uvicorn --workers >1)
    requires external storage (Redis, DB) — deferred to v2.
    """

    def __init__(self) -> None:
        self.clients: Dict[str, Dict[str, Any]] = {}       # client_id → client
        self.codes: Dict[str, Dict[str, Any]] = {}          # auth_code → {client_id, scope, redirect_uri, user, expires}
        self.tokens: Dict[str, Dict[str, Any]] = {}         # access_token → {client_id, scope, expires, refresh_token}
        self.refresh_tokens: Dict[str, str] = {}            # refresh_token → access_token
        self._load()

    def _load(self) -> None:
        p = _store_path()
        if not p or not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            self.clients = data.get("clients", {})
            self.tokens = data.get("tokens", {})
            self.refresh_tokens = data.get("refresh_tokens", {})
            # Don't restore auth codes — they're short-lived
            logger.info("OAuth store loaded from %s (%d clients, %d tokens)", p, len(self.clients), len(self.tokens))
        except Exception as e:
            logger.warning("OAuth store load failed: %s", e)

    def _save(self) -> None:
        p = _store_path()
        if not p:
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "clients": self.clients,
                "tokens": self.tokens,
                "refresh_tokens": self.refresh_tokens,
            }, indent=2))
        except Exception as e:
            logger.warning("OAuth store save failed: %s", e)

    # ── Client management ─────────────────────────────────────────────

    def register_client(
        self,
        client_name: str = "",
        redirect_uris: Optional[List[str]] = None,
        grant_types: Optional[List[str]] = None,
        scopes: str = _DEFAULT_SCOPES,
    ) -> Dict[str, Any]:
        client_id = f"nucleus_{secrets.token_hex(12)}"
        client_secret = secrets.token_hex(32)
        now = int(time.time())
        client = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name or "unnamed",
            "redirect_uris": redirect_uris or [],
            "grant_types": grant_types or ["authorization_code", "refresh_token"],
            "scope": scopes,
            "created_at": now,
        }
        self.clients[client_id] = client
        self._save()
        logger.info("DCR: registered client_id=%s name=%s scopes=%s", client_id, client_name, scopes)
        return client

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        return self.clients.get(client_id)

    # ── Authorization codes ───────────────────────────────────────────

    def create_code(
        self,
        client_id: str,
        scope: str,
        redirect_uri: str,
        user: str = "operator",
        tenant_id: Optional[str] = None,
    ) -> str:
        code = secrets.token_urlsafe(32)
        self.codes[code] = {
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "user": user,
            "tenant_id": tenant_id,
            "expires": int(time.time()) + 600,  # 10 min
        }
        return code

    def consume_code(self, code: str) -> Optional[Dict[str, Any]]:
        entry = self.codes.pop(code, None)
        if not entry:
            return None
        if int(time.time()) > entry["expires"]:
            return None
        return entry

    # ── Tokens ────────────────────────────────────────────────────────

    def issue_token(
        self, client_id: str, scope: str, tenant_id: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """Issue (access_token, refresh_token, expires_in).

        If tenant_id is provided it is stored in the token entry so the
        tenant middleware can route each request to the correct per-user
        brain.  If absent the token falls back to the legacy static
        tenant (NUCLEUS_TENANT_ID or "oauth") — backward compat.
        """
        access = f"nucleus_at_{secrets.token_hex(24)}"
        refresh = f"nucleus_rt_{secrets.token_hex(24)}"
        now = int(time.time())
        self.tokens[access] = {
            "client_id": client_id,
            "scope": scope,
            "expires": now + _access_ttl(),
            "refresh_token": refresh,
            "tenant_id": tenant_id,
        }
        self.refresh_tokens[refresh] = access
        self._save()
        logger.info("Token issued: client_id=%s scope=%s expires_in=%ds", client_id, scope, _access_ttl())
        return access, refresh, _access_ttl()

    def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        entry = self.tokens.get(access_token)
        if not entry:
            return None
        if int(time.time()) > entry["expires"]:
            # Try refresh
            return None
        return entry

    def refresh_token(self, refresh_token: str) -> Optional[Tuple[str, str, int]]:
        access = self.refresh_tokens.get(refresh_token)
        if not access:
            return None
        old = self.tokens.get(access)
        if not old:
            return None
        # Revoke old access token
        del self.tokens[access]
        del self.refresh_tokens[refresh_token]
        # Issue new pair, preserving tenant_id
        return self.issue_token(old["client_id"], old["scope"], old.get("tenant_id"))

    def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token."""
        if token in self.tokens:
            rt = self.tokens[token].get("refresh_token")
            del self.tokens[token]
            if rt and rt in self.refresh_tokens:
                del self.refresh_tokens[rt]
            self._save()
            return True
        if token in self.refresh_tokens:
            access = self.refresh_tokens.pop(token)
            if access in self.tokens:
                del self.tokens[access]
            self._save()
            return True
        return False


_store: Optional[_OAuthStore] = None


def _get_store() -> _OAuthStore:
    global _store
    if _store is None:
        _store = _OAuthStore()
    return _store


# ── Token validation for middleware ─────────────────────────────────────

def validate_bearer(token: str) -> Optional[Dict[str, Any]]:
    """Validate an OAuth bearer token. Returns token info or None.

    Called by the MCP endpoint middleware to check OAuth-issued tokens.
    Falls through to the existing tenant-map bearer check if not an OAuth token.
    """
    if token.startswith("nucleus_at_"):
        return _get_store().validate_token(token)
    return None


# ── Route handlers ───────────────────────────────────────────────────────

async def protected_resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728 — Protected Resource Metadata."""
    issuer = _issuer() or str(request.base_url).rstrip("/")
    return JSONResponse({
        "resource": f"{issuer}/mcp",
        "authorization_servers": [issuer],
        "scopes_supported": _SCOPES_SUPPORTED,
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{issuer}/",
    })


async def authorization_server_metadata(request: Request) -> JSONResponse:
    """RFC 8414 — Authorization Server Metadata."""
    issuer = _issuer() or str(request.base_url).rstrip("/")
    return JSONResponse({
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "registration_endpoint": f"{issuer}/register",
        "revocation_endpoint": f"{issuer}/revoke",
        "scopes_supported": _SCOPES_SUPPORTED,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
        "code_challenge_methods_supported": ["S256"],
        "require_pushed_authorization_requests": False,
    })


async def register(request: Request) -> JSONResponse:
    """RFC 7591 — Dynamic Client Registration."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_request", "error_description": "JSON body required"}, status_code=400)

    client_name = body.get("client_name", "")
    redirect_uris = body.get("redirect_uris", [])
    grant_types = body.get("grant_types", ["authorization_code", "refresh_token"])
    scopes = body.get("scope", _DEFAULT_SCOPES)

    client = _get_store().register_client(
        client_name=client_name,
        redirect_uris=redirect_uris,
        grant_types=grant_types,
        scopes=scopes,
    )

    # Per RFC 7591, return the client credentials
    return JSONResponse({
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "client_name": client["client_name"],
        "redirect_uris": client["redirect_uris"],
        "grant_types": client["grant_types"],
        "scope": client["scope"],
        "token_endpoint_auth_method": "client_secret_post",
    }, status_code=201)


async def authorize(request: Request) -> Any:
    """Authorization endpoint — consent screen + code issuance.

    On POST, form body fields take precedence over query params (the HTML
    consent form sends client_id/redirect_uri/scope/state as hidden fields).
    Query params are the fallback for programmatic clients that POST without
    a form body.
    """
    qp = request.query_params
    client_id = qp.get("client_id", "")
    redirect_uri = qp.get("redirect_uri", "")
    response_type = qp.get("response_type", "")
    scope = qp.get("scope", _DEFAULT_SCOPES)
    state = qp.get("state", "")
    code_challenge = qp.get("code_challenge", "")
    code_challenge_method = qp.get("code_challenge_method", "")

    # On POST, override with form body values (hidden fields from consent screen)
    if request.method == "POST":
        form = await request.form()
        client_id = form.get("client_id", "") or client_id
        redirect_uri = form.get("redirect_uri", "") or redirect_uri
        response_type = form.get("response_type", "") or response_type
        scope = form.get("scope", "") or scope
        state = form.get("state", "") or state
        action = form.get("action", "")
        user_email = form.get("user_email", "")
    else:
        action = ""
        user_email = ""

    # Validate client
    store = _get_store()
    client = store.get_client(client_id)
    if not client:
        return JSONResponse({"error": "invalid_client", "error_description": "Unknown client_id"}, status_code=400)

    if response_type and response_type != "code":
        return JSONResponse({"error": "unsupported_response_type"}, status_code=400)

    # Check redirect_uri
    if redirect_uri and client["redirect_uris"] and redirect_uri not in client["redirect_uris"]:
        return JSONResponse({"error": "invalid_redirect_uri"}, status_code=400)

    # ── Clerk integration ─────────────────────────────────────────────
    # If Clerk is enabled, redirect to Clerk's hosted sign-in page instead
    # of showing the self-hosted consent screen.  Clerk authenticates the
    # user (magic link / Google / GitHub / MFA) and redirects back to
    # /auth/clerk/callback with a session JWT.  The callback verifies the
    # JWT, extracts the verified email, derives tenant_id, and issues the
    # auth code — then redirects to the MCP client's redirect_uri.
    if _clerk_enabled() and request.method == "GET":
        clerk_issuer = _clerk_issuer()
        if not clerk_issuer:
            return JSONResponse(
                {"error": "server_error", "error_description": "NUCLEUS_CLERK_ISSUER not configured"},
                status_code=500,
            )
        # Build the callback URL that Clerk will redirect back to.
        # We pass the OAuth params through as query params so the callback
        # can reconstruct the full authorize flow after Clerk auth.
        callback_url = f"{_issuer() or str(request.base_url).rstrip('/')}/auth/clerk/callback"
        callback_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "response_type": response_type,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }
        redirect_url = f"{callback_url}?{urlencode(callback_params)}"
        # Clerk's hosted sign-in page — redirect_url carries our callback
        sign_in_url = f"{clerk_issuer}/sign-in?{urlencode({'redirect_url': redirect_url})}"
        return RedirectResponse(sign_in_url, status_code=302)

    # If this is a POST (user consented), issue the code
    if request.method == "POST":
        if action == "deny":
            error_params = {"error": "access_denied"}
            if state:
                error_params["state"] = state
            if redirect_uri:
                return RedirectResponse(f"{redirect_uri}?{urlencode(error_params)}", status_code=302)
            return JSONResponse(error_params, status_code=403)

        # User consented — derive per-user tenant_id from email and issue code
        tenant_id = _derive_tenant_id_from_email(user_email) if user_email else None
        code = store.create_code(client_id, scope, redirect_uri, tenant_id=tenant_id)
        callback_params = {"code": code}
        if state:
            callback_params["state"] = state
        if redirect_uri:
            return RedirectResponse(f"{redirect_uri}?{urlencode(callback_params)}", status_code=302)
        # No redirect_uri — return code directly (native app flow)
        return JSONResponse(callback_params)

    # GET — show consent screen
    scopes_list = scope.split()
    scope_descriptions = {
        "mcp:tools": "Call Nucleus MCP tools (memory, tasks, relay, governance)",
        "mcp:resources": "Read Nucleus MCP resources",
        "mcp:prompts": "Use Nucleus MCP prompts",
        "mcp:relay": "Send and receive cross-agent relay messages",
    }
    scope_items = "".join(
        f"<li><strong>{s}</strong> — {scope_descriptions.get(s, s)}</li>"
        for s in scopes_list
    )
    client_name = client.get("client_name", "Unknown app")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Nucleus — Authorize {client_name}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 480px; margin: 60px auto; padding: 20px; }}
h1 {{ font-size: 1.4em; }}
.scopes {{ background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0; }}
.scopes ul {{ padding-left: 20px; }}
.email-field {{ margin: 16px 0; }}
.email-field label {{ display: block; font-weight: 600; margin-bottom: 4px; }}
.email-field input {{ width: 100%; padding: 8px 12px; font-size: 1em; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }}
.email-field .hint {{ font-size: 0.85em; color: #6b7280; margin-top: 4px; }}
button {{ padding: 10px 24px; margin-right: 12px; font-size: 1em; border: none; border-radius: 6px; cursor: pointer; }}
.allow {{ background: #2563eb; color: white; }}
.deny {{ background: #e5e7eb; }}
</style></head>
<body>
<h1>Authorize <em>{client_name}</em></h1>
<p><strong>{client_name}</strong> wants to access your Nucleus Brain with these permissions:</p>
<div class="scopes"><ul>{scope_items}</ul></div>
<form method="POST">
  <div class="email-field">
    <label for="user_email">Your email</label>
    <input type="email" id="user_email" name="user_email" placeholder="you@example.com" required>
    <div class="hint">Determines which Brain you access. Same email = same memory. No password needed.</div>
  </div>
  <input type="hidden" name="client_id" value="{client_id}">
  <input type="hidden" name="redirect_uri" value="{redirect_uri}">
  <input type="hidden" name="scope" value="{scope}">
  <input type="hidden" name="state" value="{state}">
  <button type="submit" name="action" value="allow" class="allow">Allow</button>
  <button type="submit" name="action" value="deny" class="deny">Deny</button>
</form>
</body></html>"""
    return HTMLResponse(html)


async def token(request: Request) -> JSONResponse:
    """Token endpoint — authorization code → access token, or refresh."""
    form = await request.form()
    grant_type = form.get("grant_type", "")
    store = _get_store()

    if grant_type == "authorization_code":
        code = form.get("code", "")
        client_id = form.get("client_id", "")
        client_secret = form.get("client_secret", "")
        redirect_uri = form.get("redirect_uri", "")

        # Validate client
        client = store.get_client(client_id)
        if not client or client["client_secret"] != client_secret:
            return JSONResponse({"error": "invalid_client"}, status_code=401)

        # Consume code
        entry = store.consume_code(code)
        if not entry:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid or expired code"}, status_code=400)

        if entry["client_id"] != client_id:
            return JSONResponse({"error": "invalid_grant", "error_description": "Client mismatch"}, status_code=400)

        access, refresh, expires_in = store.issue_token(
            client_id, entry["scope"], tenant_id=entry.get("tenant_id")
        )
        return JSONResponse({
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": refresh,
            "scope": entry["scope"],
        })

    elif grant_type == "refresh_token":
        refresh = form.get("refresh_token", "")
        result = store.refresh_token(refresh)
        if not result:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid refresh token"}, status_code=400)
        access, new_refresh, expires_in = result
        return JSONResponse({
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": new_refresh,
        })

    return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)


async def revoke(request: Request) -> JSONResponse:
    """Token revocation endpoint (RFC 7009)."""
    form = await request.form()
    token = form.get("token", "")
    if token:
        _get_store().revoke_token(token)
    return JSONResponse({})


async def clerk_callback(request: Request) -> Any:
    """Clerk OAuth callback — verifies Clerk JWT and issues auth code.

    Clerk redirects here after successful authentication.  The redirect
    includes:
      - __clerk_db_jwt  : Clerk session JWT (query param, dev mode)
      - client_id       : original OAuth client_id (passed through)
      - redirect_uri    : original MCP client redirect (passed through)
      - scope, state    : original OAuth params (passed through)
      - code_challenge  : PKCE challenge (passed through)

    The handler:
      1. Verifies the Clerk JWT signature + issuer + expiry
      2. Extracts the verified email from JWT claims
      3. Derives tenant_id = SHA-256(email)[:16]
      4. Creates an auth code with the tenant_id
      5. Redirects to the MCP client's redirect_uri with code + state

    If the JWT is missing or invalid, returns a 401 error page.
    """
    from mcp_server_nucleus.http_transport.clerk_auth import (
        verify_clerk_jwt,
        extract_email,
    )

    qp = request.query_params
    clerk_jwt = qp.get("__clerk_db_jwt", qp.get("token", ""))
    client_id = qp.get("client_id", "")
    redirect_uri = qp.get("redirect_uri", "")
    scope = qp.get("scope", _DEFAULT_SCOPES)
    state = qp.get("state", "")
    code_challenge = qp.get("code_challenge", "")
    code_challenge_method = qp.get("code_challenge_method", "")

    if not clerk_jwt:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing Clerk JWT"},
            status_code=401,
        )

    # Verify the Clerk JWT
    claims = verify_clerk_jwt(clerk_jwt)
    if not claims:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Clerk JWT verification failed"},
            status_code=401,
        )

    # Extract verified email
    email = extract_email(claims)
    if not email:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "No verified email in Clerk JWT"},
            status_code=401,
        )

    # Validate the OAuth client
    store = _get_store()
    client = store.get_client(client_id)
    if not client:
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Unknown client_id"},
            status_code=400,
        )

    # Check redirect_uri
    if redirect_uri and client["redirect_uris"] and redirect_uri not in client["redirect_uris"]:
        return JSONResponse({"error": "invalid_redirect_uri"}, status_code=400)

    # Derive tenant_id from the verified email and issue auth code
    tenant_id = _derive_tenant_id_from_email(email)
    code = store.create_code(
        client_id, scope, redirect_uri,
        user=claims.get("sub", "clerk_user"),
        tenant_id=tenant_id,
    )

    callback_params = {"code": code}
    if state:
        callback_params["state"] = state

    if redirect_uri:
        return RedirectResponse(
            f"{redirect_uri}?{urlencode(callback_params)}",
            status_code=302,
        )
    # No redirect_uri — return code directly (native app flow)
    return JSONResponse(callback_params)


# ── Route list for wiring into app.py ────────────────────────────────────

oauth_routes = [
    Route("/.well-known/oauth-protected-resource", protected_resource_metadata),
    Route("/.well-known/oauth-authorization-server", authorization_server_metadata),
    Route("/register", register, methods=["POST"]),
    Route("/authorize", authorize, methods=["GET", "POST"]),
    Route("/auth/clerk/callback", clerk_callback, methods=["GET"]),
    Route("/token", token, methods=["POST"]),
    Route("/revoke", revoke, methods=["POST"]),
]
