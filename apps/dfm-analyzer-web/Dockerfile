# Build context must be the repo root (npm workspaces monorepo).
FROM node:20-alpine AS builder
WORKDIR /repo

COPY package.json package-lock.json turbo.json ./
COPY apps/dfm-analyzer-web ./apps/dfm-analyzer-web
COPY packages ./packages

RUN npm ci
RUN npm run build --workspace=dfm-analyzer-web

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /repo/apps/dfm-analyzer-web/.next/standalone ./
COPY --from=builder /repo/apps/dfm-analyzer-web/.next/static ./apps/dfm-analyzer-web/.next/static
COPY --from=builder /repo/apps/dfm-analyzer-web/public ./apps/dfm-analyzer-web/public

EXPOSE 3001
CMD ["node", "apps/dfm-analyzer-web/server.js"]
