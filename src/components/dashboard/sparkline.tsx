import type { SeriesPoint } from "@/lib/types";

interface Props {
  data: SeriesPoint[] | null | undefined;
  width?: number;
  height?: number;
  stroke?: string;
  zeroLine?: boolean;
  className?: string;
}

export function Sparkline({ data, width = 160, height = 40, stroke = "#334155", zeroLine = false, className }: Props) {
  if (!data || data.length < 2) {
    return <div className={`text-xs text-slate-400 ${className ?? ""}`}>历史不足</div>;
  }
  const values = data.map((d) => d[1]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (zeroLine) {
    min = Math.min(min, 0);
    max = Math.max(max, 0);
  }
  const span = max - min || 1;
  const pad = 2;
  const pts = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - pad * 2);
    const y = pad + (1 - (v - min) / span) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const zeroY = pad + (1 - (0 - min) / span) * (height - pad * 2);
  const last = values[values.length - 1];
  const first = values[0];
  const color = zeroLine ? (last >= 0 ? "#047857" : "#be123c") : last >= first ? "#047857" : "#be123c";
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className={className} role="img" aria-label="走势图">
      {zeroLine && <line x1={0} x2={width} y1={zeroY} y2={zeroY} stroke="#cbd5e1" strokeDasharray="3 3" />}
      <polyline fill="none" stroke={stroke === "auto" ? color : stroke} strokeWidth={1.5} points={pts.join(" ")} />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r={2.2} fill={stroke === "auto" ? color : stroke} />
    </svg>
  );
}

interface StepProps {
  values: number[];
  dates: string[];
  width?: number;
  height?: number;
}

/** Discrete -2..+2 score history as a step chart. */
export function ScoreSteps({ values, dates, width = 220, height = 44 }: StepProps) {
  if (values.length < 2) {
    return <div className="text-xs text-slate-400">仅 {values.length} 个快照，累计更多日期后显示历史</div>;
  }
  const pad = 3;
  const y = (v: number) => pad + (1 - (v + 2) / 4) * (height - pad * 2);
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2);
  const d = values
    .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}${i < values.length - 1 ? ` L${x(i + 1).toFixed(1)},${y(v).toFixed(1)}` : ""}`)
    .join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${dates[0]} 至 ${dates[dates.length - 1]}`}>
      <line x1={0} x2={width} y1={y(0)} y2={y(0)} stroke="#cbd5e1" strokeDasharray="3 3" />
      <path d={d} fill="none" stroke="#0f172a" strokeWidth={1.5} />
    </svg>
  );
}
