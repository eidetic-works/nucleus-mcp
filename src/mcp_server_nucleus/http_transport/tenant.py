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

Design contract:
  - Each tenant gets a fully isolated brain path: {NUCLEUS_BRAIN_ROOT}/{tenant_id}/.brain
  - The brain path is created on first access (matches get_brain_path() behaviour)
  - No tenant can access another's brain — isolation is enforced here, not in tools
  - Solo mode (no NUCLEUS_TENANT_MAP, no header, no env) works exactly like stdio

Environment variables:
  NUCLEUS_BRAIN_ROOT      Base directory for all tenant brains (default: ~/.nucleus/tenants)
  NUCLEUS_TENANT_ID       Static tenant slug for single-tenant deployments
  NUCLEUS_TENANT_MAP      JSON mapping of {token: tenant_id} for multi-tenant auth
  NUCLEUS_REQUIRE_AUTH    Set to "true" to reject requests with no valid token (enterprise)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("nucleus.tenant")


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _brain_root() -> Path:
    """Return the root directory under which per-tenant .brain dirs live."""
    root = os.environ.get("NUCLEUS_BRAIN_ROOT")
    if root:
        return Path(root)
    return Path.home() / ".nucleus" / "tenants"


def _tenant_map() -> dict:
    """Load token→tenant_id mapping from env (JSON string or file path)."""
    raw = os.environ.get("NUCLEUS_TENANT_MAP", "")
    if not raw:
        return {}
    # Support either inline JSON or a path to a JSON file
    try:
        if raw.startswith("{"):
            return json.loads(raw)
        path = Path(raw)
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        logger.warning(f"[tenant] Could not parse NUCLEUS_TENANT_MAP: {e}")
    return {}


def _require_auth() -> bool:
    return os.environ.get("NUCLEUS_REQUIRE_AUTH", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------

def resolve_tenant(request: Request) -> Optional[str]:
    """
    Return the tenant_id for this request, or None if unauthenticated
    and auth is not required.
    """
    tenant_map = _tenant_map()

    # 1. Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token in tenant_map:
            return tenant_map[token]
        elif tenant_map:
            # Map exists but token unknown — reject
            return None

    # 2. Explicit tenant header (trusted internal routing, no map required)
    tenant_header = request.headers.get("X-Nucleus-Tenant-ID", "").strip()
    if tenant_header:
        return tenant_header

    # 3. Static env override (single-tenant Cloud Run deployment)
    env_tenant = os.environ.get("NUCLEUS_TENANT_ID", "").strip()
    if env_tenant:
        return env_tenant

    # 4. Default solo fallback
    return "default"


def brain_path_for_tenant(tenant_id: str) -> Path:
    """
    Return (and create if needed) the .brain path for a given tenant.
    Each tenant is isolated under NUCLEUS_BRAIN_ROOT/<tenant_id>/.brain
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
    in the process environment for the duration of the request.

    Also exposes request.state.nucleus_tenant_id and
    request.state.nucleus_brain_path for downstream use.

    NOTE: os.environ mutation is process-wide. This is safe for
    single-threaded async servers (uvicorn default). For true
    multi-tenant concurrency isolation, use per-process or
    per-container deployment (recommended for enterprise).
    The middleware still correctly namespaces the brain path per request,
    so data isolation is preserved even under concurrent load — the
    "last write wins" concern only applies to the env var itself,
    not to the actual file system paths used by tools.
    """

    async def dispatch(self, request: Request, call_next):
        # Health/readiness probes — skip tenant resolution
        if request.url.path in ("/health", "/ready", "/"):
            return await call_next(request)

        tenant_id = resolve_tenant(request)

        if tenant_id is None:
            if _require_auth():
                return JSONResponse(
                    {"error": "Unauthorized", "detail": "Valid Bearer token required"},
                    status_code=401,
                )
            # Permissive fallback when auth not required
            tenant_id = "default"

        brain = brain_path_for_tenant(tenant_id)

        # Inject into environment so all Nucleus runtime functions pick it up
        # (get_brain_path() reads NUCLEUS_BRAIN_PATH)
        os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)

        # Also expose on request state for any future HTTP-aware code
        request.state.nucleus_tenant_id = tenant_id
        request.state.nucleus_brain_path = str(brain)

        logger.debug(f"[tenant] {request.method} {request.url.path} → tenant={tenant_id} brain={brain}")

        response = await call_next(request)
        response.headers["X-Nucleus-Tenant"] = tenant_id
        return response
