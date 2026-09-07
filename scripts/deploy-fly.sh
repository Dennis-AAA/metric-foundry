#!/usr/bin/env bash
# Create (if needed) and deploy this dashboard to Fly.io.
# Resulting URL: https://<app>.fly.dev  — stays up after this Cloud Agent session ends.
set -euo pipefail
cd "$(dirname "$0")/.."

APP="${FLY_APP:-gmunu-metric-foundry}"
REGION="${FLY_REGION:-sjc}"

if ! command -v fly >/dev/null 2>&1 && ! command -v flyctl >/dev/null 2>&1; then
  echo "installing flyctl → ~/.local/bin …"
  mkdir -p "$HOME/.local/bin"
  curl -fsSL https://fly.io/install.sh | sh
  export FLYCTL_INSTALL="${FLYCTL_INSTALL:-$HOME/.fly}"
  export PATH="$FLYCTL_INSTALL/bin:$HOME/.local/bin:$PATH"
fi
FLY="$(command -v fly || command -v flyctl)"

if ! "$FLY" auth whoami >/dev/null 2>&1; then
  echo
  echo "还没有登录 Fly。在这台电脑上执行："
  echo "  fly auth login"
  echo "浏览器授权后重新跑： bash scripts/deploy-fly.sh"
  echo
  echo "没有 Fly 账号：打开 https://fly.io/app/sign-up （可用 GitHub / Google）"
  exit 2
fi

if ! "$FLY" apps list --json 2>/dev/null | grep -q "\"${APP}\""; then
  echo "creating app ${APP} in ${REGION} …"
  "$FLY" apps create "$APP" --org personal || "$FLY" apps create "$APP"
fi

if ! "$FLY" volumes list -a "$APP" 2>/dev/null | grep -q macrovol_data; then
  echo "creating 1GB volume macrovol_data …"
  "$FLY" volumes create macrovol_data --region "$REGION" --size 1 -a "$APP" -y
fi

echo "deploying …"
"$FLY" deploy -a "$APP" --region "$REGION" --yes
echo
echo "已发布： https://${APP}.fly.dev"
echo "绑定自己的域名： fly certs add 你的域名.com -a ${APP}"
echo "然后在域名 DNS 加 CNAME → ${APP}.fly.dev"
