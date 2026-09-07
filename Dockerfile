FROM node:22-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip python3-venv ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY engine ./engine
RUN python3 -m venv .venv \
  && .venv/bin/pip install --no-cache-dir -e ./engine

COPY . .
RUN mkdir -p /app/data-seed/history \
  && if [ -f data/latest.json ]; then cp data/latest.json /app/data-seed/; fi \
  && if [ -f data/timeline.json ]; then cp data/timeline.json /app/data-seed/; fi \
  && if [ -d data/history ]; then cp -R data/history/. /app/data-seed/history/; fi \
  && npm run build \
  && mkdir -p data/history data/cache \
  && chmod +x scripts/docker-entrypoint.sh

ENV NODE_ENV=production
ENV MACROVOL_PYTHON=/app/.venv/bin/python
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

CMD ["./scripts/docker-entrypoint.sh"]
