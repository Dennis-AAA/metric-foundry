import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const execFileAsync = promisify(execFile);

function pythonBinary(): string {
  if (process.env.MACROVOL_PYTHON) return process.env.MACROVOL_PYTHON;
  const venv = path.join(process.cwd(), ".venv", "bin", "python");
  return existsSync(venv) ? venv : "python3";
}

/** Runs the Python engine in-process for local use; disabled on serverless hosts. */
export async function POST(request: Request) {
  if (process.env.MACROVOL_ALLOW_REFRESH === "0" || process.env.VERCEL) {
    return Response.json({ ok: false, error: "此部署环境不允许在线刷新，请通过 CLI / GitHub Actions 更新 data/latest.json" }, { status: 403 });
  }
  let mode: "daily" | "weekly" = "daily";
  try {
    const body = (await request.json()) as { mode?: string };
    if (body.mode === "weekly") mode = "weekly";
  } catch {
    // no body -> daily
  }
  try {
    const { stdout, stderr } = await execFileAsync(pythonBinary(), ["-m", "macrovol.cli", "run", "--mode", mode], {
      cwd: process.cwd(),
      timeout: 280_000,
      maxBuffer: 10 * 1024 * 1024,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
    return Response.json({ ok: true, mode, output: `${stdout}\n${stderr}`.trim() });
  } catch (err) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    return Response.json({ ok: false, error: e.stderr?.trim() || e.message || "engine failed", output: e.stdout }, { status: 500 });
  }
}
