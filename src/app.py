"""
Nucleus Sovereign Agent OS — Cloud Run Entrypoint (Option 2)
=============================================================
Mounts the Nucleus MCP ASGI app on a production-grade Starlette/uvicorn
server suitable for Cloud Run, Fly.io, Railway, or any container platform.

Key design decisions:
  - Tenant-aware from day one (see http_transport/tenant.py)
  - Single binary supports solo (NUCLEUS_TENANT_ID) AND multi-tenant
    (NUCLEUS_TENANT_MAP) deployments — just change env vars
  - Health and readiness probes at /health and /ready (Cloud Run compatible)
  - MCP endpoint at /mcp (streamable-http) or /sse (SSE)
  - Jurisdiction-aware: NUCLEUS_JURISDICTION controls governance policy

Environment variables:
  PORT                     Cloud Run injects this (default: 8080)
  NUCLEUS_TRANSPORT        streamable-http | sse (default: streamable-http)
  NUCLEUS_BRAIN_ROOT       Root for per-tenant brain dirs
  NUCLEUS_TENANT_ID        Static tenant slug (single-tenant mode)
  NUCLEUS_TENANT_MAP       JSON {token: tenant_id} (multi-tenant mode)
  NUCLEUS_REQUIRE_AUTH     "true" to enforce auth (recommended for cloud)
  NUCLEUS_JURISDICTION     e.g. "eu-dora", "global-default"
  NUCLEAR_BRAIN_PATH       Override brain path directly (solo/stdio compat)

Deployment:
  docker build -t nucleus-mcp .
  docker run -p 8080:8080 \
    -e NUCLEUS_TENANT_ID=myorg \
    -e NUCLEAR_BRAIN_PATH=/app/.brain \
    -v ./brain:/app/.brain \
    nucleus-mcp http

  # Multi-tenant (SaaS mode):
  docker run -p 8080:8080 \
    -e NUCLEUS_BRAIN_ROOT=/app/tenants \
    -e NUCLEUS_TENANT_MAP='{"tok_abc":"acme","tok_xyz":"globex"}' \
    -e NUCLEUS_REQUIRE_AUTH=true \
    -v ./tenants:/app/tenants \
    nucleus-mcp http
"""

import os
import sys
import json
import logging
import time

# ---------------------------------------------------------------------------
# Logging — suppress startup noise before any Nucleus import
# ---------------------------------------------------------------------------
_log_level = os.environ.get("NUCLEUS_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.WARNING),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nucleus.cloud")

os.environ["FASTMCP_SHOW_CLI_BANNER"] = "False"
os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"

# ---------------------------------------------------------------------------
# Import shared MCP instance
# ---------------------------------------------------------------------------
from mcp_server_nucleus import mcp, __version__
from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware

# ---------------------------------------------------------------------------
# Build the ASGI app
# ---------------------------------------------------------------------------
_transport = os.environ.get("NUCLEUS_TRANSPORT", "streamable-http")
_mcp_path = "/sse" if _transport == "sse" else "/mcp"

# Get the fastmcp Starlette app
_mcp_app = mcp.http_app(transport=_transport, path=_mcp_path)

# Inject tenant middleware
_mcp_app.add_middleware(NucleusTenantMiddleware)

# ---------------------------------------------------------------------------
# Add Cloud Run compatible health routes
# ---------------------------------------------------------------------------
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse

_start_time = time.time()


async def health(request: Request):
    """Liveness probe — always returns 200 if the process is alive."""
    return JSONResponse({
        "status": "ok",
        "version": __version__,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "jurisdiction": os.environ.get("NUCLEUS_JURISDICTION", "global-default"),
        "transport": _transport,
        "mcp_endpoint": _mcp_path,
    })


async def ready(request: Request):
    """Readiness probe — checks brain path is accessible."""
    try:
        from mcp_server_nucleus.runtime.common import get_brain_path
        brain = get_brain_path()
        accessible = brain.exists()
    except Exception as e:
        return JSONResponse(
            {"status": "not_ready", "error": str(e)},
            status_code=503,
        )
    if not accessible:
        return JSONResponse(
            {"status": "not_ready", "detail": "Brain path not accessible"},
            status_code=503,
        )
    return JSONResponse({"status": "ready", "brain": str(brain)})


async def root(request: Request):
    """Root — identity card for this Nucleus instance."""
    tenant_map_configured = bool(os.environ.get("NUCLEUS_TENANT_MAP"))
    tenant_id = os.environ.get("NUCLEUS_TENANT_ID")
    mode = "multi-tenant" if tenant_map_configured else ("single-tenant" if tenant_id else "solo")

    return JSONResponse({
        "name": "Nucleus Sovereign Agent OS",
        "version": __version__,
        "mode": mode,
        "transport": _transport,
        "mcp_endpoint": _mcp_path,
        "jurisdiction": os.environ.get("NUCLEUS_JURISDICTION", "global-default"),
        "auth_required": os.environ.get("NUCLEUS_REQUIRE_AUTH", "false").lower() == "true",
        "docs": "https://github.com/eidetic-works/nucleus-mcp",
    })


# Compose: health routes + MCP app mounted at /mcp (or /sse)
app = Starlette(
    routes=[
        Route("/", root),
        Route("/health", health),
        Route("/ready", ready),
        Mount(_mcp_path, app=_mcp_app),
    ]
)

# ---------------------------------------------------------------------------
# CLI entrypoint for `nucleus-mcp http` and direct `python src/app.py`
# ---------------------------------------------------------------------------

def serve():
    """Start the Cloud Run compatible HTTP server."""
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("NUCLEUS_HTTP_HOST", "0.0.0.0")

    sys.stderr.write(
        f"[Nucleus Cloud] v{__version__} starting on http://{host}:{port}{_mcp_path} "
        f"(transport={_transport})\n"
    )
    sys.stderr.flush()

    try:
        import uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=_log_level.lower(),
        )
    except ImportError:
        sys.stderr.write("[Nucleus Cloud] uvicorn not installed. Run: pip install uvicorn\n")
        sys.exit(1)


if __name__ == "__main__":
    serve()
