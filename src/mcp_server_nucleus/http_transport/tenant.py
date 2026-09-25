"""
Nucleus Tenant-Aware Middleware
================================
Resolves tenant identity from an incoming HTTP request and injects
NUCLEAR_BRAIN_PATH into the request state before any MCP tool runs.

Tenant resolution order (first match wins):
  1. Authorization: Bearer <token>  →  looked up in NUCLEUS_TENANT_MAP
  2. X-Nucleus-Tenant-ID header     →  ONLY from a verified internal hop (see below)
  3. NUCLEUS_TENANT_ID env var      →  static single-tenant fallback
  4. "default"                       →  solo-user fallback, permissive mode only

Security posture (audit ledger AU-1, TN-1, TN-2, HS-1, 2026-09-11):
  Step 2 used to accept X-Nucleus-Tenant-ID from any caller with no credential
  at all, which made every tenant's brain readable and writable by anyone who
  could reach the port, and bypassed NUCLEUS_REQUIRE_AUTH entirely because that
  gate only fired when a token was presented AND failed. The header is now
  honoured only when the request also proves it came from a trusted internal
  hop, and a request that reaches step 4 with no credential is rejected when
  NUCLEUS_REQUIRE_AUTH is set. Tenant slugs are validated against a strict
  pattern before they are ever joined into a filesystem path.

Token security:
  - Tokens can carry optional expiry: {"tok": {"tenant": "acme", "expires": "2026-12-31T00:00:00Z"}}
  - Revoked tokens listed in NUCLEUS_REVOKED_TOKENS (comma-separated or JSON array)
  - Revocation and expiry checked on every request — no server restart needed
    (NUCLEUS_TENANT_MAP and NUCLEUS_REVOKED_TOKENS are re-read per request)

Environment variables:
  NUCLEUS_BRAIN_ROOT      Base directory for all tenant brains (default: ~/.nucleus/tenants)
  NUCLEUS_TENANT_ID       Static tenant slug for single-tenant deployments
  NUCLEUS_TENANT_MAP      Token map. Two formats supported:
                            Simple:   {"token": "tenant_id"}
                            Extended: {"token": {"tenant": "tenant_id", "expires": "ISO8601"}}
                          Value can be inline JSON or a path to a JSON file.
  NUCLEUS_REVOKED_TOKENS  Comma-separated list of revoked tokens, or JSON array string.
                          Checked on every request — update without restart.
  NUCLEUS_REQUIRE_AUTH    Set to "true" to reject requests with no valid token (enterprise).
                          This now also rejects a request carrying NO credential at all,
                          which is the case it was always documented to cover.
  NUCLEUS_INTERNAL_ROUTING_SECRET
                          Shared secret proving a request came from a trusted internal hop
                          (gateway, sidecar). When set, X-Nucleus-Tenant-ID is honoured only
                          if the request also carries a matching X-Nucleus-Internal-Auth.
  NUCLEUS_TRUST_TENANT_HEADER
                          Escape hatch for deployments that terminate authentication at a
                          trusted gateway and cannot pass a shared secret. "true" restores
                          the old behaviour of honouring X-Nucleus-Tenant-ID unconditionally.
                          Do not set this on a service reachable from an untrusted network.
"""

import os
import re
import json
import hmac
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("nucleus.tenant")


# ---------------------------------------------------------------------------
# Configuration helpers (re-read per request — no restart needed)
# ---------------------------------------------------------------------------

def _brain_root() -> Path:
    root = os.environ.get("NUCLEUS_BRAIN_ROOT")
    if root:
        return Path(root)
    return Path.home() / ".nucleus" / "tenants"


def _tenant_map() -> dict:
    """Load token→tenant mapping. Re-read every call so updates take effect immediately."""
    raw = os.environ.get("NUCLEUS_TENANT_MAP", "")
    if not raw:
        return {}
    try:
        if raw.startswith("{"):
            return json.loads(raw)
        path = Path(raw)
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        logger.warning(f"[tenant] Could not parse NUCLEUS_TENANT_MAP: {e}")
    return {}


