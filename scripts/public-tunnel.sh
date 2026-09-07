#!/usr/bin/env bash
# Publish the production Next.js server on a public HTTPS URL (Cloudflare Quick Tunnel).
# The URL stays up as long as this process (and the VM) stay running.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-43180}"
BIN="${HOME}/.local/bin/cloudflared"
mkdir -p "$(dirname "$BIN")"

if [[ ! -x "$BIN" ]]; then
  echo "downloading cloudflared…"
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o "$BIN"
  chmod +x "$BIN"
fi

if ! curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null; then
  echo "production server is not listening on :${PORT}; start it first (npm run start)"
  exit 1
fi

echo "opening Cloudflare Quick Tunnel to http://127.0.0.1:${PORT}"
exec "$BIN" tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}"
