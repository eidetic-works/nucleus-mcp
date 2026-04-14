#!/usr/bin/env bash
# =============================================================================
# Nucleus Sovereign Agent OS — Container Entrypoint
# =============================================================================
# Modes (pass as CMD):
#   sovereign   stdio MCP server (default — backward-compatible)
#   http        Cloud Run / container HTTP server (Option 2)
#   cli         Drop into nucleus CLI
# =============================================================================
set -euo pipefail

MODE="${1:-sovereign}"

case "$MODE" in
  sovereign|stdio|mcp)
    echo "[entrypoint] Starting Nucleus MCP (stdio transport)" >&2
    exec nucleus-mcp
    ;;

  http|cloud|serve)
    echo "[entrypoint] Starting Nucleus MCP (HTTP transport, port=${PORT:-8080})" >&2
    # Run the Cloud Run ASGI app via uvicorn
    exec python /app/src/app.py
    ;;

  cli|shell)
    echo "[entrypoint] Starting Nucleus CLI" >&2
    exec nucleus "$@"
    ;;

  *)
    echo "[entrypoint] Unknown mode: $MODE. Use: sovereign | http | cli" >&2
    exit 1
    ;;
esac
