FROM node:24-alpine AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    NEXT_TELEMETRY_DISABLED=1

RUN corepack enable
WORKDIR /workspace

FROM base AS dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web-console/package.json apps/web-console/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS build
COPY apps/web-console apps/web-console
RUN pnpm --filter @agentic-delivery/web-console build

FROM node:24-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=build --chown=nextjs:nodejs /workspace/apps/web-console/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /workspace/apps/web-console/.next/static ./apps/web-console/.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "apps/web-console/server.js"]
