export function Legend() {
  return (
    <div className="grid gap-2 text-[11px] leading-relaxed text-slate-500 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <span className="font-semibold text-slate-700">行底</span> = 综合热度（|短线| + |长线| + |Vega| + |Skew| + Gamma 体制 + Vol 体制，0–12），越深越热。
      </div>
      <div>
        <span className="font-semibold text-slate-700">≠</span> 短线与长线方向不一致；<span className="font-semibold text-slate-700">圆点</span> = 趋势分项状态（短线 Flash / 长线 Confirmed），文字 = 叠加后的结论。
      </div>
      <div>
        <span className="font-semibold text-slate-700">虚线框</span> = 中性或“结构观察”（半档、雷达）；<span className="font-semibold text-slate-700">实线框</span> = 有方向且趋势确认。
      </div>
      <div>
        <span className="font-semibold text-slate-700">⚠</span> 数据质量提示：期权链稀疏、ETF 代理、无公开 IV 指数或分项信号冲突。美债 = ZN 价格方向，FX = 6E / 6J 期货方向。
      </div>
    </div>
  );
}
