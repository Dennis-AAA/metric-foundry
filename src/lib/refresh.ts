import { existsSync } from "node:fs";
import path from "node:path";

/** Serverless hosts cannot exec the Python engine or persist data/ writes. */
export function refreshBlockedReason(): string | null {
  if (process.env.MACROVOL_ALLOW_REFRESH === "0") {
    return "已通过 MACROVOL_ALLOW_REFRESH=0 关闭在线刷新";
  }
  if (process.env.VERCEL) {
    return "Vercel 等无盘环境不能现场重算，请用 GitHub Actions 或带 Python 的主机";
  }
  return null;
}

export function refreshEnabled(): boolean {
  return refreshBlockedReason() === null;
}

export function pythonBinary(): string {
  if (process.env.MACROVOL_PYTHON) return process.env.MACROVOL_PYTHON;
  const venv = path.join(process.cwd(), ".venv", "bin", "python");
  return existsSync(venv) ? venv : "python3";
}
