FROM oven/bun:1.3.5-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM base AS builder
WORKDIR /app
RUN apk add --no-cache brotli

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN bun run build \
  && find /app/out -type f \( \
    -name "*.html" -o -name "*.css" -o -name "*.js" -o -name "*.json" -o \
    -name "*.svg" -o -name "*.txt" -o -name "*.xml" -o -name "*.ico" -o \
    -name "*.map" \
  \) -print0 | while IFS= read -r -d "" file; do \
    gzip -9 -c "$file" > "$file.gz"; \
    brotli -f -q 11 -o "$file.br" "$file"; \
  done

FROM alpine:3.20
RUN apk add --no-cache nginx nginx-mod-http-brotli \
  && mkdir -p /run/nginx

WORKDIR /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/out ./

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
