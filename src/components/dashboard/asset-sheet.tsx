"use client";

import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fmt, gammaColor, scoreColor, scoreText, signed } from "@/lib/format";
import type { AssetSnapshot, Timeline } from "@/lib/types";

import { GexProfile } from "./gex-profile";
import { ScoreSteps, Sparkline } from "./sparkline";

interface Props {
  asset: AssetSnapshot | null;
  timeline: Timeline;
  onClose: () => void;
}

function Metric({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-1.5 text-sm last:border-b-0">
      <div className="text-slate-500">
        {label}
        {hint && <div className="text-[11px] text-slate-400">{hint}</div>}
      </div>
      <div className="text-right font-medium tabular-nums text-slate-800">{value}</div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  return (
    <Badge variant="outline" className={`tabular-nums ${scoreColor(score)}`}>
      {scoreText(score)}
    </Badge>
  );
}

function WhyList({ lines }: { lines: string[] }) {
  if (!lines?.length) return null;
  return (
    <ul className="mt-3 list-disc space-y-1 rounded-md bg-slate-50 px-4 py-3 pl-8 text-sm text-slate-600">
      {lines.map((l, i) => (
        <li key={i}>{l}</li>
      ))}
    </ul>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      {children}
    </section>
  );
}

export function AssetSheet({ asset, timeline, onClose }: Props) {
  const a = asset;
  const tl = a ? timeline.assets[a.key] : undefined;
  return (
    <Sheet open={!!a} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto p-0 sm:max-w-2xl">
        {a && (
          <div className="flex flex-col gap-4 p-6">
            <SheetHeader className="p-0">
              <SheetTitle className="flex flex-wrap items-baseline gap-2 text-xl">
                {a.name}
                <span className="text-sm font-normal text-slate-500">{a.instrument}</span>
              </SheetTitle>
              <SheetDescription className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span>
                  {a.futures_ticker} 收盘 <span className="font-medium text-slate-800">{fmt(a.price, a.price && a.price < 1 ? 5 : 2)}</span>{" "}
                  <span className={a.chg_1d_pct !== null && a.chg_1d_pct >= 0 ? "text-emerald-700" : "text-rose-700"}>{signed(a.chg_1d_pct, 2, "%")}</span>
                </span>
                <span>价格日期 {a.price_date}</span>
                <span>COT {a.cot_date ?? "—"}</span>
                <span>期权代理 {a.option_proxy}</span>
              </SheetDescription>
            </SheetHeader>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {[
                ["短线", a.short.label, a.short.score],
                ["长线", a.long.label, a.long.score],
                ["Vega", a.vega.label, a.vega.score],
                ["Skew", a.skew.label, a.skew.score],
                ["Gamma", a.gamma.label, a.gamma.score],
                ["体制", a.regime.label, 0],
              ].map(([k, v, s]) => (
                <div key={k as string} className="rounded-md border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">{k as string}</div>
                  <div className={`text-sm font-semibold ${k === "Gamma" ? gammaColor(a.gamma.code, a.gamma.label) : k === "体制" ? "text-slate-700" : scoreColor(s as number)}`}>{v as string}</div>
                </div>
              ))}
            </div>

            <Tabs defaultValue="overview">
              <TabsList className="flex w-full flex-wrap">
                <TabsTrigger value="overview">概览</TabsTrigger>
                <TabsTrigger value="short">短线</TabsTrigger>
                <TabsTrigger value="long">长线</TabsTrigger>
                <TabsTrigger value="vega">Vega</TabsTrigger>
                <TabsTrigger value="skew">Skew</TabsTrigger>
                <TabsTrigger value="gamma">Gamma</TabsTrigger>
                <TabsTrigger value="regime">体制</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="flex flex-col gap-3">
                <Section title="综合热度">
                  <div className="flex items-center gap-3">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-slate-800" style={{ width: `${(a.heat.value / a.heat.max) * 100}%` }} />
                    </div>
                    <span className="text-sm font-semibold tabular-nums">
                      {a.heat.value}/{a.heat.max}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-slate-500">
                    {Object.entries(a.heat.parts).map(([k, v]) => (
                      <span key={k} className="rounded bg-slate-100 px-1.5 py-0.5">
                        {k} {v}
                      </span>
                    ))}
                  </div>
                </Section>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Section title={`${a.futures_ticker} 收盘 · 90日`}>
                    <Sparkline data={a.series.close} width={280} height={60} stroke="auto" />
                  </Section>
                  <Section title="隐含波动率 · 90日">
                    <Sparkline data={a.series.iv} width={280} height={60} stroke="#7c3aed" />
                  </Section>
                  <Section title="快钱净仓位 (占OI%) · 52周">
                    <Sparkline data={a.series.fm_net_pct} width={280} height={60} stroke="#0f766e" zeroLine />
                  </Section>
                  <Section title="慢钱净仓位 (占OI%) · 52周">
                    <Sparkline data={a.series.rm_net_pct} width={280} height={60} stroke="#1d4ed8" zeroLine />
                  </Section>
                </div>
                <Section title="信号历史（每次更新累计一个点）">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <div className="mb-1 text-xs text-slate-500">短线 DELTA</div>
                      <ScoreSteps values={tl?.short ?? []} dates={timeline.dates} />
                    </div>
                    <div>
                      <div className="mb-1 text-xs text-slate-500">长线 DELTA</div>
                      <ScoreSteps values={tl?.long ?? []} dates={timeline.dates} />
                    </div>
                    <div>
                      <div className="mb-1 text-xs text-slate-500">Vega</div>
                      <ScoreSteps values={tl?.vega ?? []} dates={timeline.dates} />
                    </div>
                    <div>
                      <div className="mb-1 text-xs text-slate-500">Skew</div>
                      <ScoreSteps values={tl?.skew ?? []} dates={timeline.dates} />
                    </div>
                  </div>
                </Section>
              </TabsContent>

              <TabsContent value="short" className="flex flex-col gap-3">
                <Section title="Flash（价格冲量）">
                  <Metric label="分项得分" value={<ScoreBadge score={a.short.components.flash.score} />} />
                  <Metric label={`${a.short.components.flash.days}日收益`} value={signed(a.short.components.flash.ret_pct, 2, "%")} />
                  <Metric label="z 值（vs 1年）" value={signed(a.short.components.flash.z)} />
                  <Metric label="突破" value={a.short.components.flash.breakout ?? "无"} />
                  <p className="mt-2 text-xs text-slate-400">{a.short.components.flash.desc}</p>
                </Section>
                <Section title={`FM 快钱仓位 · ${a.short.components.fm.group}`}>
                  <Metric label="分项得分" value={<ScoreBadge score={a.short.components.fm.score} />} />
                  <Metric label="净仓位 / OI" value={signed(a.short.components.fm.net_pct_oi, 1, "%")} />
                  <Metric label="4周流量 (占OI)" value={signed(a.short.components.fm.flow_4w_pct_oi, 2, "%")} />
                  <Metric label="流量 z 值" value={signed(a.short.components.fm.z)} />
                  <Metric label="3年水位分位" value={fmt(a.short.components.fm.level_pct_3y, 0, "%")} hint=">90% 多头拥挤 / <10% 空头拥挤" />
                  <p className="mt-2 text-xs text-slate-400">{a.short.components.fm.desc}</p>
                </Section>
                <Section title="Gamma 修正">
                  <Metric label="分项得分" value={<ScoreBadge score={a.short.components.gamma.score} />} />
                  <Metric label="净 GEX (bn$/1%)" value={signed(a.short.components.gamma.net_gex_bn, 3)} />
                  <p className="mt-2 text-xs text-slate-500">{a.short.components.gamma.note}</p>
                </Section>
                <Section title="合成">
                  <Metric label="权重" value={Object.entries(a.short.weights).map(([k, v]) => `${k} ${v}`).join(" · ")} />
                  <Metric label="加权原始分" value={signed(a.short.raw)} />
                  <Metric label="最终" value={<span className={`font-semibold ${scoreColor(a.short.score)}`}>{a.short.label} ({scoreText(a.short.score)})</span>} />
                  <WhyList lines={a.short.overlays} />
                </Section>
              </TabsContent>

              <TabsContent value="long" className="flex flex-col gap-3">
                <Section title="Confirmed（趋势确认）">
                  <Metric label="分项得分" value={<ScoreBadge score={a.long.components.confirmed.score} />} />
                  <Metric label="三票合计" value={signed(a.long.components.confirmed.votes, 0)} hint="价格>MA200 · MA50>MA200 · 63日收益>0" />
                  <Metric label="价格 > MA200" value={a.long.components.confirmed.above_ma200 ? "是" : "否"} />
                  <Metric label="MA50 > MA200" value={a.long.components.confirmed.ma50_gt_ma200 ? "是" : "否"} />
                  <Metric label="63日收益" value={signed(a.long.components.confirmed.ret_63d_pct, 2, "%")} />
                  <Metric label="63日收益 z" value={signed(a.long.components.confirmed.ret_63d_z)} />
                </Section>
                <Section title={`RM 慢钱仓位 · ${a.long.components.rm.group}`}>
                  <Metric label="分项得分" value={<ScoreBadge score={a.long.components.rm.score} />} />
                  <Metric label="净仓位 / OI" value={signed(a.long.components.rm.net_pct_oi, 1, "%")} />
                  <Metric label="13周流量 (占OI)" value={signed(a.long.components.rm.flow_13w_pct_oi, 2, "%")} />
                  <Metric label="流量 z 值" value={signed(a.long.components.rm.z)} />
                  <Metric label="3年水位分位" value={fmt(a.long.components.rm.level_pct_3y, 0, "%")} />
                </Section>
                <Section title="FV（估值偏离）">
                  <Metric label="分项得分" value={<ScoreBadge score={a.long.components.fv.score} />} />
                  <Metric label="偏离 1年均值" value={signed(a.long.components.fv.stretch_z, 2, "σ")} />
                  <p className="mt-2 text-xs text-slate-400">{a.long.components.fv.desc}</p>
                </Section>
                <Section title="合成">
                  <Metric label="权重" value={Object.entries(a.long.weights).map(([k, v]) => `${k} ${v}`).join(" · ")} />
                  <Metric label="加权原始分" value={signed(a.long.raw)} />
                  <Metric label="结构观察 (半档)" value={a.long.structural ? "是" : "否"} />
                  <Metric label="最终" value={<span className={`font-semibold ${scoreColor(a.long.score)}`}>{a.long.label} ({scoreText(a.long.score)})</span>} />
                  <WhyList lines={a.long.notes} />
                </Section>
              </TabsContent>

              <TabsContent value="vega" className="flex flex-col gap-3">
                <Section title={`隐含 vs 已实现 · ${a.vega.metrics.iv_source ?? ""}`}>
                  <Metric label="隐含波动率 (IV)" value={fmt(a.vega.metrics.iv, 2, "%")} />
                  <Metric label="IV 1年分位" value={fmt(a.vega.metrics.iv_pct_1y, 0, "%")} />
                  <Metric label="RV20 / RV60" value={`${fmt(a.vega.metrics.rv20)} / ${fmt(a.vega.metrics.rv60)}`} />
                  <Metric label="IV − RV20" value={signed(a.vega.metrics.iv_minus_rv, 2, " vol")} />
                  <Metric label="Carry (IV/RV−1)" value={signed(a.vega.metrics.carry, 0, "%")} hint="< −10% 买波 · > +30% 卖波" />
                  <Metric label="水位分 / carry 分" value={`${a.vega.metrics.level_pts ?? 0} / ${a.vega.metrics.carry_pts ?? 0}`} />
                  {a.vega.metrics.term && (
                    <>
                      <Metric label="VIX9D / VIX" value={fmt(a.vega.metrics.term.vix9d_vix, 3)} />
                      <Metric label="VIX / VIX3M" value={`${fmt(a.vega.metrics.term.vix_vix3m, 3)} · ${a.vega.metrics.term.shape}`} />
                      <Metric label="VVIX" value={fmt(a.vega.metrics.term.vvix, 1)} />
                    </>
                  )}
                  <WhyList lines={a.vega.why} />
                </Section>
              </TabsContent>

              <TabsContent value="skew" className="flex flex-col gap-3">
                <Section title={`25Δ 风险逆转 · ${a.skew.metrics.proxy ?? a.option_proxy} ${a.skew.metrics.expiry ?? ""}`}>
                  <Metric label="RR25 (call − put)" value={signed(a.skew.metrics.rr25_vol, 2, " vol")} />
                  <Metric label="RR25 / ATM IV" value={signed(a.skew.metrics.rr25_norm == null ? null : a.skew.metrics.rr25_norm * 100, 0, "%")} />
                  <Metric label="资产常态" value={signed(a.skew.metrics.baseline == null ? null : a.skew.metrics.baseline * 100, 0, "%")} />
                  <Metric label="偏离常态" value={signed(a.skew.metrics.dev_vs_baseline == null ? null : a.skew.metrics.dev_vs_baseline * 100, 0, "%")} />
                  <Metric label="ATM / 25Δ Call / 25Δ Put IV" value={`${fmt(a.skew.metrics.atm_iv, 1)} / ${fmt(a.skew.metrics.call25_iv, 1)} / ${fmt(a.skew.metrics.put25_iv, 1)}`} />
                  <Metric label="到期 / DTE" value={`${a.skew.metrics.expiry ?? "—"} / ${a.skew.metrics.dte ?? "—"}`} />
                  <Metric label="有效报价 (call / put)" value={a.skew.metrics.n_quotes ? a.skew.metrics.n_quotes.join(" / ") : "—"} />
                  {a.skew.metrics.skew_index != null && <Metric label="CBOE SKEW 指数" value={fmt(a.skew.metrics.skew_index, 1)} />}
                  <WhyList lines={a.skew.why} />
                </Section>
              </TabsContent>

              <TabsContent value="gamma" className="flex flex-col gap-3">
                <Section title={`做市商 Gamma 曲线 · ${a.gamma.metrics.proxy ?? a.option_proxy} ≤${a.gamma.metrics.max_dte ?? "—"}DTE`}>
                  <GexProfile profile={a.gamma.metrics.profile ?? []} spot={a.gamma.metrics.spot} flip={a.gamma.metrics.flip} />
                  <Metric label="净 GEX (bn$ / 1%)" value={signed(a.gamma.metrics.net_gex_bn, 3)} />
                  <Metric label="Call / Put gamma" value={`${fmt(a.gamma.metrics.call_gex_bn, 3)} / ${fmt(a.gamma.metrics.put_gex_bn, 3)}`} />
                  <Metric label="净/总 比例" value={signed(a.gamma.metrics.ratio, 2)} hint="|比例| < 0.15 视为平衡 → 初起" />
                  <Metric label="翻转位 / 现价" value={`${fmt(a.gamma.metrics.flip)} / ${fmt(a.gamma.metrics.spot)} (${signed(a.gamma.metrics.spot_vs_flip_pct, 1, "%")})`} />
                  <Metric label="总 OI / 到期数" value={`${a.gamma.metrics.total_oi?.toLocaleString() ?? "—"} / ${a.gamma.metrics.n_expiries ?? "—"}`} />
                  {a.gamma.metrics.largest_strikes && a.gamma.metrics.largest_strikes.length > 0 && (
                    <div className="mt-3">
                      <div className="mb-1 text-xs text-slate-500">最大 gamma 行权价 (bn$/1%)</div>
                      <div className="flex flex-wrap gap-1.5">
                        {a.gamma.metrics.largest_strikes.map(([k, v]) => (
                          <span key={k} className={`rounded px-1.5 py-0.5 text-[11px] tabular-nums ${v >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>
                            {k} · {signed(v, 2)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <WhyList lines={a.gamma.why} />
                </Section>
              </TabsContent>

              <TabsContent value="regime" className="flex flex-col gap-3">
                <Section title={`波动率体制 · ${a.regime.metrics.source ?? ""}`}>
                  <Metric label="当前波动率" value={fmt(a.regime.metrics.vol_now, 2, "%")} />
                  <Metric label="1年分位" value={fmt(a.regime.metrics.vol_pct_1y, 0, "%")} hint=">70% 高Vol · <40% 低Vol" />
                  <Metric label="5日变化" value={signed(a.regime.metrics.chg_5d_pct, 0, "%")} />
                  <Metric label="vol-of-vol 分位" value={fmt(a.regime.metrics.vov_pct_1y, 0, "%")} hint=">75% 且 RV>IV 或 RV20/RV60>1.15 → 混乱" />
                  <Metric label="RV20 / RV60" value={`${fmt(a.regime.metrics.rv20)} / ${fmt(a.regime.metrics.rv60)} (${fmt(a.regime.metrics.rv_ratio)})`} />
                  <WhyList lines={a.regime.why} />
                </Section>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
