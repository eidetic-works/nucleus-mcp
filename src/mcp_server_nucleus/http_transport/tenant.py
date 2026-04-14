"""
Nucleus Tenant-Aware Middleware
================================
Resolves tenant identity from an incoming HTTP request and injects
NUCLEUS_BRAIN_PATH into the request state before any MCP tool runs.

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
                # Map exists — token failure is a hard rejection
                return None, error
            # No map — unknown token is ignored, fall through
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


def brain_path_for_tenant(tenant_id: str) -> Path:
    """
    Return (and create if needed) the .brain path for a given tenant.
    Each tenant is fully isolated under NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain
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
        logger.info(f"[tenant] Created brain for tenant '{tenant_id}' at {brain}")
    return brain


# ---------------------------------------------------------------------------
# Starlette middleware
# ---------------------------------------------------------------------------

class NucleusTenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant from each request and sets NUCLEUS_BRAIN_PATH
    in the process environment so all Nucleus runtime ops pick it up.

    Also sets:
      request.state.nucleus_tenant_id  — resolved tenant slug
      request.state.nucleus_brain_path — absolute path to tenant brain

    Response headers added:
      X-Nucleus-Tenant — resolved tenant slug (useful for debugging)

    Concurrency note:
      os.environ mutation is process-wide. Safe for single-threaded async
      (uvicorn default). For true parallel multi-tenant isolation, run
      one process per tenant (recommended for enterprise/high-load).
      Brain path isolation is still enforced correctly per request.
    """

    async def dispatch(self, request: Request, call_next):
        # Health/readiness/root probes — skip tenant resolution
        if request.url.path in ("/health", "/ready", "/"):
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

        # Inject into environment so all runtime functions pick it up
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)

        request.state.nucleus_tenant_id = tenant_id
        request.state.nucleus_brain_path = str(brain)

        logger.debug(
            f"[tenant] {request.method} {request.url.path} "
            f"→ tenant={tenant_id} brain={brain}"
        )

        response = await call_next(request)
        response.headers["X-Nucleus-Tenant"] = tenant_id
        return response
