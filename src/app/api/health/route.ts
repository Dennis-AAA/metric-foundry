import { refreshEnabled } from "@/lib/refresh";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({
    ok: true,
    service: "macro-vol-dashboard",
    refresh: refreshEnabled(),
    time: new Date().toISOString(),
  });
}
