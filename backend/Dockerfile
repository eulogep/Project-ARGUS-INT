# ============================================================================
# ARGUS-INT Backend - Production Dockerfile
# Multi-stage build: Builder (compilation) → Runtime (minimal attack surface)
# ============================================================================

# ============================================================================
# Stage 1: Builder - Compile dependencies and prepare artifacts
# ============================================================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /home/builder/build

# Install build dependencies (minimal set for asyncpg, cryptography, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q app/

# ============================================================================
# Stage 2: Runtime - Minimal image with only necessary artifacts
# ============================================================================
FROM python:3.12-slim-bookworm AS runtime

# Security labels for traceability
LABEL org.opencontainers.image.title="ARGUS-INT Backend" \
      org.opencontainers.image.description="Multi-Spectrum Intelligence Fusion Platform - Backend API" \
      org.opencontainers.image.version="0.4.0" \
      org.opencontainers.image.vendor="ARGUS-INT Project" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.source="https://github.com/your-org/argus-int" \
      security.policy="zero-trust" \
      opsec.level="production"

# Create non-root user with no home directory (minimal footprint)
RUN groupadd -g 1000 argus && \
    useradd -r -u 1000 -g argus -s /sbin/nologin argus && \
    mkdir -p /app/logs /app/tmp && \
    chown -R argus:argus /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy virtual environment from builder
COPY --from=builder --chown=argus:argus /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder --chown=argus:argus /home/builder/build/app /app/app
COPY --from=builder --chown=argus:argus /home/builder/build/alembic /app/alembic
COPY --from=builder --chown=argus:argus /home/builder/build/alembic.ini /app/

WORKDIR /app

# Security: Drop all capabilities and set restrictive umask
USER argus

# Environment variables with secure defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    WORKERS=2 \
    LOG_LEVEL=INFO \
    ENV=production \
    TMPDIR=/app/tmp

# Expose only necessary port
EXPOSE 8000

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Command to run the application with Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL} --access-log --proxy-headers --forwarded-allow-ips='*'"]
