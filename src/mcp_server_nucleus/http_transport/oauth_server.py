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

Tenancy, decided (audit ledger AU-2): the self-hosted consent path is
SINGLE-TENANT. It does not verify email and will not be taught to — everyone
who completes it reaches the same brain. Verified per-user tenants require
Clerk. An operator on a closed network who wants the old email-keyed routing
can set NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL=true and gets a consent screen
that says the address is unverified.

Env contract:
  NUCLEUS_OAUTH_ENABLED       Three states. "false" CLOSES the endpoints below
                              (404) — a kill switch this server did not
                              previously have. "true" serves them. Unset
                              serves them and logs one warning per process,
                              because a deployment that never set it is
                              already relying on them and must not be broken
                              by an upgrade. It previously changed nothing but
                              what the `/` endpoint reported.
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

import functools
import base64
import hashlib
import hmac
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


def _oauth_enabled() -> bool:
    """Whether the OAuth endpoints are served. Three states, not two.

    ``True``/``False`` when the operator set the variable, ``None`` when they
    never did. The third state matters — see ``_gated``.

    Read per request, not at import, so a deployment can flip it without a
    rebuild and so tests can exercise every side.
    """
    raw = os.environ.get("NUCLEUS_OAUTH_ENABLED")
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _gated(handler):
    """Gate ``handler`` on NUCLEUS_OAUTH_ENABLED, honouring "never set" as its own case.

    The flag used to control nothing but what the ``/`` root endpoint reported
    (app.py:118). The routes themselves were inserted unconditionally, so
    /register, /authorize and /token answered on every deployment — including
    ones whose operator had read the env contract ("true" to enable OAuth on the
    MCP endpoint) and believed OAuth was off. Dynamic client registration takes
    no auth, so a caller could self-register a client, consent to themselves and
    walk out with a bearer token for the default brain (audit ledger AU-2).

    The obvious fix — serve only when the variable is true — would have been a
    production outage. Checked against the live relay on 2026-09-11: ``GET /``
    returns ``"oauth_enabled": false`` while ``/.well-known/oauth-protected-resource``
    and ``/.well-known/oauth-authorization-server`` both return 200. The variable
    is not set there, and Connector sign-in works *because* of the bug. Two
    submission docs claimed the opposite; they have been corrected. A two-state
    gate would have 404'd ChatGPT and Claude.ai sign-in the moment it shipped.

    So the variable is read as three states:

    ``false`` (explicit)
        404. A real kill switch, which this deployment never had — an operator
        who wants the surface closed can now close it.
    ``true`` (explicit)
        Served, silently. The documented contract, unchanged.
    unset
        Served, with a warning logged once per process naming the variable.
        A deployment that never expressed an intent is not one whose intent we
        can infer, and silently breaking it is worse than the gap being closed.
        The warning is what makes this state non-silent, which was the actual
        complaint in AU-2: an operator could not tell the surface was live.

    Gating here rather than at insertion time in app.py keeps the route-index
    arithmetic in that module untouched; an unreachable endpoint and a 404 are
    the same thing to a caller. The 404 body names the variable so the closed
    state is diagnosable rather than mysterious.
    """

    @functools.wraps(handler)
    async def _guarded(request: Request) -> Any:
        state = _oauth_enabled()
        if state is False:
            return JSONResponse(
                {
                    "error": "oauth_disabled",
                    "error_description": (
                        "OAuth is disabled on this deployment "
                        "(NUCLEUS_OAUTH_ENABLED is set to a false value). "
                        "Set NUCLEUS_OAUTH_ENABLED=true to serve these endpoints."
                    ),
                },
                status_code=404,
            )
        if state is None:
            _warn_oauth_unconfigured()
        return await handler(request)

    return _guarded


_warned_oauth_unconfigured = False


def _warn_oauth_unconfigured() -> None:
    """Say once per process that the OAuth surface is live but never configured.

    Once, not per request: this is a deployment fact, and a public endpoint
    would otherwise let any caller drive the log volume.
    """
    global _warned_oauth_unconfigured
    if _warned_oauth_unconfigured:
        return
    _warned_oauth_unconfigured = True
    logger.warning(
        "[oauth] The OAuth endpoints (/register, /authorize, /token) are being served, "
        "but NUCLEUS_OAUTH_ENABLED is not set. Dynamic client registration takes no auth, "
        "so any caller who can reach this deployment can register a client and obtain a "
        "token. Set NUCLEUS_OAUTH_ENABLED=true to confirm this is intended, or =false to "
        "close the surface."
    )


