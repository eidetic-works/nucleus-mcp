#!/usr/bin/env bash

# =============================================================================
# Nucleus Sovereign Controller - Air-Gapped Agent Deployer
# =============================================================================
# This script demonstrates how to deploy an AI agent inside a Docker container
# with ABSOLUTELY NO outbound networking (--network none).
# 
# The agent can ONLY communicate with the world via the Nucleus Host
# over the FastMCP stdio pipe. This implements Level 4 of the Nucleus 
# Trust Matrix (Egress Firewall).
# =============================================================================

set -e

# Default to OpenHands / AllHands image if none provided
AGENT_IMAGE=${1:-"docker.all-hands.dev/all-hands-ai/runtime:main-latest-al2023"}
WORKSPACE_DIR=$(pwd)

echo "🛡️  Nucleus Air-Gapped Agent Deployer"
echo "----------------------------------------"
echo "📦 Image:      $AGENT_IMAGE"
echo "📂 Workspace:  $WORKSPACE_DIR"
echo "🌐 Network:    NONE (Air-Gapped)"
echo "----------------------------------------"

# Check if docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: Docker daemon is not running."
    exit 1
fi

echo "🚀 Spawning isolated container..."

# Run the container with strict isolation properties
# -i : Interactive (binds stdio for MCP)
# -t : TTY (optional, remove if strictly plumbing MCP pipes)
# --network none : NO internet access
# -v : Mounts local workspace
# --read-only : Container filesystem is read-only (except mounted volumes and tmpfs if supplied)

docker run -it --rm \\
    --network none \\
    -v "$WORKSPACE_DIR:/workspace" \\
    -w /workspace \\
    --read-only \\
    --tmpfs /tmp \\
    --tmpfs /run \\
    --log-driver none \\
    "$AGENT_IMAGE" \\
    /bin/bash -c "echo 'Sovereign Agent Initialized. Network is unreachable.' && /bin/bash"

echo "🏁 Container terminated."
