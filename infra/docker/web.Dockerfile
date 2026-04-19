FROM node:22-alpine AS builder

WORKDIR /app

COPY apps/web/package.json ./
COPY apps/web/package-lock.json* ./
RUN npm ci

COPY apps/web /app

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER appuser

CMD ["node", "server.js"]
