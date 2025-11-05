FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY services/gateway/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY services/gateway/src ./src

# Copy proto files (needed for gRPC client)
COPY contracts/proto ./contracts/proto

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    chown -R nodejs:nodejs /app

USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["node", "src/server.js"]

