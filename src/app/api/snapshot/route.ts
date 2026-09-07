import { loadSnapshot } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const snapshot = await loadSnapshot();
  if (!snapshot) {
    return Response.json({ error: "no snapshot yet; run `python -m macrovol.cli run`" }, { status: 404 });
  }
  return Response.json(snapshot, { headers: { "cache-control": "no-store" } });
}
