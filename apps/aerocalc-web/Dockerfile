# Build context must be the repo root (npm workspaces monorepo).
FROM node:20-alpine AS builder
WORKDIR /repo

COPY package.json package-lock.json turbo.json ./
COPY apps/aerocalc-web ./apps/aerocalc-web
COPY packages ./packages

RUN npm ci
RUN npm run build --workspace=aerocalc-web

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /repo/apps/aerocalc-web/.next/standalone ./
COPY --from=builder /repo/apps/aerocalc-web/.next/static ./apps/aerocalc-web/.next/static
COPY --from=builder /repo/apps/aerocalc-web/public ./apps/aerocalc-web/public

EXPOSE 3000
CMD ["node", "apps/aerocalc-web/server.js"]
