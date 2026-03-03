#!/bin/bash
# ============================================================
# Nucleus Sovereign Agent OS — One-Command Deployment Script
# ============================================================
# Deploys Nucleus with jurisdiction-specific compliance configuration.
#
# Usage:
#   ./deploy.sh eu-dora          # Deploy with EU DORA compliance
#   ./deploy.sh sg-mas-trm       # Deploy with Singapore MAS TRM
#   ./deploy.sh us-soc2          # Deploy with SOC2 compliance
#   ./deploy.sh                  # Deploy with global defaults
#
# Features:
#   - Auto-detects Docker or local Python
#   - Applies jurisdiction configuration
#   - Runs compliance check
#   - Generates initial sovereignty report
# ============================================================
set -e

JURISDICTION="${1:-global-default}"
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"

echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║       🧠  NUCLEUS SOVEREIGN AGENT OS — DEPLOY          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Jurisdiction: $JURISDICTION"
echo ""

# Validate jurisdiction
if ! echo "eu-dora sg-mas-trm us-soc2 global-default" | grep -qw "$JURISDICTION"; then
    echo "  ❌ Unknown jurisdiction: $JURISDICTION"
    echo ""
    echo "  Available jurisdictions:"
    echo "    eu-dora        — EU Digital Operational Resilience Act"
    echo "    sg-mas-trm     — Singapore MAS Technology Risk Management"
    echo "    us-soc2        — SOC2 Type II"
    echo "    global-default — Sensible defaults"
    echo ""
    exit 1
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "  📦 Docker detected — deploying as container..."
    echo ""

    COMPOSE_FILE="$DEPLOY_DIR/docker-compose.${JURISDICTION}.yml"
    if [ -f "$COMPOSE_FILE" ]; then
        cd "$PROJECT_DIR"
        docker compose -f "$COMPOSE_FILE" build
        docker compose -f "$COMPOSE_FILE" up -d

        echo ""
        echo "  ✅ Nucleus deployed with $JURISDICTION compliance"
        echo ""
        echo "  Commands:"
        echo "    docker compose -f $COMPOSE_FILE run nucleus sovereign"
        echo "    docker compose -f $COMPOSE_FILE run nucleus kyc demo"
        echo "    docker compose -f $COMPOSE_FILE run nucleus audit-report"
        echo "    docker compose -f $COMPOSE_FILE run nucleus comply --report"
    else
        echo "  ⚠️  No compose file for $JURISDICTION, using generic build..."
        cd "$PROJECT_DIR"
        docker build --build-arg JURISDICTION="$JURISDICTION" -t "nucleus-agent-os:$JURISDICTION" .
        echo ""
        echo "  ✅ Image built: nucleus-agent-os:$JURISDICTION"
        echo ""
        echo "  Run:"
        echo "    docker run -v \$(pwd)/brain:/app/.brain nucleus-agent-os:$JURISDICTION sovereign"
    fi
else
    echo "  🐍 Docker not found — deploying locally with Python..."
    echo ""

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "  ❌ Python 3 not found. Install Python 3.10+ first."
        exit 1
    fi

    # Install nucleus
    cd "$PROJECT_DIR"
    pip install -e . 2>/dev/null || pip3 install -e . 2>/dev/null

    # Initialize brain if needed
    if [ ! -d ".brain" ]; then
        echo "  Initializing brain..."
        nucleus init --template solo 2>/dev/null || true
    fi

    # Apply jurisdiction
    echo "  Applying jurisdiction: $JURISDICTION"
    nucleus comply --jurisdiction "$JURISDICTION" 2>/dev/null

    # Verify
    echo ""
    nucleus comply --report 2>/dev/null

    echo ""
    echo "  ✅ Nucleus deployed locally with $JURISDICTION compliance"
    echo ""
    echo "  Commands:"
    echo "    nucleus sovereign       # Show sovereignty status"
    echo "    nucleus kyc demo        # Run compliance demo"
    echo "    nucleus audit-report    # Generate audit report"
    echo "    nucleus morning-brief   # Daily brief"
    echo ""
fi
