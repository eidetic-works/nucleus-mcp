#!/bin/bash
# Smart Telemetry Drain - Auto-start Docker if needed, drain, clean up

set -euo pipefail

PROJECT="/Users/lokeshgarg/ai-mvp-backend/mcp-server-nucleus"
COMPOSE_FILE="$PROJECT/infra/telemetry/docker-compose.yaml"
LOG_FILE="$PROJECT/.telemetry/smart-drain.log"

# Logging helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Track if we started Docker Desktop
STARTED_DOCKER=0

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    log "🐳 Docker not running - attempting to start Docker Desktop..."
    
    # Start Docker Desktop (macOS)
    if [ -d "/Applications/Docker.app" ]; then
        open -a Docker
        STARTED_DOCKER=1
        log "⏳ Waiting for Docker daemon to be ready..."
        
        # Wait up to 60 seconds for Docker to start
        WAIT_COUNT=0
        while ! docker info >/dev/null 2>&1; do
            sleep 2
            WAIT_COUNT=$((WAIT_COUNT + 1))
            if [ $WAIT_COUNT -gt 30 ]; then
                log "❌ Docker failed to start after 60 seconds - skipping drain"
                exit 1
            fi
        done
        
        log "✅ Docker daemon is ready"
    else
        log "❌ Docker Desktop not found at /Applications/Docker.app - skipping drain"
        exit 1
    fi
fi

# Check if telemetry stack is already running
STACK_RUNNING=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | wc -l | tr -d ' ')
STARTED_STACK=0

if [ "$STACK_RUNNING" -eq 0 ]; then
    log "🚀 Starting telemetry stack..."
    docker compose -f "$COMPOSE_FILE" up -d >> "$LOG_FILE" 2>&1
    STARTED_STACK=1
    # Give containers a moment to be ready
    sleep 3
    log "✅ Telemetry stack started"
else
    log "ℹ️  Telemetry stack already running"
fi

# Run the drain (run once mode)
log "🔄 Draining spans from Upstash..."
cd "$PROJECT"
NUCLEUS_DRAIN_ONCE=true npm run telemetry:drain >> "$LOG_FILE" 2>&1 || log "⚠️  Drain failed (see log)"

# Check for first external user
log "🔍 Checking for first external user..."
bash "$PROJECT/scripts/first-user-alert.sh" || true

# Stop stack only if we started it
if [ "$STARTED_STACK" -eq 1 ]; then
    log "🛑 Stopping telemetry stack (we started it)..."
    docker compose -f "$COMPOSE_FILE" down >> "$LOG_FILE" 2>&1
    log "✅ Telemetry stack stopped"
else
    log "ℹ️  Leaving telemetry stack running (was already up)"
fi

# Stop Docker Desktop only if we started it
if [ "$STARTED_DOCKER" -eq 1 ]; then
    log "🛑 Stopping Docker Desktop (we started it)..."
    osascript -e 'quit app "Docker"' 2>/dev/null || true

    # Wait up to 30s for Docker daemon to go away
    WAIT_COUNT=0
    while docker info >/dev/null 2>&1; do
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 1))
        if [ $WAIT_COUNT -gt 15 ]; then
            log "⚠️  Docker still running after 30s."

            # Optional force quit if env is set
            if [ "${NUCLEUS_FORCE_DOCKER_QUIT:-false}" = "true" ]; then
                log "⚠️  Forcing Docker Desktop quit (NUCLEUS_FORCE_DOCKER_QUIT=true)"
                pkill -f "Docker" 2>/dev/null || true
            fi
            break
        fi
    done

    if ! docker info >/dev/null 2>&1; then
        log "✅ Docker Desktop stopped"
    else
        log "ℹ️  Leaving Docker Desktop running (did not stop cleanly)"
    fi
else
    log "ℹ️  Leaving Docker Desktop running (was already up)"
fi

log "✅ Smart drain complete"
