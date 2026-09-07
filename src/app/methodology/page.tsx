import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";

export const metadata = {
  title: "方法说明 · 方向偏好 × 波动率偏好",
};

function Row({ cells, head = false }: { cells: React.ReactNode[]; head?: boolean }) {
  const Tag = head ? "th" : "td";
  return (
    <tr className={head ? "bg-slate-50 text-left text-xs text-slate-500" : "border-t border-slate-200 align-top text-sm"}>
      {cells.map((c, i) => (
        <Tag key={i} className={`px-3 py-2 ${head ? "font-medium" : ""}`}>
          {c}
        </Tag>
      ))}
    </tr>
  );
}

function Rule({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[160px_1fr]">
      <div className="text-sm font-semibold text-slate-800">{label}</div>
      <div className="text-sm leading-relaxed text-slate-600">{children}</div>
    </div>
  );
}

const ok = <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">可复现</span>;
const approx = <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">近似/代理</span>;
const weak = <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[11px] font-medium text-rose-700">弱代理</span>;

export default function MethodologyPage() {
  return (
    <main className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6">
      <div>
        <Button variant="ghost" size="sm" render={<Link href="/" />}>
          <ArrowLeft />
          返回看板
        </Button>
      </div>
      <header>
        <h1 className="text-2xl font-bold tracking-tight">方法说明与复现边界</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          看板把原图的七列全部落实为可计算的规则。每一列由 <code className="rounded bg-slate-100 px-1">engine/macrovol/signals.py</code> 中的一个函数生成，
          阈值集中在 <code className="rounded bg-slate-100 px-1">engine/macrovol/config.py</code>。 所有数据来自公开免费来源；无法免费获取的部分用明确标注的代理量替代，并在单元格上以 ⚠ 提示。
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">数据源</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <Row head cells={["数据", "来源", "频率", "用途"]} />
            </thead>
            <tbody>
              <Row cells={["ES / ZN / 6E / 6J / GC / CL 期货日线", "Yahoo Finance (yfinance)", "日", "Flash、Confirmed、FV、已实现波动率"]} />
              <Row cells={["VIX · VIX9D · VIX3M · VVIX · SKEW · GVZ · OVX", "CBOE 官方 CSV 历史", "日", "美股 / 黄金 / 原油的隐含波动率水位、期限结构、尾部偏斜"]} />
              <Row cells={["MOVE", "Yahoo Finance (^MOVE)", "日", "美债隐含波动率（×0.065 换算为 ZN 价格波动率）"]} />
              <Row cells={["SPY · TLT · FXE · FXY · GLD · USO 期权链（IV、OI）", "Yahoo Finance", "日（盘后）", "25Δ 风险逆转（Skew）、做市商 Gamma 曲线（GEX）、FX 的 ATM IV"]} />
              <Row cells={["CFTC 持仓报告 TFF / Disaggregated（期货）", "publicreporting.cftc.gov (Socrata API)", "周（周五 15:30 ET 发布，截至周二）", "FM 快钱 = Leveraged Funds / Managed Money；RM 慢钱 = Asset Manager / Swap Dealers"]} />
              <Row cells={["13 周国债收益率 (^IRX)", "Yahoo Finance", "日", "Greeks 的无风险利率"]} />
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">七列的计算规则</h2>
        <div className="flex flex-col gap-5">
          <Rule label="短线 DELTA (1–4 周)">
            {ok} 三个分项各打 −2…+2：<b>Flash</b> = 10 日收益相对 1 年分布的 z 值（±0.75σ → ±1，±1.5σ → ±2）；<b>FM</b> = 快钱净仓位（占 OI%）4 周变化的 z 值，3 年水位 &gt;90% / &lt;10% 视为拥挤并打折；
            <b>Gamma</b> = 做市商净 Gamma 为负时放大 Flash 方向，为正时为 0。 加权 0.5 / 0.3 / 0.2 后取整。 <b>高频叠加</b>：若做市商多 Gamma 且波动率体制为“平静”，|原始分| &lt; 1.25 一律拉回中性——对应原图“全部拉回中性”。 圆点颜色 = Flash 分项的原始方向。
          </Rule>
          <Rule label="长线 DELTA (1–3 月)">
            {ok} <b>Confirmed</b> = 三票制（价格 &gt; MA200、MA50 &gt; MA200、63 日收益 &gt; 0），三票同向 ±2，否则看 63 日收益 z 值；<b>RM</b> = 慢钱净仓位 13 周变化 z 值；<b>FV</b> = 对数价格相对 1 年均值的偏离，&gt;+1.5σ 记 −1（偏贵）、&lt;−1.5σ 记 +1。 加权 0.4 / 0.3 / 0.3。 若最终方向不是由 Confirmed 驱动（趋势未确认、仅结构分项主导），只给<b>半档 ±1</b> 并标注“结构观察”（原图的“暂定结构·雷达·半档”）；由三票趋势驱动则标注“确认”。
          </Rule>
          <Rule label="VEGA">
            {ok} 水位分：IV 1 年分位 &lt;10% → +2、&lt;25% → +1、&gt;75% → −1、&gt;90% → −2；Carry 分：(IV − RV20)/RV20 &lt; −10% → +1、&gt; +30% → −1。 两者相加并截断到 ±2：+2 强买波、+1 买波、−1 卖波、−2 强卖波。 水位与 carry 冲突时标 ⚠。 EUR / JPY 没有公开 IV 指数（CBOE EVZ/JYVIX 已停更）：{approx} IV 取 FXE / FXY 期权链 ATM IV，水位用 RV20 的 1 年分位代理；看板累计 60 个以上日度快照后自动改用自身 IV 历史分位。
          </Rule>
          <Rule label="SKEW">
            {ok} 选取 21–90 DTE 中流动性最好、最接近 45 DTE 的到期，用 Black-Scholes delta 在 OTM 两翼插值出 25Δ call / put 的 IV，RR25 = call − put，再除以 ATM IV 归一化。 RR/ATM &lt; −5% → 偏空 RR，&gt; +5% → 偏多 RR，|RR/ATM| &gt; 35% 为 ±2。 与该资产“常态偏斜”（美股 −30%、黄金 +5% 等）偏离超过 10% 而标签仍为中性时标 ⚠；美股附加 CBOE SKEW 指数。 {weak} FXE / FXY 报价极稀疏，EUR 通常无法算出，JPY 会带 ⚠。
          </Rule>
          <Rule label="GAMMA">
            {approx} 采用 SpotGamma 式假设：做市商持有全部 call 多头、put 空头。 对 ≤60 DTE 的所有合约计算 Γ × OI × 100 × S² × 1%，得到每 1% 波动的美元 Gamma；在 ±15% 的价格网格上重新定价整本簿子得到 Gamma 曲线，零点即“翻转位”。 净 Gamma &gt; 0 且不贴近翻转位 → <b>平静·收theta</b>；净 Gamma &lt; 0 → <b>风暴</b>（方向跟随 Flash）；|净/总| &lt; 0.15 或现价在翻转位 ±1% 内 → <b>初起·中性</b>。 期货期权（ES/ZN/GC/CL 本身的 CME 期权）没有免费链数据，因此以 ETF 期权代理；SPY/GLD/TLT 质量尚可，USO/FXE/FXY {weak} 并标 ⚠。
          </Rule>
          <Rule label="VOL 体制">
            {ok} 以隐含波动率序列（无指数者用 RV20）计算 1 年分位、5 日变化、vol-of-vol 分位与 RV20/RV60： 分位 &gt;70% 且下行 → <b>高Vol缓和</b>，上行 → <b>高Vol扩张</b>；vol-of-vol 分位 &gt;75% 且 RV &gt; IV 或 RV20/RV60 &gt; 1.15 → <b>混乱</b>；分位 &lt;40% 但 5 日 +15% → <b>低Vol转折</b>；其余 <b>平静</b>。
          </Rule>
          <Rule label="行底 = 综合热度">
            {ok} |短线| + |长线| + |Vega| + |Skew| + Gamma 体制热度（平静 0 / 初起 1 / 风暴 2）+ Vol 体制热度（平静 0 / 缓和·转折 1 / 混乱·扩张 2），范围 0–12，映射为行背景深浅。 “≠” 表示短线与长线方向不一致。
          </Rule>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">与原图的差异 / 不能完全复现的部分</h2>
        <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
          <li>
            原图的 Flash / FM / Confirmed / RM / FV 是作者内部模型的名字，具体口径未知。这里给出的是<b>一套自洽且可审计的公开数据实现</b>：Flash/Confirmed 用价格动量，FM/RM 用 CFTC 持仓，FV 用估值偏离。若你有自己的口径，只需改 <code className="rounded bg-slate-100 px-1">signals.py</code> 对应函数。
          </li>
          <li>真实做市商 Gamma 需要 OPRA 全量成交 + 方向推断（SpotGamma、SqueezeMetrics 等付费数据）；免费方案只能做 ETF 期权的 OI 近似，且 CME 期货期权完全缺失。</li>
          <li>FX 的隐含波动率与偏斜在免费渠道几乎没有可靠来源（CBOE FX 波动率指数 2025 年停更），所以 EUR / JPY 的 Vega / Skew / Gamma 会长期带 ⚠，或显示“无数据”。</li>
          <li>Yahoo Finance 的期权 IV 为交易所盘后快照，深度虚值合约的 IV 噪音大；引擎已过滤无买价的合约并对 Gamma 计算的 IV 做 5%–200% 截断。</li>
          <li>
            原图 JPY 行的“+1 / 空JPY”很可能采用 USDJPY 口径；本看板统一用 6J 期货价格口径（JPY 升值 = 多JPY），并在标签中直接写出 多JPY / 空JPY。
          </li>
        </ul>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">日度 / 周度更新</h2>
        <div className="grid gap-4 text-sm text-slate-600 sm:grid-cols-2">
          <div>
            <h3 className="mb-1 font-semibold text-slate-800">本地</h3>
            <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">{`# 日度（美东收盘后）
python -m macrovol.cli run
# 周度（周五 COT 发布后）
python -m macrovol.cli run --mode weekly
# 也可以在看板右上角点“日度刷新 / 周度刷新”`}</pre>
          </div>
          <div>
            <h3 className="mb-1 font-semibold text-slate-800">自动</h3>
            <p className="leading-relaxed">
              仓库自带 <code className="rounded bg-slate-100 px-1">.github/workflows/update-signals.yml</code>：周一至周五 22:30 UTC（美东收盘后）跑日度，周五 21:00 UTC（COT 发布后）跑周度，结果提交回{" "}
              <code className="rounded bg-slate-100 px-1">data/</code>。 每次运行都会在 <code className="rounded bg-slate-100 px-1">data/history/</code> 留下一份快照，看板的“信号历史”据此累积。
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
