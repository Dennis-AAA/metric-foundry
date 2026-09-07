import type { Dot, GammaCode, RegimeCode } from "./types";

export function fmt(x: number | null | undefined, digits = 2, suffix = ""): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${x.toFixed(digits)}${suffix}`;
}

export function signed(x: number | null | undefined, digits = 2, suffix = ""): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const s = x > 0 ? "+" : "";
  return `${s}${x.toFixed(digits)}${suffix}`;
}

export function scoreText(score: number): string {
  return score > 0 ? `+${score}` : `${score}`;
}

/** Text colour for a directional / vol score. Positive = long / long-vol = emerald. */
export function scoreColor(score: number): string {
  if (score > 0) return "text-emerald-700";
  if (score < 0) return "text-rose-700";
  return "text-slate-500";
}

export function dotColor(dot: Dot): string {
  return dot === "green" ? "bg-emerald-500" : dot === "red" ? "bg-rose-500" : "bg-amber-400";
}

export function dotMeaning(dot: Dot): string {
  return dot === "green" ? "趋势分项偏多" : dot === "red" ? "趋势分项偏空" : "趋势分项中性/混合";
}

/** Box styling of the two DELTA cells: dashed neutral, tinted when a bias exists. */
export function deltaBoxClass(score: number, structural = false): string {
  if (score === 0) return "border-dashed border-slate-300 bg-white";
  const tint = score > 0 ? "border-emerald-300 bg-emerald-50/70" : "border-rose-300 bg-rose-50/70";
  return `${structural ? "border-dashed" : "border-solid"} ${tint}`;
}

export function gammaColor(code: GammaCode, label: string): string {
  if (code === "calm") return "text-rose-700";
  if (code === "storm") return label.includes("偏多") ? "text-emerald-700" : "text-rose-700";
  return "text-slate-500";
}

export function regimeDot(code: RegimeCode): string {
  switch (code) {
    case "high_expanding":
    case "choppy":
      return "bg-amber-500";
    case "high_easing":
    case "low_turning":
      return "bg-sky-500";
    default:
      return "bg-slate-400";
  }
}

export function heatBackground(heat: number, max = 12): string {
  const alpha = Math.min(0.14, 0.02 + (heat / max) * 0.16);
  return `rgba(15, 23, 42, ${alpha.toFixed(3)})`;
}

export function heatWord(heat: number): string {
  if (heat >= 7) return "高";
  if (heat >= 4) return "中";
  return "低";
}

export function statusBadge(status: "ok" | "warn" | "error"): string {
  return status === "ok"
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : status === "warn"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-rose-50 text-rose-700 border-rose-200";
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-CN", { hour12: false, timeZone: "Asia/Shanghai" }) + " (北京时间)";
}