def _require_pkce() -> bool:
    """Whether an authorization code must be bound to a PKCE challenge.

    Default off. Turning it on rejects any client that does not send a
    ``code_challenge``, and this server has been accepting such clients since it
    shipped, so requiring it by default would break them. With it off, a client
    that *does* use PKCE now gets the protection it asked for — which is the
    actual defect: the challenge was accepted, advertised as supported, and then
    never checked (ledger AU-5).
    """
    return os.environ.get("NUCLEUS_OAUTH_REQUIRE_PKCE", "false").lower() in (
        "1", "true", "yes", "on",
    )


def _check_pkce(entry: Dict[str, Any], code_verifier: str) -> Optional[str]:
    """Verify a PKCE code_verifier against a stored challenge.

    Returns an error string to reject with, or None to allow.

    Only S256 is accepted, which is exactly what
    ``/.well-known/oauth-authorization-server`` advertises. ``plain`` is
    deliberately not supported: it offers no protection against an attacker who
    can read the authorization request, and advertising S256 while honouring
    plain would let a downgrade undo the whole mechanism.
    """
    challenge = entry.get("code_challenge") or ""
    method = (entry.get("code_challenge_method") or "").upper()

    if not challenge:
        if _require_pkce():
            return (
                "PKCE is required on this deployment: the authorization request "
                "carried no code_challenge."
            )
        # No challenge was ever supplied, so there is nothing to bind to. This
        # is the pre-existing behaviour for clients that do not use PKCE.
        return None

    if not code_verifier:
        return "code_verifier is required because the authorization request used PKCE."

    # RFC 7636 §4.1 — the verifier is 43-128 characters from an unreserved set.
    if not (43 <= len(code_verifier) <= 128):
        return "code_verifier must be 43-128 characters."

    if method and method != "S256":
        return f"Unsupported code_challenge_method {method!r}; only S256 is supported."

    expected = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    if not hmac.compare_digest(expected, challenge):
        return "code_verifier does not match the code_challenge."
    return None


def _clerk_enabled() -> bool:
    return os.environ.get("NUCLEUS_CLERK_ENABLED", "false").lower() == "true"


def _clerk_issuer() -> str:
    return os.environ.get("NUCLEUS_CLERK_ISSUER", "").rstrip("/")


def _allow_unverified_email_tenants() -> bool:
    """Whether /authorize may bind a tenant to a self-asserted email address.

    Default off. The self-hosted consent screen takes an email from a plain
    text input with, in its own words, "no password needed", so honouring it
    as a tenant claim hands any caller a token for any address they can type.
    Operators who genuinely want the old behaviour on a closed network can
    set NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL=true.
    """
    return os.environ.get("NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL", "false").lower() == "true"


