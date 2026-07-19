# capstat web. Built from the repository root:
#     docker build -f apps/web/Dockerfile -t capstat-web .
#
# Only needed for self-hosting (docker compose). Vercel builds the app itself
# and ignores this file.

# --- dependencies -----------------------------------------------------------
FROM node:22-slim AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

# --- build ------------------------------------------------------------------
FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./

# The API base URL is baked in at build time (it is a NEXT_PUBLIC_ variable, so
# it ends up in the client bundle). Override it for a real deployment:
#     docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com ...
ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# --- runtime ----------------------------------------------------------------
FROM node:22-slim AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# `output: standalone` emits server.js plus only the node_modules it reached.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public

USER node
EXPOSE 3000
CMD ["node", "server.js"]
