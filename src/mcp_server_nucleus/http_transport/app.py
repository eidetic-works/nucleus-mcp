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

from mcp_server_nucleus import mcp, __version__, _ensure_registered
from mcp_server_nucleus.http_transport.tenant import NucleusTenantMiddleware
from mcp_server_nucleus.http_transport.relay_route import (
    relay_route,
    relay_get_route,
    relay_ack_route,
    relay_status_route,
)
from mcp_server_nucleus.http_transport.engram_sync_route import (
    engram_sync_route,
    engram_sync_status_route,
)
from mcp_server_nucleus.http_transport.oauth_server import oauth_routes as _oauth_routes
from mcp_server_nucleus.http_transport.telemetry_route import (
    telemetry_post_route,
    telemetry_installs_route,
    telemetry_g35_route,
)
from mcp_server_nucleus.http_transport.fleet_dashboard import (
    fleet_dashboard_route,
    fleet_panel_route,
)
from mcp_server_nucleus.http_transport.readonly_app import get_readonly_app

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware

_start_time = time.time()
_transport = os.environ.get("NUCLEUS_TRANSPORT", "streamable-http")
_mcp_path = "/sse" if _transport == "sse" else "/mcp"

# Move 1 followup: tool registration was deferred out of package import into
# _ensure_registered() (invoked by the stdio main() entry). The HTTP/SSE/cloud
# transports build tools/list from this shared `mcp` instance, so registration
# must fire HERE — at cloud-app import (which is server start for this module) —
# BEFORE http_app() enumerates tools. Idempotent: fires exactly once per process.
_ensure_registered()

# Build the fastmcp ASGI app — no explicit path arg to avoid trailing-slash redirects.
# fastmcp handles routing internally; we mount at _mcp_path in Starlette below.
_mcp_app = mcp.http_app(transport=_transport)
_mcp_app.add_middleware(NucleusTenantMiddleware)

# Read-only MCP endpoint for Microsoft 365 Copilot and other platforms
# that require readOnlyHint=True on all tools. Mounted at /mcp-readonly.
# Exposes 4 tools: nucleus_search, nucleus_audit, nucleus_route, nucleus_relay_subscribe.
_readonly_path = "/mcp-readonly"
_readonly_app = get_readonly_app(transport=_transport)
_readonly_app.add_middleware(NucleusTenantMiddleware)


# ─── Combined lifespan for main + read-only MCP apps ──────────────────────
# FastMCP's StreamableHTTPSessionManager requires its lifespan to run to
# initialize the task group. When mounting a FastMCP app as a sub-app inside
# another Starlette app, the sub-app's lifespan doesn't run automatically.
# This combined lifespan runs both lifespans so both MCP instances work.
import contextlib

@contextlib.asynccontextmanager
async def _combined_lifespan(app):
    """Run both the main and read-only MCP app lifespans."""
    async with contextlib.AsyncExitStack() as stack:
        # Enter main MCP app lifespan
        if hasattr(_mcp_app, 'lifespan'):
            await stack.enter_async_context(_mcp_app.lifespan(app))
        # Enter read-only MCP app lifespan
        if hasattr(_readonly_app, 'lifespan'):
            await stack.enter_async_context(_readonly_app.lifespan(app))
        yield


