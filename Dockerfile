# ============================================================================
# Nucleus MCP Server - Production Dockerfile
# Version: 1.0.8
# Description: The Agent Control Plane for MCP Servers
# ============================================================================

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Build wheel
RUN pip install --no-cache-dir hatchling && \
    python -m hatchling build -t wheel

# ============================================================================
# Production stage
# ============================================================================
FROM python:3.11-slim as production

# Labels
LABEL maintainer="Nucleus Team <hello@nucleus-mcp.com>"
LABEL version="1.0.8"
LABEL description="Nucleus MCP Server - The Agent Control Plane"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NUCLEAR_BRAIN_PATH=/data/.brain

# Create non-root user
RUN groupadd --gid 1000 nucleus && \
    useradd --uid 1000 --gid nucleus --shell /bin/bash --create-home nucleus

# Create data directory
RUN mkdir -p /data/.brain && \
    chown -R nucleus:nucleus /data

WORKDIR /app

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Switch to non-root user
USER nucleus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import mcp_server_nucleus; print('healthy')" || exit 1

# Expose MCP port (stdio-based, but useful for documentation)
EXPOSE 8765

# Volume for persistent brain data
VOLUME ["/data/.brain"]

# Default command - run MCP server
CMD ["nucleus-mcp"]