def _derive_tenant_id_from_email(email: str) -> str:
    """Derive a deterministic tenant slug from an email address.

    Same email → same tenant_id every time, so a user who re-authorizes
    lands in the same brain.  No PII in the slug — just the first 16 hex
    chars of the SHA-256 hash.

    This is an identity *claim*, not a verified identity. The old TODO here
    asked for a magic-link verifier on the self-hosted path; that is not being
    built. Clerk already verifies the address and calls this from
    /auth/clerk/callback, and a second home-grown verifier would be a second
    thing to get wrong for a deployment shape (self-hosted multi-tenant) that
    the rest of this module does not support anyway — DCR takes no auth, and
    the store is in-process. The supported answers are: Clerk for verified
    per-user tenants, or a single shared brain (audit ledger AU-2).

    So the only callers that may reach this are ones holding a *verified*
    address: the Clerk callback, or the self-hosted path when an operator has
    explicitly set NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL on a closed network.
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
        code_challenge: str = "",
        code_challenge_method: str = "",
    ) -> str:
        """Mint an authorization code, binding it to a PKCE challenge if given.

        The challenge used to be read at /authorize and dropped on the floor —
        never stored, never checked at /token (ledger AU-5). The metadata
        endpoint advertised S256 support the whole time. An intercepted code
        could therefore be redeemed by anyone, which is the exact attack PKCE
        exists to stop, and open dynamic client registration meant the
        client_secret check on /token did not distinguish a real app from an
        attacker who had just registered one.
        """
        code = secrets.token_urlsafe(32)
        self.codes[code] = {
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "user": user,
            "tenant_id": tenant_id,
            "code_challenge": code_challenge or "",
            "code_challenge_method": (code_challenge_method or "").upper(),
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
        logger.debug("Swallowed exception in register", exc_info=True)
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
        # Carried as hidden fields by the consent form. Without these the
        # challenge a client sent to GET /authorize would be lost across the
        # consent POST, and the code would be minted unbound — PKCE silently
        # dropped on exactly the path most users take (ledger AU-5).
        code_challenge = form.get("code_challenge", "") or code_challenge
        code_challenge_method = (
            form.get("code_challenge_method", "") or code_challenge_method
        )
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

        # User consented — derive per-user tenant_id from email and issue code.
        #
        # The email here is typed into an unauthenticated form; nothing has
        # verified the caller owns it. Binding a tenant to it let anyone mint a
        # standing token for any victim's brain by typing their address
        # (audit ledger AU-2). The Clerk path at /auth/clerk/callback does
        # verify the address and still binds a tenant; this self-hosted path
        # now refuses to unless the operator has explicitly accepted the risk.
        #
        # With no binding the code carries tenant_id=None, and _validate_oauth_token
        # falls back to the documented single-tenant behaviour (NUCLEUS_TENANT_ID,
        # else "oauth") — so the flow keeps working, it just stops handing out
        # other people's tenants.
        tenant_id = None
        if user_email:
            if _allow_unverified_email_tenants():
                tenant_id = _derive_tenant_id_from_email(user_email)
                logger.warning(
                    "[oauth] Bound tenant from an UNVERIFIED email claim because "
                    "NUCLEUS_OAUTH_ALLOW_UNVERIFIED_EMAIL is set. Anyone who can reach "
                    "/authorize can claim any address. Enable Clerk for verified sign-in."
                )
            else:
                logger.info(
                    "[oauth] Ignoring self-asserted email for tenant routing; issuing a "
                    "single-tenant code. Enable Clerk for verified per-user tenants."
                )
        code = store.create_code(
            client_id, scope, redirect_uri, tenant_id=tenant_id,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
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

    # The email field used to promise "Same email = same memory. No password
    # needed." That promise is now only true on the path that honours the claim,
    # and that path is off by default (AU-2). Saying it anyway would be a false
    # statement on the screen a user reads before granting access, so the field
    # is only rendered when the deployment actually routes on it — and when it
    # does, the screen says plainly that nothing verifies the address.
    #
    # With the field absent the POST handler sees user_email="" and issues a
    # single-tenant code, which is what this deployment shape means: one brain,
    # shared by everyone who can complete the flow. Clerk is the supported way
    # to get verified per-user tenants; see the module docstring.
    if _allow_unverified_email_tenants():
        email_field = """
  <div class="email-field">
    <label for="user_email">Your email</label>
    <input type="email" id="user_email" name="user_email" placeholder="you@example.com" required>
    <div class="hint"><strong>Not verified.</strong> This deployment routes you to a
    Brain based on whatever address you type here, and nothing checks that it is
    yours. Only use this on a network where you trust every caller.</div>
  </div>"""
    else:
        email_field = """
  <div class="email-field">
    <div class="hint">This deployment serves a <strong>single shared Brain</strong>.
    Everyone who completes this flow reaches the same memory. Per-user Brains
    require verified sign-in (Clerk).</div>
  </div>"""

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
<form method="POST">{email_field}
  <input type="hidden" name="client_id" value="{client_id}">
  <input type="hidden" name="redirect_uri" value="{redirect_uri}">
  <input type="hidden" name="scope" value="{scope}">
  <input type="hidden" name="state" value="{state}">
  <input type="hidden" name="code_challenge" value="{code_challenge}">
  <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
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

        pkce_error = _check_pkce(entry, form.get("code_verifier", ""))
        if pkce_error:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": pkce_error},
                status_code=400,
            )

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
        # Round-tripped through the Clerk redirect as callback params, so the
        # verified-sign-in path binds the code the same way the self-hosted one
        # does. Dropping it here would leave Clerk users with unbound codes.
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
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

# Every one of these goes through _gated: with NUCLEUS_OAUTH_ENABLED unset the
# whole surface answers 404, including the discovery metadata, so a disabled
# deployment does not advertise an authorization server it will not honour.
oauth_routes = [
    Route("/.well-known/oauth-protected-resource", _gated(protected_resource_metadata)),
    Route("/.well-known/oauth-authorization-server", _gated(authorization_server_metadata)),
    Route("/register", _gated(register), methods=["POST"]),
    Route("/authorize", _gated(authorize), methods=["GET", "POST"]),
    Route("/auth/clerk/callback", _gated(clerk_callback), methods=["GET"]),
    Route("/token", _gated(token), methods=["POST"]),
    Route("/revoke", _gated(revoke), methods=["POST"]),
]
