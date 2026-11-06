# Production web image (IMP-218; A1 §4.3, §8.3). Build context: apps/web.
# Next.js inlines the NEXT_PUBLIC_* values at build time, so they are build arguments and each
# environment gets its own image. They are public values; this image holds no secret and no .env.

FROM node:22-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_FEATURES_DISABLED
ARG BUILD_VERSION=dev
RUN npm run build

FROM node:22-slim
ARG BUILD_VERSION=dev
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    BUILD_VERSION=$BUILD_VERSION
WORKDIR /app
# The standalone output leaves out .next/static and public.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
