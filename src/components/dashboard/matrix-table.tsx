"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { deltaBoxClass, dotColor, dotMeaning, gammaColor, heatBackground, heatWord, regimeDot, scoreColor, scoreText } from "@/lib/format";
import type { AssetSnapshot, Snapshot, Timeline } from "@/lib/types";

import { AssetSheet } from "./asset-sheet";

interface Props {
  snapshot: Snapshot;
  timeline: Timeline;
}

function WhyTooltip({ children, lines, title }: { children: React.ReactNode; lines: string[]; title?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="inline-flex cursor-help" />}>{children}</TooltipTrigger>
      <TooltipContent className="max-w-sm text-left leading-relaxed">
        {title && <div className="mb-1 font-semibold">{title}</div>}
        <ul className="list-disc space-y-0.5 pl-4">
          {lines.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </TooltipContent>
    </Tooltip>
  );
}

function DeltaBox({ score, label, dot, structural, sub }: { score: number; label: string; dot: "green" | "yellow" | "red"; structural?: boolean; sub: string[] }) {
  return (
    <div className={`mx-auto flex w-full max-w-[180px] flex-col items-center rounded-md border px-3 py-2 ${deltaBoxClass(score, structural)}`}>
      <div className="flex items-center gap-1.5">
        <Tooltip>
          <TooltipTrigger render={<span className={`inline-block size-2.5 rounded-full ${dotColor(dot)}`} />} />
          <TooltipContent>{dotMeaning(dot)}</TooltipContent>
        </Tooltip>
        <span className={`text-sm font-semibold ${score === 0 ? "text-slate-800" : scoreColor(score)}`}>{label}</span>
      </div>
      <WhyTooltip lines={sub}>
        <span className={`mt-0.5 text-[11px] tabular-nums ${score === 0 ? "text-slate-400" : scoreColor(score)}`}>{scoreText(score)}</span>
      </WhyTooltip>
    </div>
  );
}

function Warn() {
  return <AlertTriangle className="ml-0.5 inline size-3.5 text-amber-500" aria-label="数据质量提示" />;
}

function shortLines(a: AssetSnapshot): string[] {
  const c = a.short.components;
  const out = [
    `Flash ${scoreText(c.flash.score)} · ${c.flash.days}日收益 ${c.flash.ret_pct ?? "—"}% (z ${c.flash.z ?? "—"})`,
    `FM ${scoreText(c.fm.score)} · ${c.fm.group} 4周流量 z ${c.fm.z ?? "—"} · 水位 ${c.fm.level_pct_3y ?? "—"}%`,
    `Gamma ${scoreText(c.gamma.score)} · ${c.gamma.note}`,
    `加权原始分 ${a.short.raw ?? "—"} → ${scoreText(a.short.score)}`,
  ];
  return out.concat(a.short.overlays);
}

function longLines(a: AssetSnapshot): string[] {
  const c = a.long.components;
  return [
    `Confirmed ${scoreText(c.confirmed.score)} · 三票 ${c.confirmed.votes > 0 ? "+" : ""}${c.confirmed.votes} · 63日收益 ${c.confirmed.ret_63d_pct ?? "—"}%`,
    `RM ${scoreText(c.rm.score)} · ${c.rm.group} 13周流量 z ${c.rm.z ?? "—"} · 水位 ${c.rm.level_pct_3y ?? "—"}%`,
    `FV ${scoreText(c.fv.score)} · 相对1年均值偏离 ${c.fv.stretch_z ?? "—"}σ`,
    `加权原始分 ${a.long.raw ?? "—"} → ${scoreText(a.long.score)}`,
  ].concat(a.long.notes);
}

