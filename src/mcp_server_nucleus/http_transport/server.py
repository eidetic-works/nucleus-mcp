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
  nucleus-mcp-http --daemon --relay --sync  # start background services

Environment variables (all optional):
  NUCLEUS_HTTP_HOST        Host to bind (default: 127.0.0.1)
  NUCLEUS_HTTP_PORT        Port to bind (default: 8766)
  NUCLEUS_HTTP_TRANSPORT   Transport: streamable-http | sse (default: streamable-http)
  NUCLEUS_BRAIN_ROOT       Root for per-tenant brain dirs
  NUCLEUS_TENANT_ID        Static tenant for single-user mode
  NUCLEUS_TENANT_MAP       JSON {token: tenant_id} for multi-user
  NUCLEUS_REQUIRE_AUTH     "true" to enforce Bearer token (default: false)
  NUCLEUS_LOG_LEVEL        Logging level (default: WARNING)
  NUCLEUS_RUN_DAEMON       "true" to start background scheduler + all jobs (default: false)
  NUCLEUS_RUN_RELAY        "true" to start relay watcher for inter-brain messaging (default: false)
  NUCLEUS_RUN_SYNC         "true" to start file sync watcher if configured (default: false)
"""

import os
import sys
import asyncio
import logging
import argparse
from contextlib import asynccontextmanager

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


def _env_flag(name: str) -> bool:
    """Return True if the given env var is set to a truthy value."""
    return os.environ.get(name, "").lower() in ("true", "1", "yes")


def build_lifespan():
    """
    Return a Starlette lifespan context manager that optionally starts
    background services (daemon, relay, sync) based on env vars.
    """
    @asynccontextmanager
    async def lifespan(app):
        daemon_task = None
        daemon_mgr = None

        # --- Daemon + Scheduler ---
        if _env_flag("NUCLEUS_RUN_DAEMON"):
            try:
                from mcp_server_nucleus.runtime.daemon import DaemonManager
                from mcp_server_nucleus.runtime.common import get_brain_path

                daemon_mgr = DaemonManager(get_brain_path())
                daemon_task = asyncio.create_task(daemon_mgr.start())
                logger.info("Background daemon started")
            except Exception:
                logger.warning("Failed to start daemon", exc_info=True)
                daemon_mgr = None
                daemon_task = None

        # --- Relay watcher ---
        if _env_flag("NUCLEUS_RUN_RELAY"):
            try:
                from mcp_server_nucleus.runtime.relay_ops import auto_start_relay_watcher
                from mcp_server_nucleus.runtime.common import get_brain_path

                auto_start_relay_watcher(get_brain_path())
                logger.info("Relay watcher started")
            except Exception:
                logger.warning("Failed to start relay watcher", exc_info=True)

        # --- Auto-sync ---
        if _env_flag("NUCLEUS_RUN_SYNC"):
            try:
                from mcp_server_nucleus.runtime.sync_ops import auto_start_sync_if_configured
                from mcp_server_nucleus.runtime.common import get_brain_path

                auto_start_sync_if_configured(get_brain_path())
                logger.info("Sync watcher started")
            except Exception:
                logger.warning("Failed to start sync watcher", exc_info=True)

        try:
            yield
        finally:
            # --- Shutdown relay ---
            if _env_flag("NUCLEUS_RUN_RELAY"):
                try:
                    from mcp_server_nucleus.runtime.relay_ops import stop_relay_watcher
                    stop_relay_watcher()
                    logger.info("Relay watcher stopped")
                except Exception:
                    logger.warning("Failed to stop relay watcher", exc_info=True)

            # --- Shutdown sync ---
            if _env_flag("NUCLEUS_RUN_SYNC"):
                try:
                    from mcp_server_nucleus.runtime.sync_ops import stop_file_watcher
                    stop_file_watcher()
                    logger.info("Sync watcher stopped")
                except Exception:
                    logger.warning("Failed to stop sync watcher", exc_info=True)

            # --- Shutdown daemon ---
            if daemon_mgr is not None:
                try:
                    await daemon_mgr.shutdown()
                    logger.info("Daemon shut down")
                except Exception:
                    logger.warning("Failed to shut down daemon", exc_info=True)
            if daemon_task is not None:
                daemon_task.cancel()
                try:
                    await daemon_task
                except (asyncio.CancelledError, Exception):
                    pass

    return lifespan


def build_app(transport: str = "streamable-http"):
    """
    Build and return the Starlette ASGI app for Nucleus MCP over HTTP.
    Wraps the shared `mcp` instance from __init__ with tenant middleware.
    If any NUCLEUS_RUN_* env vars are set, chains a lifespan that starts
    the corresponding background services alongside fastmcp's own lifespan.
    """
    # Import the shared mcp instance (same one used by stdio)
    from mcp_server_nucleus import mcp
    from .tenant import NucleusTenantMiddleware

    # Get the fastmcp Starlette app for the chosen transport
    # fastmcp returns a Starlette app with its own lifespan (session manager init)
    app = mcp.http_app(transport=transport)

    # Wrap with tenant middleware
    app.add_middleware(NucleusTenantMiddleware)

    # If background services requested, chain our lifespan with fastmcp's existing one
    needs_lifespan = any(
        _env_flag(v) for v in ("NUCLEUS_RUN_DAEMON", "NUCLEUS_RUN_RELAY", "NUCLEUS_RUN_SYNC")
    )
    if needs_lifespan:
        # fastmcp's lifespan is stored on the Starlette app's router
        original_lifespan = getattr(app, "lifespan", None) or getattr(app.router, "lifespan_context", None)
        nucleus_lifespan = build_lifespan()

        @asynccontextmanager
        async def chained_lifespan(a):
            # Run fastmcp's lifespan first (initialises session manager)
            if original_lifespan is not None:
                async with original_lifespan(a):
                    async with nucleus_lifespan(a):
                        yield
            else:
                async with nucleus_lifespan(a):
                    yield

        app.router.lifespan_context = chained_lifespan

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
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Start background scheduler + all daemon jobs",
    )
    parser.add_argument(
        "--relay",
        action="store_true",
        help="Start relay watcher for inter-brain messaging",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Start file sync watcher if configured",
    )
    args = parser.parse_args()

    # Re-apply log level if overridden via CLI
    logging.getLogger().setLevel(getattr(logging, args.log_level, logging.WARNING))

    # Set env vars from CLI flags so build_app() / build_lifespan() picks them up
    if args.daemon:
        os.environ["NUCLEUS_RUN_DAEMON"] = "true"
    if args.relay:
        os.environ["NUCLEUS_RUN_RELAY"] = "true"
    if args.sync:
        os.environ["NUCLEUS_RUN_SYNC"] = "true"

    bg_services = []
    if args.daemon:
        bg_services.append("daemon")
    if args.relay:
        bg_services.append("relay")
    if args.sync:
        bg_services.append("sync")
    bg_label = f", bg={'+'.join(bg_services)}" if bg_services else ""

    sys.stderr.write(
        f"[Nucleus HTTP] Starting on http://{args.host}:{args.port} "
        f"(transport={args.transport}{bg_label})\n"
    )
    sys.stderr.flush()

    http_app = build_app(transport=args.transport)

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
        from mcp_server_nucleus import mcp
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()
