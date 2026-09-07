#!/usr/bin/env bash
# Create a public GitHub repo and push this project so GitHub Pages can host it.
# Run on YOUR machine (this Cloud Agent cannot log into your GitHub).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v gh >/dev/null 2>&1; then
  echo "请先安装 GitHub CLI：https://cli.github.com/"
  echo "  macOS: brew install gh"
  echo "  或:    https://github.com/cli/cli#installation"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "正在打开浏览器登录 GitHub…"
  gh auth login
fi
gh auth setup-git >/dev/null

USER_LOGIN="$(gh api user -q .login)"
REPO="${GITHUB_REPO:-metric-foundry}"
SLUG="${USER_LOGIN}/${REPO}"

echo "GitHub 用户：${USER_LOGIN}"
echo "仓库：${SLUG}（公开，才能用免费 GitHub Pages）"

if gh repo view "$SLUG" >/dev/null 2>&1; then
  echo "仓库已存在，推送当前代码到 main…"
  if git remote get-url github >/dev/null 2>&1; then
    git remote set-url github "https://github.com/${SLUG}.git"
  else
    git remote add github "https://github.com/${SLUG}.git"
  fi
else
  gh repo create "$REPO" --public \
    --description "方向偏好 × 波动率偏好：对齐 Delta / Vega / Skew / Gamma 的日度宏观看板" \
    --disable-wiki --disable-issues
  git remote remove github 2>/dev/null || true
  git remote add github "https://github.com/${SLUG}.git"
fi

git push -u github HEAD:main

echo "启用 GitHub Pages（来源 = GitHub Actions）…"
gh api -X POST "repos/${SLUG}/pages" -f build_type=workflow >/dev/null 2>&1 || \
  gh api -X PUT "repos/${SLUG}/pages" -f build_type=workflow >/dev/null 2>&1 || true

echo "触发第一次站点构建…"
gh workflow run "Update and publish" --repo "$SLUG" || true

echo
echo "仓库： https://github.com/${SLUG}"
echo "网页： https://${USER_LOGIN}.github.io/${REPO}/"
echo
echo "第一次构建大约 1–3 分钟。若 404：打开仓库 Settings → Pages，确认 Source 是 GitHub Actions，"
echo "再到 Actions 里看 “Update and publish” 是否绿灯。"