export function MatrixTable({ snapshot, timeline }: Props) {
  const [selected, setSelected] = useState<AssetSnapshot | null>(null);

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[960px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
              <th className="w-[120px] px-4 py-3 font-medium">大类</th>
              <th className="w-[200px] px-3 py-3 text-center font-medium">
                <div className="font-semibold text-slate-700">
                  短线 DELTA <span className="font-normal text-slate-500">~1–4周</span>
                </div>
                <div className="text-[11px] text-slate-400">Flash · FM · Gamma</div>
              </th>
              <th className="w-[200px] px-3 py-3 text-center font-medium">
                <div className="font-semibold text-slate-700">
                  长线 DELTA <span className="font-normal text-slate-500">~1–3月</span>
                </div>
                <div className="text-[11px] text-slate-400">Confirmed · RM · FV</div>
              </th>
              <th className="px-3 py-3 text-center font-semibold tracking-wide text-slate-700">VEGA</th>
              <th className="px-3 py-3 text-center font-semibold tracking-wide text-slate-700">SKEW</th>
              <th className="px-3 py-3 text-center font-semibold tracking-wide text-slate-700">GAMMA</th>
              <th className="px-3 py-3 text-center font-semibold tracking-wide text-slate-700">VOL体制</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.assets.map((a) => (
              <tr
                key={a.key}
                style={{ backgroundColor: heatBackground(a.heat.value, a.heat.max) }}
                className="cursor-pointer border-b border-slate-200/80 last:border-b-0 transition-colors hover:brightness-[0.97]"
                onClick={() => setSelected(a)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(a);
                  }
                }}
                aria-label={`${a.name} 详情`}
              >
                <td className="px-4 py-4 align-middle">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-base font-bold text-slate-900">{a.name}</span>
                    <span className="text-[11px] text-slate-400">{a.code_label}</span>
                    {a.diverge && (
                      <Tooltip>
                        <TooltipTrigger render={<span className="text-xs font-semibold text-slate-500" />}>≠</TooltipTrigger>
                        <TooltipContent>短线与长线方向不一致</TooltipContent>
                      </Tooltip>
                    )}
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-400">
                    热度 {a.heat.value}/{a.heat.max} · {heatWord(a.heat.value)}
                  </div>
                </td>
                <td className="px-3 py-3 align-middle">
                  <DeltaBox score={a.short.score} label={a.short.label} dot={a.short.dot} sub={shortLines(a)} />
                </td>
                <td className="px-3 py-3 align-middle">
                  <DeltaBox score={a.long.score} label={a.long.label} dot={a.long.dot} structural={a.long.structural} sub={longLines(a)} />
                </td>
                <td className="px-3 py-3 text-center align-middle">
                  <WhyTooltip lines={a.vega.why} title={`Vega · ${a.vega.metrics.iv_source ?? ""}`}>
                    <span className={`text-sm font-medium ${scoreColor(a.vega.score)}`}>
                      {a.vega.label}
                      {a.vega.warn && <Warn />}
                    </span>
                  </WhyTooltip>
                </td>
                <td className="px-3 py-3 text-center align-middle">
                  <WhyTooltip lines={a.skew.why} title={`Skew · ${a.skew.metrics.proxy ?? a.option_proxy} 25Δ 风险逆转`}>
                    <span className={`text-sm font-medium ${scoreColor(a.skew.score)}`}>
                      {a.skew.label}
                      {a.skew.warn && <Warn />}
                    </span>
                  </WhyTooltip>
                </td>
                <td className="px-3 py-3 text-center align-middle">
                  <WhyTooltip lines={a.gamma.why} title={`Gamma · ${a.gamma.metrics.proxy ?? a.option_proxy} 做市商 GEX`}>
                    <span className={`text-sm font-medium ${gammaColor(a.gamma.code, a.gamma.label)}`}>
                      {a.gamma.label}
                      {a.gamma.warn && <Warn />}
                    </span>
                  </WhyTooltip>
                </td>
                <td className="px-3 py-3 text-center align-middle">
                  <WhyTooltip lines={a.regime.why} title={`Vol 体制 · ${a.regime.metrics.source ?? ""}`}>
                    <span className="inline-flex items-center gap-1.5 text-sm text-slate-700">
                      <span className={`inline-block size-1.5 rounded-full ${regimeDot(a.regime.code)}`} />
                      {a.regime.label}
                      {a.regime.warn && <Warn />}
                    </span>
                  </WhyTooltip>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <AssetSheet asset={selected} timeline={timeline} onClose={() => setSelected(null)} />
    </>
  );
}
