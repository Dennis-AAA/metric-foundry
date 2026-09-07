import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { pythonBinary, refreshBlockedReason } from "@/lib/refresh";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const execFileAsync = promisify(execFile);
const COOLDOWN_MS = 90_000;

let running = false;
let lastStartedAt = 0;

export async function POST(request: Request) {
  const blocked = refreshBlockedReason();
  if (blocked) {
    return Response.json({ ok: false, error: blocked }, { status: 403 });
  }

  const secret = process.env.MACROVOL_REFRESH_TOKEN;
  if (secret) {
    const header = request.headers.get("x-refresh-token") ?? "";
    const url = new URL(request.url);
    const query = url.searchParams.get("token") ?? "";
    if (header !== secret && query !== secret) {
      return Response.json({ ok: false, error: "需要刷新口令（X-Refresh-Token）" }, { status: 401 });
    }
  }

  let mode: "daily" | "weekly" = "daily";
  try {
    const body = (await request.json()) as { mode?: string };
    if (body.mode === "weekly") mode = "weekly";
  } catch {
    // no body -> daily
  }

  const now = Date.now();
  if (running) {
    return Response.json({ ok: false, error: "已有一次刷新在进行，请稍后再试" }, { status: 409 });
  }
  if (lastStartedAt && now - lastStartedAt < COOLDOWN_MS) {
    const wait = Math.ceil((COOLDOWN_MS - (now - lastStartedAt)) / 1000);
    return Response.json({ ok: false, error: `刷新冷却中，请 ${wait} 秒后再试（防止重复拉取数据源）` }, { status: 429 });
  }

  running = true;
  lastStartedAt = now;
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
  } finally {
    running = false;
  }
}
