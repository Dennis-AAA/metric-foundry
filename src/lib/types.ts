export type Score = -2 | -1 | 0 | 1 | 2;
export type Dot = "green" | "yellow" | "red";
export type GammaCode = "calm" | "transition" | "storm" | "na";
export type RegimeCode = "calm" | "choppy" | "high_easing" | "high_expanding" | "low_turning";

export interface SourceStatus {
  name: string;
  status: "ok" | "warn" | "error";
  detail: string;
}

export interface FlashComponent {
  score: number;
  z: number | null;
  ret_pct: number | null;
  days: number;
  breakout: string | null;
  desc: string;
}

export interface CotComponent {
  score: number;
  z: number | null;
  net_pct_oi: number | null;
  flow_4w_pct_oi?: number | null;
  flow_13w_pct_oi?: number | null;
  level_pct_3y: number | null;
  group: string;
  desc: string;
}

export interface ShortDelta {
  score: Score;
  label: string;
  dot: Dot;
  raw: number | null;
  overlays: string[];
  components: {
    flash: FlashComponent;
    fm: CotComponent;
    gamma: { score: number; note: string; net_gex_bn: number | null };
  };
  weights: Record<string, number>;
}

export interface LongDelta {
  score: Score;
  label: string;
  dot: Dot;
  structural: boolean;
  confirmed: boolean;
  raw: number | null;
  notes: string[];
  components: {
    confirmed: {
      score: number;
      votes: number;
      above_ma200: boolean;
      ma50_gt_ma200: boolean;
      ret_63d_pct: number | null;
      ret_63d_z: number | null;
      desc: string;
    };
    rm: CotComponent;
    fv: { score: number; stretch_z: number | null; desc: string };
  };
  weights: Record<string, number>;
}

export interface VegaCell {
  score: Score;
  label: string;
  warn: boolean;
  metrics: {
    iv?: number | null;
    iv_source?: string;
    iv_pct_1y?: number | null;
    rv20?: number | null;
    rv60?: number | null;
    iv_minus_rv?: number | null;
    carry?: number | null;
    level_pts?: number;
    carry_pts?: number;
    term?: {
      vix9d_vix: number | null;
      vix_vix3m: number | null;
      vvix: number | null;
      shape: string;
    } | null;
  };
  why: string[];
}

export interface SkewCell {
  score: Score;
  label: string;
  warn: boolean;
  metrics: {
    rr25_vol?: number | null;
    rr25_norm?: number | null;
    baseline?: number;
    dev_vs_baseline?: number | null;
    atm_iv?: number | null;
    call25_iv?: number | null;
    put25_iv?: number | null;
    expiry?: string;
    dte?: number;
    n_quotes?: [number, number];
    skew_index?: number | null;
    proxy?: string;
  };
  why: string[];
}

export interface GammaCell {
  score: number;
  code: GammaCode;
  label: string;
  warn: boolean;
  metrics: {
    net_gex_bn?: number | null;
    call_gex_bn?: number | null;
    put_gex_bn?: number | null;
    ratio?: number | null;
    flip?: number | null;
    spot?: number | null;
    spot_vs_flip_pct?: number | null;
    total_oi?: number;
    n_expiries?: number;
    max_dte?: number;
    proxy?: string;
    profile?: [number, number][];
    largest_strikes?: [number, number][];
  };
  why: string[];
}

export interface RegimeCell {
  code: RegimeCode;
  label: string;
  heat?: number;
  warn: boolean;
  metrics: {
    vol_now?: number | null;
    vol_pct_1y?: number | null;
    chg_5d_pct?: number | null;
    vov_pct_1y?: number | null;
    rv20?: number | null;
    rv60?: number | null;
    rv_ratio?: number | null;
    source?: string;
  };
  why: string[];
}

export type SeriesPoint = [string, number];

export interface AssetSnapshot {
  key: string;
  name: string;
  code_label: string;
  instrument: string;
  futures_ticker: string;
  option_proxy: string;
  diverge: boolean;
  price: number | null;
  price_date: string;
  chg_1d_pct: number | null;
  cot_date: string | null;
  heat: { value: number; max: number; parts: Record<string, number> };
  short: ShortDelta;
  long: LongDelta;
  vega: VegaCell;
  skew: SkewCell;
  gamma: GammaCell;
  regime: RegimeCell;
  series: {
    close: SeriesPoint[];
    iv: SeriesPoint[] | null;
    fm_net_pct: SeriesPoint[] | null;
    rm_net_pct: SeriesPoint[] | null;
  };
}

export interface Snapshot {
  schema_version: number;
  generated_at: string;
  mode: "daily" | "weekly";
  as_of: {
    prices: string;
    vol_indices: string;
    cot: string | null;
    options: string | null;
  };
  risk_free: number | null;
  sources: SourceStatus[];
  notes: { short: string; long: string };
  assets: AssetSnapshot[];
}

export interface Timeline {
  dates: string[];
  assets: Record<
    string,
    {
      short: number[];
      long: number[];
      vega: number[];
      skew: number[];
      gamma: (GammaCode | null)[];
      heat: number[];
      regime: (RegimeCode | null)[];
    }
  >;
}
