"""
Nucleus HTTP Server — Option 1: Local HTTP/SSE Entrypoint
===========================================================
Runs the same Nucleus MCP instance that stdio uses, but over HTTP/SSE
or streamable-HTTP transport. Designed for:

  - Local dev/test (hit from Computer, curl, or any HTTP MCP client)
  - LAN team access (multiple devs → one Nucleus brain per token)
  - CI/CD pipeline integration

Usage:
  nucleus-mcp-http                      # streamable-http on :8766
  nucleus-mcp-http --transport sse      # SSE on :8766
  nucleus-mcp-http --port 9000          # custom port
  nucleus-mcp-http --host 0.0.0.0       # expose on all interfaces

Environment variables (all optional):
  NUCLEUS_HTTP_HOST        Host to bind (default: 127.0.0.1)
  NUCLEUS_HTTP_PORT        Port to bind (default: 8766)
  NUCLEUS_HTTP_TRANSPORT   Transport: streamable-http | sse (default: streamable-http)
  NUCLEUS_BRAIN_ROOT       Root for per-tenant brain dirs
  NUCLEUS_TENANT_ID        Static tenant for single-user mode
  NUCLEUS_TENANT_MAP       JSON {token: tenant_id} for multi-user
  NUCLEUS_REQUIRE_AUTH     "true" to enforce Bearer token (default: false)
  NUCLEUS_LOG_LEVEL        Logging level (default: WARNING)
"""

import os
import sys
import logging
import argparse

# ---------------------------------------------------------------------------
# Logging — must happen before any Nucleus import to suppress startup noise
# ---------------------------------------------------------------------------
_log_level = os.environ.get("NUCLEUS_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.WARNING),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nucleus.http")

# Suppress FastMCP banner
os.environ["FASTMCP_SHOW_CLI_BANNER"] = "False"
os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"


def build_app(transport: str = "streamable-http"):
    """
    Build and return the Starlette ASGI app for Nucleus MCP over HTTP.
    Wraps the shared `mcp` instance from __init__ with tenant middleware.
    """
    # Import the shared mcp instance (same one used by stdio)
    from mcp_server_nucleus import mcp
    from .tenant import NucleusTenantMiddleware

    # Get the fastmcp Starlette app for the chosen transport
    app = mcp.http_app(transport=transport)

    # Wrap with tenant middleware — this is what makes it multi-tenant aware
    app.add_middleware(NucleusTenantMiddleware)

    return app


def main():
    """CLI entrypoint: nucleus-mcp-http"""
    parser = argparse.ArgumentParser(
        prog="nucleus-mcp-http",
        description="Nucleus MCP over HTTP/SSE — local dev and team access",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("NUCLEUS_HTTP_HOST", "127.0.0.1"),
        help="Host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("NUCLEUS_HTTP_PORT", "8766")),
        help="Port to bind (default: 8766)",
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default=os.environ.get("NUCLEUS_HTTP_TRANSPORT", "streamable-http"),
        help="MCP transport protocol (default: streamable-http)",
    )
    parser.add_argument(
        "--log-level",
        default=_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: WARNING)",
    )
    args = parser.parse_args()

    # Re-apply log level if overridden via CLI
    logging.getLogger().setLevel(getattr(logging, args.log_level, logging.WARNING))

    sys.stderr.write(
        f"[Nucleus HTTP] Starting on http://{args.host}:{args.port} "
        f"(transport={args.transport})\n"
    )
    sys.stderr.flush()

    # Use fastmcp's built-in uvicorn runner for Option 1
    from mcp_server_nucleus import mcp
    from .tenant import NucleusTenantMiddleware

    # Attach tenant middleware
    # No explicit path= to avoid trailing-slash redirects from fastmcp
    http_app = mcp.http_app(transport=args.transport)
    http_app.add_middleware(NucleusTenantMiddleware)

    # Run via uvicorn
    try:
        import uvicorn
        uvicorn.run(
            http_app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
        )
    except ImportError:
        # Fallback: use fastmcp's own runner
        sys.stderr.write("[Nucleus HTTP] uvicorn not found, using fastmcp runner\n")
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()