async def root(request: Request):
    tenant_map_configured = bool(os.environ.get("NUCLEUS_TENANT_MAP"))
    tenant_id = os.environ.get("NUCLEUS_TENANT_ID")
    mode = "multi-tenant" if tenant_map_configured else ("single-tenant" if tenant_id else "solo")
    oauth_enabled = os.environ.get("NUCLEUS_OAUTH_ENABLED", "false").lower() == "true"
    return JSONResponse({
        "name": "Nucleus Sovereign Agent OS",
        "version": __version__,
        "mode": mode,
        "transport": _transport,
        "mcp_endpoint": _mcp_path,
        "mcp_readonly_endpoint": _readonly_path,
        "jurisdiction": os.environ.get("NUCLEUS_JURISDICTION", "global-default"),
        "auth_required": os.environ.get("NUCLEUS_REQUIRE_AUTH", "false").lower() == "true",
        "oauth_enabled": oauth_enabled,
        "oauth_endpoints": {
            "protected_resource": "/.well-known/oauth-protected-resource",
            "authorization_server": "/.well-known/oauth-authorization-server",
            "register": "/register",
            "authorize": "/authorize",
            "token": "/token",
            "revoke": "/revoke",
        } if oauth_enabled else None,
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


async def metrics_handler(request: Request):
    """Prometheus metrics endpoint — text/plain exposition format."""
    from mcp_server_nucleus.runtime.prometheus import get_prometheus_metrics
    from starlette.responses import Response
    body = get_prometheus_metrics()
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


async def openai_apps_verification(request: Request):
    """OpenAI App Catalog domain verification endpoint.

    Serves the verification token at /.well-known/openai-apps and
    /.well-known/openai-apps-challenge on the same domain that hosts the
    MCP endpoint. Required for ChatGPT App Catalog submission per OpenAI's
    domain-verification policy.

    Set NUCLEUS_OPENAI_APPS_TOKEN env var to the token OpenAI provides
    during the submission flow. If unset, returns 404 (verification not
    configured).

    Returns the token as PLAIN TEXT (Content-Type: text/plain) — NOT JSON.
    OpenAI's domain-verification flow requires the raw token string with no
    JSON wrapper, no HTML, no trailing newline. See:
    https://developers.openai.com/apps-sdk/deploy/submission
    """
    from starlette.responses import PlainTextResponse
    token = os.environ.get("NUCLEUS_OPENAI_APPS_TOKEN", "").strip()
    if not token:
        return PlainTextResponse(
            "openai-apps verification not configured",
            status_code=404,
            media_type="text/plain",
        )
    return PlainTextResponse(token, media_type="text/plain")


# Add health/identity routes directly to the fastmcp Starlette app
# instead of using Mount (which causes 307 trailing-slash redirects)
_mcp_app.router.routes.insert(0, Route("/", root))
_mcp_app.router.routes.insert(1, Route("/health", health))
_mcp_app.router.routes.insert(2, Route("/ready", ready))
_mcp_app.router.routes.insert(3, Route("/metrics", metrics_handler))
_mcp_app.router.routes.insert(4, Route("/.well-known/openai-apps", openai_apps_verification))
_mcp_app.router.routes.insert(4, Route("/.well-known/openai-apps-challenge", openai_apps_verification))
_mcp_app.router.routes.insert(5, relay_route)
_mcp_app.router.routes.insert(6, relay_get_route)
_mcp_app.router.routes.insert(7, relay_ack_route)
_mcp_app.router.routes.insert(8, relay_status_route)
_mcp_app.router.routes.insert(9, engram_sync_route)
_mcp_app.router.routes.insert(10, engram_sync_status_route)
# Telemetry routes — POST /telemetry, GET /telemetry/installs, GET /telemetry/g35
_mcp_app.router.routes.insert(11, telemetry_post_route)
_mcp_app.router.routes.insert(12, telemetry_installs_route)
_mcp_app.router.routes.insert(13, telemetry_g35_route)
# Fleet dashboard routes — GET /fleet (HTML page), GET /fleet/panel (HTMX partial)
_mcp_app.router.routes.insert(14, fleet_dashboard_route)
_mcp_app.router.routes.insert(15, fleet_panel_route)

# OAuth 2.1 routes — for ChatGPT Connectors, Claude Connectors, and any
# MCP client that follows the MCP authorization spec.
# Inserted at the front so .well-known/* and /authorize /token /register
# are matched before the MCP /mcp catch-all.
for _i, _route in enumerate(_oauth_routes):
    _mcp_app.router.routes.insert(9 + _i, _route)

# Mount the read-only MCP endpoint at /mcp-readonly.
# This exposes only tools with readOnlyHint=True for Microsoft 365 Copilot
# and other platforms that restrict to search/fetch operations.
_mcp_app.router.routes.insert(20, Mount(_readonly_path, app=_readonly_app))

# ─── Build composite top-level app with combined lifespan ────────────────
# The main _mcp_app already has all routes (health, relay, oauth, MCP, etc.)
# inserted into its router. We need to ensure BOTH lifespans run, so we
# create a top-level Starlette app that wraps _mcp_app and runs the combined
# lifespan. The _mcp_app handles all routing; the lifespan just needs to
# initialize both MCP session managers.
app = Starlette(
    routes=[Mount("/", app=_mcp_app)],
    lifespan=_combined_lifespan,
)


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
