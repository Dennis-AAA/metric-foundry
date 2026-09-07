"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Props {
  enabled: boolean;
}

export function RefreshButton({ enabled }: Props) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  if (!enabled) return null;

  async function run(mode: "daily" | "weekly") {
    setState("running");
    setMessage(`正在拉取数据并重算（${mode === "weekly" ? "周度·含 COT" : "日度"}），通常需要 20–60 秒…`);
    try {
      const res = await fetch("/api/refresh", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mode }) });
      const body = (await res.json()) as { ok: boolean; output?: string; error?: string };
      if (!res.ok || !body.ok) {
        setState("error");
        setMessage(body.error ?? body.output ?? `刷新失败 (${res.status})`);
        return;
      }
      setState("done");
      setMessage(body.output?.split("\n").find((l) => l.startsWith("as_of")) ?? "已更新");
      router.refresh();
    } catch (err) {
      setState("error");
      setMessage(err instanceof Error ? err.message : "刷新失败");
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={state === "running"} onClick={() => run("daily")}>
          <RefreshCw className={state === "running" ? "animate-spin" : ""} />
          日度刷新
        </Button>
        <Button size="sm" variant="secondary" disabled={state === "running"} onClick={() => run("weekly")}>
          周度刷新
        </Button>
      </div>
      {message && <div className={`max-w-md text-right text-[11px] ${state === "error" ? "text-rose-600" : "text-slate-500"}`}>{message}</div>}
    </div>
  );
}
