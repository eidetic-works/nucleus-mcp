"""
Nucleus Tenant-Aware Middleware
================================
Resolves tenant identity from an incoming HTTP request and injects
NUCLEAR_BRAIN_PATH into the request state before any MCP tool runs.

Tenant resolution order (first match wins):
  1. Authorization: Bearer <token>  →  looked up in NUCLEUS_TENANT_MAP
  2. X-Nucleus-Tenant-ID header     →  used directly as tenant slug
  3. NUCLEUS_TENANT_ID env var      →  static single-tenant fallback
  4. "default"                       →  solo-user fallback (no auth)

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
  NUCLEUS_REQUIRE_AUTH    Set to "true" to reject requests with no valid token (enterprise)
"""

import os
import json
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


def _validate_oauth_token(token: str) -> Optional[str]:
    """Validate an OAuth-issued bearer token (nucleus_at_*).

    Returns tenant_id on success, None on failure.

    Per-user routing: if the token entry carries a tenant_id (set during
    the OAuth authorize flow from the user's email), that tenant_id is
    returned → each user lands in their own isolated brain.

    Backward compat: if the token entry has no tenant_id (legacy tokens
    issued before per-user routing), falls back to the static
    NUCLEUS_TENANT_ID env var or "oauth" — the original single-tenant
    demo behavior.
    """
    try:
        from mcp_server_nucleus.http_transport.oauth_server import validate_bearer
        result = validate_bearer(token)
        if result:
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
            if tenant_map:
                # Map exists — token failure is a hard rejection, UNLESS this
                # is an OAuth-issued token (nucleus_at_*) — try OAuth validation
                if token.startswith("nucleus_at_"):
                    oauth_result = _validate_oauth_token(token)
                    if oauth_result:
                        return oauth_result, None
                return None, error
            # No map — unknown token is ignored, fall through to OAuth check
            # (enables OAuth without a static tenant map)
            if token.startswith("nucleus_at_"):
                oauth_result = _validate_oauth_token(token)
                if oauth_result:
                    return oauth_result, None
        else:
            return tenant_id, None

    # 2. Explicit tenant header (trusted internal routing)
    tenant_header = request.headers.get("X-Nucleus-Tenant-ID", "").strip()
    if tenant_header:
        return tenant_header, None

    # 3. Static env override
    env_tenant = os.environ.get("NUCLEUS_TENANT_ID", "").strip()
    if env_tenant:
        return env_tenant, None

    # 4. Solo fallback
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
    brain = _brain_root() / tenant_id / ".brain"
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

        if tenant_id is None:
            if _require_auth():
                return JSONResponse(
                    {"error": "Unauthorized", "detail": error or "Valid Bearer token required"},
                    status_code=401,
                )
            # Permissive mode — fall back to default
            tenant_id = "default"

        brain = brain_path_for_tenant(tenant_id)

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
