# frontend/Dockerfile
# ============================================================================
# ARGUS-INT Frontend - Production Dockerfile
# Multi-stage build: Deps → Builder → Runner (standalone, minimal attack surface)
# ============================================================================

# ============================================================================
# Stage 1: Dependencies - Install npm packages with cache optimization
# ============================================================================
FROM node:20-alpine AS deps

RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files for layer caching
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Install dependencies based on available lockfile
RUN \
  if [ -f yarn.lock ]; then yarn install --frozen-lockfile --production=false; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

# ============================================================================
# Stage 2: Builder - Compile Next.js application
# ============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from previous stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Security: Disable Next.js telemetry
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    NODE_OPTIONS="--max-old-space-size=4096"

# Build Next.js with standalone output for minimal runtime
RUN npm run build

# ============================================================================
# Stage 3: Runner - Minimal production image
# ============================================================================
FROM node:20-alpine AS runner

# Security labels for traceability
LABEL org.opencontainers.image.title="ARGUS-INT Frontend" \
      org.opencontainers.image.description="Multi-Spectrum Intelligence Fusion Platform - Tactical UI" \
      org.opencontainers.image.version="0.4.0" \
      org.opencontainers.image.vendor="ARGUS-INT Project" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.source="https://github.com/your-org/argus-int" \
      security.policy="zero-trust" \
      opsec.level="production"

WORKDIR /app

# Security: Disable telemetry and set production env
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0" \
    PORT=3000

# Create non-root user with no home directory
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    mkdir -p /app/.next/cache && \
    chown -R nextjs:nodejs /app

# Copy built assets (standalone output includes only necessary files)
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Security: Drop to non-root user
USER nextjs

# Expose only necessary port
EXPOSE 3000

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the application
CMD ["node", "server.js"]
