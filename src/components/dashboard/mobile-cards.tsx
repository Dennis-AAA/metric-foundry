"use client";

import { useState } from "react";

import { deltaBoxClass, dotColor, gammaColor, heatBackground, regimeDot, scoreColor, scoreText } from "@/lib/format";
import type { AssetSnapshot, Snapshot, Timeline } from "@/lib/types";

import { AssetSheet } from "./asset-sheet";

interface Props {
  snapshot: Snapshot;
  timeline: Timeline;
}

function Chip({ label, value, className }: { label: string; value: string; className: string }) {
  return (
    <div className="flex flex-col rounded-md border border-slate-200 bg-white px-2 py-1.5">
      <span className="text-[10px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className={`text-sm font-medium ${className}`}>{value}</span>
    </div>
  );
}

export function MobileCards({ snapshot, timeline }: Props) {
  const [selected, setSelected] = useState<AssetSnapshot | null>(null);
  return (
    <>
      <div className="flex flex-col gap-3">
        {snapshot.assets.map((a) => (
          <button
            key={a.key}
            type="button"
            onClick={() => setSelected(a)}
            style={{ backgroundColor: heatBackground(a.heat.value, a.heat.max) }}
            className="rounded-xl border border-slate-200 p-3 text-left shadow-sm"
          >
            <div className="mb-2 flex items-baseline justify-between">
              <div className="flex items-baseline gap-1.5">
                <span className="text-base font-bold text-slate-900">{a.name}</span>
                <span className="text-[11px] text-slate-400">{a.code_label}</span>
                {a.diverge && <span className="text-xs font-semibold text-slate-500">≠</span>}
              </div>
              <span className="text-[11px] text-slate-500">
                热度 {a.heat.value}/{a.heat.max}
              </span>
            </div>
            <div className="mb-2 grid grid-cols-2 gap-2">
              {[
                { t: "短线 1–4周", d: a.short },
                { t: "长线 1–3月", d: a.long },
              ].map(({ t, d }) => (
                <div key={t} className={`rounded-md border px-2 py-1.5 ${deltaBoxClass(d.score, "structural" in d ? d.structural : false)}`}>
                  <div className="text-[10px] text-slate-400">{t}</div>
                  <div className="flex items-center gap-1.5">
                    <span className={`inline-block size-2 rounded-full ${dotColor(d.dot)}`} />
                    <span className={`text-sm font-semibold ${d.score === 0 ? "text-slate-800" : scoreColor(d.score)}`}>{d.label}</span>
                    <span className="ml-auto text-[11px] text-slate-400">{scoreText(d.score)}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Chip label="Vega" value={a.vega.label + (a.vega.warn ? " ⚠" : "")} className={scoreColor(a.vega.score)} />
              <Chip label="Skew" value={a.skew.label + (a.skew.warn ? " ⚠" : "")} className={scoreColor(a.skew.score)} />
              <Chip label="Gamma" value={a.gamma.label + (a.gamma.warn ? " ⚠" : "")} className={gammaColor(a.gamma.code, a.gamma.label)} />
              <div className="flex flex-col rounded-md border border-slate-200 bg-white px-2 py-1.5">
                <span className="text-[10px] uppercase tracking-wide text-slate-400">Vol 体制</span>
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-700">
                  <span className={`inline-block size-1.5 rounded-full ${regimeDot(a.regime.code)}`} />
                  {a.regime.label}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
      <AssetSheet asset={selected} timeline={timeline} onClose={() => setSelected(null)} />
    </>
  );
}
