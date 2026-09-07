import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatDateTime, statusBadge } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

import { RefreshButton } from "./refresh-button";

interface Props {
  snapshot: Snapshot;
  historyCount: number;
  refreshEnabled: boolean;
}

function Stamp({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-sm font-medium tabular-nums text-slate-800">{value ?? "—"}</span>
    </div>
  );
}

export function StatusBar({ snapshot, historyCount, refreshEnabled }: Props) {
  const warnings = snapshot.sources.filter((s) => s.status !== "ok");
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Stamp label="价格" value={snapshot.as_of.prices} />
        <Stamp label="波动率指数" value={snapshot.as_of.vol_indices} />
        <Stamp label="CFTC COT" value={snapshot.as_of.cot} />
        <Stamp label="期权链" value={snapshot.as_of.options} />
        <div className="flex flex-col">
          <span className="text-[11px] uppercase tracking-wide text-slate-400">更新</span>
          <span className="flex items-center gap-1.5 text-sm text-slate-800">
            <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
              {snapshot.mode === "weekly" ? "周度" : "日度"}
            </Badge>
            <span className="text-xs text-slate-500">{formatDateTime(snapshot.generated_at)}</span>
          </span>
        </div>
        <Stamp label="累计快照" value={`${historyCount} 天`} />
        <Tooltip>
          <TooltipTrigger render={<span className="inline-flex cursor-help flex-wrap gap-1" />}>
            {snapshot.sources.map((s) => (
              <span key={s.name} className={`rounded border px-1.5 py-0.5 text-[10px] ${statusBadge(s.status)}`}>
                {s.name}
              </span>
            ))}
          </TooltipTrigger>
          <TooltipContent className="max-w-md">
            <ul className="space-y-0.5">
              {snapshot.sources.map((s) => (
                <li key={s.name}>
                  <span className="font-semibold">{s.name}</span>：{s.detail || s.status}
                </li>
              ))}
            </ul>
          </TooltipContent>
        </Tooltip>
        {warnings.length > 0 && <span className="text-[11px] text-amber-700">{warnings.length} 个数据源降级</span>}
      </div>
      <RefreshButton enabled={refreshEnabled} />
    </div>
  );
}
