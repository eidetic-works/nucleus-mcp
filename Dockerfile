# ============================================================
# Nucleus Sovereign Agent OS — Production Dockerfile
# ============================================================
# Multi-stage build for a minimal, secure deployment image.
#
# Usage:
#   docker build -t nucleus-agent-os .
#   docker run -v ./brain:/app/.brain nucleus-agent-os sovereign
#
# Jurisdiction-aware deployment:
#   docker build --build-arg JURISDICTION=eu-dora -t nucleus-dora .
#   docker run -v ./brain:/app/.brain nucleus-dora comply --report
# ============================================================

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build
COPY . .

RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd -r nucleus && useradd -r -g nucleus -d /app -s /sbin/nologin nucleus

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Jurisdiction configuration (build-time)
ARG JURISDICTION=global-default
ENV NUCLEUS_JURISDICTION=${JURISDICTION}
ENV NUCLEAR_BRAIN_PATH=/app/.brain

# Create brain directory structure
RUN mkdir -p /app/.brain/engrams \
             /app/.brain/ledger \
             /app/.brain/dsor \
             /app/.brain/governance \
             /app/.brain/sessions \
             /app/.brain/config && \
    chown -R nucleus:nucleus /app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD nucleus sovereign --json 2>/dev/null || exit 1

# Switch to non-root
USER nucleus

# Copy entrypoint
COPY --chown=nucleus:nucleus deploy/entrypoint.sh /app/entrypoint.sh

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
CMD ["sovereign"]

# Labels
LABEL org.opencontainers.image.title="Nucleus Sovereign Agent OS"
LABEL org.opencontainers.image.description="Sovereign, local-first Agent OS with persistent memory and compliance governance"
LABEL org.opencontainers.image.version="1.3.0"
LABEL org.opencontainers.image.vendor="Eidetic Works"
LABEL org.opencontainers.image.source="https://github.com/eidetic-works/nucleus-mcp"
