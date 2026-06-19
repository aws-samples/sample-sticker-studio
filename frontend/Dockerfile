# ============================================
# Builder Stage
# ============================================
FROM public.ecr.aws/docker/library/node:22.16.0-alpine AS builder

# Install required build dependencies for native modules (canvas)
RUN apk add --no-cache \
    build-base \
    python3 \
    cairo-dev \
    pango-dev \
    jpeg-dev \
    giflib-dev \
    librsvg-dev

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ============================================
# Runtime Stage
# ============================================
FROM public.ecr.aws/docker/library/node:22.16.0-alpine AS runner

# Install required runtime dependencies
RUN apk add --no-cache \
    cairo \
    pango \
    libjpeg-turbo \
    giflib \
    librsvg \
    curl && \
    # Remove package managers not needed at runtime to reduce attack surface
    rm -rf /usr/local/lib/node_modules/npm \
           /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm \
           /usr/local/bin/npx \
           /usr/local/bin/corepack \
           /opt/yarn*

# Create non-root user
RUN addgroup -g 1001 nodejs && \
    adduser -D -u 1001 -G nodejs nextjs

WORKDIR /app
ENV NODE_ENV=production

# Copy standalone output (includes all dependencies)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
