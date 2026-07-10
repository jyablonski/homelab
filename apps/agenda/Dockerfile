FROM node:24-alpine AS base

WORKDIR /app

FROM base AS deps

COPY package.json package-lock.json ./

RUN npm ci

FROM deps AS builder

COPY next.config.ts tsconfig.json postcss.config.mjs ./
COPY src ./src

RUN npm run build

FROM base AS runtime

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY package.json next.config.ts tsconfig.json postcss.config.mjs ./
COPY src ./src

# `next dev` writes auxiliary files (next-env.d.ts, .next/dev/*) directly under
# /app and .next at runtime, so appuser needs write access there. node_modules
# is read-only at runtime, so it's excluded to keep this fast (chown -R over
# 450 packages took ~60s in testing).
RUN chown appuser:appgroup /app && chown -R appuser:appgroup /app/.next

USER appuser

EXPOSE 3000

CMD ["npm", "run", "start"]
