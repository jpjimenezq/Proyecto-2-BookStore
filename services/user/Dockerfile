# ============================
# User Service (Node.js / gRPC)
# Base: Debian 12 (bookworm-slim) to reduce high vulns vs Alpine
# ============================

# ---- Stage 1: Builder ----
    FROM node:20-bookworm-slim AS builder
    WORKDIR /build
    
    # Copy package manifest(s) first for better layer caching
    COPY services/user/package*.json ./
    
    # Deterministic install if lockfile exists, fallback otherwise
    RUN if [ -f package-lock.json ]; then \
          npm ci --omit=dev; \
        else \
          echo "No package-lock.json found -> using npm install (prod only)"; \
          npm install --only=production --no-audit --no-fund; \
        fi
    
    # Copy the rest of the service (src, proto, etc.)
    COPY services/user ./
    
    # If you transpile (TypeScript / Nest), do it here so only built files go to runtime
    # RUN npm run build
    
    # Optionally prune dev deps if your build step added any
    # RUN npm prune --omit=dev
    
    
    # ---- Stage 2: Runtime ----
    FROM node:20-bookworm-slim
    
    # Minimal tools for health checks; keep image lean
    RUN apt-get update \
     && apt-get install -y --no-install-recommends curl netcat-traditional \
     && rm -rf /var/lib/apt/lists/*
    
    # Use a non-root user (provided by the official Node image: uid/gid 1000:1000)
    WORKDIR /app
    COPY --chown=node:node --from=builder /build ./
    
    # Copy proto files from contracts
    COPY --chown=node:node contracts/proto /app/contracts/proto
    
    USER node
    ENV NODE_ENV=production
    
    # Healthcheck: TCP probe on gRPC port
    HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
      CMD nc -z 127.0.0.1 ${GRPC_PORT:-50054} || exit 1
    
    EXPOSE 50054
    CMD ["npm", "start"]
    