def _revoked_tokens() -> set:
    """Return the current set of revoked tokens. Re-read every call."""
    raw = os.environ.get("NUCLEUS_REVOKED_TOKENS", "").strip()
    if not raw:
        return set()
    try:
        if raw.startswith("["):
            return set(json.loads(raw))
        return set(t.strip() for t in raw.split(",") if t.strip())
    except Exception as e:
        logger.warning(f"[tenant] Could not parse NUCLEUS_REVOKED_TOKENS: {e}")
    return set()


def _require_auth() -> bool:
    return os.environ.get("NUCLEUS_REQUIRE_AUTH", "false").lower() == "true"


def _internal_routing_secret() -> str:
    return os.environ.get("NUCLEUS_INTERNAL_ROUTING_SECRET", "").strip()


def _trust_tenant_header() -> bool:
    return os.environ.get("NUCLEUS_TRUST_TENANT_HEADER", "false").lower() == "true"


# A tenant slug becomes one path segment under NUCLEUS_BRAIN_ROOT, so it must
# never contain a separator, a drive letter, or a parent reference. Everything
# this codebase actually mints already fits: "default", "oauth", the OAuth
# flow's "tenant_<16 hex>", and hand-written slugs in NUCLEUS_TENANT_MAP.
_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _is_valid_tenant_id(tenant_id) -> bool:
    """True if this slug is safe to use as a single filesystem path segment."""
    if not isinstance(tenant_id, str):
        return False
    if not _TENANT_ID_RE.match(tenant_id):
        return False
    # The pattern already excludes separators and a leading dot, but spell the
    # traversal case out so a future widening of the pattern cannot reintroduce it.
    if ".." in tenant_id or "/" in tenant_id or "\\" in tenant_id:
        return False
    return True


