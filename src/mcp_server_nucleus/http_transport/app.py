"""
Nucleus HTTP Cloud App — Option 2
===================================
Production ASGI app for Cloud Run, Fly.io, Railway, or any container platform.
This module lives inside the installed package — no sys.path hacks needed.

Entry points:
  nucleus-mcp-cloud              (via pyproject.toml scripts)
  python -m mcp_server_nucleus.http_transport.app
  CMD=http in deploy/entrypoint.sh

Environment variables:
  PORT                     Cloud Run injects this (default: 8080)
  NUCLEUS_TRANSPORT        streamable-http | sse (default: streamable-http)
  NUCLEUS_BRAIN_ROOT       Root for per-tenant brain dirs
  NUCLEUS_TENANT_ID        Static tenant slug (single-tenant mode)
  NUCLEUS_TENANT_MAP       JSON {token: tenant_id} (multi-tenant mode)
  NUCLEUS_REQUIRE_AUTH     "true" to enforce auth
  NUCLEUS_JURISDICTION     e.g. "eu-dora", "global-default"
  NUCLEUS_LOG_LEVEL        Logging verbosity (default: WARNING)
"""

import os
import sys
import time
import logging

# Suppress FastMCP banner before any import
os.environ.setdefault("FASTMCP_SHOW_CLI_BANNER", "False")
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

_log_level = os.environ.get("NUCLEUS_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.WARNING),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nucleus.cloud")

from mcp_server_nucleus import mcp, __version__
from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse

_start_time = time.time()
_transport = os.environ.get("NUCLEUS_TRANSPORT", "streamable-http")
_mcp_path = "/sse" if _transport == "sse" else "/mcp"

# Build the fastmcp ASGI app and wrap with tenant middleware
_mcp_app = mcp.http_app(transport=_transport, path=_mcp_path)
_mcp_app.add_middleware(NucleusTenantMiddleware)


async def root(request: Request):
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


async def health(request: Request):
    return JSONResponse({
        "status": "ok",
        "version": __version__,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "jurisdiction": os.environ.get("NUCLEUS_JURISDICTION", "global-default"),
        "transport": _transport,
        "mcp_endpoint": _mcp_path,
    })


async def ready(request: Request):
    try:
        from mcp_server_nucleus.runtime.common import get_brain_path
        brain = get_brain_path()
        if not brain.exists():
            return JSONResponse({"status": "not_ready", "detail": "Brain path not accessible"}, status_code=503)
    except Exception as e:
        return JSONResponse({"status": "not_ready", "error": str(e)}, status_code=503)
    return JSONResponse({"status": "ready", "brain": str(brain)})


app = Starlette(routes=[
    Route("/", root),
    Route("/health", health),
    Route("/ready", ready),
    Mount(_mcp_path, app=_mcp_app),
])


def serve():
    """CLI entrypoint: nucleus-mcp-cloud"""
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("NUCLEUS_HTTP_HOST", "0.0.0.0")
    sys.stderr.write(
        f"[Nucleus Cloud] v{__version__} starting on http://{host}:{port}{_mcp_path} "
        f"(transport={_transport})\n"
    )
    sys.stderr.flush()
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level=_log_level.lower())
    except ImportError:
        sys.stderr.write("[Nucleus Cloud] uvicorn not installed. Run: pip install 'nucleus-mcp[http]'\n")
        sys.exit(1)


if __name__ == "__main__":
    serve()
