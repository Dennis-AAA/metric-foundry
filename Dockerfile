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
RUN npm run build \
  && mkdir -p data/history data/cache

ENV NODE_ENV=production
ENV MACROVOL_PYTHON=/app/.venv/bin/python
ENV PORT=43180
EXPOSE 43180

CMD ["npm", "run", "start"]
