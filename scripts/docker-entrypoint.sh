#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/data/history /app/data/cache
if [[ ! -f /app/data/latest.json && -f /app/data-seed/latest.json ]]; then
  cp /app/data-seed/latest.json /app/data/
  [[ -f /app/data-seed/timeline.json ]] && cp /app/data-seed/timeline.json /app/data/
  if [[ -d /app/data-seed/history ]]; then
    cp -R /app/data-seed/history/. /app/data/history/ || true
  fi
fi
exec node /app/scripts/start-web.mjs