def _checked(tenant_id: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Gate every resolution path through slug validation."""
    if not _is_valid_tenant_id(tenant_id):
        logger.warning("[tenant] Rejected malformed tenant identifier (%d chars)",
                       len(tenant_id) if isinstance(tenant_id, str) else -1)
        return None, "Invalid tenant identifier"
    return tenant_id, None


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def _validate_token(token: str, tenant_map: dict, revoked: set) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate a Bearer token.

    Returns:
        (tenant_id, None)        — valid token
        (None, error_message)    — invalid/expired/revoked token

    Token map formats supported:
      Simple:   {"token": "tenant_id"}
      Extended: {"token": {"tenant": "tenant_id", "expires": "2026-12-31T00:00:00Z"}}
    """
    # Revocation check first
    if token in revoked:
        logger.warning(f"[tenant] Rejected revoked token: {token[:8]}...")
        return None, "Token has been revoked"

    entry = tenant_map.get(token)
    if entry is None:
        return None, "Unknown token"

    # Simple string value
    if isinstance(entry, str):
        return entry, None

    # Extended object value
    if isinstance(entry, dict):
        tenant_id = entry.get("tenant") or entry.get("tenant_id")
        if not tenant_id:
            return None, "Token map entry missing 'tenant' field"

        # Expiry check
        expires_raw = entry.get("expires")
        if expires_raw:
            try:
                expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires:
                    logger.warning(f"[tenant] Rejected expired token for tenant '{tenant_id}'")
                    return None, f"Token expired at {expires_raw}"
            except ValueError as e:
                logger.warning(f"[tenant] Could not parse token expiry '{expires_raw}': {e}")

        return tenant_id, None

    return None, f"Unexpected token map entry type: {type(entry)}"


def _validate_oauth_token(token: str, request: Optional[Request] = None) -> Optional[str]:
    """Validate an OAuth-issued bearer token (nucleus_at_*).

    Returns tenant_id on success, None on failure.

    Per-user routing: if the token entry carries a tenant_id (set during
    the OAuth authorize flow from the user's email), that tenant_id is
    returned → each user lands in their own isolated brain.

    Backward compat: if the token entry has no tenant_id (legacy tokens
    issued before per-user routing), falls back to the static
    NUCLEUS_TENANT_ID env var or "oauth" — the original single-tenant
    demo behavior.

    When ``request`` is given, the token's granted scope is recorded on
    ``request.state.nucleus_oauth_scopes`` for the middleware to enforce. The
    scope was previously read off the validation result and thrown away, which
    is what made the consent screen's permission list decorative (ledger AU-3):
    a user could grant ``mcp:resources`` alone and the token still reached
    every tool.
    """
    try:
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        result = validate_bearer(token)
        if result:
            if request is not None:
                raw_scope = result.get("scope") or ""
                request.state.nucleus_oauth_scopes = frozenset(raw_scope.split())
            # Per-user tenant routing (new path)
            tenant_id = result.get("tenant_id")
            if tenant_id:
                return tenant_id
            # Legacy fallback — static single-tenant
            return os.environ.get("NUCLEUS_TENANT_ID", "oauth")
    except Exception as e:
        logger.debug(f"[tenant] OAuth token validation failed: {e}")
    return None


# ---------------------------------------------------------------------------
# OAuth scope enforcement (ledger AU-3)
# ---------------------------------------------------------------------------
#
# Which granted scope each HTTP surface requires. A request needs ANY one of
# the listed scopes, not all of them.
#
# `mcp:tools` appears alongside `mcp:relay` on the relay routes deliberately.
# Relay send/receive is also exposed as MCP tools, so a token holding the
# default `mcp:tools` scope can already do over /mcp everything the relay
# routes do. Rejecting it here would constrain nothing and break existing
# clients. What this map does stop is a token deliberately narrowed to, say,
# `mcp:resources` reaching the tool surface.
_SCOPE_REQUIREMENTS: Tuple[Tuple[str, frozenset], ...] = (
    ("/relay", frozenset({"mcp:relay", "mcp:tools"})),
    ("/mcp-readonly", frozenset({"mcp:resources", "mcp:tools"})),
    ("/mcp", frozenset({"mcp:tools"})),
    ("/sse", frozenset({"mcp:tools"})),
)


def _scope_enforced() -> bool:
    """Whether a scope violation is a 403 or a log line.

    Default OFF, and that is not timidity — it is the same lesson AU-2 taught.
    Tokens already issued carry whatever scope their client requested, and this
    process cannot enumerate them. Turning enforcement on blind would reject
    live clients for a permission model that has never been enforced, so the
    default records violations instead. Every one is logged with the path and
    the scopes actually held, which is exactly the evidence needed to decide
    whether flipping this on is safe.

    Set NUCLEUS_OAUTH_SCOPE_ENFORCE=true once those logs are quiet.
    """
    return os.environ.get("NUCLEUS_OAUTH_SCOPE_ENFORCE", "false").lower() in (
        "1", "true", "yes", "on",
    )


def required_scopes_for_path(path: str) -> Optional[frozenset]:
    """The scopes that satisfy ``path``, or None if the path is unscoped."""
    for prefix, scopes in _SCOPE_REQUIREMENTS:
        if path == prefix or path.startswith(prefix + "/"):
            return scopes
    return None


def check_scope(request: Request) -> Optional[str]:
    """Return an error message if the request's token lacks the needed scope.

    Returns None when the request is allowed — which includes every request
    that did not arrive on an OAuth token, since scope is an OAuth concept and
    a static map token has no scope to check.
    """
    granted = getattr(request.state, "nucleus_oauth_scopes", None)
    if granted is None:
        return None
    required = required_scopes_for_path(request.url.path)
    if required is None or granted & required:
        return None

    logger.warning(
        "[tenant] OAuth scope violation on %s: token holds {%s}, needs one of {%s}%s",
        request.url.path,
        " ".join(sorted(granted)) or "none",
        " ".join(sorted(required)),
        "" if _scope_enforced() else " — allowed, NUCLEUS_OAUTH_SCOPE_ENFORCE is off",
    )
    if not _scope_enforced():
        return None
    return (
        f"Token scope does not permit {request.url.path}. "
        f"Granted: {' '.join(sorted(granted)) or 'none'}. "
        f"Required: one of {' '.join(sorted(required))}."
    )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------

def resolve_tenant(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (tenant_id, error) for this request.

    Returns (tenant_id, None) on success.
    Returns (None, error_message) on auth failure when map is configured.
    Returns ("default", None) as solo fallback when no auth is configured.
    """
    tenant_map = _tenant_map()
    revoked = _revoked_tokens()

    # 1. Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        tenant_id, error = _validate_token(token, tenant_map, revoked)
        if error:
            # An OAuth-issued token never appears in the static map, so try it
            # before treating the map miss as a failure.
            if token.startswith("nucleus_at_"):
                oauth_result = _validate_oauth_token(token, request)
                if oauth_result:
                    return _checked(oauth_result)
            if tenant_map or _require_auth():
                # A real isolation boundary exists here, so a token that does
                # not validate is a hard rejection. It previously fell through
                # to the header/env/default path whenever no map was configured.
                return None, error
            # Solo, permissive deployment: one brain, no boundary to breach.
            # Keep the old lenient behaviour so a local user who sends a stray
            # Authorization header is not locked out of their own machine.
            logger.warning(
                "[tenant] Ignoring unrecognised bearer token in solo permissive mode. "
                "Configure NUCLEUS_TENANT_MAP or NUCLEUS_REQUIRE_AUTH to reject it."
            )
        else:
            return _checked(tenant_id)

    # 2. Explicit tenant header — a routing hint from a trusted internal hop,
    #    never an identity claim from an arbitrary caller.
    tenant_header = request.headers.get("X-Nucleus-Tenant-ID", "").strip()
    if tenant_header:
        secret = _internal_routing_secret()
        if secret:
            presented = request.headers.get("X-Nucleus-Internal-Auth", "")
            if hmac.compare_digest(presented, secret):
                return _checked(tenant_header)
            logger.warning("[tenant] X-Nucleus-Tenant-ID presented with a bad internal credential")
            return None, "Invalid internal routing credential"
        if _trust_tenant_header():
            return _checked(tenant_header)
        # Fail closed rather than silently dropping the caller into "default".
        # Silently ignoring the header would merge every tenant of a gateway
        # deployment into one brain, which is worse than a visible 401.
        logger.warning(
            "[tenant] Rejected X-Nucleus-Tenant-ID: no internal routing credential configured"
        )
        return None, (
            "X-Nucleus-Tenant-ID is not honoured without proof the request came from a "
            "trusted internal hop. Set NUCLEUS_INTERNAL_ROUTING_SECRET and send a matching "
            "X-Nucleus-Internal-Auth header, or set NUCLEUS_TRUST_TENANT_HEADER=true if this "
            "deployment terminates authentication at a gateway you control."
        )

    # 3. Static env override
    env_tenant = os.environ.get("NUCLEUS_TENANT_ID", "").strip()
    if env_tenant:
        return _checked(env_tenant)

    # 4. Solo fallback — only for a deployment with no isolation boundary at all.
    #
    # A configured NUCLEUS_TENANT_MAP is proof the deployment is multi-tenant, so
    # a request carrying no credential must not land in the shared "default" brain
    # just because NUCLEUS_REQUIRE_AUTH happens to be unset. That was the residual
    # hole behind RL-2: /engrams/sync and the other data routes trust the tenant the
    # middleware resolves, and an anonymous caller was resolving to a real one.
    #
    # Solo deployments — no map, no required auth — keep working untouched. There is
    # one brain and no boundary to breach.
    if _require_auth() or tenant_map:
        return None, "Authentication required"
    return "default", None


def _seed_welcome_engram(brain: Path) -> None:
    """Seed a welcome engram into a freshly-created tenant brain.

    Implements the "Mitigation 2" recommendation from
    CHATGPT_FIRST_RUN_ONBOARDING.md: on first brain creation, seed one
    engram so the user's first search_engrams call returns a meaningful
    result instead of an empty-brain moment that feels broken.
    """
    from datetime import datetime, timezone
    ledger = brain / "engrams" / "ledger.jsonl"
    if ledger.exists() and ledger.stat().st_size > 0:
        return  # already has content — don't re-seed
    now = datetime.now(timezone.utc).isoformat()
    welcome = {
        "key": "onboarding_welcome",
        "value": (
            "Welcome to Nucleus. This is your sovereign memory — it "
            "persists across all your conversations. Ask me to remember "
            "anything: preferences, decisions, project context, contacts. "
            "Then start a new chat and ask me what I know about you."
        ),
        "context": "Feature",
        "intensity": 3,
        "version": 1,
        "source_agent": "nucleus_onboarding",
        "op_type": "ADD",
        "timestamp": now,
        "deleted": False,
        "signature": None,
    }
    try:
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(welcome, ensure_ascii=False) + "\n")
        logger.info(f"[tenant] Seeded welcome engram for new brain at {brain}")
    except Exception as e:
        logger.warning(f"[tenant] Could not seed welcome engram: {e}")


def brain_path_for_tenant(tenant_id: str) -> Path:
    """
    Return (and create if needed) the .brain path for a given tenant.
    Each tenant is fully isolated under NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain

    On first creation, seeds a welcome engram so the user's initial
    search_engrams call returns a meaningful result (per
    CHATGPT_FIRST_RUN_ONBOARDING.md Mitigation 2).
    """
    if not _is_valid_tenant_id(tenant_id):
        raise ValueError("Refusing to build a brain path for an invalid tenant identifier")

    root = _brain_root().resolve()
    brain = (root / tenant_id / ".brain")

    # Defence in depth. The slug pattern already forbids separators and parent
    # references, so this can only fire if that pattern is ever widened — which
    # is exactly when a traversal would otherwise come back unnoticed.
    resolved = brain.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("Refusing to build a brain path outside the tenant root")

    if not brain.exists():
        brain.mkdir(parents=True, exist_ok=True)
        for subdir in [
            "engrams", "ledger", "sessions", "memory",
            "tasks", "artifacts", "proofs", "strategy",
            "governance", "channels", "federation",
            "deltas", "training", "meta", "driver",
        ]:
            (brain / subdir).mkdir(exist_ok=True)
        _seed_welcome_engram(brain)
        logger.info(f"[tenant] Created brain for tenant '{tenant_id}' at {brain}")
    return brain


# ---------------------------------------------------------------------------
# Starlette middleware
# ---------------------------------------------------------------------------

class NucleusTenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant from each request and sets the per-request brain path
    via a contextvar (async-safe) AND the process environment (backward
    compat for modules that read os.environ directly).

    Sets:
      request.state.nucleus_tenant_id  — resolved tenant slug
      request.state.nucleus_brain_path — absolute path to tenant brain
      _tenant_brain_path contextvar    — async-safe per-request brain path
      os.environ NUCLEUS_BRAIN_PATH    — process-wide (backward compat)
      os.environ NUCLEAR_BRAIN_PATH    — process-wide (legacy alias)

    Response headers added:
      X-Nucleus-Tenant — resolved tenant slug (useful for debugging)

    Concurrency note:
      The contextvar is the primary isolation mechanism and is async-safe:
      each request's async task keeps its own value across await points,
      so concurrent multi-tenant requests on a single process do NOT
      cross-read each other's brains via get_brain_path().

      os.environ is still set as a backward-compat fallback for modules
      that read it directly instead of calling get_brain_path(). This env
      var DOES race under concurrent multi-tenant load — those direct
      readers should be migrated to get_brain_path() over time. The
      security-critical paths (engram_ops, relay/paths, sync_ops) all
      route through get_brain_path() and are therefore race-free.
    """

    async def dispatch(self, request: Request, call_next):
        # Public endpoints — skip tenant resolution + auth
        # .well-known/* per RFC 8414/9728 + OpenAI domain verification
        # /authorize, /token, /register per OAuth 2.1 + MCP DCR spec
        if (request.url.path in ("/health", "/ready", "/")
                or request.url.path.startswith("/.well-known/")
                or request.url.path in ("/authorize", "/token", "/register", "/revoke",
                                         "/auth/clerk/callback")):
            return await call_next(request)

        tenant_id, error = resolve_tenant(request)

        # Any resolution error is a rejection, in permissive mode too. Falling
        # back to "default" here was how a bad credential, or an untrusted
        # tenant header, quietly became access to the default brain.
        if tenant_id is None:
            return JSONResponse(
                {"error": "Unauthorized", "detail": error or "Valid credentials required"},
                status_code=401,
            )

        # Scope is checked after identity and before any brain is resolved:
        # an insufficiently-scoped token is authenticated but not authorised,
        # so it gets 403, not 401, and never reaches a brain path (AU-3).
        scope_error = check_scope(request)
        if scope_error is not None:
            return JSONResponse(
                {"error": "Forbidden", "detail": scope_error},
                status_code=403,
            )

        try:
            brain = brain_path_for_tenant(tenant_id)
        except ValueError as e:
            logger.warning("[tenant] Refused brain path for resolved tenant: %s", e)
            return JSONResponse(
                {"error": "Bad Request", "detail": "Invalid tenant identifier"},
                status_code=400,
            )

        # Primary: async-safe contextvar (checked first by get_brain_path)
        from mcp_server_nucleus.runtime.common import set_tenant_brain_path
        set_tenant_brain_path(str(brain))

        # Backward compat: process-wide env vars. These DO race under
        # concurrent multi-tenant load, but get_brain_path() checks the
        # contextvar first so callers that route through it are safe.
        # Set BOTH the canonical NUCLEUS_BRAIN_PATH (read by common.get_brain_path
        # and the majority of the runtime) and the legacy NUCLEAR_BRAIN_PATH
        # (still read by stdio_server.py and a few older modules). Setting only
        # the legacy name was the root cause of a cross-tenant data leak: the
        # tenant middleware pointed at tenant B's brain, but get_brain_path()
        # fell back to the dev's ~/.brain because the canonical var was unset.
        # Saved so the finally block can put them back. Leaving the last
        # request's tenant path in the process environment after the response
        # meant any later code path that read os.environ instead of
        # get_brain_path() saw a stale tenant's brain (ledger TN-5).
        _prev_env = {
            "NUCLEUS_BRAIN_PATH": os.environ.get("NUCLEUS_BRAIN_PATH"),
            "NUCLEAR_BRAIN_PATH": os.environ.get("NUCLEAR_BRAIN_PATH"),
        }
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)

        request.state.nucleus_tenant_id = tenant_id
        request.state.nucleus_brain_path = str(brain)

        logger.debug(
            f"[tenant] {request.method} {request.url.path} "
            f"→ tenant={tenant_id} brain={brain}"
        )

        try:
            response = await call_next(request)
            response.headers["X-Nucleus-Tenant"] = tenant_id
            return response
        finally:
            # Clear the contextvar to prevent leakage across requests.
            # Without this, a subsequent request that bypasses the
            # middleware (e.g. a public endpoint) could inherit the
            # previous tenant's brain path.
            set_tenant_brain_path(None)
            # Same reasoning for the process-wide fallbacks. These still race
            # under concurrent multi-tenant load — the contextvar is the real
            # isolation mechanism — but a stale value must not outlive the
            # request that set it.
            for _key, _prev in _prev_env.items():
                if _prev is None:
                    os.environ.pop(_key, None)
                else:
                    os.environ[_key] = _prev
